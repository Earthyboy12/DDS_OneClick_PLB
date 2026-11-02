import time
import uuid
import shutil
import pandas as pd
from typing import Dict, Any, Optional
from app.config import SESSIONS_DIR, SESSION_TIMEOUT_SECONDS


class SessionStore:
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, session_id: Optional[str] = None) -> str:
        sid = session_id or str(uuid.uuid4())
        self._sessions[sid] = {
            "created_at": time.time(),
            "last_accessed": time.time(),
            "raw_df": None,
            "standardized_df": None,
            "authoritative_df": None,
            "cleaned_df": None,
            "population_df": None,
            "raw_count": 0,
            "trailing_blanks_removed": 0,
            "audit_trail": {},
            "mappings": {},
            "filters": {},
            "is_synthetic": False,
        }
        return sid

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        self.cleanup_expired()
        session = self._sessions.get(session_id)
        if session:
            session["last_accessed"] = time.time()
        return session

    def set_data(
        self,
        session_id: str,
        cleaned_df: pd.DataFrame,
        raw_count: int,
        audit_trail: Dict[str, Any],
        mappings: Dict[str, Any],
        is_synthetic: bool = False,
        population_df: Optional[pd.DataFrame] = None,
        standardized_df: Optional[pd.DataFrame] = None,
        authoritative_df: Optional[pd.DataFrame] = None,
        trailing_blanks_removed: int = 0,
    ):
        session = self._sessions.get(session_id)
        if not session:
            self.create_session(session_id)
            session = self._sessions[session_id]

        session["cleaned_df"] = cleaned_df
        session["raw_count"] = raw_count
        session["trailing_blanks_removed"] = trailing_blanks_removed
        session["audit_trail"] = audit_trail
        session["mappings"] = mappings
        session["is_synthetic"] = is_synthetic
        if standardized_df is not None:
            session["standardized_df"] = standardized_df
        if authoritative_df is not None:
            session["authoritative_df"] = authoritative_df
        if population_df is not None:
            session["population_df"] = population_df
        session["last_accessed"] = time.time()
        return session_id

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            session_dir = SESSIONS_DIR / session_id
            if session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)
            return True
        return False

    def cleanup_expired(self):
        now = time.time()
        expired = [
            sid
            for sid, data in self._sessions.items()
            if (now - data.get("last_accessed", now)) > SESSION_TIMEOUT_SECONDS
        ]
        for sid in expired:
            self.delete_session(sid)


session_store = SessionStore()
