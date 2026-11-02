import math
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy import stats

from app.epi_calendar import date_to_epi_week, format_epi_week_label
from app.dds_importer import parse_flexible_date


def build_continuous_weekly_series(
    df: pd.DataFrame,
    date_col: Optional[str] = None,
    fill_zeros: bool = True,
) -> pd.DataFrame:
    """
    Aggregates episodes into a chronological weekly series by Epi Week.
    Uses a continuous calendar-based index t across New Year.
    Falls back across analysis_date -> parsed_onset_date -> parsed_diagnosis_date -> parsed_report_date -> parsed_update_date.
    """
    if df.empty:
        return pd.DataFrame()

    candidate_cols = [date_col] if date_col else []
    candidate_cols += [
        "analysis_date",
        "parsed_onset_date",
        "parsed_diagnosis_date",
        "parsed_treatment_date",
        "parsed_report_date",
        "parsed_update_date",
        "onset_date",
        "report_date",
        "update_date",
    ]

    valid_dates: List[date] = []
    for c in candidate_cols:
        if not c or c not in df.columns:
            continue
        col_dates: List[date] = []
        for raw_val in df[c].dropna().tolist():
            if isinstance(raw_val, date):
                col_dates.append(raw_val)
            else:
                parsed = parse_flexible_date(raw_val)
                if isinstance(parsed, date):
                    col_dates.append(parsed)
        if col_dates:
            valid_dates = col_dates
            break

    if not valid_dates:
        return pd.DataFrame()

    min_date = min(valid_dates)
    max_date = max(valid_dates)

    _, _, min_start, _ = date_to_epi_week(min_date)
    _, _, max_start, _ = date_to_epi_week(max_date)

    # Count observed cases per epi week start date
    obs_counts: Dict[date, int] = {}
    for d in valid_dates:
        _, _, ws, _ = date_to_epi_week(d)
        obs_counts[ws] = obs_counts.get(ws, 0) + 1

    all_weeks = []
    curr_start = min_start
    t_idx = 0
    while curr_start <= max_start:
        ey, ew, ws, we = date_to_epi_week(curr_start)
        count = obs_counts.get(ws, 0 if fill_zeros else None)
        all_weeks.append({
            "t": t_idx,
            "epi_year": ey,
            "epi_week": ew,
            "week_start": ws,
            "week_end": we,
            "label_th": format_epi_week_label(ey, ew, ws, we, "th"),
            "label_en": format_epi_week_label(ey, ew, ws, we, "en"),
            "observed_cases": count,
        })
        curr_start += timedelta(days=7)
        t_idx += 1

    return pd.DataFrame(all_weeks)


def fit_ols_forecast(
    weekly_df: pd.DataFrame,
    horizon_weeks: int = 4,
    include_seasonality: bool = False,  # Ignored by design: strictly OLS trend without multi-year seasonality
    exclude_last_n_weeks: int = 1,
    max_training_weeks: int = 52,
) -> Dict[str, Any]:
    """
    Fits linear regression forecast strictly on the latest available one year:
    - At most 52 complete epi weeks through the data-defined training cutoff.
    - If shorter history is available (< 52 complete weeks), uses available weeks and states actual range.
    - Visible completeness lag if exclude_last_n_weeks > 0.
    - Preserves real coverage gaps (does not pad leading empty weeks before actual reporting in the window).
    - OLS model: weekly_cases = beta0 + beta1 * t + error with continuous calendar-based index t across New Year.
    - No multi-year seasonality or historical-median requirement; no Phitsanulok comparator.
    - Chronological holdout evaluation vs last-observation naive baseline within the latest-year window.
    """
    horizon_weeks = max(1, min(12, int(horizon_weeks)))
    exclude_last_n_weeks = max(0, min(4, int(exclude_last_n_weeks)))

    if weekly_df.empty:
        return {
            "status": "unavailable",
            "reason": "ไม่มีข้อมูลรายสัปดาห์สำหรับการพยากรณ์ / No weekly data available for forecasting.",
            "n_training_weeks": 0,
            "max_window_weeks": max_training_weeks,
            "history": [],
            "lag_excluded": [],
            "forecasts": [],
        }

    # 1. Separate reporting-completeness lag weeks at the tail if selected
    if exclude_last_n_weeks > 0 and len(weekly_df) > exclude_last_n_weeks:
        complete_df = weekly_df.iloc[:-exclude_last_n_weeks].copy()
        lag_df = weekly_df.iloc[-exclude_last_n_weeks:].copy()
        lag_excluded_count = exclude_last_n_weeks
    else:
        complete_df = weekly_df.copy()
        lag_df = pd.DataFrame()
        lag_excluded_count = 0

    # 2. Restrict strictly to the latest available one-year window (at most 52 complete epi weeks)
    if len(complete_df) > max_training_weeks:
        window_df = complete_df.iloc[-max_training_weeks:].copy()
    else:
        window_df = complete_df.copy()

    # Preserve real coverage gaps: if the 52-week slice starts with leading zero weeks from a multi-year gap,
    # start from the first week with actual reported cases inside the latest-year window.
    pos_mask = window_df["observed_cases"].fillna(0) > 0
    if pos_mask.any():
        first_pos_idx = pos_mask.idxmax()
        train_df = window_df.loc[first_pos_idx:].copy().reset_index(drop=True)
    else:
        train_df = window_df.copy().reset_index(drop=True)

    N_train = len(train_df)
    if N_train < 4:
        return {
            "status": "unavailable",
            "reason": (
                f"ข้อมูลสัปดาห์สมบูรณ์มีเพียง {N_train} สัปดาห์ (หลังหัก Lag {lag_excluded_count} สัปดาห์) "
                f"ซึ่งไม่เพียงพอสำหรับการประมาณค่า OLS Linear Regression และช่วงความเชื่อมั่น (ต้องการอย่างน้อย 4 สัปดาห์สมบูรณ์) / "
                f"Only {N_train} complete weeks available (after {lag_excluded_count} lag week(s)); minimum 4 complete weeks required for OLS forecast."
            ),
            "n_training_weeks": N_train,
            "max_window_weeks": max_training_weeks,
            "lag_excluded_weeks": lag_excluded_count,
            "history": [],
            "lag_excluded": [],
            "forecasts": [],
        }

    # 3. Continuous calendar-based week index t across New Year starting at 0 for train_df[0]
    base_week_start: date = train_df.iloc[0]["week_start"]
    train_df["t"] = [(ws - base_week_start).days // 7 for ws in train_df["week_start"]]

    t_vals = train_df["t"].values.astype(float)
    y_vals = train_df["observed_cases"].fillna(0).values.astype(float)
    zero_case_weeks_count = int(np.sum(y_vals == 0))

    # Design matrix strictly [1, t]: weekly_cases = beta0 + beta1 * t + error
    X_train = np.column_stack([np.ones(N_train), t_vals])
    p = 2

    try:
        XtX = X_train.T @ X_train
        XtX_inv = np.linalg.inv(XtX)
        beta = XtX_inv @ X_train.T @ y_vals
    except np.linalg.LinAlgError:
        return {
            "status": "unavailable",
            "reason": "Singular matrix encountered in OLS calculation.",
            "n_training_weeks": N_train,
            "max_window_weeks": max_training_weeks,
            "history": [],
            "lag_excluded": [],
            "forecasts": [],
        }

    y_fitted = X_train @ beta
    residuals = y_vals - y_fitted
    dof = max(1, N_train - p)
    sigma2 = float(np.sum(residuals**2) / dof)
    sigma = math.sqrt(sigma2)

    t_crit_95 = float(stats.t.ppf(0.975, df=dof))
    t_crit_80 = float(stats.t.ppf(0.90, df=dof))

    history_records: List[Dict[str, Any]] = []
    for i, row in train_df.iterrows():
        x_i = X_train[i]
        se_pred = sigma * math.sqrt(1.0 + float(x_i @ XtX_inv @ x_i))
        fit_val = float(y_fitted[i])
        obs_val = int(row["observed_cases"])

        history_records.append({
            "t": int(row["t"]),
            "epi_year": int(row["epi_year"]),
            "epi_week": int(row["epi_week"]),
            "week_start": str(row["week_start"]),
            "week_end": str(row["week_end"]),
            "label_th": row["label_th"],
            "label_en": row["label_en"],
            "observed": obs_val,
            "fitted": round(fit_val, 2),
            "fitted_clipped": max(0.0, round(fit_val, 2)),
            "pi_80_lower": round(fit_val - t_crit_80 * se_pred, 2),
            "pi_80_upper": round(fit_val + t_crit_80 * se_pred, 2),
            "pi_95_lower": round(fit_val - t_crit_95 * se_pred, 2),
            "pi_95_upper": round(fit_val + t_crit_95 * se_pred, 2),
            "is_forecast": False,
            "is_lag_excluded": False,
        })

    # Visible completeness lag records (if exclude_last_n_weeks > 0)
    lag_excluded_records: List[Dict[str, Any]] = []
    if not lag_df.empty:
        for _, row in lag_df.iterrows():
            lag_t = int((row["week_start"] - base_week_start).days // 7)
            x_lag = np.array([1.0, float(lag_t)])
            pred_lag = float(x_lag @ beta)
            se_lag = sigma * math.sqrt(1.0 + float(x_lag @ XtX_inv @ x_lag))
            lag_excluded_records.append({
                "t": lag_t,
                "epi_year": int(row["epi_year"]),
                "epi_week": int(row["epi_week"]),
                "week_start": str(row["week_start"]),
                "week_end": str(row["week_end"]),
                "label_th": row["label_th"],
                "label_en": row["label_en"],
                "observed": int(row["observed_cases"]),
                "fitted": round(pred_lag, 2),
                "fitted_clipped": max(0.0, round(pred_lag, 2)),
                "pi_80_lower": round(pred_lag - t_crit_80 * se_lag, 2),
                "pi_80_upper": round(pred_lag + t_crit_80 * se_lag, 2),
                "pi_95_lower": round(pred_lag - t_crit_95 * se_lag, 2),
                "pi_95_upper": round(pred_lag + t_crit_95 * se_lag, 2),
                "is_forecast": False,
                "is_lag_excluded": True,
            })

    # 4. Chronological backtest evaluation vs last-observation naive strictly within the latest-year window
    val_mae, val_rmse, baseline_mae, baseline_rmse = None, None, None, None
    val_k = 0
    val_status = "unavailable"
    if N_train >= 6:
        val_k = min(4, max(2, N_train // 5))
        val_train_N = N_train - val_k
        if val_train_N >= 4:
            X_val_tr = X_train[:val_train_N]
            y_val_tr = y_vals[:val_train_N]
            try:
                val_beta = np.linalg.inv(X_val_tr.T @ X_val_tr) @ X_val_tr.T @ y_val_tr
                X_val_test = X_train[val_train_N:]
                y_val_test = y_vals[val_train_N:]
                preds_val = X_val_test @ val_beta

                # Last-observation naive baseline
                last_obs = y_val_tr[-1]
                baseline_preds = np.full_like(y_val_test, last_obs)

                val_mae = round(float(np.mean(np.abs(y_val_test - preds_val))), 2)
                val_rmse = round(float(math.sqrt(np.mean((y_val_test - preds_val) ** 2))), 2)
                baseline_mae = round(float(np.mean(np.abs(y_val_test - baseline_preds))), 2)
                baseline_rmse = round(float(math.sqrt(np.mean((y_val_test - baseline_preds) ** 2))), 2)
                val_status = "evaluated"
            except Exception:
                val_status = "singular_in_backtest"

    # 5. Forecast future horizon weeks from the data-defined training cutoff
    last_week_row = train_df.iloc[-1]
    last_t = int(last_week_row["t"])
    last_start: date = last_week_row["week_start"]

    forecast_records: List[Dict[str, Any]] = []
    for h in range(1, horizon_weeks + 1):
        fut_t = last_t + h
        fut_start = last_start + timedelta(days=7 * h)
        ey, ew, ws, we = date_to_epi_week(fut_start)

        x_fut = np.array([1.0, float(fut_t)])
        pred_val = float(x_fut @ beta)
        se_pred = sigma * math.sqrt(1.0 + float(x_fut @ XtX_inv @ x_fut))

        pi_95_l = pred_val - t_crit_95 * se_pred
        pi_95_u = pred_val + t_crit_95 * se_pred
        pi_80_l = pred_val - t_crit_80 * se_pred
        pi_80_u = pred_val + t_crit_80 * se_pred

        # Check if this forecast week coincides with a lag-excluded observed week
        lag_obs = None
        if not lag_df.empty:
            matching_lag = lag_df[lag_df["week_start"] == ws]
            if not matching_lag.empty:
                lag_obs = int(matching_lag.iloc[0]["observed_cases"])

        forecast_records.append({
            "t": fut_t,
            "epi_year": ey,
            "epi_week": ew,
            "week_start": str(ws),
            "week_end": str(we),
            "label_th": format_epi_week_label(ey, ew, ws, we, "th"),
            "label_en": format_epi_week_label(ey, ew, ws, we, "en"),
            "observed": None,
            "lag_excluded_observed": lag_obs,
            "fitted": round(pred_val, 2),
            "fitted_clipped": max(0.0, round(pred_val, 2)),
            "pi_80_lower": round(pi_80_l, 2),
            "pi_80_upper": round(pi_80_u, 2),
            "pi_95_lower": round(pi_95_l, 2),
            "pi_95_upper": round(pi_95_u, 2),
            "is_forecast": True,
            "is_lag_excluded": False,
        })

    model_formula = f"weekly_cases = {beta[0]:.2f} + ({beta[1]:.2f} * t)"
    ss_tot = float(np.sum((y_vals - np.mean(y_vals)) ** 2))
    r2_val = round(float(1.0 - float(np.sum(residuals**2)) / ss_tot), 4) if ss_tot > 1e-9 else 0.0

    first_row = train_df.iloc[0]
    start_wk_str = f"W{int(first_row['epi_week']):02d}/{int(first_row['epi_year'])}"
    end_wk_str = f"W{int(last_week_row['epi_week']):02d}/{int(last_week_row['epi_year'])}"
    start_dt_str = str(first_row["week_start"])
    end_dt_str = str(last_week_row["week_end"])

    if N_train < max_training_weeks:
        window_note_th = (
            f"ใช้ข้อมูลจริงที่มีอยู่ {N_train} สัปดาห์สมบูรณ์ล่าสุด "
            f"({start_wk_str} [{start_dt_str}] ถึง {end_wk_str} [{end_dt_str}]; เกณฑ์สูงสุดไม่เกิน 52 สัปดาห์)"
        )
        window_note_en = (
            f"Trained on {N_train} available complete epi weeks "
            f"({start_wk_str} [{start_dt_str}] to {end_wk_str} [{end_dt_str}]; capped at max 52 weeks)"
        )
    else:
        window_note_th = (
            f"ใช้ข้อมูล 52 สัปดาห์สมบูรณ์ล่าสุด ({start_wk_str} [{start_dt_str}] ถึง {end_wk_str} [{end_dt_str}])"
        )
        window_note_en = (
            f"Trained on latest 52 complete epi weeks ({start_wk_str} [{start_dt_str}] to {end_wk_str} [{end_dt_str}])"
        )

    return {
        "status": "success",
        "model_type": "OLS Linear Regression (Latest <=52 Complete Weeks)",
        "formula": model_formula,
        "beta0": round(float(beta[0]), 4),
        "beta1": round(float(beta[1]), 4),
        "n_training_weeks": N_train,
        "max_window_weeks": max_training_weeks,
        "used_shorter_history": N_train < max_training_weeks,
        "training_start_week": start_wk_str,
        "training_end_week": end_wk_str,
        "training_start_date": start_dt_str,
        "training_end_date": end_dt_str,
        "training_window_note_th": window_note_th,
        "training_window_note_en": window_note_en,
        "zero_case_weeks_count": zero_case_weeks_count,
        "horizon_weeks": horizon_weeks,
        "lag_excluded_weeks": lag_excluded_count,
        "r_squared": r2_val,
        "sigma_residuals": round(sigma, 2),
        "validation_metrics": {
            "status": val_status,
            "validation_holdout_weeks": val_k,
            "mae": val_mae,
            "rmse": val_rmse,
            "baseline_mae": baseline_mae,
            "baseline_rmse": baseline_rmse,
            "improvement_pct": (
                round((baseline_mae - val_mae) / baseline_mae * 100.0, 1)
                if (baseline_mae is not None and val_mae is not None and baseline_mae > 0)
                else None
            ),
        },
        "history": history_records,
        "lag_excluded": lag_excluded_records,
        "forecasts": forecast_records,
        "disclosure_th": (
            f"{window_note_th} | สมการ OLS: weekly_cases = beta0 + beta1*t (ดัชนีเวลา t ต่อเนื่องข้ามปี ไม่บังคับข้อมูลหลายปีหรือฤดูกาล) "
            f"| ตัดสัปดาห์ล่าสุดที่อาจรายงานไม่ครบ (Lag) = {lag_excluded_count} สัปดาห์ | สัปดาห์ที่มี 0 รายในช่วงฝึกสอน = {zero_case_weeks_count} สัปดาห์"
        ),
        "disclosure_en": (
            f"{window_note_en} | OLS: weekly_cases = beta0 + beta1*t (continuous calendar index t across New Year; no multi-year seasonality required) "
            f"| Completeness lag excluded = {lag_excluded_count} week(s) | Zero-case weeks in window = {zero_case_weeks_count}."
        ),
    }


def build_seasonal_comparison_series(
    df: pd.DataFrame,
    denominator_pop: Optional[int] = None,
    pop_by_year: Optional[Dict[int, int]] = None,
    population: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Builds a 52-week seasonal comparison series (W01–W52) comparing:
    - Latest year (e.g. 2026 / พ.ศ. 2569)
    - Previous year (e.g. 2025 / พ.ศ. 2568)
    - 5-Year Historical Median (up to 5 years preceding the latest year, or all available prior years)
    Provides both weekly case counts and weekly incidence per 100,000 population.
    """
    if denominator_pop is None and population is not None:
        denominator_pop = population

    if df.empty:
        return {"available": False, "weeks": []}

    candidate_cols = [
        "analysis_date",
        "parsed_onset_date",
        "parsed_diagnosis_date",
        "parsed_treatment_date",
        "parsed_report_date",
        "parsed_update_date",
        "onset_date",
        "report_date",
        "update_date",
    ]
    valid_dates: List[date] = []
    for c in candidate_cols:
        if c not in df.columns:
            continue
        col_dates: List[date] = []
        for raw_val in df[c].dropna().tolist():
            if isinstance(raw_val, date):
                col_dates.append(raw_val)
            else:
                parsed = parse_flexible_date(raw_val)
                if isinstance(parsed, date):
                    col_dates.append(parsed)
        if col_dates:
            valid_dates = col_dates
            break

    if not valid_dates:
        return {"available": False, "weeks": []}

    yr_wk_counts: Dict[int, Dict[int, int]] = {}
    for d in valid_dates:
        ey, ew, _, _ = date_to_epi_week(d)
        ew_clamped = min(52, max(1, int(ew)))
        if ey not in yr_wk_counts:
            yr_wk_counts[ey] = {}
        yr_wk_counts[ey][ew_clamped] = yr_wk_counts[ey].get(ew_clamped, 0) + 1

    years = sorted(yr_wk_counts.keys())
    if not years:
        return {"available": False, "weeks": []}

    latest_year = years[-1]
    prev_year = years[-2] if len(years) >= 2 else None
    prior_years = [y for y in years[:-1]][-5:] if len(years) >= 2 else [latest_year]

    latest_max_week = max(yr_wk_counts[latest_year].keys()) if yr_wk_counts.get(latest_year) else 52
    is_incomplete_latest = latest_max_week < 50 and len(years) >= 2

    def _get_pop(yr: Optional[int]) -> Optional[int]:
        if yr is not None and pop_by_year and pop_by_year.get(yr):
            return int(pop_by_year[yr])
        if denominator_pop and denominator_pop > 0:
            return int(denominator_pop)
        return None

    pop_latest = _get_pop(latest_year)
    pop_prev = _get_pop(prev_year) if prev_year else None

    weeks_out: List[Dict[str, Any]] = []
    for w in range(1, 53):
        if is_incomplete_latest and w > latest_max_week:
            lat_c: Optional[int] = None
            lat_r: Optional[float] = None
        else:
            lat_c = int(yr_wk_counts.get(latest_year, {}).get(w, 0))
            lat_r = round(lat_c / pop_latest * 100000.0, 3) if (pop_latest and pop_latest > 0) else None

        if prev_year is not None:
            prv_c: Optional[int] = int(yr_wk_counts.get(prev_year, {}).get(w, 0))
            prv_r: Optional[float] = round(prv_c / pop_prev * 100000.0, 3) if (pop_prev and pop_prev > 0) else None
        else:
            prv_c = None
            prv_r = None

        hist_vals = [float(yr_wk_counts.get(y, {}).get(w, 0)) for y in prior_years]
        med_c = round(float(np.median(hist_vals)), 1) if hist_vals else 0.0
        q25_c = round(float(np.percentile(hist_vals, 25)), 1) if hist_vals else 0.0
        q75_c = round(float(np.percentile(hist_vals, 75)), 1) if hist_vals else 0.0

        hist_rates: List[float] = []
        for y in prior_years:
            py = _get_pop(y)
            if py and py > 0:
                hist_rates.append(float(yr_wk_counts.get(y, {}).get(w, 0)) / py * 100000.0)
        med_r = round(float(np.median(hist_rates)), 3) if hist_rates else None

        weeks_out.append({
            "epi_week": w,
            "week_label": f"W{w:02d}",
            "week_label_th": f"ส.{w}",
            "latest_cases": lat_c,
            "prev_cases": prv_c,
            "median_5yr_cases": med_c,
            "q25_5yr_cases": q25_c,
            "q75_5yr_cases": q75_c,
            "latest_rate": lat_r,
            "prev_rate": prv_r,
            "median_5yr_rate": med_r,
        })

    if len(prior_years) > 1:
        med_lbl_th = f"มัธยฐาน 5 ปีย้อนหลัง (พ.ศ. {prior_years[0] + 543}–{prior_years[-1] + 543}, n={len(prior_years)} ปี)"
        med_lbl_en = f"5-Year Median ({prior_years[0]}–{prior_years[-1]}, n={len(prior_years)} yrs)"
    else:
        med_lbl_th = f"มัธยฐานอ้างอิง (พ.ศ. {prior_years[0] + 543})"
        med_lbl_en = f"Reference Median ({prior_years[0]})"

    return {
        "available": True,
        "latest_year": latest_year,
        "latest_year_ce": latest_year,
        "latest_year_be": latest_year + 543,
        "prev_year": prev_year,
        "prev_year_ce": prev_year,
        "prev_year_be": (prev_year + 543) if prev_year else None,
        "median_years": prior_years,
        "median_years_used": prior_years,
        "median_years_ce": prior_years,
        "median_years_be": [y + 543 for y in prior_years],
        "median_years_count": len(prior_years),
        "latest_label_th": f"พ.ศ. {latest_year + 543} ({latest_year})",
        "latest_label_en": f"Year {latest_year} (B.E. {latest_year + 543})",
        "prev_label_th": f"พ.ศ. {prev_year + 543} ({prev_year})" if prev_year else None,
        "prev_label_en": f"Year {prev_year} (B.E. {prev_year + 543})" if prev_year else None,
        "median_label_th": med_lbl_th,
        "median_label_en": med_lbl_en,
        "latest_year_max_week": latest_max_week,
        "has_incidence": pop_latest is not None and pop_latest > 0,
        "has_rate": pop_latest is not None and pop_latest > 0,
        "note_th": f"เปรียบเทียบสัปดาห์ระบาดวิทยา W01–W52 ของ 2 ปีล่าสุด กับค่ามัธยฐาน 5 ปีย้อนหลัง ({med_lbl_th})",
        "note_en": f"Comparing W01–W52 of the latest 2 years against 5-year historical median ({med_lbl_en})",
        "weeks": weeks_out,
    }
