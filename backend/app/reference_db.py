import json
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from app.config import REFERENCE_DB_PATH, PROJECT_ROOT

AGE_BAND_INDEX_RANGES: Dict[str, Tuple[int, int]] = {
    "<1": (0, 0),
    "1-4": (1, 4),
    "5-9": (5, 9),
    "10-14": (10, 14),
    "15-19": (15, 19),
    "20-24": (20, 24),
    "25-29": (25, 29),
    "30-34": (30, 34),
    "35-39": (35, 39),
    "40-44": (40, 44),
    "45-49": (45, 49),
    "50-54": (50, 54),
    "55-59": (55, 59),
    "60-64": (60, 64),
    "65-69": (65, 69),
    "70-74": (70, 74),
    "75-79": (75, 79),
    "≥80": (80, 101),
}

# 50 Bangkok (province code 10) districts / khets officially matched to DOPA / GeoJSON
BANGKOK_DISTRICTS: Dict[str, Dict[str, str]] = {
    "1001": {"name_th": "เขตพระนคร", "name_en": "Phra Nakhon", "local_code": "01"},
    "1002": {"name_th": "เขตดุสิต", "name_en": "Dusit", "local_code": "02"},
    "1003": {"name_th": "เขตหนองจอก", "name_en": "Nong Chok", "local_code": "03"},
    "1004": {"name_th": "เขตบางรัก", "name_en": "Bang Rak", "local_code": "04"},
    "1005": {"name_th": "เขตบางเขน", "name_en": "Bang Khen", "local_code": "05"},
    "1006": {"name_th": "เขตบางกะปิ", "name_en": "Bang Kapi", "local_code": "06"},
    "1007": {"name_th": "เขตปทุมวัน", "name_en": "Pathum Wan", "local_code": "07"},
    "1008": {"name_th": "เขตป้อมปราบศัตรูพ่าย", "name_en": "Pom Prap Sattru Phai", "local_code": "08"},
    "1009": {"name_th": "เขตพระโขนง", "name_en": "Phra Khanong", "local_code": "09"},
    "1010": {"name_th": "เขตมีนบุรี", "name_en": "Min Buri", "local_code": "10"},
    "1011": {"name_th": "เขตลาดกระบัง", "name_en": "Lat Krabang", "local_code": "11"},
    "1012": {"name_th": "เขตยานนาวา", "name_en": "Yan Nawa", "local_code": "12"},
    "1013": {"name_th": "เขตสัมพันธวงศ์", "name_en": "Samphanthawong", "local_code": "13"},
    "1014": {"name_th": "เขตพญาไท", "name_en": "Phaya Thai", "local_code": "14"},
    "1015": {"name_th": "เขตธนบุรี", "name_en": "Thon Buri", "local_code": "15"},
    "1016": {"name_th": "เขตบางกอกใหญ่", "name_en": "Bangkok Yai", "local_code": "16"},
    "1017": {"name_th": "เขตห้วยขวาง", "name_en": "Huai Khwang", "local_code": "17"},
    "1018": {"name_th": "เขตคลองสาน", "name_en": "Khlong San", "local_code": "18"},
    "1019": {"name_th": "เขตตลิ่งชัน", "name_en": "Taling Chan", "local_code": "19"},
    "1020": {"name_th": "เขตบางกอกน้อย", "name_en": "Bangkok Noi", "local_code": "20"},
    "1021": {"name_th": "เขตบางขุนเทียน", "name_en": "Bang Khun Thian", "local_code": "21"},
    "1022": {"name_th": "เขตภาษีเจริญ", "name_en": "Phasi Charoen", "local_code": "22"},
    "1023": {"name_th": "เขตหนองแขม", "name_en": "Nong Khaem", "local_code": "23"},
    "1024": {"name_th": "เขตราษฎร์บูรณะ", "name_en": "Rat Burana", "local_code": "24"},
    "1025": {"name_th": "เขตบางพลัด", "name_en": "Bang Phlat", "local_code": "25"},
    "1026": {"name_th": "เขตดินแดง", "name_en": "Din Daeng", "local_code": "26"},
    "1027": {"name_th": "เขตบึงกุ่ม", "name_en": "Bueng Kum", "local_code": "27"},
    "1028": {"name_th": "เขตสาทร", "name_en": "Sathon", "local_code": "28"},
    "1029": {"name_th": "เขตบางซื่อ", "name_en": "Bang Sue", "local_code": "29"},
    "1030": {"name_th": "เขตจตุจักร", "name_en": "Chatuchak", "local_code": "30"},
    "1031": {"name_th": "เขตบางคอแหลม", "name_en": "Bang Kho Laem", "local_code": "31"},
    "1032": {"name_th": "เขตประเวศ", "name_en": "Prawet", "local_code": "32"},
    "1033": {"name_th": "เขตคลองเตย", "name_en": "Khlong Toei", "local_code": "33"},
    "1034": {"name_th": "เขตสวนหลวง", "name_en": "Suan Luang", "local_code": "34"},
    "1035": {"name_th": "เขตจอมทอง", "name_en": "Chom Thong", "local_code": "35"},
    "1036": {"name_th": "เขตดอนเมือง", "name_en": "Don Mueang", "local_code": "36"},
    "1037": {"name_th": "เขตราชเทวี", "name_en": "Ratchathewi", "local_code": "37"},
    "1038": {"name_th": "เขตลาดพร้าว", "name_en": "Lat Phrao", "local_code": "38"},
    "1039": {"name_th": "เขตวัฒนา", "name_en": "Watthana", "local_code": "39"},
    "1040": {"name_th": "เขตบางแค", "name_en": "Bang Khae", "local_code": "40"},
    "1041": {"name_th": "เขตหลักสี่", "name_en": "Lak Si", "local_code": "41"},
    "1042": {"name_th": "เขตสายไหม", "name_en": "Sai Mai", "local_code": "42"},
    "1043": {"name_th": "เขตคันนายาว", "name_en": "Khan Na Yao", "local_code": "43"},
    "1044": {"name_th": "เขตสะพานสูง", "name_en": "Saphan Sung", "local_code": "44"},
    "1045": {"name_th": "เขตวังทองหลาง", "name_en": "Wang Thonglang", "local_code": "45"},
    "1046": {"name_th": "เขตคลองสามวา", "name_en": "Khlong Sam Wa", "local_code": "46"},
    "1047": {"name_th": "เขตบางนา", "name_en": "Bang Na", "local_code": "47"},
    "1048": {"name_th": "เขตทวีวัฒนา", "name_en": "Thawi Watthana", "local_code": "48"},
    "1049": {"name_th": "เขตทุ่งครุ", "name_en": "Thung Khru", "local_code": "49"},
    "1050": {"name_th": "เขตบางบอน", "name_en": "Bang Bon", "local_code": "50"},
}


def _get_ro_connection() -> sqlite3.Connection:
    if not REFERENCE_DB_PATH.exists():
        raise FileNotFoundError(f"Reference SQLite database not found at {REFERENCE_DB_PATH}")
    con = sqlite3.connect(REFERENCE_DB_PATH.as_uri() + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


@lru_cache(maxsize=1)
def get_dataset_metadata() -> Dict[str, Any]:
    with _get_ro_connection() as con:
        rows = con.execute("SELECT key, value_json FROM dataset_metadata").fetchall()
        meta: Dict[str, Any] = {}
        for r in rows:
            try:
                meta[r["key"]] = json.loads(r["value_json"])
            except Exception:
                meta[r["key"]] = r["value_json"]
        return meta


@lru_cache(maxsize=1)
def get_all_provinces() -> List[Dict[str, Any]]:
    with _get_ro_connection() as con:
        rows = con.execute(
            "SELECT province_code, province_name_th, province_name_en_source, scr_group_source "
            "FROM province ORDER BY province_code"
        ).fetchall()
        return [
            {
                "province_code": r["province_code"],
                "name_th": r["province_name_th"],
                "name_en": r["province_name_en_source"],
                "scr_group_source": r["scr_group_source"],
            }
            for r in rows
        ]


@lru_cache(maxsize=128)
def get_province_by_code(province_code: str) -> Optional[Dict[str, Any]]:
    if not province_code:
        return None
    code = str(province_code).strip().zfill(2)
    with _get_ro_connection() as con:
        row = con.execute(
            "SELECT province_code, province_name_th, province_name_en_source, scr_group_source "
            "FROM province WHERE province_code = ?",
            (code,),
        ).fetchone()
        if not row:
            return None
        return {
            "province_code": row["province_code"],
            "name_th": row["province_name_th"],
            "name_en": row["province_name_en_source"],
            "scr_group_source": row["scr_group_source"],
        }


@lru_cache(maxsize=128)
def get_districts_by_province(province_code: Optional[str] = None) -> List[Dict[str, Any]]:
    if province_code and str(province_code).strip() not in ("", "all"):
        code = str(province_code).strip().zfill(2)
        if code == "10":
            return [
                {
                    "district_code": d_code,
                    "province_code": "10",
                    "district_local_code": d_info["local_code"],
                    "name_th": d_info["name_th"],
                    "source_label_th": d_info["name_th"],
                    "name_en": f"{d_info['name_th']} ({d_code}, Bangkok)",
                    "province_name_th": "กรุงเทพมหานคร",
                    "province_name_en": "Bangkok",
                }
                for d_code, d_info in BANGKOK_DISTRICTS.items()
            ]
        with _get_ro_connection() as con:
            rows = con.execute(
                "SELECT d.district_code, d.province_code, d.district_local_code, "
                "d.district_name_th, d.source_label_th, d.source_pdf_page, "
                "p.province_name_th, p.province_name_en_source "
                "FROM district d "
                "LEFT JOIN province p ON d.province_code = p.province_code "
                "WHERE d.province_code = ? "
                "ORDER BY d.district_code",
                (code,),
            ).fetchall()
            return [
                {
                    "district_code": r["district_code"],
                    "province_code": r["province_code"],
                    "district_local_code": r["district_local_code"],
                    "name_th": r["district_name_th"],
                    "source_label_th": r["source_label_th"],
                    "name_en": f"{r['district_name_th']} ({r['district_code']}, {r['province_name_en_source'] or r['province_code']})",
                    "province_name_th": r["province_name_th"],
                    "province_name_en": r["province_name_en_source"],
                }
                for r in rows
            ]
    else:
        with _get_ro_connection() as con:
            rows = con.execute(
                "SELECT d.district_code, d.province_code, d.district_local_code, "
                "d.district_name_th, d.source_label_th, d.source_pdf_page, "
                "p.province_name_th, p.province_name_en_source "
                "FROM district d "
                "LEFT JOIN province p ON d.province_code = p.province_code "
                "ORDER BY d.district_code"
            ).fetchall()
            sqlite_dists = [
                {
                    "district_code": r["district_code"],
                    "province_code": r["province_code"],
                    "district_local_code": r["district_local_code"],
                    "name_th": r["district_name_th"],
                    "source_label_th": r["source_label_th"],
                    "name_en": f"{r['district_name_th']} ({r['district_code']}, {r['province_name_en_source'] or r['province_code']})",
                    "province_name_th": r["province_name_th"],
                    "province_name_en": r["province_name_en_source"],
                }
                for r in rows
            ]
            bkk_dists = [
                {
                    "district_code": d_code,
                    "province_code": "10",
                    "district_local_code": d_info["local_code"],
                    "name_th": d_info["name_th"],
                    "source_label_th": d_info["name_th"],
                    "name_en": f"{d_info['name_th']} ({d_code}, Bangkok)",
                    "province_name_th": "กรุงเทพมหานคร",
                    "province_name_en": "Bangkok",
                }
                for d_code, d_info in BANGKOK_DISTRICTS.items()
            ]
            return sqlite_dists + bkk_dists


@lru_cache(maxsize=1024)
def get_district_by_code(district_code: str) -> Optional[Dict[str, Any]]:
    if not district_code:
        return None
    code = str(district_code).strip()
    if len(code) != 4 or not code.isdigit():
        return None
    if code in BANGKOK_DISTRICTS:
        bk = BANGKOK_DISTRICTS[code]
        return {
            "district_code": code,
            "province_code": "10",
            "district_local_code": bk["local_code"],
            "name_th": bk["name_th"],
            "source_label_th": bk["name_th"],
            "name_en": f"{bk['name_th']} ({code}, Bangkok)",
            "province_name_th": "กรุงเทพมหานคร",
            "province_name_en": "Bangkok",
        }
    with _get_ro_connection() as con:
        row = con.execute(
            "SELECT d.district_code, d.province_code, d.district_local_code, "
            "d.district_name_th, d.source_label_th, d.source_pdf_page, "
            "p.province_name_th, p.province_name_en_source "
            "FROM district d "
            "LEFT JOIN province p ON d.province_code = p.province_code "
            "WHERE d.district_code = ?",
            (code,),
        ).fetchone()
        if not row:
            return None
        return {
            "district_code": row["district_code"],
            "province_code": row["province_code"],
            "district_local_code": row["district_local_code"],
            "name_th": row["district_name_th"],
            "source_label_th": row["source_label_th"],
            "name_en": f"{row['district_name_th']} ({row['district_code']}, {row['province_name_en_source'] or row['province_code']})",
            "province_name_th": row["province_name_th"],
            "province_name_en": row["province_name_en_source"],
        }


@lru_cache(maxsize=1)
def get_population_snapshots() -> List[Dict[str, Any]]:
    with _get_ro_connection() as con:
        rows = con.execute(
            "SELECT reference_year, reference_month, source_period_be, source_sheet, duplicate_rows_removed "
            "FROM population_snapshot ORDER BY reference_year"
        ).fetchall()
        return [dict(r) for r in rows]


@lru_cache(maxsize=256)
def get_geography_population_row(reference_year: int, province_code: str) -> Optional[Dict[str, Any]]:
    code = str(province_code).strip().zfill(2)
    with _get_ro_connection() as con:
        row = con.execute(
            "SELECT reference_year, reference_month, province_code, source_province_name_th, "
            "population_total_source, male_total_source, female_total_source, "
            "age_known_population_sum, source_counts_json "
            "FROM population_by_geography "
            "WHERE reference_year = ? AND province_code = ?",
            (int(reference_year), code),
        ).fetchone()
        if not row:
            return None
        res = dict(row)
        try:
            res["source_counts"] = json.loads(res.pop("source_counts_json") or "{}")
        except Exception:
            res["source_counts"] = {}
        return res


@lru_cache(maxsize=512)
def get_age_range_population_sql(
    reference_year: int,
    province_code: str,
    min_age_index: int,
    max_age_index: int,
    sex_db: Optional[str] = None,
) -> Optional[int]:
    """
    Executes parameterized SQL against population_by_age view:
    SELECT SUM(population) FROM population_by_age WHERE reference_year=? AND province_code=? AND age_index BETWEEN ? AND ?
    """
    code = str(province_code).strip().zfill(2)
    with _get_ro_connection() as con:
        if sex_db in ("male", "female"):
            row = con.execute(
                "SELECT SUM(population) AS pop_sum FROM population_by_age "
                "WHERE reference_year = ? AND province_code = ? AND sex = ? AND age_index BETWEEN ? AND ?",
                (int(reference_year), code, sex_db, int(min_age_index), int(max_age_index)),
            ).fetchone()
        else:
            row = con.execute(
                "SELECT SUM(population) AS pop_sum FROM population_by_age "
                "WHERE reference_year = ? AND province_code = ? AND age_index BETWEEN ? AND ?",
                (int(reference_year), code, int(min_age_index), int(max_age_index)),
            ).fetchone()
        if not row or row["pop_sum"] is None:
            return None
        return int(row["pop_sum"])


@lru_cache(maxsize=256)
def get_all_standard_age_band_populations(
    reference_year: int,
    province_code: str,
    sex_db: Optional[str] = None,
) -> Optional[Dict[str, int]]:
    """
    Queries single-year age counts via SQL and aggregates into the 18 standard surveillance age bands.
    Never double-counts source subtotals.
    """
    code = str(province_code).strip().zfill(2)
    with _get_ro_connection() as con:
        if sex_db in ("male", "female"):
            rows = con.execute(
                "SELECT age_index, SUM(population) AS pop_sum FROM population_by_age "
                "WHERE reference_year = ? AND province_code = ? AND sex = ? "
                "GROUP BY age_index ORDER BY age_index",
                (int(reference_year), code, sex_db),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT age_index, SUM(population) AS pop_sum FROM population_by_age "
                "WHERE reference_year = ? AND province_code = ? "
                "GROUP BY age_index ORDER BY age_index",
                (int(reference_year), code),
            ).fetchall()
        if not rows:
            return None
        by_idx = {int(r["age_index"]): int(r["pop_sum"]) for r in rows if r["pop_sum"] is not None}
        band_pops: Dict[str, int] = {}
        for band, (lo, hi) in AGE_BAND_INDEX_RANGES.items():
            band_pops[band] = sum(by_idx.get(idx, 0) for idx in range(lo, hi + 1))
        return band_pops


def get_bounded_reference_summary() -> Dict[str, Any]:
    """Returns bounded verification summary (counts, schema, max 3 examples) without dumping full data."""
    table_names = (
        "province",
        "district",
        "age_bin",
        "population_snapshot",
        "population_by_geography",
        "population_by_age",
        "dataset_metadata",
    )
    with _get_ro_connection() as con:
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        counts = {
            name: con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            for name in table_names[:6]
        }
        schema = {
            name: [f"{r[1]} ({r[2]})" for r in con.execute(f"PRAGMA table_info({name})").fetchall()]
            for name in table_names
        }
        nat_2025 = con.execute(
            "SELECT population_total_source FROM population_by_geography WHERE reference_year = ? AND province_code = ?",
            (2025, "00"),
        ).fetchone()[0]
        prov_samples = [
            dict(r)
            for r in con.execute(
                "SELECT province_code, province_name_th, province_name_en_source, scr_group_source FROM province ORDER BY province_code LIMIT 3"
            ).fetchall()
        ]
        dist_samples = [
            dict(r)
            for r in con.execute(
                "SELECT district_code, province_code, district_local_code, district_name_th, source_pdf_page FROM district ORDER BY district_code LIMIT 3"
            ).fetchall()
        ]
        age_bin_samples = [
            dict(r)
            for r in con.execute(
                "SELECT age_index, label, lower_completed_years, upper_exclusive_years FROM age_bin ORDER BY age_index LIMIT 3"
            ).fetchall()
        ]
        snap_samples = [
            dict(r)
            for r in con.execute(
                "SELECT reference_year, reference_month, source_period_be, source_sheet, duplicate_rows_removed FROM population_snapshot ORDER BY reference_year DESC LIMIT 3"
            ).fetchall()
        ]
        geo_samples = [
            dict(r)
            for r in con.execute(
                "SELECT reference_year, reference_month, province_code, source_province_name_th, population_total_source, male_total_source, female_total_source, age_known_population_sum "
                "FROM population_by_geography WHERE reference_year = 2025 ORDER BY province_code LIMIT 3"
            ).fetchall()
        ]
        age_view_samples = [
            dict(r)
            for r in con.execute(
                "SELECT reference_year, reference_month, province_code, sex, age_index, population "
                "FROM population_by_age WHERE reference_year = 2025 AND province_code = '10' ORDER BY sex, age_index LIMIT 3"
            ).fetchall()
        ]
        return {
            "db_exists": REFERENCE_DB_PATH.exists(),
            "integrity_check": integrity,
            "counts": counts,
            "schema": schema,
            "national_population_2025": int(nat_2025),
            "district_example": ["1101", get_district_by_code("1101")["name_th"] if get_district_by_code("1101") else ""],
            "available_years": [s["reference_year"] for s in get_population_snapshots()],
            "samples_max_3": {
                "province": prov_samples,
                "district": dist_samples,
                "age_bin": age_bin_samples,
                "population_snapshot": snap_samples,
                "population_by_geography": geo_samples,
                "population_by_age": age_view_samples,
            },
            "metadata": get_dataset_metadata(),
        }


def get_reference_summary() -> Dict[str, Any]:
    return get_bounded_reference_summary()


def get_provinces_list() -> List[Dict[str, Any]]:
    return [
        {
            "province_code": p["province_code"],
            "province_name_th": p["name_th"],
            "province_name_en": p["name_en"],
            "scr_group_source": p["scr_group_source"],
        }
        for p in get_all_provinces()
    ]


def get_districts_list(province_code: Optional[str] = None) -> List[Dict[str, Any]]:
    return [
        {
            "district_code": d["district_code"],
            "province_code": d["province_code"],
            "district_local_code": d["district_local_code"],
            "district_name_th": d["name_th"],
            "source_label_th": d["source_label_th"],
        }
        for d in get_districts_by_province(province_code)
    ]
