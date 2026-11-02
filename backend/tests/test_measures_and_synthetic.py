import io
import datetime
import struct
import pandas as pd
import numpy as np
import pytest

from app.measures import (
    calculate_surveillance_measures,
    wilson_score_interval,
    exact_poisson_rate_interval,
)
from app.reference_db import (
    get_reference_summary,
)
from app.district_crosswalk import (
    construct_four_digit_district_code,
    get_district_info,
    load_custom_geography_table,
)
from app.population import population_manager
from app.filters import apply_filters_and_resolve_scope
from app.dds_importer import (
    parse_flexible_date,
    classify_nationality,
    process_dds_dataframe,
    read_dataframe_from_bytes,
    standardize_single_file_dataframe,
    resolve_combined_standardized_dataframe,
)
from app.forecast import (
    build_continuous_weekly_series,
    fit_ols_forecast,
    build_seasonal_comparison_series,
)
from app.studio_renderer import (
    render_figure_1_epicurve,
    render_figure_2_district_bar,
    render_figure_7_forecast,
    render_figure_8_seasonal_comparison,
)


def test_sqlite_reference_counts_and_samut_prakan_lookup():
    summary = get_reference_summary()
    assert summary["db_exists"] is True
    assert summary["counts"] == {
        "province": 77,
        "district": 878,
        "age_bin": 102,
        "population_snapshot": 13,
        "population_by_geography": 1014,
        "population_by_age": 206856,
    }
    assert summary["national_population_2025"] == 65826149
    assert summary["district_example"] == ["1101", "เมืองสมุทรปราการ"]

    p_code, d_code = construct_four_digit_district_code("11", "01")
    assert p_code == "11"
    assert d_code == "1101"
    d_info = get_district_info(d_code, p_code)
    assert d_info["name_th"] == "เมืองสมุทรปราการ"
    assert d_info["lookup_status"] == "matched"

    _, d_heading = construct_four_digit_district_code("11", "00")
    assert d_heading is None

    # Bangkok 50 districts verification
    p_bkk, d_bkk = construct_four_digit_district_code("10", "01")
    assert p_bkk == "10"
    assert d_bkk == "1001"
    bkk_1001 = get_district_info(d_bkk, p_bkk)
    assert bkk_1001["name_th"] == "เขตพระนคร"
    assert bkk_1001["lookup_status"] == "matched"

    bkk_1050 = get_district_info("1050", "10")
    assert bkk_1050["name_th"] == "เขตบางบอน"
    assert bkk_1050["lookup_status"] == "matched"

    from app.reference_db import get_districts_by_province, get_district_by_code
    bkk_all = get_districts_by_province("10")
    assert len(bkk_all) == 50
    assert bkk_all[0]["district_code"] == "1001"
    assert bkk_all[0]["name_th"] == "เขตพระนคร"
    assert bkk_all[-1]["district_code"] == "1050"
    assert bkk_all[-1]["name_th"] == "เขตบางบอน"

    d_lookup_1002 = get_district_by_code("1002")
    assert d_lookup_1002 is not None
    assert d_lookup_1002["name_th"] == "เขตดุสิต"


def test_single_multi_national_and_fallback_2568_denominators():
    # 1. Single province (Phitsanulok = 65, Samut Prakan = 11)
    d_65 = population_manager.resolve_denominator(
        year=2025, prov_codes=["65"], scope_mode="provinces"
    )
    assert d_65["available"] is True
    assert d_65["population"] == 835956
    assert d_65["population_year_be"] == 2568
    assert d_65["is_fallback_year"] is False

    d_11 = population_manager.resolve_denominator(
        year=2025, prov_codes=["11"], scope_mode="provinces"
    )
    assert d_11["available"] is True
    pop_11 = d_11["population"]
    assert pop_11 > 1000000

    # 2. Multi-province summation: sum(pop_selected_provinces), no duplicate counting, no 00 mixed in
    d_multi = population_manager.resolve_denominator(
        year=2025, prov_codes=["65", "11", "65", "00"], scope_mode="provinces"
    )
    assert d_multi["available"] is True
    assert d_multi["province_codes"] == ["65", "11"]
    assert d_multi["population"] == 835956 + pop_11

    # 3. Missing province in multi-province selection -> unavailable & reports missing_provinces
    d_missing = population_manager.resolve_denominator(
        year=2025, prov_codes=["65", "99"], scope_mode="provinces"
    )
    assert d_missing["available"] is False
    assert d_missing["population"] is None
    assert "99" in d_missing["missing_provinces"]

    # 4. Nationwide scope ("national") uses national total (65,826,149) once
    d_nat = population_manager.resolve_denominator(
        year=2025, scope_mode="national"
    )
    assert d_nat["available"] is True
    assert d_nat["population"] == 65826149

    # 5. Missing year (e.g. 2026 / พ.ศ. 2569) falls back to 2025 (พ.ศ. 2568) and marks is_fallback_year=True
    d_2026 = population_manager.resolve_denominator(
        year=2026, prov_codes=["65"], scope_mode="provinces"
    )
    assert d_2026["available"] is True
    assert d_2026["population"] == 835956
    assert d_2026["reference_year"] == 2025
    assert d_2026["population_year_be"] == 2568
    assert d_2026["is_fallback_year"] is True

    # 6. District scope without district denominator -> unavailable (never divides by province population)
    d_dist = population_manager.resolve_denominator(
        year=2025, prov_codes=["11"], district_code="1101", scope_mode="district"
    )
    assert d_dist["available"] is False
    assert d_dist["population"] is None


def test_multi_province_rate_formula_and_multi_year_separation():
    # Create dataset spanning 2 provinces (65 and 11) and 2 years (2024 and 2025)
    rows = []
    # 2025: 100 cases in prov 65, 200 cases in prov 11 -> total 300 cases
    for i in range(100):
        rows.append({
            "CID": f"65_2025_{i}",
            "รหัสกลุ่มโรค": "01",
            "datesick": "2025-04-10",
            "status": 8,
            "type": "IPD" if i < 20 else "OPD",
            "sex": "ชาย",
            "year": 25,
            "prov_code": "65",
            "รหัสอำเภอ(ที่อยู่ปัจจุบัน)": "01",
        })
    for i in range(200):
        rows.append({
            "CID": f"11_2025_{i}",
            "รหัสกลุ่มโรค": "01",
            "datesick": "2025-05-10",
            "status": 8,
            "type": "IPD" if i < 50 else "OPD",
            "sex": "หญิง",
            "year": 30,
            "prov_code": "11",
            "รหัสอำเภอ(ที่อยู่ปัจจุบัน)": "01",
        })
    # 2024: 50 cases in prov 65
    for i in range(50):
        rows.append({
            "CID": f"65_2024_{i}",
            "รหัสกลุ่มโรค": "01",
            "datesick": "2024-06-10",
            "status": 8,
            "type": "OPD",
            "sex": "ชาย",
            "year": 20,
            "prov_code": "65",
            "รหัสอำเภอ(ที่อยู่ปัจจุบัน)": "01",
        })

    processed = process_dds_dataframe(pd.DataFrame(rows))
    cleaned_df = processed["cleaned_df"]
    assert len(cleaned_df) == 350

    # Filter to year=2025, scope_mode="provinces", province_codes=["65", "11"]
    scope_2025 = apply_filters_and_resolve_scope(
        cleaned_df,
        {"scope_mode": "provinces", "province_codes": ["65", "11"], "year": 2025},
    )
    denom_2025 = scope_2025["denominator"]
    assert denom_2025["available"] is True
    pop_65 = population_manager.resolve_denominator(year=2025, prov_codes=["65"], scope_mode="provinces")["population"]
    pop_11 = population_manager.resolve_denominator(year=2025, prov_codes=["11"], scope_mode="provinces")["population"]
    assert denom_2025["population"] == pop_65 + pop_11

    expected_rate = round(300 / (pop_65 + pop_11) * 100000.0, 2)
    m_2025 = calculate_surveillance_measures(70, 230, 0, denom_2025["population"])
    assert m_2025["case_notification_rate"] == expected_rate

    # Multi-year (year=None) with scope_mode="provinces", province_codes=["65", "11"]
    # Uses the median reference year across detected years AND provides per-year rates in rates_by_year
    scope_multi_yr = apply_filters_and_resolve_scope(
        cleaned_df,
        {"scope_mode": "provinces", "province_codes": ["65", "11"], "year": None},
    )
    assert scope_multi_yr["denominator"]["available"] is True
    assert scope_multi_yr["denominator"]["is_median_year"] is True
    assert scope_multi_yr["denominator"]["reference_year"] in (2024, 2025)
    assert len(scope_multi_yr["rates_by_year"]) == 2
    by_yr = {r["year_ce"]: r for r in scope_multi_yr["rates_by_year"]}
    assert by_yr[2025]["numerator_cases_C"] == 300
    assert by_yr[2025]["case_rate_per_100k"] == expected_rate
    assert by_yr[2024]["numerator_cases_C"] == 50
    assert by_yr[2024]["case_rate_per_100k"] is not None


def test_csv_thai_encoding_leading_zeros_and_multi_file_dedup():
    # Build a CSV with Thai CP874 encoding, custom header names, quoted fields, and leading zeros ("10", "01")
    csv_text = (
        'เลขบัตรประชาชน,รหัสโรค,วันที่เริ่มป่วย,เวลาแก้ไข,สถานะรายงาน,ประเภทผู้ป่วย,เพศ,อายุ(ปี),รหัสจังหวัด,รหัสอำเภอ,หมายเหตุ\n'
        '"0123456789012","01","2025-03-10","2025-03-11 09:00:00","8","OPD","ชาย","25","11","01","ปกติ, มีคอมม่า"\n'
        '"0999999999999","01","2025-03-12","2025-03-12 10:00:00","8","IPD","หญิง","40","65","01","รายที่สอง"\n'
    )
    csv_bytes_cp874 = csv_text.encode("cp874")
    parsed_csv = read_dataframe_from_bytes(csv_bytes_cp874, "batch1_cp874.csv")
    df_csv = parsed_csv["df"]
    assert len(df_csv) == 2
    # Verify leading zeros preserved in raw string columns
    assert df_csv.iloc[0]["เลขบัตรประชาชน"] == "0123456789012"
    assert df_csv.iloc[0]["รหัสอำเภอ"] == "01"

    # Build a second file (XLSX with 2 sheets: "Summary_Ignore" and "Cases_2025")
    # Contains:
    # - Exact duplicate of row 2 ("0999999999999")
    # - Newer revision of row 1 ("0123456789012") upgrading OPD -> IPD on 2025-03-15
    # - A new 3rd patient ("0888888888888")
    xlsx_buf = io.BytesIO()
    with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
        pd.DataFrame([{"info": "do not import this sheet"}]).to_excel(
            writer, sheet_name="Summary_Ignore", index=False
        )
        pd.DataFrame([
            {
                "CID": "0999999999999",
                "รหัสกลุ่มโรค": "01",
                "datesick": "2025-03-12",
                "วันที่ Update": "2025-03-12 10:00:00",
                "status": "8",
                "type": "IPD",
                "sex": "หญิง",
                "year": "40",
                "prov_code": "65",
                "รหัสอำเภอ(ที่อยู่ปัจจุบัน)": "01",
            },
            {
                "CID": "0123456789012",
                "รหัสกลุ่มโรค": "01",
                "datesick": "2025-03-10",
                "วันที่ Update": "2025-03-15 16:30:00",
                "status": "8",
                "type": "IPD",
                "sex": "ชาย",
                "year": "25",
                "prov_code": "11",
                "รหัสอำเภอ(ที่อยู่ปัจจุบัน)": "01",
            },
            {
                "CID": "0888888888888",
                "รหัสกลุ่มโรค": "01",
                "datesick": "2025-03-18",
                "วันที่ Update": "2025-03-18 11:00:00",
                "status": "8",
                "type": "OPD",
                "sex": "ชาย",
                "year": "19",
                "prov_code": "65",
                "รหัสอำเภอ(ที่อยู่ปัจจุบัน)": "02",
            },
        ]).to_excel(writer, sheet_name="Cases_2025", index=False)

    parsed_xlsx = read_dataframe_from_bytes(
        xlsx_buf.getvalue(), "batch2_multi_sheet.xlsx", selected_sheet="Cases_2025"
    )
    assert "Summary_Ignore" in parsed_xlsx["sheets"]
    assert "Cases_2025" in parsed_xlsx["sheets"]
    assert parsed_xlsx["selected_sheet"] == "Cases_2025"
    assert len(parsed_xlsx["df"]) == 3

    std1 = standardize_single_file_dataframe(
        parsed_csv["df"],
        source_file="batch1_cp874.csv",
        source_sheet="CSV",
        import_seq_offset=0,
    )
    std2 = standardize_single_file_dataframe(
        parsed_xlsx["df"],
        source_file="batch2_multi_sheet.xlsx",
        source_sheet="Cases_2025",
        import_seq_offset=100,
    )

    combined_std = pd.concat([std1["standardized_df"], std2["standardized_df"]], ignore_index=True)
    merged = resolve_combined_standardized_dataframe(combined_std, total_rows_imported=5, trailing_blanks_removed=0)
    cleaned = merged["cleaned_df"]
    audit = merged["audit_trail"]

    # 2 rows in CSV + 3 rows in XLSX = 5 raw rows
    # 1 exact duplicate removed ("0999999999999")
    # 1 cross-file revision superseded ("0123456789012" OPD superseded by IPD)
    # Resulting eligible cases C = 3 (2 IPD, 1 OPD)
    assert audit["total_rows_imported"] == 5
    assert audit["exact_duplicates_removed"] == 1
    assert audit["cross_file_revisions_superseded"] == 1
    assert audit["eligible_episodes_C"] == 3
    assert audit["ipd_episodes_H"] == 2
    assert audit["opd_episodes_O"] == 1
    assert set(cleaned["source_file"].unique()) == {"batch1_cp874.csv", "batch2_multi_sheet.xlsx"}


def test_forecast_ols_capped_at_52_weeks_and_figure_7_render():
    dates_60 = [datetime.date(2024, 6, 2) + datetime.timedelta(days=7 * i) for i in range(60)]
    df_60 = pd.DataFrame([
        {
            "analysis_date": d,
            "epi_year": d.year,
            "epi_week": (i % 52) + 1,
            "clean_patient_type": "IPD" if i % 3 == 0 else "OPD",
        }
        for i, d in enumerate(dates_60)
        for _ in range(10)
    ])
    ws_60 = build_continuous_weekly_series(df_60)
    fc_60 = fit_ols_forecast(ws_60, horizon_weeks=4, exclude_last_n_weeks=1)
    assert fc_60["status"] == "success"
    assert fc_60["n_training_weeks"] == 52

    for lang in ("th", "en"):
        buf1 = render_figure_1_epicurve(df_60, export_fmt="png", lang=lang)
        w1, h1 = struct.unpack(">II", buf1.getvalue()[16:24])
        assert (w1, h1) == (3840, 2160)

        buf7 = render_figure_7_forecast(fc_60, export_fmt="png", lang=lang)
        w7, h7 = struct.unpack(">II", buf7.getvalue()[16:24])
        assert (w7, h7) == (3840, 2160)


def test_seasonal_comparison_and_prism_figure8_render():
    # Multi-year synthetic dataframe spanning 2021..2025
    rows = []
    for yr in range(2021, 2026):
        for wk in range(1, 53):
            n_cases = 10 + (yr - 2020) * 2 + (wk % 10)
            d = datetime.date(yr, 1, 1) + datetime.timedelta(days=7 * (wk - 1))
            for _ in range(n_cases):
                rows.append({
                    "analysis_date": d,
                    "epi_year": yr,
                    "epi_week": wk,
                    "clean_patient_type": "IPD" if wk % 3 == 0 else "OPD",
                    "residence_prov_code": "65",
                    "residence_district_code": "6501",
                })
    multi_df = pd.DataFrame(rows)
    seasonal = build_seasonal_comparison_series(multi_df, population=835956)
    assert seasonal["available"] is True
    assert seasonal["latest_year"] == 2025
    assert seasonal["prev_year"] == 2024
    assert len(seasonal["weeks"]) == 52
    assert seasonal["median_years_count"] in (4, 5)  # Historical prior years preceding latest 2025

    # Test Figure 8 4K render in TH and EN
    for lang in ("th", "en"):
        buf8 = render_figure_8_seasonal_comparison(seasonal, metric="cases", export_fmt="png", lang=lang)
        w8, h8 = struct.unpack(">II", buf8.getvalue()[16:24])
        assert (w8, h8) == (3840, 2160)

    # Test Figure 2 4K render with place_level='province' and place_metric='rate'
    buf2 = render_figure_2_district_bar(
        multi_df,
        place_level="province",
        place_metric="rate",
        export_fmt="png",
        lang="th",
    )
    w2, h2 = struct.unpack(">II", buf2.getvalue()[16:24])
    assert (w2, h2) == (3840, 2160)

