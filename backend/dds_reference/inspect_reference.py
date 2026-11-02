from pathlib import Path
import json
import sqlite3

path = Path(__file__).resolve().parent / "data" / "dds_reference.sqlite"
with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as con:
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    counts = {name: con.execute("SELECT COUNT(*) FROM " + name).fetchone()[0]
              for name in ("province", "district", "age_bin", "population_snapshot", "population_by_geography", "population_by_age")}
    assert counts == {"province":77,"district":878,"age_bin":102,"population_snapshot":13,"population_by_geography":1014,"population_by_age":206856}
    national = con.execute("SELECT population_total_source FROM population_by_geography WHERE reference_year=? AND province_code=?", (2025,"00")).fetchone()[0]
    assert national == 65826149
    example = con.execute("SELECT district_code,district_name_th FROM district WHERE district_code=?",("1101",)).fetchone()
    print(json.dumps({"checks":"passed","counts":counts,"national_population_2025":national,"district_example":example,"limitations":["No Bangkok district names","No district population","No age-by-nationality denominators","No 2026 population"]},ensure_ascii=False))
