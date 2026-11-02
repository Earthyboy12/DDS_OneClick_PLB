export type Language = 'th' | 'en';
export type GeographyScopeMode = 'all_imported' | 'national' | 'provinces' | 'district';
export type FileCategory = 'cases' | 'population' | 'geography';
export type ImportMode = 'replace' | 'append';

export interface ActiveFilters {
  scope_mode: GeographyScopeMode;
  province_code: string | null;
  province_codes: string[];
  district_code: string | null;
  year: number | null;
  sex: string | null;
  nationality: string | null;
  patient_type: string | null;
  address_type: 'residence' | 'illness';
  comparator_province_code: string | null;
  lang: Language;
}

export interface DenominatorInfo {
  available: boolean;
  population: number | null;
  requested_year?: number | null;
  reference_year: number | null;
  population_year_be?: number | null;
  is_fallback_year?: boolean;
  reference_month: number | null;
  scope_mode?: GeographyScopeMode;
  province_code: string | null;
  province_codes?: string[];
  province_breakdown?: Record<string, number>;
  province_name_th?: string;
  province_name_en?: string;
  scope_name_th?: string;
  scope_name_en?: string;
  district_code: string | null;
  missing_provinces?: string[];
  reason_th?: string | null;
  reason_en?: string | null;
}

export interface RateByYearRow {
  year_ce: number;
  year_be: number;
  numerator_cases_C: number;
  numerator_ipd_H: number;
  opd_O: number;
  unknown_U: number;
  population_denominator: number | null;
  population_year_ce: number | null;
  population_year_be: number | null;
  is_fallback_year: boolean;
  scope_name_th: string;
  scope_name_en: string;
  case_rate_per_100k: number | null;
  case_rate_ci: [number, number] | null;
  hosp_rate_per_100k: number | null;
  hosp_rate_ci: [number, number] | null;
  hospitalization_prop: number;
  hospitalization_prop_ci: [number, number];
  denominator_note_th?: string;
  denominator_note_en?: string;
}

export interface ComparatorSummary {
  province_code: string;
  province_name_th: string;
  province_name_en: string;
  denominator_info: DenominatorInfo;
  measures: {
    cases_C: number;
    ipd_H: number;
    opd_O: number;
    unknown_U: number;
    hospitalization_prop: number;
    hospitalization_prop_ci: [number, number];
    patient_type_completeness: number;
    compatible_population: number | null;
    case_notification_rate: number | null;
    case_notification_rate_ci: [number, number] | null;
  };
}

export interface SourceFileSummaryItem {
  source_file: string;
  source_sheet: string;
  non_empty_rows: number;
  eligible_contributed: number;
  duplicates_or_excluded: number;
}

export interface AuditTrail {
  total_rows_imported: number;
  trailing_blanks_removed: number;
  non_empty_records: number;
  exact_duplicates_removed?: number;
  cross_file_revisions_superseded?: number;
  superseded_revisions_removed: number;
  authoritative_episodes_total: number;
  cancelled_episodes_excluded: number;
  pending_or_other_excluded: number;
  missing_status_excluded: number;
  used_fallback_approval: boolean;
  eligible_episodes_C: number;
  ipd_episodes_H: number;
  opd_episodes_O: number;
  unknown_patient_type_U: number;
  patient_type_missing_pct: number;
  suspicious_age_count: number;
  missing_onset_date_count: number;
  recorded_deaths_count: number;
  known_alive_count?: number;
  unknown_outcome_count?: number;
  source_files_summary?: SourceFileSummaryItem[];
}

export interface OverviewMeasures {
  cases_C: number;
  ipd_H: number;
  opd_O: number;
  unknown_U: number;
  known_patient_type: number;
  hospitalization_prop: number;
  hospitalization_prop_ci: [number, number];
  patient_type_completeness: number;
  compatible_population: number | null;
  case_notification_rate: number | null;
  case_notification_rate_ci: [number, number] | null;
  hosp_notification_rate: number | null;
  hosp_notification_rate_ci: [number, number] | null;
  is_synthetic: boolean;
  scope_mode?: GeographyScopeMode;
  selected_province_codes?: string[];
  province_name_th: string;
  province_name_en: string;
  scope_name_th?: string;
  scope_name_en?: string;
  effective_year?: number | null;
  effective_prov_code?: string | null;
  effective_district_code?: string | null;
  detected_provinces?: string[];
  detected_years?: number[];
  numerator_cases_C?: number;
  numerator_ipd_H?: number;
  population_denominator?: number | null;
  population_year_ce?: number | null;
  population_year_be?: number | null;
  is_fallback_year?: boolean;
  denominator_info?: DenominatorInfo;
  rates_by_year?: RateByYearRow[];
  comparator?: ComparatorSummary | null;
  filters?: ActiveFilters;
  audit_trail: AuditTrail;
}

export interface WeekPoint {
  t: number;
  epi_year: number;
  epi_week: number;
  week_start: string;
  week_end: string;
  label_th: string;
  label_en: string;
  total_cases: number;
  ipd_cases: number;
  opd_cases: number;
  unknown_cases: number;
}

export interface DistrictSummaryRow {
  district_code: string;
  province_code?: string;
  district_name_th: string;
  district_name_en: string;
  province_name_th?: string;
  province_name_en?: string;
  lookup_status?: string;
  cases_C: number;
  numerator_cases_C?: number;
  numerator_ipd_H?: number;
  ipd_H: number;
  opd_O: number;
  unknown_U: number;
  hospitalization_prop: number;
  hospitalization_prop_ci: [number, number];
  patient_type_completeness: number;
  district_population: number | null;
  population_year_ce?: number | null;
  population_year_be?: number | null;
  case_rate_per_100k: number | null;
  case_rate_ci: [number, number] | null;
  hosp_rate_per_100k: number | null;
  hosp_rate_ci: [number, number] | null;
  rate_status_note: string;
}

export interface AgeBurdenRow {
  age_band: string;
  cases_C: number;
  numerator_cases_C?: number;
  numerator_ipd_H?: number;
  compatible_population: number | null;
  population_year_ce?: number | null;
  population_year_be?: number | null;
  is_fallback_year?: boolean;
  scope_name_th?: string;
  scope_name_en?: string;
  case_notification_rate: number | null;
  case_notification_rate_ci: [number, number] | null;
  ipd_H: number;
  opd_O: number;
  unknown_U: number;
  hospitalization_prop: number;
  hospitalization_prop_ci: [number, number];
  patient_type_completeness: number;
  hosp_notification_rate: number | null;
  hosp_notification_rate_ci: [number, number] | null;
  denominator_note_th?: string | null;
  denominator_note_en?: string | null;
}

export interface ForecastPoint {
  t: number;
  epi_year: number;
  epi_week: number;
  week_start: string;
  week_end: string;
  label_th: string;
  label_en: string;
  observed: number | null;
  fitted: number | null;
  fitted_clipped: number | null;
  pi_80_lower: number | null;
  pi_80_upper: number | null;
  pi_95_lower: number | null;
  pi_95_upper: number | null;
  is_forecast: boolean;
  is_lag_excluded?: boolean;
}

export interface ForecastResult {
  status: 'success' | 'unavailable';
  reason?: string;
  model_type?: string;
  formula?: string;
  beta0?: number;
  beta1?: number;
  n_training_weeks?: number;
  max_window_weeks?: number;
  used_shorter_history?: boolean;
  training_start_week?: string;
  training_end_week?: string;
  training_start_date?: string;
  training_end_date?: string;
  training_window_note_th?: string;
  training_window_note_en?: string;
  horizon_weeks?: number;
  lag_excluded_weeks?: number;
  r_squared?: number;
  sigma_residuals?: number;
  validation_metrics?: {
    validation_holdout_weeks: number;
    mae: number | null;
    rmse: number | null;
    baseline_mae: number | null;
    improvement_pct: number | null;
  };
  history?: ForecastPoint[];
  lag_excluded?: ForecastPoint[];
  forecasts?: ForecastPoint[];
  disclosure_th?: string;
  disclosure_en?: string;
  scope_name_th?: string;
  scope_name_en?: string;
}

export interface StudioFigureItem {
  id: number;
  name_th: string;
  name_en: string;
  description_th: string;
  description_en: string;
  type: string;
  available: boolean;
  disabled_reason?: string | null;
}

export interface ReferenceProvince {
  province_code: string;
  province_name_th: string;
  province_name_en: string;
  scr_group_source?: string;
}

export interface ReferenceDistrict {
  district_code: string;
  province_code: string;
  district_local_code: string;
  district_name_th: string;
  source_label_th?: string;
}

export interface StagedImportFileItem {
  staged_id: string;
  filename: string;
  file_format: 'xlsx' | 'csv';
  file_category: FileCategory;
  sheets: string[];
  selected_sheet: string;
  encoding: string;
  encoding_used: string;
  delimiter: string;
  delimiter_used: string | null;
  total_rows: number;
  non_empty_rows: number;
  trailing_blanks: number;
  columns: string[];
  std_to_detected: Record<string, string>;
  detected_to_std: Record<string, string>;
  preview_rows: Record<string, any>[];
  issues: Array<{ level: 'info' | 'warning' | 'error'; message_th: string; message_en: string }>;
  status: string;
}

export interface ImportImpactPreview {
  import_mode: ImportMode;
  has_existing_session: boolean;
  existing_eligible_cases: number;
  cases_files_count: number;
  population_files_count: number;
  geography_files_count: number;
  incoming_raw_rows: number;
  incoming_non_empty_rows: number;
  total_combined_raw_rows: number;
  exact_duplicates_removed: number;
  cross_file_revisions_superseded: number;
  superseded_revisions_removed: number;
  cancelled_episodes_excluded: number;
  resulting_eligible_cases_C: number;
  net_change_cases: number;
  source_files_summary: SourceFileSummaryItem[];
  population_files_summary: any[];
  geography_files_summary: any[];
  audit_trail: AuditTrail;
}
