import React, { useEffect, useState, useRef, useMemo } from 'react';
import {
  ToggleLeft,
  ToggleRight,
  AlertTriangle,
  Upload,
  Presentation,
  CheckCircle2,
  Database,
  Info,
  Globe2,
  MapPin,
  BarChart3,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { getDistrictsSummary, getReferenceDistricts, uploadDistrictPopulation } from '../services/api';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { ReferenceDistrict } from '../types';
import { ChoroplethMap, MapLevel, MapMetric } from '../components/ChoroplethMap';

export const DistrictsPage: React.FC = () => {
  const { lang, figLang, setActiveTab, isLoaded, filters, updateFilters, filterVersion, measures } = useApp();
  const [districtData, setDistrictData] = useState<any[]>([]);
  const [refDistricts, setRefDistricts] = useState<ReferenceDistrict[]>([]);
  const [bangkokMissing, setBangkokMissing] = useState<boolean>(false);
  const [disclaimerTh, setDisclaimerTh] = useState<string>('');
  const [disclaimerEn, setDisclaimerEn] = useState<string>('');
  const [selectedDistrict, setSelectedDistrict] = useState<string | null>(null);
  const tidyInputRef = useRef<HTMLInputElement>(null);
  const [tidyMsg, setTidyMsg] = useState<string | null>(null);

  // Synchronized controls between Choropleth Map and Ranked Bar Chart
  const [placeLevel, setPlaceLevel] = useState<MapLevel>('national');
  const [placeMetric, setPlaceMetric] = useState<MapMetric>('rate');
  const [choroplethData, setChoroplethData] = useState<any | null>(null);
  const [currentInspectProvince, setCurrentInspectProvince] = useState<string>('65');

  const useIllness = filters.address_type === 'illness';
  const effProv = filters.province_code || measures?.effective_prov_code || null;

  const fetchDistricts = () => {
    getDistrictsSummary(useIllness)
      .then((res) => {
        setDistrictData(res.districts || []);
        setDisclaimerTh(res.disclaimer_th || '');
        setDisclaimerEn(res.disclaimer_en || '');
      })
      .catch(console.error);

    if (effProv && effProv !== 'Unknown') {
      getReferenceDistricts(effProv)
        .then((res) => {
          setRefDistricts(res.districts || []);
          setBangkokMissing(Boolean(res.bangkok_lookup_missing));
        })
        .catch(console.error);
    } else {
      setRefDistricts([]);
      setBangkokMissing(false);
    }
  };

  useEffect(() => {
    if (isLoaded) {
      fetchDistricts();
    }
  }, [isLoaded, useIllness, filterVersion, effProv]);

  const handleTidyUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const res = await uploadDistrictPopulation(file);
      setTidyMsg(res.message);
      fetchDistricts();
    } catch (err: any) {
      alert(err.message);
    }
  };

  // Ranked data source for GraphPad Prism horizontal bar chart
  const rankedBarData = useMemo(() => {
    if (placeLevel === 'national') {
      let provs = choroplethData?.provinces || [];
      const selProvs = (filters.province_codes || []).filter((p: string) => p && p !== '00' && p !== 'all');
      if (selProvs.length > 0 && filters.scope_mode === 'provinces') {
        provs = provs.filter((p: any) => selProvs.includes(p.province_code));
      }
      const sorted = [...provs].sort((a: any, b: any) => {
        if (placeMetric === 'rate') return (b.case_rate_per_100k ?? -1) - (a.case_rate_per_100k ?? -1);
        if (placeMetric === 'ipd_pct') return (b.hospitalization_prop ?? -1) - (a.hospitalization_prop ?? -1);
        return (b.cases_C ?? 0) - (a.cases_C ?? 0);
      });
      return sorted.slice(0, 15).map((p: any) => ({
        code: p.province_code,
        name_th: p.province_name_th,
        name_en: p.province_name_en,
        cases_C: p.cases_C,
        ipd_H: p.ipd_H,
        opd_O: p.opd_O,
        unknown_U: p.unknown_U,
        hospitalization_prop: p.hospitalization_prop,
        case_rate_per_100k: p.case_rate_per_100k,
        val:
          placeMetric === 'rate'
            ? p.case_rate_per_100k ?? 0
            : placeMetric === 'ipd_pct'
            ? p.hospitalization_prop ?? 0
            : p.cases_C ?? 0,
      }));
    } else {
      const dists =
        choroplethData?.districts && choroplethData.districts.length > 0
          ? choroplethData.districts
          : districtData;
      const sorted = [...dists].sort((a: any, b: any) => {
        if (placeMetric === 'rate') return (b.case_rate_per_100k ?? -1) - (a.case_rate_per_100k ?? -1);
        if (placeMetric === 'ipd_pct') return (b.hospitalization_prop ?? -1) - (a.hospitalization_prop ?? -1);
        return (b.cases_C ?? 0) - (a.cases_C ?? 0);
      });
      return sorted.slice(0, 15).map((d: any) => ({
        code: d.district_code,
        name_th: d.district_name_th,
        name_en: d.district_name_en,
        province_name_th: d.province_name_th,
        province_name_en: d.province_name_en,
        cases_C: d.cases_C,
        ipd_H: d.ipd_H,
        opd_O: d.opd_O,
        unknown_U: d.unknown_U,
        hospitalization_prop: d.hospitalization_prop,
        case_rate_per_100k: d.case_rate_per_100k,
        val:
          placeMetric === 'rate'
            ? d.case_rate_per_100k ?? 0
            : placeMetric === 'ipd_pct'
            ? d.hospitalization_prop ?? 0
            : d.cases_C ?? 0,
      }));
    }
  }, [placeLevel, placeMetric, choroplethData, districtData, filters.province_codes, filters.scope_mode]);

  const metricTitle =
    placeMetric === 'rate'
      ? figLang === 'th'
        ? 'อุบัติการณ์ต่อแสนประชากร (Incidence / 100,000)'
        : 'Incidence Rate per 100,000'
      : placeMetric === 'ipd_pct'
      ? figLang === 'th'
        ? 'สัดส่วนผู้ป่วยใน (IPD %)'
        : 'Hospitalization Proportion (IPD %)'
      : figLang === 'th'
      ? 'จำนวนผู้ป่วยสะสม (ราย / Cases)'
      : 'Reported Cases (n)';

  const metricUnit =
    placeMetric === 'rate'
      ? figLang === 'th'
        ? 'ต่อแสน'
        : '/ 100k'
      : placeMetric === 'ipd_pct'
      ? '%'
      : figLang === 'th'
      ? 'ราย'
      : 'cases';

  return (
    <div className="space-y-6">
      {/* Geography Mode Control Bar */}
      <div className="bg-white rounded-2xl border-2 border-slate-900 p-5 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h3 className="font-extrabold text-slate-950 text-base">
              {lang === 'th' ? 'การกระจายทางภูมิศาสตร์' : 'Geographic Distribution'}
            </h3>
            <span className="text-xs px-2.5 py-0.5 rounded border border-slate-900 bg-slate-100 text-slate-900 font-mono font-bold">
              {placeLevel === 'national' ? '77 Provinces' : 'Districts Scope'}
            </span>
          </div>
          <p className="text-xs text-slate-600 font-medium mt-1">
            {useIllness
              ? lang === 'th'
                ? 'มุมมอง: อำเภอขณะป่วย (Illness Location)'
                : 'View: Illness Location District'
              : lang === 'th'
              ? 'มุมมอง: อำเภอที่อยู่ปัจจุบัน (Current Residence)'
              : 'View: Current Residence District'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() =>
              updateFilters({
                address_type: useIllness ? 'residence' : 'illness',
                district_code: null,
              })
            }
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border-2 text-xs font-bold transition ${
              useIllness
                ? 'bg-amber-50 border-amber-500 text-amber-950'
                : 'bg-slate-100 border-slate-900 text-slate-900'
            }`}
          >
            {useIllness ? (
              <ToggleRight className="w-5 h-5 text-amber-700" />
            ) : (
              <ToggleLeft className="w-5 h-5 text-slate-900" />
            )}
            <span>
              {useIllness
                ? lang === 'th'
                  ? 'กำลังแสดง: อำเภอขณะป่วย'
                  : 'Showing: Illness Address'
                : lang === 'th'
                ? 'กำลังแสดง: ที่อยู่ปัจจุบัน'
                : 'Showing: Residence'}
            </span>
          </button>

          <button
            onClick={() => tidyInputRef.current?.click()}
            className="px-3 py-1.5 rounded-lg border-2 border-slate-900 hover:bg-slate-100 text-slate-900 text-xs font-bold transition flex items-center gap-1.5"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>{lang === 'th' ? 'นำเข้าประชากรรายอำเภอ (CSV)' : 'Tidy District Pop'}</span>
          </button>
          <input ref={tidyInputRef} type="file" accept=".csv" onChange={handleTidyUpload} className="hidden" />

          <button
            onClick={() => setActiveTab('studio')}
            className="px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold transition flex items-center gap-1.5 shadow-xs"
          >
            <Presentation className="w-3.5 h-3.5" />
            <span>{lang === 'th' ? 'สไลด์ 4K' : '4K Slide'}</span>
          </button>
        </div>
      </div>

      {/* Disclaimers & Alert Banners */}
      <div className="space-y-2">
        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-300 text-slate-800 text-xs flex items-start gap-2.5 font-medium">
          <Info className="w-4 h-4 text-slate-900 flex-shrink-0 mt-0.5" />
          <p>{lang === 'th' ? disclaimerTh : disclaimerEn}</p>
        </div>

        {bangkokMissing && (
          <div className="p-3.5 rounded-xl bg-amber-50 border-2 border-amber-400 text-amber-950 text-xs flex items-center gap-2.5 font-semibold">
            <AlertTriangle className="w-4 h-4 text-amber-700 flex-shrink-0" />
            <p>
              {lang === 'th'
                ? 'หมายเหตุกรุงเทพมหานคร (รหัสจังหวัด 10): ฐานข้อมูล dds_reference.sqlite ไม่มีตารางรหัสเขตของกรุงเทพมหานคร ระบบจึงแสดงสถานะ explicitly missing lookup โดยไม่เดาชื่อเขตเอง'
                : 'Bangkok (Province 10) Notice: dds_reference.sqlite does not contain Bangkok district lookup rows; records are explicitly flagged rather than guessed.'}
            </p>
          </div>
        )}

        {tidyMsg && (
          <div className="p-3 rounded-lg bg-teal-50 border-2 border-teal-600 text-teal-950 text-xs flex items-center gap-2 font-bold">
            <CheckCircle2 className="w-4 h-4 text-teal-700" />
            <span>{tidyMsg}</span>
          </div>
        )}
      </div>

      {/* Interactive Choropleth Map with Quantitative Colorbar */}
      <ChoroplethMap
        lang={lang}
        figLang={figLang}
        useIllness={useIllness}
        filterVersion={filterVersion}
        selectedProvinceCodes={filters.province_codes || []}
        selectedDistrictCode={filters.district_code || null}
        controlledLevel={placeLevel}
        onLevelChange={setPlaceLevel}
        controlledMetric={placeMetric}
        onMetricChange={setPlaceMetric}
        onChoroplethLoaded={(data, inspectProv) => {
          setChoroplethData(data);
          setCurrentInspectProvince(inspectProv);
        }}
        onSelectProvince={(provCode) => {
          updateFilters({
            scope_mode: 'provinces',
            province_code: provCode,
            province_codes: [provCode],
            district_code: null,
          });
        }}
        onUpdateProvinces={(codes) => {
          if (!codes || codes.length === 0) {
            updateFilters({
              scope_mode: 'national',
              province_code: null,
              province_codes: [],
              district_code: null,
            });
          } else {
            updateFilters({
              scope_mode: 'provinces',
              province_code: codes[0],
              province_codes: codes,
              district_code: null,
            });
          }
        }}
        onSelectDistrict={(distCode, provCode) => {
          setSelectedDistrict(distCode);
          if (distCode && distCode.length === 4 && /^\d{4}$/.test(distCode)) {
            updateFilters({
              scope_mode: 'district',
              province_code: provCode || distCode.slice(0, 2),
              province_codes: [provCode || distCode.slice(0, 2)],
              district_code: distCode,
            });
          } else {
            updateFilters({ district_code: null });
          }
        }}
      />

      {/* Visual Section: GraphPad Prism Styled Ranked Bar Chart & Reference SQLite District Directory */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Ranked Horizontal Bar Chart in Authentic GraphPad Prism Theme */}
        <div className="bg-white rounded-2xl border-2 border-slate-900 p-6 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b-2 border-slate-900 pb-3">
            <div>
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-slate-900" />
                <h4 className="font-extrabold text-slate-950 text-sm">
                  {figLang === 'th'
                    ? `แผนภูมิแท่งจัดอันดับสูงสุด 15 อันดับ (${placeLevel === 'national' ? 'ระดับจังหวัด' : 'ระดับอำเภอ'})`
                    : `Ranked Top 15 Bar Chart (${placeLevel === 'national' ? 'Province Level' : 'District Level'})`}
                </h4>
              </div>
              <p className="text-xs text-slate-600 font-semibold mt-0.5">
                {metricTitle} • {placeLevel === 'national' ? (lang === 'th' ? 'จัดอันดับรายจังหวัด' : 'Ranked Provinces') : (lang === 'th' ? 'จัดอันดับรายอำเภอ' : 'Ranked Districts')}
              </p>
            </div>

            {/* Quick Level & Metric Controls for Bar Graph */}
            <div className="flex items-center gap-1.5 self-start sm:self-auto">
              <button
                onClick={() => setPlaceLevel(placeLevel === 'national' ? 'province' : 'national')}
                className="px-2.5 py-1 rounded border border-slate-900 bg-slate-100 hover:bg-slate-200 text-slate-900 text-[11px] font-bold flex items-center gap-1"
              >
                {placeLevel === 'national' ? <MapPin className="w-3 h-3" /> : <Globe2 className="w-3 h-3" />}
                <span>{placeLevel === 'national' ? (lang === 'th' ? 'สลับดูอำเภอ' : 'Switch District') : (lang === 'th' ? 'สลับดูจังหวัด' : 'Switch Province')}</span>
              </button>
              <button
                onClick={() => setPlaceMetric(placeMetric === 'rate' ? 'cases' : placeMetric === 'cases' ? 'ipd_pct' : 'rate')}
                className="px-2.5 py-1 rounded border border-slate-900 bg-slate-900 text-white text-[11px] font-bold"
              >
                {placeMetric === 'rate' ? 'Incidence' : placeMetric === 'cases' ? 'Cases' : 'IPD %'}
              </button>
            </div>
          </div>

          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={rankedBarData}
                margin={{ top: 10, right: 30, left: 40, bottom: 15 }}
              >
                {/* GraphPad Prism style: open top & right axes, thick black L-axes, outward tick styling */}
                <CartesianGrid strokeDasharray="0" stroke="#f1f5f9" horizontal={false} />
                <XAxis
                  type="number"
                  stroke="#000000"
                  strokeWidth={2}
                  tick={{ fontSize: 11, fill: '#000000', fontWeight: 700 }}
                  tickLine={{ stroke: '#000000', strokeWidth: 1.5 }}
                />
                <YAxis
                  dataKey={figLang === 'th' ? 'name_th' : 'name_en'}
                  type="category"
                  stroke="#000000"
                  strokeWidth={2}
                  tick={{ fontSize: 11, fill: '#000000', fontWeight: 700 }}
                  tickLine={{ stroke: '#000000', strokeWidth: 1.5 }}
                  width={110}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-white p-3 rounded-lg border-2 border-slate-900 shadow-lg text-xs space-y-1">
                          <p className="font-extrabold text-slate-950">
                            {figLang === 'th' ? data.name_th : data.name_en} ({data.code})
                          </p>
                          <p className="text-[#1d4ed8] font-bold">
                            {metricTitle}: {Number(data.val).toLocaleString()} {metricUnit}
                          </p>
                          <p className="text-slate-800 font-medium">
                            {figLang === 'th' ? 'ผู้ป่วยรวม (C):' : 'Cases (C):'} {Number(data.cases_C || 0).toLocaleString()}
                          </p>
                          <p className="text-slate-700">
                            IPD: {Number(data.ipd_H || 0).toLocaleString()} ({data.hospitalization_prop}%) | OPD: {Number(data.opd_O || 0).toLocaleString()}
                          </p>
                          {data.case_rate_per_100k !== null && data.case_rate_per_100k !== undefined && (
                            <p className="text-slate-600 font-mono">
                              Rate: {Number(data.case_rate_per_100k).toFixed(2)} / 100k
                            </p>
                          )}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar
                  dataKey="val"
                  fill="#2563eb"
                  stroke="#000000"
                  strokeWidth={1.5}
                  radius={0}
                  name={metricTitle}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Dynamic Reference District Directory Card */}
        <div className="bg-white rounded-2xl border-2 border-slate-900 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3 border-b-2 border-slate-900 pb-3">
              <div>
                <h4 className="font-extrabold text-slate-950 text-sm flex items-center gap-1.5">
                  <Database className="w-4 h-4 text-slate-900" />
                  <span>
                    {lang === 'th'
                      ? 'สารบบรหัสอำเภออ้างอิงจาก dds_reference.sqlite'
                      : 'Reference District Code Directory (dds_reference.sqlite)'}
                  </span>
                </h4>
                <p className="text-xs text-slate-600 font-medium">
                  {lang === 'th'
                    ? 'คลิกเลือกอำเภอเพื่อกรองข้อมูลตามรหัส 4 หลัก'
                    : 'Click a district to filter by 4-digit code'}
                </p>
              </div>
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded border border-slate-900 bg-slate-100 text-slate-900">
                {refDistricts.length > 0 ? `${refDistricts.length} Ref Districts` : `${districtData.length} Active`}
              </span>
            </div>

            <div className="bg-slate-50 border border-slate-300 rounded-xl p-3 max-h-[265px] overflow-y-auto grid grid-cols-1 sm:grid-cols-2 gap-2">
              {districtData.map((d) => {
                const isSel = selectedDistrict === d.district_code || filters.district_code === d.district_code;
                return (
                  <button
                    key={d.district_code}
                    onClick={() => {
                      const next = isSel ? null : d.district_code;
                      setSelectedDistrict(next);
                      if (next && next.length === 4 && /^\d{4}$/.test(next)) {
                        updateFilters({ district_code: next });
                      } else {
                        updateFilters({ district_code: null });
                      }
                    }}
                    className={`p-2.5 rounded-lg border-2 text-left transition flex items-center justify-between ${
                      isSel
                        ? 'bg-slate-900 text-white border-slate-900 shadow-xs'
                        : 'bg-white hover:bg-slate-100 border-slate-300 text-slate-900'
                    }`}
                  >
                    <div className="min-w-0 pr-2">
                      <div className="text-xs font-bold truncate">
                        {lang === 'th' ? d.district_name_th : d.district_name_en}
                      </div>
                      <div className={`text-[10px] font-mono ${isSel ? 'text-slate-300' : 'text-slate-500'}`}>
                        Code: {d.district_code} | IPD: {d.hospitalization_prop}%
                      </div>
                    </div>
                    <span
                      className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                        isSel ? 'bg-slate-800 text-white border border-slate-700' : 'bg-slate-100 text-slate-900 border border-slate-300'
                      }`}
                    >
                      {d.cases_C.toLocaleString()}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-200 flex items-center justify-between text-xs text-slate-600 font-medium">
            <span>
              {filters.district_code
                ? lang === 'th'
                  ? `กำลังกรองรหัสอำเภอ: ${filters.district_code}`
                  : `Filtered to district code: ${filters.district_code}`
                : lang === 'th'
                ? 'คลิกที่รายการอำเภอเพื่อกรองหรือไฮไลต์'
                : 'Click a district card to filter scope'}
            </span>
            {filters.district_code && (
              <button
                onClick={() => {
                  setSelectedDistrict(null);
                  updateFilters({ district_code: null });
                }}
                className="text-[#1d4ed8] hover:underline font-bold"
              >
                {lang === 'th' ? 'แสดงทุกอำเภอ' : 'Show All Districts'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* District Detail Summary Table */}
      <div className="bg-white rounded-2xl border-2 border-slate-900 p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="font-extrabold text-slate-950 text-sm">
            {lang === 'th'
              ? 'ตารางสรุปข้อมูลรายอำเภอ (District Surveillance Summary)'
              : 'District Summary Data Table'}
          </h4>
          <span className="text-xs text-slate-600 font-medium">
            {lang === 'th'
              ? 'รหัส 4 หลักจาก dds_reference.sqlite (ไม่รวมแถวหัวข้อ XX00)'
              : 'Validated 4-digit codes from dds_reference.sqlite (excluding XX00 headings)'}
          </span>
        </div>

        <div className="overflow-x-auto border-2 border-slate-900 rounded-xl">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-100 border-b-2 border-slate-900 text-slate-900 font-bold">
              <tr>
                <th className="py-2.5 px-3">{lang === 'th' ? 'รหัสอำเภอ' : 'Code'}</th>
                <th className="py-2.5 px-3">{lang === 'th' ? 'ชื่ออำเภอ (ไทย)' : 'District Name (TH)'}</th>
                <th className="py-2.5 px-3">{lang === 'th' ? 'จังหวัด' : 'Province'}</th>
                <th className="py-2.5 px-3 text-right">{lang === 'th' ? 'ผู้ป่วย C (ราย)' : 'Cases C'}</th>
                <th className="py-2.5 px-3 text-right">IPD (H)</th>
                <th className="py-2.5 px-3 text-right">OPD (O)</th>
                <th className="py-2.5 px-3 text-right">{lang === 'th' ? 'ไม่ระบุ (U)' : 'Unknown'}</th>
                <th className="py-2.5 px-3 text-right">{lang === 'th' ? 'สัดส่วน IPD (%)' : 'Hospitalization %'}</th>
                <th className="py-2.5 px-3 text-right">{lang === 'th' ? 'ความสมบูรณ์ (%)' : 'Completeness %'}</th>
                <th className="py-2.5 px-3 text-right">{lang === 'th' ? 'อัตราป่วย/แสน' : 'Rate / 100k'}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 font-mono font-medium">
              {districtData.map((d) => (
                <tr
                  key={d.district_code}
                  className={`hover:bg-slate-50 ${
                    selectedDistrict === d.district_code || filters.district_code === d.district_code
                      ? 'bg-blue-50 font-bold text-slate-950'
                      : ''
                  }`}
                >
                  <td className="py-2.5 px-3 text-slate-600">{d.district_code}</td>
                  <td className="py-2.5 px-3 font-sans font-bold text-slate-950">{d.district_name_th}</td>
                  <td className="py-2.5 px-3 font-sans text-slate-700">
                    {lang === 'th' ? d.province_name_th || '-' : d.province_name_en || '-'}
                  </td>
                  <td className="py-2.5 px-3 text-right font-extrabold text-slate-950">{d.cases_C.toLocaleString()}</td>
                  <td className="py-2.5 px-3 text-right text-teal-800 font-bold">{d.ipd_H.toLocaleString()}</td>
                  <td className="py-2.5 px-3 text-right text-blue-800 font-bold">{d.opd_O.toLocaleString()}</td>
                  <td className="py-2.5 px-3 text-right text-slate-500">{d.unknown_U.toLocaleString()}</td>
                  <td className="py-2.5 px-3 text-right font-bold text-slate-900">{d.hospitalization_prop}%</td>
                  <td className="py-2.5 px-3 text-right text-slate-700">{d.patient_type_completeness}%</td>
                  <td className="py-2.5 px-3 text-right">
                    {d.case_rate_per_100k !== null ? (
                      <span className="text-[#1d4ed8] font-extrabold">{d.case_rate_per_100k}</span>
                    ) : (
                      <span
                        className="text-slate-400 font-sans italic text-[11px]"
                        title={lang === 'th' ? d.rate_status_note : d.rate_status_note_en || d.rate_status_note}
                      >
                        Unavailable
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
