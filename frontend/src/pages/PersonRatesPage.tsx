import React, { useEffect, useState } from 'react';
import { Presentation, AlertCircle, Info } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { getPersonPyramid, getTable2 } from '../services/api';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  LineChart,
  Line,
} from 'recharts';

export const PersonRatesPage: React.FC = () => {
  const { lang, figLang, setActiveTab, isLoaded, filterVersion, measures } = useApp();
  const [pyramidData, setPyramidData] = useState<any[]>([]);
  const [natData, setNatData] = useState<any>({ Thai: 0, 'Non-Thai': 0, Unknown: 0 });
  const [ageBurden, setAgeBurden] = useState<any[]>([]);

  useEffect(() => {
    if (isLoaded) {
      getPersonPyramid()
        .then((res) => {
          setPyramidData(res.pyramid);
          setNatData(res.nationality_breakdown);
        })
        .catch(console.error);

      getTable2()
        .then((res) => {
          setAgeBurden(res.rows.filter((r) => r.age_band !== 'Unknown'));
        })
        .catch(console.error);
    }
  }, [isLoaded, filterVersion]);

  const totalCases = (natData.Thai || 0) + (natData['Non-Thai'] || 0) + (natData.Unknown || 0);
  const denom = measures?.denominator_info;
  const hasAgeRates = ageBurden.some((r) => r.case_notification_rate !== null);

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 className="font-bold text-slate-800 text-base">
            {lang === 'th'
              ? 'ลักษณะบุคคลและอัตราป่วยตามกลุ่มอายุ (Person & Age-Specific Rates)'
              : 'Person Characteristics & Age-Specific Rates'}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {lang === 'th'
              ? 'คำนวณอัตราต่อประชากรรายกลุ่มอายุจากมุมมอง population_by_age ใน dds_reference.sqlite รองรับจังหวัดเดียว หลายจังหวัด และทั่วประเทศ (หากไม่มีปีประชากรนั้น ใช้ปี 2568 ล่าสุดแทน)'
              : 'Age-specific rates computed from population_by_age in dds_reference.sqlite for single province, multiple provinces, and nationwide scopes (with 2568 BE fallback when needed).'}
          </p>
        </div>

        <button
          onClick={() => setActiveTab('studio')}
          className="px-3.5 py-1.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-medium transition flex items-center gap-1.5"
        >
          <Presentation className="w-3.5 h-3.5" />
          <span>{lang === 'th' ? 'สไลด์ 4K' : '4K Slide'}</span>
        </button>
      </div>

      {/* Row 1: Age-Sex Pyramid & Nationality Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-bold text-slate-800 text-sm">
                {figLang === 'th'
                  ? 'พีระมิดประชากรผู้ป่วย (Age-Sex Surveillance Pyramid)'
                  : 'Age-Sex Surveillance Pyramid'}
              </h4>
              <p className="text-xs text-slate-500">
                {figLang === 'th'
                  ? 'เปรียบเทียบจำนวนผู้ป่วยระหว่างเพศชาย (ซ้าย) และเพศหญิง (ขวา)'
                  : 'Male vs Female case distribution by standard age groups'}
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-blue-700 font-medium">
                <span className="w-3 h-3 rounded-xs bg-[#0284c7]" />
                {figLang === 'th' ? 'ชาย (Male)' : 'Male'}
              </span>
              <span className="flex items-center gap-1.5 text-rose-700 font-medium">
                <span className="w-3 h-3 rounded-xs bg-[#e11d48]" />
                {figLang === 'th' ? 'หญิง (Female)' : 'Female'}
              </span>
            </div>
          </div>

          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={pyramidData.map((d) => ({
                  ...d,
                  male_neg: -d.male,
                }))}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="0" stroke="#f1f5f9" horizontal={false} />
                <XAxis
                  type="number"
                  stroke="#000000"
                  strokeWidth={2}
                  tickFormatter={(val) => Math.abs(val).toLocaleString()}
                  tick={{ fontSize: 11, fill: '#000000', fontWeight: 700 }}
                  tickLine={{ stroke: '#000000', strokeWidth: 1.5 }}
                />
                <YAxis
                  dataKey="age_band"
                  type="category"
                  stroke="#000000"
                  strokeWidth={2}
                  tick={{ fontSize: 12, fill: '#000000', fontWeight: 700 }}
                  tickLine={{ stroke: '#000000', strokeWidth: 1.5 }}
                  width={65}
                />
                <Tooltip
                  formatter={(val: any, name: any) => [
                    `${Math.abs(Number(val)).toLocaleString()} ${figLang === 'th' ? 'ราย' : 'cases'}`,
                    name === 'male_neg'
                      ? figLang === 'th'
                        ? 'เพศชาย'
                        : 'Male'
                      : figLang === 'th'
                      ? 'เพศหญิง'
                      : 'Female',
                  ]}
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: '2px solid #000000' }}
                />
                <Bar dataKey="male_neg" fill="#0284c7" stroke="#000000" strokeWidth={1} radius={0} name="male_neg" />
                <Bar dataKey="female" fill="#e11d48" stroke="#000000" strokeWidth={1} radius={0} name="female" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Nationality Breakdown Card */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-bold text-slate-800 text-sm">
                {lang === 'th' ? 'การจำแนกกลุ่มสัญชาติ' : 'Nationality Distribution'}
              </h4>
              <span className="text-[11px] px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono">
                Counts & IPD% Only
              </span>
            </div>

            <p className="text-xs text-slate-500 mb-5 leading-relaxed">
              {lang === 'th'
                ? 'ฐานข้อมูล dds_reference.sqlite ไม่มีตารางประชากรแยกสัญชาติหรือแยกอายุตามสัญชาติ จึงแสดงเฉพาะจำนวนผู้ป่วยและสัดส่วน IPD% โดยไม่คำนวณอัตราต่อประชากรแยกสัญชาติ'
                : 'dds_reference.sqlite does not provide verified nationality or age-by-nationality denominators; only counts and hospitalization proportions are reported.'}
            </p>

            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-teal-50/70 border border-teal-200">
                <div className="flex items-center justify-between text-xs font-semibold text-teal-900 mb-1">
                  <span>{lang === 'th' ? 'สัญชาติไทย (Thai)' : 'Thai Nationals'}</span>
                  <span className="font-mono text-sm">{natData.Thai?.toLocaleString()}</span>
                </div>
                <div className="w-full bg-teal-200/50 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-teal-600 h-2 rounded-full"
                    style={{ width: `${totalCases ? (natData.Thai / totalCases) * 100 : 0}%` }}
                  />
                </div>
                <div className="text-[11px] text-teal-700 mt-1 text-right font-mono">
                  {totalCases ? ((natData.Thai / totalCases) * 100).toFixed(1) : 0}%
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-blue-50/70 border border-blue-200">
                <div className="flex items-center justify-between text-xs font-semibold text-blue-900 mb-1">
                  <span>{lang === 'th' ? 'ไม่ใช่สัญชาติไทย (Non-Thai)' : 'Non-Thai Residents'}</span>
                  <span className="font-mono text-sm">{natData['Non-Thai']?.toLocaleString()}</span>
                </div>
                <div className="w-full bg-blue-200/50 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{ width: `${totalCases ? (natData['Non-Thai'] / totalCases) * 100 : 0}%` }}
                  />
                </div>
                <div className="text-[11px] text-blue-700 mt-1 text-right font-mono">
                  {totalCases ? ((natData['Non-Thai'] / totalCases) * 100).toFixed(1) : 0}%
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-800 mb-1">
                  <span>{lang === 'th' ? 'ไม่ระบุ / รอการตรวจสอบ' : 'Unknown / Unresolved'}</span>
                  <span className="font-mono text-sm">{natData.Unknown?.toLocaleString()}</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-slate-500 h-2 rounded-full"
                    style={{ width: `${totalCases ? (natData.Unknown / totalCases) * 100 : 0}%` }}
                  />
                </div>
                <div className="text-[11px] text-slate-500 mt-1 text-right font-mono">
                  {totalCases ? ((natData.Unknown / totalCases) * 100).toFixed(1) : 0}%
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-500">
            {lang === 'th'
              ? 'ห้ามนำยอดคนต่างด้าวไปลบออกจากประชากรรวมเพื่ออนุมานตัวหารคนไทย'
              : 'Never subtracts foreign-national subtotals from total population to infer Thai denominators.'}
          </div>
        </div>
      </div>

      {/* Row 2: Age-Specific Case Notification Rates & Hospitalization Proportions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div>
            <h4 className="font-bold text-slate-800 text-sm">
              {figLang === 'th'
                ? 'อัตราป่วยต่อแสนประชากรตามกลุ่มอายุ (Exact Poisson CI)'
                : 'Age-Specific Notification Rates per 100,000'}
            </h4>
            <p className="text-xs text-slate-500">
              {denom?.available
                ? figLang === 'th'
                  ? `คำนวณเทียบกับประชากรรายอายุที่ตรงเงื่อนไข (${measures?.scope_name_th}, ปีประชากร พ.ศ. ${denom.population_year_be} / ค.ศ. ${denom.reference_year}${denom.is_fallback_year ? ' • ใช้ปี 2568 ล่าสุดแทน' : ''})`
                  : `Calculated against matched single-year age denominators (${measures?.scope_name_en}, Pop Year ${denom.reference_year} / BE ${denom.population_year_be}${denom.is_fallback_year ? ' fallback' : ''})`
                : figLang === 'th'
                ? `งดคำนวณอัตราต่อประชากรรายอายุ: ${denom?.reason_th}`
                : `Age-specific rates unavailable: ${denom?.reason_en}`}
            </p>
          </div>

          {hasAgeRates ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={ageBurden} margin={{ top: 15, right: 20, left: 0, bottom: 30 }}>
                  <CartesianGrid strokeDasharray="0" stroke="#f1f5f9" vertical={false} />
                  <XAxis
                    dataKey="age_band"
                    stroke="#000000"
                    strokeWidth={2}
                    tick={{ fontSize: 11, fill: '#000000', fontWeight: 700 }}
                    tickLine={{ stroke: '#000000', strokeWidth: 1.5 }}
                    angle={-35}
                    textAnchor="end"
                  />
                  <YAxis
                    stroke="#000000"
                    strokeWidth={2}
                    tick={{ fontSize: 11, fill: '#000000', fontWeight: 700 }}
                    tickLine={{ stroke: '#000000', strokeWidth: 1.5 }}
                  />
                  <Tooltip
                    formatter={(val: any, _name: any, props: any) => {
                      const row = props?.payload;
                      const detail = row
                        ? ` (C=${row.cases_C?.toLocaleString()} / Pop=${row.compatible_population?.toLocaleString()} | ปี พ.ศ. ${row.population_year_be} | ${row.scope_name_th})`
                        : '';
                      return [
                        `${Number(val).toLocaleString()} ${figLang === 'th' ? 'ต่อแสนประชากร' : 'per 100,000'}${detail}`,
                        figLang === 'th' ? 'อัตราป่วย' : 'Rate',
                      ];
                    }}
                    contentStyle={{ fontSize: 11, borderRadius: 8, border: '2px solid #000000' }}
                  />
                  <Line
                    type="linear"
                    dataKey="case_notification_rate"
                    stroke="#0d9488"
                    strokeWidth={2.5}
                    dot={{ r: 4.5, fill: '#0d9488', stroke: '#000000', strokeWidth: 1 }}
                    activeDot={{ r: 6.5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-72 flex flex-col items-center justify-center bg-amber-50/50 border border-amber-200 rounded-xl p-6 text-center text-xs text-amber-900 space-y-2">
              <AlertCircle className="w-6 h-6 text-amber-600" />
              <span className="font-bold">
                {lang === 'th'
                  ? 'ไม่สามารถคำนวณอัตราป่วยต่อประชากรรายกลุ่มอายุในขอบเขตตัวกรองนี้'
                  : 'Age-Specific Population Rates Unavailable for Active Filter Scope'}
              </span>
              <p className="text-amber-800 max-w-md">
                {lang === 'th' ? denom?.reason_th : denom?.reason_en}
              </p>
            </div>
          )}
        </div>

        {/* Chart 2: Hospitalization Proportions (Wilson CI) */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div>
            <h4 className="font-bold text-slate-800 text-sm">
              {figLang === 'th'
                ? 'สัดส่วนการนอนโรงพยาบาลตามกลุ่มอายุ (95% Wilson CI)'
                : 'Age-Specific Hospitalization Proportions'}
            </h4>
            <p className="text-xs text-slate-500">
              {figLang === 'th'
                ? 'H / (H + O) × 100 (ใช้ได้ทุกตัวกรอง ไม่รวมผู้ป่วยไม่ระบุประเภทในตัวหาร)'
                : 'H / (H + O) * 100 with Wilson score intervals (supported across all filter scopes)'}
            </p>
          </div>

          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={ageBurden} margin={{ top: 15, right: 20, left: 0, bottom: 25 }}>
                <CartesianGrid strokeDasharray="0" stroke="#f1f5f9" vertical={false} />
                <XAxis
                  dataKey="age_band"
                  stroke="#000000"
                  strokeWidth={2}
                  tick={{ fontSize: 10, fill: '#000000', fontWeight: 700 }}
                  tickLine={{ stroke: '#000000', strokeWidth: 1.5 }}
                  angle={-35}
                  textAnchor="end"
                />
                <YAxis
                  stroke="#000000"
                  strokeWidth={2}
                  tick={{ fontSize: 11, fill: '#000000', fontWeight: 700 }}
                  tickLine={{ stroke: '#000000', strokeWidth: 1.5 }}
                  domain={[0, 'dataMax + 10']}
                />
                <Tooltip
                  formatter={(val: any, _name: any, props: any) => {
                    const row = props?.payload;
                    const detail = row ? ` (IPD H=${row.ipd_H?.toLocaleString()}, OPD O=${row.opd_O?.toLocaleString()})` : '';
                    return [`${val}%${detail}`, figLang === 'th' ? 'สัดส่วน IPD' : 'IPD %'];
                  }}
                  contentStyle={{ fontSize: 11, borderRadius: 8, border: '2px solid #000000' }}
                />
                <Bar
                  dataKey="hospitalization_prop"
                  fill="#0284c7"
                  stroke="#000000"
                  strokeWidth={1.2}
                  radius={0}
                  name={figLang === 'th' ? 'สัดส่วน IPD (%)' : 'IPD %'}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Explicit Age-Specific Numerator / Denominator / Population Year / Scope Table */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-teal-600" />
            <h4 className="font-bold text-slate-800 text-sm">
              {lang === 'th'
                ? 'ตารางแสดงตัวตั้ง (Numerator) ตัวหารประชากร (Denominator) ปีประชากร และขอบเขตพื้นที่ตามกลุ่มอายุ'
                : 'Age-Specific Numerator, Denominator, Population Year & Geography Scope Breakdown'}
            </h4>
          </div>
          <span className="text-xs font-mono text-slate-500">
            {lang === 'th' ? measures?.scope_name_th : measures?.scope_name_en}
          </span>
        </div>

        <div className="overflow-x-auto border border-slate-200 rounded-xl">
          <table className="w-full text-xs text-left font-mono">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
              <tr>
                <th className="py-2 px-3 font-semibold">{lang === 'th' ? 'กลุ่มอายุ' : 'Age Band'}</th>
                <th className="py-2 px-3 font-semibold text-right">{lang === 'th' ? 'ตัวตั้ง C (ราย)' : 'Numerator C'}</th>
                <th className="py-2 px-3 font-semibold text-right">{lang === 'th' ? 'ตัวหารประชากร P' : 'Denominator P'}</th>
                <th className="py-2 px-3 font-semibold text-center">{lang === 'th' ? 'ปีประชากร' : 'Pop Year'}</th>
                <th className="py-2 px-3 font-semibold">{lang === 'th' ? 'ขอบเขตพื้นที่' : 'Scope'}</th>
                <th className="py-2 px-3 font-semibold text-right">{lang === 'th' ? 'อัตราป่วย/แสน' : 'Rate / 100k'}</th>
                <th className="py-2 px-3 font-semibold text-center">95% Poisson CI</th>
                <th className="py-2 px-3 font-semibold text-right">{lang === 'th' ? 'IPD (H)' : 'IPD (H)'}</th>
                <th className="py-2 px-3 font-semibold text-right">{lang === 'th' ? 'สัดส่วน IPD (%)' : 'Hosp %'}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {ageBurden.map((r) => (
                <tr key={r.age_band} className="hover:bg-slate-50/70">
                  <td className="py-2 px-3 font-sans font-semibold text-slate-900">{r.age_band}</td>
                  <td className="py-2 px-3 text-right font-bold text-slate-900">{r.cases_C.toLocaleString()}</td>
                  <td className="py-2 px-3 text-right text-slate-700">
                    {r.compatible_population !== null && r.compatible_population !== undefined
                      ? r.compatible_population.toLocaleString()
                      : '-'}
                  </td>
                  <td className="py-2 px-3 text-center text-slate-600">
                    {r.population_year_be ? `พ.ศ. ${r.population_year_be} (${r.population_year_ce})` : '-'}
                  </td>
                  <td className="py-2 px-3 font-sans text-slate-600 text-[11px]">
                    {lang === 'th' ? r.scope_name_th : r.scope_name_en}
                  </td>
                  <td className="py-2 px-3 text-right font-bold text-teal-800">
                    {r.case_notification_rate !== null && r.case_notification_rate !== undefined
                      ? r.case_notification_rate.toLocaleString()
                      : 'Unavailable'}
                  </td>
                  <td className="py-2 px-3 text-center text-slate-500">
                    {r.case_notification_rate_ci
                      ? `[${r.case_notification_rate_ci[0]}, ${r.case_notification_rate_ci[1]}]`
                      : '-'}
                  </td>
                  <td className="py-2 px-3 text-right text-teal-700">{r.ipd_H.toLocaleString()}</td>
                  <td className="py-2 px-3 text-right font-bold text-blue-800">{r.hospitalization_prop}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
