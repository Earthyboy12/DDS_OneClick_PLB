import React, { useEffect, useState } from 'react';
import {
  Download,
  FileSpreadsheet,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import {
  getTable0,
  getTable1,
  getTable2,
  getTable3,
  getTable4,
  getExcelExportUrl,
  getCsvExportUrl,
} from '../services/api';

export const SummaryTablesPage: React.FC = () => {
  const { lang, isLoaded, filterVersion, measures } = useApp();
  const [activeTable, setActiveTable] = useState<string>('table1');
  const [table0Data, setTable0Data] = useState<any[]>([]);
  const [table1Data, setTable1Data] = useState<any>(null);
  const [table2Data, setTable2Data] = useState<any[]>([]);
  const [table2RatesByYear, setTable2RatesByYear] = useState<any[]>([]);
  const [table3Data, setTable3Data] = useState<any[]>([]);
  const [table4Data, setTable4Data] = useState<any>(null);
  const [, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (isLoaded) {
      setLoading(true);
      Promise.all([
        getTable0().then((r: any) => setTable0Data(r.rows || [])),
        getTable1().then((r: any) => setTable1Data(r)),
        getTable2().then((r: any) => {
          setTable2Data(r.rows || []);
          setTable2RatesByYear(r.rates_by_year || []);
        }),
        getTable3().then((r: any) => setTable3Data(r.rows || [])),
        getTable4().then((r: any) => setTable4Data(r)),
      ])
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [isLoaded, filterVersion]);

  const tabs = [
    { id: 'table0', labelTh: 'ตารางที่ 0 — ผังคัดกรองระเบียน', labelEn: 'Table 0 — Audit Flow' },
    { id: 'table1', labelTh: 'ตารางที่ 1 — ลักษณะทั่วไป', labelEn: 'Table 1 — Characteristics' },
    { id: 'table2', labelTh: 'ตารางที่ 2 — ภาระโรคตามกลุ่มอายุ', labelEn: 'Table 2 — Age Burden' },
    { id: 'table3', labelTh: 'ตารางที่ 3 — สรุปรายอำเภอ', labelEn: 'Table 3 — Districts' },
    { id: 'table4', labelTh: 'ตารางที่ 4 — สถิติและพยากรณ์รายสัปดาห์', labelEn: 'Table 4 — Weekly OLS Forecast' },
  ];

  return (
    <div className="space-y-6">
      {/* Table Navigation Header */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h3 className="font-bold text-slate-800 text-base">
            {lang === 'th' ? 'ตารางสรุปมาตรฐานระบาดวิทยา (Summary Tables 0–4)' : 'Surveillance Summary Tables (Tables 0–4)'}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {lang === 'th'
              ? 'จัดรูปแบบพร้อมแสดงตัวตั้ง ตัวหาร ปีประชากร ขอบเขตพื้นที่ และเชิงอรรถระบาดวิทยา สามารถดาวน์โหลดเป็น XLSX / CSV'
              : 'Filter-responsive tables with numerator, denominator, population year, geography scope, and multi-sheet XLSX export.'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <a
            href={getExcelExportUrl()}
            download
            className="px-3.5 py-1.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-medium transition flex items-center gap-1.5 shadow-xs"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>{lang === 'th' ? 'ดาวน์โหลด Excel (ทุกตาราง)' : 'Download XLSX (All Tables)'}</span>
          </a>
        </div>
      </div>

      {/* Tabs list */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-slate-200">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTable(tab.id)}
            className={`px-3.5 py-2 rounded-xl text-xs font-medium whitespace-nowrap transition ${
              activeTable === tab.id
                ? 'bg-navy-800 text-white shadow-xs font-semibold'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            {lang === 'th' ? tab.labelTh : tab.labelEn}
          </button>
        ))}
      </div>

      {/* Table Views */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        {/* TABLE 0: Ingestion & Flow */}
        {activeTable === 'table0' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-slate-800 text-sm">
                {lang === 'th'
                  ? 'ตารางที่ 0 — ผังการนำเข้าและตรวจสอบสิทธิ์ระเบียนผู้ป่วย (Auditable Ingestion Flow)'
                  : 'Table 0 — Auditable Data Ingestion & Eligibility Flow'}
              </h4>
              <a
                href={getCsvExportUrl('table0')}
                className="text-xs text-teal-600 hover:underline flex items-center gap-1"
              >
                <Download className="w-3 h-3" />
                <span>Export CSV</span>
              </a>
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-xl">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                  <tr>
                    <th className="py-2.5 px-3 font-semibold">{lang === 'th' ? 'ลำดับ' : 'Step'}</th>
                    <th className="py-2.5 px-3 font-semibold">{lang === 'th' ? 'ขั้นตอนการคัดกรอง' : 'Screening Stage'}</th>
                    <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'จำนวน (N)' : 'Count (N)'}</th>
                    <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'ร้อยละ (%)' : 'Percent (%)'}</th>
                    <th className="py-2.5 px-3 font-semibold">{lang === 'th' ? 'หมายเหตุระบาดวิทยา' : 'Methodological Note'}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {table0Data.map((r) => (
                    <tr key={r.step} className="hover:bg-slate-50/70">
                      <td className="py-2.5 px-3 text-slate-400">{r.step}</td>
                      <td className="py-2.5 px-3 font-sans font-medium text-slate-900">
                        {lang === 'th' ? r.stage_th : r.stage_en}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-slate-900">{r.count.toLocaleString()}</td>
                      <td className="py-2.5 px-3 text-right text-teal-800 font-semibold">{r.pct_th}</td>
                      <td className="py-2.5 px-3 font-sans text-slate-500 text-[11px]">
                        {lang === 'th' ? r.note_th : r.note_en}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TABLE 1: Characteristics */}
        {activeTable === 'table1' && table1Data && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-slate-800 text-sm">
                {lang === 'th'
                  ? 'ตารางที่ 1 — ลักษณะทั่วไปของผู้ป่วยที่เข้าเกณฑ์การเฝ้าระวัง (Reported Case Characteristics)'
                  : 'Table 1 — Reported Case Characteristics'}
              </h4>
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-xl">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                  <tr>
                    <th className="py-2.5 px-3 font-semibold">{lang === 'th' ? 'ลักษณะ / ตัวชี้วัด' : 'Characteristic / Metric'}</th>
                    <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'ภาพรวม (Overall)' : 'Overall'}</th>
                    <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'สัญชาติไทย (Thai)' : 'Thai'}</th>
                    <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'ไม่ใช่สัญชาติไทย (Non-Thai)' : 'Non-Thai'}</th>
                    <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'ไม่ระบุ / ตรวจสอบ (Unknown)' : 'Unknown'}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  <tr className="hover:bg-slate-50/70 font-semibold text-slate-900">
                    <td className="py-2.5 px-3 font-sans">{lang === 'th' ? 'ผู้ป่วยเข้าเกณฑ์ C (ราย)' : 'Reported Cases (C)'}</td>
                    {table1Data.columns.map((c: string) => (
                      <td key={c} className="py-2.5 px-3 text-right">{table1Data.metrics.cases[c]?.toLocaleString()}</td>
                    ))}
                  </tr>
                  <tr className="hover:bg-slate-50/70">
                    <td className="py-2.5 px-3 font-sans text-slate-700">{lang === 'th' ? 'อายุเฉลี่ย มัธยฐาน (IQR)' : 'Median Age (IQR)'}</td>
                    {table1Data.columns.map((c: string) => (
                      <td key={c} className="py-2.5 px-3 text-right text-slate-800">{table1Data.metrics.median_iqr_age[c]}</td>
                    ))}
                  </tr>
                  <tr className="hover:bg-slate-50/70">
                    <td className="py-2.5 px-3 font-sans text-slate-700">{lang === 'th' ? 'เพศ: ชาย n (%)' : 'Sex: Male n (%)'}</td>
                    {table1Data.columns.map((c: string) => (
                      <td key={c} className="py-2.5 px-3 text-right text-blue-700">{table1Data.metrics.sex_male[c]}</td>
                    ))}
                  </tr>
                  <tr className="hover:bg-slate-50/70">
                    <td className="py-2.5 px-3 font-sans text-slate-700">{lang === 'th' ? 'เพศ: หญิง n (%)' : 'Sex: Female n (%)'}</td>
                    {table1Data.columns.map((c: string) => (
                      <td key={c} className="py-2.5 px-3 text-right text-rose-700">{table1Data.metrics.sex_female[c]}</td>
                    ))}
                  </tr>
                  <tr className="hover:bg-slate-50/70">
                    <td className="py-2.5 px-3 font-sans text-slate-700">{lang === 'th' ? 'ผู้ป่วยใน IPD (H) n (%)' : 'Inpatient IPD (H) n (%)'}</td>
                    {table1Data.columns.map((c: string) => (
                      <td key={c} className="py-2.5 px-3 text-right text-teal-800">{table1Data.metrics.ipd_count[c]}</td>
                    ))}
                  </tr>
                  <tr className="hover:bg-slate-50/70">
                    <td className="py-2.5 px-3 font-sans text-slate-700">{lang === 'th' ? 'ผู้ป่วยนอก OPD (O) n (%)' : 'Outpatient OPD (O) n (%)'}</td>
                    {table1Data.columns.map((c: string) => (
                      <td key={c} className="py-2.5 px-3 text-right text-blue-800">{table1Data.metrics.opd_count[c]}</td>
                    ))}
                  </tr>
                  <tr className="hover:bg-slate-50/70">
                    <td className="py-2.5 px-3 font-sans text-slate-700">{lang === 'th' ? 'ไม่ระบุประเภท (U) n (%)' : 'Unknown Type (U) n (%)'}</td>
                    {table1Data.columns.map((c: string) => (
                      <td key={c} className="py-2.5 px-3 text-right text-slate-400">{table1Data.metrics.unknown_pt_count[c]}</td>
                    ))}
                  </tr>
                  <tr className="hover:bg-slate-50/70 bg-teal-50/30 font-semibold">
                    <td className="py-2.5 px-3 font-sans text-teal-900">{lang === 'th' ? 'สัดส่วนนอน รพ. H/(H+O) (95% Wilson CI)' : 'Hospitalization Prop (95% Wilson CI)'}</td>
                    {table1Data.columns.map((c: string) => (
                      <td key={c} className="py-2.5 px-3 text-right text-teal-800">{table1Data.metrics.hospitalization_prop[c]}</td>
                    ))}
                  </tr>
                  <tr className="hover:bg-slate-50/70">
                    <td className="py-2.5 px-3 font-sans text-slate-700">{lang === 'th' ? 'ความสมบูรณ์ประเภทผู้ป่วย (H+O)/C' : 'Patient-Type Completeness (%)'}</td>
                    {table1Data.columns.map((c: string) => (
                      <td key={c} className="py-2.5 px-3 text-right text-slate-700">{table1Data.metrics.patient_type_completeness[c]}</td>
                    ))}
                  </tr>
                  <tr className="hover:bg-slate-50/70">
                    <td className="py-2.5 px-3 font-sans text-slate-700">{lang === 'th' ? 'ผู้เสียชีวิตที่บันทึกไว้ n (%)' : 'Recorded Deaths n (%)'}</td>
                    {table1Data.columns.map((c: string) => (
                      <td key={c} className="py-2.5 px-3 text-right text-slate-700">{table1Data.metrics.recorded_deaths[c]}</td>
                    ))}
                  </tr>

                  <tr className="bg-slate-100/70 font-semibold text-slate-700">
                    <td colSpan={5} className="py-2 px-3 font-sans">
                      {lang === 'th' ? 'กลุ่มอายุ 5 ปี (Age Bands)' : '5-Year Age Groups'}
                    </td>
                  </tr>
                  {Object.entries(table1Data.age_bands).map(([band, dict]: any) => (
                    <tr key={band} className="hover:bg-slate-50/70 text-slate-600">
                      <td className="py-1.5 px-5 font-sans">• {band} {lang === 'th' ? 'ปี' : 'years'}</td>
                      {table1Data.columns.map((c: string) => (
                        <td key={c} className="py-1.5 px-3 text-right">{dict[c] || '-'}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="text-[11px] text-slate-500 italic">
              {lang === 'th' ? table1Data.notes_th : table1Data.notes_en}
            </p>
          </div>
        )}

        {/* TABLE 2: Age-Specific Burden */}
        {activeTable === 'table2' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-bold text-slate-800 text-sm">
                  {lang === 'th'
                    ? 'ตารางที่ 2 — ภาระโรคจำแนกตามกลุ่มอายุ (Age-Specific Disease Burden)'
                    : 'Table 2 — Age-Specific Disease Burden'}
                </h4>
                <p className="text-xs text-slate-500 mt-0.5">
                  {lang === 'th'
                    ? `ขอบเขตพื้นที่: ${measures?.scope_name_th || '-'} | ปีประชากร: ${measures?.population_year_be ? `พ.ศ. ${measures.population_year_be} (${measures.population_year_ce})` : 'แยกตามปีที่เลือก'}`
                    : `Scope: ${measures?.scope_name_en || '-'} | Pop Year: ${measures?.population_year_ce ?? 'Per-Year'}`}
                </p>
              </div>
              <a
                href={getCsvExportUrl('table2')}
                className="text-xs text-teal-600 hover:underline flex items-center gap-1"
              >
                <Download className="w-3 h-3" />
                <span>Export CSV</span>
              </a>
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-xl">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                  <tr>
                    <th className="py-2.5 px-3 font-semibold">{lang === 'th' ? 'กลุ่มอายุ' : 'Age Band'}</th>
                    <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'ตัวตั้ง C' : 'Cases C'}</th>
                    <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'ตัวหารประชากร P' : 'Population P'}</th>
                    <th className="py-2.5 px-3 font-semibold text-center">{lang === 'th' ? 'ปีประชากร' : 'Pop Year'}</th>
                    <th className="py-2.5 px-3 font-semibold">{lang === 'th' ? 'ขอบเขตพื้นที่' : 'Scope'}</th>
                    <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'อัตราป่วย/แสน' : 'Rate / 100k'}</th>
                    <th className="py-2.5 px-3 font-semibold text-center">95% Poisson CI</th>
                    <th className="py-2.5 px-3 font-semibold text-right">IPD (H)</th>
                    <th className="py-2.5 px-3 font-semibold text-right">OPD (O)</th>
                    <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'ไม่ระบุ (U)' : 'Unknown'}</th>
                    <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'สัดส่วน IPD (%)' : 'Hosp %'}</th>
                    <th className="py-2.5 px-3 font-semibold text-center">95% Wilson CI</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {table2Data.map((r) => (
                    <tr key={r.age_band} className="hover:bg-slate-50/70">
                      <td className="py-2 px-3 font-sans font-medium text-slate-900">{r.age_band}</td>
                      <td className="py-2 px-3 text-right font-bold text-slate-900">{r.cases_C.toLocaleString()}</td>
                      <td className="py-2 px-3 text-right text-slate-600">{r.compatible_population?.toLocaleString() ?? '-'}</td>
                      <td className="py-2 px-3 text-center text-slate-600">
                        {r.population_year_be ? `พ.ศ. ${r.population_year_be}` : '-'}
                      </td>
                      <td className="py-2 px-3 font-sans text-slate-600 text-[11px]">
                        {lang === 'th' ? r.scope_name_th : r.scope_name_en}
                      </td>
                      <td className="py-2 px-3 text-right font-semibold text-teal-800">{r.case_notification_rate?.toLocaleString() ?? '-'}</td>
                      <td className="py-2 px-3 text-center text-slate-500">
                        {r.case_notification_rate_ci ? `[${r.case_notification_rate_ci[0]}, ${r.case_notification_rate_ci[1]}]` : '-'}
                      </td>
                      <td className="py-2 px-3 text-right text-teal-700">{r.ipd_H.toLocaleString()}</td>
                      <td className="py-2 px-3 text-right text-blue-700">{r.opd_O.toLocaleString()}</td>
                      <td className="py-2 px-3 text-right text-slate-400">{r.unknown_U.toLocaleString()}</td>
                      <td className="py-2 px-3 text-right font-bold text-teal-800">{r.hospitalization_prop}%</td>
                      <td className="py-2 px-3 text-center text-slate-500">[{r.hospitalization_prop_ci[0]}%, {r.hospitalization_prop_ci[1]}%]</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Per-Year Rate Breakdown inside Table 2 when multi-year is present */}
            {table2RatesByYear && table2RatesByYear.length > 0 && (
              <div className="pt-2 space-y-2">
                <h5 className="font-bold text-slate-700 text-xs">
                  {lang === 'th'
                    ? 'ตารางย่อย — อัตราป่วยต่อแสนประชากรจำแนกรายปี (แยกคำนวณตามปี ไม่รวมผู้ป่วยหลายปีหารด้วยประชากรปีเดียว):'
                    : 'Subtable — Per-Year Population-Based Rates Breakdown:'}
                </h5>
                <div className="overflow-x-auto border border-slate-200 rounded-xl">
                  <table className="w-full text-xs text-left font-mono">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                      <tr>
                        <th className="py-2 px-3 font-semibold">{lang === 'th' ? 'ปีที่ป่วย' : 'Year'}</th>
                        <th className="py-2 px-3 font-semibold">{lang === 'th' ? 'ปีประชากรที่ใช้หาร' : 'Pop Year Used'}</th>
                        <th className="py-2 px-3 font-semibold">{lang === 'th' ? 'ขอบเขตพื้นที่' : 'Scope'}</th>
                        <th className="py-2 px-3 font-semibold text-right">{lang === 'th' ? 'ตัวตั้ง C' : 'Cases C'}</th>
                        <th className="py-2 px-3 font-semibold text-right">{lang === 'th' ? 'ตัวหารประชากร P' : 'Population P'}</th>
                        <th className="py-2 px-3 font-semibold text-right">{lang === 'th' ? 'อัตราป่วย/แสน' : 'Rate / 100k'}</th>
                        <th className="py-2 px-3 font-semibold text-center">95% Poisson CI</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {table2RatesByYear.map((ry: any) => (
                        <tr key={ry.year_ce} className="hover:bg-slate-50/70">
                          <td className="py-2 px-3 font-bold text-slate-900">
                            พ.ศ. {ry.year_be} ({ry.year_ce})
                          </td>
                          <td className="py-2 px-3 text-slate-700">
                            {ry.population_year_be ? `พ.ศ. ${ry.population_year_be} (${ry.population_year_ce})` : '-'}
                          </td>
                          <td className="py-2 px-3 font-sans text-slate-600">
                            {lang === 'th' ? ry.scope_name_th : ry.scope_name_en}
                          </td>
                          <td className="py-2 px-3 text-right font-bold text-slate-900">{(ry.numerator_cases_C ?? ry.cases_C ?? 0).toLocaleString()}</td>
                          <td className="py-2 px-3 text-right text-slate-700">
                            {ry.population_denominator !== null && ry.population_denominator !== undefined ? ry.population_denominator.toLocaleString() : '-'}
                          </td>
                          <td className="py-2 px-3 text-right font-bold text-teal-800">
                            {ry.case_rate_per_100k !== null && ry.case_rate_per_100k !== undefined ? ry.case_rate_per_100k.toLocaleString() : 'Unavailable'}
                          </td>
                          <td className="py-2 px-3 text-center text-slate-500">
                            {ry.case_rate_ci
                              ? `[${ry.case_rate_ci[0]}, ${ry.case_rate_ci[1]}]`
                              : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TABLE 3: District Summary */}
        {activeTable === 'table3' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-slate-800 text-sm">
                {lang === 'th'
                  ? 'ตารางที่ 3 — ข้อมูลสรุปรายอำเภอ (District Summary Table)'
                  : 'Table 3 — District Surveillance Summary'}
              </h4>
              <a
                href={getCsvExportUrl('table3')}
                className="text-xs text-teal-600 hover:underline flex items-center gap-1"
              >
                <Download className="w-3 h-3" />
                <span>Export CSV</span>
              </a>
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-xl">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                  <tr>
                    <th className="py-2.5 px-3 font-semibold">{lang === 'th' ? 'รหัสอำเภอ' : 'District Code'}</th>
                    <th className="py-2.5 px-3 font-semibold">{lang === 'th' ? 'ชื่ออำเภอ (ไทย)' : 'Name (TH)'}</th>
                    <th className="py-2.5 px-3 font-semibold">{lang === 'th' ? 'District (EN)' : 'Name (EN)'}</th>
                    <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'ตัวตั้ง C' : 'Cases C'}</th>
                    <th className="py-2.5 px-3 font-semibold text-right">IPD (H)</th>
                    <th className="py-2.5 px-3 font-semibold text-right">OPD (O)</th>
                    <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'ไม่ระบุ (U)' : 'Unknown'}</th>
                    <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'สัดส่วน IPD (%)' : 'Hosp %'}</th>
                    <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'ตัวหารประชากร' : 'Pop Denominator'}</th>
                    <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'อัตราป่วย/แสน' : 'Rate / 100k'}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {table3Data.map((d) => (
                    <tr key={d.district_code} className="hover:bg-slate-50/70">
                      <td className="py-2 px-3 text-slate-500">{d.district_code}</td>
                      <td className="py-2 px-3 font-sans font-medium text-slate-900">{d.district_name_th}</td>
                      <td className="py-2 px-3 font-sans text-slate-600">{d.district_name_en}</td>
                      <td className="py-2 px-3 text-right font-bold text-slate-900">{d.cases_C.toLocaleString()}</td>
                      <td className="py-2 px-3 text-right text-teal-700">{d.ipd_H.toLocaleString()}</td>
                      <td className="py-2 px-3 text-right text-blue-700">{d.opd_O.toLocaleString()}</td>
                      <td className="py-2 px-3 text-right text-slate-400">{d.unknown_U.toLocaleString()}</td>
                      <td className="py-2 px-3 text-right font-bold text-teal-800">{d.hospitalization_prop}%</td>
                      <td className="py-2 px-3 text-right text-slate-500">
                        {d.compatible_population ? d.compatible_population.toLocaleString() : '-'}
                      </td>
                      <td className="py-2 px-3 text-right">
                        {d.case_rate_per_100k !== null ? (
                          <span className="text-teal-800 font-bold">{d.case_rate_per_100k}</span>
                        ) : (
                          <span className="text-slate-400 font-sans italic text-[11px]" title={d.rate_status_note}>
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
        )}

        {/* TABLE 4: Weekly Surveillance & OLS Forecast */}
        {activeTable === 'table4' && table4Data && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-bold text-slate-800 text-sm">
                  {lang === 'th'
                    ? 'ตารางที่ 4 — ข้อมูลการเฝ้าระวังรายสัปดาห์และการพยากรณ์โรค (Weekly Surveillance & OLS Forecast)'
                    : 'Table 4 — Weekly Surveillance Observations & OLS Forecast'}
                </h4>
                {table4Data.model_summary && (
                  <p className="text-xs text-slate-500 mt-0.5">
                    {lang === 'th'
                      ? `ฝึกแบบจำลองจาก ${table4Data.model_summary.n_weeks_used} สัปดาห์สมบูรณ์ล่าสุด (${table4Data.model_summary.fit_window_label_th})`
                      : `Fitted on ${table4Data.model_summary.n_weeks_used} latest complete weeks (${table4Data.model_summary.fit_window_label_en})`}
                  </p>
                )}
              </div>
              <a
                href={getCsvExportUrl('table4')}
                className="text-xs text-teal-600 hover:underline flex items-center gap-1"
              >
                <Download className="w-3 h-3" />
                <span>Export CSV</span>
              </a>
            </div>

            {table4Data.status === 'success' ? (
              <div className="overflow-x-auto max-h-96 border border-slate-200 rounded-xl">
                <table className="w-full text-xs text-left">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 sticky top-0">
                    <tr>
                      <th className="py-2.5 px-3 font-semibold">t</th>
                      <th className="py-2.5 px-3 font-semibold">{lang === 'th' ? 'ปี/สัปดาห์' : 'Year/Wk'}</th>
                      <th className="py-2.5 px-3 font-semibold">{lang === 'th' ? 'ช่วงวันที่' : 'Interval'}</th>
                      <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'ผู้ป่วยจริง (Observed)' : 'Observed'}</th>
                      <th className="py-2.5 px-3 font-semibold text-right">{lang === 'th' ? 'คาดหมาย (Fitted)' : 'Fitted'}</th>
                      <th className="py-2.5 px-3 font-semibold text-center">80% PI</th>
                      <th className="py-2.5 px-3 font-semibold text-center">95% PI</th>
                      <th className="py-2.5 px-3 font-semibold">{lang === 'th' ? 'สถานะ' : 'Status'}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {[...(table4Data.history || []), ...(table4Data.forecasts || [])].map((r: any) => (
                      <tr
                        key={r.t}
                        className={`hover:bg-slate-50/70 ${r.is_forecast ? 'bg-rose-50/40 font-semibold' : ''}`}
                      >
                        <td className="py-2 px-3 text-slate-400">{r.t}</td>
                        <td className="py-2 px-3 font-semibold text-slate-800">W{String(r.epi_week).padStart(2, '0')}/{r.epi_year}</td>
                        <td className="py-2 px-3 font-sans text-slate-600">{r.week_start} ถึง {r.week_end}</td>
                        <td className="py-2 px-3 text-right font-bold text-slate-900">{r.observed !== null ? r.observed.toLocaleString() : '-'}</td>
                        <td className="py-2 px-3 text-right text-teal-800">{r.fitted_clipped}</td>
                        <td className="py-2 px-3 text-center text-slate-600">[{r.pi_80_lower}, {r.pi_80_upper}]</td>
                        <td className="py-2 px-3 text-center text-slate-600">[{r.pi_95_lower}, {r.pi_95_upper}]</td>
                        <td className="py-2 px-3 font-sans">
                          {r.is_forecast ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] bg-rose-100 text-rose-800 font-medium">
                              {lang === 'th' ? 'พยากรณ์ล่วงหน้า' : 'Forecast'}
                            </span>
                          ) : (
                            <span className="text-slate-400 text-[11px]">{lang === 'th' ? 'สังเกตการณ์' : 'Observed'}</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs">
                {table4Data.reason}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
