import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
SESSIONS_DIR = BASE_DIR / "data_sessions"
FIXTURES_DIR = BASE_DIR / "data_fixtures"

# Support reference database in root, backend directory, Docker path, or custom env
_candidate_paths = [
    os.environ.get("REFERENCE_DB_PATH"),
    BASE_DIR / "dds_reference" / "data" / "dds_reference.sqlite",
    PROJECT_ROOT / "dds_reference" / "data" / "dds_reference.sqlite",
    Path("/app/dds_reference/data/dds_reference.sqlite"),
    Path(__file__).resolve().parent.parent / "dds_reference" / "data" / "dds_reference.sqlite",
]
REFERENCE_DB_PATH = None
for cp in _candidate_paths:
    if cp and Path(cp).exists():
        REFERENCE_DB_PATH = Path(cp).resolve()
        break
if REFERENCE_DB_PATH is None:
    REFERENCE_DB_PATH = (BASE_DIR / "dds_reference" / "data" / "dds_reference.sqlite").resolve()

SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

# Upload limits (configurable via MAX_UPLOAD_SIZE_MB env, defaults to 200 MB)
MAX_UPLOAD_SIZE_MB = int(os.environ.get("MAX_UPLOAD_SIZE_MB", 200))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Session TTL
SESSION_TIMEOUT_SECONDS = 7200  # 2 hours

# Default analytical scope: eligible imported data, no hard-coded province comparator
DEFAULT_SCOPE = "all"
DEFAULT_COMPARATOR_PROVINCE = None

# Font search paths for server-side 4K figure rendering (Windows + Linux container support)
FONT_SEARCH_PATHS = [
    # Windows paths
    Path("C:/Windows/Fonts/LeelawUI.ttf"),
    Path("C:/Windows/Fonts/leelawad.ttf"),
    Path("C:/Windows/Fonts/tahoma.ttf"),
    Path("C:/Windows/Fonts/angsana.ttc"),
    # Linux Debian / Ubuntu container paths (fonts-thai-tlwg)
    Path("/usr/share/fonts/truetype/tlwg/Loma.ttf"),
    Path("/usr/share/fonts/truetype/tlwg/Garuda.ttf"),
    Path("/usr/share/fonts/truetype/tlwg/Norasi.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]

def get_thai_font_path() -> str | None:
    for p in FONT_SEARCH_PATHS:
        if p.exists():
            return str(p)
    return None
