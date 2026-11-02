import {
  ActiveFilters,
  OverviewMeasures,
  WeekPoint,
  DistrictSummaryRow,
  AgeBurdenRow,
  RateByYearRow,
  ForecastResult,
  StudioFigureItem,
  ReferenceProvince,
  ReferenceDistrict,
  StagedImportFileItem,
  ImportImpactPreview,
  ImportMode,
} from '../types';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '') + '/api';

export async function getSessionStatus() {
  const res = await fetch(`${API_BASE}/session/status`);
  if (!res.ok) throw new Error('Failed to fetch session status');
  return res.json();
}

export async function purgeSession() {
  const res = await fetch(`${API_BASE}/session`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to purge session');
  return res.json();
}

export async function getReferenceSummary() {
  const res = await fetch(`${API_BASE}/reference/summary`);
  if (!res.ok) throw new Error('Failed to fetch reference DB summary');
  return res.json();
}

export async function getReferenceProvinces(): Promise<{ count: number; provinces: ReferenceProvince[] }> {
  const res = await fetch(`${API_BASE}/reference/provinces`);
  if (!res.ok) throw new Error('Failed to fetch reference provinces');
  return res.json();
}

export async function getReferenceDistricts(provinceCode?: string | null): Promise<{
  province_code: string | null;
  count: number;
  bangkok_lookup_missing: boolean;
  disclosure_th: string;
  disclosure_en: string;
  districts: ReferenceDistrict[];
}> {
  const q = provinceCode ? `?province_code=${encodeURIComponent(provinceCode)}` : '';
  const res = await fetch(`${API_BASE}/reference/districts${q}`);
  if (!res.ok) throw new Error('Failed to fetch reference districts');
  return res.json();
}

export async function getActiveFilters(addressType?: string) {
  const q = addressType ? `?address_type=${encodeURIComponent(addressType)}` : '';
  const res = await fetch(`${API_BASE}/filters${q}`);
  if (!res.ok) throw new Error('Failed to fetch active filters');
  return res.json();
}

export async function updateActiveFilters(filters: Partial<ActiveFilters>) {
  const res = await fetch(`${API_BASE}/filters`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(filters),
  });
  if (!res.ok) throw new Error('Failed to update filters');
  return res.json();
}

export async function generateSyntheticData() {
  const res = await fetch(`${API_BASE}/generate-synthetic`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to generate synthetic dataset');
  }
  return res.json();
}

// Multi-file & CSV Import Queue APIs
export async function getImportSchema() {
  const res = await fetch(`${API_BASE}/import/schema`);
  if (!res.ok) throw new Error('Failed to fetch import schema');
  return res.json();
}

export async function getImportQueue(): Promise<{ queue: StagedImportFileItem[] }> {
  const res = await fetch(`${API_BASE}/import/queue`);
  if (!res.ok) throw new Error('Failed to fetch import queue');
  return res.json();
}

export async function stageImportFiles(files: File[]): Promise<{
  status: string;
  staged_Now: StagedImportFileItem[];
  queue: StagedImportFileItem[];
}> {
  const formData = new FormData();
  files.forEach((f) => formData.append('files', f));
  const res = await fetch(`${API_BASE}/import/stage`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to stage files');
  }
  return res.json();
}

export async function updateStagedImportFile(
  stagedId: string,
  payload: {
    selected_sheet?: string;
    encoding?: string;
    delimiter?: string;
    file_category?: string;
    custom_mappings?: Record<string, string>;
  }
): Promise<{ status: string; item: StagedImportFileItem; queue: StagedImportFileItem[] }> {
  const res = await fetch(`${API_BASE}/import/stage/${encodeURIComponent(stagedId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update staged file settings');
  }
  return res.json();
}

export async function removeStagedImportFile(stagedId: string): Promise<{ status: string; queue: StagedImportFileItem[] }> {
  const res = await fetch(`${API_BASE}/import/stage/${encodeURIComponent(stagedId)}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to remove staged file');
  return res.json();
}

export async function clearImportQueue(): Promise<{ status: string; queue: StagedImportFileItem[] }> {
  const res = await fetch(`${API_BASE}/import/queue`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to clear import queue');
  return res.json();
}

export async function previewImportImpact(importMode: ImportMode = 'replace'): Promise<ImportImpactPreview> {
  const res = await fetch(`${API_BASE}/import/preview-impact`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ import_mode: importMode }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to preview import impact');
  }
  return res.json();
}

export async function commitImportQueue(importMode: ImportMode = 'replace'): Promise<ImportImpactPreview & { status: string; queue: StagedImportFileItem[] }> {
  const res = await fetch(`${API_BASE}/import/commit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ import_mode: importMode }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to commit import queue');
  }
  return res.json();
}

export async function uploadDdsFile(file: File, importMode: ImportMode = 'replace') {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/upload/dds?import_mode=${importMode}`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to upload DDS file');
  }
  return res.json();
}

export async function uploadPopulationFile(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/upload/population`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to upload Population Excel workbook');
  }
  return res.json();
}

export async function uploadDistrictPopulation(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/upload/district-population`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to upload district population CSV');
  }
  return res.json();
}

export async function getOverview(): Promise<OverviewMeasures> {
  const res = await fetch(`${API_BASE}/measures/overview`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch overview measures');
  }
  return res.json();
}

export async function getTimeEpicurve(): Promise<{
  weeks: WeekPoint[];
  year_boundaries?: Array<{
    epi_year: number;
    year_be: number;
    epi_week: number;
    t: number;
    label_th: string;
    label_en: string;
  }>;
  seasonal_comparison?: {
    available: boolean;
    years_detected: number[];
    latest_year: number | null;
    latest_year_be: number | null;
    prev_year: number | null;
    prev_year_be: number | null;
    median_years_used: number[];
    median_years_count: number;
    has_rate: boolean;
    note_th: string;
    note_en: string;
    weeks: Array<{
      epi_week: number;
      week_label_th: string;
      week_label_en: string;
      latest_cases: number | null;
      prev_cases: number | null;
      median_5yr_cases: number | null;
      q25_5yr_cases: number | null;
      q75_5yr_cases: number | null;
      latest_rate: number | null;
      prev_rate: number | null;
      median_5yr_rate: number | null;
    }>;
  };
  total_weeks: number;
  earliest_date: string;
  latest_date: string;
  scope_name_th?: string;
  scope_name_en?: string;
}> {
  const res = await fetch(`${API_BASE}/time/epicurve`);
  if (!res.ok) throw new Error('Failed to fetch weekly epidemic series');
  return res.json();
}

export async function getDistrictsSummary(useIllness?: boolean): Promise<{
  use_illness_district: boolean;
  address_type?: string;
  scope_mode?: string;
  scope_name_th?: string;
  scope_name_en?: string;
  effective_prov_code?: string | null;
  effective_year?: number | null;
  detected_provinces?: string[];
  bangkok_in_scope?: boolean;
  geography_mode: string;
  disclaimer_th: string;
  disclaimer_en: string;
  districts: DistrictSummaryRow[];
  has_district_population: boolean;
}> {
  const q = useIllness !== undefined ? `?use_illness_district=${useIllness}` : '';
  const res = await fetch(`${API_BASE}/districts/summary${q}`);
  if (!res.ok) throw new Error('Failed to fetch district summary');
  return res.json();
}

export async function getPlaceGeoJson(level: 'national' | 'province', provinceCode?: string | null): Promise<any> {
  const params = new URLSearchParams();
  params.set('level', level);
  if (provinceCode) params.set('province_code', provinceCode);
  const res = await fetch(`${API_BASE}/place/geojson?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch GeoJSON boundaries');
  return res.json();
}

export async function getPlaceChoropleth(params?: {
  useIllness?: boolean;
  mapProvinceCode?: string | null;
}): Promise<any> {
  const sp = new URLSearchParams();
  if (params?.useIllness !== undefined) sp.set('use_illness_district', String(params.useIllness));
  if (params?.mapProvinceCode) sp.set('map_province_code', params.mapProvinceCode);
  const qs = sp.toString();
  const res = await fetch(`${API_BASE}/place/choropleth${qs ? `?${qs}` : ''}`);
  if (!res.ok) throw new Error('Failed to fetch choropleth map metrics');
  return res.json();
}

export async function getPersonPyramid(): Promise<{
  scope_mode?: string;
  scope_name_th?: string;
  scope_name_en?: string;
  denominator?: any;
  rates_by_year?: RateByYearRow[];
  pyramid: Array<{ age_band: string; male: number; female: number; unknown_sex: number; total: number }>;
  nationality_breakdown: { Thai: number; 'Non-Thai': number; Unknown: number };
}> {
  const res = await fetch(`${API_BASE}/person/age-pyramid`);
  if (!res.ok) throw new Error('Failed to fetch person pyramid');
  return res.json();
}

export async function getTable0(): Promise<{ rows: any[]; source_files_summary?: any[] }> {
  const res = await fetch(`${API_BASE}/tables/table0`);
  if (!res.ok) throw new Error('Failed to fetch Table 0');
  return res.json();
}

export async function getTable1(): Promise<any> {
  const res = await fetch(`${API_BASE}/tables/table1`);
  if (!res.ok) throw new Error('Failed to fetch Table 1');
  return res.json();
}

export async function getTable2(): Promise<{
  rows: AgeBurdenRow[];
  scope_mode?: string;
  selected_province_codes?: string[];
  scope_name_th?: string;
  scope_name_en?: string;
  denominator?: any;
  rates_by_year?: RateByYearRow[];
}> {
  const res = await fetch(`${API_BASE}/tables/table2`);
  if (!res.ok) throw new Error('Failed to fetch Table 2');
  return res.json();
}

export async function getTable3(useIllness?: boolean): Promise<{ rows: DistrictSummaryRow[]; scope_name_th?: string }> {
  const q = useIllness !== undefined ? `?use_illness_district=${useIllness}` : '';
  const res = await fetch(`${API_BASE}/tables/table3${q}`);
  if (!res.ok) throw new Error('Failed to fetch Table 3');
  return res.json();
}

export async function getTable4(horizon: number = 4): Promise<ForecastResult> {
  const res = await fetch(`${API_BASE}/tables/table4?horizon=${horizon}`);
  if (!res.ok) throw new Error('Failed to fetch Table 4 (Forecast)');
  return res.json();
}

export async function runForecast(
  horizon: number = 4,
  lagExclude: number = 1,
  seasonal: boolean = false
): Promise<ForecastResult> {
  const res = await fetch(`${API_BASE}/forecast/run?horizon=${horizon}&lag_exclude=${lagExclude}&seasonal=${seasonal}`);
  if (!res.ok) throw new Error('Failed to compute forecast');
  return res.json();
}

export async function getStudioFigures(): Promise<StudioFigureItem[]> {
  const res = await fetch(`${API_BASE}/studio/figures`);
  if (!res.ok) throw new Error('Failed to fetch studio figures');
  return res.json();
}

export function getFigureRenderUrl(
  figId: number,
  options: {
    format?: string;
    theme?: string;
    preset?: string;
    transparent?: boolean;
    lang?: string;
    title?: string;
    subtitle?: string;
    footnote?: string;
    placeLevel?: string;
    placeMetric?: string;
  } = {}
) {
  const params = new URLSearchParams();
  if (options.format) params.append('format', options.format);
  if (options.theme) params.append('theme', options.theme);
  if (options.preset) params.append('preset', options.preset);
  if (options.transparent) params.append('transparent', 'true');
  if (options.lang) params.append('lang', options.lang);
  if (options.title) params.append('title', options.title);
  if (options.subtitle) params.append('subtitle', options.subtitle);
  if (options.footnote) params.append('footnote', options.footnote);
  if (options.placeLevel) params.append('place_level', options.placeLevel);
  if (options.placeMetric) params.append('place_metric', options.placeMetric);
  return `${API_BASE}/studio/render-figure/${figId}?${params.toString()}`;
}

export function getPresentationPackUrl(theme: string = 'light', lang: string = 'th') {
  return `${API_BASE}/studio/presentation-pack.zip?theme=${theme}&lang=${lang}`;
}

export function getExcelExportUrl() {
  return `${API_BASE}/export/excel`;
}

export function getCsvExportUrl(tableId: string) {
  return `${API_BASE}/export/csv/${tableId}`;
}
