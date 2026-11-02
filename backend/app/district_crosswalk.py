from typing import Dict, Any, Optional, Tuple
import pandas as pd
from app.reference_db import (
    get_province_by_code,
    get_district_by_code,
    get_all_provinces,
    get_districts_by_province,
    BANGKOK_DISTRICTS,
)

# Optional user-imported geography code overrides (from file_category="geography")
CUSTOM_PROVINCE_LOOKUP: Dict[str, Dict[str, Any]] = {}
CUSTOM_DISTRICT_LOOKUP: Dict[str, Dict[str, Any]] = {}


def _clean_numeric_code(raw_val: Any) -> Optional[str]:
    """
    Cleans raw code string from Excel/CSV without inferring codes from text names.
    Strips trailing '.0' from float representations. Returns digits string or None.
    """
    if raw_val is None:
        return None
    s = str(raw_val).strip()
    if not s or s.lower() in ("nan", "none", "null", "-", ""):
        return None
    if s.endswith(".0"):
        s = s[:-2]
    if not s.isdigit():
        return None
    return s


def construct_four_digit_district_code(
    prov_raw: Any, dist_raw: Any
) -> Tuple[Optional[str], Optional[str]]:
    """
    Constructs validated 2-digit province_code and 4-digit district_code
    strictly from the SAME address family, preserving leading zeros.
    - Example: prov="11", dist="01" (or 1) -> ("11", "1101") (เมืองสมุทรปราการ)
    - Excludes XX00 headings (local code "00") and province "00".
    - Never infers districts from names alone.
    """
    s_prov_clean = _clean_numeric_code(prov_raw)
    s_dist_clean = _clean_numeric_code(dist_raw)

    prov_code: Optional[str] = None
    if s_prov_clean is not None:
        if len(s_prov_clean) <= 2:
            candidate_p = s_prov_clean.zfill(2)
            if candidate_p != "00":
                prov_code = candidate_p

    if s_dist_clean is None:
        return prov_code, None

    # Case 1: dist_raw is already 4 digits
    if len(s_dist_clean) == 4:
        d_prefix = s_dist_clean[:2]
        d_local = s_dist_clean[2:]
        if d_prefix == "00" or d_local == "00":
            return prov_code or (d_prefix if d_prefix != "00" else None), None
        # Must match province from the same address family if province was supplied
        if prov_code is not None and prov_code != d_prefix:
            return prov_code, None
        return d_prefix, s_dist_clean

    # Case 2: dist_raw is 1-2 digit local district code; requires prov_code from same address family
    if len(s_dist_clean) <= 2 and prov_code is not None:
        d_local = s_dist_clean.zfill(2)
        if d_local == "00":
            # XX00 headings are excluded
            return prov_code, None
        return prov_code, f"{prov_code}{d_local}"

    return prov_code, None


def get_province_info(prov_code: Optional[str]) -> Dict[str, Any]:
    """Returns verified province info from dds_reference.sqlite (or custom geography table)."""
    if not prov_code or prov_code == "Unknown":
        return {
            "province_code": "Unknown",
            "name_th": "ไม่ระบุจังหวัด",
            "name_en": "Unspecified Province",
            "scr_group_source": None,
            "lookup_status": "missing_code",
        }
    norm = str(prov_code).strip().zfill(2) if str(prov_code).strip().isdigit() else str(prov_code).strip()
    if norm in CUSTOM_PROVINCE_LOOKUP:
        cp = CUSTOM_PROVINCE_LOOKUP[norm]
        return {
            "province_code": norm,
            "name_th": cp["name_th"],
            "name_en": cp.get("name_en", cp["name_th"]),
            "scr_group_source": cp.get("scr_group_source"),
            "lookup_status": "matched_custom",
        }
    p = get_province_by_code(norm)
    if p:
        return {
            "province_code": p["province_code"],
            "name_th": p["name_th"],
            "name_en": p["name_en"],
            "scr_group_source": p["scr_group_source"],
            "lookup_status": "matched",
        }
    return {
        "province_code": str(prov_code),
        "name_th": f"รหัสจังหวัดไม่ปรากฏในฐานอ้างอิง ({prov_code})",
        "name_en": f"Unmatched Province ({prov_code})",
        "scr_group_source": None,
        "lookup_status": "unmatched_code",
    }


def get_district_info(
    four_digit_code: Optional[str], prov_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Looks up 4-digit district code in dds_reference.sqlite, Bangkok districts lookup,
    or custom uploaded geography table.
    Never guesses or invents district names.
    """
    eff_prov = prov_code
    if not eff_prov and four_digit_code and len(four_digit_code) == 4 and four_digit_code.isdigit():
        eff_prov = four_digit_code[:2]

    prov_info = get_province_info(eff_prov)

    if four_digit_code and str(four_digit_code) in CUSTOM_DISTRICT_LOOKUP:
        cd = CUSTOM_DISTRICT_LOOKUP[str(four_digit_code)]
        return {
            "code": str(four_digit_code),
            "name_th": cd["name_th"],
            "name_en": cd.get("name_en", cd["name_th"]),
            "prov_code": cd.get("prov_code", prov_info["province_code"]),
            "prov_name_th": prov_info["name_th"],
            "prov_name_en": prov_info["name_en"],
            "lookup_status": "matched_custom",
        }

    # Check Bangkok districts (1001-1050)
    if four_digit_code and str(four_digit_code) in BANGKOK_DISTRICTS:
        bk = BANGKOK_DISTRICTS[str(four_digit_code)]
        return {
            "code": str(four_digit_code),
            "name_th": bk["name_th"],
            "name_en": f"{bk['name_th']} ({four_digit_code}, Bangkok)",
            "source_label_th": bk["name_th"],
            "prov_code": "10",
            "prov_name_th": "กรุงเทพมหานคร",
            "prov_name_en": "Bangkok",
            "lookup_status": "matched",
        }

    # Check Bangkok explicit matching or unassigned
    if eff_prov == "10":
        if four_digit_code and str(four_digit_code).strip().isdigit():
            norm_code = (
                f"10{str(four_digit_code).strip().zfill(2)}"
                if len(str(four_digit_code).strip()) <= 2
                else str(four_digit_code).strip()
            )
            if norm_code in BANGKOK_DISTRICTS:
                bk = BANGKOK_DISTRICTS[norm_code]
                return {
                    "code": norm_code,
                    "name_th": bk["name_th"],
                    "name_en": f"{bk['name_th']} ({norm_code}, Bangkok)",
                    "source_label_th": bk["name_th"],
                    "prov_code": "10",
                    "prov_name_th": "กรุงเทพมหานคร",
                    "prov_name_en": "Bangkok",
                    "lookup_status": "matched",
                }
            return {
                "code": str(four_digit_code),
                "name_th": f"รหัสเขต กทม. ไม่ปรากฏในฐานอ้างอิง ({four_digit_code})",
                "name_en": f"Unmatched Bangkok District ({four_digit_code})",
                "prov_code": "10",
                "prov_name_th": "กรุงเทพมหานคร",
                "prov_name_en": "Bangkok",
                "lookup_status": "unmatched_code",
            }
        return {
            "code": "Unknown",
            "name_th": "ไม่ระบุเขต (กรุงเทพมหานคร)",
            "name_en": "Unspecified District (Bangkok)",
            "prov_code": "10",
            "prov_name_th": "กรุงเทพมหานคร",
            "prov_name_en": "Bangkok",
            "lookup_status": "missing_code",
        }

    if not four_digit_code or four_digit_code == "Unknown":
        return {
            "code": "Unknown",
            "name_th": "ไม่ระบุอำเภอ" if eff_prov in (None, "Unknown") else f"ไม่ระบุอำเภอ ({prov_info['name_th']})",
            "name_en": "Unspecified District" if eff_prov in (None, "Unknown") else f"Unspecified District ({prov_info['name_en']})",
            "prov_code": prov_info["province_code"],
            "prov_name_th": prov_info["name_th"],
            "prov_name_en": prov_info["name_en"],
            "lookup_status": "missing_code",
        }

    dist = get_district_by_code(four_digit_code)
    if dist:
        return {
            "code": dist["district_code"],
            "name_th": dist["name_th"],
            "name_en": dist["name_en"],
            "source_label_th": dist["source_label_th"],
            "prov_code": dist["province_code"],
            "prov_name_th": dist["province_name_th"],
            "prov_name_en": dist["province_name_en"],
            "lookup_status": "matched",
        }

    return {
        "code": str(four_digit_code),
        "name_th": f"รหัสอำเภอไม่ปรากฏในฐานอ้างอิง ({four_digit_code})",
        "name_en": f"Unmatched District ({four_digit_code})",
        "prov_code": prov_info["province_code"],
        "prov_name_th": prov_info["name_th"],
        "prov_name_en": prov_info["name_en"],
        "lookup_status": "unmatched_code",
    }


def load_custom_geography_table(df: pd.DataFrame) -> Dict[str, int]:
    """
    Loads user-supplied geography lookup table (province/district codes and names).
    Never mixes geography lookup rows into patient surveillance records.
    """
    prov_loaded = 0
    dist_loaded = 0
    if df is None or df.empty:
        return {"provinces_loaded": 0, "districts_loaded": 0}

    cols = [str(c).strip() for c in df.columns]
    d_code_col = next((c for c in cols if any(k in c.lower() for k in ["district_code", "amphur_code", "รหัสอำเภอ", "code"])), None)
    d_name_col = next((c for c in cols if any(k in c.lower() for k in ["district_name", "amphur_name", "ชื่ออำเภอ", "อำเภอ", "name_th", "name"])), None)
    p_code_col = next((c for c in cols if any(k in c.lower() for k in ["province_code", "prov_code", "รหัสจังหวัด"])), None)
    p_name_col = next((c for c in cols if any(k in c.lower() for k in ["province_name", "prov_name", "ชื่อจังหวัด", "จังหวัด"])), None)

    for _, row in df.iterrows():
        if p_code_col and p_name_col:
            pc = _clean_numeric_code(row.get(p_code_col))
            pn = str(row.get(p_name_col, "")).strip()
            if pc and len(pc) <= 2 and pc.zfill(2) != "00" and pn:
                CUSTOM_PROVINCE_LOOKUP[pc.zfill(2)] = {"name_th": pn, "name_en": pn}
                prov_loaded += 1
        if d_code_col and d_name_col:
            dc = _clean_numeric_code(row.get(d_code_col))
            pc = _clean_numeric_code(row.get(p_code_col)) if p_code_col else None
            dn = str(row.get(d_name_col, "")).strip()
            if dc and dn:
                if len(dc) <= 2 and pc and len(pc) <= 2:
                    full_d = f"{pc.zfill(2)}{dc.zfill(2)}"
                elif len(dc) <= 4:
                    full_d = dc.zfill(4)
                else:
                    full_d = None
                if full_d and not full_d.endswith("00") and not full_d.startswith("00"):
                    CUSTOM_DISTRICT_LOOKUP[full_d] = {
                        "name_th": dn,
                        "name_en": f"District {full_d} ({dn})",
                        "prov_code": full_d[:2],
                    }
                    dist_loaded += 1
    return {"provinces_loaded": prov_loaded, "districts_loaded": dist_loaded}
