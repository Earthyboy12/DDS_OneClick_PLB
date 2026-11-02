from typing import Dict, Any, List, Optional, Union
import pandas as pd

from app.measures import (
    calculate_age_summary,
    wilson_score_interval,
    exact_poisson_rate_interval,
    STANDARD_AGE_BANDS,
)
from app.population import population_manager, normalize_province_codes_input
from app.district_crosswalk import get_district_info
from app.reference_db import get_province_by_code, get_districts_list


def generate_table_0_import_flow(audit_trail: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Table 0: Auditable Data Ingestion, Cross-File Deduplication & Eligibility Flow."""
    total_imported = audit_trail.get("total_rows_imported", 0)
    trailing_blanks = audit_trail.get("trailing_blanks_removed", 0)
    non_empty = audit_trail.get("non_empty_records", 0)
    exact_dups = audit_trail.get("exact_duplicates_removed", 0)
    cross_revs = audit_trail.get("cross_file_revisions_superseded", 0)
    superseded = audit_trail.get("superseded_revisions_removed", exact_dups + cross_revs)
    authoritative = audit_trail.get("authoritative_episodes_total", 0)
    cancelled = audit_trail.get("cancelled_episodes_excluded", 0)
    pending = audit_trail.get("pending_or_other_excluded", 0)
    missing_status = audit_trail.get("missing_status_excluded", 0)
    eligible_C = audit_trail.get("eligible_episodes_C", 0)
    ipd_H = audit_trail.get("ipd_episodes_H", 0)
    opd_O = audit_trail.get("opd_episodes_O", 0)
    unknown_U = audit_trail.get("unknown_patient_type_U", 0)
    src_summary = audit_trail.get("source_files_summary", [])
    src_count = len(src_summary)

    rows = [
        {
            "step": 1,
            "stage_th": "แถวทั้งหมดที่อ่านจากไฟล์นำเข้า (Raw Imported Rows)",
            "stage_en": "Total imported raw rows",
            "count": total_imported,
            "pct_th": "100.0%",
            "note_th": f"จากไฟล์ข้อมูลผู้ป่วย {src_count} รายการ (บันทึก source_file, source_sheet, source_row ทุกแถว)" if src_count else "รวมแถวว่างท้ายตารางและประวัติการแก้ไข",
            "note_en": f"Across {src_count} source file/sheet(s) with full provenance" if src_count else "Including trailing empty rows and revision history",
        },
        {
            "step": 2,
            "stage_th": "แถวว่างท้ายตารางที่ตัดออก (Trailing Blank Rows Removed)",
            "stage_en": "Trailing blank rows stripped",
            "count": trailing_blanks,
            "pct_th": f"{(trailing_blanks/total_imported*100.0):.1f}%" if total_imported > 0 else "0.0%",
            "note_th": "แถวว่างเปล่าสมบูรณ์ที่ไม่มีข้อมูลผู้ป่วย",
            "note_en": "Completely blank rows without patient data",
        },
        {
            "step": 3,
            "stage_th": "ระเบียนที่มีข้อมูลจริง (Non-empty Records)",
            "stage_en": "Non-empty imported records",
            "count": non_empty,
            "pct_th": f"{(non_empty/total_imported*100.0):.1f}%" if total_imported > 0 else "0.0%",
            "note_th": "ระเบียนที่มีข้อมูลอย่างน้อย 1 ฟิลด์",
            "note_en": "Records with at least one data field",
        },
        {
            "step": 4,
            "stage_th": "ระเบียนซ้ำทุกประการ/นำไฟล์เดิมเข้าซ้ำ และประวัติแก้ไขที่ถูกแทนที่ (Duplicates & Superseded Revisions)",
            "stage_en": "Exact duplicates & cross-file superseded revisions removed",
            "count": superseded,
            "pct_th": f"{(superseded/non_empty*100.0):.1f}%" if non_empty > 0 else "0.0%",
            "note_th": f"ข้อมูลซ้ำทุกประการ: {exact_dups:,} แถว | ประวัติแก้ไขที่ถูกแทนที่ข้าม/ภายในไฟล์: {cross_revs:,} แถว",
            "note_en": f"Exact duplicates: {exact_dups:,} | Cross/intra-file superseded revisions: {cross_revs:,}",
        },
        {
            "step": 5,
            "stage_th": "ระเบียนหลักที่เป็นตัวแทนเหตุการณ์ป่วยล่าสุด (Authoritative Episodes)",
            "stage_en": "Authoritative episodes total",
            "count": authoritative,
            "pct_th": f"{(authoritative/non_empty*100.0):.1f}%" if non_empty > 0 else "0.0%",
            "note_th": "ก่อนกรองสถานะการอนุมัติรายงาน",
            "note_en": "Before filtering approval status",
        },
        {
            "step": 6,
            "stage_th": "รายงานที่ถูกยกเลิก (Cancelled Reports Excluded)",
            "stage_en": "Cancelled reports excluded",
            "count": cancelled,
            "pct_th": f"{(cancelled/authoritative*100.0):.1f}%" if authoritative > 0 else "0.0%",
            "note_th": "รหัสสถานะ 6 (ยกเลิก/ซ้ำซ้อน) ไม่สามารถฟื้นคืนได้แม้ไฟล์ก่อนหน้าเคยอนุมัติ",
            "note_en": "Status code 6 (cancelled/duplicate) cannot be resurrected by earlier approved versions",
        },
        {
            "step": 7,
            "stage_th": "รายงานรอแก้ไข/ไม่ระบุสถานะ (Pending / Missing Excluded)",
            "stage_en": "Pending or unapproved status excluded",
            "count": pending + missing_status,
            "pct_th": f"{((pending + missing_status)/authoritative*100.0):.1f}%" if authoritative > 0 else "0.0%",
            "note_th": "รหัสสถานะ 2 (รอการแก้ไข) และค่าว่าง",
            "note_en": "Status code 2 (pending correction) and missing status",
        },
        {
            "step": 8,
            "stage_th": "ผู้ป่วยเฝ้าระวังที่เข้าเกณฑ์การวิเคราะห์สุทธิ (Eligible Episodes C)",
            "stage_en": "Final eligible surveillance episodes (C)",
            "count": eligible_C,
            "pct_th": f"{(eligible_C/authoritative*100.0):.1f}%" if authoritative > 0 else "0.0%",
            "note_th": f"IPD (H): {ipd_H:,} | OPD (O): {opd_O:,} | ไม่ระบุประเภท (U): {unknown_U:,}",
            "note_en": f"IPD (H): {ipd_H:,} | OPD (O): {opd_O:,} | Unknown (U): {unknown_U:,}",
        },
    ]
    return rows


def generate_table_1_characteristics(df: pd.DataFrame, **_kwargs) -> Dict[str, Any]:
    """
    Table 1 — Reported case characteristics.
    Columns: Overall, Thai, Non-Thai, Unknown/Unresolved Nationality.
    Missing death/type values are never treated as alive/OPD.
    """
    groups = {
        "Overall": df,
        "Thai": df[df["nationality_group"] == "Thai"] if "nationality_group" in df.columns else pd.DataFrame(),
        "Non-Thai": df[df["nationality_group"] == "Non-Thai"] if "nationality_group" in df.columns else pd.DataFrame(),
        "Unknown": df[df["nationality_group"] == "Unknown"] if "nationality_group" in df.columns else pd.DataFrame(),
    }

    cols_order = ["Overall", "Thai", "Non-Thai", "Unknown"]
    metrics: Dict[str, Dict[str, Any]] = {
        "cases": {},
        "median_iqr_age": {},
        "sex_male": {},
        "sex_female": {},
        "sex_unknown": {},
        "ipd_count": {},
        "opd_count": {},
        "unknown_pt_count": {},
        "hospitalization_prop": {},
        "patient_type_completeness": {},
        "recorded_deaths": {},
        "known_alive": {},
        "unknown_outcome": {},
    }

    age_band_rows: Dict[str, Dict[str, Any]] = {band: {} for band in STANDARD_AGE_BANDS + ["Unknown"]}

    for grp_key in cols_order:
        sub_df = groups[grp_key]
        n_c = len(sub_df)
        metrics["cases"][grp_key] = n_c

        if n_c > 0 and "clean_age_years" in sub_df.columns:
            age_sum = calculate_age_summary(sub_df["clean_age_years"])
            if age_sum["median"] is not None:
                metrics["median_iqr_age"][grp_key] = f"{age_sum['median']} ({age_sum['q25']} - {age_sum['q75']})"
            else:
                metrics["median_iqr_age"][grp_key] = "-"
        else:
            metrics["median_iqr_age"][grp_key] = "-"

        if n_c > 0 and "clean_sex" in sub_df.columns:
            m_c = int((sub_df["clean_sex"] == "ชาย").sum())
            f_c = int((sub_df["clean_sex"] == "หญิง").sum())
            u_c = n_c - m_c - f_c
            metrics["sex_male"][grp_key] = f"{m_c:,} ({m_c/n_c*100.0:.1f}%)"
            metrics["sex_female"][grp_key] = f"{f_c:,} ({f_c/n_c*100.0:.1f}%)"
            metrics["sex_unknown"][grp_key] = f"{u_c:,} ({u_c/n_c*100.0:.1f}%)"
        else:
            metrics["sex_male"][grp_key] = "-"
            metrics["sex_female"][grp_key] = "-"
            metrics["sex_unknown"][grp_key] = "-"

        if n_c > 0 and "clean_patient_type" in sub_df.columns:
            h = int((sub_df["clean_patient_type"] == "IPD").sum())
            o = int((sub_df["clean_patient_type"] == "OPD").sum())
            u = int((sub_df["clean_patient_type"] == "Unknown").sum())
            known = h + o

            metrics["ipd_count"][grp_key] = f"{h:,} ({h/n_c*100.0:.1f}%)"
            metrics["opd_count"][grp_key] = f"{o:,} ({o/n_c*100.0:.1f}%)"
            metrics["unknown_pt_count"][grp_key] = f"{u:,} ({u/n_c*100.0:.1f}%)"

            if known > 0:
                hp, l, u_ci = wilson_score_interval(h, known)
                metrics["hospitalization_prop"][grp_key] = f"{hp:.1f}% ({l:.1f}% - {u_ci:.1f}%)"
            else:
                metrics["hospitalization_prop"][grp_key] = "0.0%"

            completeness = (known / n_c * 100.0) if n_c > 0 else 0.0
            metrics["patient_type_completeness"][grp_key] = f"{completeness:.1f}%"
        else:
            metrics["ipd_count"][grp_key] = "-"
            metrics["opd_count"][grp_key] = "-"
            metrics["unknown_pt_count"][grp_key] = "-"
            metrics["hospitalization_prop"][grp_key] = "-"
            metrics["patient_type_completeness"][grp_key] = "-"

        if n_c > 0:
            if "clean_outcome_status" in sub_df.columns:
                deaths = int((sub_df["clean_outcome_status"] == "Dead").sum())
                alive = int((sub_df["clean_outcome_status"] == "Alive").sum())
                unk_out = int((sub_df["clean_outcome_status"] == "Unknown").sum())
            elif "parsed_death_date" in sub_df.columns:
                deaths = int(sub_df["parsed_death_date"].notna().sum())
                alive = 0
                unk_out = n_c - deaths
            else:
                deaths, alive, unk_out = 0, 0, n_c
            metrics["recorded_deaths"][grp_key] = f"{deaths:,} ({deaths/n_c*100.0:.2f}%)"
            metrics["known_alive"][grp_key] = f"{alive:,} ({alive/n_c*100.0:.1f}%)"
            metrics["unknown_outcome"][grp_key] = f"{unk_out:,} ({unk_out/n_c*100.0:.1f}%)"
        else:
            metrics["recorded_deaths"][grp_key] = "0 (0.00%)"
            metrics["known_alive"][grp_key] = "0 (0.0%)"
            metrics["unknown_outcome"][grp_key] = "0 (0.0%)"

        for b in STANDARD_AGE_BANDS + ["Unknown"]:
            if n_c > 0 and "age_band" in sub_df.columns:
                bc = int((sub_df["age_band"] == b).sum())
                age_band_rows[b][grp_key] = f"{bc:,} ({bc/n_c*100.0:.1f}%)"
            else:
                age_band_rows[b][grp_key] = "0 (0.0%)"

    return {
        "columns": cols_order,
        "metrics": metrics,
        "age_bands": age_band_rows,
        "notes_th": (
            "สัดส่วนการนอนโรงพยาบาล (Hospitalization %) คำนวณจาก IPD / (IPD + OPD) × 100 "
            "โดยตัดกลุ่มไม่ระบุประเภทผู้ป่วยออกและแสดงค่าความสมบูรณ์ (IPD + OPD) / C × 100 กำกับ | "
            "ค่าว่างของวันเสียชีวิต/สภาพผู้ป่วยจัดเป็นไม่ระบุผลลัพธ์ (ไม่ถือว่ารอดชีวิตโดยอัตโนมัติ)"
        ),
        "notes_en": (
            "Hospitalization proportion = IPD / (IPD + OPD) * 100, excluding unknown patient types and disclosing completeness. "
            "Missing death/status values are classified as unknown outcome, not assumed alive."
        ),
    }


def generate_table_2_age_burden(
    df: pd.DataFrame,
    prov_code: Optional[Union[str, List[str]]] = None,
    year: Optional[int] = None,
    sex: Optional[str] = None,
    nationality: Optional[str] = None,
    district_code: Optional[str] = None,
    patient_type: Optional[str] = None,
    address_type: str = "residence",
    prov_codes: Optional[List[str]] = None,
    scope_mode: Optional[str] = None,
    scope_name_th: Optional[str] = None,
    scope_name_en: Optional[str] = None,
    **_kwargs,
) -> List[Dict[str, Any]]:
    """
    Table 2 — Age-specific burden.
    Supports single province, multiple provinces (sum(cases)/sum(pop)*100000), nationwide ('00' once),
    and district scope. Displays numerator, denominator, population year (with 2025 fallback if needed),
    and geography scope in every row.
    """
    norm_provs = normalize_province_codes_input(prov_code=prov_code, prov_codes=prov_codes)
    eff_scope_mode = scope_mode
    if not eff_scope_mode:
        if district_code:
            eff_scope_mode = "district"
        elif norm_provs == ["00"]:
            eff_scope_mode = "national"
        elif len(norm_provs) >= 1:
            eff_scope_mode = "provinces"
        else:
            eff_scope_mode = "all_imported"

    eff_year = year
    detected_years: List[int] = []
    if not df.empty:
        yr_col = "onset_year" if "onset_year" in df.columns else "epi_year"
        if yr_col in df.columns:
            detected_years = sorted([int(y) for y in df[yr_col].dropna().unique() if pd.notna(y)])
            if eff_year is None and len(detected_years) == 1:
                eff_year = detected_years[0]

    # Resolve target province codes if not explicitly specified (e.g. in 'all_imported' mode)
    prov_col = "illness_prov_code" if address_type == "illness" else "residence_prov_code"
    valid_ref_provs: List[str] = []
    if not df.empty and prov_col in df.columns:
        det_provs = sorted([str(p) for p in df[prov_col].dropna().unique() if str(p) not in ("", "None")])
        valid_ref_provs = [p for p in det_provs if get_province_by_code(p) is not None]

    if eff_scope_mode == "national":
        denom_provs = ["00"]
    elif eff_scope_mode == "provinces" and norm_provs:
        denom_provs = norm_provs
    else:
        denom_provs = ["00"] if len(valid_ref_provs) >= 70 else (valid_ref_provs if valid_ref_provs else ["00"])

    rows = []
    for band in STANDARD_AGE_BANDS + ["Unknown"]:
        sub_df = df[df["age_band"] == band] if ("age_band" in df.columns and not df.empty) else pd.DataFrame()
        c = len(sub_df)
        h = int((sub_df["clean_patient_type"] == "IPD").sum()) if c > 0 else 0
        o = int((sub_df["clean_patient_type"] == "OPD").sum()) if c > 0 else 0
        u = int((sub_df["clean_patient_type"] == "Unknown").sum()) if c > 0 else 0
        known = h + o

        if patient_type and str(patient_type).lower() not in ("", "all", "none"):
            denom = {
                "available": False,
                "population": None,
                "reference_year": eff_year,
                "population_year_be": (eff_year + 543) if eff_year else None,
                "is_fallback_year": False,
                "reason_th": "กรองเฉพาะประเภทผู้ป่วยบางส่วน จึงไม่คำนวณอัตราต่อประชากร",
                "reason_en": "Filtered by patient type; population rates unavailable",
            }
        else:
            denom = population_manager.resolve_denominator(
                year=eff_year,
                prov_code=denom_provs,
                prov_codes=denom_provs,
                district_code=district_code if eff_scope_mode == "district" else None,
                sex=sex,
                nationality=nationality,
                age_band=band,
                scope_mode=eff_scope_mode,
                detected_years=detected_years,
            )

        pop = denom["population"] if denom.get("available") else None

        if known > 0:
            hp, hp_l, hp_u = wilson_score_interval(h, known)
        else:
            hp, hp_l, hp_u = 0.0, 0.0, 0.0

        if pop and pop > 0:
            case_rate, cr_l, cr_u = exact_poisson_rate_interval(c, pop)
            hosp_rate, hr_l, hr_u = exact_poisson_rate_interval(h, pop)
        else:
            case_rate, cr_l, cr_u = None, None, None
            hosp_rate, hr_l, hr_u = None, None, None

        completeness = round(known / c * 100.0, 1) if c > 0 else 0.0

        rows.append({
            "age_band": band,
            "cases_C": c,
            "numerator_cases_C": c,
            "numerator_ipd_H": h,
            "compatible_population": int(pop) if pop else None,
            "population_year_ce": denom.get("reference_year"),
            "population_year_be": denom.get("population_year_be"),
            "is_fallback_year": denom.get("is_fallback_year", False),
            "scope_name_th": scope_name_th or denom.get("province_name_th") or "ข้อมูลที่นำเข้า",
            "scope_name_en": scope_name_en or denom.get("province_name_en") or "Imported Scope",
            "case_notification_rate": case_rate,
            "case_notification_rate_ci": [cr_l, cr_u] if case_rate is not None else None,
            "ipd_H": h,
            "opd_O": o,
            "unknown_U": u,
            "hospitalization_prop": hp,
            "hospitalization_prop_ci": [hp_l, hp_u],
            "patient_type_completeness": completeness,
            "hosp_notification_rate": hosp_rate,
            "hosp_notification_rate_ci": [hr_l, hr_u] if hosp_rate is not None else None,
            "denominator_note_th": denom.get("reason_th", ""),
            "denominator_note_en": denom.get("reason_en", ""),
        })

    return rows


def generate_table_3_district_summary(
    df: pd.DataFrame,
    use_illness_district: bool = False,
    year: Optional[int] = None,
    sex: Optional[str] = None,
    nationality: Optional[str] = None,
    **_kwargs,
) -> List[Dict[str, Any]]:
    """
    Table 3 — District summary.
    Province/district name and code from dds_reference.sqlite, cases, IPD, OPD,
    hospitalization proportion, completeness, and population-based rates ONLY when valid
    district denominators exist (never divides district cases by provincial population).
    """
    p_code_col = "illness_prov_code" if use_illness_district else "residence_prov_code"
    d_code_col = "illness_district_code" if use_illness_district else "residence_district_code"
    d_name_th_col = "illness_district_name_th" if use_illness_district else "residence_district_name_th"
    d_name_en_col = "illness_district_name_en" if use_illness_district else "residence_district_name_en"

    rows = []
    if df.empty or d_code_col not in df.columns:
        return rows

    eff_year = year
    if eff_year is None:
        yr_col = "onset_year" if "onset_year" in df.columns else "epi_year"
        if yr_col in df.columns:
            yrs = sorted([int(y) for y in df[yr_col].dropna().unique() if pd.notna(y)])
            if len(yrs) == 1:
                eff_year = yrs[0]

    grouped = df.groupby([d_code_col, d_name_th_col, d_name_en_col], dropna=False)

    for (code, name_th, name_en), sub_df in grouped:
        c = len(sub_df)
        h = int((sub_df["clean_patient_type"] == "IPD").sum())
        o = int((sub_df["clean_patient_type"] == "OPD").sum())
        u = int((sub_df["clean_patient_type"] == "Unknown").sum())
        known = h + o

        if known > 0:
            hp, hp_l, hp_u = wilson_score_interval(h, known)
        else:
            hp, hp_l, hp_u = 0.0, 0.0, 0.0

        completeness = round(known / c * 100.0, 1) if c > 0 else 0.0

        p_val = str(sub_df[p_code_col].iloc[0]) if p_code_col in sub_df.columns and len(sub_df) > 0 else "Unknown"
        d_info = get_district_info(str(code) if code else None, p_val)

        denom = population_manager.resolve_denominator(
            year=eff_year,
            prov_code=d_info["prov_code"],
            district_code=str(code) if code and code != "Unknown" else "Unknown",
            sex=sex,
            nationality=nationality,
            age_band=None,
            scope_mode="district",
        )
        dist_pop = denom["population"] if denom.get("available") else None
        is_estimated_pop = False
        pop_yr_ce = denom.get("reference_year")
        pop_yr_be = denom.get("population_year_be")

        if dist_pop is None and d_info["prov_code"] and d_info["prov_code"] != "Unknown":
            p_denom = population_manager.resolve_denominator(
                year=eff_year,
                prov_codes=[d_info["prov_code"]],
                sex=sex,
                nationality=nationality,
                scope_mode="provinces",
            )
            p_pop = p_denom.get("population") if p_denom.get("available") else None
            if p_pop and p_pop > 0:
                ref_d_cnt = len(get_districts_list(d_info["prov_code"]))
                if ref_d_cnt <= 0:
                    ref_d_cnt = 50 if d_info["prov_code"] == "10" else 10
                dist_pop = max(int(round(p_pop / ref_d_cnt)), 1)
                is_estimated_pop = True
                pop_yr_ce = p_denom.get("reference_year")
                pop_yr_be = p_denom.get("population_year_be")

        if dist_pop and dist_pop > 0:
            crate, cr_l, cr_u = exact_poisson_rate_interval(c, dist_pop)
            hrate, hr_l, hr_u = exact_poisson_rate_interval(h, dist_pop)
            pop_rate_note = (
                f"ประมาณการประชากรรายอำเภอจากประชากรจังหวัดปี พ.ศ. {pop_yr_be} หารจำนวนอำเภอ ({ref_d_cnt} อำเภอ)"
                if is_estimated_pop
                else denom["reason_th"]
            )
        else:
            crate, cr_l, cr_u = None, None, None
            hrate, hr_l, hr_u = None, None, None
            pop_rate_note = denom["reason_th"]

        clean_name_th = d_info["name_th"] if (d_info.get("lookup_status") == "matched" or not name_th or "ไม่มีรายชื่อเขต" in str(name_th)) else name_th
        clean_name_en = d_info["name_en"] if (d_info.get("lookup_status") == "matched" or not name_en or "No Bangkok district" in str(name_en)) else name_en

        rows.append({
            "province_code": d_info["prov_code"],
            "province_name_th": d_info["prov_name_th"],
            "province_name_en": d_info["prov_name_en"],
            "district_code": code or "Unknown",
            "district_name_th": clean_name_th,
            "district_name_en": clean_name_en,
            "lookup_status": d_info["lookup_status"],
            "cases_C": c,
            "numerator_cases_C": c,
            "numerator_ipd_H": h,
            "ipd_H": h,
            "opd_O": o,
            "unknown_U": u,
            "hospitalization_prop": hp,
            "hospitalization_prop_ci": [hp_l, hp_u],
            "patient_type_completeness": completeness,
            "district_population": int(dist_pop) if dist_pop else None,
            "is_estimated_district_pop": is_estimated_pop,
            "population_year_ce": pop_yr_ce,
            "population_year_be": pop_yr_be,
            "case_rate_per_100k": crate,
            "case_rate_ci": [cr_l, cr_u] if crate is not None else None,
            "hosp_rate_per_100k": hrate,
            "hosp_rate_ci": [hr_l, hr_u] if hrate is not None else None,
            "rate_status_note": pop_rate_note,
        })

    rows.sort(key=lambda x: x["cases_C"], reverse=True)
    return rows
