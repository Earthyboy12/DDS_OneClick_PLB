import React, { useEffect, useMemo, useState } from 'react';
import {
  Globe2,
  MapPin,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Layers,
  Palette,
  ArrowUpRight,
  Filter,
  Sparkles,
  X,
  Plus,
} from 'lucide-react';
import { getPlaceChoropleth, getPlaceGeoJson } from '../services/api';

export type MapLevel = 'national' | 'province';
export type MapMetric = 'rate' | 'cases' | 'ipd_pct';
export type ColorScheme = 'teal' | 'heat' | 'indigo' | 'prism';

interface ChoroplethMapProps {
  lang: 'th' | 'en';
  figLang: 'th' | 'en';
  useIllness: boolean;
  filterVersion: number;
  selectedProvinceCodes: string[];
  selectedDistrictCode: string | null;
  onSelectProvince: (provCode: string) => void;
  onUpdateProvinces?: (provCodes: string[]) => void;
  onSelectDistrict: (distCode: string | null, provCode?: string) => void;
  controlledLevel?: MapLevel;
  onLevelChange?: (level: MapLevel) => void;
  controlledMetric?: MapMetric;
  onMetricChange?: (metric: MapMetric) => void;
  onChoroplethLoaded?: (data: any, inspectProvince: string) => void;
}

const COLOR_RAMPS: Record<ColorScheme, string[]> = {
  prism: ['#f8fafc', '#dbeafe', '#93c5fd', '#60a5fa', '#3b82f6', '#2563eb', '#1d4ed8', '#1e40af', '#1e3a8a', '#0f172a'],
  teal: ['#f0fdfa', '#ccfbf1', '#99f6e4', '#5eead4', '#2dd4bf', '#14b8a6', '#0d9488', '#0f766e', '#115e59', '#134e4a'],
  heat: ['#fffbeb', '#fef3c7', '#fde68a', '#fcd34d', '#fbbf24', '#f59e0b', '#ea580c', '#dc2626', '#b91c1c', '#7f1d1d'],
  indigo: ['#eef2ff', '#e0e7ff', '#c7d2fe', '#a5b4fc', '#818cf8', '#6366f1', '#4f46e5', '#4338ca', '#3730a3', '#1e1b4b'],
};

function getColorForValue(val: number | null | undefined, maxVal: number, scheme: ColorScheme): string {
  if (val === null || val === undefined || val <= 0 || maxVal <= 0) {
    return '#f1f5f9';
  }
  const ramp = COLOR_RAMPS[scheme];
  const ratio = Math.min(1, Math.max(0, Math.sqrt(val / maxVal)));
  const idx = Math.min(ramp.length - 1, Math.max(1, Math.floor(ratio * (ramp.length - 1)) + 1));
  return ramp[idx];
}

export const ChoroplethMap: React.FC<ChoroplethMapProps> = ({
  lang,
  figLang,
  useIllness,
  filterVersion,
  selectedProvinceCodes,
  selectedDistrictCode,
  onSelectProvince,
  onUpdateProvinces,
  onSelectDistrict,
  controlledLevel,
  onLevelChange,
  controlledMetric,
  onMetricChange,
  onChoroplethLoaded,
}) => {
  const [internalLevel, setInternalLevel] = useState<MapLevel>('national');
  const [inspectProvince, setInspectProvince] = useState<string>('10');
  const [internalMetric, setInternalMetric] = useState<MapMetric>('rate');
  const [colorScheme, setColorScheme] = useState<ColorScheme>('prism');
  const [focusSelectedOnly, setFocusSelectedOnly] = useState<boolean>(true);

  const mapLevel = controlledLevel ?? internalLevel;
  const setMapLevel = (lvl: MapLevel) => {
    setInternalLevel(lvl);
    onLevelChange?.(lvl);
  };

  const metric = controlledMetric ?? internalMetric;
  const setMetric = (m: MapMetric) => {
    setInternalMetric(m);
    onMetricChange?.(m);
  };

  const activeSelectedProvs = useMemo(() => {
    return (selectedProvinceCodes || []).filter((p) => p && p !== '00' && p !== 'all');
  }, [selectedProvinceCodes]);

  const effectiveProvParam = useMemo(() => {
    if (activeSelectedProvs.length > 0 && focusSelectedOnly) {
      return activeSelectedProvs.join(',');
    }
    return mapLevel === 'province' ? inspectProvince : null;
  }, [activeSelectedProvs, focusSelectedOnly, mapLevel, inspectProvince]);

  const [choroplethData, setChoroplethData] = useState<any | null>(null);
  const [geoJson, setGeoJson] = useState<any | null>(null);
  const [loadingGeo, setLoadingGeo] = useState<boolean>(false);

  const [hoveredCode, setHoveredCode] = useState<string | null>(null);
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Sync map level when user filters to province(s) or district from the top FilterBar
  useEffect(() => {
    if (selectedDistrictCode && selectedDistrictCode.length === 4) {
      const pCode = selectedDistrictCode.slice(0, 2);
      setInspectProvince(pCode);
      setMapLevel('province');
    } else if (activeSelectedProvs.length >= 1) {
      setInspectProvince(activeSelectedProvs[0]);
    }
  }, [selectedProvinceCodes.join(','), selectedDistrictCode]);

  // Fetch Choropleth analytical metrics
  useEffect(() => {
    getPlaceChoropleth({
      useIllness,
      mapProvinceCode: effectiveProvParam,
    })
      .then((res) => {
        setChoroplethData(res);
        let effInspect = inspectProvince;
        if (activeSelectedProvs.length > 0) {
          effInspect = activeSelectedProvs[0];
          setInspectProvince(effInspect);
        } else if (mapLevel !== 'province' && res.target_district_provinces?.length > 0) {
          effInspect = res.target_district_provinces[0];
          setInspectProvince(effInspect);
        }
        onChoroplethLoaded?.(res, effInspect);
      })
      .catch(console.error);
  }, [useIllness, filterVersion, mapLevel, effectiveProvParam]);

  // Fetch GeoJSON boundaries for current level
  useEffect(() => {
    setLoadingGeo(true);
    getPlaceGeoJson(mapLevel, effectiveProvParam)
      .then((geo) => {
        setGeoJson(geo);
        setZoom(1);
        setPan({ x: 0, y: 0 });
      })
      .catch(console.error)
      .finally(() => setLoadingGeo(false));
  }, [mapLevel, effectiveProvParam]);

  // Build lookup dictionary of metrics keyed by code ('10'..'96' or '1001'..'9613')
  const metricsMap = useMemo(() => {
    const map: Record<string, any> = {};
    if (!choroplethData) return map;
    if (mapLevel === 'national') {
      for (const p of choroplethData.provinces || []) {
        map[p.province_code] = p;
      }
    } else {
      for (const d of choroplethData.districts || []) {
        map[d.district_code] = d;
      }
    }
    return map;
  }, [choroplethData, mapLevel]);

  const effectiveMetric: MapMetric = metric;

  const getVal = (item: any): number => {
    if (!item) return 0;
    if (effectiveMetric === 'rate') return Number(item.case_rate_per_100k || 0);
    if (effectiveMetric === 'ipd_pct') return Number(item.hospitalization_prop || 0);
    return Number(item.cases_C || 0);
  };

  // Compute SVG projected paths from GeoJSON features
  const projected = useMemo(() => {
    const features = geoJson?.features || [];
    if (!features.length) {
      return { paths: [], width: 560, height: 640 };
    }

    let minLon = Infinity;
    let maxLon = -Infinity;
    let minLat = Infinity;
    let maxLat = -Infinity;

    const visitCoords = (coords: any) => {
      if (!Array.isArray(coords)) return;
      if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
        const lon = coords[0];
        const lat = coords[1];
        if (lon < minLon) minLon = lon;
        if (lon > maxLon) maxLon = lon;
        if (lat < minLat) minLat = lat;
        if (lat > maxLat) maxLat = lat;
      } else {
        for (const c of coords) visitCoords(c);
      }
    };

    for (const f of features) {
      visitCoords(f.geometry?.coordinates);
    }

    if (!isFinite(minLon) || !isFinite(minLat)) {
      return { paths: [], width: 560, height: 640 };
    }

    const midLatRad = (((minLat + maxLat) / 2) * Math.PI) / 180;
    const cosFactor = Math.cos(midLatRad);

    const lonSpan = Math.max(0.01, (maxLon - minLon) * cosFactor);
    const latSpan = Math.max(0.01, maxLat - minLat);

    const svgWidth = 560;
    const svgHeight = 620;
    const pad = 28;

    const scaleX = (svgWidth - pad * 2) / lonSpan;
    const scaleY = (svgHeight - pad * 2) / latSpan;
    const scale = Math.min(scaleX, scaleY);

    const drawnW = lonSpan * scale;
    const drawnH = latSpan * scale;
    const offsetX = (svgWidth - drawnW) / 2;
    const offsetY = (svgHeight - drawnH) / 2;

    const projectPoint = (lon: number, lat: number): [number, number] => {
      const x = offsetX + (lon - minLon) * cosFactor * scale;
      const y = offsetY + (maxLat - lat) * scale;
      return [x, y];
    };

    const ringToSvg = (ring: number[][]): string => {
      if (!ring || ring.length < 3) return '';
      return (
        ring
          .map((pt, idx) => {
            const [x, y] = projectPoint(pt[0], pt[1]);
            return `${idx === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
          })
          .join(' ') + ' Z'
      );
    };

    const builtPaths = features.map((f: any) => {
      const props = f.properties || {};
      const code = mapLevel === 'national' ? String(props.pro_code || '').padStart(2, '0') : String(props.amp_code || '').padStart(4, '0');
      const nameTh = mapLevel === 'national' ? props.pro_th : props.amp_th;
      const nameEn = mapLevel === 'national' ? props.pro_en : props.amp_en;
      const geom = f.geometry || {};
      const gtype = geom.type;
      const coords = geom.coordinates || [];

      let dStr = '';
      if (gtype === 'Polygon') {
        for (const ring of coords) {
          dStr += ringToSvg(ring) + ' ';
        }
      } else if (gtype === 'MultiPolygon') {
        for (const poly of coords) {
          for (const ring of poly) {
            dStr += ringToSvg(ring) + ' ';
          }
        }
      }

      const [cx, cy] = props.lon && props.lat ? projectPoint(Number(props.lon), Number(props.lat)) : [svgWidth / 2, svgHeight / 2];

      return {
        code,
        nameTh: nameTh || code,
        nameEn: nameEn || code,
        provCode: String(props.pro_code || code.slice(0, 2)).padStart(2, '0'),
        d: dStr.trim(),
        cx,
        cy,
      };
    });

    return { paths: builtPaths, width: svgWidth, height: svgHeight };
  }, [geoJson, mapLevel]);

  const maxVal = useMemo(() => {
    if (projected.paths.length > 0) {
      const vals = projected.paths.map((p: any) => getVal(metricsMap[p.code])).filter((v: number) => v > 0);
      if (vals.length > 0) return Math.max(1, ...vals);
    }
    const items = Object.values(metricsMap);
    if (!items.length) return 1;
    return Math.max(1, ...items.map((it) => getVal(it)));
  }, [projected.paths, metricsMap, effectiveMetric]);

  // Build 5 quantitative class intervals for the Colorbar Legend so the user sees exact colour -> Case/Incidence mapping
  const colorBins = useMemo(() => {
    const ramp = COLOR_RAMPS[colorScheme];
    const fmt = (v: number) =>
      effectiveMetric === 'cases'
        ? Math.round(v).toLocaleString()
        : effectiveMetric === 'ipd_pct'
        ? `${v.toFixed(1)}%`
        : v.toFixed(1);

    // Since getColorForValue uses sqrt(val / maxVal), threshold at ratio r corresponds to val = r^2 * maxVal
    const stops = [0, 0.25, 0.5, 0.75, 1.0];
    const bins: Array<{ color: string; label: string }> = [
      {
        color: '#f1f5f9',
        label: effectiveMetric === 'cases' ? '0' : '0.0',
      },
    ];
    const binColors = [ramp[2], ramp[4], ramp[6], ramp[9]];
    for (let i = 0; i < 4; i++) {
      const low = Math.pow(stops[i], 2) * maxVal;
      const high = Math.pow(stops[i + 1], 2) * maxVal;
      const lowLabel = i === 0 ? (effectiveMetric === 'cases' ? '1' : '0.1') : fmt(low);
      bins.push({
        color: binColors[i],
        label: `${lowLabel} – ${fmt(high)}`,
      });
    }
    return bins;
  }, [maxVal, colorScheme, effectiveMetric]);

  // Top 5 ranked items in current view
  const topRanked = useMemo(() => {
    const items =
      projected.paths.length > 0
        ? projected.paths.map((p: any) => metricsMap[p.code]).filter(Boolean)
        : Object.values(metricsMap);
    return [...items]
      .filter((it) => getVal(it) > 0)
      .sort((a, b) => getVal(b) - getVal(a))
      .slice(0, 5);
  }, [projected.paths, metricsMap, effectiveMetric]);

  const hoveredItem = hoveredCode ? metricsMap[hoveredCode] : null;
  const hoveredPath = hoveredCode ? projected.paths.find((p: any) => p.code === hoveredCode) : null;

  const activeProvinceInfo = useMemo(() => {
    if (!choroplethData?.provinces) return null;
    return choroplethData.provinces.find((p: any) => p.province_code === inspectProvince) || null;
  }, [choroplethData, inspectProvince]);

  const selectedProvNamesTh = useMemo(() => {
    if (!choroplethData?.provinces || !activeSelectedProvs.length) return '';
    return activeSelectedProvs
      .map((c) => {
        const found = choroplethData.provinces.find((p: any) => p.province_code === c);
        return found ? found.province_name_th : c;
      })
      .join(', ');
  }, [choroplethData, activeSelectedProvs]);

  const selectedProvNamesEn = useMemo(() => {
    if (!choroplethData?.provinces || !activeSelectedProvs.length) return '';
    return activeSelectedProvs
      .map((c) => {
        const found = choroplethData.provinces.find((p: any) => p.province_code === c);
        return found ? (found.province_name_en || c) : c;
      })
      .join(', ');
  }, [choroplethData, activeSelectedProvs]);

  const metricLabel =
    effectiveMetric === 'rate'
      ? figLang === 'th'
        ? 'อุบัติการณ์ / อัตราป่วยต่อแสนประชากร (Incidence per 100,000)'
        : 'Incidence / Notification Rate (per 100,000)'
      : effectiveMetric === 'ipd_pct'
      ? figLang === 'th'
        ? 'สัดส่วนผู้ป่วยใน (IPD %)'
        : 'Hospitalization Proportion (IPD %)'
      : figLang === 'th'
      ? 'จำนวนผู้ป่วยสะสม (ราย / Cases)'
      : 'Reported Cases (n)';

  const unitSuffix =
    effectiveMetric === 'rate'
      ? figLang === 'th'
        ? 'ต่อแสนประชากร'
        : 'per 100k'
      : effectiveMetric === 'ipd_pct'
      ? '%'
      : figLang === 'th'
      ? 'ราย'
      : 'cases';

  return (
    <div className="bg-white rounded-2xl border-2 border-slate-900 shadow-xs overflow-hidden">
      {/* Top Toolbar */}
      <div className="p-5 border-b-2 border-slate-900 bg-white flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 text-white text-xs font-bold">
              <Globe2 className="w-3.5 h-3.5" />
              {lang === 'th' ? 'แผนที่ระบาดวิทยาเชิงพื้นที่' : 'Choropleth Map'}
            </span>
            <h4 className="font-extrabold text-slate-950 text-base">
              {activeSelectedProvs.length >= 1 && focusSelectedOnly
                ? mapLevel === 'national'
                  ? figLang === 'th'
                    ? `เปรียบเทียบเฉพาะจังหวัดที่เลือก: ${selectedProvNamesTh}`
                    : `Selected Comparison: ${selectedProvNamesEn}`
                  : figLang === 'th'
                  ? `ระดับอำเภอ — รวมเขต/อำเภอของ ${selectedProvNamesTh}`
                  : `District Level — ${selectedProvNamesEn}`
                : mapLevel === 'national'
                ? figLang === 'th'
                  ? 'ระดับจังหวัด (77 จังหวัด)'
                  : 'Province Level (77 Provinces)'
                : figLang === 'th'
                ? `ระดับอำเภอ — จังหวัด${activeProvinceInfo?.province_name_th || inspectProvince} (รหัส ${inspectProvince})`
                : `District Level — ${activeProvinceInfo?.province_name_en || inspectProvince} (${inspectProvince})`}
            </h4>
            {choroplethData?.population_year_be && (
              <span className="text-[11px] px-2.5 py-0.5 rounded border border-slate-900 bg-slate-100 text-slate-900 font-bold">
                {lang === 'th'
                  ? `ประชากร พ.ศ. ${choroplethData.population_year_be}${choroplethData.is_median_year ? ' (มัธยฐาน)' : ''}`
                  : `Pop B.E. ${choroplethData.population_year_be}${choroplethData.is_median_year ? ' (Median)' : ''}`}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-600 font-medium">
            {mapLevel === 'national'
              ? lang === 'th'
                ? 'เลือกแสดงสีตามอุบัติการณ์ (Incidence ต่อแสนประชากร) หรือจำนวนเคส • คลิกที่จังหวัดบนแผนที่เพื่อเจาะลึกดูระดับอำเภอ'
                : 'Color by Incidence per 100k or Case Counts • Click any province polygon to drill down into districts'
              : lang === 'th'
              ? 'แสดงผลระดับอำเภอตามอุบัติการณ์ (Incidence ต่อแสนประชากร) หรือจำนวนเคส • คลิกที่อำเภอเพื่อกรองข้อมูลเฉพาะอำเภอ'
              : 'District-level Choropleth by Incidence per 100k or Case Counts • Click any district polygon to filter'}
          </p>
        </div>

        {/* Controls: Level Toggle (Province vs District), Focus Toggle, Province Selector, Metric Toggle, Color Scheme */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Level Selector: Province Level vs District Level */}
          <div className="inline-flex rounded-lg bg-slate-100 p-1 border-2 border-slate-900">
            <button
              onClick={() => {
                setMapLevel('national');
                setHoveredCode(null);
              }}
              className={`px-3 py-1.5 rounded-md text-xs font-extrabold transition flex items-center gap-1.5 ${
                mapLevel === 'national'
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'text-slate-700 hover:text-slate-950'
              }`}
            >
              <Globe2 className="w-3.5 h-3.5" />
              <span>{lang === 'th' ? 'ระดับจังหวัด' : 'Province Level'}</span>
            </button>
            <button
              onClick={() => {
                setMapLevel('province');
                setHoveredCode(null);
              }}
              className={`px-3 py-1.5 rounded-md text-xs font-extrabold transition flex items-center gap-1.5 ${
                mapLevel === 'province'
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'text-slate-700 hover:text-slate-950'
              }`}
            >
              <MapPin className="w-3.5 h-3.5" />
              <span>{lang === 'th' ? 'ระดับอำเภอ' : 'District Level'}</span>
            </button>
          </div>

          {/* Multi-Province Focus Mode Toggle (Only when 1 or more provinces are selected) */}
          {activeSelectedProvs.length > 0 && (
            <div className="inline-flex rounded-lg bg-amber-50 p-1 border-2 border-amber-600">
              <button
                onClick={() => setFocusSelectedOnly(true)}
                className={`px-2.5 py-1.5 rounded-md text-xs font-black transition flex items-center gap-1 ${
                  focusSelectedOnly
                    ? 'bg-amber-600 text-white shadow-2xs'
                    : 'text-amber-900 hover:text-black'
                }`}
                title={lang === 'th' ? 'ซูมและแสดงเฉพาะจังหวัดที่เลือกไว้' : 'Focus and show only selected provinces'}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>
                  {lang === 'th'
                    ? `เฉพาะที่เลือก (${activeSelectedProvs.length} จ.)`
                    : `Selected Only (${activeSelectedProvs.length})`}
                </span>
              </button>
              <button
                onClick={() => setFocusSelectedOnly(false)}
                className={`px-2.5 py-1.5 rounded-md text-xs font-black transition flex items-center gap-1 ${
                  !focusSelectedOnly
                    ? 'bg-slate-900 text-white shadow-2xs'
                    : 'text-slate-700 hover:text-black'
                }`}
                title={lang === 'th' ? 'แสดงทั้ง 77 จังหวัดทั่วประเทศ' : 'Show all 77 provinces'}
              >
                <span>{lang === 'th' ? 'ทั่วประเทศ (77)' : 'All 77'}</span>
              </button>
            </div>
          )}

          {/* Province Dropdown (for jumping to any province's districts) */}
          <select
            value={inspectProvince}
            onChange={(e) => {
              const pc = e.target.value;
              setInspectProvince(pc);
              setMapLevel('province');
              setHoveredCode(null);
            }}
            className="px-3 py-1.5 rounded-lg border-2 border-slate-900 bg-white text-slate-900 text-xs font-bold focus:outline-none"
            title={lang === 'th' ? 'เลือกจังหวัดเพื่อดูแผนที่ระดับอำเภอ' : 'Select province for district choropleth'}
          >
            {(choroplethData?.provinces || []).map((p: any) => (
              <option key={p.province_code} value={p.province_code}>
                [{p.province_code}] {lang === 'th' ? p.province_name_th : p.province_name_en} ({p.cases_C.toLocaleString()}{' '}
                {lang === 'th' ? 'ราย' : 'cases'})
              </option>
            ))}
          </select>

          {/* Metric Selector: Incidence vs Cases vs IPD % */}
          <div className="inline-flex rounded-lg bg-slate-100 p-1 border-2 border-slate-900">
            <button
              onClick={() => setMetric('rate')}
              className={`px-2.5 py-1 rounded-md text-xs font-extrabold transition ${
                effectiveMetric === 'rate'
                  ? 'bg-[#1d4ed8] text-white shadow-2xs'
                  : 'text-slate-700 hover:text-slate-950'
              }`}
            >
              {lang === 'th' ? 'อุบัติการณ์ (Incidence/แสน)' : 'Incidence / 100k'}
            </button>
            <button
              onClick={() => setMetric('cases')}
              className={`px-2.5 py-1 rounded-md text-xs font-extrabold transition ${
                effectiveMetric === 'cases'
                  ? 'bg-[#1d4ed8] text-white shadow-2xs'
                  : 'text-slate-700 hover:text-slate-950'
              }`}
            >
              {lang === 'th' ? 'จำนวนเคส (Cases)' : 'Cases (C)'}
            </button>
            <button
              onClick={() => setMetric('ipd_pct')}
              className={`px-2.5 py-1 rounded-md text-xs font-extrabold transition ${
                effectiveMetric === 'ipd_pct'
                  ? 'bg-[#1d4ed8] text-white shadow-2xs'
                  : 'text-slate-700 hover:text-slate-950'
              }`}
            >
              IPD %
            </button>
          </div>

          {/* Color Scheme Selector */}
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border-2 border-slate-900 bg-white">
            <Palette className="w-3.5 h-3.5 text-slate-700 mr-0.5" />
            {(['prism', 'teal', 'heat', 'indigo'] as ColorScheme[]).map((sc) => (
              <button
                key={sc}
                onClick={() => setColorScheme(sc)}
                className={`w-4 h-4 rounded-sm border border-slate-900 transition ${
                  colorScheme === sc ? 'ring-2 ring-offset-1 ring-slate-900 scale-110' : 'opacity-70 hover:opacity-100'
                }`}
                style={{
                  background:
                    sc === 'prism'
                      ? 'linear-gradient(135deg, #93c5fd, #1e3a8a)'
                      : sc === 'teal'
                      ? 'linear-gradient(135deg, #5eead4, #0f766e)'
                      : sc === 'heat'
                      ? 'linear-gradient(135deg, #fcd34d, #dc2626)'
                      : 'linear-gradient(135deg, #a5b4fc, #3730a3)',
                }}
                title={sc.toUpperCase()}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Comparison & Filter Presets Sub-Bar */}
      <div className="px-5 py-2.5 bg-slate-50 border-b-2 border-slate-900 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-extrabold text-slate-800 flex items-center gap-1">
            <Layers className="w-3.5 h-3.5 text-blue-700" />
            {lang === 'th' ? 'การเปรียบเทียบจังหวัด:' : 'Province Scope:'}
          </span>

          {/* Active province badges with remove button */}
          {activeSelectedProvs.length > 0 ? (
            <div className="flex flex-wrap items-center gap-1.5">
              {activeSelectedProvs.map((code) => {
                const pInfo = choroplethData?.provinces?.find((p: any) => p.province_code === code);
                const name = lang === 'th' ? (pInfo?.province_name_th || code) : (pInfo?.province_name_en || code);
                return (
                  <span
                    key={code}
                    className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-blue-100 border border-blue-900 text-blue-950 font-bold text-[11px]"
                  >
                    <span>{name} ({code})</span>
                    {onUpdateProvinces && (
                      <button
                        onClick={() => {
                          const rem = activeSelectedProvs.filter((c) => c !== code);
                          onUpdateProvinces(rem.length > 0 ? rem : ['00']);
                        }}
                        className="hover:bg-blue-200 rounded-full p-0.5 transition ml-0.5"
                        title={lang === 'th' ? 'นำออกจากการเปรียบเทียบ' : 'Remove'}
                      >
                        <X className="w-3 h-3 text-blue-900" />
                      </button>
                    )}
                  </span>
                );
              })}
            </div>
          ) : (
            <span className="text-slate-500 italic text-[11px]">
              {lang === 'th' ? 'ทั่วประเทศ (ยังไม่ได้เลือกเปรียบเทียบเฉพาะกลุ่ม)' : 'All provinces (no filter)'}
            </span>
          )}

          {/* Add Province Dropdown */}
          {onUpdateProvinces && (
            <select
              value=""
              onChange={(e) => {
                const addCode = e.target.value;
                if (addCode && !activeSelectedProvs.includes(addCode)) {
                  onUpdateProvinces([...activeSelectedProvs, addCode]);
                  setFocusSelectedOnly(true);
                }
              }}
              className="px-2 py-1 rounded border border-slate-700 bg-white text-slate-900 text-[11px] font-bold focus:outline-none"
            >
              <option value="">{lang === 'th' ? '＋ เพิ่มจังหวัดเทียบ...' : '+ Add Province...'}</option>
              {(choroplethData?.provinces || [])
                .filter((p: any) => !activeSelectedProvs.includes(p.province_code))
                .map((p: any) => (
                  <option key={p.province_code} value={p.province_code}>
                    {lang === 'th' ? p.province_name_th : p.province_name_en} ({p.province_code})
                  </option>
                ))}
            </select>
          )}

          {/* Reset button */}
          {activeSelectedProvs.length > 0 && onUpdateProvinces && (
            <button
              onClick={() => {
                onUpdateProvinces(['00']);
                setFocusSelectedOnly(false);
              }}
              className="px-2 py-0.5 rounded border border-slate-400 hover:border-slate-900 bg-white text-slate-700 hover:text-slate-950 font-bold text-[11px] transition"
            >
              {lang === 'th' ? 'รีเซ็ตเป็นทั้งประเทศ' : 'Reset to All'}
            </button>
          )}
        </div>

        {/* Adjacent Province Presets */}
        {onUpdateProvinces && (
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-bold text-slate-600">{lang === 'th' ? 'คู่จังหวัดติดกัน:' : 'Adjacent Pairs:'}</span>
            {[
              { labelTh: 'กทม. + นนทบุรี', labelEn: 'BKK + Nonthaburi', codes: ['10', '12'] },
              { labelTh: 'กทม. + สมุทรปราการ', labelEn: 'BKK + Samut Prakan', codes: ['10', '11'] },
              { labelTh: 'กทม. + ปทุมธานี', labelEn: 'BKK + Pathum Thani', codes: ['10', '13'] },
              { labelTh: 'เชียงใหม่ + ลำพูน', labelEn: 'Chiang Mai + Lamphun', codes: ['50', '51'] },
              { labelTh: 'พิษณุโลก + สุโขทัย', labelEn: 'Phitsanulok + Sukhothai', codes: ['65', '64'] },
            ].map((preset) => {
              const isMatch =
                activeSelectedProvs.length === preset.codes.length &&
                preset.codes.every((c) => activeSelectedProvs.includes(c));
              return (
                <button
                  key={preset.labelEn}
                  onClick={() => {
                    onUpdateProvinces(preset.codes);
                    setFocusSelectedOnly(true);
                  }}
                  className={`px-2.5 py-0.5 rounded border text-[11px] font-bold transition ${
                    isMatch
                      ? 'bg-blue-600 text-white border-blue-800 shadow-2xs'
                      : 'bg-white text-slate-800 border-slate-300 hover:border-slate-900 hover:bg-slate-100'
                  }`}
                >
                  {lang === 'th' ? preset.labelTh : preset.labelEn}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Main Map Grid: Interactive SVG Canvas + Quantitative Colorbar + Right Side Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-12">
        {/* Left 7 Cols: Interactive SVG Map Canvas + Dedicated Quantitative Colorbar Panel */}
        <div className="lg:col-span-7 flex flex-col border-b-2 lg:border-b-0 lg:border-r-2 border-slate-900">
          <div
            className="relative bg-white min-h-[500px] flex items-center justify-center overflow-hidden select-none"
            onMouseDown={(e) => {
              if (e.button !== 0) return;
              setIsDragging(true);
              setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
            }}
            onMouseMove={(e) => {
              if (!isDragging) return;
              setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
            }}
            onMouseUp={() => setIsDragging(false)}
            onMouseLeave={() => setIsDragging(false)}
          >
            {/* Floating Zoom & Level Breadcrumb Controls */}
            <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
              <div className="bg-white border-2 border-slate-900 rounded-lg p-1 shadow-xs flex items-center gap-1">
                <button
                  onClick={() => setZoom((z) => Math.min(4, +(z + 0.35).toFixed(2)))}
                  className="p-1.5 rounded hover:bg-slate-100 text-slate-900 transition"
                  title="Zoom In"
                >
                  <ZoomIn className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setZoom((z) => Math.max(0.8, +(z - 0.35).toFixed(2)))}
                  className="p-1.5 rounded hover:bg-slate-100 text-slate-900 transition"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-4 h-4" />
                </button>
                <button
                  onClick={() => {
                    setZoom(1);
                    setPan({ x: 0, y: 0 });
                  }}
                  className="p-1.5 rounded hover:bg-slate-100 text-slate-900 transition"
                  title="Reset View"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
                <span className="text-[11px] font-mono font-bold text-slate-900 px-1.5">{Math.round(zoom * 100)}%</span>
              </div>

              {mapLevel === 'province' && (
                <button
                  onClick={() => {
                    setMapLevel('national');
                    setHoveredCode(null);
                  }}
                  className="bg-white border-2 border-slate-900 hover:bg-slate-100 text-slate-900 px-3 py-1.5 rounded-lg text-xs font-extrabold shadow-xs transition flex items-center gap-1.5"
                >
                  <Globe2 className="w-3.5 h-3.5" />
                  <span>{lang === 'th' ? '← กลับไปดูระดับจังหวัด (77 จังหวัด)' : '← Back to Province Map (77 Provinces)'}</span>
                </button>
              )}
            </div>

            {loadingGeo ? (
              <div className="text-xs font-bold text-slate-500 animate-pulse">
                {lang === 'th' ? 'กำลังโหลดพิกัดแผนที่ประเทศไทย...' : 'Loading Thailand GeoJSON boundaries...'}
              </div>
            ) : (
              <svg
                viewBox={`0 0 ${projected.width} ${projected.height}`}
                className={`w-full h-[500px] ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
              >
                <g
                  transform={`translate(${pan.x}, ${pan.y}) translate(${projected.width / 2}, ${projected.height / 2}) scale(${zoom}) translate(${-projected.width / 2}, ${-projected.height / 2})`}
                >
                  {projected.paths.map((p: any) => {
                    const item = metricsMap[p.code];
                    const val = getVal(item);
                    const fill = getColorForValue(val, maxVal, colorScheme);
                    const isHovered = hoveredCode === p.code;
                    const isSelected =
                      mapLevel === 'national'
                        ? selectedProvinceCodes.includes(p.code)
                        : selectedDistrictCode === p.code;

                    return (
                      <path
                        key={p.code}
                        d={p.d}
                        fill={fill}
                        stroke={isHovered ? '#000000' : isSelected ? '#dc2626' : '#0f172a'}
                        strokeWidth={isHovered ? 2.2 / zoom : isSelected ? 1.8 / zoom : 0.75 / zoom}
                        className="transition-colors duration-150 cursor-pointer"
                        onMouseEnter={() => setHoveredCode(p.code)}
                        onMouseLeave={() => setHoveredCode((prev) => (prev === p.code ? null : prev))}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (mapLevel === 'national') {
                            if (e.shiftKey || e.ctrlKey || e.metaKey) {
                              if (onUpdateProvinces) {
                                const already = activeSelectedProvs.includes(p.code);
                                const updated = already
                                  ? activeSelectedProvs.filter((c) => c !== p.code)
                                  : [...activeSelectedProvs, p.code];
                                onUpdateProvinces(updated.length > 0 ? updated : ['00']);
                                setFocusSelectedOnly(true);
                              }
                              return;
                            }
                            setInspectProvince(p.code);
                            setMapLevel('province');
                            setHoveredCode(null);
                          } else {
                            const nextDist = selectedDistrictCode === p.code ? null : p.code;
                            onSelectDistrict(nextDist, p.provCode);
                          }
                        }}
                      />
                    );
                  })}

                  {/* Labels on district map or focused provincial comparison */}
                  {(mapLevel === 'province' || (mapLevel === 'national' && projected.paths.length <= 10)) &&
                    projected.paths.map((p: any) => {
                      const item = metricsMap[p.code];
                      const c = item?.cases_C || 0;
                      const rateVal = item?.case_rate_per_100k;
                      return (
                        <g key={`lbl-${p.code}`} className="pointer-events-none">
                          <text
                            x={p.cx}
                            y={p.cy}
                            textAnchor="middle"
                            fontSize={11.5 / Math.sqrt(zoom)}
                            fontWeight="800"
                            fill="#000000"
                            stroke="#ffffff"
                            strokeWidth={2.8 / Math.sqrt(zoom)}
                            paintOrder="stroke"
                          >
                            {figLang === 'th' ? p.nameTh.replace(/\s*\(\d+\)$/, '') : p.nameEn}
                          </text>
                          {c > 0 && (
                            <text
                              x={p.cx}
                              y={p.cy + 12 / Math.sqrt(zoom)}
                              textAnchor="middle"
                              fontSize={10.5 / Math.sqrt(zoom)}
                              fontWeight="800"
                              fill="#1e3a8a"
                              stroke="#ffffff"
                              strokeWidth={2.4 / Math.sqrt(zoom)}
                              paintOrder="stroke"
                            >
                              {effectiveMetric === 'rate' && rateVal !== null && rateVal !== undefined
                                ? `${Number(rateVal).toFixed(1)}/แสน`
                                : effectiveMetric === 'ipd_pct'
                                ? `${Number(item?.hospitalization_prop || 0).toFixed(1)}%`
                                : `${c.toLocaleString()}`}
                            </text>
                          )}
                        </g>
                      );
                    })}
                </g>
              </svg>
            )}
          </div>

          {/* GraphPad Prism Quantitative Colorbar & Interval Legend Bar */}
          <div className="p-4 border-t-2 border-slate-900 bg-slate-50 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-extrabold text-slate-950 uppercase tracking-wide">
                {lang === 'th' ? 'แถบเทียบสเกลสี (Colorbar Scale): ' : 'Colorbar Scale: '}
                <span className="text-[#1d4ed8]">{metricLabel}</span>
              </span>
              <span className="text-[11px] font-mono font-bold text-slate-700">
                Min: 0 — Max: {effectiveMetric === 'cases' ? Math.round(maxVal).toLocaleString() : maxVal.toFixed(2)} {unitSuffix}
              </span>
            </div>

            {/* Continuous Prism Colorbar with Tick Marks */}
            <div className="space-y-1">
              <div className="h-4 w-full rounded-none overflow-hidden flex border-2 border-slate-900">
                {COLOR_RAMPS[colorScheme].map((col, i) => (
                  <div key={i} className="flex-1 h-full" style={{ backgroundColor: col }} />
                ))}
              </div>
              <div className="flex justify-between text-[11px] font-mono font-bold text-slate-900 pt-0.5">
                {[0, 0.25, 0.5, 0.75, 1.0].map((r, idx) => {
                  const v = Math.pow(r, 2) * maxVal;
                  return (
                    <span key={idx} className="flex flex-col items-center">
                      <span className="h-1.5 w-[2px] bg-slate-900 -mt-1.5 mb-0.5" />
                      <span>
                        {effectiveMetric === 'cases'
                          ? Math.round(v).toLocaleString()
                          : effectiveMetric === 'ipd_pct'
                          ? `${v.toFixed(1)}%`
                          : v.toFixed(1)}
                      </span>
                    </span>
                  );
                })}
              </div>
            </div>

            {/* Stepped Quantitative Class Swatches */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-1">
              {colorBins.map((bin, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-white border border-slate-900 text-[11px] font-mono font-bold text-slate-900"
                >
                  <span
                    className="w-4 h-4 rounded-none border border-slate-900 flex-shrink-0"
                    style={{ backgroundColor: bin.color }}
                  />
                  <span className="truncate">{bin.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right 5 Cols: Live Inspector Card + Top 5 Hotspots + Quick Drilldown */}
        <div className="lg:col-span-5 p-5 flex flex-col justify-between bg-white space-y-5">
          {/* Inspector Panel (Hovered or Active Summary) */}
          <div className="space-y-4">
            <div className="rounded-xl border-2 border-slate-900 bg-slate-50 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-extrabold uppercase tracking-wider text-slate-900 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5" />
                  {hoveredItem
                    ? lang === 'th'
                      ? 'ข้อมูลพื้นที่ที่ชี้เมาส์ (Hover Inspector)'
                      : 'Hovered Area Details'
                    : mapLevel === 'province' && activeProvinceInfo
                    ? lang === 'th'
                      ? 'สรุปภาพรวมจังหวัดที่กำลังแสดงรายอำเภอ'
                      : 'Active Province Summary'
                    : lang === 'th'
                    ? 'ชี้เมาส์หรือคลิกบนแผนที่เพื่อดูรายละเอียด'
                    : 'Hover or click a polygon on the map'}
                </span>
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-white border border-slate-900 text-slate-900">
                  {hoveredItem
                    ? `Code: ${hoveredItem.province_code || hoveredItem.district_code}`
                    : mapLevel === 'province'
                    ? `Prov: ${inspectProvince}`
                    : '77 Provinces'}
                </span>
              </div>

              {hoveredItem ? (
                <div className="space-y-3">
                  <div>
                    <div className="text-base font-extrabold text-slate-950">
                      {figLang === 'th'
                        ? hoveredItem.district_name_th || hoveredItem.province_name_th || hoveredPath?.nameTh
                        : hoveredItem.district_name_en || hoveredItem.province_name_en || hoveredPath?.nameEn}
                    </div>
                    {hoveredItem.district_code && (
                      <div className="text-xs font-semibold text-slate-600">
                        {lang === 'th' ? `จังหวัด${hoveredItem.province_name_th}` : `${hoveredItem.province_name_en} Province`}
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-3 gap-2">
                    <div className="bg-white p-2.5 rounded-lg border border-slate-900">
                      <div className="text-[10px] font-bold text-slate-600">{lang === 'th' ? 'ผู้ป่วยสะสม (C)' : 'Cases (C)'}</div>
                      <div className="text-sm font-extrabold text-slate-950 font-mono">
                        {(hoveredItem.cases_C || 0).toLocaleString()}
                      </div>
                    </div>
                    <div className="bg-white p-2.5 rounded-lg border border-slate-900">
                      <div className="text-[10px] font-bold text-slate-600">{lang === 'th' ? 'อุบัติการณ์/แสน' : 'Incidence/100k'}</div>
                      <div className="text-sm font-extrabold text-[#1d4ed8] font-mono">
                        {hoveredItem.case_rate_per_100k !== null && hoveredItem.case_rate_per_100k !== undefined
                          ? Number(hoveredItem.case_rate_per_100k).toFixed(2)
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="bg-white p-2.5 rounded-lg border border-slate-900">
                      <div className="text-[10px] font-bold text-slate-600">IPD %</div>
                      <div className="text-sm font-extrabold text-amber-800 font-mono">
                        {(hoveredItem.hospitalization_prop || 0).toFixed(1)}%
                      </div>
                    </div>
                  </div>

                  <div className="text-[11px] text-slate-700 flex items-center justify-between pt-1 border-t border-slate-300">
                    <span>
                      {lang === 'th' ? 'ประชากรตัวหาร:' : 'Denominator:'}{' '}
                      <strong className="font-mono">
                        {(hoveredItem.population || hoveredItem.district_population)
                          ? Number(hoveredItem.population || hoveredItem.district_population).toLocaleString()
                          : '-'}
                      </strong>
                      {hoveredItem.is_estimated_district_pop && (
                        <span className="ml-1 text-[10px] text-amber-800">
                          {lang === 'th' ? '(ประมาณการจากจังหวัด)' : '(Est.)'}
                        </span>
                      )}
                    </span>
                    <span>
                      IPD: <strong>{hoveredItem.ipd_H || 0}</strong> | OPD: <strong>{hoveredItem.opd_O || 0}</strong>
                    </span>
                  </div>
                </div>
              ) : mapLevel === 'province' && activeProvinceInfo ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-base font-extrabold text-slate-950">
                        {figLang === 'th' ? activeProvinceInfo.province_name_th : activeProvinceInfo.province_name_en}
                      </div>
                      <div className="text-xs font-medium text-slate-600">
                        {lang === 'th'
                          ? `แสดงแผนที่ครบทุกอำเภอ (${(choroplethData?.districts || []).length} อำเภอ/เขต)`
                          : `Showing all ${(choroplethData?.districts || []).length} districts`}
                      </div>
                    </div>
                    <button
                      onClick={() => onSelectProvince(inspectProvince)}
                      className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold transition flex items-center gap-1"
                    >
                      <Filter className="w-3.5 h-3.5" />
                      <span>{lang === 'th' ? 'กรองทั้งแดชบอร์ดเฉพาะจังหวัดนี้' : 'Filter Dashboard to Province'}</span>
                    </button>
                  </div>

                  <div className="grid grid-cols-3 gap-2">
                    <div className="bg-white p-2.5 rounded-lg border border-slate-900">
                      <div className="text-[10px] font-bold text-slate-600">{lang === 'th' ? 'ผู้ป่วยจังหวัด (C)' : 'Province Cases'}</div>
                      <div className="text-sm font-extrabold text-slate-950 font-mono">
                        {activeProvinceInfo.cases_C.toLocaleString()}
                      </div>
                    </div>
                    <div className="bg-white p-2.5 rounded-lg border border-slate-900">
                      <div className="text-[10px] font-bold text-slate-600">{lang === 'th' ? 'อุบัติการณ์จังหวัด' : 'Province Rate'}</div>
                      <div className="text-sm font-extrabold text-[#1d4ed8] font-mono">
                        {activeProvinceInfo.case_rate_per_100k !== null
                          ? `${activeProvinceInfo.case_rate_per_100k.toFixed(2)}`
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="bg-white p-2.5 rounded-lg border border-slate-900">
                      <div className="text-[10px] font-bold text-slate-600">{lang === 'th' ? 'ประชากรจังหวัด' : 'Population'}</div>
                      <div className="text-sm font-extrabold text-slate-900 font-mono">
                        {activeProvinceInfo.population ? activeProvinceInfo.population.toLocaleString() : 'N/A'}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-slate-600 py-2 font-medium">
                  {lang === 'th'
                    ? 'เลื่อนเมาส์ชี้ที่แต่ละจังหวัดหรืออำเภอบนแผนที่เพื่อดูจำนวนผู้ป่วย อุบัติการณ์ต่อแสนประชากร (Incidence) และสัดส่วนผู้ป่วยใน'
                    : 'Hover over any polygon to inspect cases, incidence rate per 100k, and IPD %.'}
                </div>
              )}
            </div>

            {/* Top 5 Ranking in Current Choropleth View */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h5 className="text-xs font-extrabold text-slate-900 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-[#1d4ed8]" />
                  <span>
                    {mapLevel === 'national'
                      ? lang === 'th'
                        ? '5 อันดับจังหวัดสูงสุดตามตัวชี้วัดที่เลือก'
                        : 'Top 5 Provinces by Selected Metric'
                      : lang === 'th'
                      ? '5 อันดับอำเภอสูงสุดในจังหวัดนี้'
                      : 'Top 5 Districts in Selected Province'}
                  </span>
                </h5>
                <span className="text-[10px] text-slate-600 font-mono font-bold">{unitSuffix}</span>
              </div>

              <div className="space-y-1.5">
                {topRanked.length === 0 ? (
                  <div className="text-xs text-slate-500 py-3 text-center bg-slate-50 rounded-xl border border-slate-300">
                    {lang === 'th' ? 'ไม่มีผู้ป่วยในขอบเขตที่เลือก' : 'No cases in selected scope'}
                  </div>
                ) : (
                  topRanked.map((item: any, idx: number) => {
                    const code = item.province_code && !item.district_code ? item.province_code : item.district_code;
                    const name =
                      figLang === 'th'
                        ? item.district_name_th || item.province_name_th
                        : item.district_name_en || item.province_name_en;
                    const v = getVal(item);
                    const pctWidth = Math.min(100, Math.max(6, (v / maxVal) * 100));

                    return (
                      <button
                        key={code}
                        onMouseEnter={() => setHoveredCode(code)}
                        onMouseLeave={() => setHoveredCode(null)}
                        onClick={() => {
                          if (mapLevel === 'national') {
                            setInspectProvince(code);
                            setMapLevel('province');
                          } else {
                            const nextDist = selectedDistrictCode === code ? null : code;
                            onSelectDistrict(nextDist, item.province_code);
                          }
                        }}
                        className="w-full p-2.5 rounded-lg border-2 border-slate-900 hover:bg-slate-50 bg-white transition text-left space-y-1 group"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <div className="font-bold text-slate-950 flex items-center gap-1.5 truncate">
                            <span className="w-5 h-5 rounded bg-slate-900 text-white font-mono text-[10px] flex items-center justify-center font-bold">
                              {idx + 1}
                            </span>
                            <span className="truncate">{name}</span>
                            <span className="text-[10px] font-mono text-slate-500">({code})</span>
                          </div>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <span className="font-mono font-extrabold text-[#1d4ed8]">
                              {effectiveMetric === 'rate'
                                ? `${v.toFixed(2)} /100k`
                                : effectiveMetric === 'ipd_pct'
                                ? `${v.toFixed(1)}%`
                                : `${v.toLocaleString()} ${lang === 'th' ? 'ราย' : ''}`}
                            </span>
                            <ArrowUpRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-950" />
                          </div>
                        </div>
                        <div className="w-full h-2 bg-slate-100 border border-slate-900 overflow-hidden">
                          <div
                            className="h-full transition-all"
                            style={{
                              width: `${pctWidth}%`,
                              backgroundColor: getColorForValue(v, maxVal, colorScheme),
                            }}
                          />
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* Denominator & Methodological Footnote */}
          {choroplethData?.denominator_note_th && (
            <div className="pt-3 border-t border-slate-200 text-[11px] text-slate-600">
              <p className="text-slate-800 font-semibold">
                {lang === 'th' ? choroplethData.denominator_note_th : choroplethData.denominator_note_en}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
