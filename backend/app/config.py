import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
SESSIONS_DIR = BASE_DIR / "data_sessions"
FIXTURES_DIR = BASE_DIR / "data_fixtures"

# Support reference database in root, backend directory, or custom env
_custom_ref = os.environ.get("REFERENCE_DB_PATH")
if _custom_ref and Path(_custom_ref).exists():
    REFERENCE_DB_PATH = Path(_custom_ref)
elif (PROJECT_ROOT / "dds_reference" / "data" / "dds_reference.sqlite").exists():
    REFERENCE_DB_PATH = PROJECT_ROOT / "dds_reference" / "data" / "dds_reference.sqlite"
elif (BASE_DIR / "dds_reference" / "data" / "dds_reference.sqlite").exists():
    REFERENCE_DB_PATH = BASE_DIR / "dds_reference" / "data" / "dds_reference.sqlite"
else:
    REFERENCE_DB_PATH = PROJECT_ROOT / "dds_reference" / "data" / "dds_reference.sqlite"

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
