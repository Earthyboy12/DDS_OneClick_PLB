from datetime import date, datetime, timedelta
from typing import Tuple, Dict, Any, List

THAI_MONTHS_SHORT = [
    "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."
]

EN_MONTHS_SHORT = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

def date_to_epi_week(d: date) -> Tuple[int, int, date, date]:
    """
    Computes (epi_year, epi_week, week_start_sunday, week_end_saturday)
    following CDC/Thai Bureau of Epidemiology standard:
    - Week starts on Sunday (weekday 6 in python calendar or 0 if Sunday=0)
    - Week ends on Saturday
    - Week 1 is the first week containing at least 4 days of that year (contains Jan 4).
    """
    # Python date.weekday(): Monday=0, Tuesday=1, ..., Sunday=6
    # For Sunday=0, Monday=1, ..., Saturday=6:
    sun_weekday = (d.weekday() + 1) % 7  # Sunday becomes 0, Saturday becomes 6
    week_start = d - timedelta(days=sun_weekday)
    week_end = week_start + timedelta(days=6)
    
    # The 4th day of the week is Wednesday:
    wednesday = week_start + timedelta(days=3)
    epi_year = wednesday.year
    
    # First week of epi_year: contains Jan 4
    jan4 = date(epi_year, 1, 4)
    jan4_sun_weekday = (jan4.weekday() + 1) % 7
    week1_start = jan4 - timedelta(days=jan4_sun_weekday)
    
    # Calculate week number
    epi_week = (week_start - week1_start).days // 7 + 1
    
    # Safety check: if epi_week == 0, it belongs to previous year's last week
    if epi_week < 1:
        prev_year = epi_year - 1
        prev_jan4 = date(prev_year, 1, 4)
        prev_jan4_sun = (prev_jan4.weekday() + 1) % 7
        prev_w1_start = prev_jan4 - timedelta(days=prev_jan4_sun)
        epi_year = prev_year
        epi_week = (week_start - prev_w1_start).days // 7 + 1
        
    return epi_year, epi_week, week_start, week_end


def format_epi_week_label(
    epi_year: int, epi_week: int, week_start: date, week_end: date, lang: str = "th"
) -> str:
    """
    Returns presentation-ready label for epidemiological week.
    e.g. Thai: "สัปดาห์ที่ 5/2568 (26 ม.ค. - 01 ก.พ. 2568)"
    e.g. EN:   "W05/2025 (26 Jan - 01 Feb 2025)"
    """
    if lang == "th":
        be_year = epi_year + 543
        start_str = f"{week_start.day:02d} {THAI_MONTHS_SHORT[week_start.month]}"
        end_str = f"{week_end.day:02d} {THAI_MONTHS_SHORT[week_end.month]} {be_year}"
        return f"สัปดาห์ที่ {epi_week}/{be_year} ({start_str} - {end_str})"
    else:
        start_str = f"{week_start.day:02d} {EN_MONTHS_SHORT[week_start.month]}"
        end_str = f"{week_end.day:02d} {EN_MONTHS_SHORT[week_end.month]} {epi_year}"
        return f"W{epi_week:02d}/{epi_year} ({start_str} - {end_str})"


def compute_continuous_week_index(
    week_start: date, base_start: date
) -> int:
    """
    Returns continuous index t = (week_start - base_start).days // 7
    Ensuring chronological continuity across year transitions.
    """
    return (week_start - base_start).days // 7
