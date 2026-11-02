import sys
import io
import json
import struct
import zipfile
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("--- 1. Health & SQLite Reference Summary ---")
r = client.get("/api/health")
assert r.status_code == 200
health = r.json()
ref = health["reference_db"]
assert ref["integrity_check"] == "ok"
assert ref["counts"] == {
    "province": 77,
    "district": 878,
    "age_bin": 102,
    "population_snapshot": 13,
    "population_by_geography": 1014,
    "population_by_age": 206856,
}
assert ref["national_population_2025"] == 65826149
print("Reference DB verified:", json.dumps(ref["counts"], ensure_ascii=False))

print("--- 2. Generate Synthetic Dataset & Test Geography Scopes ---")
r_syn = client.post("/api/generate-synthetic")
assert r_syn.status_code == 200
syn_data = r_syn.json()
assert syn_data["status"] == "success"

# 2A. Single Province (Phitsanulok = 65)
r_prov1 = client.put("/api/filters", json={"scope_mode": "provinces", "province_codes": ["65"], "year": 2025})
assert r_prov1.status_code == 200
ov_prov1 = client.get("/api/measures/overview").json()
assert ov_prov1["compatible_population"] == 835956
assert ov_prov1["case_notification_rate"] is not None
assert ov_prov1["population_year_be"] == 2568
print(f"Single Province (65) OK: C={ov_prov1['cases_C']}, Pop={ov_prov1['compatible_population']}, Rate={ov_prov1['case_notification_rate']}")

# 2B. Multi-Province (Phitsanulok 65 + Samut Prakan 11, plus 00 to verify 00 is stripped and never double-counted)
r_prov_multi = client.put(
    "/api/filters",
    json={"scope_mode": "provinces", "province_codes": ["65", "11", "00"], "year": 2025},
)
assert r_prov_multi.status_code == 200
ov_multi = client.get("/api/measures/overview").json()
assert ov_multi["selected_province_codes"] == ["65", "11"]
assert ov_multi["compatible_population"] > 835956
expected_multi_rate = round(ov_multi["cases_C"] / ov_multi["compatible_population"] * 100000.0, 2)
assert ov_multi["case_notification_rate"] == expected_multi_rate
print(f"Multi-Province (65+11) OK: C={ov_multi['cases_C']}, Pop={ov_multi['compatible_population']}, Rate={ov_multi['case_notification_rate']}")

# 2C. Missing Province Denominator (["65", "99"]) -> unavailable & reports missing_provinces=["99"]
r_prov_miss = client.put(
    "/api/filters",
    json={"scope_mode": "provinces", "province_codes": ["65", "99"], "year": 2025},
)
assert r_prov_miss.status_code == 200
ov_miss = client.get("/api/measures/overview").json()
assert ov_miss["case_notification_rate"] is None
assert ov_miss["denominator_info"]["available"] is False
assert "99" in ov_miss["denominator_info"]["missing_provinces"]
print("Missing Province Denominator Safeguard OK: missing_provinces =", ov_miss["denominator_info"]["missing_provinces"])

# 2D. Nationwide Scope ("national") -> uses 65,826,149 once
r_nat = client.put("/api/filters", json={"scope_mode": "national", "year": 2025})
assert r_nat.status_code == 200
ov_nat = client.get("/api/measures/overview").json()
assert ov_nat["compatible_population"] == 65826149
assert ov_nat["case_notification_rate"] is not None
print(f"Nationwide Scope OK: C={ov_nat['cases_C']}, Pop={ov_nat['compatible_population']}, Rate={ov_nat['case_notification_rate']}")

# 2E. Fallback Year (Year 2026 -> uses 2568 BE / 2025 CE with is_fallback_year=True)
ov_2026 = client.get("/api/measures/overview?scope_mode=provinces&province_codes=65&year=2026").json()
assert ov_2026["denominator_info"]["available"] is True
assert ov_2026["denominator_info"]["population"] == 835956
assert ov_2026["denominator_info"]["population_year_be"] == 2568
assert ov_2026["denominator_info"]["is_fallback_year"] is True
print("Year 2026 -> 2568 (2025) Fallback OK")

# 2F. District Scope without District Population -> Counts & IPD% available, Rate unavailable
r_dist = client.put(
    "/api/filters",
    json={"scope_mode": "district", "province_codes": ["65"], "district_code": "6501", "year": 2025},
)
assert r_dist.status_code == 200
ov_dist = client.get("/api/measures/overview").json()
assert ov_dist["cases_C"] > 0
assert ov_dist["hospitalization_prop"] > 0
assert ov_dist["case_notification_rate"] is None
assert ov_dist["denominator_info"]["available"] is False
print(f"District Scope Safeguard OK: C={ov_dist['cases_C']}, IPD%={ov_dist['hospitalization_prop']}%, Rate=None")

# Reset filters to all_imported
client.put("/api/filters", json={"scope_mode": "all_imported", "province_codes": [], "district_code": None, "year": 2025})

print("--- 3. Verify Associated Factors Removed & Tables 0-4 / Figures 1-7 Renumbered ---")
r_reg_gone = client.get("/api/regression/logistic")
assert r_reg_gone.status_code == 404
r_t5_gone = client.get("/api/tables/table5")
assert r_t5_gone.status_code == 404
r_f8_gone = client.get("/api/studio/render-figure/8")
assert r_f8_gone.status_code == 404

for t in ["table0", "table1", "table2", "table3", "table4"]:
    rt = client.get(f"/api/tables/{t}")
    assert rt.status_code == 200, f"Failed {t}: {rt.text}"
t4 = client.get("/api/tables/table4").json()
assert t4["status"] == "success"
assert "forecasts" in t4
print("Associated Factors removed (404) and Tables 0..4 (Table 4 = Forecast) verified OK")

figs = client.get("/api/studio/figures").json()
assert [f["id"] for f in figs] == [1, 2, 3, 4, 5, 6, 7]
for lang in ["th", "en"]:
    for fig_id in [1, 4, 7]:
        rf = client.get(f"/api/studio/render-figure/{fig_id}?format=png&lang={lang}")
        assert rf.status_code == 200
        w, h = struct.unpack(">II", rf.content[16:24])
        assert (w, h) == (3840, 2160)
print("Studio Figures 1..7 (Figure 7 = Forecast) rendered at 3840x2160 in TH & EN OK")

print("--- 4. Multi-File Import Queue (.CSV + .XLSX), Duplicate & Revision Resolution ---")
csv_content = (
    'CID,รหัสกลุ่มโรค,datesick,วันที่ Update,status,type,sex,year,prov_code,รหัสอำเภอ(ที่อยู่ปัจจุบัน)\n'
    '"0111111111111","01","2025-02-01","2025-02-01 08:00:00","8","OPD","ชาย","30","65","01"\n'
    '"0222222222222","01","2025-02-05","2025-02-05 09:00:00","8","IPD","หญิง","45","11","01"\n'
).encode("cp874")

xlsx_io = io.BytesIO()
with pd.ExcelWriter(xlsx_io, engine="openpyxl") as writer:
    pd.DataFrame([{"note": "unused sheet"}]).to_excel(writer, sheet_name="Readme", index=False)
    pd.DataFrame([
        # Exact duplicate of 0222222222222
        {
            "CID": "0222222222222",
            "รหัสกลุ่มโรค": "01",
            "datesick": "2025-02-05",
            "วันที่ Update": "2025-02-05 09:00:00",
            "status": "8",
            "type": "IPD",
            "sex": "หญิง",
            "year": "45",
            "prov_code": "11",
            "รหัสอำเภอ(ที่อยู่ปัจจุบัน)": "01",
        },
        # Revision of 0111111111111 changing OPD -> IPD
        {
            "CID": "0111111111111",
            "รหัสกลุ่มโรค": "01",
            "datesick": "2025-02-01",
            "วันที่ Update": "2025-02-10 15:00:00",
            "status": "8",
            "type": "IPD",
            "sex": "ชาย",
            "year": "30",
            "prov_code": "65",
            "รหัสอำเภอ(ที่อยู่ปัจจุบัน)": "01",
        },
        # New 3rd case in 2025
        {
            "CID": "0333333333333",
            "รหัสกลุ่มโรค": "01",
            "datesick": "2025-02-12",
            "วันที่ Update": "2025-02-12 10:00:00",
            "status": "8",
            "type": "OPD",
            "sex": "ชาย",
            "year": "12",
            "prov_code": "65",
            "รหัสอำเภอ(ที่อยู่ปัจจุบัน)": "02",
        },
    ]).to_excel(writer, sheet_name="Data2025", index=False)

client.delete("/api/import/queue")
r_stage = client.post(
    "/api/import/stage",
    files=[
        ("files", ("file1_cp874.csv", csv_content, "text/csv")),
        ("files", ("file2_workbook.xlsx", xlsx_io.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
    ],
)
assert r_stage.status_code == 200
staged_items = r_stage.json()["queue"]
assert len(staged_items) == 2

# Select "Data2025" sheet on the xlsx file
xlsx_item = [it for it in staged_items if it["file_format"] == "xlsx"][0]
r_upd_sheet = client.put(
    f"/api/import/stage/{xlsx_item['staged_id']}",
    json={"selected_sheet": "Data2025"},
)
assert r_upd_sheet.status_code == 200

# Preview impact in "replace" mode
r_prev = client.post("/api/import/preview-impact", json={"import_mode": "replace"})
assert r_prev.status_code == 200
prev = r_prev.json()
assert prev["incoming_raw_rows"] == 5
assert prev["exact_duplicates_removed"] == 1
assert prev["cross_file_revisions_superseded"] == 1
assert prev["resulting_eligible_cases_C"] == 3

# Commit import in "replace" mode
r_commit = client.post("/api/import/commit", json={"import_mode": "replace"})
assert r_commit.status_code == 200
ov_after = client.get("/api/measures/overview").json()
assert ov_after["cases_C"] == 3
assert ov_after["ipd_H"] == 2
assert ov_after["opd_O"] == 1

# Re-import the exact same CSV in "append" mode -> must add 0 net cases!
client.post(
    "/api/import/stage",
    files=[("files", ("file1_cp874_reimport.csv", csv_content, "text/csv"))],
)
r_prev_append = client.post("/api/import/preview-impact", json={"import_mode": "append"}).json()
assert r_prev_append["resulting_eligible_cases_C"] == 3
assert r_prev_append["net_change_cases"] == 0
r_commit_append = client.post("/api/import/commit", json={"import_mode": "append"})
assert r_commit_append.status_code == 200
assert client.get("/api/measures/overview").json()["cases_C"] == 3
print("Multi-file CSV+XLSX import, sheet selection, deduplication, and append idempotency OK!")

print("--- 5. Restore Synthetic Dataset & Verify Exports (.XLSX, .CSV, .ZIP) ---")
client.post("/api/generate-synthetic")
rx = client.get("/api/export/excel")
assert rx.status_code == 200
assert len(rx.content) > 10000

rz = client.get("/api/studio/presentation-pack.zip?lang=th")
assert rz.status_code == 200
zf = zipfile.ZipFile(io.BytesIO(rz.content))
names = zf.namelist()
assert any("07_weekly_forecast" in n for n in names)
assert any("Table_4_Forecast.csv" in n for n in names)
assert not any("forest_plot" in n.lower() for n in names)
print("Exports (.XLSX, .CSV, .ZIP without Forest Plot / Associated Factors) verified OK!")

print("\n>>> ALL END-TO-END VERIFICATIONS PASSED SUCCESSFULLY! <<<")
