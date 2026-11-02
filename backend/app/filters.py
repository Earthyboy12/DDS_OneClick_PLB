from typing import Dict, Any, Optional, List
import pandas as pd

from app.district_crosswalk import get_province_info, get_district_info
from app.reference_db import get_province_by_code
from app.population import population_manager, normalize_province_codes_input
from app.measures import calculate_surveillance_measures
from app.dds_importer import ensure_dataframe_dates_and_epi_weeks


DEFAULT_FILTERS: Dict[str, Any] = {
    "scope_mode": "all_imported",  # 'all_imported' | 'national' | 'provinces' | 'district'
    "province_code": None,
    "province_codes": [],
    "district_code": None,
    "year": None,
    "sex": None,
    "nationality": None,
    "patient_type": None,
    "address_type": "residence",
    "comparator_province_code": None,
    "lang": "th",
}


def normalize_filters(raw_filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    f = {
        "scope_mode": "all_imported",
        "province_code": None,
        "province_codes": [],
        "district_code": None,
        "year": None,
        "sex": None,
        "nationality": None,
        "patient_type": None,
        "address_type": "residence",
        "comparator_province_code": None,
        "lang": "th",
    }
    if not raw_filters:
        return f

    for k in ("province_code", "district_code", "year", "sex", "nationality", "patient_type", "address_type", "comparator_province_code", "lang", "scope_mode"):
        if k in raw_filters and raw_filters[k] is not None:
            val = raw_filters[k]
            if isinstance(val, str):
                val_s = val.strip()
                if val_s == "" or val_s.lower() in ("all", "none", "null", "ทั้งหมด"):
                    if k not in ("address_type", "lang", "scope_mode"):
                        f[k] = None
                else:
                    f[k] = val_s
            else:
                f[k] = val

    if raw_filters.get("use_illness_district") is True:
        f["address_type"] = "illness"
    elif raw_filters.get("use_illness_district") is False and "address_type" not in raw_filters:
        f["address_type"] = "residence"

    # Normalize province_codes and province_code
    raw_provs = raw_filters.get("province_codes")
    raw_prov_single = f.get("province_code")
    norm_provs = normalize_province_codes_input(prov_code=raw_prov_single, prov_codes=raw_provs)

    explicit_mode = raw_filters.get("scope_mode")
    if explicit_mode in ("all_imported", "national", "provinces", "district"):
        f["scope_mode"] = explicit_mode
    else:
        if f["district_code"]:
            f["scope_mode"] = "district"
        elif norm_provs == ["00"] or str(raw_prov_single).strip() in ("00", "national", "ทั่วประเทศ"):
            f["scope_mode"] = "national"
        elif len(norm_provs) > 0:
            f["scope_mode"] = "provinces"
        else:
            f["scope_mode"] = "all_imported"

    # Keep fields consistent with scope_mode
    if f["scope_mode"] == "all_imported":
        f["province_codes"] = []
        f["province_code"] = None
        f["district_code"] = None
    elif f["scope_mode"] == "national":
        f["province_codes"] = ["00"]
        f["province_code"] = "00"
        f["district_code"] = None
    elif f["scope_mode"] == "provinces":
        clean_p = [p for p in norm_provs if p != "00"]
        f["province_codes"] = clean_p
        f["province_code"] = clean_p[0] if len(clean_p) == 1 else (",".join(clean_p) if clean_p else None)
        f["district_code"] = None
    elif f["scope_mode"] == "district":
        if f["district_code"]:
            d_str = str(f["district_code"]).strip()
            if d_str.isdigit() and len(d_str) <= 4:
                d_str = d_str.zfill(4)
            f["district_code"] = d_str
            p_from_d = d_str[:2] if len(d_str) == 4 and d_str.isdigit() else None
            f["province_codes"] = [p_from_d] if p_from_d else [p for p in norm_provs if p != "00"]
            f["province_code"] = f["province_codes"][0] if f["province_codes"] else None
        else:
            f["province_codes"] = [p for p in norm_provs if p != "00"]
            f["province_code"] = f["province_codes"][0] if len(f["province_codes"]) == 1 else None

    if f["comparator_province_code"]:
        c_str = str(f["comparator_province_code"]).strip()
        f["comparator_province_code"] = c_str.zfill(2) if c_str.isdigit() else c_str

    if f["year"] is not None:
        try:
            yr_int = int(f["year"])
            if yr_int >= 2400:
                yr_int -= 543
            f["year"] = yr_int
        except (ValueError, TypeError):
            f["year"] = None

    if f["sex"]:
        s_low = str(f["sex"]).lower()
        if s_low in ("male", "m", "ชาย", "1"):
            f["sex"] = "ชาย"
        elif s_low in ("female", "f", "หญิง", "2"):
            f["sex"] = "หญิง"
        elif s_low in ("unknown", "ไม่ระบุ"):
            f["sex"] = "Unknown"

    if f["lang"] not in ("th", "en"):
        f["lang"] = "th"
    return f


def apply_filters_and_resolve_scope(
    df: pd.DataFrame,
    raw_filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Applies shared filters to the cleaned surveillance DataFrame and resolves
    the exact denominator context:
    - 'all_imported': All imported records; does NOT guess national or partial surveillance coverage.
    - 'national': Nationwide (77 provinces, national code '00' used once).
    - 'provinces': Single or multiple selected provinces:
        rate = sum(cases_selected_provinces) / sum(population_selected_provinces) * 100000
      Never averages provincial rates, never duplicates provinces, never sums '00' with provinces,
      and reports missing provinces if any selected province lacks a compatible denominator.
    - 'district': Selected district; counts and hospitalization % remain available while population rates
      are unavailable unless matching district population exists.
    - Multi-year: Computes per-year rates ('rates_by_year') rather than pooling multi-year cases over 1 year's population.
    """
    filters = normalize_filters(raw_filters)
    use_illness = filters["address_type"] == "illness"
    prov_col = "illness_prov_code" if use_illness else "residence_prov_code"
    dist_col = "illness_district_code" if use_illness else "residence_district_code"

    work_df = df.copy()
    if not work_df.empty and (
        "analysis_date" not in work_df.columns
        or work_df["analysis_date"].isna().all()
        or "onset_year" not in work_df.columns
        or work_df["onset_year"].isna().all()
    ):
        work_df = ensure_dataframe_dates_and_epi_weeks(work_df)

    scope_mode = filters["scope_mode"]
    selected_provs: List[str] = filters["province_codes"]
    eff_dist: Optional[str] = filters["district_code"]

    if not work_df.empty:
        if scope_mode == "provinces":
            if selected_provs and prov_col in work_df.columns:
                work_df = work_df[work_df[prov_col].isin(selected_provs)]
        elif scope_mode == "national":
            # Include all records within Thailand's 77 provinces (exclude '00' or invalid non-Thai codes if any)
            if prov_col in work_df.columns:
                work_df = work_df[work_df[prov_col] != "00"]
        elif scope_mode == "district":
            if eff_dist and dist_col in work_df.columns:
                work_df = work_df[work_df[dist_col] == eff_dist]
            elif selected_provs and prov_col in work_df.columns:
                work_df = work_df[work_df[prov_col].isin(selected_provs)]

        if filters["year"] is not None:
            yr_col = "onset_year" if "onset_year" in work_df.columns else "epi_year"
            if yr_col in work_df.columns:
                work_df = work_df[work_df[yr_col] == filters["year"]]

        if filters["sex"] and "clean_sex" in work_df.columns:
            work_df = work_df[work_df["clean_sex"] == filters["sex"]]

        if filters["nationality"] and "nationality_group" in work_df.columns:
            work_df = work_df[work_df["nationality_group"] == filters["nationality"]]

        if filters["patient_type"] and "clean_patient_type" in work_df.columns:
            work_df = work_df[work_df["clean_patient_type"] == filters["patient_type"]]

    detected_provinces: List[str] = []
    if not work_df.empty and prov_col in work_df.columns:
        detected_provinces = sorted(
            [str(p) for p in work_df[prov_col].dropna().unique() if str(p) not in ("", "None")]
        )
    valid_ref_provs: List[str] = [p for p in detected_provinces if get_province_by_code(p) is not None]

    # Resolve effective year for denominator matching (single year or median year across multi-year data)
    eff_year = filters["year"]
    detected_years: List[int] = []
    yr_col = "onset_year" if ("onset_year" in work_df.columns or "onset_year" in df.columns) else "epi_year"
    if not work_df.empty and yr_col in work_df.columns:
        detected_years = sorted(
            [int(y) for y in work_df[yr_col].dropna().unique() if pd.notna(y)]
        )
    if eff_year is None and len(detected_years) == 1:
        eff_year = detected_years[0]

    # Determine denominator province codes
    if scope_mode == "national":
        denom_prov_codes = ["00"]
    elif scope_mode == "provinces":
        if selected_provs:
            denom_prov_codes = selected_provs
        else:
            denom_prov_codes = ["00"] if len(valid_ref_provs) >= 70 else (valid_ref_provs if valid_ref_provs else ["00"])
    elif scope_mode == "all_imported":
        denom_prov_codes = ["00"] if len(valid_ref_provs) >= 70 else (valid_ref_provs if valid_ref_provs else ["00"])
    else:
        denom_prov_codes = selected_provs

    # Build human-readable scope descriptions
    if scope_mode == "district" and eff_dist:
        p_for_d = eff_dist[:2] if len(eff_dist) == 4 and eff_dist.isdigit() else (selected_provs[0] if selected_provs else None)
        d_info = get_district_info(eff_dist, p_for_d)
        scope_th = f"อำเภอ{d_info['name_th']} (รหัส {eff_dist}, จังหวัด{d_info['prov_name_th']})"
        scope_en = f"District {d_info['name_en']} (Code {eff_dist}, {d_info['prov_name_en']})"
        prov_name_th = d_info["prov_name_th"]
        prov_name_en = d_info["prov_name_en"]
        eff_prov_code = d_info["prov_code"]
    elif scope_mode == "national":
        scope_th = "ทั่วประเทศ (77 จังหวัด - ใช้ยอดประชากรประเทศรหัส 00 เพียงครั้งเดียว)"
        scope_en = "Nationwide (77 Provinces - National Code 00 used once)"
        prov_name_th = "ทั่วประเทศ (77 จังหวัด)"
        prov_name_en = "Nationwide (77 Provinces)"
        eff_prov_code = "00"
    elif scope_mode == "provinces":
        if len(selected_provs) == 1:
            p_info = get_province_info(selected_provs[0])
            scope_th = f"จังหวัด{p_info['name_th']} (รหัส {selected_provs[0]})"
            scope_en = f"{p_info['name_en']} Province (Code {selected_provs[0]})"
            prov_name_th = p_info["name_th"]
            prov_name_en = p_info["name_en"]
            eff_prov_code = selected_provs[0]
        elif len(selected_provs) > 1:
            p_infos = [get_province_info(pc) for pc in selected_provs]
            names_th = [pi["name_th"] for pi in p_infos]
            names_en = [pi["name_en"] for pi in p_infos]
            short_th = ", ".join(names_th[:4]) + (f" และอีก {len(names_th) - 4} จังหวัด" if len(names_th) > 4 else "")
            short_en = ", ".join(names_en[:4]) + (f" +{len(names_en) - 4} more" if len(names_en) > 4 else "")
            scope_th = f"รวม {len(selected_provs)} จังหวัดที่เลือก ({short_th})"
            scope_en = f"Combined {len(selected_provs)} Selected Provinces ({short_en})"
            prov_name_th = scope_th
            prov_name_en = scope_en
            eff_prov_code = ",".join(selected_provs)
        else:
            scope_th = (
                f"ข้อมูลทุกจังหวัดในชุดข้อมูล ({len(valid_ref_provs)} จังหวัด — คลิกเลือกจังหวัดด้านบนเพื่อกรองเฉพาะจังหวัด)"
                if valid_ref_provs
                else "เลือกจังหวัด (คลิกเลือกจังหวัดด้านบน)"
            )
            scope_en = (
                f"All Provinces in Dataset ({len(valid_ref_provs)} provinces — select province chips above to filter)"
                if valid_ref_provs
                else "Select Province(s)"
            )
            prov_name_th = scope_th
            prov_name_en = scope_en
            eff_prov_code = "00" if denom_prov_codes == ["00"] else (",".join(denom_prov_codes) if denom_prov_codes else None)
    else:
        if len(valid_ref_provs) >= 70:
            scope_th = f"ข้อมูลทั้งหมดที่นำเข้า (ครอบคลุม {len(valid_ref_provs)} จังหวัดทั่วประเทศ — ใช้ประชากรระดับประเทศรหัส 00)"
            scope_en = f"All Imported Data ({len(valid_ref_provs)} provinces — using Nationwide Code 00 denominator)"
            eff_prov_code = "00"
        elif len(valid_ref_provs) >= 1:
            scope_th = f"ข้อมูลทั้งหมดที่นำเข้า (รวมประชากร {len(valid_ref_provs)} จังหวัดที่พบในข้อมูล)"
            scope_en = f"All Imported Data (combined denominator of {len(valid_ref_provs)} provinces in dataset)"
            eff_prov_code = ",".join(valid_ref_provs)
        else:
            scope_th = "ข้อมูลทั้งหมดที่นำเข้า (All Imported Data)"
            scope_en = "All Imported Data"
            eff_prov_code = "00"
        prov_name_th = scope_th
        prov_name_en = scope_en

    # Resolve primary denominator via PopulationManager
    if filters["patient_type"] is not None:
        denom_info = {
            "available": False,
            "population": None,
            "requested_year": eff_year,
            "reference_year": eff_year,
            "population_year_be": (eff_year + 543) if eff_year else None,
            "is_fallback_year": False,
            "reference_month": None,
            "scope_mode": scope_mode,
            "province_code": eff_prov_code,
            "province_codes": denom_prov_codes,
            "district_code": eff_dist,
            "missing_provinces": [],
            "reason_th": "กรองเฉพาะประเภทผู้ป่วยบางส่วน (IPD/OPD) จึงไม่คำนวณอัตราป่วยรวมต่อประชากรทั้งหมด",
            "reason_en": "Filtered to a specific patient type subset; overall population rates are disabled",
        }
    else:
        denom_info = population_manager.resolve_denominator(
            year=eff_year,
            prov_code=denom_prov_codes,
            prov_codes=denom_prov_codes,
            district_code=eff_dist if scope_mode == "district" else None,
            sex=filters["sex"],
            nationality=filters["nationality"],
            age_band=None,
            scope_mode=scope_mode,
            detected_years=detected_years,
        )

    denom_info["scope_name_th"] = scope_th
    denom_info["scope_name_en"] = scope_en

    # Compute per-year rates breakdown ('rates_by_year') so multi-year selections also display rates separately by year
    rates_by_year: List[Dict[str, Any]] = []
    years_to_eval = [filters["year"]] if filters["year"] is not None else detected_years
    for yr in years_to_eval:
        if yr is None:
            continue
        yr_df = work_df[work_df[yr_col] == yr] if (not work_df.empty and yr_col in work_df.columns) else pd.DataFrame()
        y_h = int((yr_df["clean_patient_type"] == "IPD").sum()) if not yr_df.empty else 0
        y_o = int((yr_df["clean_patient_type"] == "OPD").sum()) if not yr_df.empty else 0
        y_u = int((yr_df["clean_patient_type"] == "Unknown").sum()) if not yr_df.empty else 0
        if filters["patient_type"] is not None:
            y_denom = denom_info
        else:
            y_denom = population_manager.resolve_denominator(
                year=int(yr),
                prov_code=denom_prov_codes,
                prov_codes=denom_prov_codes,
                district_code=eff_dist if scope_mode == "district" else None,
                sex=filters["sex"],
                nationality=filters["nationality"],
                age_band=None,
                scope_mode=scope_mode,
            )
        y_pop = y_denom["population"] if y_denom.get("available") else None
        y_m = calculate_surveillance_measures(y_h, y_o, y_u, y_pop)
        rates_by_year.append({
            "year_ce": int(yr),
            "year_be": int(yr) + 543,
            "numerator_cases_C": y_m["cases_C"],
            "numerator_ipd_H": y_m["ipd_H"],
            "opd_O": y_m["opd_O"],
            "unknown_U": y_m["unknown_U"],
            "population_denominator": int(y_pop) if y_pop else None,
            "population_year_ce": y_denom.get("reference_year"),
            "population_year_be": y_denom.get("population_year_be"),
            "is_fallback_year": y_denom.get("is_fallback_year", False),
            "scope_name_th": scope_th,
            "scope_name_en": scope_en,
            "case_rate_per_100k": y_m["case_notification_rate"],
            "case_rate_ci": y_m["case_notification_rate_ci"],
            "hosp_rate_per_100k": y_m["hosp_notification_rate"],
            "hosp_rate_ci": y_m["hosp_notification_rate_ci"],
            "hospitalization_prop": y_m["hospitalization_prop"],
            "hospitalization_prop_ci": y_m["hospitalization_prop_ci"],
            "denominator_note_th": y_denom.get("reason_th"),
            "denominator_note_en": y_denom.get("reason_en"),
        })

    # Optional comparator province (default: None)
    comparator_summary = None
    comp_code = filters.get("comparator_province_code")
    if comp_code:
        comp_info = get_province_info(comp_code)
        comp_df = df.copy()
        if not comp_df.empty and prov_col in comp_df.columns:
            comp_df = comp_df[comp_df[prov_col] == comp_code]
            if filters["year"] is not None and yr_col in comp_df.columns:
                comp_df = comp_df[comp_df[yr_col] == filters["year"]]
            if filters["sex"] and "clean_sex" in comp_df.columns:
                comp_df = comp_df[comp_df["clean_sex"] == filters["sex"]]
            if filters["nationality"] and "nationality_group" in comp_df.columns:
                comp_df = comp_df[comp_df["nationality_group"] == filters["nationality"]]

        c_h = int((comp_df["clean_patient_type"] == "IPD").sum()) if not comp_df.empty else 0
        c_o = int((comp_df["clean_patient_type"] == "OPD").sum()) if not comp_df.empty else 0
        c_u = int((comp_df["clean_patient_type"] == "Unknown").sum()) if not comp_df.empty else 0
        comp_denom = population_manager.resolve_denominator(
            year=eff_year,
            prov_code=comp_code,
            prov_codes=[comp_code],
            district_code=None,
            sex=filters["sex"],
            nationality=filters["nationality"],
            age_band=None,
            scope_mode="provinces",
        )
        comp_measures = calculate_surveillance_measures(
            c_h, c_o, c_u, comp_denom["population"] if comp_denom["available"] else None
        )
        comparator_summary = {
            "province_code": comp_code,
            "province_name_th": comp_info["name_th"],
            "province_name_en": comp_info["name_en"],
            "denominator_info": comp_denom,
            "measures": comp_measures,
        }

    return {
        "filtered_df": work_df,
        "filters": filters,
        "scope_mode": scope_mode,
        "selected_province_codes": selected_provs,
        "effective_year": eff_year,
        "effective_prov_code": eff_prov_code,
        "effective_district_code": eff_dist,
        "detected_provinces": detected_provinces,
        "detected_years": detected_years,
        "scope_name_th": scope_th,
        "scope_name_en": scope_en,
        "province_name_th": prov_name_th,
        "province_name_en": prov_name_en,
        "denominator": denom_info,
        "rates_by_year": rates_by_year,
        "comparator": comparator_summary,
    }


def extract_available_filter_options(df: pd.DataFrame, address_type: str = "residence") -> Dict[str, Any]:
    """Returns available filter options present in the imported dataset plus reference provinces."""
    use_illness = address_type == "illness"
    prov_col = "illness_prov_code" if use_illness else "residence_prov_code"
    dist_col = "illness_district_code" if use_illness else "residence_district_code"

    dataset_provinces = []
    dataset_districts = []
    dataset_years = []

    if not df.empty:
        if prov_col in df.columns:
            p_counts = df[prov_col].value_counts().to_dict()
            for p_code, cnt in p_counts.items():
                p_info = get_province_info(str(p_code))
                dataset_provinces.append({
                    "province_code": str(p_code),
                    "name_th": p_info["name_th"],
                    "name_en": p_info["name_en"],
                    "cases": int(cnt),
                })
            dataset_provinces.sort(key=lambda x: (x["province_code"] == "Unknown", x["province_code"]))

        if dist_col in df.columns:
            d_counts = df[dist_col].value_counts().to_dict()
            for d_code, cnt in d_counts.items():
                d_str = str(d_code)
                p_hint = d_str[:2] if len(d_str) == 4 and d_str.isdigit() else None
                d_info = get_district_info(d_str, p_hint)
                dataset_districts.append({
                    "district_code": d_str,
                    "province_code": d_info["prov_code"],
                    "name_th": d_info["name_th"],
                    "name_en": d_info["name_en"],
                    "cases": int(cnt),
                })
            dataset_districts.sort(key=lambda x: (x["district_code"] == "Unknown", x["district_code"]))

        yr_col = "onset_year" if "onset_year" in df.columns else "epi_year"
        if yr_col in df.columns:
            dataset_years = sorted([int(y) for y in df[yr_col].dropna().unique() if pd.notna(y)], reverse=True)

    return {
        "provinces_in_data": dataset_provinces,
        "districts_in_data": dataset_districts,
        "years_in_data": dataset_years,
        "sex_options": ["ชาย", "หญิง", "Unknown"],
        "nationality_options": ["Thai", "Non-Thai", "Unknown"],
        "patient_type_options": ["IPD", "OPD", "Unknown"],
        "scope_modes": [
            {"value": "all_imported", "label_th": "ข้อมูลทั้งหมดที่นำเข้า (All Imported Data)", "label_en": "All Imported Data"},
            {"value": "national", "label_th": "ทั่วประเทศ (77 จังหวัด)", "label_en": "Nationwide (77 Provinces)"},
            {"value": "provinces", "label_th": "เลือกจังหวัดเดียวหรือหลายจังหวัด", "label_en": "Select Single or Multiple Provinces"},
            {"value": "district", "label_th": "เลือกอำเภอ (District)", "label_en": "Select District"},
        ],
    }
