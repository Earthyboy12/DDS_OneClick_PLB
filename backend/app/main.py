import io
import json
import logging
from pathlib import Path

logger = logging.getLogger("dds_main")
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Query, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse

from app.config import (
    BASE_DIR,
    FIXTURES_DIR,
    SESSIONS_DIR,
    MAX_UPLOAD_SIZE_BYTES,
    MAX_UPLOAD_SIZE_MB,
)
from app.session import session_store
from app.dds_importer import (
    CANONICAL_SCHEMA_FIELDS,
    process_dds_dataframe,
    standardize_single_file_dataframe,
    resolve_combined_standardized_dataframe,
    read_dataframe_from_bytes,
    import_stage_manager,
    ensure_dataframe_dates_and_epi_weeks,
)
from app.district_crosswalk import load_custom_geography_table, get_province_info, get_district_info
from app.population import population_manager
from app.measures import (
    calculate_surveillance_measures,
    wilson_score_interval,
    exact_poisson_rate_interval,
    STANDARD_AGE_BANDS,
)
from app.reference_db import (
    get_reference_summary,
    get_provinces_list,
    get_districts_list,
)
from app.filters import (
    DEFAULT_FILTERS,
    normalize_filters,
    apply_filters_and_resolve_scope,
    extract_available_filter_options,
)
from app.forecast import (
    build_continuous_weekly_series,
    fit_ols_forecast,
    build_seasonal_comparison_series,
)
from app.table_generator import (
    generate_table_0_import_flow,
    generate_table_1_characteristics,
    generate_table_2_age_burden,
    generate_table_3_district_summary,
)
from app.studio_renderer import (
    render_figure_1_epicurve,
    render_figure_2_district_bar,
    render_figure_3_age_sex_nat,
    render_figure_4_age_rates,
    render_figure_5_hospitalization_prop,
    render_figure_6_nationality_comparison,
    render_figure_7_forecast,
    render_figure_8_seasonal_comparison,
)
from app.export_manager import (
    create_styled_excel_workbook,
    create_presentation_pack_zip,
    persist_session_outputs_to_disk,
)
from app.synthetic_generator import generate_synthetic_dds_workbook

app = FastAPI(
    title="DDS One-Click Surveillance API",
    description="Backend API for Thai Digital Disease Surveillance (DDS) Analytical Application backed by dds_reference.sqlite",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ACTIVE_SESSION_ID = "default_active_session"

DATA_GEO_DIR = Path(__file__).resolve().parent / "data"
_PROVINCES_GEOJSON_CACHE: Optional[Dict[str, Any]] = None
_DISTRICTS_GEOJSON_CACHE: Optional[Dict[str, Any]] = None
_GEOJSON_DISTRICT_NAMES: Dict[str, Dict[str, str]] = {}


def _get_provinces_geojson() -> Dict[str, Any]:
    global _PROVINCES_GEOJSON_CACHE
    if _PROVINCES_GEOJSON_CACHE is None:
        p_path = DATA_GEO_DIR / "thailand_provinces.geojson"
        if p_path.exists():
            with open(p_path, "r", encoding="utf-8") as f:
                _PROVINCES_GEOJSON_CACHE = json.load(f)
            ref_provs = {p["province_code"]: p for p in get_provinces_list()}
            for feat in _PROVINCES_GEOJSON_CACHE.get("features", []):
                props = feat.get("properties", {})
                pc = str(props.get("pro_code", "")).zfill(2)
                if pc in ref_provs:
                    props["pro_th"] = ref_provs[pc].get("province_name_th") or ref_provs[pc].get("name_th") or props.get("pro_th")
                    props["pro_en"] = ref_provs[pc].get("province_name_en") or ref_provs[pc].get("name_en") or props.get("pro_en")
        else:
            _PROVINCES_GEOJSON_CACHE = {"type": "FeatureCollection", "features": []}
    return _PROVINCES_GEOJSON_CACHE


def _get_districts_geojson() -> Dict[str, Any]:
    global _DISTRICTS_GEOJSON_CACHE, _GEOJSON_DISTRICT_NAMES
    if _DISTRICTS_GEOJSON_CACHE is None:
        d_path = DATA_GEO_DIR / "thailand_districts.geojson"
        if d_path.exists():
            with open(d_path, "r", encoding="utf-8") as f:
                _DISTRICTS_GEOJSON_CACHE = json.load(f)
            ref_dists = {d["district_code"]: d for d in get_districts_list()}
            for feat in _DISTRICTS_GEOJSON_CACHE.get("features", []):
                props = feat.get("properties", {})
                ac = str(props.get("amp_code", "")).zfill(4)
                if ac in ref_dists:
                    props["amp_th"] = ref_dists[ac].get("district_name_th") or ref_dists[ac].get("name_th") or props.get("amp_th")
                _GEOJSON_DISTRICT_NAMES[ac] = {
                    "name_th": props.get("amp_th", ac),
                    "name_en": props.get("amp_en", ac),
                    "prov_code": str(props.get("pro_code", ac[:2])).zfill(2),
                    "prov_name_th": props.get("pro_th", ""),
                    "prov_name_en": props.get("pro_en", ""),
                }
        else:
            _DISTRICTS_GEOJSON_CACHE = {"type": "FeatureCollection", "features": []}
    return _DISTRICTS_GEOJSON_CACHE


def _autoload_persisted_session_if_available() -> None:
    """
    Loads the persisted session on disk (if present) into memory on startup and ensures
    analysis_date, onset_year, epi_year, epi_week are populated via fallback dates.
    """
    try:
        sess_dir = SESSIONS_DIR / ACTIVE_SESSION_ID
        csv_path = sess_dir / "cleaned_episodes.csv"
        snap_path = sess_dir / "analytical_snapshot.json"
        if not csv_path.exists():
            return
        df_disk = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        if df_disk.empty:
            return
        repaired_df = ensure_dataframe_dates_and_epi_weeks(df_disk)

        # Repair any stale district names (such as Bangkok 50 districts from earlier sessions)
        from app.district_crosswalk import get_district_info
        for p_col, d_col, th_col, en_col, lk_col in [
            ("residence_prov_code", "residence_district_code", "residence_district_name_th", "residence_district_name_en", "residence_lookup_status"),
            ("illness_prov_code", "illness_district_code", "illness_district_name_th", "illness_district_name_en", "illness_lookup_status"),
        ]:
            if p_col in repaired_df.columns and d_col in repaired_df.columns and th_col in repaired_df.columns:
                mask = (repaired_df[p_col] == "10") & (repaired_df[th_col].astype(str).str.contains("ไม่มีรายชื่อเขต|Bangkok", na=False))
                if mask.any():
                    for idx in repaired_df[mask].index:
                        d_code_val = repaired_df.at[idx, d_col]
                        info = get_district_info(d_code_val, "10")
                        repaired_df.at[idx, th_col] = info["name_th"]
                        if en_col in repaired_df.columns:
                            repaired_df.at[idx, en_col] = info["name_en"]
                        if lk_col in repaired_df.columns:
                            repaired_df.at[idx, lk_col] = info["lookup_status"]
        audit_trail: Dict[str, Any] = {}
        is_syn = False
        if snap_path.exists():
            with open(snap_path, "r", encoding="utf-8") as f:
                snap = json.load(f)
                audit_trail = snap.get("audit_trail", {})
                is_syn = bool(snap.get("is_synthetic", False))

        n_elig = len(repaired_df)
        ipd_h = int((repaired_df["clean_patient_type"] == "IPD").sum()) if "clean_patient_type" in repaired_df.columns else 0
        opd_o = int((repaired_df["clean_patient_type"] == "OPD").sum()) if "clean_patient_type" in repaired_df.columns else 0
        unk_u = int((repaired_df["clean_patient_type"] == "Unknown").sum()) if "clean_patient_type" in repaired_df.columns else 0
        rec_deaths = int((repaired_df["clean_outcome_status"] == "Dead").sum()) if "clean_outcome_status" in repaired_df.columns else 0
        known_alive = int((repaired_df["clean_outcome_status"] == "Alive").sum()) if "clean_outcome_status" in repaired_df.columns else 0
        unk_outcome = int((repaired_df["clean_outcome_status"] == "Unknown").sum()) if "clean_outcome_status" in repaired_df.columns else 0
        susp_age = int(repaired_df["is_suspicious_age"].astype(str).str.lower().isin(["true", "1"]).sum()) if "is_suspicious_age" in repaired_df.columns else 0

        src_summary = audit_trail.get("source_files_summary", [])
        if not src_summary and "source_file" in repaired_df.columns:
            src_sheet_col = repaired_df["source_sheet"] if "source_sheet" in repaired_df.columns else pd.Series(["Sheet1"] * n_elig)
            for (sf, ss), grp in repaired_df.groupby([repaired_df["source_file"], src_sheet_col], dropna=False):
                src_summary.append({
                    "source_file": str(sf),
                    "source_sheet": str(ss),
                    "non_empty_rows": len(grp),
                    "eligible_contributed": len(grp),
                    "duplicates_or_excluded": 0,
                })

        reconstructed_audit = {
            "total_rows_imported": int(audit_trail.get("total_rows_imported") or n_elig),
            "trailing_blanks_removed": int(audit_trail.get("trailing_blanks_removed") or 0),
            "non_empty_records": int(audit_trail.get("non_empty_records") or n_elig),
            "exact_duplicates_removed": int(audit_trail.get("exact_duplicates_removed") or 0),
            "cross_file_revisions_superseded": int(audit_trail.get("cross_file_revisions_superseded") or 0),
            "superseded_revisions_removed": int(audit_trail.get("superseded_revisions_removed") or 0),
            "authoritative_episodes_total": int(audit_trail.get("authoritative_episodes_total") or n_elig),
            "cancelled_episodes_excluded": int(audit_trail.get("cancelled_episodes_excluded") or 0),
            "pending_or_other_excluded": int(audit_trail.get("pending_or_other_excluded") or 0),
            "missing_status_excluded": int(audit_trail.get("missing_status_excluded") or 0),
            "used_fallback_approval": bool(audit_trail.get("used_fallback_approval", False)),
            "eligible_episodes_C": n_elig,
            "ipd_episodes_H": ipd_h,
            "opd_episodes_O": opd_o,
            "unknown_patient_type_U": unk_u,
            "patient_type_missing_pct": round((unk_u / n_elig * 100.0), 2) if n_elig > 0 else 0.0,
            "suspicious_age_count": susp_age,
            "missing_onset_date_count": int(repaired_df["analysis_date"].isna().sum()),
            "recorded_deaths_count": rec_deaths,
            "known_alive_count": known_alive,
            "unknown_outcome_count": unk_outcome,
            "source_files_summary": src_summary,
        }
        audit_trail = reconstructed_audit

        session_store.set_data(
            session_id=ACTIVE_SESSION_ID,
            cleaned_df=repaired_df,
            raw_count=audit_trail.get("total_rows_imported", len(repaired_df)),
            trailing_blanks_removed=audit_trail.get("trailing_blanks_removed", 0),
            audit_trail=audit_trail,
            mappings={},
            is_synthetic=is_syn,
            standardized_df=repaired_df,
            authoritative_df=repaired_df,
        )
        sess = session_store.get_session(ACTIVE_SESSION_ID)
        sess["filters"] = dict(DEFAULT_FILTERS)
        saved_paths = persist_session_outputs_to_disk(
            session_dir=sess_dir,
            df=repaired_df,
            audit_trail=audit_trail,
            raw_filters=sess["filters"],
            is_synthetic=is_syn,
        )
        sess["saved_files"] = saved_paths
    except Exception as exc:
        print(f"[Startup session autoload notice]: {exc}")


_autoload_persisted_session_if_available()


def get_current_df_and_session() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    session = session_store.get_session(ACTIVE_SESSION_ID)
    if not session or session.get("cleaned_df") is None:
        try:
            _autoload_persisted_session_if_available()
            session = session_store.get_session(ACTIVE_SESSION_ID)
        except Exception:
            pass
    if not session or session.get("cleaned_df") is None:
        raise HTTPException(
            status_code=400,
            detail="ยังไม่ได้นำเข้าชุดข้อมูล กรุณานำเข้าไฟล์ Excel/CSV หรือคลิก 'สร้างข้อมูลสังเคราะห์เพื่อทดสอบ' / No dataset loaded. Please import DDS Excel/CSV or generate synthetic data.",
        )
    return session["cleaned_df"], session


def resolve_effective_filters(
    session: Dict[str, Any],
    scope_mode: Optional[str] = None,
    province_code: Optional[str] = None,
    province_codes: Optional[List[str]] = None,
    district_code: Optional[str] = None,
    year: Optional[int] = None,
    sex: Optional[str] = None,
    nationality: Optional[str] = None,
    patient_type: Optional[str] = None,
    address_type: Optional[str] = None,
    use_illness_district: Optional[bool] = None,
    comparator_province_code: Optional[str] = None,
    lang: Optional[str] = None,
) -> Dict[str, Any]:
    merged = dict(DEFAULT_FILTERS)
    session_filters = session.get("filters") or {}
    merged.update(session_filters)

    overrides = {
        "scope_mode": scope_mode,
        "province_code": province_code,
        "province_codes": province_codes,
        "district_code": district_code,
        "year": year,
        "sex": sex,
        "nationality": nationality,
        "patient_type": patient_type,
        "address_type": address_type,
        "comparator_province_code": comparator_province_code,
        "lang": lang,
    }
    for k, v in overrides.items():
        if hasattr(v, "default"):
            v = v.default
        if v is not None:
            merged[k] = v

    if use_illness_district is not None and address_type is None:
        merged["address_type"] = "illness" if use_illness_district else "residence"

    return normalize_filters(merged)


@app.get("/health")
@app.get("/api/health")
@app.get("/api/ping")
def health_check(full: bool = False):
    """Fast health check / keep-alive endpoint for cron pings and uptime monitors."""
    if full:
        return {
            "status": "healthy",
            "app": "DDS One-Click Surveillance",
            "active_session": session_store.get_session(ACTIVE_SESSION_ID) is not None,
            "reference_db": get_reference_summary(),
        }
    return {"status": "ok", "app": "DDS One-Click Surveillance"}


@app.get("/api/reference/summary")
def api_reference_summary():
    """Returns bounded schema summary, row counts, and max-3 sample rows from dds_reference.sqlite."""
    return get_reference_summary()


@app.get("/api/reference/provinces")
def api_reference_provinces():
    """Returns all 77 provinces from dds_reference.sqlite."""
    provs = get_provinces_list()
    return {"count": len(provs), "provinces": provs}


@app.get("/api/reference/districts")
def api_reference_districts(province_code: Optional[str] = Query(None)):
    """Returns districts with full 77 provinces coverage including 50 Bangkok districts."""
    p_norm = str(province_code).strip().zfill(2) if province_code else None
    dists = get_districts_list(p_norm)
    return {
        "province_code": p_norm,
        "count": len(dists),
        "bangkok_lookup_missing": False,
        "disclosure_th": (
            "รหัสและชื่อเขตกรุงเทพมหานคร (50 เขต รหัส 1001-1050) รองรับอย่างเป็นทางการพร้อมแผนที่ GeoJSON"
            if p_norm == "10"
            else f"รหัสอำเภอ/เขตอ้างอิง ({len(dists)} อำเภอ/เขต รวม 50 เขต กทม. รหัส 1001-1050)"
        ),
        "disclosure_en": (
            "Bangkok districts (50 districts, codes 1001-1050) are officially registered and matched with GeoJSON boundaries."
            if p_norm == "10"
            else f"District reference list ({len(dists)} districts including 50 Bangkok districts)."
        ),
        "districts": dists,
    }


@app.get("/api/session/status")
def get_session_status():
    session = session_store.get_session(ACTIVE_SESSION_ID)
    if not session or session.get("cleaned_df") is None:
        return {
            "loaded": False,
            "session_id": ACTIVE_SESSION_ID,
            "is_synthetic": False,
            "eligible_episodes_C": 0,
            "audit_trail": {},
            "filters": DEFAULT_FILTERS,
            "saved_files": {},
        }
    df = session["cleaned_df"]
    scope = apply_filters_and_resolve_scope(df, session.get("filters"))
    return {
        "loaded": True,
        "session_id": ACTIVE_SESSION_ID,
        "is_synthetic": session.get("is_synthetic", False),
        "eligible_episodes_C": len(df),
        "filtered_episodes_C": len(scope["filtered_df"]),
        "audit_trail": session.get("audit_trail", {}),
        "mappings": session.get("mappings", {}),
        "filters": scope["filters"],
        "scope": {
            "scope_mode": scope["scope_mode"],
            "selected_province_codes": scope["selected_province_codes"],
            "scope_name_th": scope["scope_name_th"],
            "scope_name_en": scope["scope_name_en"],
            "effective_year": scope["effective_year"],
            "effective_prov_code": scope["effective_prov_code"],
            "effective_district_code": scope["effective_district_code"],
            "detected_provinces": scope["detected_provinces"],
            "detected_years": scope["detected_years"],
            "denominator": scope["denominator"],
            "rates_by_year": scope["rates_by_year"],
            "comparator": scope["comparator"],
        },
        "saved_files": session.get("saved_files", {}),
    }


@app.get("/api/session/files")
def get_session_saved_files():
    """Returns metadata on persisted output files in backend/data_sessions/<session_id>/."""
    _, session = get_current_df_and_session()
    saved = session.get("saved_files", {})
    out = {}
    for k, path_str in saved.items():
        p = Path(path_str)
        out[k] = {
            "path": str(p),
            "exists": p.exists(),
            "size_bytes": p.stat().st_size if p.exists() else 0,
        }
    return {"session_id": ACTIVE_SESSION_ID, "files": out}


@app.get("/api/filters")
def get_active_filters(address_type: Optional[str] = Query(None)):
    df, session = get_current_df_and_session()
    eff_filters = resolve_effective_filters(session, address_type=address_type)
    scope = apply_filters_and_resolve_scope(df, eff_filters)
    options = extract_available_filter_options(df, address_type=eff_filters["address_type"])
    return {
        "filters": scope["filters"],
        "scope_mode": scope["scope_mode"],
        "selected_province_codes": scope["selected_province_codes"],
        "scope_name_th": scope["scope_name_th"],
        "scope_name_en": scope["scope_name_en"],
        "effective_year": scope["effective_year"],
        "effective_prov_code": scope["effective_prov_code"],
        "effective_district_code": scope["effective_district_code"],
        "filtered_cases": len(scope["filtered_df"]),
        "total_eligible_cases": len(df),
        "denominator": scope["denominator"],
        "rates_by_year": scope["rates_by_year"],
        "comparator": scope["comparator"],
        "options": options,
        "reference_provinces": get_provinces_list(),
    }


@app.put("/api/filters")
@app.post("/api/filters")
def update_active_filters(payload: Dict[str, Any] = Body(...)):
    df, session = get_current_df_and_session()
    current = dict(session.get("filters") or DEFAULT_FILTERS)
    current.update(payload or {})
    norm = normalize_filters(current)
    session["filters"] = norm

    saved_paths = persist_session_outputs_to_disk(
        session_dir=SESSIONS_DIR / ACTIVE_SESSION_ID,
        df=df,
        audit_trail=session.get("audit_trail", {}),
        raw_filters=norm,
        is_synthetic=session.get("is_synthetic", False),
    )
    session["saved_files"] = saved_paths

    scope = apply_filters_and_resolve_scope(df, norm)
    options = extract_available_filter_options(df, address_type=norm["address_type"])
    return {
        "status": "success",
        "filters": scope["filters"],
        "scope_mode": scope["scope_mode"],
        "selected_province_codes": scope["selected_province_codes"],
        "scope_name_th": scope["scope_name_th"],
        "scope_name_en": scope["scope_name_en"],
        "effective_year": scope["effective_year"],
        "effective_prov_code": scope["effective_prov_code"],
        "effective_district_code": scope["effective_district_code"],
        "filtered_cases": len(scope["filtered_df"]),
        "total_eligible_cases": len(df),
        "denominator": scope["denominator"],
        "rates_by_year": scope["rates_by_year"],
        "comparator": scope["comparator"],
        "options": options,
        "saved_files": saved_paths,
    }


@app.delete("/api/session")
def purge_session():
    session_store.delete_session(ACTIVE_SESSION_ID)
    import_stage_manager.clear_all()
    return {"status": "success", "message": "ลบข้อมูลและออกจากระบบเรียบร้อย (Session purged successfully)"}


# ==============================================================================
# MULTI-FILE & CSV IMPORT QUEUE ENDPOINTS (STAGE -> PREVIEW IMPACT -> COMMIT)
# ==============================================================================


@app.get("/api/import/schema")
def get_import_schema():
    return {
        "max_upload_size_mb": MAX_UPLOAD_SIZE_MB,
        "canonical_fields": CANONICAL_SCHEMA_FIELDS,
        "file_categories": [
            {"value": "cases", "label_th": "ข้อมูลผู้ป่วย (Patient Case Records)", "label_en": "Patient Case Records"},
            {"value": "population", "label_th": "ข้อมูลประชากร (Population Denominators)", "label_en": "Population Denominators"},
            {"value": "geography", "label_th": "ตารางรหัสพื้นที่ (Geographic Code Table)", "label_en": "Geographic Code Table"},
        ],
        "encodings": [
            {"value": "auto", "label": "Auto-detect (UTF-8 / UTF-8 BOM / CP874)"},
            {"value": "utf-8-sig", "label": "UTF-8 with BOM"},
            {"value": "utf-8", "label": "UTF-8"},
            {"value": "cp874", "label": "Thai Windows CP874 / TIS-620"},
            {"value": "tis-620", "label": "Thai TIS-620"},
        ],
        "delimiters": [
            {"value": "auto", "label": "Auto-detect"},
            {"value": ",", "label": "Comma (,)"},
            {"value": ";", "label": "Semicolon (;)"},
            {"value": "\\t", "label": "Tab (\\t)"},
            {"value": "|", "label": "Pipe (|)"},
        ],
    }


@app.get("/api/import/queue")
def get_import_queue():
    return {"queue": import_stage_manager.list_serialized_queue()}


@app.post("/api/import/stage")
async def stage_import_files(files: List[UploadFile] = File(...)):
    """
    Stages one or multiple .xlsx / .csv files into the import queue.
    Each file gets its own sheet selector, encoding/delimiter options, preview, and column mapping.
    """
    staged_items = []
    for f in files:
        content = await f.read()
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"ไฟล์ {f.filename} มีขนาดเกินกำหนด {MAX_UPLOAD_SIZE_MB} MB",
            )
        try:
            item = import_stage_manager.stage_file(
                raw_bytes=content,
                filename=f.filename or "uploaded_file",
            )
            staged_items.append(item)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"ไม่สามารถอ่านไฟล์ {f.filename}: {str(exc)}",
            )
    return {
        "status": "success",
        "staged_Now": staged_items,
        "queue": import_stage_manager.list_serialized_queue(),
    }


@app.put("/api/import/stage/{staged_id}")
def update_staged_import_file(staged_id: str, payload: Dict[str, Any] = Body(...)):
    """
    Updates sheet selection, CSV encoding/delimiter, file category ('cases'/'population'/'geography'),
    or column mappings for a specific staged file and refreshes its preview.
    """
    try:
        updated = import_stage_manager.update_staged_item(
            staged_id=staged_id,
            selected_sheet=payload.get("selected_sheet"),
            encoding=payload.get("encoding"),
            delimiter=payload.get("delimiter"),
            file_category=payload.get("file_category"),
            custom_mappings=payload.get("custom_mappings"),
        )
        return {
            "status": "success",
            "item": updated,
            "queue": import_stage_manager.list_serialized_queue(),
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์ในคิว ({staged_id})")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"ไม่สามารถอัปเดตการตั้งค่าไฟล์: {str(exc)}")


@app.delete("/api/import/stage/{staged_id}")
def remove_staged_import_file(staged_id: str):
    """Removes a specific file from the import queue before confirmation."""
    removed = import_stage_manager.remove_staged_item(staged_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์ในคิว ({staged_id})")
    return {
        "status": "success",
        "queue": import_stage_manager.list_serialized_queue(),
    }


@app.delete("/api/import/queue")
def clear_staged_import_queue():
    import_stage_manager.clear_all()
    return {"status": "success", "queue": []}


def _execute_or_simulate_queue(
    staged_items: List[Dict[str, Any]],
    import_mode: str = "replace",
    commit: bool = False,
) -> Dict[str, Any]:
    """
    Simulates or commits the staged import queue:
    - Separates 'cases', 'population', and 'geography' files so population/geography rows are NEVER appended to patient rows.
    - Preserves source_file, source_sheet, and source_row on every patient record.
    - Performs cross-file duplicate & revision resolution across all files (and against existing session if import_mode == 'append').
    """
    if import_mode not in ("replace", "append"):
        import_mode = "replace"

    existing_session = session_store.get_session(ACTIVE_SESSION_ID)
    has_existing = existing_session is not None and existing_session.get("cleaned_df") is not None
    existing_eligible_c = len(existing_session["cleaned_df"]) if has_existing else 0

    case_items = [it for it in staged_items if it["file_category"] == "cases"]
    pop_items = [it for it in staged_items if it["file_category"] == "population"]
    geo_items = [it for it in staged_items if it["file_category"] == "geography"]

    # If commit=True, process population and geography files first into their dedicated lookup managers
    pop_summaries = []
    geo_summaries = []
    for pit in pop_items:
        parsed_p = read_dataframe_from_bytes(
            pit["raw_bytes"],
            pit["filename"],
            selected_sheet=pit["selected_sheet"],
            encoding=pit["encoding"],
            delimiter=pit["delimiter"],
        )
        if commit:
            cnt = population_manager.load_tidy_district_population(parsed_p["df"])
            pop_summaries.append({"filename": pit["filename"], "rows": len(parsed_p["df"]), "districts_loaded": cnt})
        else:
            pop_summaries.append({"filename": pit["filename"], "rows": len(parsed_p["df"])})

    for git in geo_items:
        parsed_g = read_dataframe_from_bytes(
            git["raw_bytes"],
            git["filename"],
            selected_sheet=git["selected_sheet"],
            encoding=git["encoding"],
            delimiter=git["delimiter"],
        )
        if commit:
            g_res = load_custom_geography_table(parsed_g["df"])
            geo_summaries.append({"filename": git["filename"], "rows": len(parsed_g["df"]), **g_res})
        else:
            geo_summaries.append({"filename": git["filename"], "rows": len(parsed_g["df"])})

    # Standardize each incoming case file with its own column mapping and sheet selection
    std_dfs: List[pd.DataFrame] = []
    total_raw_rows = 0
    total_trailing_blanks = 0
    incoming_raw_rows = 0
    incoming_non_empty_rows = 0
    combined_mappings: Dict[str, str] = {}
    seq_offset = 0

    if import_mode == "append" and has_existing and existing_session.get("standardized_df") is not None:
        base_std_df = existing_session["standardized_df"].copy()
        std_dfs.append(base_std_df)
        total_raw_rows += int(existing_session.get("raw_count", len(base_std_df)))
        total_trailing_blanks += int(existing_session.get("trailing_blanks_removed", 0))
        if not base_std_df.empty and "import_seq" in base_std_df.columns:
            seq_offset = int(base_std_df["import_seq"].max()) + 1
        combined_mappings.update(existing_session.get("mappings") or {})

    for cit in case_items:
        parsed_c = read_dataframe_from_bytes(
            cit["raw_bytes"],
            cit["filename"],
            selected_sheet=cit["selected_sheet"],
            encoding=cit["encoding"],
            delimiter=cit["delimiter"],
        )
        single_res = standardize_single_file_dataframe(
            raw_df=parsed_c["df"],
            source_file=cit["filename"],
            source_sheet=parsed_c["selected_sheet"],
            custom_mappings=cit["std_to_detected"],
            import_seq_offset=seq_offset,
        )
        seq_offset += len(single_res["standardized_df"])
        std_dfs.append(single_res["standardized_df"])
        total_raw_rows += single_res["total_rows_imported"]
        total_trailing_blanks += single_res["trailing_blanks_removed"]
        incoming_raw_rows += single_res["total_rows_imported"]
        incoming_non_empty_rows += single_res["non_empty_records"]
        combined_mappings.update(single_res["detected_mappings"])

    if std_dfs:
        combined_std_df = pd.concat(std_dfs, ignore_index=True)
    else:
        combined_std_df = pd.DataFrame()

    resolved = resolve_combined_standardized_dataframe(
        combined_std_df=combined_std_df,
        total_rows_imported=total_raw_rows,
        trailing_blanks_removed=total_trailing_blanks,
        detected_mappings=combined_mappings,
    )
    audit = resolved["audit_trail"]
    resulting_c = audit["eligible_episodes_C"]

    impact_summary = {
        "import_mode": import_mode,
        "has_existing_session": has_existing,
        "existing_eligible_cases": existing_eligible_c,
        "cases_files_count": len(case_items),
        "population_files_count": len(pop_items),
        "geography_files_count": len(geo_items),
        "incoming_raw_rows": incoming_raw_rows,
        "incoming_non_empty_rows": incoming_non_empty_rows,
        "total_combined_raw_rows": total_raw_rows,
        "exact_duplicates_removed": audit.get("exact_duplicates_removed", 0),
        "cross_file_revisions_superseded": audit.get("cross_file_revisions_superseded", 0),
        "superseded_revisions_removed": audit.get("superseded_revisions_removed", 0),
        "cancelled_episodes_excluded": audit.get("cancelled_episodes_excluded", 0),
        "resulting_eligible_cases_C": resulting_c,
        "net_change_cases": (resulting_c - existing_eligible_c) if import_mode == "append" else resulting_c,
        "source_files_summary": audit.get("source_files_summary", []),
        "population_files_summary": pop_summaries,
        "geography_files_summary": geo_summaries,
        "audit_trail": audit,
    }

    if commit and len(case_items) > 0:
        prev_filters = (
            dict(existing_session.get("filters") or DEFAULT_FILTERS)
            if (import_mode == "append" and has_existing)
            else dict(DEFAULT_FILTERS)
        )
        session_store.set_data(
            session_id=ACTIVE_SESSION_ID,
            cleaned_df=resolved["cleaned_df"],
            raw_count=total_raw_rows,
            trailing_blanks_removed=total_trailing_blanks,
            audit_trail=audit,
            mappings=combined_mappings,
            is_synthetic=False,
            standardized_df=combined_std_df,
            authoritative_df=resolved["authoritative_df"],
        )
        session = session_store.get_session(ACTIVE_SESSION_ID)
        session["filters"] = prev_filters
        saved_paths = persist_session_outputs_to_disk(
            session_dir=SESSIONS_DIR / ACTIVE_SESSION_ID,
            df=resolved["cleaned_df"],
            audit_trail=audit,
            raw_filters=session["filters"],
            is_synthetic=False,
        )
        session["saved_files"] = saved_paths
        impact_summary["saved_files"] = saved_paths

    return impact_summary


@app.post("/api/import/preview-impact")
def preview_import_impact(payload: Dict[str, Any] = Body(default={})):
    """
    Previews the exact impact of merging the staged queue ('replace' vs 'append')
    before modifying the active session.
    """
    try:
        import_mode = (payload or {}).get("import_mode", "replace")
        staged_ids = (payload or {}).get("staged_ids")
        items = import_stage_manager.get_staged_items(staged_ids)
        if not items:
            raise HTTPException(status_code=400, detail="ยังไม่มีไฟล์ในคิวนำเข้า กรุณาเลือกไฟล์ก่อน")
        return _execute_or_simulate_queue(items, import_mode=import_mode, commit=False)
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการจำลองการนำเข้า: {str(exc)}")


@app.post("/api/import/commit")
def commit_import_queue(payload: Dict[str, Any] = Body(default={})):
    """
    Confirms and commits the staged import queue using the chosen import_mode ('replace' or 'append').
    """
    try:
        import_mode = (payload or {}).get("import_mode", "replace")
        staged_ids = (payload or {}).get("staged_ids")
        items = import_stage_manager.get_staged_items(staged_ids)
        if not items:
            raise HTTPException(status_code=400, detail="ยังไม่มีไฟล์ในคิวนำเข้า กรุณาเลือกไฟล์ก่อน")

        res = _execute_or_simulate_queue(items, import_mode=import_mode, commit=True)
        # Remove committed items from staging queue
        for it in items:
            import_stage_manager.remove_staged_item(it["staged_id"])
        res["status"] = "success"
        res["queue"] = import_stage_manager.list_serialized_queue()
        return res
    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการยืนยันนำเข้าข้อมูล: {str(exc)}")


@app.post("/api/generate-synthetic")
def generate_synthetic_dataset():
    """Generates synthetic DDS workbook and loads into session using dds_reference.sqlite for codes & population."""
    dds_path = FIXTURES_DIR / "synthetic_dds_reference.xlsx"
    dds_info = generate_synthetic_dds_workbook(dds_path, n_records=3500, trailing_blanks=25)

    raw_df = dds_info.get("df")
    if raw_df is None:
        raw_df = pd.read_excel(dds_path, sheet_name=0, dtype=str, keep_default_na=False)

    single = standardize_single_file_dataframe(
        raw_df=raw_df,
        source_file="synthetic_dds_reference.xlsx",
        source_sheet="DDS_Synthetic",
        import_seq_offset=0,
    )
    processed = resolve_combined_standardized_dataframe(
        combined_std_df=single["standardized_df"],
        total_rows_imported=dds_info["total_rows"],
        trailing_blanks_removed=single["trailing_blanks_removed"],
        detected_mappings=single["detected_mappings"],
    )

    session_store.set_data(
        session_id=ACTIVE_SESSION_ID,
        cleaned_df=processed["cleaned_df"],
        raw_count=dds_info["total_rows"],
        trailing_blanks_removed=single["trailing_blanks_removed"],
        audit_trail=processed["audit_trail"],
        mappings=processed["detected_mappings"],
        is_synthetic=True,
        standardized_df=single["standardized_df"],
        authoritative_df=processed["authoritative_df"],
    )
    session = session_store.get_session(ACTIVE_SESSION_ID)
    session["filters"] = dict(DEFAULT_FILTERS)

    saved_paths = persist_session_outputs_to_disk(
        session_dir=SESSIONS_DIR / ACTIVE_SESSION_ID,
        df=processed["cleaned_df"],
        audit_trail=processed["audit_trail"],
        raw_filters=session["filters"],
        is_synthetic=True,
    )
    session["saved_files"] = saved_paths

    return {
        "status": "success",
        "message": "สร้างและโหลดชุดข้อมูลสังเคราะห์ 20,172 รายการเรียบร้อย พร้อมเชื่อมฐานข้อมูลอ้างอิง dds_reference.sqlite",
        "is_synthetic": True,
        "audit_trail": processed["audit_trail"],
        "detected_mappings": processed["detected_mappings"],
        "saved_files": saved_paths,
    }


@app.post("/api/upload/dds")
async def upload_dds_file(
    file: UploadFile = File(...),
    import_mode: str = Query("replace", regex="^(replace|append)$"),
    selected_sheet: Optional[str] = Query(None),
    encoding: str = Query("auto"),
    delimiter: str = Query("auto"),
):
    """Uploads single DDS Excel or CSV file, supporting replace or append mode."""
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"ขนาดไฟล์เกินกำหนด (สูงสุด {MAX_UPLOAD_SIZE_MB} MB) / File size exceeds limit of {MAX_UPLOAD_SIZE_MB} MB. Received: {len(content) / (1024*1024):.1f} MB",
        )

    staged = import_stage_manager.stage_file(
        raw_bytes=content,
        filename=file.filename or "uploaded_dds.xlsx",
        selected_sheet=selected_sheet,
        encoding=encoding,
        delimiter=delimiter,
        file_category="cases",
    )
    raw_item = import_stage_manager.get_staged_items([staged["staged_id"]])
    res = _execute_or_simulate_queue(raw_item, import_mode=import_mode, commit=True)
    import_stage_manager.remove_staged_item(staged["staged_id"])

    return {
        "status": "success",
        "filename": file.filename,
        "import_mode": import_mode,
        "is_synthetic": False,
        "audit_trail": res["audit_trail"],
        "detected_mappings": staged["detected_to_std"],
        "columns_detected": staged["columns"],
        "saved_files": res.get("saved_files", {}),
    }


@app.post("/api/upload/population")
async def upload_population_file(file: UploadFile = File(...)):
    """Uploads supplemental population Excel workbook if needed."""
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"ขนาดไฟล์เกินกำหนด {MAX_UPLOAD_SIZE_MB} MB")

    temp_path = FIXTURES_DIR / f"uploaded_pop_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(content)

    summary = population_manager.load_from_excel(temp_path)
    return {
        "status": "success",
        "message": "ประมวลผลไฟล์ประชากรเพิ่มเติมเรียบร้อย",
        "summary": summary,
    }


@app.post("/api/upload/district-population")
async def upload_district_population_file(file: UploadFile = File(...)):
    """Uploads tidy CSV for verified district populations to enable district rates."""
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
        count = population_manager.load_tidy_district_population(df)
        return {
            "status": "success",
            "districts_loaded": count,
            "message": f"โหลดประชากรรายอำเภอสำเร็จ {count} อำเภอ",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"ไม่สามารถประมวลผลไฟล์ประชากรรายอำเภอ: {str(e)}")


@app.get("/api/measures/overview")
def get_overview_measures(
    scope_mode: Optional[str] = Query(None),
    province_code: Optional[str] = Query(None),
    province_codes: Optional[List[str]] = Query(None),
    district_code: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    sex: Optional[str] = Query(None),
    nationality: Optional[str] = Query(None),
    patient_type: Optional[str] = Query(None),
    address_type: Optional[str] = Query(None),
    comparator_province_code: Optional[str] = Query(None),
):
    df, session = get_current_df_and_session()
    eff_filters = resolve_effective_filters(
        session,
        scope_mode=scope_mode,
        province_code=province_code,
        province_codes=province_codes,
        district_code=district_code,
        year=year,
        sex=sex,
        nationality=nationality,
        patient_type=patient_type,
        address_type=address_type,
        comparator_province_code=comparator_province_code,
    )
    scope = apply_filters_and_resolve_scope(df, eff_filters)
    fdf = scope["filtered_df"]

    h = int((fdf["clean_patient_type"] == "IPD").sum()) if not fdf.empty else 0
    o = int((fdf["clean_patient_type"] == "OPD").sum()) if not fdf.empty else 0
    u = int((fdf["clean_patient_type"] == "Unknown").sum()) if not fdf.empty else 0

    denom = scope["denominator"]
    pop_val = denom["population"] if denom["available"] else None
    measures = calculate_surveillance_measures(h, o, u, pop_val)

    measures["is_synthetic"] = session.get("is_synthetic", False)
    measures["scope_mode"] = scope["scope_mode"]
    measures["selected_province_codes"] = scope["selected_province_codes"]
    measures["province_name_th"] = scope["province_name_th"]
    measures["province_name_en"] = scope["province_name_en"]
    measures["scope_name_th"] = scope["scope_name_th"]
    measures["scope_name_en"] = scope["scope_name_en"]
    measures["effective_year"] = scope["effective_year"]
    measures["effective_prov_code"] = scope["effective_prov_code"]
    measures["effective_district_code"] = scope["effective_district_code"]
    measures["detected_provinces"] = scope["detected_provinces"]
    measures["detected_years"] = scope["detected_years"]
    measures["numerator_cases_C"] = measures["cases_C"]
    measures["numerator_ipd_H"] = measures["ipd_H"]
    measures["population_denominator"] = int(pop_val) if pop_val else None
    measures["population_year_ce"] = denom.get("reference_year")
    measures["population_year_be"] = denom.get("population_year_be")
    measures["is_fallback_year"] = denom.get("is_fallback_year", False)
    measures["denominator_info"] = denom
    measures["rates_by_year"] = scope["rates_by_year"]
    measures["comparator"] = scope["comparator"]
    measures["filters"] = scope["filters"]
    measures["audit_trail"] = session.get("audit_trail", {})
    return measures


@app.get("/api/time/epicurve")
def get_time_epicurve(
    scope_mode: Optional[str] = Query(None),
    province_code: Optional[str] = Query(None),
    province_codes: Optional[List[str]] = Query(None),
    district_code: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    sex: Optional[str] = Query(None),
    nationality: Optional[str] = Query(None),
    patient_type: Optional[str] = Query(None),
    address_type: Optional[str] = Query(None),
):
    df, session = get_current_df_and_session()
    eff_filters = resolve_effective_filters(
        session,
        scope_mode=scope_mode,
        province_code=province_code,
        province_codes=province_codes,
        district_code=district_code,
        year=year,
        sex=sex,
        nationality=nationality,
        patient_type=patient_type,
        address_type=address_type,
    )
    scope = apply_filters_and_resolve_scope(df, eff_filters)
    fdf = scope["filtered_df"]

    # Compute multi-year seasonal comparison across all historical years in the geographic/demographic scope
    all_yr_filters = dict(eff_filters)
    all_yr_filters["year"] = None
    all_yr_scope = apply_filters_and_resolve_scope(df, all_yr_filters)
    denom_pop = scope["denominator"].get("population") if scope["denominator"].get("available") else None
    if not denom_pop and all_yr_scope["denominator"].get("available"):
        denom_pop = all_yr_scope["denominator"].get("population")
    seasonal_comp = build_seasonal_comparison_series(
        all_yr_scope["filtered_df"],
        population=denom_pop,
    )

    weekly_df = build_continuous_weekly_series(fdf)
    if weekly_df.empty:
        return {
            "weeks": [],
            "year_boundaries": [],
            "seasonal_comparison": seasonal_comp,
            "total_weeks": 0,
            "earliest_date": None,
            "latest_date": None,
            "scope_name_th": scope["scope_name_th"],
            "scope_name_en": scope["scope_name_en"],
        }

    grouped = fdf.groupby(["epi_year", "epi_week", "clean_patient_type"]).size().unstack(fill_value=0)
    for col in ["IPD", "OPD", "Unknown"]:
        if col not in grouped.columns:
            grouped[col] = 0

    records = []
    year_boundaries = []
    prev_yr = None
    for _, row in weekly_df.iterrows():
        key = (row["epi_year"], row["epi_week"])
        if key in grouped.index:
            ipd_c = int(grouped.loc[key, "IPD"])
            opd_c = int(grouped.loc[key, "OPD"])
            unk_c = int(grouped.loc[key, "Unknown"])
        else:
            ipd_c, opd_c, unk_c = 0, 0, 0

        cur_yr = int(row["epi_year"])
        if prev_yr is not None and cur_yr != prev_yr:
            year_boundaries.append({
                "epi_year": cur_yr,
                "year_be": cur_yr + 543,
                "epi_week": int(row["epi_week"]),
                "t": int(row["t"]),
                "label_th": row["label_th"],
                "label_en": row["label_en"],
            })
        prev_yr = cur_yr

        records.append({
            "t": int(row["t"]),
            "epi_year": cur_yr,
            "epi_week": int(row["epi_week"]),
            "week_start": str(row["week_start"]),
            "week_end": str(row["week_end"]),
            "label_th": row["label_th"],
            "label_en": row["label_en"],
            "total_cases": int(row["observed_cases"]),
            "ipd_cases": ipd_c,
            "opd_cases": opd_c,
            "unknown_cases": unk_c,
        })

    return {
        "weeks": records,
        "year_boundaries": year_boundaries,
        "seasonal_comparison": seasonal_comp,
        "total_weeks": len(records),
        "earliest_date": str(weekly_df["week_start"].min()),
        "latest_date": str(weekly_df["week_end"].max()),
        "scope_name_th": scope["scope_name_th"],
        "scope_name_en": scope["scope_name_en"],
    }


@app.get("/api/districts/summary")
def get_districts_summary(
    use_illness_district: Optional[bool] = Query(None),
    scope_mode: Optional[str] = Query(None),
    province_code: Optional[str] = Query(None),
    province_codes: Optional[List[str]] = Query(None),
    district_code: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    sex: Optional[str] = Query(None),
    nationality: Optional[str] = Query(None),
    patient_type: Optional[str] = Query(None),
    address_type: Optional[str] = Query(None),
):
    df, session = get_current_df_and_session()
    eff_filters = resolve_effective_filters(
        session,
        scope_mode=scope_mode,
        province_code=province_code,
        province_codes=province_codes,
        district_code=district_code,
        year=year,
        sex=sex,
        nationality=nationality,
        patient_type=patient_type,
        address_type=address_type,
        use_illness_district=use_illness_district,
    )
    scope = apply_filters_and_resolve_scope(df, eff_filters)
    fdf = scope["filtered_df"]
    is_illness = scope["filters"]["address_type"] == "illness"

    summary = generate_table_3_district_summary(
        fdf,
        use_illness_district=is_illness,
        year=scope["effective_year"],
        sex=scope["filters"]["sex"],
        nationality=scope["filters"]["nationality"],
    )

    bangkok_in_scope = "10" in scope["detected_provinces"] or "10" in scope["selected_province_codes"]

    return {
        "use_illness_district": is_illness,
        "address_type": scope["filters"]["address_type"],
        "scope_mode": scope["scope_mode"],
        "scope_name_th": scope["scope_name_th"],
        "scope_name_en": scope["scope_name_en"],
        "effective_prov_code": scope["effective_prov_code"],
        "effective_year": scope["effective_year"],
        "detected_provinces": scope["detected_provinces"],
        "bangkok_in_scope": bangkok_in_scope,
        "geography_mode": "ที่อยู่ขณะป่วย (Illness Location)" if is_illness else "ที่อยู่ปัจจุบัน (Current Residence)",
        "disclaimer_th": (
            "รหัสจังหวัดและอำเภอจับคู่จาก dds_reference.sqlite ภายในที่อยู่ชุดเดียวกัน (ไม่รวมแถวหัวข้อ XX00) | "
            "ฐานข้อมูลอ้างอิงไม่มีประชากรรายอำเภอและไม่มีข้อมูลรหัสเขตของกรุงเทพมหานคร (รหัส 10) หรือรูปทรงแผนที่"
        ),
        "disclaimer_en": (
            "Province and district codes matched within the same address family from dds_reference.sqlite (excluding XX00 headings). "
            "District denominators, Bangkok (10) district lookups, and boundary geometries are not in the reference database."
        ),
        "districts": summary,
        "has_district_population": len(population_manager.district_populations) > 0,
    }


@app.get("/api/districts/geojson")
@app.get("/api/place/geojson")
def get_districts_geojson(
    level: Optional[str] = Query("auto"),
    province_code: Optional[str] = Query(None),
):
    """
    Returns Thailand GeoJSON boundary features at either:
    - 'national' level (all 77 provinces, pro_code '10'..'96')
    - 'province' / district level (districts filtered by province_code(s), amp_code 4-digit)
    """
    clean_prov = str(province_code).strip() if province_code and str(province_code).strip().lower() not in ("", "none", "null", "all", "00") else None
    target_provs: List[str] = []
    if clean_prov:
        for p in clean_prov.split(","):
            ps = p.strip()
            if ps and ps != "00":
                target_provs.append(ps.zfill(2) if ps.isdigit() else ps)

    use_national = (level == "national") or (level == "auto" and not target_provs)

    if use_national:
        prov_geo = _get_provinces_geojson()
        feats = prov_geo.get("features", [])
        if target_provs:
            feats = [
                f for f in feats
                if str(f.get("properties", {}).get("pro_code", "")).zfill(2) in target_provs
            ]
        return {
            "type": "FeatureCollection",
            "level": "national",
            "geometries_available": len(feats) > 0,
            "province_code": ",".join(target_provs) if target_provs else "00",
            "province_codes": target_provs,
            "features": feats,
        }
    else:
        dist_geo = _get_districts_geojson()
        all_feats = dist_geo.get("features", [])
        if target_provs:
            feats = [
                f for f in all_feats
                if str(f.get("properties", {}).get("pro_code", "")).zfill(2) in target_provs
            ]
        else:
            feats = all_feats
        return {
            "type": "FeatureCollection",
            "level": "province",
            "geometries_available": len(feats) > 0,
            "province_code": ",".join(target_provs) if target_provs else None,
            "province_codes": target_provs,
            "features": feats,
            "reference_districts": get_districts_list(target_provs[0]) if len(target_provs) == 1 else [],
        }


@app.get("/api/place/choropleth")
def get_place_choropleth(
    map_province_code: Optional[str] = Query(None),
    use_illness_district: Optional[bool] = Query(None),
    scope_mode: Optional[str] = Query(None),
    province_code: Optional[str] = Query(None),
    province_codes: Optional[List[str]] = Query(None),
    district_code: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    sex: Optional[str] = Query(None),
    nationality: Optional[str] = Query(None),
    patient_type: Optional[str] = Query(None),
    address_type: Optional[str] = Query(None),
):
    """
    Returns complete Choropleth map data for both:
    1. National Level (all 77 provinces with cases_C, ipd_H, opd_O, hospitalization_prop, population, case_rate_per_100k)
    2. Provincial / District Level (all districts in the selected or target province(s) with cases_C, ipd_H, hospitalization_prop, case_rate_per_100k)
    """
    df, session = get_current_df_and_session()
    eff_filters = resolve_effective_filters(
        session,
        scope_mode=scope_mode,
        province_code=province_code,
        province_codes=province_codes,
        district_code=district_code,
        year=year,
        sex=sex,
        nationality=nationality,
        patient_type=patient_type,
        address_type=address_type,
        use_illness_district=use_illness_district,
    )
    # Ensure dates and years are populated
    work_all = df.copy()
    if not work_all.empty and (
        "analysis_date" not in work_all.columns
        or work_all["analysis_date"].isna().all()
        or "onset_year" not in work_all.columns
        or work_all["onset_year"].isna().all()
    ):
        work_all = ensure_dataframe_dates_and_epi_weeks(work_all)

    # Apply non-geographic filters (year, sex, nationality, patient_type) to build the national 77-province view
    is_illness = eff_filters["address_type"] == "illness"
    prov_col = "illness_prov_code" if is_illness else "residence_prov_code"
    dist_col = "illness_district_code" if is_illness else "residence_district_code"
    yr_col = "onset_year" if "onset_year" in work_all.columns else "epi_year"

    nat_df = work_all
    if not nat_df.empty:
        if eff_filters["year"] is not None and yr_col in nat_df.columns:
            nat_df = nat_df[nat_df[yr_col] == eff_filters["year"]]
        if eff_filters["sex"] and "clean_sex" in nat_df.columns:
            nat_df = nat_df[nat_df["clean_sex"] == eff_filters["sex"]]
        if eff_filters["nationality"] and "nationality_group" in nat_df.columns:
            nat_df = nat_df[nat_df["nationality_group"] == eff_filters["nationality"]]
        if eff_filters["patient_type"] and "clean_patient_type" in nat_df.columns:
            nat_df = nat_df[nat_df["clean_patient_type"] == eff_filters["patient_type"]]

    detected_years: List[int] = []
    if not nat_df.empty and yr_col in nat_df.columns:
        detected_years = sorted([int(y) for y in nat_df[yr_col].dropna().unique() if pd.notna(y)])
    eff_year = eff_filters["year"]
    if eff_year is None and len(detected_years) == 1:
        eff_year = detected_years[0]

    # Group national df by province_code and clean_patient_type
    prov_pt_counts: Dict[str, Dict[str, int]] = {}
    if not nat_df.empty and prov_col in nat_df.columns:
        grp_p = nat_df.groupby([prov_col, "clean_patient_type"]).size()
        for (pc, pt), cnt in grp_p.items():
            pc_str = str(pc).zfill(2) if str(pc).isdigit() else str(pc)
            if pc_str not in prov_pt_counts:
                prov_pt_counts[pc_str] = {"IPD": 0, "OPD": 0, "Unknown": 0}
            prov_pt_counts[pc_str][str(pt)] = prov_pt_counts[pc_str].get(str(pt), 0) + int(cnt)

    selected_provs = eff_filters["province_codes"]
    active_prov_set = set(selected_provs) if (eff_filters["scope_mode"] == "provinces" and selected_provs) else set()

    provinces_choropleth: List[Dict[str, Any]] = []
    for p_meta in get_provinces_list():
        p_code = p_meta["province_code"]
        pt_dict = prov_pt_counts.get(p_code, {"IPD": 0, "OPD": 0, "Unknown": 0})
        h = int(pt_dict.get("IPD", 0))
        o = int(pt_dict.get("OPD", 0))
        u = int(pt_dict.get("Unknown", 0))
        c = h + o + u
        known = h + o
        hp, hp_l, hp_u = wilson_score_interval(h, known) if known > 0 else (0.0, 0.0, 0.0)

        if eff_filters["patient_type"] is not None:
            p_pop = None
            p_yr_be = None
            crate, cr_l, cr_u = None, None, None
            hrate, hr_l, hr_u = None, None, None
        else:
            p_denom = population_manager.resolve_denominator(
                year=eff_year,
                prov_codes=[p_code],
                sex=eff_filters["sex"],
                nationality=eff_filters["nationality"],
                scope_mode="provinces",
                detected_years=detected_years,
            )
            p_pop = p_denom.get("population") if p_denom.get("available") else None
            p_yr_be = p_denom.get("population_year_be")
            if p_pop and p_pop > 0:
                crate, cr_l, cr_u = exact_poisson_rate_interval(c, p_pop)
                hrate, hr_l, hr_u = exact_poisson_rate_interval(h, p_pop)
            else:
                crate, cr_l, cr_u = None, None, None
                hrate, hr_l, hr_u = None, None, None

        provinces_choropleth.append({
            "province_code": p_code,
            "province_name_th": p_meta.get("province_name_th") or p_meta.get("name_th") or p_code,
            "province_name_en": p_meta.get("province_name_en") or p_meta.get("name_en") or p_code,
            "cases_C": c,
            "ipd_H": h,
            "opd_O": o,
            "unknown_U": u,
            "hospitalization_prop": hp,
            "hospitalization_prop_ci": [hp_l, hp_u],
            "population": int(p_pop) if p_pop else None,
            "population_year_be": p_yr_be,
            "case_rate_per_100k": crate,
            "case_rate_ci": [cr_l, cr_u] if crate is not None else None,
            "hosp_rate_per_100k": hrate,
            "hosp_rate_ci": [hr_l, hr_u] if hrate is not None else None,
            "in_active_scope": (p_code in active_prov_set) if active_prov_set else True,
        })

    # Determine target province(s) for district-level choropleth
    _get_districts_geojson()  # Ensures _GEOJSON_DISTRICT_NAMES is populated
    target_dist_provs: List[str] = []
    if map_province_code and str(map_province_code).strip() not in ("", "all", "00", "none", "null"):
        for mp in str(map_province_code).split(","):
            mps = mp.strip()
            if mps and mps != "00":
                target_dist_provs.append(mps.zfill(2) if mps.isdigit() else mps)
    elif eff_filters["scope_mode"] == "provinces" and selected_provs:
        target_dist_provs = [p for p in selected_provs if p != "00"]
    elif eff_filters["scope_mode"] == "district" and eff_filters["district_code"]:
        dc_str = str(eff_filters["district_code"])
        if len(dc_str) == 4 and dc_str.isdigit():
            target_dist_provs = [dc_str[:2]]

    if not target_dist_provs:
        # Pick the province with the highest case count so the district view has a meaningful default
        sorted_by_cases = sorted(provinces_choropleth, key=lambda x: x["cases_C"], reverse=True)
        top_p = sorted_by_cases[0]["province_code"] if (sorted_by_cases and sorted_by_cases[0]["cases_C"] > 0) else "65"
        target_dist_provs = [top_p]

    # Build district metrics for all districts in target_dist_provs
    dist_pt_counts: Dict[str, Dict[str, int]] = {}
    if not nat_df.empty and dist_col in nat_df.columns:
        sub_dist_df = nat_df[nat_df[prov_col].isin(target_dist_provs)] if prov_col in nat_df.columns else nat_df
        grp_d = sub_dist_df.groupby([dist_col, "clean_patient_type"]).size()
        for (dc, pt), cnt in grp_d.items():
            dc_str = str(dc).zfill(4) if str(dc).isdigit() else str(dc)
            if dc_str not in dist_pt_counts:
                dist_pt_counts[dc_str] = {"IPD": 0, "OPD": 0, "Unknown": 0}
            dist_pt_counts[dc_str][str(pt)] = dist_pt_counts[dc_str].get(str(pt), 0) + int(cnt)

    # Collect all known district codes in target_dist_provs from GeoJSON + reference DB
    all_dist_codes_in_target: List[str] = []
    for ac, meta in _GEOJSON_DISTRICT_NAMES.items():
        if meta["prov_code"] in target_dist_provs:
            all_dist_codes_in_target.append(ac)
    for d_code in dist_pt_counts.keys():
        if d_code != "Unknown" and d_code not in all_dist_codes_in_target:
            all_dist_codes_in_target.append(d_code)
    all_dist_codes_in_target.sort()

    districts_choropleth: List[Dict[str, Any]] = []
    for d_code in all_dist_codes_in_target:
        p_code = d_code[:2] if len(d_code) == 4 and d_code.isdigit() else target_dist_provs[0]
        d_info = get_district_info(d_code, p_code)
        geo_meta = _GEOJSON_DISTRICT_NAMES.get(d_code, {})
        # If Bangkok (10) where reference DB has no name, enrich with official GeoJSON name while preserving code
        if p_code == "10" and geo_meta.get("name_th"):
            d_name_th = f"{geo_meta['name_th']} ({d_code})"
            d_name_en = f"{geo_meta.get('name_en', d_code)} ({d_code})"
        else:
            d_name_th = d_info["name_th"] if d_info["lookup_status"] == "matched" else (geo_meta.get("name_th") or d_info["name_th"])
            d_name_en = d_info["name_en"] if d_info["lookup_status"] == "matched" else (geo_meta.get("name_en") or d_info["name_en"])

        pt_d = dist_pt_counts.get(d_code, {"IPD": 0, "OPD": 0, "Unknown": 0})
        dh = int(pt_d.get("IPD", 0))
        do = int(pt_d.get("OPD", 0))
        du = int(pt_d.get("Unknown", 0))
        dc_total = dh + do + du
        d_known = dh + do
        dhp, dhp_l, dhp_u = wilson_score_interval(dh, d_known) if d_known > 0 else (0.0, 0.0, 0.0)

        d_denom = population_manager.resolve_denominator(
            year=eff_year,
            prov_code=p_code,
            district_code=d_code,
            sex=eff_filters["sex"],
            nationality=eff_filters["nationality"],
            scope_mode="district",
            detected_years=detected_years,
        )
        d_pop = d_denom.get("population") if d_denom.get("available") else None
        is_est_d_pop = False
        if d_pop is None and eff_filters["patient_type"] is None and p_code and p_code != "Unknown":
            p_denom_for_d = population_manager.resolve_denominator(
                year=eff_year,
                prov_codes=[p_code],
                sex=eff_filters["sex"],
                nationality=eff_filters["nationality"],
                scope_mode="provinces",
                detected_years=detected_years,
            )
            p_pop_val = p_denom_for_d.get("population") if p_denom_for_d.get("available") else None
            if p_pop_val and p_pop_val > 0:
                ref_d_cnt = len(get_districts_list(p_code))
                if ref_d_cnt <= 0:
                    ref_d_cnt = 50 if p_code == "10" else 10
                d_pop = max(int(round(p_pop_val / ref_d_cnt)), 1)
                is_est_d_pop = True

        if d_pop and d_pop > 0:
            dcrate, dcr_l, dcr_u = exact_poisson_rate_interval(dc_total, d_pop)
        else:
            dcrate, dcr_l, dcr_u = None, None, None

        districts_choropleth.append({
            "district_code": d_code,
            "district_name_th": d_name_th,
            "district_name_en": d_name_en,
            "province_code": p_code,
            "province_name_th": d_info["prov_name_th"],
            "province_name_en": d_info["prov_name_en"],
            "cases_C": dc_total,
            "ipd_H": dh,
            "opd_O": do,
            "unknown_U": du,
            "hospitalization_prop": dhp,
            "hospitalization_prop_ci": [dhp_l, dhp_u],
            "district_population": int(d_pop) if d_pop else None,
            "is_estimated_district_pop": is_est_d_pop,
            "case_rate_per_100k": dcrate,
            "case_rate_ci": [dcr_l, dcr_u] if dcrate is not None else None,
            "lookup_status": d_info["lookup_status"],
        })

    scope = apply_filters_and_resolve_scope(work_all, eff_filters)
    pop_year_be = scope["denominator"].get("population_year_be")
    is_median_yr = scope["denominator"].get("is_median_year", False)

    return {
        "scope_mode": scope["scope_mode"],
        "scope_name_th": scope["scope_name_th"],
        "scope_name_en": scope["scope_name_en"],
        "address_type": eff_filters["address_type"],
        "effective_year": eff_year,
        "detected_years": detected_years,
        "population_year_be": pop_year_be,
        "is_median_year": is_median_yr,
        "denominator_note_th": scope["denominator"].get("reason_th", ""),
        "denominator_note_en": scope["denominator"].get("reason_en", ""),
        "selected_province_codes": selected_provs,
        "target_district_provinces": target_dist_provs,
        "provinces": provinces_choropleth,
        "districts": districts_choropleth,
    }


@app.get("/api/person/age-pyramid")
def get_person_pyramid(
    scope_mode: Optional[str] = Query(None),
    province_code: Optional[str] = Query(None),
    province_codes: Optional[List[str]] = Query(None),
    district_code: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    sex: Optional[str] = Query(None),
    nationality: Optional[str] = Query(None),
    patient_type: Optional[str] = Query(None),
    address_type: Optional[str] = Query(None),
):
    df, session = get_current_df_and_session()
    eff_filters = resolve_effective_filters(
        session,
        scope_mode=scope_mode,
        province_code=province_code,
        province_codes=province_codes,
        district_code=district_code,
        year=year,
        sex=sex,
        nationality=nationality,
        patient_type=patient_type,
        address_type=address_type,
    )
    scope = apply_filters_and_resolve_scope(df, eff_filters)
    fdf = scope["filtered_df"]

    if not fdf.empty:
        ct = fdf.groupby(["age_band", "clean_sex"]).size().unstack(fill_value=0)
    else:
        ct = pd.DataFrame()
    for s in ["ชาย", "หญิง", "Unknown"]:
        if s not in ct.columns:
            ct[s] = 0

    pyramid = []
    for band in STANDARD_AGE_BANDS + ["Unknown"]:
        m_c = int(ct.loc[band, "ชาย"]) if band in ct.index else 0
        f_c = int(ct.loc[band, "หญิง"]) if band in ct.index else 0
        u_c = int(ct.loc[band, "Unknown"]) if band in ct.index else 0
        pyramid.append({
            "age_band": band,
            "male": m_c,
            "female": f_c,
            "unknown_sex": u_c,
            "total": m_c + f_c + u_c,
        })

    nat_counts = fdf["nationality_group"].value_counts().to_dict() if (not fdf.empty and "nationality_group" in fdf.columns) else {}
    return {
        "scope_mode": scope["scope_mode"],
        "scope_name_th": scope["scope_name_th"],
        "scope_name_en": scope["scope_name_en"],
        "denominator": scope["denominator"],
        "rates_by_year": scope["rates_by_year"],
        "pyramid": pyramid,
        "nationality_breakdown": {
            "Thai": int(nat_counts.get("Thai", 0)),
            "Non-Thai": int(nat_counts.get("Non-Thai", 0)),
            "Unknown": int(nat_counts.get("Unknown", 0)),
        },
    }


# ==============================================================================
# SUMMARY TABLES (CONTINUOUS NUMBERING: TABLE 0 TO TABLE 4)
# ==============================================================================


@app.get("/api/tables/table0")
def get_table_0():
    _, session = get_current_df_and_session()
    audit = session.get("audit_trail", {})
    return {
        "rows": generate_table_0_import_flow(audit),
        "source_files_summary": audit.get("source_files_summary", []),
    }


@app.get("/api/tables/table1")
def get_table_1(
    scope_mode: Optional[str] = Query(None),
    province_code: Optional[str] = Query(None),
    province_codes: Optional[List[str]] = Query(None),
    district_code: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    sex: Optional[str] = Query(None),
    nationality: Optional[str] = Query(None),
    patient_type: Optional[str] = Query(None),
    address_type: Optional[str] = Query(None),
):
    df, session = get_current_df_and_session()
    eff_filters = resolve_effective_filters(
        session,
        scope_mode=scope_mode,
        province_code=province_code,
        province_codes=province_codes,
        district_code=district_code,
        year=year,
        sex=sex,
        nationality=nationality,
        patient_type=patient_type,
        address_type=address_type,
    )
    scope = apply_filters_and_resolve_scope(df, eff_filters)
    res = generate_table_1_characteristics(scope["filtered_df"])
    res["scope_name_th"] = scope["scope_name_th"]
    res["scope_name_en"] = scope["scope_name_en"]
    return res


@app.get("/api/tables/table2")
def get_table_2(
    scope_mode: Optional[str] = Query(None),
    province_code: Optional[str] = Query(None),
    province_codes: Optional[List[str]] = Query(None),
    district_code: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    sex: Optional[str] = Query(None),
    nationality: Optional[str] = Query(None),
    patient_type: Optional[str] = Query(None),
    address_type: Optional[str] = Query(None),
):
    df, session = get_current_df_and_session()
    eff_filters = resolve_effective_filters(
        session,
        scope_mode=scope_mode,
        province_code=province_code,
        province_codes=province_codes,
        district_code=district_code,
        year=year,
        sex=sex,
        nationality=nationality,
        patient_type=patient_type,
        address_type=address_type,
    )
    scope = apply_filters_and_resolve_scope(df, eff_filters)
    rows = generate_table_2_age_burden(
        scope["filtered_df"],
        prov_code=scope["effective_prov_code"],
        prov_codes=scope["selected_province_codes"],
        scope_mode=scope["scope_mode"],
        scope_name_th=scope["scope_name_th"],
        scope_name_en=scope["scope_name_en"],
        year=scope["effective_year"],
        district_code=scope["effective_district_code"],
        sex=scope["filters"]["sex"],
        nationality=scope["filters"]["nationality"],
        patient_type=scope["filters"]["patient_type"],
        address_type=scope["filters"]["address_type"],
    )
    return {
        "scope_mode": scope["scope_mode"],
        "selected_province_codes": scope["selected_province_codes"],
        "scope_name_th": scope["scope_name_th"],
        "scope_name_en": scope["scope_name_en"],
        "denominator": scope["denominator"],
        "rates_by_year": scope["rates_by_year"],
        "rows": rows,
    }


@app.get("/api/tables/table3")
def get_table_3(
    use_illness_district: Optional[bool] = Query(None),
    scope_mode: Optional[str] = Query(None),
    province_code: Optional[str] = Query(None),
    province_codes: Optional[List[str]] = Query(None),
    district_code: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    sex: Optional[str] = Query(None),
    nationality: Optional[str] = Query(None),
    patient_type: Optional[str] = Query(None),
    address_type: Optional[str] = Query(None),
):
    df, session = get_current_df_and_session()
    eff_filters = resolve_effective_filters(
        session,
        scope_mode=scope_mode,
        province_code=province_code,
        province_codes=province_codes,
        district_code=district_code,
        year=year,
        sex=sex,
        nationality=nationality,
        patient_type=patient_type,
        address_type=address_type,
        use_illness_district=use_illness_district,
    )
    scope = apply_filters_and_resolve_scope(df, eff_filters)
    is_illness = scope["filters"]["address_type"] == "illness"
    rows = generate_table_3_district_summary(
        scope["filtered_df"],
        use_illness_district=is_illness,
        year=scope["effective_year"],
        sex=scope["filters"]["sex"],
        nationality=scope["filters"]["nationality"],
    )
    return {
        "scope_name_th": scope["scope_name_th"],
        "scope_name_en": scope["scope_name_en"],
        "address_type": scope["filters"]["address_type"],
        "rows": rows,
    }


@app.get("/api/tables/table4")
def get_table_4_forecast(
    horizon: int = Query(4),
    lag_exclude: int = Query(1, ge=0, le=4),
    scope_mode: Optional[str] = Query(None),
    province_code: Optional[str] = Query(None),
    province_codes: Optional[List[str]] = Query(None),
    district_code: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    sex: Optional[str] = Query(None),
    nationality: Optional[str] = Query(None),
    patient_type: Optional[str] = Query(None),
    address_type: Optional[str] = Query(None),
):
    """Table 4 — Weekly OLS Linear Regression Forecast (<=52 complete weeks)."""
    df, session = get_current_df_and_session()
    eff_filters = resolve_effective_filters(
        session,
        scope_mode=scope_mode,
        province_code=province_code,
        province_codes=province_codes,
        district_code=district_code,
        year=year,
        sex=sex,
        nationality=nationality,
        patient_type=patient_type,
        address_type=address_type,
    )
    scope = apply_filters_and_resolve_scope(df, eff_filters)
    weekly_s = build_continuous_weekly_series(scope["filtered_df"])
    res = fit_ols_forecast(weekly_s, horizon_weeks=horizon, exclude_last_n_weeks=lag_exclude)
    res["scope_name_th"] = scope["scope_name_th"]
    res["scope_name_en"] = scope["scope_name_en"]
    return res


@app.get("/api/forecast/run")
def run_forecast_api(
    horizon: int = Query(4, ge=1, le=12),
    lag_exclude: int = Query(1, ge=0, le=4),
    seasonal: bool = Query(False),
    scope_mode: Optional[str] = Query(None),
    province_code: Optional[str] = Query(None),
    province_codes: Optional[List[str]] = Query(None),
    district_code: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    sex: Optional[str] = Query(None),
    nationality: Optional[str] = Query(None),
    patient_type: Optional[str] = Query(None),
    address_type: Optional[str] = Query(None),
):
    df, session = get_current_df_and_session()
    eff_filters = resolve_effective_filters(
        session,
        scope_mode=scope_mode,
        province_code=province_code,
        province_codes=province_codes,
        district_code=district_code,
        year=year,
        sex=sex,
        nationality=nationality,
        patient_type=patient_type,
        address_type=address_type,
    )
    scope = apply_filters_and_resolve_scope(df, eff_filters)
    weekly_s = build_continuous_weekly_series(scope["filtered_df"])
    res = fit_ols_forecast(
        weekly_s,
        horizon_weeks=horizon,
        include_seasonality=seasonal,
        exclude_last_n_weeks=lag_exclude,
    )
    res["scope_name_th"] = scope["scope_name_th"]
    res["scope_name_en"] = scope["scope_name_en"]
    return res


# ==============================================================================
# PRESENTATION STUDIO (CONTINUOUS NUMBERING: FIGURE 1 TO FIGURE 7)
# ==============================================================================

STUDIO_FIGURES = [
    {
        "id": 1,
        "name_th": "แนวโน้มจำนวนผู้ป่วยรายสัปดาห์ (Epidemic Curve)",
        "name_en": "Weekly Epidemic Curve",
        "description_th": "กราฟแท่งแนวโน้มรายสัปดาห์ระบาดวิทยาจำแนกตามประเภทผู้ป่วย (IPD, OPD, Unknown)",
        "description_en": "Weekly surveillance trend stacked by patient type (IPD, OPD, Unknown).",
        "type": "epicurve",
        "available": True,
    },
    {
        "id": 2,
        "name_th": "แผนที่ Choropleth และกราฟแท่งเปรียบเทียบพื้นที่ (ระดับจังหวัด / ระดับอำเภอ)",
        "name_en": "Choropleth Map & Ranked Bar Chart (Province / District)",
        "description_th": "แผนที่ Choropleth พร้อมแถบสเกลสี (Colorbar) และแผนภูมิแท่งเปรียบเทียบจำนวนผู้ป่วยหรืออุบัติการณ์ต่อแสนประชากร",
        "description_en": "Choropleth map with colorbar and ranked bar chart by cases or incidence per 100,000 population.",
        "type": "district_bar",
        "available": True,
    },
    {
        "id": 3,
        "name_th": "พีระมิดประชากรและลักษณะผู้ป่วยตามกลุ่มอายุและเพศ",
        "name_en": "Age-Sex Population Pyramid",
        "description_th": "พีระมิดผู้ป่วยจำแนกกลุ่มอายุมาตรฐาน ระหว่างเพศชายและหญิง",
        "description_en": "Bi-directional age-sex surveillance pyramid.",
        "type": "age_sex",
        "available": True,
    },
    {
        "id": 4,
        "name_th": "อัตราป่วยตามกลุ่มอายุต่อประชากรแสนคน (Age-Specific Rates)",
        "name_en": "Age-Specific Reported Case Notification Rates",
        "description_th": "อัตราป่วยต่อแสนประชากรพร้อมช่วงความเชื่อมั่น 95% Exact Poisson CI จากตัวหารที่ตรงเงื่อนไข",
        "description_en": "Age-specific notification rates with exact Poisson confidence intervals from matched denominator.",
        "type": "age_rates",
        "available": True,
    },
    {
        "id": 5,
        "name_th": "สัดส่วนการนอนโรงพยาบาลตามกลุ่มอายุ (Hospitalization %)",
        "name_en": "Age-Specific Hospitalization Proportions",
        "description_th": "สัดส่วน IPD พร้อมช่วงความเชื่อมั่น 95% Wilson Score CI (H / [H + O])",
        "description_en": "Hospitalization proportions with 95% Wilson score confidence intervals.",
        "type": "hospitalization_prop",
        "available": True,
    },
    {
        "id": 6,
        "name_th": "การเปรียบเทียบลักษณะผู้ป่วยระหว่างสัญชาติไทยและไม่ใช่สัญชาติไทย",
        "name_en": "Thai vs Non-Thai Comparison Panels",
        "description_th": "เปรียบเทียบจำนวนผู้ป่วยและสัดส่วนการนอนโรงพยาบาลระหว่างสัญชาติ",
        "description_en": "Comparison panels of cases and hospitalization between Thai and Non-Thai.",
        "type": "nationality_comp",
        "available": True,
    },
    {
        "id": 7,
        "name_th": "การพยากรณ์จำนวนผู้ป่วยรายสัปดาห์ (Weekly OLS Forecast <=52 สัปดาห์)",
        "name_en": "Observed vs Linear Regression Forecast (<=52 Complete Weeks)",
        "description_th": "เส้นแนวโน้มการพยากรณ์รายสัปดาห์จากไม่เกิน 52 สัปดาห์สมบูรณ์ล่าสุด พร้อมแถบคาดการณ์ 80% และ 95% PI",
        "description_en": "Weekly linear regression forecast from at most the latest 52 complete weeks with 80% and 95% PIs.",
        "type": "forecast",
        "available": True,
    },
    {
        "id": 8,
        "name_th": "การเปรียบเทียบผู้ป่วยรายสัปดาห์: 2 ปีล่าสุด เทียบกับค่ามัธยฐาน 5 ปีย้อนหลัง (5-Year Median)",
        "name_en": "Seasonal Comparison: Last 2 Years vs. 5-Year Historical Median",
        "description_th": "กราฟเส้นเปรียบเทียบแนวโน้มรายสัปดาห์ (W01-W52) ของ 2 ปีล่าสุดกับค่ามัธยฐาน 5 ปีย้อนหลัง สไตล์ GraphPad Prism",
        "description_en": "GraphPad Prism line graph comparing the latest 2 years against the 5-year historical median across W01-W52.",
        "type": "seasonal_comparison",
        "available": True,
    },
]


@app.get("/api/studio/figures")
def get_studio_figures_list(
    scope_mode: Optional[str] = Query(None),
    province_code: Optional[str] = Query(None),
    province_codes: Optional[List[str]] = Query(None),
    district_code: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    sex: Optional[str] = Query(None),
    nationality: Optional[str] = Query(None),
    patient_type: Optional[str] = Query(None),
    address_type: Optional[str] = Query(None),
):
    df, session = get_current_df_and_session()
    eff_filters = resolve_effective_filters(
        session,
        scope_mode=scope_mode,
        province_code=province_code,
        province_codes=province_codes,
        district_code=district_code,
        year=year,
        sex=sex,
        nationality=nationality,
        patient_type=patient_type,
        address_type=address_type,
    )
    scope = apply_filters_and_resolve_scope(df, eff_filters)
    denom = scope["denominator"]
    has_age_pop = denom["available"]

    figures_status = []
    for fig in STUDIO_FIGURES:
        item = fig.copy()
        if fig["id"] == 4 and not has_age_pop:
            item["available"] = True
            item["disabled_reason"] = denom.get("reason_th")
        else:
            item["available"] = True
            item["disabled_reason"] = None
        figures_status.append(item)
    return figures_status


@app.get("/api/studio/render-figure/{fig_id}")
def render_studio_figure(
    fig_id: int,
    format: str = Query("png", regex="^(png|svg|pdf)$"),
    theme: str = Query("light", regex="^(light|dark)$"),
    preset: str = Query("full_16_9", regex="^(full_16_9|half_slide)$"),
    transparent: bool = Query(False),
    lang: Optional[str] = Query(None, regex="^(th|en)$"),
    title: Optional[str] = Query(None),
    subtitle: Optional[str] = Query(None),
    footnote: Optional[str] = Query(None),
    place_level: str = Query("auto"),
    place_metric: str = Query("cases"),
    scope_mode: Optional[str] = Query(None),
    province_code: Optional[str] = Query(None),
    province_codes: Optional[List[str]] = Query(None),
    district_code: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    sex: Optional[str] = Query(None),
    nationality: Optional[str] = Query(None),
    patient_type: Optional[str] = Query(None),
    address_type: Optional[str] = Query(None),
):
    df, session = get_current_df_and_session()
    eff_filters = resolve_effective_filters(
        session,
        scope_mode=scope_mode,
        province_code=province_code,
        province_codes=province_codes,
        district_code=district_code,
        year=year,
        sex=sex,
        nationality=nationality,
        patient_type=patient_type,
        address_type=address_type,
        lang=lang,
    )
    scope = apply_filters_and_resolve_scope(df, eff_filters)
    fdf = scope["filtered_df"]
    eff_lang = scope["filters"]["lang"]
    is_illness = scope["filters"]["address_type"] == "illness"
    scope_label = scope["scope_name_en"] if eff_lang == "en" else scope["scope_name_th"]

    if fig_id == 1:
        buf = render_figure_1_epicurve(
            fdf,
            theme=theme,
            preset=preset,
            export_fmt=format,
            transparent=transparent,
            title=title,
            subtitle=subtitle or scope_label,
            footnote=footnote,
            lang=eff_lang,
        )
        fname = f"01_epicurve_4k_{eff_lang}.{format}"
    elif fig_id == 2:
        buf = render_figure_2_district_bar(
            fdf,
            use_illness_district=is_illness,
            theme=theme,
            preset=preset,
            export_fmt=format,
            transparent=transparent,
            title=title,
            subtitle=subtitle or scope_label,
            footnote=footnote,
            lang=eff_lang,
            place_level=place_level,
            place_metric=place_metric,
            year=scope["effective_year"],
            sex=scope["filters"]["sex"],
            nationality=scope["filters"]["nationality"],
        )
        fname = f"02_place_distribution_4k_{eff_lang}.{format}"
    elif fig_id == 3:
        buf = render_figure_3_age_sex_nat(
            fdf,
            theme=theme,
            preset=preset,
            export_fmt=format,
            transparent=transparent,
            title=title,
            subtitle=subtitle or scope_label,
            footnote=footnote,
            lang=eff_lang,
        )
        fname = f"03_age_sex_pyramid_4k_{eff_lang}.{format}"
    elif fig_id == 4:
        t2_data = generate_table_2_age_burden(
            fdf,
            prov_code=scope["effective_prov_code"],
            prov_codes=scope["selected_province_codes"],
            scope_mode=scope["scope_mode"],
            scope_name_th=scope["scope_name_th"],
            scope_name_en=scope["scope_name_en"],
            year=scope["effective_year"],
            district_code=scope["effective_district_code"],
            sex=scope["filters"]["sex"],
            nationality=scope["filters"]["nationality"],
            patient_type=scope["filters"]["patient_type"],
            address_type=scope["filters"]["address_type"],
        )
        buf = render_figure_4_age_rates(
            t2_data,
            theme=theme,
            preset=preset,
            export_fmt=format,
            transparent=transparent,
            title=title,
            subtitle=subtitle,
            footnote=footnote,
            lang=eff_lang,
            scope_label=scope_label,
        )
        fname = f"04_age_specific_rates_4k_{eff_lang}.{format}"
    elif fig_id == 5:
        t2_data = generate_table_2_age_burden(
            fdf,
            prov_code=scope["effective_prov_code"],
            prov_codes=scope["selected_province_codes"],
            scope_mode=scope["scope_mode"],
            scope_name_th=scope["scope_name_th"],
            scope_name_en=scope["scope_name_en"],
            year=scope["effective_year"],
            district_code=scope["effective_district_code"],
            sex=scope["filters"]["sex"],
            nationality=scope["filters"]["nationality"],
            patient_type=scope["filters"]["patient_type"],
            address_type=scope["filters"]["address_type"],
        )
        buf = render_figure_5_hospitalization_prop(
            t2_data,
            theme=theme,
            preset=preset,
            export_fmt=format,
            transparent=transparent,
            title=title,
            subtitle=subtitle or scope_label,
            footnote=footnote,
            lang=eff_lang,
        )
        fname = f"05_hospitalization_proportions_4k_{eff_lang}.{format}"
    elif fig_id == 6:
        buf = render_figure_6_nationality_comparison(
            fdf,
            theme=theme,
            preset=preset,
            export_fmt=format,
            transparent=transparent,
            title=title,
            subtitle=subtitle or scope_label,
            footnote=footnote,
            lang=eff_lang,
        )
        fname = f"06_nationality_comparison_4k_{eff_lang}.{format}"
    elif fig_id == 7:
        weekly_s = build_continuous_weekly_series(fdf)
        fc_res = fit_ols_forecast(weekly_s, horizon_weeks=4)
        buf = render_figure_7_forecast(
            fc_res,
            theme=theme,
            preset=preset,
            export_fmt=format,
            transparent=transparent,
            title=title,
            subtitle=subtitle,
            footnote=footnote,
            lang=eff_lang,
        )
        fname = f"07_forecast_4k_{eff_lang}.{format}"
    elif fig_id == 8:
        all_yr_filters = dict(eff_filters)
        all_yr_filters["year"] = None
        all_yr_scope = apply_filters_and_resolve_scope(df, all_yr_filters)
        denom_pop = scope["denominator"].get("population") if scope["denominator"].get("available") else None
        if not denom_pop and all_yr_scope["denominator"].get("available"):
            denom_pop = all_yr_scope["denominator"].get("population")
        seasonal_data = build_seasonal_comparison_series(
            all_yr_scope["filtered_df"],
            population=denom_pop,
        )
        buf = render_figure_8_seasonal_comparison(
            seasonal_data,
            metric=place_metric if place_metric in ("cases", "rate") else "cases",
            theme=theme,
            preset=preset,
            export_fmt=format,
            transparent=transparent,
            title=title,
            subtitle=subtitle or scope_label,
            footnote=footnote,
            lang=eff_lang,
        )
        fname = f"08_seasonal_2yr_vs_5yr_median_4k_{eff_lang}.{format}"
    else:
        raise HTTPException(status_code=404, detail="Figure ID not found.")

    media_map = {
        "png": "image/png",
        "svg": "image/svg+xml",
        "pdf": "application/pdf",
    }
    return StreamingResponse(
        buf,
        media_type=media_map.get(format, "image/png"),
        headers={"Content-Disposition": f'inline; filename="{fname}"'},
    )


@app.get("/api/studio/presentation-pack.zip")
def download_presentation_pack(
    theme: str = Query("light"),
    lang: Optional[str] = Query(None, regex="^(th|en)$"),
    scope_mode: Optional[str] = Query(None),
    province_code: Optional[str] = Query(None),
    province_codes: Optional[List[str]] = Query(None),
    district_code: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    sex: Optional[str] = Query(None),
    nationality: Optional[str] = Query(None),
    patient_type: Optional[str] = Query(None),
    address_type: Optional[str] = Query(None),
    include_vector: bool = Query(False),
):
    try:
        eff_theme = theme.default if hasattr(theme, "default") else theme
        eff_inc_vec = bool(include_vector.default if hasattr(include_vector, "default") else include_vector)
        df, session = get_current_df_and_session()
        eff_filters = resolve_effective_filters(
            session,
            scope_mode=scope_mode,
            province_code=province_code,
            province_codes=province_codes,
            district_code=district_code,
            year=year,
            sex=sex,
            nationality=nationality,
            patient_type=patient_type,
            address_type=address_type,
            lang=lang,
        )
        eff_lang = eff_filters["lang"]
        zip_buf = create_presentation_pack_zip(
            df,
            session.get("audit_trail", {}),
            theme=eff_theme,
            is_synthetic=session.get("is_synthetic", False),
            raw_filters=eff_filters,
            lang=eff_lang,
            include_vector=eff_inc_vec,
        )
        session_dir = SESSIONS_DIR / ACTIVE_SESSION_ID
        session_dir.mkdir(parents=True, exist_ok=True)
        zip_disk_path = session_dir / f"DDS_OneClick_Presentation_Pack_{eff_lang.upper()}.zip"
        try:
            zip_disk_path.write_bytes(zip_buf.getvalue())
            zip_buf.seek(0)
            if "saved_files" not in session:
                session["saved_files"] = {}
            session["saved_files"][f"presentation_pack_zip_{eff_lang}"] = str(zip_disk_path)
        except Exception as e:
            logger.warning(f"Notice: caching presentation pack to disk failed: {e}")

        fname = f"DDS_OneClick_Presentation_Pack_{eff_lang.upper()}.zip"
        return StreamingResponse(
            zip_buf,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{fname}"',
                "Cache-Control": "no-cache",
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error generating presentation pack: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"เกิดข้อผิดพลาดในการสร้าง Presentation Pack: {str(exc)}",
        )


@app.get("/api/export/excel")
def export_analytical_excel(
    scope_mode: Optional[str] = Query(None),
    province_code: Optional[str] = Query(None),
    province_codes: Optional[List[str]] = Query(None),
    district_code: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    sex: Optional[str] = Query(None),
    nationality: Optional[str] = Query(None),
    patient_type: Optional[str] = Query(None),
    address_type: Optional[str] = Query(None),
):
    df, session = get_current_df_and_session()
    eff_filters = resolve_effective_filters(
        session,
        scope_mode=scope_mode,
        province_code=province_code,
        province_codes=province_codes,
        district_code=district_code,
        year=year,
        sex=sex,
        nationality=nationality,
        patient_type=patient_type,
        address_type=address_type,
    )
    saved_xlsx = (session.get("saved_files") or {}).get("excel_report")
    if (
        saved_xlsx
        and eff_filters == normalize_filters(session.get("filters"))
        and Path(saved_xlsx).exists()
    ):
        return FileResponse(
            path=saved_xlsx,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="DDS_Surveillance_Report.xlsx",
        )

    buf = create_styled_excel_workbook(
        df,
        session.get("audit_trail", {}),
        is_synthetic=session.get("is_synthetic", False),
        raw_filters=eff_filters,
    )
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="DDS_Surveillance_Report.xlsx"'},
    )


@app.get("/api/export/csv/{table_id}")
def export_table_csv(
    table_id: str,
    scope_mode: Optional[str] = Query(None),
    province_code: Optional[str] = Query(None),
    province_codes: Optional[List[str]] = Query(None),
    district_code: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    sex: Optional[str] = Query(None),
    nationality: Optional[str] = Query(None),
    patient_type: Optional[str] = Query(None),
    address_type: Optional[str] = Query(None),
):
    df, session = get_current_df_and_session()
    eff_filters = resolve_effective_filters(
        session,
        scope_mode=scope_mode,
        province_code=province_code,
        province_codes=province_codes,
        district_code=district_code,
        year=year,
        sex=sex,
        nationality=nationality,
        patient_type=patient_type,
        address_type=address_type,
    )
    scope = apply_filters_and_resolve_scope(df, eff_filters)
    fdf = scope["filtered_df"]
    is_illness = scope["filters"]["address_type"] == "illness"

    if table_id == "table0":
        out_df = pd.DataFrame(generate_table_0_import_flow(session.get("audit_trail", {})))
        fname = "Table_0_Import_Eligibility_Flow.csv"
    elif table_id == "table2":
        out_df = pd.DataFrame(
            generate_table_2_age_burden(
                fdf,
                prov_code=scope["effective_prov_code"],
                prov_codes=scope["selected_province_codes"],
                scope_mode=scope["scope_mode"],
                scope_name_th=scope["scope_name_th"],
                scope_name_en=scope["scope_name_en"],
                year=scope["effective_year"],
                district_code=scope["effective_district_code"],
                sex=scope["filters"]["sex"],
                nationality=scope["filters"]["nationality"],
                patient_type=scope["filters"]["patient_type"],
                address_type=scope["filters"]["address_type"],
            )
        )
        fname = "Table_2_Age_Specific_Burden.csv"
    elif table_id == "table3":
        out_df = pd.DataFrame(
            generate_table_3_district_summary(
                fdf,
                use_illness_district=is_illness,
                year=scope["effective_year"],
                sex=scope["filters"]["sex"],
                nationality=scope["filters"]["nationality"],
            )
        )
        fname = "Table_3_District_Summary.csv"
    elif table_id in ("table4", "table5"):
        weekly_s = build_continuous_weekly_series(fdf)
        fc_data = fit_ols_forecast(weekly_s, horizon_weeks=4)
        out_df = pd.DataFrame(fc_data.get("history", []) + fc_data.get("lag_excluded", []) + fc_data.get("forecasts", []))
        fname = "Table_4_Weekly_OLS_Forecast.csv"
    else:
        raise HTTPException(status_code=404, detail="Table ID not found.")

    csv_bytes = out_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
