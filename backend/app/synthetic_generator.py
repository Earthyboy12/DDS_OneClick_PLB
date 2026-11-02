import os
import random
import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np

from app.config import FIXTURES_DIR

# 48 DDS Reference Column Names
DDS_COLUMNS = [
    "CID",
    "sex",
    "year", # Age in completed years!
    "month", # Age months
    "race",
    "occupat",
    "prov_code",
    "รหัสอำเภอ(ที่อยู่ปัจจุบัน)",
    "รหัสตำบล(ที่อยู่ปัจจุบัน)",
    "จังหวัดขณะป่วย",
    "อำเภอขณะป่วย",
    "ตำบลขณะป่วย",
    "Province_code",
    "datesick", # Symptom onset date
    "date_tx",
    "datedefine",
    "วันที่ส่งรายงาน",
    "วันที่ Update",
    "รหัสกลุ่มโรค",
    "Diagnosis ICD10",
    "diagnosis_icd10_list",
    "type", # IPD, OPD, opd, missing
    "รหัสสภาพผู้ป่วย",
    "สภาพผู้ป่วย",
    "วันที่เสียชีวิต",
    "สาเหตุการเสียชีวิต",
    "status", # 8=approved, 6=cancelled, 2=pending
    "สถานะ",
    "ความรุนแรง",
    "ใส่เครื่องช่วยหายใจ",
    "complication",
    "organism",
    "HOSPCODE",
    "HOSPNAME",
    "address_no",
    "moo",
    "road",
    "marry",
    "lab_result",
    "lab_date",
    "approver_name",
    "date_approve",
    "note",
    "extra_col1",
    "extra_col2",
    "extra_col3",
    "extra_col4",
    "extra_col5"
]

PHITSANULOK_DISTRICT_CODES = ["01", "02", "03", "04", "05", "06", "07", "08", "09"]
DISTRICT_WEIGHTS = [0.35, 0.12, 0.08, 0.11, 0.07, 0.09, 0.05, 0.08, 0.05]

def generate_synthetic_dds_workbook(
    file_path: Path,
    n_records: int = 20172,
    trailing_blanks: int = 150,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Generates a realistic synthetic DDS workbook mimicking the real surveillance export:
    - Exactly 48 columns
    - Approximately 20,172 non-empty records + trailing blank rows
    - Dates spanning January - November 2025
    - ~52.33% missing patient type
    - Normalized OPD/opd mix
    - Report status: 8 (approved, ~92%), 6 (cancelled/duplicate, ~5%), 2 (pending, ~3%)
    - Sparse death information (~12 deaths, mostly in cancelled/pending records)
    - Mixed nationality strings: Thai ('ไทย', '1'), Non-Thai ('พม่า', 'ลาว', 'กัมพูชา'), Unknown ('-', '99', 'ไม่ระบุ')
    - Suspicious ages (~0.8% with year > 120 or negative)
    - Revisions with duplicate CID/disease/onset where later update exists
    - Both Gregorian and Buddhist Era dates in string format
    """
    random.seed(seed)
    np.random.seed(seed)

    start_date = datetime.date(2025, 1, 1)
    end_date = datetime.date(2025, 11, 25)
    date_range_days = (end_date - start_date).days

    records = []
    
    # We will generate ~19,200 unique episodes, plus ~972 revision/duplicate records to reach n_records
    n_base = n_records - 972

    cids_pool = [f"{random.randint(1000000000000, 9999999999999)}" for _ in range(n_base)]
    
    occupations = ["เกษตรกร", "รับจ้างทั่วไป", "นักเรียน/นักศึกษา", "ค้าขาย", "ข้าราชการ/รัฐวิสาหกิจ", "เด็กในปกครอง", "ว่างงาน"]
    occ_weights = [0.28, 0.25, 0.18, 0.12, 0.07, 0.06, 0.04]

    for i in range(n_base):
        cid = cids_pool[i]
        
        # Sex: ชาย (~51%), หญิง (~49%)
        sex = "ชาย" if random.random() < 0.51 else "หญิง"
        
        # Age distribution realistic for endemic surveillance (bimodal: children & older adults)
        r = random.random()
        if r < 0.22:
            # Young children 0-9
            y_age = random.randint(0, 9)
            m_age = random.randint(0, 11) if y_age == 0 else 0
        elif r < 0.40:
            # School age & young adults 10-24
            y_age = random.randint(10, 24)
            m_age = 0
        elif r < 0.75:
            # Adults 25-59
            y_age = random.randint(25, 59)
            m_age = 0
        else:
            # Elderly 60-95
            y_age = random.randint(60, 92)
            m_age = 0

        # Inject a few suspicious ages (<0.8%)
        if random.random() < 0.006:
            y_age = random.choice([145, 160, -3, 999])

        # Nationality mix
        # Thai ~88%, Non-Thai ~7%, Unknown ~5%
        nat_r = random.random()
        if nat_r < 0.88:
            race = random.choice(["ไทย", "ไทย", "1", "01", "สัญชาติไทย"])
        elif nat_r < 0.95:
            race = random.choice(["พม่า", "ลาว", "กัมพูชา", "จีน", "ต่างชาติ"])
        else:
            race = random.choice(["-", "ไม่ระบุ", "99", "อื่นๆ", "0", ""])

        # Residence Geography: Phitsanulok 65
        prov_code = "65"
        dist_code = random.choices(PHITSANULOK_DISTRICT_CODES, weights=DISTRICT_WEIGHTS)[0]
        tam_code = f"{dist_code}{random.randint(1, 10):02d}"

        # Illness Geography: ~92% same, ~8% neighbouring province or other district
        if random.random() < 0.92:
            ill_prov = prov_code
            ill_dist = dist_code
            ill_tam = tam_code
        else:
            ill_prov = random.choice(["65", "64", "67", "53", "66"])
            ill_dist = f"{random.randint(1, 8):02d}"
            ill_tam = f"{ill_dist}01"

        # Onset Date (January - November 2025)
        # Add seasonal peak around June - August (monsoon / dengue peak)
        month_weights = [0.05, 0.05, 0.06, 0.07, 0.10, 0.16, 0.20, 0.14, 0.08, 0.05, 0.04]
        target_month = random.choices(range(1, 12), weights=month_weights)[0]
        day = random.randint(1, 28)
        onset_dt = datetime.date(2025, target_month, day)

        # Formats: 60% Gregorian YYYY-MM-DD, 30% Buddhist Era DD/MM/YYYY, 10% Excel serial format
        fmt_choice = random.random()
        if fmt_choice < 0.60:
            onset_str = onset_dt.isoformat()
        elif fmt_choice < 0.90:
            be_year = onset_dt.year + 543
            onset_str = f"{onset_dt.day:02d}/{onset_dt.month:02d}/{be_year}"
        else:
            # Excel serial number
            excel_serial = (onset_dt - datetime.date(1899, 12, 30)).days
            onset_str = excel_serial

        # Report Date: 1 to 5 days after onset
        lag_days = random.randint(1, 5)
        report_dt = onset_dt + datetime.timedelta(days=lag_days)
        report_str = f"{report_dt.isoformat()} 09:30:00"

        # Update Date
        update_str = report_str

        # Disease Group & ICD10
        disease_group = "01" # Surveillance code (e.g. Dengue / Respiratory / Diarrhea)
        icd10 = random.choice(["A09", "A09.0", "A09.9", "B54", "A90", "A91"])

        # Patient Type (~52.33% missing!)
        # Of known ~47.67%: ~22% IPD, ~78% OPD (mix of 'OPD', 'opd', 'IPD')
        pt_r = random.random()
        if pt_r < 0.5233:
            patient_type = None # Missing!
        elif pt_r < 0.628:
            patient_type = "IPD"
        else:
            patient_type = random.choice(["OPD", "OPD", "opd"])

        # Report Status: 8 = approved (~92%), 6 = cancelled (~5%), 2 = pending (~3%)
        st_r = random.random()
        if st_r < 0.92:
            status_val = 8
            status_text = "อนุมัติ"
        elif st_r < 0.97:
            status_val = 6
            status_text = "ยกเลิก"
        else:
            status_val = 2
            status_text = "รอการแก้ไข"

        # Death info: very sparse, mostly occurs in cancelled or pending records
        death_dt_str = None
        death_cause = None
        if status_val != 8 and random.random() < 0.015:
            d_death = onset_dt + datetime.timedelta(days=random.randint(3, 10))
            death_dt_str = d_death.isoformat()
            death_cause = "Septicemia"

        records.append({
            "CID": cid,
            "sex": sex,
            "year": y_age,
            "month": m_age,
            "race": race,
            "occupat": random.choices(occupations, weights=occ_weights)[0],
            "prov_code": prov_code,
            "รหัสอำเภอ(ที่อยู่ปัจจุบัน)": dist_code,
            "รหัสตำบล(ที่อยู่ปัจจุบัน)": tam_code,
            "จังหวัดขณะป่วย": ill_prov,
            "อำเภอขณะป่วย": ill_dist,
            "ตำบลขณะป่วย": ill_tam,
            "Province_code": prov_code,
            "datesick": onset_str,
            "date_tx": onset_str,
            "datedefine": onset_str,
            "วันที่ส่งรายงาน": report_str,
            "วันที่ Update": update_str,
            "รหัสกลุ่มโรค": disease_group,
            "Diagnosis ICD10": icd10,
            "diagnosis_icd10_list": icd10,
            "type": patient_type,
            "รหัสสภาพผู้ป่วย": 1 if death_dt_str else 2,
            "สภาพผู้ป่วย": "เสียชีวิต" if death_dt_str else "หาย",
            "วันที่เสียชีวิต": death_dt_str,
            "สาเหตุการเสียชีวิต": death_cause,
            "status": status_val,
            "สถานะ": status_text,
            "ความรุนแรง": "ปานกลาง",
            "ใส่เครื่องช่วยหายใจ": "ไม่ใส่",
            "complication": "-",
            "organism": "-",
            "HOSPCODE": "10670",
            "HOSPNAME": "โรงพยาบาลศูนย์พิษณุโลก",
            "address_no": f"{random.randint(1, 200)}",
            "moo": f"{random.randint(1, 15)}",
            "road": "-",
            "marry": "สมรส",
            "lab_result": "Positive",
            "lab_date": onset_str,
            "approver_name": "เจ้าหน้าที่ สสจ.",
            "date_approve": report_str,
            "note": "สังเคราะห์เพื่อการทดสอบระบบ (Synthetic)",
            "extra_col1": None,
            "extra_col2": None,
            "extra_col3": None,
            "extra_col4": None,
            "extra_col5": None,
        })

    # Add ~972 revision/duplicate records
    for i in range(972):
        base_rec = random.choice(records[:1000]).copy()
        # Older version of an approved report that was updated, or a later cancellation
        base_rec["temp_rev_flag"] = True
        if random.random() < 0.5:
            # Earlier report date (superseded)
            base_rec["วันที่ Update"] = "2025-01-01 08:00:00"
            base_rec["status"] = 8
        else:
            # Later update where report was cancelled (code 6)
            base_rec["วันที่ Update"] = "2025-11-28 10:00:00"
            base_rec["status"] = 6
            base_rec["สถานะ"] = "ยกเลิก"
        records.append(base_rec)

    # Convert to DataFrame
    df = pd.DataFrame(records)
    if "temp_rev_flag" in df.columns:
        df = df.drop(columns=["temp_rev_flag"])

    # Ensure all 48 columns exist in exact order
    for c in DDS_COLUMNS:
        if c not in df.columns:
            df[c] = None
    df = df[DDS_COLUMNS]

    # Add trailing blank rows (e.g. 150 blank rows)
    blank_rows = pd.DataFrame([{c: None for c in DDS_COLUMNS} for _ in range(trailing_blanks)])
    final_df = pd.concat([df, blank_rows], ignore_index=True)

    # Save to Excel
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        final_df.to_excel(writer, sheet_name="DDS_DATA", index=False)

    return {
        "file_path": str(file_path),
        "total_rows": len(final_df),
        "non_empty_rows": len(df),
        "trailing_blanks": trailing_blanks,
        "columns_count": len(DDS_COLUMNS),
        "df": final_df,
    }


def generate_synthetic_population_workbook(
    file_path: Path
) -> Dict[str, Any]:
    """
    Generates a realistic DOPA population Excel workbook matching official Thai format:
    - Multiple sheets: '1_6712' (Dec 2024), '1_6811' (Nov 2025)
    - Province code 0 as national aggregate (must not be added to provincial sum)
    - Province code 65 (Phitsanulok) with single-year age columns: '<1', '1', '2', ..., '100', '>100'
    - Male and female counts
    - 'รวม 0-5 ปี' subtotal column (must not be double-counted)
    - Intentional identical duplicate row collapsed
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    sheets_data = {}
    years_data = [
        ("1_6712", 2024, 846000),
        ("1_6811", 2025, 848000),
    ]

    age_headers = ["<1"] + [str(i) for i in range(1, 101)] + [">100"]

    for sheet_name, gregorian_yr, plb_total in years_data:
        rows = []
        
        # Row 1: Code 0 (National aggregate)
        nat_row = {
            "รหัสจังหวัด": "0",
            "ชื่อจังหวัด": "ทั่วประเทศ",
            "รวม 0-5 ปี": 2800000,
            "รวมทั้งสิ้น": 66000000,
            "สัญชาติไทย": 65000000,
            "ไม่ใช่สัญชาติไทย": 1000000,
        }
        for ah in age_headers:
            nat_row[f"อายุ_{ah}_ชาย"] = 320000
            nat_row[f"อายุ_{ah}_หญิง"] = 330000
        rows.append(nat_row)

        # Row 2: Phitsanulok (Code 65)
        # Realistic age distribution for ~848,000 population
        plb_row = {
            "รหัสจังหวัด": "65",
            "ชื่อจังหวัด": "พิษณุโลก",
            "รวม 0-5 ปี": 36000,
            "รวมทั้งสิ้น": plb_total,
            "สัญชาติไทย": plb_total - 12000,
            "ไม่ใช่สัญชาติไทย": 12000,
        }
        # Distribute single-year counts
        for idx, ah in enumerate(age_headers):
            # Normal-like curve peaked around 30-50
            if idx < 5:
                base_c = 3600
            elif idx < 20:
                base_c = 4800
            elif idx < 60:
                base_c = 6200
            elif idx < 80:
                base_c = 3800
            else:
                base_c = 1200
            plb_row[f"อายุ_{ah}_ชาย"] = int(base_c * 0.49)
            plb_row[f"อายุ_{ah}_หญิง"] = int(base_c * 0.51)
        rows.append(plb_row)

        # Add duplicate identical row for Phitsanulok to test duplicate collapse requirement
        rows.append(plb_row.copy())

        # Row 3: Neighbouring province Sukhothai (64)
        sk_row = {
            "รหัสจังหวัด": "64",
            "ชื่อจังหวัด": "สุโขทัย",
            "รวม 0-5 ปี": 25000,
            "รวมทั้งสิ้น": 580000,
            "สัญชาติไทย": 574000,
            "ไม่ใช่สัญชาติไทย": 6000,
        }
        for ah in age_headers:
            sk_row[f"อายุ_{ah}_ชาย"] = 2800
            sk_row[f"อายุ_{ah}_หญิง"] = 2900
        rows.append(sk_row)

        sheets_data[sheet_name] = pd.DataFrame(rows)

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        for sname, s_df in sheets_data.items():
            s_df.to_excel(writer, sheet_name=sname, index=False)

    return {
        "file_path": str(file_path),
        "sheets": list(sheets_data.keys()),
    }
