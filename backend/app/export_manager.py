import io
import zipfile
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import matplotlib.pyplot as plt
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from app.config import SESSIONS_DIR
from app.filters import apply_filters_and_resolve_scope
from app.table_generator import (
    generate_table_0_import_flow,
    generate_table_1_characteristics,
    generate_table_2_age_burden,
    generate_table_3_district_summary,
)
from app.forecast import fit_ols_forecast, build_continuous_weekly_series, build_seasonal_comparison_series
from app.studio_renderer import (
    render_figure_1_epicurve,
    render_figure_2_district_bar,
    render_figure_3_age_sex_nat,
    render_figure_4_age_rates,
    render_figure_5_hospitalization_prop,
    render_figure_6_nationality_comparison,
    render_figure_7_forecast,
    render_figure_8_seasonal_comparison,
    render_slide_readable_table,
)


def create_styled_excel_workbook(
    cleaned_df: pd.DataFrame,
    audit_trail: Dict[str, Any],
    is_synthetic: bool = False,
    filters: Optional[Dict[str, Any]] = None,
    raw_filters: Optional[Dict[str, Any]] = None,
) -> io.BytesIO:
    """Creates a multi-sheet analytical Excel workbook sharing active filters and denominators (Tables 0 to 4)."""
    eff_filters = raw_filters if raw_filters is not None else filters
    scope_ctx = apply_filters_and_resolve_scope(cleaned_df, eff_filters)
    work_df = scope_ctx["filtered_df"]
    f = scope_ctx["filters"]
    use_illness = f["address_type"] == "illness"

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    header_font = Font(name="Prompt", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="111C38", end_color="111C38", fill_type="solid")
    regular_font = Font(name="Sarabun", size=10)
    bold_font = Font(name="Sarabun", size=10, bold=True)
    center_align = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )

    # 1. Sheet: Table 0 - Audit & Eligibility Flow
    ws0 = wb.create_sheet("0_Audit_Flow")
    ws0.views.sheetView[0].showGridLines = True
    ws0.append(["ขั้นตอนการนำเข้า ตรวจสอบแหล่งที่มา และคัดกรองข้อมูล (Auditable Data Ingestion & Eligibility Flow)"])
    ws0.append([f"ขอบเขตข้อมูล (Active Scope): {scope_ctx['scope_name_th']} | ตัวหารประชากร: {scope_ctx['denominator']['reason_th']}"])
    ws0.append([f"ข้อมูลประมวลผล ณ วันที่ {datetime.now().strftime('%Y-%m-%d %H:%M')}"])

    t0_data = generate_table_0_import_flow(audit_trail)
    ws0.append(["ลำดับ", "ขั้นตอน (ไทย)", "Stage (English)", "จำนวนระเบียน (N)", "ร้อยละ (%)", "หมายเหตุระบาดวิทยา"])
    for cell in ws0[ws0.max_row]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    for r in t0_data:
        ws0.append([r["step"], r["stage_th"], r["stage_en"], r["count"], r["pct_th"], r["note_th"]])
        for cell in ws0[ws0.max_row]:
            cell.font = regular_font
            cell.border = thin_border

    src_summary = audit_trail.get("source_files_summary", [])
    if src_summary:
        ws0.append([])
        ws0.append(["สรุปแหล่งไฟล์ที่นำเข้า (Source Files Provenance Summary)"])
        ws0[ws0.max_row][0].font = bold_font
        ws0.append(["ชื่อไฟล์ (source_file)", "ชีต (source_sheet)", "แถวข้อมูล (Non-empty)", "ผู้ป่วยเข้าเกณฑ์สุทธิ (Eligible)", "ซ้ำซ้อน/ถูกตัดออก"])
        for cell in ws0[ws0.max_row]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
        for s_item in src_summary:
            ws0.append([
                s_item.get("source_file", ""),
                s_item.get("source_sheet", ""),
                s_item.get("non_empty_rows", 0),
                s_item.get("eligible_contributed", 0),
                s_item.get("duplicates_or_excluded", 0),
            ])
            for cell in ws0[ws0.max_row]:
                cell.font = regular_font
                cell.border = thin_border

    # 2. Sheet: Table 1 - Characteristics
    ws1 = wb.create_sheet("Table_1_Characteristics")
    ws1.views.sheetView[0].showGridLines = True
    ws1.append(["ตารางที่ 1 — ลักษณะทั่วไปของผู้ป่วยที่เข้าเกณฑ์การเฝ้าระวัง (Reported Case Characteristics)"])
    ws1.append(["ตัวชี้วัด / กลุ่มประชากร", "ภาพรวม (Overall)", "สัญชาติไทย (Thai)", "ไม่ใช่สัญชาติไทย (Non-Thai)", "ไม่ระบุ/รอการตรวจสอบ (Unknown)"])
    for cell in ws1[ws1.max_row]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    t1 = generate_table_1_characteristics(work_df)
    m = t1["metrics"]
    rows_to_add = [
        ("จำนวนผู้ป่วยทั้งหมด C (ราย)", [m["cases"][c] for c in t1["columns"]]),
        ("อายุเฉลี่ย มัธยฐาน (IQR)", [m["median_iqr_age"][c] for c in t1["columns"]]),
        ("เพศ: ชาย n (%)", [m["sex_male"][c] for c in t1["columns"]]),
        ("เพศ: หญิง n (%)", [m["sex_female"][c] for c in t1["columns"]]),
        ("เพศ: ไม่ระบุ n (%)", [m["sex_unknown"][c] for c in t1["columns"]]),
        ("ผู้ป่วยใน IPD (H) n (%)", [m["ipd_count"][c] for c in t1["columns"]]),
        ("ผู้ป่วยนอก OPD (O) n (%)", [m["opd_count"][c] for c in t1["columns"]]),
        ("ไม่ระบุประเภทผู้ป่วย (U) n (%)", [m["unknown_pt_count"][c] for c in t1["columns"]]),
        ("สัดส่วนการนอนโรงพยาบาล IPD / (IPD + OPD) (95% Wilson CI)", [m["hospitalization_prop"][c] for c in t1["columns"]]),
        ("ความสมบูรณ์ของประเภทผู้ป่วย (IPD + OPD) / C (%)", [m["patient_type_completeness"][c] for c in t1["columns"]]),
        ("ผู้เสียชีวิตที่บันทึกไว้ n (%)", [m["recorded_deaths"][c] for c in t1["columns"]]),
        ("ผู้มีผลลัพธ์ยืนยันรอดชีวิต/หาย n (%)", [m["known_alive"][c] for c in t1["columns"]]),
        ("ไม่ระบุผลลัพธ์การรักษา n (%)", [m["unknown_outcome"][c] for c in t1["columns"]]),
    ]
    for label, vals in rows_to_add:
        ws1.append([label] + vals)
        for cell in ws1[ws1.max_row]:
            cell.font = regular_font
            cell.border = thin_border

    ws1.append(["กลุ่มอายุ (Age Bands)"] + [""] * 4)
    ws1[ws1.max_row][0].font = bold_font
    for band, vals_dict in t1["age_bands"].items():
        ws1.append([f"  • กลุ่มอายุ {band} ปี"] + [vals_dict.get(c, "-") for c in t1["columns"]])
        for cell in ws1[ws1.max_row]:
            cell.font = regular_font
            cell.border = thin_border

    # 3. Sheet: Table 2 - Age Burden (with Numerator, Denominator, Population Year, Scope)
    ws2 = wb.create_sheet("Table_2_Age_Burden")
    ws2.views.sheetView[0].showGridLines = True
    ws2.append([f"ตารางที่ 2 — ภาระโรคและอัตราป่วยจำแนกตามกลุ่มอายุ ({scope_ctx['scope_name_th']})"])
    ws2.append([
        "กลุ่มอายุ", "ตัวเศษ ผู้ป่วย (C)", "ตัวหาร ประชากรฐาน", "ปีประชากร (พ.ศ./ค.ศ.)", "ขอบเขตพื้นที่",
        "อัตราป่วย/แสน", "95% Poisson CI", "IPD (H)", "OPD (O)", "ไม่ระบุ (U)",
        "สัดส่วน IPD (%)", "95% Wilson CI", "ความสมบูรณ์ (%)", "อัตรานอน รพ./แสน", "หมายเหตุตัวหาร"
    ])
    for cell in ws2[ws2.max_row]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    t2 = generate_table_2_age_burden(
        work_df,
        prov_code=scope_ctx["effective_prov_code"],
        prov_codes=scope_ctx["selected_province_codes"],
        scope_mode=scope_ctx["scope_mode"],
        scope_name_th=scope_ctx["scope_name_th"],
        scope_name_en=scope_ctx["scope_name_en"],
        year=scope_ctx["effective_year"],
        sex=f["sex"],
        nationality=f["nationality"],
        district_code=scope_ctx["effective_district_code"],
        patient_type=f["patient_type"],
        address_type=f["address_type"],
    )
    for r in t2:
        cr_ci = f"[{r['case_notification_rate_ci'][0]:.1f}, {r['case_notification_rate_ci'][1]:.1f}]" if r["case_notification_rate_ci"] else "-"
        hp_ci = f"[{r['hospitalization_prop_ci'][0]:.1f}, {r['hospitalization_prop_ci'][1]:.1f}]"
        pop_yr_str = (
            f"พ.ศ. {r['population_year_be']} (ค.ศ. {r['population_year_ce']})"
            + (" [Fallback 2568]" if r.get("is_fallback_year") else "")
            if r.get("population_year_ce")
            else "-"
        )
        ws2.append([
            r["age_band"],
            r["cases_C"],
            r["compatible_population"] if r["compatible_population"] is not None else "Unavailable",
            pop_yr_str,
            r.get("scope_name_th", ""),
            r["case_notification_rate"] if r["case_notification_rate"] is not None else "Unavailable",
            cr_ci,
            r["ipd_H"],
            r["opd_O"],
            r["unknown_U"],
            r["hospitalization_prop"],
            hp_ci,
            r["patient_type_completeness"],
            r["hosp_notification_rate"] if r["hosp_notification_rate"] is not None else "Unavailable",
            r.get("denominator_note_th", ""),
        ])
        for cell in ws2[ws2.max_row]:
            cell.font = regular_font
            cell.border = thin_border

    # If multiple years are present, append per-year rates table
    rates_by_year = scope_ctx.get("rates_by_year", [])
    if len(rates_by_year) > 1:
        ws2.append([])
        ws2.append(["อัตราป่วยแยกตามรายปี (Per-Year Rates Breakdown — ไม่รวมผู้ป่วยทุกปีหารประชากรปีเดียว)"])
        ws2[ws2.max_row][0].font = bold_font
        ws2.append(["ปีที่ป่วย (พ.ศ./ค.ศ.)", "ตัวเศษ ผู้ป่วย (C)", "ตัวหาร ประชากรฐาน", "ปีประชากร (พ.ศ./ค.ศ.)", "ขอบเขตพื้นที่", "อัตราป่วย/แสน", "อัตรานอน รพ./แสน", "สัดส่วน IPD (%)", "หมายเหตุตัวหาร"])
        for cell in ws2[ws2.max_row]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
        for yr_row in rates_by_year:
            ws2.append([
                f"พ.ศ. {yr_row['year_be']} ({yr_row['year_ce']})",
                yr_row["numerator_cases_C"],
                yr_row["population_denominator"] if yr_row["population_denominator"] is not None else "Unavailable",
                f"พ.ศ. {yr_row['population_year_be']} ({yr_row['population_year_ce']})" if yr_row.get("population_year_ce") else "-",
                yr_row["scope_name_th"],
                yr_row["case_rate_per_100k"] if yr_row["case_rate_per_100k"] is not None else "Unavailable",
                yr_row["hosp_rate_per_100k"] if yr_row["hosp_rate_per_100k"] is not None else "Unavailable",
                yr_row["hospitalization_prop"],
                yr_row.get("denominator_note_th", ""),
            ])
            for cell in ws2[ws2.max_row]:
                cell.font = regular_font
                cell.border = thin_border

    # 4. Sheet: Table 3 - Districts
    ws3 = wb.create_sheet("Table_3_Districts")
    ws3.views.sheetView[0].showGridLines = True
    ws3.append(["ตารางที่ 3 — ข้อมูลสรุปรายอำเภอ (District Summary Table)"])
    ws3.append([
        "รหัสจังหวัด", "จังหวัด", "รหัสอำเภอ (4 หลัก)", "ชื่ออำเภอ (ไทย)", "District (English)", "ตัวเศษ ผู้ป่วย C",
        "IPD (H)", "OPD (O)", "ไม่ระบุ (U)", "สัดส่วน IPD (%)", "ความสมบูรณ์ (%)",
        "ตัวหาร ประชากรอำเภอ", "อัตราป่วย/แสน", "สถานะการคำนวณอัตราประชากร"
    ])
    for cell in ws3[ws3.max_row]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    t3 = generate_table_3_district_summary(
        work_df,
        use_illness_district=use_illness,
        year=scope_ctx["effective_year"],
        sex=f["sex"],
        nationality=f["nationality"],
    )
    for r in t3:
        ws3.append([
            r.get("province_code", ""),
            r.get("province_name_th", ""),
            r["district_code"],
            r["district_name_th"],
            r["district_name_en"],
            r["cases_C"],
            r["ipd_H"],
            r["opd_O"],
            r["unknown_U"],
            r["hospitalization_prop"],
            r["patient_type_completeness"],
            r["district_population"] if r.get("district_population") is not None else "Unavailable",
            r["case_rate_per_100k"] if r["case_rate_per_100k"] is not None else "Unavailable",
            r["rate_status_note"],
        ])
        for cell in ws3[ws3.max_row]:
            cell.font = regular_font
            cell.border = thin_border

    # 5. Sheet: Table 4 - Weekly OLS Forecast (<=52 complete weeks)
    ws4 = wb.create_sheet("Table_4_Forecast")
    ws4.views.sheetView[0].showGridLines = True
    ws4.append(["ตารางที่ 4 — สถิติการเฝ้าระวังรายสัปดาห์และการพยากรณ์โรค (Weekly Surveillance & OLS Forecast <=52 Complete Weeks)"])
    weekly_s = build_continuous_weekly_series(work_df)
    fc = fit_ols_forecast(weekly_s, horizon_weeks=4)
    ws4.append([f"แบบจำลอง: {fc.get('formula', '')} | ช่วงฝึกสอน: {fc.get('training_window_note_th', '')} | Horizon: {fc.get('horizon_weeks', 4)} weeks"])
    ws4.append([
        "ลำดับ t", "ปีระบาด", "สัปดาห์ระบาด", "ช่วงวันที่ (Date Interval)", "ผู้ป่วยจริง (Observed)",
        "ค่าคาดหมาย/พยากรณ์ (Fitted)", "80% PI Lower", "80% PI Upper", "95% PI Lower", "95% PI Upper", "ประเภทข้อมูล"
    ])
    for cell in ws4[ws4.max_row]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    if fc.get("status") == "success":
        for r in fc.get("history", []) + fc.get("lag_excluded", []) + fc.get("forecasts", []):
            if r.get("is_forecast"):
                tag = "พยากรณ์ล่วงหน้า (Forecast)"
            elif r.get("is_lag_excluded"):
                tag = "สัปดาห์ล่าสุดที่ตัดออก (Lag Excluded)"
            else:
                tag = "ข้อมูลฝึกสอนสมบูรณ์ (Complete Training Week)"
            ws4.append([
                r["t"], r["epi_year"], r["epi_week"], r["label_th"],
                r["observed"] if r["observed"] is not None else "-",
                r["fitted_clipped"], r["pi_80_lower"], r["pi_80_upper"],
                r["pi_95_lower"], r["pi_95_upper"], tag
            ])
            for cell in ws4[ws4.max_row]:
                cell.font = regular_font
                cell.border = thin_border

    for sheet in wb.worksheets:
        for col in sheet.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            sheet.column_dimensions[col_letter].width = min(42, max(max_len + 3, 12))

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def create_presentation_pack_zip(
    cleaned_df: pd.DataFrame,
    audit_trail: Dict[str, Any],
    theme: str = "light",
    is_synthetic: bool = False,
    filters: Optional[Dict[str, Any]] = None,
    raw_filters: Optional[Dict[str, Any]] = None,
    lang: str = "th",
    include_vector: bool = False,
) -> io.BytesIO:
    """
    Generates a complete One-Click Presentation Pack ZIP containing:
    - 8 High-resolution 4K slides (exact 3840×2160 PNG) in requested language (th/en)
    - Vector SVG & PDF versions of slides (when include_vector=True)
    - Slide-readable summary table exports (4K PNG, and PDF if include_vector=True)
    - Aggregate XLSX workbook & CSV tables (Tables 0 to 4) sharing the same filters and denominators
    - Manifest and README.txt
    """
    eff_filters = raw_filters if raw_filters is not None else filters
    scope_ctx = apply_filters_and_resolve_scope(cleaned_df, eff_filters)
    work_df = scope_ctx["filtered_df"]
    f = scope_ctx["filters"]
    eff_lang = lang if lang in ("th", "en") else f.get("lang", "th")
    use_illness = f["address_type"] == "illness"
    scope_label = scope_ctx["scope_name_en"] if eff_lang == "en" else scope_ctx["scope_name_th"]

    t2_data = generate_table_2_age_burden(
        work_df,
        prov_code=scope_ctx["effective_prov_code"],
        prov_codes=scope_ctx["selected_province_codes"],
        scope_mode=scope_ctx["scope_mode"],
        scope_name_th=scope_ctx["scope_name_th"],
        scope_name_en=scope_ctx["scope_name_en"],
        year=scope_ctx["effective_year"],
        sex=f["sex"],
        nationality=f["nationality"],
        district_code=scope_ctx["effective_district_code"],
        patient_type=f["patient_type"],
        address_type=f["address_type"],
    )
    t3_data = generate_table_3_district_summary(
        work_df,
        use_illness_district=use_illness,
        year=scope_ctx["effective_year"],
        sex=f["sex"],
        nationality=f["nationality"],
    )
    weekly_s = build_continuous_weekly_series(work_df)
    fc_data = fit_ols_forecast(weekly_s, horizon_weeks=4)
    pop_by_yr = {
        int(ry["year_ce"]): int(ry["population_denominator"])
        for ry in scope_ctx.get("rates_by_year", [])
        if ry.get("population_denominator")
    }
    seasonal_data = build_seasonal_comparison_series(
        work_df,
        denominator_pop=scope_ctx["denominator"].get("population"),
        pop_by_year=pop_by_yr,
    )

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Render 8 Figures in PNG (1920x1080 Publication Quality), and optionally SVG / PDF
        fig_specs = [
            ("01_weekly_epidemic_curve", lambda fmt: render_figure_1_epicurve(work_df, theme=theme, export_fmt=fmt, lang=eff_lang)),
            ("02_district_distribution", lambda fmt: render_figure_2_district_bar(work_df, theme=theme, export_fmt=fmt, use_illness_district=use_illness, lang=eff_lang)),
            ("03_age_sex_profile", lambda fmt: render_figure_3_age_sex_nat(work_df, theme=theme, export_fmt=fmt, lang=eff_lang)),
            ("04_age_specific_rates", lambda fmt: render_figure_4_age_rates(t2_data, theme=theme, export_fmt=fmt, lang=eff_lang, scope_label=scope_label)),
            ("05_hospitalization_proportions", lambda fmt: render_figure_5_hospitalization_prop(t2_data, theme=theme, export_fmt=fmt, lang=eff_lang)),
            ("06_thai_vs_non_thai_comparison", lambda fmt: render_figure_6_nationality_comparison(work_df, theme=theme, export_fmt=fmt, lang=eff_lang)),
            ("07_weekly_forecast", lambda fmt: render_figure_7_forecast(fc_data, theme=theme, export_fmt=fmt, lang=eff_lang)),
            ("08_seasonal_2yr_vs_5yr_median", lambda fmt: render_figure_8_seasonal_comparison(seasonal_data, theme=theme, export_fmt=fmt, lang=eff_lang)),
        ]

        for base_name, renderer in fig_specs:
            png_buf = renderer("png")
            zf.writestr(f"figures_png/{base_name}.png", png_buf.getvalue())
            del png_buf
            if include_vector:
                zf.writestr(f"figures_vector_svg/{base_name}.svg", renderer("svg").getvalue())
                zf.writestr(f"figures_vector_pdf/{base_name}.pdf", renderer("pdf").getvalue())
            plt.close("all")

        # 2. Slide-Readable Table Exports (PNG & optional PDF)
        t2_headers = (
            ["Age Group", "Cases (C)", "Population", "Pop Year", "Rate/100k", "IPD", "OPD", "Unk", "Hosp %"]
            if eff_lang == "en"
            else ["กลุ่มอายุ", "ตัวเศษ (C)", "ตัวหารประชากร", "ปีประชากร", "อัตราป่วย/แสน", "IPD", "OPD", "ไม่ระบุ", "สัดส่วน IPD %"]
        )
        t2_rows = [
            [
                r["age_band"],
                f"{r['cases_C']:,}",
                f"{r['compatible_population']:,}" if r["compatible_population"] else "Unavailable",
                str(r["population_year_be"] if eff_lang == "th" else r["population_year_ce"]) if r.get("population_year_ce") else "-",
                f"{r['case_notification_rate']:.2f}" if r["case_notification_rate"] is not None else "Unavailable",
                f"{r['ipd_H']:,}",
                f"{r['opd_O']:,}",
                f"{r['unknown_U']:,}",
                f"{r['hospitalization_prop']:.1f}%",
            ]
            for r in t2_data
        ]
        slide_t2_png = render_slide_readable_table(
            title="Table 2 — Age-Specific Burden Summary" if eff_lang == "en" else "ตารางที่ 2 — สรุปภาระโรคจำแนกตามกลุ่มอายุ",
            subtitle=scope_label,
            headers=t2_headers,
            rows=t2_rows,
            footnote=scope_ctx["denominator"]["reason_en" if eff_lang == "en" else "reason_th"],
            theme=theme,
            export_fmt="png",
            lang=eff_lang,
        )
        zf.writestr("slide_tables/Table_2_Age_Burden_Slide.png", slide_t2_png.getvalue())
        plt.close("all")

        if include_vector:
            slide_t2_pdf = render_slide_readable_table(
                title="Table 2 — Age-Specific Burden Summary" if eff_lang == "en" else "ตารางที่ 2 — สรุปภาระโรคจำแนกตามกลุ่มอายุ",
                subtitle=scope_label,
                headers=t2_headers,
                rows=t2_rows,
                footnote=scope_ctx["denominator"]["reason_en" if eff_lang == "en" else "reason_th"],
                theme=theme,
                export_fmt="pdf",
                lang=eff_lang,
            )
            zf.writestr("slide_tables/Table_2_Age_Burden_Slide.pdf", slide_t2_pdf.getvalue())
            plt.close("all")

        # 3. Styled Excel Workbook (reuses disk cache when available for extreme speed)
        excel_disk = SESSIONS_DIR / "default_active_session" / "DDS_Surveillance_Report.xlsx"
        if excel_disk.exists() and (raw_filters is None or raw_filters == filters):
            try:
                excel_bytes = excel_disk.read_bytes()
            except Exception:
                excel_bytes = create_styled_excel_workbook(cleaned_df, audit_trail, is_synthetic=is_synthetic, filters=eff_filters).getvalue()
        else:
            excel_bytes = create_styled_excel_workbook(cleaned_df, audit_trail, is_synthetic=is_synthetic, filters=eff_filters).getvalue()
        zf.writestr("data_tables/DDS_Surveillance_Summary_Workbook.xlsx", excel_bytes)

        # 4. Aggregate CSV Tables (Tables 0 to 4)
        df_t0 = pd.DataFrame(generate_table_0_import_flow(audit_trail))
        zf.writestr("data_tables/csv/Table_0_Import_Eligibility_Flow.csv", df_t0.to_csv(index=False, encoding="utf-8-sig"))

        df_t2 = pd.DataFrame(t2_data)
        zf.writestr("data_tables/csv/Table_2_Age_Burden.csv", df_t2.to_csv(index=False, encoding="utf-8-sig"))

        df_t3 = pd.DataFrame(t3_data)
        zf.writestr("data_tables/csv/Table_3_Districts_Summary.csv", df_t3.to_csv(index=False, encoding="utf-8-sig"))

        if fc_data.get("status") == "success":
            df_t4 = pd.DataFrame(fc_data.get("history", []) + fc_data.get("lag_excluded", []) + fc_data.get("forecasts", []))
            zf.writestr("data_tables/csv/Table_4_Forecast.csv", df_t4.to_csv(index=False, encoding="utf-8-sig"))

        # 5. Manifest & Settings JSON
        pack_manifest = {
            "application": "DDS One-Click Surveillance System",
            "version": "2.1.0",
            "generation_timestamp": datetime.now().isoformat(),
            "is_synthetic_demonstration": is_synthetic,
            "theme_mode": theme,
            "language": eff_lang,
            "aspect_ratio": "16:9 (1920x1080 Publication Quality)",
            "active_filters": f,
            "active_scope": {
                "scope_mode": scope_ctx["scope_mode"],
                "selected_province_codes": scope_ctx["selected_province_codes"],
                "scope_name_th": scope_ctx["scope_name_th"],
                "scope_name_en": scope_ctx["scope_name_en"],
                "effective_year": scope_ctx["effective_year"],
                "effective_prov_code": scope_ctx["effective_prov_code"],
                "effective_district_code": scope_ctx["effective_district_code"],
                "denominator": scope_ctx["denominator"],
            },
            "audit_trail": audit_trail,
        }
        zf.writestr("manifest_settings.json", json.dumps(pack_manifest, ensure_ascii=False, indent=2, default=str))

        readme_text = (
            "========================================================================\r\n"
            "DDS ONE-CLICK SURVEILLANCE SYSTEM - PRESENTATION PACK (PUBLICATION QUALITY)\r\n"
            "กลุ่มงานระบาดวิทยา สำนักงานสาธารณสุขจังหวัดพิษณุโลก\r\n"
            "========================================================================\r\n\r\n"
            "โครงสร้างไฟล์ในแพ็กเกจนำเสนอ:\r\n"
            "1. figures_png/    : แผนภูมิคุณภาพตีพิมพ์ 1920x1080 (16:9 Full HD) ครบ 8 ภาพ\r\n"
            "   (01 Epicurve, 02 Districts, 03 Age-Sex, 04 Rates, 05 Hospitalization,\r\n"
            "    06 Thai vs Non-Thai, 07 Weekly Forecast, 08 Seasonal Comparison)\r\n"
            "2. slide_tables/   : ตารางนำเสนอความละเอียดสูง Table 2 สำหรับวางบนสไลด์\r\n"
            "3. data_tables/    : สมุดงาน DDS_Surveillance_Summary_Workbook.xlsx และตาราง CSV\r\n"
            "4. manifest_settings.json : ข้อมูล Audit trail และพารามิเตอร์ตัวกรองทางระบาดวิทยา\r\n"
        )
        zf.writestr("README.txt", readme_text)

    zip_buf.seek(0)
    return zip_buf


def persist_session_outputs_to_disk(
    session_id: Optional[str] = None,
    cleaned_df: Optional[pd.DataFrame] = None,
    audit_trail: Optional[Dict[str, Any]] = None,
    filters: Optional[Dict[str, Any]] = None,
    is_synthetic: bool = False,
    *,
    session_dir: Optional[Path] = None,
    df: Optional[pd.DataFrame] = None,
    raw_filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Saves large analytical results, table snapshots, and Excel report to project files under
    backend/data_sessions/<session_id>/ so the application reads/serves them from disk.
    """
    target_dir = session_dir if session_dir is not None else (SESSIONS_DIR / (session_id or "default_active_session"))
    target_dir.mkdir(parents=True, exist_ok=True)
    target_df = df if df is not None else cleaned_df
    if target_df is None:
        return {}
    eff_filters = raw_filters if raw_filters is not None else filters
    audit_trail = audit_trail or {}

    # Save anonymized cleaned dataframe on disk (preserving source_file, source_sheet, source_row)
    cleaned_csv_path = target_dir / "cleaned_episodes.csv"
    target_df.to_csv(cleaned_csv_path, index=False, encoding="utf-8-sig")

    scope_ctx = apply_filters_and_resolve_scope(target_df, eff_filters)
    work_df = scope_ctx["filtered_df"]
    f = scope_ctx["filters"]
    use_illness = f["address_type"] == "illness"

    t0 = generate_table_0_import_flow(audit_trail)
    t1 = generate_table_1_characteristics(work_df)
    t2 = generate_table_2_age_burden(
        work_df,
        prov_code=scope_ctx["effective_prov_code"],
        prov_codes=scope_ctx["selected_province_codes"],
        scope_mode=scope_ctx["scope_mode"],
        scope_name_th=scope_ctx["scope_name_th"],
        scope_name_en=scope_ctx["scope_name_en"],
        year=scope_ctx["effective_year"],
        sex=f["sex"],
        nationality=f["nationality"],
        district_code=scope_ctx["effective_district_code"],
        patient_type=f["patient_type"],
        address_type=f["address_type"],
    )
    t3 = generate_table_3_district_summary(
        work_df,
        use_illness_district=use_illness,
        year=scope_ctx["effective_year"],
        sex=f["sex"],
        nationality=f["nationality"],
    )
    t4 = fit_ols_forecast(build_continuous_weekly_series(work_df), horizon_weeks=4)

    snapshot = {
        "updated_at": datetime.now().isoformat(),
        "is_synthetic": is_synthetic,
        "audit_trail": audit_trail,
        "filters": f,
        "scope": {
            "scope_mode": scope_ctx["scope_mode"],
            "selected_province_codes": scope_ctx["selected_province_codes"],
            "scope_name_th": scope_ctx["scope_name_th"],
            "scope_name_en": scope_ctx["scope_name_en"],
            "effective_year": scope_ctx["effective_year"],
            "effective_prov_code": scope_ctx["effective_prov_code"],
            "effective_district_code": scope_ctx["effective_district_code"],
            "detected_provinces": scope_ctx["detected_provinces"],
            "detected_years": scope_ctx["detected_years"],
            "denominator": scope_ctx["denominator"],
            "rates_by_year": scope_ctx["rates_by_year"],
            "comparator": scope_ctx["comparator"],
        },
        "table0": t0,
        "table1": t1,
        "table2": t2,
        "table3": t3,
        "table4": t4,
    }

    snapshot_path = target_dir / "analytical_snapshot.json"
    with open(snapshot_path, "w", encoding="utf-8") as fp:
        json.dump(snapshot, fp, ensure_ascii=False, indent=2)

    xlsx_path = target_dir / "DDS_Surveillance_Report.xlsx"
    xlsx_buf = create_styled_excel_workbook(target_df, audit_trail, is_synthetic=is_synthetic, filters=eff_filters)
    xlsx_path.write_bytes(xlsx_buf.getvalue())

    return {
        "cleaned_episodes_csv": str(cleaned_csv_path),
        "analytical_snapshot_json": str(snapshot_path),
        "excel_report": str(xlsx_path),
    }
