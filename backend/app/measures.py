import math
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, Optional, List
from scipy import stats

Z_95 = 1.959963984540054

STANDARD_AGE_BANDS = [
    "<1", "1-4", "5-9", "10-14", "15-19", "20-24", "25-29",
    "30-34", "35-39", "40-44", "45-49", "50-54", "55-59",
    "60-64", "65-69", "70-74", "75-79", "≥80"
]

def wilson_score_interval(
    x: int, n: int, confidence: float = 0.95
) -> Tuple[float, float, float]:
    """
    Computes Wilson score confidence interval for a binomial proportion.
    Returns: (proportion_pct, lower_pct, upper_pct)
    If n == 0, returns (0.0, 0.0, 0.0)
    """
    if n <= 0:
        return 0.0, 0.0, 0.0
    
    p = x / n
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    z2 = z * z
    
    denominator = 1.0 + z2 / n
    center_adj = (p + z2 / (2.0 * n)) / denominator
    margin = (z * math.sqrt((p * (1.0 - p) / n) + (z2 / (4.0 * n * n)))) / denominator
    
    lower = max(0.0, center_adj - margin)
    upper = min(1.0, center_adj + margin)
    
    return round(p * 100.0, 2), round(lower * 100.0, 2), round(upper * 100.0, 2)


def exact_poisson_rate_interval(
    count: int, population: float, per: float = 100000.0, confidence: float = 0.95
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Computes Exact Poisson confidence interval for a count rate per population.
    Returns: (rate, lower, upper)
    If population <= 0 or unavailable, returns (None, None, None)
    """
    if population <= 0 or math.isnan(population):
        return None, None, None
    
    alpha = 1.0 - confidence
    rate = (count / population) * per
    
    # Lower bound
    if count == 0:
        lower = 0.0
    else:
        # chi2 quantile with df = 2 * count
        lower = 0.5 * stats.chi2.ppf(alpha / 2.0, 2 * count) / population * per
        
    # Upper bound
    upper = 0.5 * stats.chi2.ppf(1.0 - alpha / 2.0, 2 * (count + 1)) / population * per
    
    return round(rate, 2), round(lower, 2), round(upper, 2)


def calculate_surveillance_measures(
    hosp_count: int, opd_count: int, unknown_count: int, population: Optional[float] = None
) -> Dict[str, Any]:
    """
    Given counts:
    H = hosp_count (IPD)
    O = opd_count (OPD)
    U = unknown_count
    C = H + O + U
    """
    h = int(hosp_count)
    o = int(opd_count)
    u = int(unknown_count)
    c = h + o + u
    
    known_type = h + o
    
    # Hospitalization proportion: H / (H + O) * 100
    if known_type > 0:
        hosp_prop, hosp_prop_lower, hosp_prop_upper = wilson_score_interval(h, known_type)
    else:
        hosp_prop, hosp_prop_lower, hosp_prop_upper = 0.0, 0.0, 0.0
        
    # Patient-type completeness: (H + O) / C * 100
    completeness = round((known_type / c * 100.0), 2) if c > 0 else 0.0
    
    # Rates per population if population provided
    case_rate, case_rate_l, case_rate_u = exact_poisson_rate_interval(c, population) if population else (None, None, None)
    hosp_rate, hosp_rate_l, hosp_rate_u = exact_poisson_rate_interval(h, population) if population else (None, None, None)
    
    return {
        "cases_C": c,
        "ipd_H": h,
        "opd_O": o,
        "unknown_U": u,
        "known_patient_type": known_type,
        "hospitalization_prop": hosp_prop,
        "hospitalization_prop_ci": [hosp_prop_lower, hosp_prop_upper],
        "patient_type_completeness": completeness,
        "compatible_population": population,
        "case_notification_rate": case_rate,
        "case_notification_rate_ci": [case_rate_l, case_rate_u] if case_rate is not None else None,
        "hosp_notification_rate": hosp_rate,
        "hosp_notification_rate_ci": [hosp_rate_l, hosp_rate_u] if hosp_rate is not None else None,
    }


def assign_age_band(age_years: Optional[float]) -> str:
    """Assigns standard 5-year surveillance age bands."""
    if age_years is None or pd.isna(age_years):
        return "Unknown"
    try:
        y = float(age_years)
    except (ValueError, TypeError):
        return "Unknown"
        
    if y < 0:
        return "Unknown"
    elif y < 1.0:
        return "<1"
    elif y < 5.0:
        return "1-4"
    elif y < 10.0:
        return "5-9"
    elif y < 15.0:
        return "10-14"
    elif y < 20.0:
        return "15-19"
    elif y < 25.0:
        return "20-24"
    elif y < 30.0:
        return "25-29"
    elif y < 35.0:
        return "30-34"
    elif y < 40.0:
        return "35-39"
    elif y < 45.0:
        return "40-44"
    elif y < 50.0:
        return "45-49"
    elif y < 55.0:
        return "50-54"
    elif y < 60.0:
        return "55-59"
    elif y < 65.0:
        return "60-64"
    elif y < 70.0:
        return "65-69"
    elif y < 75.0:
        return "70-74"
    elif y < 80.0:
        return "75-79"
    else:
        return "≥80"


def calculate_age_summary(ages: pd.Series) -> Dict[str, Any]:
    """Calculates median age and Interquartile Range (IQR)."""
    valid_ages = pd.to_numeric(ages, errors="coerce").dropna()
    valid_ages = valid_ages[(valid_ages >= 0) & (valid_ages <= 125)]
    if len(valid_ages) == 0:
        return {"median": None, "q25": None, "q75": None, "iqr": None, "valid_n": 0}
        
    median = float(valid_ages.median())
    q25 = float(valid_ages.quantile(0.25))
    q75 = float(valid_ages.quantile(0.75))
    iqr = round(q75 - q25, 2)
    
    return {
        "median": round(median, 1),
        "q25": round(q25, 1),
        "q75": round(q75, 1),
        "iqr": iqr,
        "valid_n": int(len(valid_ages))
    }
