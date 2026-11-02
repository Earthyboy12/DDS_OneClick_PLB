import io
import csv
import re
import uuid
import hashlib
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd

from app.district_crosswalk import construct_four_digit_district_code, get_district_info
from app.epi_calendar import date_to_epi_week
from app.measures import assign_age_band

STANDARD_FIELD_ALIASES: Dict[str, List[str]] = {
    "cid": ["cid", "เลขประจำตัวประชาชน", "citizen_id", "id_card", "pid", "hn", "เลขบัตรประชาชน"],
    "sex": ["sex", "gender", "เพศ", "gender_name"],
    "age_years": ["year", "age_y", "age_years", "อายุ(ปี)", "อายุปี", "อายุ", "age", "age_yr"],
    "age_months": ["month", "age_m", "age_months", "อายุ(เดือน)", "อายุเดือน"],
    "nationality_raw": ["race", "nationality", "สัญชาติ", "เชื้อชาติ", "nation", "nat"],
    "occupation": ["occupat", "occupation", "อาชีพ"],
    "residence_province": [
        "prov_code", "chw_code", "จังหวัด(ที่อยู่ปัจจุบัน)", "residence_province",
        "รหัสจังหวัด", "รหัสจังหวัด(ที่อยู่ปัจจุบัน)", "res_prov", "province_code",
    ],
    "residence_district": [
        "รหัสอำเภอ(ที่อยู่ปัจจุบัน)", "amp_code", "อำเภอ(ที่อยู่ปัจจุบัน)", "residence_district",
        "รหัสอำเภอ", "res_dist", "district_code", "amphur_code",
    ],
    "residence_subdistrict": ["รหัสตำบล(ที่อยู่ปัจจุบัน)", "tam_code", "ตำบล(ที่อยู่ปัจจุบัน)", "residence_subdistrict"],
    "illness_province": ["จังหวัดขณะป่วย", "epidem_chw_code", "epidem_province", "รหัสจังหวัดขณะป่วย", "ill_prov"],
    "illness_district": ["อำเภอขณะป่วย", "epidem_amp_code", "epidem_district", "รหัสอำเภอขณะป่วย", "ill_dist"],
    "illness_subdistrict": ["ตำบลขณะป่วย", "epidem_tam_code", "epidem_subdistrict"],
    "onset_date": [
        "datesick", "onset_date", "วันเริ่มป่วย", "วันที่เริ่มป่วย", "วันเริ่มมีอาการ",
        "วันที่เริ่มมีอาการ", "วันที่ป่วย", "วันป่วย", "วันที่มีอาการ", "วันที่เริ่มป่วย/วันที่มีอาการ",
        "datesick_raw", "date_onset", "sickdate", "date_sick", "illness_date", "วันที่เริ่ม", "วันเริ่ม",
    ],
    "treatment_date": ["date_tx", "treatment_date", "วันที่รักษา", "วันที่เข้ารับการรักษา", "datetreat"],
    "diagnosis_date": ["datedefine", "diagnosis_date", "วันที่วินิจฉัย", "วันที่วินิจฉัยโรค", "datediag"],
    "report_date": ["วันที่ส่งรายงาน", "report_date", "datesend", "วันที่รายงาน"],
    "update_date": ["วันที่ update", "update_date", "date_update", "dateupdate", "last_update", "วันที่แก้ไข", "เวลาแก้ไข", "วันที่แก้ไขล่าสุด", "วันเวลาแก้ไข"],
    "disease_group": ["รหัสกลุ่มโรค", "disease_group", "disease_code", "กลุ่มโรค", "disease"],
    "icd10": ["diagnosis icd10", "icd10", "icd10_code", "รหัสโรค"],
    "icd10_list": ["diagnosis_icd10_list", "icd10_list"],
    "patient_type": ["type", "patient_type", "ประเภทผู้ป่วย", "pt_type"],
    "patient_status": ["รหัสสภาพผู้ป่วย", "สภาพผู้ป่วย", "patient_status", "condition", "outcome"],
    "death_date": ["วันที่เสียชีวิต", "death_date", "datedeath"],
    "death_cause": ["สาเหตุการเสียชีวิต", "death_cause", "cause_of_death"],
    "report_status": ["status", "สถานะ", "report_status", "approval_status", "สถานะรายงาน"],
    "severity": ["ความรุนแรง", "severity"],
    "ventilator": ["ใส่เครื่องช่วยหายใจ", "ventilator", "respirator"],
    "complication": ["complication", "ภาวะแทรกซ้อน"],
    "organism": ["organism", "เชื้อก่อโรค"],
}

CANONICAL_SCHEMA_FIELDS: List[Dict[str, str]] = [
    {"key": "cid", "label_th": "รหัสผู้ป่วย/เลขบัตรประชาชน (CID/PID)", "label_en": "Patient ID / CID"},
    {"key": "sex", "label_th": "เพศ (Sex)", "label_en": "Sex"},
    {"key": "age_years", "label_th": "อายุ ปี (Age Years)", "label_en": "Age (Years)"},
    {"key": "age_months", "label_th": "อายุ เดือน (Age Months)", "label_en": "Age (Months)"},
    {"key": "nationality_raw", "label_th": "สัญชาติ (Nationality)", "label_en": "Nationality"},
    {"key": "onset_date", "label_th": "วันเริ่มป่วย (Onset Date)", "label_en": "Onset Date"},
    {"key": "report_date", "label_th": "วันที่ส่งรายงาน (Report Date)", "label_en": "Report Date"},
    {"key": "update_date", "label_th": "วันที่แก้ไขล่าสุด (Update Date)", "label_en": "Update Date"},
    {"key": "patient_type", "label_th": "ประเภทผู้ป่วย IPD/OPD (Patient Type)", "label_en": "Patient Type (IPD/OPD)"},
    {"key": "report_status", "label_th": "สถานะรายงาน (Approval Status)", "label_en": "Approval Status"},
    {"key": "patient_status", "label_th": "สภาพผู้ป่วย (Patient Outcome)", "label_en": "Patient Outcome"},
    {"key": "death_date", "label_th": "วันที่เสียชีวิต (Death Date)", "label_en": "Death Date"},
    {"key": "residence_province", "label_th": "รหัสจังหวัดที่อยู่ปัจจุบัน (Residence Province)", "label_en": "Residence Province Code"},
    {"key": "residence_district", "label_th": "รหัสอำเภอที่อยู่ปัจจุบัน (Residence District)", "label_en": "Residence District Code"},
    {"key": "illness_province", "label_th": "รหัสจังหวัดขณะป่วย (Illness Province)", "label_en": "Illness Province Code"},
    {"key": "illness_district", "label_th": "รหัสอำเภอขณะป่วย (Illness District)", "label_en": "Illness District Code"},
    {"key": "disease_group", "label_th": "รหัสกลุ่มโรค (Disease Code)", "label_en": "Disease Group Code"},
    {"key": "icd10", "label_th": "รหัส ICD-10", "label_en": "ICD-10 Code"},
]

THAI_MONTHS_MAP = {
    "ม.ค.": 1, "มกราคม": 1, "ก.พ.": 2, "กุมภาพันธ์": 2, "มี.ค.": 3, "มีนาคม": 3,
    "เม.ย.": 4, "เมษายน": 4, "พ.ค.": 5, "พฤษภาคม": 5, "มิ.ย.": 6, "มิถุนายน": 6,
    "ก.ค.": 7, "กรกฎาคม": 7, "ส.ค.": 8, "สิงหาคม": 8, "ก.ย.": 9, "กันยายน": 9,
    "ต.ค.": 10, "ตุลาคม": 10, "พ.ย.": 11, "พฤศจิกายน": 11, "ธ.ค.": 12, "ธันวาคม": 12,
}


def _is_empty_val(val: Any) -> bool:
    if val is None or pd.isna(val):
        return True
    s = str(val).strip()
    return s == "" or s.lower() in ("nan", "nat", "none", "null")


def parse_flexible_date(val: Any) -> Optional[datetime.date]:
    """
    Parses dates safely handling:
    - datetime.date / datetime.datetime
    - Excel serial numbers (e.g. 45658)
    - Strings with Gregorian (2025-05-12) or Buddhist Era (12/05/2568, 2568-05-12)
    - Never subtracts 543 from a date already stored correctly in Gregorian form!
    """
    if _is_empty_val(val):
        return None

    if isinstance(val, (datetime.date, datetime.datetime)):
        if isinstance(val, datetime.datetime):
            return val.date()
        return val

    if isinstance(val, (int, float)):
        try:
            if 30000 <= val <= 60000:
                return datetime.date(1899, 12, 30) + datetime.timedelta(days=int(val))
        except Exception:
            pass

    s = str(val).strip()
    if not s or s.lower() in ["nan", "nat", "none", "-", "null"]:
        return None

    # Check if string is a numeric Excel serial date
    if s.replace(".", "", 1).isdigit():
        try:
            num_v = float(s)
            if 30000 <= num_v <= 60000:
                return datetime.date(1899, 12, 30) + datetime.timedelta(days=int(num_v))
        except Exception:
            pass

    s_date = s.split(" ")[0].split("T")[0]

    iso_match = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", s_date)
    if iso_match:
        y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        if y >= 2400:
            y -= 543
        try:
            return datetime.date(y, m, d)
        except ValueError:
            return None

    dmy_match = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", s_date)
    if dmy_match:
        d, m, y = int(dmy_match.group(1)), int(dmy_match.group(2)), int(dmy_match.group(3))
        if y >= 2400:
            y -= 543
        try:
            return datetime.date(y, m, d)
        except ValueError:
            return None

    for th_m_name, m_num in THAI_MONTHS_MAP.items():
        if th_m_name in s:
            parts = s.replace(th_m_name, " ").split()
            if len(parts) >= 2:
                try:
                    d = int(parts[0])
                    y = int(parts[1])
                    if y >= 2400:
                        y -= 543
                    return datetime.date(y, m_num, d)
                except (ValueError, IndexError):
                    pass

    try:
        dt = pd.to_datetime(s_date, dayfirst=True)
        if not pd.isna(dt):
            d = dt.date()
            if d.year >= 2400:
                d = datetime.date(d.year - 543, d.month, d.day)
            return d
    except Exception:
        pass

    return None


def map_columns(df_columns: List[str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Maps detected Excel/CSV column names to standard canonical field names.
    Returns: (detected_to_std, std_to_detected)
    """
    detected_to_std: Dict[str, str] = {}
    std_to_detected: Dict[str, str] = {}

    col_clean_map = {c: str(c).strip().lower() for c in df_columns}

    for std_field, aliases in STANDARD_FIELD_ALIASES.items():
        matched_col = None
        for alias in aliases:
            alias_lower = alias.lower()
            for orig_col, clean_col in col_clean_map.items():
                if orig_col in detected_to_std:
                    continue
                if clean_col == alias_lower:
                    matched_col = orig_col
                    break
            if matched_col:
                break
        if not matched_col:
            for alias in aliases:
                alias_lower = alias.lower()
                for orig_col, clean_col in col_clean_map.items():
                    if orig_col in detected_to_std:
                        continue
                    if alias_lower in clean_col and len(alias_lower) >= 4:
                        matched_col = orig_col
                        break
                if matched_col:
                    break

        if matched_col:
            detected_to_std[matched_col] = std_field
            std_to_detected[std_field] = matched_col

    return detected_to_std, std_to_detected


def detect_file_category(df_columns: List[str], filename: str = "") -> str:
    """
    Classifies an uploaded file into one of 3 distinct categories:
    - 'cases': ข้อมูลผู้ป่วย (Patient surveillance records)
    - 'population': ข้อมูลประชากร (Population denominator data)
    - 'geography': ตารางรหัสพื้นที่ (Geographic code / crosswalk lookup)
    """
    cols_lower = [str(c).strip().lower() for c in df_columns]
    fname_lower = filename.lower()

    has_onset_or_pt = any(
        any(k in c for k in ["datesick", "onset", "วันเริ่มป่วย", "วันที่เริ่มป่วย", "patient_type", "ประเภทผู้ป่วย", "icd10", "รหัสกลุ่มโรค"])
        for c in cols_lower
    )
    if has_onset_or_pt:
        return "cases"

    has_pop = any(any(k in c for k in ["population", "ประชากร", "male_total", "female_total", "pop_total"]) for c in cols_lower)
    if has_pop or "pop" in fname_lower or "ประชากร" in fname_lower:
        return "population"

    has_geo_lookup = (
        any(any(k in c for k in ["district_name", "ชื่ออำเภอ", "amphur_name", "province_name", "ชื่อจังหวัด"]) for c in cols_lower)
        and any(any(k in c for k in ["district_code", "รหัสอำเภอ", "amphur_code", "province_code", "รหัสจังหวัด", "code"]) for c in cols_lower)
    )
    if has_geo_lookup or "crosswalk" in fname_lower or "รหัสพื้นที่" in fname_lower or "รหัสอำเภอ" in fname_lower:
        return "geography"

    return "cases"


def detect_csv_encoding_and_delimiter(
    raw_bytes: bytes,
    preferred_encoding: str = "auto",
    preferred_delimiter: str = "auto",
) -> Tuple[str, str, str]:
    """
    Detects CSV text encoding (supporting UTF-8 BOM, UTF-8, CP874/TIS-620) and delimiter.
    Returns (decoded_text, encoding_used, delimiter_used).
    """
    encoding_used = "utf-8"
    decoded_text = ""

    if preferred_encoding and preferred_encoding.lower() not in ("auto", ""):
        enc = preferred_encoding.lower()
        if enc == "tis-620":
            enc = "cp874"
        try:
            decoded_text = raw_bytes.decode(enc)
            encoding_used = preferred_encoding.lower()
        except UnicodeDecodeError:
            decoded_text = raw_bytes.decode(enc, errors="replace")
            encoding_used = preferred_encoding.lower()
    else:
        if raw_bytes.startswith(b"\xef\xbb\xbf"):
            decoded_text = raw_bytes.decode("utf-8-sig")
            encoding_used = "utf-8-sig"
        else:
            try:
                decoded_text = raw_bytes.decode("utf-8")
                encoding_used = "utf-8"
            except UnicodeDecodeError:
                decoded_text = raw_bytes.decode("cp874", errors="replace")
                encoding_used = "cp874"

    if preferred_delimiter and preferred_delimiter not in ("auto", ""):
        delim_used = "\t" if preferred_delimiter == "\\t" else preferred_delimiter
    else:
        sample_lines = "\n".join(decoded_text.splitlines()[:15])
        delim_used = ","
        try:
            dialect = csv.Sniffer().sniff(sample_lines, delimiters=[",", ";", "\t", "|"])
            delim_used = dialect.delimiter
        except Exception:
            # Count occurrences in header line
            first_line = decoded_text.splitlines()[0] if decoded_text.splitlines() else ""
            candidates = [(",", first_line.count(",")), (";", first_line.count(";")), ("\t", first_line.count("\t")), ("|", first_line.count("|"))]
            candidates.sort(key=lambda x: x[1], reverse=True)
            if candidates[0][1] > 0:
                delim_used = candidates[0][0]

    return decoded_text, encoding_used, delim_used


def read_dataframe_from_bytes(
    raw_bytes: bytes,
    filename: str,
    selected_sheet: Optional[str] = None,
    encoding: str = "auto",
    delimiter: str = "auto",
) -> Dict[str, Any]:
    """
    Reads an Excel (.xlsx/.xls) or CSV (.csv) file into a string-typed DataFrame
    preserving leading zeros on all codes and identifiers.
    For Excel, lists all sheets and reads ONLY the selected sheet (never auto-concatenates all sheets).
    """
    fname_lower = filename.lower()
    is_csv = fname_lower.endswith(".csv") or fname_lower.endswith(".tsv") or fname_lower.endswith(".txt")

    if is_csv:
        decoded_text, enc_used, delim_used = detect_csv_encoding_and_delimiter(
            raw_bytes, preferred_encoding=encoding, preferred_delimiter=delimiter
        )
        df = pd.read_csv(
            io.StringIO(decoded_text),
            sep=delim_used,
            dtype=str,
            keep_default_na=False,
            quotechar='"',
            skipinitialspace=True,
        )
        df.columns = [str(c).strip() for c in df.columns]
        return {
            "df": df,
            "file_format": "csv",
            "sheets": ["CSV"],
            "selected_sheet": "CSV",
            "encoding_used": enc_used,
            "delimiter_used": delim_used,
        }
    else:
        wb = pd.ExcelFile(io.BytesIO(raw_bytes))
        sheets = list(wb.sheet_names)
        sheet_to_read = selected_sheet if (selected_sheet and selected_sheet in sheets) else sheets[0]
        df = wb.parse(sheet_name=sheet_to_read, dtype=str, keep_default_na=False)
        df.columns = [str(c).strip() for c in df.columns]
        return {
            "df": df,
            "file_format": "xlsx",
            "sheets": sheets,
            "selected_sheet": sheet_to_read,
            "encoding_used": "excel",
            "delimiter_used": None,
        }


def classify_nationality(raw_val: Any) -> str:
    """
    Classifies nationality into Thai, Non-Thai, or Unknown.
    """
    if _is_empty_val(raw_val):
        return "Unknown"

    s = str(raw_val).strip()
    if not s or s.lower() in ["nan", "-", "none", "null", "ไม่ระบุ", "ไม่ทราบ", "อื่นๆ", "99", "0"]:
        return "Unknown"

    if any(k in s.lower() for k in ["ไทย", "thai", "thailand"]) or s in ("1", "01", "99_thai"):
        return "Thai"

    non_thai_keywords = [
        "พม่า", "myanmar", "burma", "burmese", "ลาว", "laos", "laotian",
        "กัมพูชา", "cambodia", "khmer", "เขมร", "เวียดนาม", "vietnam",
        "มาเลเซีย", "malaysia", "จีน", "china", "chinese", "ต่างชาติ",
        "foreign", "non-thai", "ม้ง", "กะเหรี่ยง",
    ]
    for k in non_thai_keywords:
        if k in s.lower():
            return "Non-Thai"

    return "Unknown"


def standardize_single_file_dataframe(
    raw_df: pd.DataFrame,
    source_file: str = "uploaded_file.xlsx",
    source_sheet: str = "Sheet1",
    custom_mappings: Optional[Dict[str, str]] = None,
    approved_statuses: Optional[List[Any]] = None,
    cancel_statuses: Optional[List[Any]] = None,
    import_seq_offset: int = 0,
) -> Dict[str, Any]:
    """
    Standardizes a single file's DataFrame into canonical columns with provenance
    (source_file, source_sheet, source_row) and episode_key/row_signature,
    ready for single-file or multi-file cross-file revision & duplicate resolution.
    """
    if approved_statuses is None:
        approved_statuses = [8, "8", 8.0, "8.0", "approved", "อนุมัติ", "ปกติ"]
    if cancel_statuses is None:
        cancel_statuses = [6, "6", 6.0, "6.0", "ยกเลิก", "cancelled", "cancel", "ซ้ำซ้อน"]

    total_rows_imported = len(raw_df)

    # Convert empty-string-only rows to NaN so dropna(how="all") strips trailing blank rows
    work_raw = raw_df.copy()
    work_raw["_orig_row_number"] = np.arange(2, len(work_raw) + 2)  # 1-based Excel/CSV row number (header is row 1)
    data_cols = [c for c in work_raw.columns if c != "_orig_row_number"]

    if data_cols:
        is_row_blank = work_raw[data_cols].apply(
            lambda r: all(_is_empty_val(v) for v in r), axis=1
        )
        non_blank_df = work_raw[~is_row_blank].copy()
    else:
        non_blank_df = work_raw.iloc[0:0].copy()

    trailing_blanks_removed = total_rows_imported - len(non_blank_df)

    detected_to_std, std_to_detected = map_columns(data_cols)
    if custom_mappings:
        # custom_mappings can be {source_col: canonical_field} or {canonical_field: source_col}
        for k, v in custom_mappings.items():
            if not v or str(v).lower() in ("none", "", "unmapped"):
                continue
            if k in data_cols and v in STANDARD_FIELD_ALIASES:
                detected_to_std[k] = v
                std_to_detected[v] = k
            elif k in STANDARD_FIELD_ALIASES and v in data_cols:
                # Remove old mapping for k if any
                old_src = std_to_detected.get(k)
                if old_src and old_src in detected_to_std:
                    del detected_to_std[old_src]
                detected_to_std[v] = k
                std_to_detected[k] = v

    std_df = pd.DataFrame(index=non_blank_df.index)
    std_df["source_file"] = str(source_file)
    std_df["source_sheet"] = str(source_sheet)
    std_df["source_row"] = non_blank_df["_orig_row_number"].astype(int)

    for std_field, orig_col in std_to_detected.items():
        if orig_col in non_blank_df.columns:
            std_df[std_field] = non_blank_df[orig_col]

    for f in ["cid", "sex", "age_years", "age_months", "onset_date", "patient_type", "report_status"]:
        if f not in std_df.columns:
            std_df[f] = None

    std_df["parsed_onset_date"] = std_df["onset_date"].apply(parse_flexible_date)
    std_df["parsed_diagnosis_date"] = std_df["diagnosis_date"].apply(parse_flexible_date) if "diagnosis_date" in std_df.columns else None
    std_df["parsed_treatment_date"] = std_df["treatment_date"].apply(parse_flexible_date) if "treatment_date" in std_df.columns else None
    std_df["parsed_report_date"] = std_df["report_date"].apply(parse_flexible_date) if "report_date" in std_df.columns else None
    std_df["parsed_update_date"] = std_df["update_date"].apply(parse_flexible_date) if "update_date" in std_df.columns else None
    std_df["parsed_death_date"] = std_df["death_date"].apply(parse_flexible_date) if "death_date" in std_df.columns else None

    # Fallback chain for analysis_date when onset_date is missing or unmapped in DDS exports:
    # onset_date -> diagnosis_date -> treatment_date -> report_date -> update_date
    onset_s = std_df["parsed_onset_date"]
    diag_s = std_df["parsed_diagnosis_date"] if "parsed_diagnosis_date" in std_df.columns else pd.Series([None] * len(std_df), index=std_df.index)
    treat_s = std_df["parsed_treatment_date"] if "parsed_treatment_date" in std_df.columns else pd.Series([None] * len(std_df), index=std_df.index)
    rep_s = std_df["parsed_report_date"] if "parsed_report_date" in std_df.columns else pd.Series([None] * len(std_df), index=std_df.index)
    upd_s = std_df["parsed_update_date"] if "parsed_update_date" in std_df.columns else pd.Series([None] * len(std_df), index=std_df.index)

    analysis_dates = []
    for o_d, dg_d, tr_d, rp_d, up_d in zip(onset_s, diag_s, treat_s, rep_s, upd_s):
        chosen = None
        for cand in (o_d, dg_d, tr_d, rp_d, up_d):
            if cand is not None and not pd.isna(cand):
                chosen = cand
                break
        analysis_dates.append(chosen)

    std_df["analysis_date"] = analysis_dates
    missing_onset_count = int(pd.Series(analysis_dates).isna().sum())

    epi_years, epi_weeks, week_starts, week_ends, onset_years = [], [], [], [], []
    for d in std_df["analysis_date"]:
        if d:
            ey, ew, ws, we = date_to_epi_week(d)
            epi_years.append(ey)
            epi_weeks.append(ew)
            week_starts.append(ws)
            week_ends.append(we)
            onset_years.append(d.year)
        else:
            epi_years.append(None)
            epi_weeks.append(None)
            week_starts.append(None)
            week_ends.append(None)
            onset_years.append(None)

    std_df["onset_year"] = onset_years
    std_df["epi_year"] = epi_years
    std_df["epi_week"] = epi_weeks
    std_df["week_start"] = week_starts
    std_df["week_end"] = week_ends

    def clean_patient_type(val):
        if _is_empty_val(val):
            return "Unknown"
        s = str(val).strip().upper()
        if s.endswith(".0"):
            s = s[:-2]
        if s in ["IPD", "ผู้ป่วยใน", "1", "01"]:
            return "IPD"
        elif s in ["OPD", "ผู้ป่วยนอก", "2", "02"]:
            return "OPD"
        return "Unknown"

    std_df["clean_patient_type"] = std_df["patient_type"].apply(clean_patient_type)

    def classify_outcome(death_dt, pat_status):
        if death_dt is not None and not pd.isna(death_dt):
            return "Dead"
        if _is_empty_val(pat_status):
            return "Unknown"
        s = str(pat_status).strip().lower()
        if s.endswith(".0"):
            s = s[:-2]
        if not s or s in ["nan", "none", "null", "-", "9", "99", "ไม่ทราบ", "ไม่ระบุ"]:
            return "Unknown"
        if any(k in s for k in ["เสียชีวิต", "ตาย", "dead", "died"]):
            return "Dead"
        if any(k in s for k in ["หาย", "รักษา", "มีชีวิต", "alive", "recovered"]) or s in ["1", "2", "01", "02"]:
            return "Alive"
        return "Unknown"

    p_stat_series = std_df["patient_status"] if "patient_status" in std_df.columns else [None] * len(std_df)
    std_df["clean_outcome_status"] = [
        classify_outcome(dd, ps) for dd, ps in zip(std_df["parsed_death_date"], p_stat_series)
    ]

    def clean_sex(val):
        if _is_empty_val(val):
            return "Unknown"
        s = str(val).strip()
        if s.endswith(".0"):
            s = s[:-2]
        if "ชาย" in s or s.lower() in ["m", "male", "1", "01"]:
            return "ชาย"
        elif "หญิง" in s or s.lower() in ["f", "female", "2", "02"]:
            return "หญิง"
        return "Unknown"

    std_df["clean_sex"] = std_df["sex"].apply(clean_sex)

    def clean_age(y_val, m_val):
        suspicious = False
        y = None
        m = None
        try:
            if not _is_empty_val(y_val):
                y = float(str(y_val).strip())
                if y < 0 or y > 120:
                    suspicious = True
        except (ValueError, TypeError):
            suspicious = True

        try:
            if not _is_empty_val(m_val):
                m = float(str(m_val).strip())
                if m < 0 or m > 12:
                    suspicious = True
        except (ValueError, TypeError):
            pass

        if y is not None and m is not None and y < 1.0:
            eff_age = round(m / 12.0, 2)
        elif y is not None:
            eff_age = y
        else:
            eff_age = None

        return eff_age, suspicious

    eff_ages, susp_flags = [], []
    for y_v, m_v in zip(std_df["age_years"], std_df["age_months"]):
        ea, sf = clean_age(y_v, m_v)
        eff_ages.append(ea)
        susp_flags.append(sf)

    std_df["clean_age_years"] = eff_ages
    std_df["is_suspicious_age"] = susp_flags
    std_df["age_band"] = std_df["clean_age_years"].apply(assign_age_band)

    std_df["nationality_group"] = (
        std_df["nationality_raw"].apply(classify_nationality)
        if "nationality_raw" in std_df.columns
        else "Unknown"
    )

    res_p_codes, res_p_th, res_p_en, res_d_codes, res_d_names_th, res_d_names_en, res_lookup = [], [], [], [], [], [], []
    for p_val, d_val in zip(
        std_df.get("residence_province", [None] * len(std_df)),
        std_df.get("residence_district", [None] * len(std_df)),
    ):
        p_c, d_c = construct_four_digit_district_code(p_val, d_val)
        info = get_district_info(d_c, p_c)
        res_p_codes.append(info["prov_code"])
        res_p_th.append(info["prov_name_th"])
        res_p_en.append(info["prov_name_en"])
        res_d_codes.append(info["code"])
        res_d_names_th.append(info["name_th"])
        res_d_names_en.append(info["name_en"])
        res_lookup.append(info["lookup_status"])

    std_df["residence_prov_code"] = res_p_codes
    std_df["residence_prov_name_th"] = res_p_th
    std_df["residence_prov_name_en"] = res_p_en
    std_df["residence_district_code"] = res_d_codes
    std_df["residence_district_name_th"] = res_d_names_th
    std_df["residence_district_name_en"] = res_d_names_en
    std_df["residence_lookup_status"] = res_lookup

    ill_p_codes, ill_p_th, ill_p_en, ill_d_codes, ill_d_names_th, ill_d_names_en, ill_lookup = [], [], [], [], [], [], []
    for p_val, d_val in zip(
        std_df.get("illness_province", [None] * len(std_df)),
        std_df.get("illness_district", [None] * len(std_df)),
    ):
        p_c, d_c = construct_four_digit_district_code(p_val, d_val)
        info = get_district_info(d_c, p_c)
        ill_p_codes.append(info["prov_code"])
        ill_p_th.append(info["prov_name_th"])
        ill_p_en.append(info["prov_name_en"])
        ill_d_codes.append(info["code"])
        ill_d_names_th.append(info["name_th"])
        ill_d_names_en.append(info["name_en"])
        ill_lookup.append(info["lookup_status"])

    std_df["illness_prov_code"] = ill_p_codes
    std_df["illness_prov_name_th"] = ill_p_th
    std_df["illness_prov_name_en"] = ill_p_en
    std_df["illness_district_code"] = ill_d_codes
    std_df["illness_district_name_th"] = ill_d_names_th
    std_df["illness_district_name_en"] = ill_d_names_en
    std_df["illness_lookup_status"] = ill_lookup

    def check_status(val):
        if _is_empty_val(val):
            return "missing"
        val_str = str(val).strip().lower()
        if val_str.endswith(".0"):
            val_str = val_str[:-2]
        for a in approved_statuses:
            if str(a).strip().lower() == val_str:
                return "approved"
        for c in cancel_statuses:
            if str(c).strip().lower() == val_str:
                return "cancelled"
        return "pending_or_other"

    std_df["status_category"] = std_df["report_status"].apply(check_status)
    std_df["import_seq"] = np.arange(import_seq_offset, import_seq_offset + len(std_df))

    # Build privacy-safe deterministic episode_key and exact row_signature
    episode_keys = []
    row_signatures = []
    for idx, row in std_df.iterrows():
        c_raw = str(row.get("cid", "")).strip()
        if c_raw.endswith(".0"):
            c_raw = c_raw[:-2]
        dz = str(row.get("disease_group") or row.get("icd10") or "DZ").strip()
        od = str(row.get("parsed_onset_date") or "NO_DATE").strip()

        if c_raw and c_raw.lower() not in ("nan", "none", "null", ""):
            cid_hash = hashlib.sha256(f"DDS_EPISODE::{c_raw}".encode("utf-8")).hexdigest()[:16]
            ep_key = f"EP_{cid_hash}_{dz}_{od}"
        else:
            # Deterministic content key when CID is absent so re-importing the same file still catches exact duplicates
            fallback_raw = (
                f"{dz}|{od}|{row.get('clean_sex')}|{row.get('clean_age_years')}|"
                f"{row.get('nationality_group')}|{row.get('residence_district_code')}|"
                f"{row.get('illness_district_code')}|{row.get('source_row')}"
            )
            fb_hash = hashlib.sha256(fallback_raw.encode("utf-8")).hexdigest()[:16]
            ep_key = f"NOCID_{fb_hash}"

        sig_raw = (
            f"{ep_key}|{row.get('clean_patient_type')}|{row.get('clean_outcome_status')}|"
            f"{row.get('status_category')}|{row.get('parsed_update_date')}|{row.get('parsed_report_date')}|"
            f"{row.get('residence_district_code')}|{row.get('illness_district_code')}"
        )
        sig_hash = hashlib.sha256(sig_raw.encode("utf-8")).hexdigest()[:20]
        episode_keys.append(ep_key)
        row_signatures.append(sig_hash)

    std_df["episode_key"] = episode_keys
    std_df["row_signature"] = row_signatures
    std_df["sort_dt"] = (
        std_df["parsed_update_date"]
        .fillna(std_df["parsed_report_date"])
        .fillna(datetime.date(1970, 1, 1))
    )

    return {
        "standardized_df": std_df,
        "total_rows_imported": total_rows_imported,
        "trailing_blanks_removed": trailing_blanks_removed,
        "non_empty_records": len(std_df),
        "missing_onset_count": missing_onset_count,
        "detected_mappings": detected_to_std,
        "std_to_detected": std_to_detected,
    }


def resolve_combined_standardized_dataframe(
    combined_std_df: pd.DataFrame,
    total_rows_imported: int,
    trailing_blanks_removed: int,
    detected_mappings: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Resolves exact duplicates and cross-file revisions across a combined standardized DataFrame:
    1. Collapses exact duplicate records (e.g. re-importing the same file or identical overlapping rows)
       so re-importing the same file never silently inflates case counts.
    2. Resolves authoritative revisions per episode_key (sorted by sort_dt DESC, import_seq DESC)
       BEFORE filtering by approval status so a later cancelled record (status 6) in another file
       cancels an earlier approved record (status 8).
    3. Preserves source_file, source_sheet, and source_row for full provenance auditability.
    """
    if combined_std_df.empty:
        empty_audit = {
            "total_rows_imported": total_rows_imported,
            "trailing_blanks_removed": trailing_blanks_removed,
            "non_empty_records": 0,
            "exact_duplicates_removed": 0,
            "superseded_revisions_removed": 0,
            "authoritative_episodes_total": 0,
            "cancelled_episodes_excluded": 0,
            "pending_or_other_excluded": 0,
            "missing_status_excluded": 0,
            "used_fallback_approval": False,
            "eligible_episodes_C": 0,
            "ipd_episodes_H": 0,
            "opd_episodes_O": 0,
            "unknown_patient_type_U": 0,
            "patient_type_missing_pct": 0.0,
            "suspicious_age_count": 0,
            "missing_onset_date_count": 0,
            "recorded_deaths_count": 0,
            "known_alive_count": 0,
            "unknown_outcome_count": 0,
            "source_files_summary": [],
        }
        return {
            "cleaned_df": pd.DataFrame(),
            "authoritative_df": pd.DataFrame(),
            "audit_trail": empty_audit,
            "detected_mappings": detected_mappings or {},
        }

    total_non_empty = len(combined_std_df)

    # Step A: Remove exact duplicate rows (identical episode_key & row_signature across or within files),
    # keeping the earliest imported instance so provenance credits the original file.
    dedup_order_df = combined_std_df.sort_values(
        by=["import_seq"], ascending=[True]
    ).copy()
    after_exact_df = dedup_order_df.drop_duplicates(subset=["episode_key", "row_signature"], keep="first").copy()
    exact_duplicates_removed = total_non_empty - len(after_exact_df)

    # Step B: Resolve authoritative revision per episode_key across all files (latest update/report date & latest import_seq wins)
    sorted_df = after_exact_df.sort_values(
        by=["sort_dt", "import_seq"], ascending=[False, False]
    ).copy()
    authoritative_df = sorted_df.drop_duplicates(subset=["episode_key"], keep="first").copy()
    superseded_revisions_only = len(after_exact_df) - len(authoritative_df)
    total_revisions_and_dups_removed = total_non_empty - len(authoritative_df)

    # Step C: Filter by approval status (status 6 cancelled cannot be resurrected!)
    approved_episodes_df = authoritative_df[authoritative_df["status_category"] == "approved"].copy()
    cancelled_episodes_count = int((authoritative_df["status_category"] == "cancelled").sum())
    pending_episodes_count = int((authoritative_df["status_category"] == "pending_or_other").sum())
    missing_status_count = int((authoritative_df["status_category"] == "missing").sum())

    used_fallback_approval = False
    if len(approved_episodes_df) == 0 and len(authoritative_df) > 0:
        approved_episodes_df = authoritative_df[authoritative_df["status_category"] != "cancelled"].copy()
        used_fallback_approval = True

    approved_episodes_df["temp_id"] = np.arange(1, len(approved_episodes_df) + 1)

    eligible_episodes = len(approved_episodes_df)
    ipd_count = int((approved_episodes_df["clean_patient_type"] == "IPD").sum()) if eligible_episodes > 0 else 0
    opd_count = int((approved_episodes_df["clean_patient_type"] == "OPD").sum()) if eligible_episodes > 0 else 0
    unknown_type_count = int((approved_episodes_df["clean_patient_type"] == "Unknown").sum()) if eligible_episodes > 0 else 0

    recorded_deaths = int((approved_episodes_df["clean_outcome_status"] == "Dead").sum()) if eligible_episodes > 0 else 0
    alive_outcomes = int((approved_episodes_df["clean_outcome_status"] == "Alive").sum()) if eligible_episodes > 0 else 0
    unknown_outcomes = int((approved_episodes_df["clean_outcome_status"] == "Unknown").sum()) if eligible_episodes > 0 else 0
    missing_onset_count = int(approved_episodes_df["parsed_onset_date"].isna().sum()) if eligible_episodes > 0 else 0

    # Per-source-file breakdown for auditability
    source_files_summary = []
    if "source_file" in combined_std_df.columns:
        for (sf, ss), grp in combined_std_df.groupby(["source_file", "source_sheet"], dropna=False):
            elig_in_src = int(
                ((approved_episodes_df["source_file"] == sf) & (approved_episodes_df["source_sheet"] == ss)).sum()
            ) if eligible_episodes > 0 else 0
            source_files_summary.append({
                "source_file": str(sf),
                "source_sheet": str(ss),
                "non_empty_rows": len(grp),
                "eligible_contributed": elig_in_src,
                "duplicates_or_excluded": len(grp) - elig_in_src,
            })

    audit_trail = {
        "total_rows_imported": total_rows_imported,
        "trailing_blanks_removed": trailing_blanks_removed,
        "non_empty_records": total_non_empty,
        "exact_duplicates_removed": exact_duplicates_removed,
        "cross_file_revisions_superseded": superseded_revisions_only,
        "superseded_revisions_removed": total_revisions_and_dups_removed,
        "authoritative_episodes_total": len(authoritative_df),
        "cancelled_episodes_excluded": cancelled_episodes_count,
        "pending_or_other_excluded": pending_episodes_count if not used_fallback_approval else 0,
        "missing_status_excluded": missing_status_count if not used_fallback_approval else 0,
        "used_fallback_approval": used_fallback_approval,
        "eligible_episodes_C": eligible_episodes,
        "ipd_episodes_H": ipd_count,
        "opd_episodes_O": opd_count,
        "unknown_patient_type_U": unknown_type_count,
        "patient_type_missing_pct": round((unknown_type_count / eligible_episodes * 100.0), 2) if eligible_episodes > 0 else 0.0,
        "suspicious_age_count": int(approved_episodes_df["is_suspicious_age"].sum()) if eligible_episodes > 0 else 0,
        "missing_onset_date_count": missing_onset_count,
        "recorded_deaths_count": recorded_deaths,
        "known_alive_count": alive_outcomes,
        "unknown_outcome_count": unknown_outcomes,
        "source_files_summary": source_files_summary,
    }

    clean_cols_to_keep = [
        "temp_id",
        "source_file",
        "source_sheet",
        "source_row",
        "episode_key",
        "row_signature",
        "sort_dt",
        "import_seq",
        "clean_sex",
        "clean_age_years",
        "age_band",
        "is_suspicious_age",
        "nationality_group",
        "clean_patient_type",
        "clean_outcome_status",
        "parsed_onset_date",
        "analysis_date",
        "onset_year",
        "epi_year",
        "epi_week",
        "week_start",
        "week_end",
        "residence_prov_code",
        "residence_prov_name_th",
        "residence_prov_name_en",
        "residence_district_code",
        "residence_district_name_th",
        "residence_district_name_en",
        "residence_lookup_status",
        "illness_prov_code",
        "illness_prov_name_th",
        "illness_prov_name_en",
        "illness_district_code",
        "illness_district_name_th",
        "illness_district_name_en",
        "illness_lookup_status",
        "disease_group",
        "icd10",
        "status_category",
        "parsed_death_date",
        "parsed_update_date",
        "parsed_report_date",
    ]
    final_cols = [c for c in clean_cols_to_keep if c in approved_episodes_df.columns]
    anonymized_cleaned_df = approved_episodes_df[final_cols].copy()

    auth_cols = [c for c in clean_cols_to_keep if c in authoritative_df.columns]
    kept_authoritative_df = authoritative_df[auth_cols].copy()

    return {
        "cleaned_df": anonymized_cleaned_df,
        "authoritative_df": kept_authoritative_df,
        "audit_trail": audit_trail,
        "detected_mappings": detected_mappings or {},
    }


def process_dds_dataframe(
    raw_df: pd.DataFrame,
    custom_mappings: Optional[Dict[str, str]] = None,
    approved_statuses: Optional[List[Any]] = None,
    cancel_statuses: Optional[List[Any]] = None,
    source_file: str = "uploaded_dds.xlsx",
    source_sheet: str = "Sheet1",
) -> Dict[str, Any]:
    """
    Single-file convenience wrapper around standardize_single_file_dataframe
    and resolve_combined_standardized_dataframe.
    """
    single = standardize_single_file_dataframe(
        raw_df=raw_df,
        source_file=source_file,
        source_sheet=source_sheet,
        custom_mappings=custom_mappings,
        approved_statuses=approved_statuses,
        cancel_statuses=cancel_statuses,
        import_seq_offset=0,
    )
    resolved = resolve_combined_standardized_dataframe(
        combined_std_df=single["standardized_df"],
        total_rows_imported=single["total_rows_imported"],
        trailing_blanks_removed=single["trailing_blanks_removed"],
        detected_mappings=single["detected_mappings"],
    )
    resolved["std_to_detected"] = single["std_to_detected"]
    return resolved


class MultiFileImportStageManager:
    """
    Manages staged files in the multi-file import queue before user confirmation.
    Supports mixed .xlsx and .csv files, per-file sheet selection, encoding/delimiter options,
    column mapping customization, file category separation ('cases', 'population', 'geography'),
    and impact preview ('replace' vs 'append').
    """

    def __init__(self):
        self._staged: Dict[str, Dict[str, Any]] = {}

    def stage_file(
        self,
        raw_bytes: bytes,
        filename: str,
        selected_sheet: Optional[str] = None,
        encoding: str = "auto",
        delimiter: str = "auto",
        file_category: Optional[str] = None,
        custom_mappings: Optional[Dict[str, str]] = None,
        staged_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        sid = staged_id or f"stg_{uuid.uuid4().hex[:10]}"
        parsed = read_dataframe_from_bytes(
            raw_bytes=raw_bytes,
            filename=filename,
            selected_sheet=selected_sheet,
            encoding=encoding,
            delimiter=delimiter,
        )
        df = parsed["df"]
        cols = list(df.columns)

        # Count non-empty rows
        if len(cols) > 0 and not df.empty:
            is_blank = df.apply(lambda r: all(_is_empty_val(v) for v in r), axis=1)
            non_empty_df = df[~is_blank]
        else:
            non_empty_df = df.iloc[0:0]

        total_rows = len(df)
        non_empty_rows = len(non_empty_df)
        trailing_blanks = total_rows - non_empty_rows

        detected_cat = file_category or detect_file_category(cols, filename)
        detected_to_std, std_to_detected = map_columns(cols)
        if custom_mappings:
            for k, v in custom_mappings.items():
                if not v or str(v).lower() in ("none", "", "unmapped"):
                    continue
                if k in STANDARD_FIELD_ALIASES and v in cols:
                    std_to_detected[k] = v
                    detected_to_std[v] = k
                elif k in cols and v in STANDARD_FIELD_ALIASES:
                    detected_to_std[k] = v
                    std_to_detected[v] = k

        # Build issues/warnings list
        issues: List[Dict[str, str]] = []
        if non_empty_rows == 0:
            issues.append({
                "level": "error",
                "message_th": "ไฟล์หรือชีตนี้ไม่มีแถวข้อมูลที่มีเนื้อหา",
                "message_en": "No non-empty rows found in this file/sheet",
            })
        if detected_cat == "cases":
            if "onset_date" not in std_to_detected:
                issues.append({
                    "level": "warning",
                    "message_th": "ยังไม่พบคอลัมน์ 'วันเริ่มป่วย (onset_date)' กรุณาจับคู่คอลัมน์ก่อนยืนยัน",
                    "message_en": "Onset date column not mapped yet; please map it before confirming",
                })
            if "residence_province" not in std_to_detected and "illness_province" not in std_to_detected:
                issues.append({
                    "level": "warning",
                    "message_th": "ยังไม่พบคอลัมน์รหัสจังหวัด (ที่อยู่ปัจจุบันหรือขณะป่วย)",
                    "message_en": "Province code column not mapped yet",
                })
        elif detected_cat == "population":
            issues.append({
                "level": "info",
                "message_th": "จำแนกเป็น 'ข้อมูลประชากร' — จะอัปเดตตารางตัวหารประชากรแยกต่างหาก (ไม่นำไปต่อแถวกับข้อมูลผู้ป่วย)",
                "message_en": "Classified as 'Population Data' — updates denominator lookup only (never appended to patient rows)",
            })
        elif detected_cat == "geography":
            issues.append({
                "level": "info",
                "message_th": "จำแนกเป็น 'ตารางรหัสพื้นที่' — จะอัปเดตตารางอ้างอิงรหัสพื้นที่แยกต่างหาก (ไม่นำไปต่อแถวกับข้อมูลผู้ป่วย)",
                "message_en": "Classified as 'Geography Code Table' — updates code crosswalk only (never appended to patient rows)",
            })

        if parsed["file_format"] == "xlsx" and len(parsed["sheets"]) > 1:
            issues.append({
                "level": "info",
                "message_th": f"ไฟล์ Excel มี {len(parsed['sheets'])} ชีต ระบบเลือกเฉพาะชีต '{parsed['selected_sheet']}' (ไม่รวมทุกชีตอัตโนมัติ)",
                "message_en": f"Excel workbook has {len(parsed['sheets'])} sheets; only '{parsed['selected_sheet']}' will be imported",
            })

        preview_rows = non_empty_df.head(5).to_dict(orient="records")

        item = {
            "staged_id": sid,
            "filename": filename,
            "raw_bytes": raw_bytes,
            "file_format": parsed["file_format"],
            "file_category": detected_cat,
            "sheets": parsed["sheets"],
            "selected_sheet": parsed["selected_sheet"],
            "encoding": encoding,
            "encoding_used": parsed["encoding_used"],
            "delimiter": delimiter,
            "delimiter_used": parsed["delimiter_used"],
            "total_rows": total_rows,
            "non_empty_rows": non_empty_rows,
            "trailing_blanks": trailing_blanks,
            "columns": cols,
            "std_to_detected": std_to_detected,
            "detected_to_std": detected_to_std,
            "preview_rows": preview_rows,
            "issues": issues,
            "status": "ready" if non_empty_rows > 0 else "empty",
        }
        self._staged[sid] = item
        return self.serialize_item(item)

    def update_staged_item(
        self,
        staged_id: str,
        selected_sheet: Optional[str] = None,
        encoding: Optional[str] = None,
        delimiter: Optional[str] = None,
        file_category: Optional[str] = None,
        custom_mappings: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if staged_id not in self._staged:
            raise KeyError(f"Staged item {staged_id} not found")
        cur = self._staged[staged_id]
        return self.stage_file(
            raw_bytes=cur["raw_bytes"],
            filename=cur["filename"],
            selected_sheet=selected_sheet if selected_sheet is not None else cur["selected_sheet"],
            encoding=encoding if encoding is not None else cur["encoding"],
            delimiter=delimiter if delimiter is not None else cur["delimiter"],
            file_category=file_category if file_category is not None else cur["file_category"],
            custom_mappings=custom_mappings if custom_mappings is not None else cur["std_to_detected"],
            staged_id=staged_id,
        )

    def remove_staged_item(self, staged_id: str) -> bool:
        return self._staged.pop(staged_id, None) is not None

    def clear_all(self) -> None:
        self._staged.clear()

    def get_staged_items(self, staged_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if staged_ids is not None:
            return [self._staged[sid] for sid in staged_ids if sid in self._staged]
        return list(self._staged.values())

    def list_serialized_queue(self) -> List[Dict[str, Any]]:
        return [self.serialize_item(it) for it in self._staged.values()]

    @staticmethod
    def serialize_item(item: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in item.items() if k != "raw_bytes"}


def ensure_dataframe_dates_and_epi_weeks(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures that a DataFrame (including one loaded from disk or with missing onset_date)
    has valid datetime.date objects in parsed_*_date and analysis_date, and populates
    onset_year, epi_year, epi_week, week_start, week_end using the fallback chain:
    parsed_onset_date -> parsed_diagnosis_date -> parsed_treatment_date -> parsed_report_date -> parsed_update_date.
    """
    if df is None or df.empty:
        return df

    work = df.copy()
    date_pairs = [
        ("parsed_onset_date", "onset_date"),
        ("parsed_diagnosis_date", "diagnosis_date"),
        ("parsed_treatment_date", "treatment_date"),
        ("parsed_report_date", "report_date"),
        ("parsed_update_date", "update_date"),
        ("parsed_death_date", "death_date"),
    ]
    for parsed_col, raw_col in date_pairs:
        if parsed_col in work.columns:
            work[parsed_col] = work[parsed_col].apply(parse_flexible_date)
        elif raw_col in work.columns:
            work[parsed_col] = work[raw_col].apply(parse_flexible_date)
        else:
            work[parsed_col] = None

    if "analysis_date" in work.columns:
        work["analysis_date"] = work["analysis_date"].apply(parse_flexible_date)
    else:
        work["analysis_date"] = None

    # Backfill analysis_date where missing
    fallback_cols = [
        "analysis_date",
        "parsed_onset_date",
        "parsed_diagnosis_date",
        "parsed_treatment_date",
        "parsed_report_date",
        "parsed_update_date",
    ]
    available_fb = [c for c in fallback_cols if c in work.columns]
    resolved_dates: List[Optional[datetime.date]] = []
    for idx in range(len(work)):
        chosen = None
        for c in available_fb:
            val = work[c].iloc[idx]
            if isinstance(val, datetime.date):
                chosen = val
                break
        resolved_dates.append(chosen)

    work["analysis_date"] = resolved_dates

    # Recompute epi_year, epi_week, week_start, week_end, onset_year whenever any are missing
    epi_years, epi_weeks, week_starts, week_ends, onset_years = [], [], [], [], []
    for d in resolved_dates:
        if isinstance(d, datetime.date):
            ey, ew, ws, we = date_to_epi_week(d)
            epi_years.append(ey)
            epi_weeks.append(ew)
            week_starts.append(ws)
            week_ends.append(we)
            onset_years.append(d.year)
        else:
            epi_years.append(None)
            epi_weeks.append(None)
            week_starts.append(None)
            week_ends.append(None)
            onset_years.append(None)

    work["onset_year"] = onset_years
    work["epi_year"] = epi_years
    work["epi_week"] = epi_weeks
    work["week_start"] = week_starts
    work["week_end"] = week_ends

    # Ensure numeric/string columns from CSV are properly typed
    if "clean_age_years" in work.columns:
        work["clean_age_years"] = pd.to_numeric(work["clean_age_years"], errors="coerce")
    for p_col in ("residence_prov_code", "illness_prov_code"):
        if p_col in work.columns:
            work[p_col] = work[p_col].apply(
                lambda x: str(x).strip().split(".")[0].zfill(2)
                if (x is not None and not pd.isna(x) and str(x).strip().replace(".0", "").isdigit())
                else ("Unknown" if _is_empty_val(x) else str(x).strip())
            )
    for d_col in ("residence_district_code", "illness_district_code"):
        if d_col in work.columns:
            work[d_col] = work[d_col].apply(
                lambda x: str(x).strip().split(".")[0].zfill(4)
                if (x is not None and not pd.isna(x) and str(x).strip().replace(".0", "").isdigit())
                else ("Unknown" if _is_empty_val(x) else str(x).strip())
            )

    return work


import_stage_manager = MultiFileImportStageManager()
