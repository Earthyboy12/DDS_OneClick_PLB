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
  Loader2,
  AlertCircle,
  RefreshCw,
  Sparkles,
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
  ComposedChart,
} from 'recharts';

export const TimePage: React.FC = () => {
  const { lang, figLang, setActiveTab, isLoaded, filterVersion, loadSynthetic } = useApp();
  const [weeks, setWeeks] = useState<any[]>([]);
  const [yearBoundaries, setYearBoundaries] = useState<any[]>([]);
  const [seasonalData, setSeasonalData] = useState<any | null>(null);
  const [selectedView, setSelectedView] = useState<'all' | 'recent52' | 'recent26' | 'recent12'>('all');
  const [seasonalMetric, setSeasonalMetric] = useState<'cases' | 'rate'>('cases');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState<boolean>(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const fetchData = (force: boolean = false) => {
    if (!isLoaded) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    getTimeEpicurve(force)
      .then((res) => {
        setWeeks(res.weeks || []);
        setYearBoundaries(res.year_boundaries || []);
        setSeasonalData(res.seasonal_comparison || null);
      })
      .catch((err) => {
        console.error('Failed to load epicurve data:', err);
        setError(err?.message || 'ไม่สามารถโหลดข้อมูลสัปดาห์ระบาดวิทยาได้');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchData(false);
  }, [isLoaded, filterVersion]);

  const displayedWeeks = useMemo(() => {
    if (!weeks.length) return [];
    if (selectedView === 'recent12') return weeks.slice(-12);
    if (selectedView === 'recent26') return weeks.slice(-26);
    if (selectedView === 'recent52') return weeks.slice(-52);
    return weeks;
  }, [weeks, selectedView]);

  const activeBoundaries = useMemo(() => {
    if (!displayedWeeks.length || !yearBoundaries.length) return [];
    const minT = displayedWeeks[0].t;
    const maxT = displayedWeeks[displayedWeeks.length - 1].t;
    return yearBoundaries.filter((b) => b.t >= minT && b.t <= maxT);
  }, [displayedWeeks, yearBoundaries]);

  const seasonalChartData = useMemo(() => {
    if (!seasonalData || !seasonalData.weeks) return [];
    return seasonalData.weeks.map((w: any) => ({
      epi_week: w.epi_week,
      week_label: `W${String(w.epi_week).padStart(2, '0')}`,
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
  }, [seasonalData, seasonalMetric]);

  const latestYearBe = seasonalData?.latest_year_be || (seasonalData?.latest_year ? seasonalData.latest_year + 543 : null);
  const prevYearBe = seasonalData?.prev_year_be || (seasonalData?.prev_year ? seasonalData.prev_year + 543 : null);

  // If no dataset loaded
  if (!isLoaded) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200/90 p-12 text-center max-w-xl mx-auto shadow-xs space-y-4 my-8">
        <div className="w-14 h-14 rounded-2xl bg-teal-50 text-teal-600 flex items-center justify-center mx-auto">
          <TrendingUp className="w-7 h-7" />
        </div>
        <h3 className="text-base font-bold text-slate-800">
          {lang === 'th' ? 'ยังไม่ได้โหลดชุดข้อมูลระบาดวิทยา' : 'No Surveillance Dataset Loaded'}
        </h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
          {lang === 'th'
            ? 'กรุณานำเข้าไฟล์ Excel/CSV ข้อมูล DDS หรือกดปุ่มด้านล่างเพื่อสร้างข้อมูลสังเคราะห์เพื่อเริ่มวิเคราะห์กราฟการระบาด'
            : 'Please import DDS Excel/CSV files or load synthetic reference data to analyze the epidemic curve.'}
        </p>
        <div className="pt-2">
          <button
            onClick={loadSynthetic}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-teal-700 to-teal-600 text-white text-xs font-semibold hover:from-teal-800 hover:to-teal-700 shadow-sm transition"
          >
            <Sparkles className="w-4 h-4" />
            <span>{lang === 'th' ? 'สร้างข้อมูลสังเคราะห์เพื่อทดสอบ' : 'Load Synthetic Demo'}</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header controls card */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-teal-600" />
            <h3 className="font-bold text-slate-900 text-base">
              {lang === 'th' ? 'แนวโน้มการระบาดตามเวลา (Time Trends & Epicurve)' : 'Surveillance Time Trends'}
            </h3>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            {lang === 'th'
              ? 'กราฟการระบาดรายสัปดาห์ (Epi Week) และการเปรียบเทียบแนวโน้มเชิงฤดูกาล'
              : 'Weekly epidemiological trends and multi-year seasonal comparisons.'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* View Filter */}
          <div className="flex items-center bg-slate-100 p-1 rounded-xl text-xs font-medium border border-slate-200">
            <button
              onClick={() => setSelectedView('all')}
              className={`px-3 py-1.5 rounded-lg transition ${
                selectedView === 'all'
                  ? 'bg-white text-slate-900 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {lang === 'th' ? 'ทั้งหมด' : 'All Weeks'}
            </button>
            <button
              onClick={() => setSelectedView('recent52')}
              className={`px-3 py-1.5 rounded-lg transition ${
                selectedView === 'recent52'
                  ? 'bg-white text-slate-900 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {lang === 'th' ? '52 สัปดาห์' : '52 Wks'}
            </button>
            <button
              onClick={() => setSelectedView('recent26')}
              className={`px-3 py-1.5 rounded-lg transition ${
                selectedView === 'recent26'
                  ? 'bg-white text-slate-900 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {lang === 'th' ? '26 สัปดาห์' : '26 Wks'}
            </button>
            <button
              onClick={() => setSelectedView('recent12')}
              className={`px-3 py-1.5 rounded-lg transition ${
                selectedView === 'recent12'
                  ? 'bg-white text-slate-900 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {lang === 'th' ? '12 สัปดาห์' : '12 Wks'}
            </button>
          </div>

          <button
            onClick={() => fetchData(true)}
            title={lang === 'th' ? 'รีเฟรชกราฟ' : 'Refresh chart'}
            className="p-2 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-teal-600' : ''}`} />
          </button>

          <button
            onClick={() => setActiveTab('studio')}
            className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold transition flex items-center gap-1.5 shadow-xs"
          >
            <Presentation className="w-3.5 h-3.5" />
            <span>{lang === 'th' ? 'ห้องจัดสไลด์' : 'Slide Studio'}</span>
          </button>
        </div>
      </div>

      {/* Error state if fetch failed */}
      {error && !weeks.length && (
        <div className="p-6 bg-rose-50 border border-rose-200 rounded-2xl flex items-center justify-between gap-4 shadow-xs">
          <div className="flex items-center gap-3 text-rose-800 text-xs font-medium">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => fetchData(true)}
            className="px-3 py-1.5 rounded-lg bg-rose-600 text-white text-xs font-semibold hover:bg-rose-700 transition"
          >
            {lang === 'th' ? 'ลองใหม่อีกครั้ง' : 'Retry'}
          </button>
        </div>
      )}

      {/* Main Interactive Stacked Epidemic Chart */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-slate-900">
                {lang === 'th'
                  ? `กราฟการระบาดรายสัปดาห์ (${displayedWeeks.length} สัปดาห์)`
                  : `Weekly Epidemic Curve (${displayedWeeks.length} weeks)`}
              </span>
            </div>
            <p className="text-xs text-slate-500">
              {lang === 'th'
                ? 'เส้นประแนวตั้งแบ่งตามปีปฏิทินระบาดวิทยา'
                : 'Vertical dotted lines demarcating calendar years'}
            </p>
          </div>

          <div className="flex items-center gap-4 text-xs font-medium">
            <span className="inline-flex items-center gap-1.5 text-slate-700">
              <span className="w-3 h-3 rounded-xs bg-[#0284c7]" />
              {lang === 'th' ? 'ผู้ป่วยนอก (OPD)' : 'OPD'}
            </span>
            <span className="inline-flex items-center gap-1.5 text-slate-700">
              <span className="w-3 h-3 rounded-xs bg-[#cbd5e1]" />
              {lang === 'th' ? 'ไม่ระบุประเภท (Unknown)' : 'Unknown'}
            </span>
            <span className="inline-flex items-center gap-1.5 text-slate-700">
              <span className="w-3 h-3 rounded-xs bg-[#0d9488]" />
              {lang === 'th' ? 'ผู้ป่วยใน (IPD)' : 'IPD'}
            </span>
            <span className="inline-flex items-center gap-1.5 text-slate-500">
              <span className="w-4 h-0 border-t border-dashed border-slate-400" />
              {lang === 'th' ? 'เส้นแบ่งปี' : 'Year Line'}
            </span>
          </div>
        </div>

        {/* Loading Spinner / Skeleton */}
        {loading && !weeks.length ? (
          <div className="h-[380px] flex flex-col items-center justify-center text-slate-400 space-y-2.5">
            <Loader2 className="w-7 h-7 animate-spin text-teal-600" />
            <p className="text-xs font-medium text-slate-600">
              {lang === 'th' ? 'กำลังประมวลผลข้อมูลสัปดาห์ระบาดวิทยา...' : 'Processing weekly epidemic data...'}
            </p>
          </div>
        ) : displayedWeeks.length > 0 && isMounted ? (
          <div className="h-[400px] w-full min-w-0">
            <ResponsiveContainer width="100%" height={390} minWidth={280}>
              <BarChart data={displayedWeeks} margin={{ top: 20, right: 20, left: -5, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis
                  dataKey={figLang === 'th' ? 'label_th' : 'label_en'}
                  stroke="#94a3b8"
                  strokeWidth={1}
                  tick={{ fontSize: 10, fill: '#64748b' }}
                  tickLine={{ stroke: '#cbd5e1' }}
                  interval={Math.max(0, Math.floor(displayedWeeks.length / 14))}
                  angle={-28}
                  textAnchor="end"
                />
                <YAxis
                  stroke="#94a3b8"
                  strokeWidth={1}
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickLine={{ stroke: '#cbd5e1' }}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const d = payload[0].payload;
                      return (
                        <div className="bg-white/95 backdrop-blur-xs p-3 rounded-xl border border-slate-200 shadow-lg text-xs space-y-1">
                          <p className="font-bold text-slate-900 border-b border-slate-100 pb-1">
                            {figLang === 'th' ? d.label_th : d.label_en} ({d.week_start} ถึง {d.week_end})
                          </p>
                          <p className="text-slate-900 font-semibold">
                            {lang === 'th' ? 'ผู้ป่วยรวม:' : 'Total Cases:'} {d.total_cases.toLocaleString()} ราย
                          </p>
                          <div className="text-xs text-slate-600 space-y-0.5 pt-0.5">
                            <p className="text-teal-700 font-medium">IPD: {d.ipd_cases.toLocaleString()}</p>
                            <p className="text-sky-700 font-medium">OPD: {d.opd_cases.toLocaleString()}</p>
                            <p className="text-slate-500">Unknown: {d.unknown_cases.toLocaleString()}</p>
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />

                {/* Vertical dotted lines separating each year */}
                {activeBoundaries.map((b) => (
                  <ReferenceLine
                    key={`yr-line-${b.epi_year}-${b.t}`}
                    x={figLang === 'th' ? b.label_th : b.label_en}
                    stroke="#94a3b8"
                    strokeDasharray="4 4"
                    strokeWidth={1.5}
                    label={{
                      value: figLang === 'th' ? `พ.ศ. ${b.year_be}` : `${b.epi_year}`,
                      position: 'top',
                      fill: '#475569',
                      fontSize: 11,
                      fontWeight: 600,
                    }}
                  />
                ))}

                <Bar
                  dataKey="opd_cases"
                  stackId="epi"
                  fill="#0284c7"
                  name={figLang === 'th' ? 'ผู้ป่วยนอก (OPD)' : 'OPD'}
                />
                <Bar
                  dataKey="unknown_cases"
                  stackId="epi"
                  fill="#cbd5e1"
                  name={figLang === 'th' ? 'ไม่ระบุประเภท (Unknown)' : 'Unknown'}
                />
                <Bar
                  dataKey="ipd_cases"
                  stackId="epi"
                  fill="#0d9488"
                  radius={[3, 3, 0, 0]}
                  name={figLang === 'th' ? 'ผู้ป่วยใน (IPD)' : 'IPD'}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-[280px] flex items-center justify-center text-slate-400 text-xs">
            {lang === 'th' ? 'ไม่มีข้อมูลสัปดาห์ระบาดวิทยาตามเงื่อนไขที่เลือก' : 'No epidemic week data for current filters.'}
          </div>
        )}

        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-600 flex items-start gap-2">
          <Info className="w-4 h-4 text-teal-600 mt-0.5 flex-shrink-0" />
          <p className="leading-relaxed">
            {lang === 'th'
              ? 'เส้นประแนวตั้งระบุจุดเริ่มต้นของสัปดาห์แรกในแต่ละปีปฏิทินระบาดวิทยา (พ.ศ.) • สัดส่วนผู้ป่วยไม่ระบุประเภทแสดงไว้เพื่อสะท้อนภาระงานจริง แต่ถูกแยกออกจากตัวหารในการคำนวณสัดส่วนการนอนโรงพยาบาล H / (H + O)'
              : 'Vertical dashed lines demarcate the start of epidemiological years • Unknown patient types are displayed to reflect actual notification volumes.'}
          </p>
        </div>
      </div>

      {/* Seasonal Comparison Line Graph */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-teal-600" />
              <h4 className="font-bold text-slate-900 text-sm">
                {lang === 'th'
                  ? 'เปรียบเทียบเชิงฤดูกาล: 2 ปีล่าสุด vs มัธยฐาน 5 ปี (W01–W52)'
                  : 'Seasonal Comparison: Last 2 Years vs. 5-Year Median (W01–W52)'}
              </h4>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {lang === 'th'
                ? `สัปดาห์ระบาดวิทยา W01–W52 เทียบปี ${prevYearBe || '-'}, ${latestYearBe || '-'} และมัธยฐาน 5 ปีย้อนหลัง`
                : `Weeks W01–W52 comparing ${prevYearBe || '-'}, ${latestYearBe || '-'} and 5-year median`}
            </p>
          </div>

          {/* Metric Toggle: Cases vs Incidence Rate */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-500">{lang === 'th' ? 'ตัวชี้วัด:' : 'Metric:'}</span>
            <div className="inline-flex rounded-xl bg-slate-100 p-1 border border-slate-200">
              <button
                onClick={() => setSeasonalMetric('cases')}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                  seasonalMetric === 'cases'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {lang === 'th' ? 'จำนวนผู้ป่วย (ราย)' : 'Cases'}
              </button>
              <button
                onClick={() => setSeasonalMetric('rate')}
                disabled={!seasonalData?.has_rate}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                  seasonalMetric === 'rate'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 disabled:opacity-40'
                }`}
                title={!seasonalData?.has_rate ? (lang === 'th' ? 'ไม่มีตัวหารประชากรสำหรับขอบเขตนี้' : 'No population denominator') : ''}
              >
                {lang === 'th' ? 'อัตราป่วย/แสน' : 'Rate / 100k'}
              </button>
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-5 text-xs font-medium bg-slate-50 border border-slate-200/80 p-2.5 rounded-xl">
          <div className="flex items-center gap-2 text-slate-800">
            <span className="w-2.5 h-2.5 rounded-full bg-[#dc2626] inline-block" />
            <span>
              {lang === 'th' ? `ปีล่าสุด (พ.ศ. ${latestYearBe || '-'})` : `Latest (${seasonalData?.latest_year || '-'})`}
            </span>
          </div>

          <div className="flex items-center gap-2 text-slate-800">
            <span className="w-2.5 h-2.5 rounded-xs bg-[#2563eb] inline-block" />
            <span>
              {lang === 'th' ? `ปีก่อนหน้า (พ.ศ. ${prevYearBe || '-'})` : `Previous (${seasonalData?.prev_year || '-'})`}
            </span>
          </div>

          <div className="flex items-center gap-2 text-slate-800">
            <span className="w-3.5 h-3 rounded-xs bg-[#cbd5e1] border border-[#94a3b8] inline-block" />
            <span>
              {lang === 'th'
                ? `มัธยฐาน 5 ปีย้อนหลัง (กราฟแท่ง) (${seasonalData?.median_years_used?.map((y: number) => y + 543).join(', ') || '-'})`
                : `5-Yr Median (Bar) (${seasonalData?.median_years_used?.join(', ') || '-'})`}
            </span>
          </div>
        </div>

        {/* Seasonal Comparison Composed Chart (Grey Bars for Median, Lines for 1 & 2 Years) */}
        {seasonalChartData.length > 0 && isMounted ? (
          <div className="h-[380px] w-full min-w-0">
            <ResponsiveContainer width="100%" height={370} minWidth={280}>
              <ComposedChart data={seasonalChartData} margin={{ top: 15, right: 20, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis
                  dataKey="week_label"
                  stroke="#94a3b8"
                  strokeWidth={1}
                  tick={{ fontSize: 10, fill: '#64748b' }}
                  tickLine={{ stroke: '#cbd5e1' }}
                  interval={3}
                />
                <YAxis
                  stroke="#94a3b8"
                  strokeWidth={1}
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickLine={{ stroke: '#cbd5e1' }}
                  domain={[0, 'auto']}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const d = payload[0].payload;
                      return (
                        <div className="bg-white/95 backdrop-blur-xs p-3 rounded-xl border border-slate-200 shadow-lg text-xs space-y-1.5">
                          <p className="font-bold text-slate-900 border-b border-slate-100 pb-1">
                            {figLang === 'th' ? `สัปดาห์ระบาดวิทยา W${String(d.epi_week).padStart(2, '0')}` : `Epidemiological Week W${String(d.epi_week).padStart(2, '0')}`}
                          </p>
                          <p className="text-[#dc2626] font-semibold">
                            {figLang === 'th' ? `ปีล่าสุด (พ.ศ. ${latestYearBe}):` : `Latest (${seasonalData?.latest_year}):`}{' '}
                            {d.raw_cases_latest !== null ? (
                              seasonalMetric === 'cases'
                                ? `${d.raw_cases_latest.toLocaleString()} ราย`
                                : `${Number(d.raw_rate_latest).toFixed(2)} ต่อแสน`
                            ) : (
                              <span className="text-slate-400 font-normal">ยังไม่มีข้อมูล</span>
                            )}
                          </p>
                          <p className="text-[#2563eb] font-semibold">
                            {figLang === 'th' ? `ปีก่อนหน้า (พ.ศ. ${prevYearBe}):` : `Previous (${seasonalData?.prev_year}):`}{' '}
                            {d.raw_cases_prev !== null ? (
                              seasonalMetric === 'cases'
                                ? `${d.raw_cases_prev.toLocaleString()} ราย`
                                : `${Number(d.raw_rate_prev).toFixed(2)} ต่อแสน`
                            ) : (
                              <span className="text-slate-400 font-normal">-</span>
                            )}
                          </p>
                          <p className="text-slate-700 font-semibold">
                            {figLang === 'th' ? 'มัธยฐาน 5 ปีย้อนหลัง (แท่งสีเทา):' : '5-Year Median (Grey Bar):'}{' '}
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

                {/* 5-Year Median as grey bar */}
                <Bar
                  dataKey="median_val"
                  fill="#cbd5e1"
                  stroke="#94a3b8"
                  strokeWidth={1}
                  radius={[2, 2, 0, 0]}
                  name={figLang === 'th' ? 'มัธยฐาน 5 ปี (กราฟแท่ง)' : '5-Year Median (Bar)'}
                />

                {/* Previous year as blue line */}
                <Line
                  type="monotone"
                  dataKey="prev_val"
                  stroke="#2563eb"
                  strokeWidth={2}
                  dot={{ r: 3, fill: '#2563eb' }}
                  connectNulls={true}
                  name={figLang === 'th' ? `พ.ศ. ${prevYearBe}` : `Year ${seasonalData?.prev_year}`}
                />

                {/* Latest year as crimson red line */}
                <Line
                  type="monotone"
                  dataKey="latest_val"
                  stroke="#dc2626"
                  strokeWidth={2.5}
                  dot={{ r: 3.5, fill: '#dc2626' }}
                  connectNulls={false}
                  name={figLang === 'th' ? `พ.ศ. ${latestYearBe}` : `Year ${seasonalData?.latest_year}`}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-[220px] flex items-center justify-center text-slate-400 text-xs">
            {lang === 'th' ? 'ไม่มีข้อมูลเปรียบเทียบเชิงฤดูกาล' : 'No seasonal data available.'}
          </div>
        )}

        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-600 space-y-0.5">
          <p>• {lang === 'th' ? seasonalData?.note_th : seasonalData?.note_en}</p>
        </div>
      </div>

      {/* Reporting Completeness Lag & Calendar Index Table */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs space-y-3">
        <h4 className="font-bold text-slate-900 text-sm">
          {lang === 'th' ? 'ดัชนีเวลาต่อเนื่อง (Continuous Time Index t) และความล่าช้าในการรายงาน' : 'Continuous Chronological Time Index & Reporting Lag'}
        </h4>

        <div className="overflow-x-auto max-h-72 border border-slate-200 rounded-xl">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold sticky top-0">
              <tr>
                <th className="py-2.5 px-3">t</th>
                <th className="py-2.5 px-3">{lang === 'th' ? 'ปี/สัปดาห์' : 'Year/Wk'}</th>
                <th className="py-2.5 px-3">{lang === 'th' ? 'ช่วงวันเริ่มป่วย - สิ้นสุด' : 'Interval'}</th>
                <th className="py-2.5 px-3 text-right">{lang === 'th' ? 'ผู้ป่วยรวม (ราย)' : 'Total Cases'}</th>
                <th className="py-2.5 px-3 text-right">IPD (H)</th>
                <th className="py-2.5 px-3 text-right">OPD (O)</th>
                <th className="py-2.5 px-3 text-right">{lang === 'th' ? 'ไม่ระบุ (U)' : 'Unknown'}</th>
                <th className="py-2.5 px-3 text-right">{lang === 'th' ? 'สัดส่วน IPD (%)' : 'IPD %'}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-slate-700">
              {weeks.slice().reverse().map((w) => {
                const known = w.ipd_cases + w.opd_cases;
                const hp = known > 0 ? ((w.ipd_cases / known) * 100).toFixed(1) : '0.0';
                return (
                  <tr key={w.t} className="hover:bg-slate-50/80 transition">
                    <td className="py-2 px-3 text-slate-400">{w.t}</td>
                    <td className="py-2 px-3 font-semibold text-slate-900">
                      W{String(w.epi_week).padStart(2, '0')}/{w.epi_year}
                    </td>
                    <td className="py-2 px-3 font-sans text-slate-600">{w.week_start} ถึง {w.week_end}</td>
                    <td className="py-2 px-3 text-right font-bold text-slate-900">{w.total_cases.toLocaleString()}</td>
                    <td className="py-2 px-3 text-right text-teal-700 font-medium">{w.ipd_cases.toLocaleString()}</td>
                    <td className="py-2 px-3 text-right text-sky-700 font-medium">{w.opd_cases.toLocaleString()}</td>
                    <td className="py-2 px-3 text-right text-slate-400">{w.unknown_cases.toLocaleString()}</td>
                    <td className="py-2 px-3 text-right font-semibold text-slate-800">{hp}%</td>
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
