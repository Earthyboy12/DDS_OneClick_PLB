import React, { useEffect, useState } from 'react';
import {
  Activity,
  Hospital,
  UserCheck,
  TrendingUp,
  MapPin,
  ArrowRight,
  GitCompare,
  Calendar,
  Info,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { getTimeEpicurve, getDistrictsSummary } from '../services/api';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

export const OverviewPage: React.FC = () => {
  const { lang, figLang, measures, isLoaded, setActiveTab, loadSynthetic, filterVersion, filters } = useApp();
  const [weeklyData, setWeeklyData] = useState<any[]>([]);
  const [districtData, setDistrictData] = useState<any[]>([]);

  useEffect(() => {
    if (isLoaded) {
      getTimeEpicurve()
        .then((res) => {
          setWeeklyData(res.weeks.slice(-16));
        })
        .catch(console.error);

      getDistrictsSummary(filters.address_type === 'illness')
        .then((res) => {
          setDistrictData(res.districts.slice(0, 10));
        })
        .catch(console.error);
    }
  }, [isLoaded, filterVersion, filters.address_type]);

  if (!isLoaded || !measures) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center max-w-xl mx-auto shadow-xs">
        <div className="w-16 h-16 rounded-2xl bg-teal-50 text-teal-600 flex items-center justify-center mx-auto mb-4">
          <Activity className="w-8 h-8" />
        </div>
        <h3 className="text-lg font-bold text-slate-800 mb-2">
          {lang === 'th' ? 'ยังไม่ได้โหลดชุดข้อมูลเฝ้าระวังโรค' : 'No Surveillance Dataset Loaded'}
        </h3>
        <p className="text-xs text-slate-500 mb-6 leading-relaxed">
          {lang === 'th'
            ? 'กรุณานำเข้าไฟล์ Excel / CSV หรือคลิกปุ่มด้านล่างเพื่อโหลดชุดข้อมูลสังเคราะห์ 20,172 รายการเพื่อเริ่มต้นใช้งาน'
            : 'Please import DDS files (.xlsx / .csv) or click below to generate synthetic reference data for demonstration.'}
        </p>
        <button
          onClick={loadSynthetic}
          className="px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-medium text-sm transition shadow-sm"
        >
          {lang === 'th' ? 'โหลดชุดข้อมูลสังเคราะห์เพื่อทดสอบ' : 'Load Synthetic Dataset'}
        </button>
      </div>
    );
  }

  const m = measures;
  const denom = m.denominator_info;
  const comp = m.comparator;

  const rateTooltipText =
    denom?.available && m.compatible_population !== null
      ? lang === 'th'
        ? `ตัวตั้ง (Numerator C): ${m.cases_C.toLocaleString()} ราย\nตัวหารประชากร (Denominator P): ${m.compatible_population.toLocaleString()} คน\nปีประชากรอ้างอิง: พ.ศ. ${m.population_year_be ?? '-'} (ค.ศ. ${m.population_year_ce ?? '-'})${m.is_fallback_year ? ' [ใช้ปี 2568 ล่าสุดแทน]' : ''}\nขอบเขตพื้นที่: ${m.scope_name_th}`
        : `Numerator (C): ${m.cases_C.toLocaleString()} cases\nDenominator (P): ${m.compatible_population.toLocaleString()} pop\nPopulation Year: ${m.population_year_ce ?? '-'} (BE ${m.population_year_be ?? '-'})${m.is_fallback_year ? ' [Fallback to 2568]' : ''}\nGeography Scope: ${m.scope_name_en}`
      : lang === 'th'
      ? `งดคำนวณอัตราต่อประชากร: ${denom?.reason_th || '-'}\nขอบเขตพื้นที่: ${m.scope_name_th}`
      : `Rate unavailable: ${denom?.reason_en || '-'}\nGeography Scope: ${m.scope_name_en}`;

  return (
    <div className="space-y-6">
      {/* Top Population & Geographical Universe Disclosure */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-3 rounded-xl bg-navy-50 text-navy-800">
            <MapPin className="w-6 h-6 text-navy-700" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-bold text-slate-900 text-base">
                {lang === 'th' ? m.scope_name_th || m.province_name_th : m.scope_name_en || m.province_name_en}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-navy-100 text-navy-800 font-semibold font-mono">
                Scope: {m.scope_mode}
              </span>
              {m.selected_province_codes && m.selected_province_codes.length > 0 && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-teal-100 text-teal-800 font-semibold font-mono">
                  Prov [{m.selected_province_codes.join(', ')}]
                </span>
              )}
              {m.effective_district_code && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 font-semibold font-mono">
                  Dist {m.effective_district_code}
                </span>
              )}
              {m.population_year_be && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-semibold font-mono">
                  Pop พ.ศ. {m.population_year_be} ({m.population_year_ce})
                  {m.is_fallback_year ? (lang === 'th' ? ' • ใช้ปี 2568 ล่าสุดแทน' : ' • Fallback 2568') : ''}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-600 mt-1">
              {denom?.available && m.compatible_population !== null
                ? lang === 'th'
                  ? `ตัวตั้งผู้ป่วย C = ${m.cases_C.toLocaleString()} ราย ÷ ตัวหารประชากร P = ${m.compatible_population.toLocaleString()} คน (ปีประชากร พ.ศ. ${m.population_year_be}${m.is_fallback_year ? ' ใช้ปี 2568 ล่าสุดแทนปีที่ไม่มีในฐานข้อมูล' : ''}) × 100,000`
                  : `Numerator C = ${m.cases_C.toLocaleString()} cases ÷ Denominator P = ${m.compatible_population.toLocaleString()} pop (Pop Year ${m.population_year_ce} / BE ${m.population_year_be}${m.is_fallback_year ? ' fallback' : ''}) × 100,000`
                : lang === 'th'
                ? `งดคำนวณอัตราต่อประชากรในมุมมองรวม: ${denom?.reason_th || 'ไม่มีตัวหารประชากรที่ตรงกับขอบเขตที่เลือก'}`
                : `Combined population rate unavailable: ${denom?.reason_en || 'No matching population denominator for selected scope'}`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('studio')}
            className="px-3.5 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-medium shadow-xs transition flex items-center gap-1.5"
          >
            <span>{lang === 'th' ? 'เปิด Presentation Studio' : 'Open Presentation Studio'}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Optional Comparator Province Card */}
      {comp && (
        <div className="bg-teal-50/70 rounded-2xl border border-teal-200 p-4 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-2.5">
            <GitCompare className="w-5 h-5 text-teal-700 flex-shrink-0" />
            <div>
              <span className="font-bold text-teal-950">
                {lang === 'th'
                  ? `จังหวัดเปรียบเทียบที่เลือก: จังหวัด${comp.province_name_th} (รหัส ${comp.province_code})`
                  : `Selected Comparator: ${comp.province_name_en} (Code ${comp.province_code})`}
              </span>
              <p className="text-teal-800 mt-0.5">
                {comp.denominator_info?.available
                  ? lang === 'th'
                    ? `ประชากรอ้างอิง: ${comp.denominator_info.population?.toLocaleString()} คน | ผู้ป่วยในชุดข้อมูล: ${comp.measures.cases_C.toLocaleString()} ราย | อัตราป่วย: ${comp.measures.case_notification_rate ?? '-'} ต่อแสน | สัดส่วน IPD: ${comp.measures.hospitalization_prop}%`
                    : `Ref Pop: ${comp.denominator_info.population?.toLocaleString()} | Cases in dataset: ${comp.measures.cases_C.toLocaleString()} | Rate/100k: ${comp.measures.case_notification_rate ?? '-'} | IPD: ${comp.measures.hospitalization_prop}%`
                  : lang === 'th'
                  ? `ผู้ป่วยในชุดข้อมูล: ${comp.measures.cases_C.toLocaleString()} ราย | งดคำนวณอัตราต่อประชากร (${comp.denominator_info?.reason_th})`
                  : `Cases in dataset: ${comp.measures.cases_C.toLocaleString()} | Rate unavailable (${comp.denominator_info?.reason_en})`}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 4 Core Surveillance Measures Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div
          className="bg-white rounded-2xl border border-slate-200 border-t-4 border-t-teal-600 p-6 shadow-xs relative overflow-hidden"
          title={`Numerator C = ${m.cases_C.toLocaleString()} (IPD H = ${m.ipd_H.toLocaleString()}, OPD O = ${m.opd_O.toLocaleString()}, Unknown U = ${m.unknown_U.toLocaleString()}) | Scope: ${m.scope_name_th}`}
        >
          <div className="flex items-center justify-between text-slate-600 text-xs font-bold mb-2">
            <span>{lang === 'th' ? 'ผู้ป่วยเข้าเกณฑ์ในขอบเขต (C)' : 'Eligible Episodes in Scope (C)'}</span>
            <Activity className="w-5 h-5 text-teal-600" />
          </div>
          <div className="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
            {m.cases_C.toLocaleString()}
          </div>
          <div className="text-xs text-slate-600 mt-3 flex items-center justify-between pt-2.5 border-t border-slate-100 font-medium">
            <span>IPD: <strong>{m.ipd_H.toLocaleString()}</strong></span>
            <span>OPD: <strong>{m.opd_O.toLocaleString()}</strong></span>
            <span className="text-slate-400">Unk: {m.unknown_U.toLocaleString()}</span>
          </div>
        </div>

        <div
          className="bg-white rounded-2xl border border-slate-200 border-t-4 border-t-emerald-600 p-6 shadow-xs relative overflow-hidden"
          title={`IPD (H) = ${m.ipd_H.toLocaleString()} / Known Patient Type (H+O) = ${(m.ipd_H + m.opd_O).toLocaleString()} × 100`}
        >
          <div className="flex items-center justify-between text-slate-600 text-xs font-bold mb-2">
            <span>{lang === 'th' ? 'สัดส่วนนอน รพ. [H / (H + O)]' : 'Hospitalization Proportion'}</span>
            <Hospital className="w-5 h-5 text-emerald-600" />
          </div>
          <div className="text-3xl font-extrabold text-teal-700 font-mono tracking-tight">
            {m.hospitalization_prop.toFixed(1)}%
          </div>
          <div className="text-xs text-slate-600 mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between">
            <span>95% Wilson CI:</span>
            <span className="font-mono font-bold text-slate-800">
              [{m.hospitalization_prop_ci[0].toFixed(1)}%, {m.hospitalization_prop_ci[1].toFixed(1)}%]
            </span>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 border-t-4 border-t-blue-600 p-6 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-600 text-xs font-bold mb-2">
            <span>{lang === 'th' ? 'ความสมบูรณ์ประเภทผู้ป่วย' : 'Patient-Type Completeness'}</span>
            <UserCheck className="w-5 h-5 text-blue-600" />
          </div>
          <div className="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
            {m.patient_type_completeness.toFixed(1)}%
          </div>
          <div className="text-xs text-amber-800 mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between font-medium">
            <span>{lang === 'th' ? 'ไม่ระบุประเภท (Unknown):' : 'Missing Type:'}</span>
            <span className="font-mono font-bold">
              {(100 - m.patient_type_completeness).toFixed(1)}%
            </span>
          </div>
        </div>

        <div
          className="bg-white rounded-2xl border border-slate-200 border-t-4 border-t-navy-700 p-6 shadow-xs relative overflow-hidden cursor-help"
          title={rateTooltipText}
        >
          <div className="flex items-center justify-between text-slate-600 text-xs font-bold mb-2">
            <span className="flex items-center gap-1.5">
              {lang === 'th' ? 'อัตราป่วยต่อแสนประชากร' : 'Notification Rate / 100k'}
              <Info className="w-4 h-4 text-slate-400" />
            </span>
            <TrendingUp className="w-5 h-5 text-navy-700" />
          </div>
          <div className="text-3xl font-extrabold text-slate-900 font-mono tracking-tight">
            {m.case_notification_rate !== null && m.case_notification_rate !== undefined
              ? m.case_notification_rate.toLocaleString()
              : 'Unavailable'}
          </div>
          <div className="text-xs text-slate-600 mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between">
            <span>
              {m.compatible_population !== null
                ? `C=${m.cases_C.toLocaleString()} / P=${m.compatible_population.toLocaleString()}`
                : '95% Poisson CI:'}
            </span>
            <span className="font-mono font-bold text-slate-800">
              {m.case_notification_rate_ci
                ? `[${m.case_notification_rate_ci[0]}, ${m.case_notification_rate_ci[1]}]`
                : '-'}
            </span>
          </div>
        </div>
      </div>

      {/* Multi-Year Per-Year Rate Breakdown Table (shown when multiple years are selected/in scope) */}
      {m.rates_by_year && m.rates_by_year.length > 1 && (
        <div className="bg-white rounded-2xl border border-teal-200 p-5 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-teal-600" />
              <h4 className="font-bold text-slate-800 text-sm">
                {lang === 'th'
                  ? 'อัตราป่วยและอัตราการนอนโรงพยาบาลจำแนกรายปี (Per-Year Population Rates Breakdown)'
                  : 'Per-Year Population-Based Rates Breakdown'}
              </h4>
            </div>
            <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-teal-50 text-teal-800 border border-teal-200 font-medium">
              {lang === 'th'
                ? 'แยกคำนวณรายปี ไม่นำผู้ป่วยหลายปีมารวมหารด้วยประชากรปีเดียว'
                : 'Calculated per year; never pools multi-year cases over a single-year denominator'}
            </span>
          </div>

          <div className="overflow-x-auto border border-slate-200 rounded-xl">
            <table className="w-full text-xs text-left font-mono">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                <tr>
                  <th className="py-2 px-3 font-semibold">{lang === 'th' ? 'ปีที่ป่วย' : 'Year'}</th>
                  <th className="py-2 px-3 font-semibold">{lang === 'th' ? 'ปีประชากรที่ใช้หาร' : 'Pop Year Used'}</th>
                  <th className="py-2 px-3 font-semibold">{lang === 'th' ? 'ขอบเขตพื้นที่' : 'Geography Scope'}</th>
                  <th className="py-2 px-3 font-semibold text-right">{lang === 'th' ? 'ตัวตั้ง C (ราย)' : 'Numerator C'}</th>
                  <th className="py-2 px-3 font-semibold text-right">{lang === 'th' ? 'ตัวหารประชากร P' : 'Denominator P'}</th>
                  <th className="py-2 px-3 font-semibold text-right">{lang === 'th' ? 'อัตราป่วย/แสน' : 'Rate / 100k'}</th>
                  <th className="py-2 px-3 font-semibold text-center">95% Poisson CI</th>
                  <th className="py-2 px-3 font-semibold text-right">{lang === 'th' ? 'อัตรา IPD/แสน' : 'IPD Rate / 100k'}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {m.rates_by_year.map((ry) => (
                  <tr key={ry.year_ce} className="hover:bg-slate-50/70">
                    <td className="py-2 px-3 font-bold text-slate-900">
                      พ.ศ. {ry.year_be} ({ry.year_ce})
                    </td>
                    <td className="py-2 px-3 text-slate-700">
                      {ry.population_year_be ? `พ.ศ. ${ry.population_year_be} (${ry.population_year_ce})` : '-'}
                      {ry.is_fallback_year && (
                        <span className="ml-1.5 px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px] font-sans font-semibold">
                          {lang === 'th' ? 'ใช้ปี 2568 ล่าสุดแทน' : 'Fallback 2568'}
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-3 font-sans text-slate-600">
                      {lang === 'th' ? ry.scope_name_th : ry.scope_name_en}
                    </td>
                    <td className="py-2 px-3 text-right font-bold text-slate-900">{ry.numerator_cases_C.toLocaleString()}</td>
                    <td className="py-2 px-3 text-right text-slate-700">
                      {ry.population_denominator !== null ? ry.population_denominator.toLocaleString() : '-'}
                    </td>
                    <td className="py-2 px-3 text-right font-bold text-teal-800">
                      {ry.case_rate_per_100k !== null ? ry.case_rate_per_100k.toLocaleString() : 'Unavailable'}
                    </td>
                    <td className="py-2 px-3 text-center text-slate-500">
                      {ry.case_rate_ci
                        ? `[${ry.case_rate_ci[0]}, ${ry.case_rate_ci[1]}]`
                        : '-'}
                    </td>
                    <td className="py-2 px-3 text-right text-blue-800">
                      {ry.hosp_rate_per_100k !== null
                        ? ry.hosp_rate_per_100k.toLocaleString()
                        : 'Unavailable'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Snapshot Visualizations: Epicurve & District Rankings */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="font-bold text-slate-800 text-sm">
                {figLang === 'th' ? 'แนวโน้มผู้ป่วยรายสัปดาห์ (Epidemic Curve)' : 'Weekly Surveillance Curve'}
              </h4>
              <p className="text-xs text-slate-500">
                {figLang === 'th' ? 'จำแนกตามผู้ป่วยใน (IPD) และผู้ป่วยนอก (OPD)' : 'Stacked by IPD, OPD, and Unknown'}
              </p>
            </div>
            <button
              onClick={() => setActiveTab('time')}
              className="text-xs text-teal-600 hover:text-teal-700 font-medium flex items-center gap-1"
            >
              <span>{lang === 'th' ? 'ดูรายละเอียด' : 'Details'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weeklyData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis
                  dataKey={figLang === 'th' ? 'label_th' : 'label_en'}
                  tick={{ fontSize: 10, fill: '#64748b' }}
                  interval={2}
                  angle={-25}
                  textAnchor="end"
                />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                <Bar dataKey="opd_cases" stackId="a" fill="#0284c7" name={figLang === 'th' ? 'ผู้ป่วยนอก (OPD)' : 'Outpatient (OPD)'} />
                <Bar dataKey="unknown_cases" stackId="a" fill="#94a3b8" name={figLang === 'th' ? 'ไม่ระบุประเภท' : 'Unknown Type'} />
                <Bar dataKey="ipd_cases" stackId="a" fill="#0d9488" name={figLang === 'th' ? 'ผู้ป่วยใน (IPD)' : 'Inpatient (IPD)'} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="font-bold text-slate-800 text-sm">
                {figLang === 'th' ? 'การกระจายของผู้ป่วยรายอำเภอ (Top Districts)' : 'District Case Burden'}
              </h4>
              <p className="text-xs text-slate-500">
                {figLang === 'th'
                  ? filters.address_type === 'illness'
                    ? 'ตามที่อยู่ขณะป่วย (Illness Address)'
                    : 'ตามที่อยู่ปัจจุบัน (Current Residence)'
                  : filters.address_type === 'illness'
                  ? 'Ranked by illness address district'
                  : 'Ranked by current residence district'}
              </p>
            </div>
            <button
              onClick={() => setActiveTab('districts')}
              className="text-xs text-teal-600 hover:text-teal-700 font-medium flex items-center gap-1"
            >
              <span>{lang === 'th' ? 'ดูรายอำเภอ' : 'District view'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart layout="vertical" data={districtData} margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis
                  dataKey={figLang === 'th' ? 'district_name_th' : 'district_name_en'}
                  type="category"
                  tick={{ fontSize: 10, fill: '#334155' }}
                  width={95}
                />
                <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                <Bar
                  dataKey="cases_C"
                  fill="#0d9488"
                  radius={[0, 4, 4, 0]}
                  name={figLang === 'th' ? 'จำนวนผู้ป่วย (ราย)' : 'Cases'}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
