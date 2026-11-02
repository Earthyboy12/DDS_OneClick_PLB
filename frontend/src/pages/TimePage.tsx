import React, { useEffect, useState, useMemo } from 'react';
import {
  CalendarDays,
  Clock,
  Layers,
  Presentation,
  Info,
  Filter,
  TrendingUp,
  Activity,
  Calendar,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { getTimeEpicurve, getFigureRenderUrl } from '../services/api';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
  LineChart,
  Line,
  Area,
  ComposedChart,
} from 'recharts';

export const TimePage: React.FC = () => {
  const { lang, figLang, setActiveTab, isLoaded, filterVersion } = useApp();
  const [weeks, setWeeks] = useState<any[]>([]);
  const [yearBoundaries, setYearBoundaries] = useState<any[]>([]);
  const [seasonalData, setSeasonalData] = useState<any | null>(null);
  const [selectedView, setSelectedView] = useState<'all' | 'recent52' | 'recent26' | 'recent12'>('all');
  const [seasonalMetric, setSeasonalMetric] = useState<'cases' | 'rate'>('cases');

  useEffect(() => {
    if (isLoaded) {
      getTimeEpicurve()
        .then((res) => {
          setWeeks(res.weeks || []);
          setYearBoundaries(res.year_boundaries || []);
          setSeasonalData(res.seasonal_comparison || null);
        })
        .catch(console.error);
    }
  }, [isLoaded, filterVersion]);

  const displayedWeeks = useMemo(() => {
    if (selectedView === 'recent12') return weeks.slice(-12);
    if (selectedView === 'recent26') return weeks.slice(-26);
    if (selectedView === 'recent52') return weeks.slice(-52);
    return weeks;
  }, [weeks, selectedView]);

  // Determine active year boundaries inside displayedWeeks
  const activeBoundaries = useMemo(() => {
    if (!displayedWeeks.length || !yearBoundaries.length) return [];
    const minT = displayedWeeks[0].t;
    const maxT = displayedWeeks[displayedWeeks.length - 1].t;
    return yearBoundaries.filter((b) => b.t >= minT && b.t <= maxT);
  }, [displayedWeeks, yearBoundaries]);

  // Seasonal 2-Year vs 5-Year Median dataset for Recharts
  const seasonalChartData = useMemo(() => {
    if (!seasonalData || !seasonalData.weeks) return [];
    return seasonalData.weeks.map((w: any) => ({
      epi_week: w.epi_week,
      week_label: figLang === 'th' ? `W${String(w.epi_week).padStart(2, '0')}` : `W${String(w.epi_week).padStart(2, '0')}`,
      latest_val: seasonalMetric === 'cases' ? w.latest_cases : w.latest_rate,
      prev_val: seasonalMetric === 'cases' ? w.prev_cases : w.prev_rate,
      median_val: seasonalMetric === 'cases' ? w.median_5yr_cases : w.median_5yr_rate,
      q25_val: seasonalMetric === 'cases' ? w.q25_5yr_cases : null,
      q75_val: seasonalMetric === 'cases' ? w.q75_5yr_cases : null,
      raw_cases_latest: w.latest_cases,
      raw_cases_prev: w.prev_cases,
      raw_cases_median: w.median_5yr_cases,
      raw_rate_latest: w.latest_rate,
      raw_rate_prev: w.prev_rate,
      raw_rate_median: w.median_5yr_rate,
    }));
  }, [seasonalData, seasonalMetric, figLang]);

  const latestYearBe = seasonalData?.latest_year_be || (seasonalData?.latest_year ? seasonalData.latest_year + 543 : null);
  const prevYearBe = seasonalData?.prev_year_be || (seasonalData?.prev_year ? seasonalData.prev_year + 543 : null);
  const medianYearsCount = seasonalData?.median_years_count || 0;

  return (
    <div className="space-y-6">
      {/* Header controls card */}
      <div className="bg-white rounded-2xl border-2 border-slate-900 p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h3 className="font-extrabold text-slate-950 text-lg">
              {lang === 'th' ? 'แนวโน้มการระบาดตามเวลา' : 'Temporal Trends'}
            </h3>
          </div>
          <p className="text-xs text-slate-600 font-medium mt-1">
            {lang === 'th'
              ? 'กราฟการระบาดรายสัปดาห์ (Epi Week) และการเปรียบเทียบแนวโน้มเชิงฤดูกาล'
              : 'Weekly epidemiological trends and seasonal comparisons.'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* View Filter */}
          <div className="flex items-center bg-slate-100 p-1 rounded-lg text-xs font-bold border-2 border-slate-900">
            <button
              onClick={() => setSelectedView('all')}
              className={`px-3 py-1.5 rounded transition ${selectedView === 'all' ? 'bg-slate-900 text-white shadow-xs' : 'text-slate-700 hover:text-slate-950'}`}
            >
              {lang === 'th' ? 'ทุกสัปดาห์' : 'All Weeks'}
            </button>
            <button
              onClick={() => setSelectedView('recent52')}
              className={`px-3 py-1.5 rounded transition ${selectedView === 'recent52' ? 'bg-slate-900 text-white shadow-xs' : 'text-slate-700 hover:text-slate-950'}`}
            >
              {lang === 'th' ? '52 สัปดาห์ล่าสุด' : 'Last 52 Wks'}
            </button>
            <button
              onClick={() => setSelectedView('recent26')}
              className={`px-3 py-1.5 rounded transition ${selectedView === 'recent26' ? 'bg-slate-900 text-white shadow-xs' : 'text-slate-700 hover:text-slate-950'}`}
            >
              {lang === 'th' ? '26 สัปดาห์ล่าสุด' : 'Last 26 Wks'}
            </button>
            <button
              onClick={() => setSelectedView('recent12')}
              className={`px-3 py-1.5 rounded transition ${selectedView === 'recent12' ? 'bg-slate-900 text-white shadow-xs' : 'text-slate-700 hover:text-slate-950'}`}
            >
              {lang === 'th' ? '12 สัปดาห์ล่าสุด' : 'Last 12 Wks'}
            </button>
          </div>

          <button
            onClick={() => setActiveTab('studio')}
            className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold transition flex items-center gap-1.5 shadow-xs"
          >
            <Presentation className="w-4 h-4" />
            <span>{lang === 'th' ? 'สไลด์ 4K' : '4K Slide'}</span>
          </button>
        </div>
      </div>

      {/* Main Interactive Stacked Epidemic Chart with Vertical Dotted Year Divider Lines */}
      <div className="bg-white rounded-2xl border-2 border-slate-900 p-6 shadow-xs space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-slate-900 pb-3">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-slate-900" />
              <span className="text-sm font-extrabold text-slate-950">
                {lang === 'th'
                  ? `กราฟการระบาดรายสัปดาห์ (${displayedWeeks.length} สัปดาห์)`
                  : `Weekly Epidemic Curve (${displayedWeeks.length} weeks)`}
              </span>
            </div>
            <p className="text-xs text-slate-600 font-medium">
              {lang === 'th'
                ? 'เส้นประแนวตั้งแบ่งตามปีปฏิทิน'
                : 'Vertical dotted lines demarcating calendar years'}
            </p>
          </div>

          <div className="flex items-center gap-4 text-xs font-bold">
            <span className="inline-flex items-center gap-1.5 text-slate-900">
              <span className="w-3.5 h-3.5 rounded-none bg-[#0284c7] border border-slate-900" />
              {lang === 'th' ? 'ผู้ป่วยนอก (OPD)' : 'OPD'}
            </span>
            <span className="inline-flex items-center gap-1.5 text-slate-900">
              <span className="w-3.5 h-3.5 rounded-none bg-[#94a3b8] border border-slate-900" />
              {lang === 'th' ? 'ไม่ระบุประเภท (Unknown)' : 'Unknown'}
            </span>
            <span className="inline-flex items-center gap-1.5 text-slate-900">
              <span className="w-3.5 h-3.5 rounded-none bg-[#0d9488] border border-slate-900" />
              {lang === 'th' ? 'ผู้ป่วยใน (IPD)' : 'IPD'}
            </span>
            <span className="inline-flex items-center gap-1.5 text-slate-900">
              <span className="w-4 h-0 border-t-2 border-dashed border-slate-900" />
              {lang === 'th' ? 'เส้นแบ่งปี (Year Line)' : 'Year Line'}
            </span>
          </div>
        </div>

        <div className="h-[430px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={displayedWeeks} margin={{ top: 25, right: 25, left: 5, bottom: 45 }}>
              {/* GraphPad Prism: open top and right, minimal or no horizontal grid */}
              <CartesianGrid strokeDasharray="0" stroke="#f1f5f9" vertical={false} />
              <XAxis
                dataKey={figLang === 'th' ? 'label_th' : 'label_en'}
                stroke="#000000"
                strokeWidth={2}
                tick={{ fontSize: 11, fill: '#000000', fontWeight: 700 }}
                tickLine={{ stroke: '#000000', strokeWidth: 1.5 }}
                interval={Math.max(0, Math.floor(displayedWeeks.length / 14))}
                angle={-28}
                textAnchor="end"
              />
              <YAxis
                stroke="#000000"
                strokeWidth={2}
                tick={{ fontSize: 12, fill: '#000000', fontWeight: 700 }}
                tickLine={{ stroke: '#000000', strokeWidth: 1.5 }}
              />
              <Tooltip
                contentStyle={{
                  fontSize: 13,
                  borderRadius: 8,
                  border: '2px solid #000000',
                  boxShadow: '0 6px 16px -2px rgb(0 0 0 / 0.15)',
                  backgroundColor: '#ffffff',
                }}
              />

              {/* Vertical dotted lines separating each year */}
              {activeBoundaries.map((b) => (
                <ReferenceLine
                  key={`yr-line-${b.epi_year}-${b.t}`}
                  x={figLang === 'th' ? b.label_th : b.label_en}
                  stroke="#000000"
                  strokeDasharray="4 4"
                  strokeWidth={2}
                  label={{
                    value: figLang === 'th' ? `พ.ศ. ${b.year_be}` : `${b.epi_year}`,
                    position: 'top',
                    fill: '#000000',
                    fontSize: 12,
                    fontWeight: 800,
                  }}
                />
              ))}

              <Bar
                dataKey="opd_cases"
                stackId="epi"
                fill="#0284c7"
                stroke="#000000"
                strokeWidth={1}
                name={figLang === 'th' ? 'ผู้ป่วยนอก (OPD)' : 'OPD'}
              />
              <Bar
                dataKey="unknown_cases"
                stackId="epi"
                fill="#94a3b8"
                stroke="#000000"
                strokeWidth={1}
                name={figLang === 'th' ? 'ไม่ระบุประเภท (Unknown)' : 'Unknown'}
              />
              <Bar
                dataKey="ipd_cases"
                stackId="epi"
                fill="#0d9488"
                stroke="#000000"
                strokeWidth={1}
                name={figLang === 'th' ? 'ผู้ป่วยใน (IPD)' : 'IPD'}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-300 text-xs text-slate-700 flex items-start gap-2.5 font-medium">
          <Info className="w-4 h-4 text-slate-900 mt-0.5 flex-shrink-0" />
          <p className="leading-relaxed">
            {lang === 'th'
              ? 'เส้นประแนวตั้งระบุจุดเริ่มต้นของสัปดาห์แรกในแต่ละปีปฏิทินระบาดวิทยา (พ.ศ.) • สัดส่วนผู้ป่วยไม่ระบุประเภท (~52%) คงไว้ในกราฟแท่งเพื่อสะท้อนภาระงานจริง แต่ถูกแยกออกจากตัวหารในการคำนวณสัดส่วนการนอนโรงพยาบาล H / (H + O)'
              : 'Vertical dashed lines demarcate the start of epidemiological years • Unknown patient types are displayed to reflect actual notification volumes.'}
          </p>
        </div>
      </div>

      {/* NEW: Seasonal Comparison Line Graph (Last 2 Years vs. 5-Year Historical Median) in GraphPad Prism Style */}
      <div className="bg-white rounded-2xl border-2 border-slate-900 p-6 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b-2 border-slate-900 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-slate-900" />
              <h4 className="font-extrabold text-slate-950 text-base">
                {lang === 'th'
                  ? 'เปรียบเทียบฤดูกาล: 2 ปีล่าสุด vs มัธยฐาน 5 ปี (W01–W52)'
                  : 'Seasonal Comparison: Last 2 Years vs. 5-Year Median (W01–W52)'}
              </h4>
            </div>
            <p className="text-xs text-slate-600 font-semibold mt-0.5">
              {lang === 'th'
                ? `สัปดาห์ระบาดวิทยา W01–W52 เทียบปี ${prevYearBe || '-'}, ${latestYearBe || '-'} และมัธยฐาน 5 ปี`
                : `Weeks W01–W52 comparing ${prevYearBe || '-'}, ${latestYearBe || '-'} and 5-year median`}
            </p>
          </div>

          {/* Metric Toggle: Cases vs Incidence Rate */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-700">{lang === 'th' ? 'ตัวชี้วัด:' : 'Metric:'}</span>
            <div className="inline-flex rounded-lg bg-slate-100 p-1 border-2 border-slate-900">
              <button
                onClick={() => setSeasonalMetric('cases')}
                className={`px-3 py-1 rounded text-xs font-extrabold transition ${
                  seasonalMetric === 'cases' ? 'bg-slate-900 text-white shadow-xs' : 'text-slate-700 hover:text-slate-950'
                }`}
              >
                {lang === 'th' ? 'จำนวนผู้ป่วย (ราย)' : 'Cases'}
              </button>
              <button
                onClick={() => setSeasonalMetric('rate')}
                disabled={!seasonalData?.has_rate}
                className={`px-3 py-1 rounded text-xs font-extrabold transition ${
                  seasonalMetric === 'rate'
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'text-slate-700 hover:text-slate-950 disabled:opacity-40'
                }`}
                title={!seasonalData?.has_rate ? (lang === 'th' ? 'ไม่มีตัวหารประชากรสำหรับขอบเขตนี้' : 'No population denominator') : ''}
              >
                {lang === 'th' ? 'อุบัติการณ์/แสน' : 'Incidence / 100k'}
              </button>
            </div>
          </div>
        </div>

        {/* Legend / Series Badges in GraphPad Prism Style */}
        <div className="flex flex-wrap items-center gap-6 text-xs font-bold bg-slate-50 border border-slate-300 p-3 rounded-xl">
          <div className="flex items-center gap-2 text-slate-900">
            <span className="w-3 h-3 rounded-full bg-[#dc2626] border border-slate-900 inline-block" />
            <span>
              {lang === 'th' ? `● ปีล่าสุด (พ.ศ. ${latestYearBe || '-'})` : `● Latest Year (${seasonalData?.latest_year || '-'})`}
            </span>
          </div>

          <div className="flex items-center gap-2 text-slate-900">
            <span className="w-3 h-3 rounded-none bg-[#2563eb] border border-slate-900 inline-block" />
            <span>
              {lang === 'th' ? `■ ปีก่อนหน้า (พ.ศ. ${prevYearBe || '-'})` : `■ Previous Year (${seasonalData?.prev_year || '-'})`}
            </span>
          </div>

          <div className="flex items-center gap-2 text-slate-900">
            <span className="inline-block text-base leading-none text-slate-950">▲</span>
            <span>
              {lang === 'th'
                ? `▲ ค่ามัธยฐาน 5 ปีย้อนหลัง (5-Year Historical Median: ${seasonalData?.median_years_used?.map((y: number) => y + 543).join(', ') || '-'})`
                : `▲ 5-Year Historical Median (${seasonalData?.median_years_used?.join(', ') || '-'})`}
            </span>
          </div>
        </div>

        {/* GraphPad Prism Styled Line Chart */}
        <div className="h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={seasonalChartData} margin={{ top: 20, right: 30, left: 10, bottom: 25 }}>
              {/* Prism theme: open top/right, tick styling, no heavy grid */}
              <CartesianGrid strokeDasharray="0" stroke="#f1f5f9" vertical={false} />
              <XAxis
                dataKey="week_label"
                stroke="#000000"
                strokeWidth={2}
                tick={{ fontSize: 11, fill: '#000000', fontWeight: 700 }}
                tickLine={{ stroke: '#000000', strokeWidth: 1.5 }}
                interval={3}
              />
              <YAxis
                stroke="#000000"
                strokeWidth={2}
                tick={{ fontSize: 12, fill: '#000000', fontWeight: 700 }}
                tickLine={{ stroke: '#000000', strokeWidth: 1.5 }}
                domain={[0, 'auto']}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const d = payload[0].payload;
                    return (
                      <div className="bg-white p-3 rounded-lg border-2 border-slate-900 shadow-xl text-xs space-y-1.5">
                        <p className="font-extrabold text-slate-950 border-b border-slate-200 pb-1">
                          {figLang === 'th' ? `สัปดาห์ระบาดวิทยา W${String(d.epi_week).padStart(2, '0')}` : `Epidemiological Week W${String(d.epi_week).padStart(2, '0')}`}
                        </p>
                        <p className="text-[#dc2626] font-bold">
                          {figLang === 'th' ? `ปีล่าสุด (พ.ศ. ${latestYearBe}):` : `Latest (${seasonalData?.latest_year}):`}{' '}
                          {d.raw_cases_latest !== null ? (
                            seasonalMetric === 'cases'
                              ? `${d.raw_cases_latest.toLocaleString()} ราย`
                              : `${Number(d.raw_rate_latest).toFixed(2)} ต่อแสน`
                          ) : (
                            <span className="text-slate-400 font-normal">ยังไม่มีข้อมูล / Incomplete</span>
                          )}
                        </p>
                        <p className="text-[#2563eb] font-bold">
                          {figLang === 'th' ? `ปีก่อนหน้า (พ.ศ. ${prevYearBe}):` : `Previous (${seasonalData?.prev_year}):`}{' '}
                          {d.raw_cases_prev !== null ? (
                            seasonalMetric === 'cases'
                              ? `${d.raw_cases_prev.toLocaleString()} ราย`
                              : `${Number(d.raw_rate_prev).toFixed(2)} ต่อแสน`
                          ) : (
                            <span className="text-slate-400 font-normal">-</span>
                          )}
                        </p>
                        <p className="text-slate-950 font-extrabold">
                          {figLang === 'th' ? 'ค่ามัธยฐาน 5 ปี (5-Yr Median):' : '5-Year Median:'}{' '}
                          {d.raw_cases_median !== null ? (
                            seasonalMetric === 'cases'
                              ? `${d.raw_cases_median.toLocaleString()} ราย`
                              : `${Number(d.raw_rate_median).toFixed(2)} ต่อแสน`
                          ) : (
                            <span className="text-slate-400 font-normal">-</span>
                          )}
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />

              {/* 5-Year Historical Median: Black Dotted Line with Triangle markers */}
              <Line
                type="linear"
                dataKey="median_val"
                stroke="#000000"
                strokeWidth={2.4}
                strokeDasharray="4 4"
                dot={{ r: 4, fill: '#000000', stroke: '#000000', strokeWidth: 1 }}
                activeDot={{ r: 6 }}
                connectNulls={true}
                name={figLang === 'th' ? 'ค่ามัธยฐาน 5 ปีย้อนหลัง' : '5-Year Median'}
              />

              {/* Previous Year: Blue Line with Square markers */}
              <Line
                type="linear"
                dataKey="prev_val"
                stroke="#2563eb"
                strokeWidth={2.2}
                dot={{ r: 4, fill: '#2563eb', stroke: '#000000', strokeWidth: 1 }}
                activeDot={{ r: 6 }}
                connectNulls={true}
                name={figLang === 'th' ? `พ.ศ. ${prevYearBe}` : `Year ${seasonalData?.prev_year}`}
              />

              {/* Latest Year: Bold Red Line with Circle markers */}
              <Line
                type="linear"
                dataKey="latest_val"
                stroke="#dc2626"
                strokeWidth={2.8}
                dot={{ r: 4.5, fill: '#dc2626', stroke: '#000000', strokeWidth: 1 }}
                activeDot={{ r: 7 }}
                connectNulls={false}
                name={figLang === 'th' ? `พ.ศ. ${latestYearBe}` : `Year ${seasonalData?.latest_year}`}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-300 text-xs text-slate-700 space-y-1 font-medium">
          <p>
            • {lang === 'th' ? seasonalData?.note_th : seasonalData?.note_en}
          </p>
          <p className="text-slate-500">
            • {lang === 'th'
              ? 'กราฟเส้นเปรียบเทียบฤดูกาลถูกรวมไว้เป็น Figure 8 ใน Presentation Studio และชุดไฟล์ส่งออกสไลด์ 4K (DDS_OneClick_Presentation_Pack.zip)'
              : 'Seasonal comparison is exported as Figure 8 in Presentation Studio and the 4K Presentation Pack.'}
          </p>
        </div>
      </div>

      {/* Reporting Completeness Lag & Calendar Index Table */}
      <div className="bg-white rounded-2xl border-2 border-slate-900 p-6 shadow-xs space-y-4">
        <h4 className="font-extrabold text-slate-950 text-sm">
          {lang === 'th' ? 'ดัชนีเวลาต่อเนื่อง (Continuous Time Index t) และความล่าช้าในการรายงาน' : 'Continuous Chronological Time Index & Reporting Lag'}
        </h4>

        <div className="overflow-x-auto max-h-72 border-2 border-slate-900 rounded-xl">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-100 border-b-2 border-slate-900 text-slate-900 font-bold sticky top-0">
              <tr>
                <th className="py-2.5 px-3">t</th>
                <th className="py-2.5 px-3">{lang === 'th' ? 'ปี/สัปดาห์' : 'Year/Wk'}</th>
                <th className="py-2.5 px-3">{lang === 'th' ? 'วันเริ่มต้น - วันสิ้นสุด' : 'Interval'}</th>
                <th className="py-2.5 px-3 text-right">{lang === 'th' ? 'ผู้ป่วยรวม (ราย)' : 'Total Cases'}</th>
                <th className="py-2.5 px-3 text-right">IPD (H)</th>
                <th className="py-2.5 px-3 text-right">OPD (O)</th>
                <th className="py-2.5 px-3 text-right">{lang === 'th' ? 'ไม่ระบุ (U)' : 'Unknown'}</th>
                <th className="py-2.5 px-3 text-right">{lang === 'th' ? 'สัดส่วน IPD (%)' : 'IPD %'}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 font-mono font-medium">
              {weeks.slice().reverse().map((w) => {
                const known = w.ipd_cases + w.opd_cases;
                const hp = known > 0 ? (w.ipd_cases / known * 100).toFixed(1) : '0.0';
                return (
                  <tr key={w.t} className="hover:bg-slate-50">
                    <td className="py-2 px-3 text-slate-500">{w.t}</td>
                    <td className="py-2 px-3 font-bold text-slate-950">W{String(w.epi_week).padStart(2, '0')}/{w.epi_year}</td>
                    <td className="py-2 px-3 font-sans text-slate-700">{w.week_start} ถึง {w.week_end}</td>
                    <td className="py-2 px-3 text-right font-extrabold text-slate-950">{w.total_cases.toLocaleString()}</td>
                    <td className="py-2 px-3 text-right text-teal-800 font-bold">{w.ipd_cases.toLocaleString()}</td>
                    <td className="py-2 px-3 text-right text-blue-800 font-bold">{w.opd_cases.toLocaleString()}</td>
                    <td className="py-2 px-3 text-right text-slate-500">{w.unknown_cases.toLocaleString()}</td>
                    <td className="py-2 px-3 text-right font-bold text-slate-900">{hp}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
