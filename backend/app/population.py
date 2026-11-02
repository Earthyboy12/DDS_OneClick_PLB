import re
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union

from app.reference_db import (
    AGE_BAND_INDEX_RANGES,
    get_population_snapshots,
    get_geography_population_row,
    get_age_range_population_sql,
    get_all_standard_age_band_populations,
    get_province_by_code,
    get_all_provinces,
)

LATEST_REFERENCE_YEAR = 2025  # พ.ศ. 2568 (เดือนพฤศจิกายน 6811)


def parse_population_sheet_name(sheet_name: str) -> Optional[Tuple[int, int]]:
    """
    Parses sheet name like '1_6811' -> (gregorian_year=2025, month=11)
    Buddhist Era year: 68 -> 2568 -> 2025.
    """
    match = re.search(r"(\d+)_(\d{2})(\d{2})", str(sheet_name))
    if not match:
        match2 = re.search(r"(\d{2})(\d{2})", str(sheet_name))
        if not match2:
            return None
        be_yr = int(match2.group(1))
        month = int(match2.group(2))
    else:
        be_yr = int(match.group(2))
        month = int(match.group(3))

    full_be_year = 2500 + be_yr
    gregorian_year = full_be_year - 543
    return gregorian_year, month


def _normalize_sex_to_db(sex: Optional[str]) -> Optional[str]:
    if not sex or str(sex).strip().lower() in ("", "all", "overall", "ทั้งหมด"):
        return None
    s = str(sex).strip().lower()
    if s in ("ชาย", "male", "m", "1"):
        return "male"
    if s in ("หญิง", "female", "f", "2"):
        return "female"
    return "unknown"


def normalize_province_codes_input(
    prov_code: Optional[Union[str, List[str]]] = None,
    prov_codes: Optional[List[str]] = None,
) -> List[str]:
    """
    Normalizes single or multiple province codes into a deduplicated list of 2-digit codes.
    Never mixes national code '00' with individual provinces.
    """
    raw_items: List[str] = []
    if prov_codes:
        if isinstance(prov_codes, list):
            raw_items.extend(str(x) for x in prov_codes if x is not None)
        elif isinstance(prov_codes, str):
            raw_items.extend(x.strip() for x in prov_codes.split(",") if x.strip())
    if prov_code:
        if isinstance(prov_code, list):
            raw_items.extend(str(x) for x in prov_code if x is not None)
        elif isinstance(prov_code, str):
            raw_items.extend(x.strip() for x in prov_code.split(",") if x.strip())

    cleaned: List[str] = []
    for item in raw_items:
        s = str(item).strip()
        if not s or s.lower() in ("all", "none", "null", "ทั้งหมด"):
            continue
        if s.isdigit():
            s = s.zfill(2)
        if s not in cleaned:
            cleaned.append(s)

    # If both '00' and specific provinces were passed, strip '00' so national row is never summed with provinces
    if len(cleaned) > 1 and "00" in cleaned:
        cleaned = [c for c in cleaned if c != "00"]
    return cleaned


class PopulationManager:
    """
    Manages provincial, multi-province, national, and age/sex-stratified population denominators
    backed by dds_reference.sqlite.
    Strictly enforces:
    - Single province: matches province, year (with fallback to 2025 / พ.ศ. 2568 if year unavailable), age, sex.
    - Multiple provinces: rate = sum(cases_selected_provinces) / sum(population_selected_provinces) * 100000.
      Never averages provincial rates, never duplicates a province, never adds national '00' to provinces.
      If any selected province lacks a compatible denominator, reports the missing province(s) and marks rate unavailable.
    - Nationwide ('national' or '00'): uses national population once (or sum of 77 provinces without double-counting '00').
    - District ('district'): never divides district cases by provincial population; uses district pop only if available.
    - Unspecified scope ('all_imported' across multiple/unspecified provinces): does not guess national or partial scope.
    - Multi-year scope: does not pool multi-year cases over a single year's population; computes per-year rates instead.
    """

    def __init__(self):
        # Optional overrides if user uploads tidy district population CSV/Excel
        self.district_populations: Dict[Tuple[int, str], float] = {}
        self.custom_province_populations: Dict[Tuple[int, str], Dict[str, Any]] = {}
        self.sheet_metadata: List[Dict[str, Any]] = []

    def get_available_years(self) -> List[int]:
        return [int(s["reference_year"]) for s in get_population_snapshots()]

    def compute_median_reference_year(self, detected_years: Optional[List[int]] = None) -> int:
        """
        Computes the median year from a list of years (e.g. [2023, 2024, 2025] -> 2024 / พ.ศ. 2567).
        Falls back to LATEST_REFERENCE_YEAR (2025 / พ.ศ. 2568) if no years are provided.
        """
        if not detected_years:
            return LATEST_REFERENCE_YEAR
        cleaned_yrs = sorted(
            set(
                (int(y) - 543 if int(y) >= 2400 else int(y))
                for y in detected_years
                if y is not None and not pd.isna(y)
            )
        )
        if not cleaned_yrs:
            return LATEST_REFERENCE_YEAR
        mid_idx = (len(cleaned_yrs) - 1) // 2
        return cleaned_yrs[mid_idx]

    def resolve_effective_population_year(
        self,
        requested_year: Optional[int],
        detected_years: Optional[List[int]] = None,
    ) -> Tuple[int, bool]:
        """
        Resolves the population snapshot year.
        If requested_year is None (multi-year or unspecified), uses the median year from detected_years
        (e.g. 2566-2568 -> 2567 / 2024 CE) or falls back to 2025 (พ.ศ. 2568, latest available).
        If requested_year is in available years (2013–2025), returns (requested_year, False).
        Otherwise, falls back to 2025 (พ.ศ. 2568, latest available) and returns (2025, True).
        """
        avail = set(self.get_available_years())
        if requested_year is None:
            med_yr = self.compute_median_reference_year(detected_years)
            if med_yr in avail:
                return med_yr, True
            return LATEST_REFERENCE_YEAR, True
        yr = int(requested_year)
        if yr >= 2400:
            yr -= 543
        if yr in avail:
            return yr, False
        return LATEST_REFERENCE_YEAR, True

    def resolve_denominator(
        self,
        year: Optional[int],
        prov_code: Optional[Union[str, List[str]]] = None,
        district_code: Optional[str] = None,
        sex: Optional[str] = None,
        nationality: Optional[str] = None,
        age_band: Optional[str] = None,
        prov_codes: Optional[List[str]] = None,
        scope_mode: Optional[str] = None,
        detected_years: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Matches denominator by scope_mode, province(s), district, year (using median year when multi-year
        or 2025 / พ.ศ. 2568 fallback if year unavailable), age, sex, and verified nationality universe.
        """
        clean_dist = (
            str(district_code).strip()
            if district_code and str(district_code).strip().lower() not in ("", "all", "none", "unknown")
            else None
        )
        norm_provs = normalize_province_codes_input(prov_code=prov_code, prov_codes=prov_codes)
        clean_nat = (
            str(nationality).strip()
            if nationality and str(nationality).strip().lower() not in ("", "all", "overall", "ทั้งหมด")
            else None
        )
        sex_db = _normalize_sex_to_db(sex)

        eff_scope_mode = scope_mode
        if not eff_scope_mode:
            if clean_dist:
                eff_scope_mode = "district"
            elif norm_provs == ["00"]:
                eff_scope_mode = "national"
            elif len(norm_provs) >= 1:
                eff_scope_mode = "provinces"
            else:
                eff_scope_mode = "all_imported"

        req_year = int(year) if year is not None else None
        if req_year is not None and req_year >= 2400:
            req_year -= 543
        is_multi_year = req_year is None
        pop_year, is_fallback_year = self.resolve_effective_population_year(req_year, detected_years=detected_years)

        # 1. District check: Never divide district cases by provincial population
        if eff_scope_mode == "district" or clean_dist:
            if (
                pop_year is not None
                and clean_dist
                and ((pop_year, clean_dist) in self.district_populations or (LATEST_REFERENCE_YEAR, clean_dist) in self.district_populations)
                and sex_db is None
                and clean_nat is None
                and age_band is None
            ):
                used_yr = pop_year if (pop_year, clean_dist) in self.district_populations else LATEST_REFERENCE_YEAR
                fb = is_fallback_year or (used_yr != req_year)
                d_pop = int(self.district_populations[(used_yr, clean_dist)])
                return {
                    "available": True,
                    "population": d_pop,
                    "requested_year": req_year,
                    "reference_year": used_yr,
                    "population_year_be": used_yr + 543,
                    "is_fallback_year": fb,
                    "is_median_year": is_multi_year,
                    "reference_month": None,
                    "scope_mode": "district",
                    "province_code": clean_dist[:2] if len(clean_dist) == 4 else None,
                    "province_codes": [clean_dist[:2]] if len(clean_dist) == 4 else [],
                    "district_code": clean_dist,
                    "missing_provinces": [],
                    "reason_th": (
                        f"คำนวณจากประชากรรายอำเภอที่นำเข้าเพิ่มเติม ปี พ.ศ. {used_yr + 543} (ค.ศ. {used_yr})"
                        + (f" [ใช้ปีมัธยฐาน/ปีล่าสุด]" if fb else "")
                    ),
                    "reason_en": (
                        f"Calculated from imported district population for year {used_yr} (B.E. {used_yr + 543})"
                        + (f" [median/latest year fallback]" if fb else "")
                    ),
                }
            return {
                "available": False,
                "population": None,
                "requested_year": req_year,
                "reference_year": pop_year,
                "population_year_be": (pop_year + 543) if pop_year else None,
                "is_fallback_year": is_fallback_year,
                "is_median_year": is_multi_year,
                "reference_month": None,
                "scope_mode": "district",
                "province_code": norm_provs[0] if len(norm_provs) == 1 else (clean_dist[:2] if clean_dist and len(clean_dist) == 4 else None),
                "province_codes": norm_provs,
                "district_code": clean_dist,
                "missing_provinces": [],
                "reason_th": "ไม่มีข้อมูลประชากรรายอำเภอที่ตรงกันในฐานข้อมูลอ้างอิง (ห้ามนำผู้ป่วยบางอำเภอหารด้วยประชากรทั้งจังหวัด)",
                "reason_en": "No matching district population in reference database (never divide district cases by provincial population)",
            }

        # 2. Scope resolution: For 'all_imported' or empty 'provinces', default to nationwide ('00') if no provinces passed
        if not norm_provs:
            norm_provs = ["00"]

        # Determine target province codes for lookup
        is_national = eff_scope_mode == "national" or norm_provs == ["00"] or len(norm_provs) >= 77
        if is_national:
            target_provs = ["00"]
        else:
            target_provs = [p for p in norm_provs if p != "00"]

        # 3. Validate every target province has a matching denominator row for pop_year
        missing_provs: List[str] = []
        geo_rows: Dict[str, Dict[str, Any]] = {}
        for p_code in target_provs:
            g_row = get_geography_population_row(pop_year, p_code)
            if not g_row:
                missing_provs.append(p_code)
            else:
                geo_rows[p_code] = g_row

        if missing_provs:
            missing_labels = []
            for mp in missing_provs:
                pm = get_province_by_code(mp)
                missing_labels.append(f"{pm['name_th']} ({mp})" if pm else f"รหัส {mp}")
            missing_str_th = ", ".join(missing_labels)
            missing_str_en = ", ".join(missing_provs)
            return {
                "available": False,
                "population": None,
                "requested_year": req_year,
                "reference_year": pop_year,
                "population_year_be": pop_year + 543,
                "is_fallback_year": is_fallback_year,
                "is_median_year": is_multi_year,
                "reference_month": None,
                "scope_mode": "national" if is_national else "provinces",
                "province_code": target_provs[0] if len(target_provs) == 1 else None,
                "province_codes": target_provs,
                "district_code": None,
                "missing_provinces": missing_provs,
                "reason_th": (
                    f"ไม่สามารถคำนวณอัตรารวมได้ เนื่องจากขาดตัวหารประชากรที่ตรงกันของจังหวัด: {missing_str_th} "
                    f"(ห้ามตัดจังหวัดที่ขาดออกจากตัวหารโดยยังเก็บผู้ป่วยไว้ในตัวเศษ)"
                ),
                "reason_en": (
                    f"Cannot compute combined rate: missing matching population denominator for province(s): {missing_str_en} "
                    f"(never drop missing provinces from denominator while retaining their cases in numerator)"
                ),
            }

        first_geo = geo_rows[target_provs[0]]
        ref_month = int(first_geo["reference_month"])
        month_name_th = "พฤศจิกายน" if ref_month == 11 else "ธันวาคม"
        month_name_en = "Nov" if ref_month == 11 else "Dec"
        if is_multi_year:
            clean_det = sorted(set((int(y) - 543 if int(y) >= 2400 else int(y)) for y in (detected_years or []) if y is not None))
            if len(clean_det) >= 2:
                fallback_note_th = (
                    f" [ข้อมูลหลายปี พ.ศ. {clean_det[0] + 543}–{clean_det[-1] + 543}: "
                    f"ใช้ประชากรปีมัธยฐาน พ.ศ. {pop_year + 543} (ค.ศ. {pop_year}) เป็นตัวหาร]"
                )
                fallback_note_en = (
                    f" [Multi-year ({clean_det[0]}–{clean_det[-1]}): using median year {pop_year} (B.E. {pop_year + 543}) population]"
                )
            else:
                fallback_note_th = f" [ใช้ประชากรปีอ้างอิง พ.ศ. {pop_year + 543} (ค.ศ. {pop_year})]"
                fallback_note_en = f" [Using reference year {pop_year} (B.E. {pop_year + 543}) population]"
        elif is_fallback_year and req_year is not None:
            fallback_note_th = (
                f" [ไม่มีข้อมูลประชากรปี ค.ศ. {req_year} (พ.ศ. {req_year + 543}) จึงใช้ประชากรปีล่าสุด พ.ศ. 2568 (ค.ศ. 2025)]"
            )
            fallback_note_en = (
                f" [No population data for {req_year}; using latest 2025 (B.E. 2568) population]"
            )
        else:
            fallback_note_th = ""
            fallback_note_en = ""

        # 5. Nationality check: No age-by-nationality cross-tabulations; single-age nationality universe unverified
        if clean_nat is not None:
            return {
                "available": False,
                "population": None,
                "requested_year": req_year,
                "reference_year": pop_year,
                "population_year_be": pop_year + 543,
                "is_fallback_year": is_fallback_year,
                "reference_month": ref_month,
                "scope_mode": "national" if is_national else "provinces",
                "province_code": "00" if is_national else (target_provs[0] if len(target_provs) == 1 else None),
                "province_codes": target_provs,
                "district_code": None,
                "missing_provinces": [],
                "reason_th": "ไม่มีตัวหารประชากรจำแนกตามสัญชาติ/อายุที่ยืนยันขอบเขตตรงกันในฐานข้อมูลอ้างอิง (ห้ามนำยอดรวมลบประชากรต่างด้าวเพื่ออนุมานสัญชาติไทย)",
                "reason_en": "No verified nationality-specific or age-by-nationality population denominator in reference database",
            }

        # 6. Sex check: Unknown sex has no population denominator
        if sex_db == "unknown":
            return {
                "available": False,
                "population": None,
                "requested_year": req_year,
                "reference_year": pop_year,
                "population_year_be": pop_year + 543,
                "is_fallback_year": is_fallback_year,
                "reference_month": ref_month,
                "scope_mode": "national" if is_national else "provinces",
                "province_code": "00" if is_national else (target_provs[0] if len(target_provs) == 1 else None),
                "province_codes": target_provs,
                "district_code": None,
                "missing_provinces": [],
                "reason_th": "ไม่มีตัวหารประชากรสำหรับกลุ่มที่ไม่ระบุเพศ",
                "reason_en": "No population denominator for unknown sex",
            }

        # Build human-readable geography label
        if is_national:
            geo_label_th = "ทั่วประเทศ (77 จังหวัด, ยอดประชากรประเทศรหัส 00 เพียงครั้งเดียว)"
            geo_label_en = "Nationwide (77 Provinces, National Code 00 used once)"
        elif len(target_provs) == 1:
            pm = get_province_by_code(target_provs[0])
            geo_label_th = f"จังหวัด{pm['name_th']} (รหัส {target_provs[0]})" if pm else f"จังหวัดรหัส {target_provs[0]}"
            geo_label_en = f"{pm['name_en']} Province (Code {target_provs[0]})" if pm else f"Province {target_provs[0]}"
        else:
            names_th = []
            names_en = []
            for p_code in target_provs:
                pm = get_province_by_code(p_code)
                names_th.append(pm["name_th"] if pm else p_code)
                names_en.append(pm["name_en"] if pm else p_code)
            preview_th = ", ".join(names_th[:4]) + (f" และอีก {len(names_th) - 4} จังหวัด" if len(names_th) > 4 else "")
            preview_en = ", ".join(names_en[:4]) + (f" +{len(names_en) - 4} more" if len(names_en) > 4 else "")
            geo_label_th = f"รวม {len(target_provs)} จังหวัดที่เลือก ({preview_th})"
            geo_label_en = f"Combined {len(target_provs)} Selected Provinces ({preview_en})"

        # 7. Age band check (sums across all target_provs without double-counting)
        if age_band is not None:
            if age_band == "Unknown" or age_band not in AGE_BAND_INDEX_RANGES:
                return {
                    "available": False,
                    "population": None,
                    "requested_year": req_year,
                    "reference_year": pop_year,
                    "population_year_be": pop_year + 543,
                    "is_fallback_year": is_fallback_year,
                    "reference_month": ref_month,
                    "scope_mode": "national" if is_national else "provinces",
                    "province_code": "00" if is_national else (target_provs[0] if len(target_provs) == 1 else None),
                    "province_codes": target_provs,
                    "province_name_th": geo_label_th,
                    "province_name_en": geo_label_en,
                    "district_code": None,
                    "missing_provinces": [],
                    "reason_th": "ไม่มีตัวหารประชากรสำหรับกลุ่มที่ไม่ระบุอายุ",
                    "reason_en": "No population denominator for unknown age group",
                }
            lo_idx, hi_idx = AGE_BAND_INDEX_RANGES[age_band]
            total_age_pop = 0
            per_prov_pop: Dict[str, int] = {}
            missing_age_provs: List[str] = []
            for p_code in target_provs:
                p_val = get_age_range_population_sql(pop_year, p_code, lo_idx, hi_idx, sex_db=sex_db)
                if p_val is None or p_val <= 0:
                    missing_age_provs.append(p_code)
                else:
                    per_prov_pop[p_code] = int(p_val)
                    total_age_pop += int(p_val)

            if missing_age_provs or total_age_pop <= 0:
                return {
                    "available": False,
                    "population": None,
                    "requested_year": req_year,
                    "reference_year": pop_year,
                    "population_year_be": pop_year + 543,
                    "is_fallback_year": is_fallback_year,
                    "reference_month": ref_month,
                    "scope_mode": "national" if is_national else "provinces",
                    "province_code": "00" if is_national else (target_provs[0] if len(target_provs) == 1 else None),
                    "province_codes": target_provs,
                    "province_name_th": geo_label_th,
                    "province_name_en": geo_label_en,
                    "district_code": None,
                    "missing_provinces": missing_age_provs,
                    "reason_th": f"ไม่พบตัวหารประชากรกลุ่มอายุ {age_band} ปี ที่ครบถ้วนสำหรับจังหวัดที่เลือก",
                    "reason_en": f"Population unavailable for age group {age_band} across all selected provinces",
                }

            return {
                "available": True,
                "population": int(total_age_pop),
                "requested_year": req_year,
                "reference_year": pop_year,
                "population_year_be": pop_year + 543,
                "is_fallback_year": is_fallback_year,
                "is_median_year": is_multi_year,
                "reference_month": ref_month,
                "scope_mode": "national" if is_national else "provinces",
                "province_code": "00" if is_national else (target_provs[0] if len(target_provs) == 1 else None),
                "province_codes": target_provs,
                "province_breakdown": per_prov_pop,
                "province_name_th": geo_label_th,
                "province_name_en": geo_label_en,
                "district_code": None,
                "missing_provinces": [],
                "reason_th": (
                    f"ประชากร {geo_label_th} กลุ่มอายุ {age_band} ปี "
                    f"(พ.ศ. {pop_year + 543} / ค.ศ. {pop_year} เดือน{month_name_th}){fallback_note_th}"
                ),
                "reason_en": (
                    f"{geo_label_en} age {age_band} population "
                    f"({month_name_en} {pop_year} / B.E. {pop_year + 543} snapshot){fallback_note_en}"
                ),
            }

        # 8. Overall geography population (all ages, summed across target_provs without double-counting)
        total_pop = 0
        total_age_known = 0
        per_prov_pop = {}
        for p_code in target_provs:
            g_row = geo_rows[p_code]
            if sex_db == "male":
                p_pop = int(g_row["male_total_source"])
            elif sex_db == "female":
                p_pop = int(g_row["female_total_source"])
            else:
                p_pop = int(g_row["population_total_source"])
            per_prov_pop[p_code] = p_pop
            total_pop += p_pop
            total_age_known += int(g_row["age_known_population_sum"])

        return {
            "available": True,
            "population": int(total_pop),
            "requested_year": req_year,
            "reference_year": pop_year,
            "population_year_be": pop_year + 543,
            "is_fallback_year": is_fallback_year,
            "is_median_year": is_multi_year,
            "reference_month": ref_month,
            "scope_mode": "national" if is_national else "provinces",
            "province_code": "00" if is_national else (target_provs[0] if len(target_provs) == 1 else None),
            "province_codes": target_provs,
            "province_breakdown": per_prov_pop,
            "province_name_th": geo_label_th,
            "province_name_en": geo_label_en,
            "district_code": None,
            "missing_provinces": [],
            "age_known_population_sum": total_age_known,
            "reason_th": (
                f"ประชากรตามทะเบียนราษฎร {geo_label_th} ณ เดือน{month_name_th} พ.ศ. {pop_year + 543} (ค.ศ. {pop_year})"
                f"{fallback_note_th}"
            ),
            "reason_en": (
                f"Registry population for {geo_label_en} ({month_name_en} {pop_year} / B.E. {pop_year + 543} snapshot)"
                f"{fallback_note_en}"
            ),
        }

    def get_province_population(
        self,
        prov_code: Optional[Union[str, List[str]]],
        year: Optional[int],
        sex: Optional[str] = None,
        nationality: Optional[str] = None,
        district_code: Optional[str] = None,
        scope_mode: Optional[str] = None,
    ) -> Optional[float]:
        res = self.resolve_denominator(
            year=year,
            prov_code=prov_code,
            district_code=district_code,
            sex=sex,
            nationality=nationality,
            age_band=None,
            scope_mode=scope_mode,
        )
        return float(res["population"]) if res["available"] and res["population"] else None

    def get_age_band_population(
        self,
        age_band: str,
        prov_code: Optional[Union[str, List[str]]],
        year: Optional[int],
        sex: Optional[str] = None,
        nationality: Optional[str] = None,
        district_code: Optional[str] = None,
        scope_mode: Optional[str] = None,
    ) -> Optional[float]:
        res = self.resolve_denominator(
            year=year,
            prov_code=prov_code,
            district_code=district_code,
            sex=sex,
            nationality=nationality,
            age_band=age_band,
            scope_mode=scope_mode,
        )
        return float(res["population"]) if res["available"] and res["population"] else None

    def load_from_excel(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Inspects an uploaded DOPA Excel workbook, verifying duplicate collapse and code 00 isolation.
        Primary reference remains dds_reference.sqlite.
        """
        wb = pd.ExcelFile(file_path)
        sheet_summaries = []
        for sheet_name in wb.sheet_names:
            parsed = parse_population_sheet_name(sheet_name)
            if not parsed:
                continue
            year, month = parsed
            df = wb.parse(sheet_name).dropna(how="all")
            df.columns = [str(c).strip() for c in df.columns]
            initial_len = len(df)
            df = df.drop_duplicates()
            collapsed_count = initial_len - len(df)

            prov_col = df.columns[0]
            for c in df.columns:
                if any(k in c.lower() for k in ["prov", "จังหวัด", "รหัส"]):
                    prov_col = c
                    break

            def clean_code(v):
                s = str(v).strip().split(".")[0]
                return s.zfill(2) if s.isdigit() else s

            df["_clean_prov"] = df[prov_col].apply(clean_code)
            national_rows = df[df["_clean_prov"].isin(["0", "00", "0000"])]
            prov_df = df[~df["_clean_prov"].isin(["0", "00", "0000"])]

            sheet_summaries.append({
                "sheet_name": sheet_name,
                "gregorian_year": year,
                "month": month,
                "collapsed_duplicates": collapsed_count,
                "has_national_code_0": len(national_rows) > 0,
                "provinces_count": len(prov_df),
            })
        self.sheet_metadata = sheet_summaries
        return {
            "sheets_processed": len(sheet_summaries),
            "summaries": sheet_summaries,
            "reference_db_active": True,
        }

    def load_tidy_district_population(self, csv_or_df: pd.DataFrame | str, default_year: int = 2025) -> int:
        """
        Loads optional tidy district population CSV/DataFrame containing [district_code, population, optional year].
        Preserves leading zeros on district_code.
        """
        if isinstance(csv_or_df, (str, Path)):
            df = pd.read_csv(csv_or_df, dtype=str, keep_default_na=False)
        else:
            df = csv_or_df

        count = 0
        code_cols = [c for c in df.columns if any(k in c.lower() for k in ["code", "รหัส", "district", "อำเภอ"])]
        pop_cols = [c for c in df.columns if any(k in c.lower() for k in ["pop", "ประชากร", "total", "จำนวน"])]
        yr_cols = [c for c in df.columns if any(k in c.lower() for k in ["year", "ปี"])]
        if not code_cols or not pop_cols:
            return 0
        code_col = code_cols[0]
        pop_col = pop_cols[0]
        yr_col = yr_cols[0] if yr_cols else None

        for _, row in df.iterrows():
            dcode = str(row[code_col]).strip().split(".")[0]
            if dcode.isdigit() and len(dcode) <= 4:
                dcode = dcode.zfill(4)
            if len(dcode) == 4 and dcode.isdigit() and not dcode.endswith("00"):
                yr_raw = str(row[yr_col]).strip() if (yr_col and pd.notna(row[yr_col]) and str(row[yr_col]).strip() != "") else str(default_year)
                try:
                    yr = int(float(yr_raw))
                    if yr >= 2400:
                        yr -= 543
                    pop_val = float(str(row[pop_col]).replace(",", "").strip())
                    self.district_populations[(yr, dcode)] = pop_val
                    count += 1
                except (ValueError, TypeError):
                    pass
        return count


population_manager = PopulationManager()
