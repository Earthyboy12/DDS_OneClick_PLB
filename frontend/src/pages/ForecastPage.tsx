import React, { useEffect, useState } from 'react';
import {
  Presentation,
  Info,
  Calendar,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { runForecast } from '../services/api';
import { ForecastResult } from '../types';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

export const ForecastPage: React.FC = () => {
  const { lang, figLang, setActiveTab, isLoaded, filterVersion } = useApp();
  const [horizon, setHorizon] = useState<number>(4);
  const [lagExclude, setLagExclude] = useState<number>(1);
  const [result, setResult] = useState<ForecastResult | null>(null);

  const fetchForecast = () => {
    runForecast(horizon, lagExclude, false)
      .then(setResult)
      .catch((err) => {
        setResult({
          status: 'unavailable',
          reason: err.message,
        });
      });
  };

  useEffect(() => {
    if (isLoaded) {
      fetchForecast();
    }
  }, [isLoaded, horizon, lagExclude, filterVersion]);

  const chartPoints = React.useMemo(() => {
    if (!result || result.status !== 'success' || !result.history) return [];
    const hist = result.history.map((h) => ({
      ...h,
      obs_val: h.observed,
      lag_val: null,
      fit_val: h.fitted_clipped,
      fc_val: null,
      pi_95_high: null,
      pi_80_high: null,
    }));

    const lagPts = (result.lag_excluded || []).map((l) => ({
      ...l,
      obs_val: null,
      lag_val: l.observed,
      fit_val: null,
      fc_val: null,
      pi_95_high: null,
      pi_80_high: null,
    }));

    const fc = (result.forecasts || []).map((f) => ({
      ...f,
      obs_val: null,
      lag_val: null,
      fit_val: null,
      fc_val: f.fitted_clipped,
      pi_95_low: Math.max(0, f.pi_95_lower || 0),
      pi_95_high: Math.max(0, f.pi_95_upper || 0),
      pi_80_low: Math.max(0, f.pi_80_lower || 0),
      pi_80_high: Math.max(0, f.pi_80_upper || 0),
    }));

    return [...hist, ...lagPts, ...fc];
  }, [result]);

  return (
    <div className="space-y-6">
      {/* Forecast Controls Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h3 className="font-bold text-slate-800 text-base">
              {lang === 'th'
                ? 'การพยากรณ์จำนวนผู้ป่วยรายสัปดาห์ (Linear Regression <= 52 สัปดาห์สมบูรณ์ล่าสุด)'
                : 'Weekly Epidemiological Forecast (Linear Regression <= 52 Complete Weeks)'}
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {lang === 'th'
                ? 'โมเดล Linear Regression (weekly_cases = beta0 + beta1 * t) จากไม่เกิน 52 สัปดาห์สมบูรณ์ล่าสุดก่อนจุดตัดข้อมูล พร้อม 80% และ 95% PI'
                : 'Linear regression trend model (weekly_cases = beta0 + beta1 * t) fitted on at most the latest 52 complete weeks.'}
            </p>
          </div>

          <button
            onClick={() => setActiveTab('studio')}
            className="px-3.5 py-1.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-medium transition flex items-center gap-1.5"
          >
            <Presentation className="w-3.5 h-3.5" />
            <span>{lang === 'th' ? 'สไลด์ Forecast 4K' : 'Forecast Slide'}</span>
          </button>
        </div>

        {/* Training Window Disclosure Banner */}
        {result && result.status === 'success' && (
          <div className="p-3 rounded-xl bg-teal-50/80 border border-teal-200 text-xs text-teal-950 flex items-center gap-2.5">
            <Calendar className="w-4 h-4 text-teal-700 flex-shrink-0" />
            <div>
              <span className="font-bold">
                {lang === 'th' ? 'ช่วงข้อมูลฝึกสอนจริง (Training Window): ' : 'Actual Training Window: '}
              </span>
              <span>
                {lang === 'th' ? result.training_window_note_th : result.training_window_note_en}
              </span>
            </div>
          </div>
        )}

        {/* Sliders & Toggles */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-3 border-t border-slate-100 text-xs">
          <div className="space-y-1">
            <div className="flex items-center justify-between font-semibold text-slate-700">
              <span>{lang === 'th' ? 'ระยะเวลาพยากรณ์ล่วงหน้า (Horizon):' : 'Forecast Horizon:'}</span>
              <span className="font-mono text-teal-700 font-bold">
                {horizon} {lang === 'th' ? 'สัปดาห์' : 'weeks'}
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={12}
              value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))}
              className="w-full accent-teal-600"
            />
            <div className="flex justify-between text-[10px] text-slate-400 font-mono">
              <span>1 wk</span>
              <span>4 wks (Def)</span>
              <span>12 wks</span>
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between font-semibold text-slate-700">
              <span>
                {lang === 'th'
                  ? 'ตัดสัปดาห์ล่าสุดที่รายงานยังไม่ครบ (Completeness Lag):'
                  : 'Reporting Completeness Lag Exclusion:'}
              </span>
              <span className="font-mono text-slate-700 font-bold">
                {lagExclude} {lang === 'th' ? 'สัปดาห์' : 'wks'}
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={4}
              value={lagExclude}
              onChange={(e) => setLagExclude(Number(e.target.value))}
              className="w-full accent-teal-600"
            />
            <div className="flex justify-between text-[10px] text-slate-400 font-mono">
              <span>0 (Keep all)</span>
              <span>1 wk (Recommended)</span>
              <span>4 wks</span>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200">
            <div>
              <span className="font-semibold text-slate-800 block text-xs">
                {lang === 'th' ? 'แบบจำลอง: OLS (<=52 สัปดาห์)' : 'Model: OLS (<=52 Wks)'}
              </span>
              <span className="text-[11px] text-slate-500 font-mono">
                {result?.formula || 'weekly_cases = beta0 + beta1 * t'}
              </span>
            </div>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-teal-100 text-teal-800 font-semibold">
              R² = {result?.r_squared?.toFixed(3) ?? '-'}
            </span>
          </div>
        </div>
      </div>

      {/* Validation Metrics Cards */}
      {result && result.status === 'success' && result.validation_metrics && (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
            <span className="text-xs font-semibold text-slate-500 block mb-1">
              {lang === 'th' ? 'สัปดาห์ที่ใช้ฝึกสอน / ทดสอบ' : 'Training / Holdout Weeks'}
            </span>
            <div className="text-xl font-bold text-slate-900 font-mono">
              {result.n_training_weeks} / {result.validation_metrics.validation_holdout_weeks}{' '}
              {lang === 'th' ? 'สัปดาห์' : 'wks'}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {lang === 'th' ? 'เพดานสูงสุด 52 สัปดาห์สมบูรณ์' : 'Capped at <=52 complete weeks'}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
            <span className="text-xs font-semibold text-slate-500 block mb-1">
              {lang === 'th' ? 'ค่าความคลาดเคลื่อนเฉลี่ย (MAE)' : 'Forecast MAE'}
            </span>
            <div className="text-xl font-bold text-teal-800 font-mono">
              {result.validation_metrics.mae?.toFixed(1) ?? '-'}
            </div>
            <div className="text-[11px] text-slate-500 mt-1">
              RMSE: {result.validation_metrics.rmse?.toFixed(1) ?? '-'}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
            <span className="text-xs font-semibold text-slate-500 block mb-1">
              {lang === 'th' ? 'เกณฑ์มาตรฐาน (Naive Baseline MAE)' : 'Naive Baseline MAE'}
            </span>
            <div className="text-xl font-bold text-slate-700 font-mono">
              {result.validation_metrics.baseline_mae?.toFixed(1) ?? '-'}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Last-observation naive baseline
            </div>
          </div>

          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
            <span className="text-xs font-semibold text-slate-500 block mb-1">
              {lang === 'th' ? 'เปรียบเทียบกับ Baseline' : 'vs Naive Baseline'}
            </span>
            <div className="text-xl font-bold text-teal-700 font-mono">
              {result.validation_metrics.improvement_pct !== null &&
              result.validation_metrics.improvement_pct !== undefined ? (
                <span>
                  {result.validation_metrics.improvement_pct >= 0 ? '+' : ''}
                  {result.validation_metrics.improvement_pct.toFixed(1)}%
                </span>
              ) : (
                <span>-</span>
              )}
            </div>
            <div className="text-[11px] text-teal-700 mt-1 font-medium">
              Chronological holdout within window
            </div>
          </div>
        </div>
      )}

      {/* Main Forecast Chart */}
      {result && result.status === 'success' && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-bold text-slate-800 text-sm">
                {figLang === 'th'
                  ? 'กราฟเส้นแนวโน้มการพยากรณ์และช่วงคาดหมาย (Observed vs Linear Regression Forecast)'
                  : 'Surveillance Forecast Curve with Prediction Intervals (<=52 Complete Weeks)'}
              </h4>
              <p className="text-xs text-slate-500">
                {figLang === 'th'
                  ? 'น้ำเงิน: สัปดาห์ฝึกสอน (<=52 สัปดาห์), ส้ม: สัปดาห์ล่าสุดที่กันออก (Lag), แดงประ: ค่าพยากรณ์พร้อม 80% และ 95% PI'
                  : 'Navy: Training weeks (<=52 wks); Amber: Lag-excluded weeks; Red dashed: Forecast with 80% & 95% PI'}
              </p>
            </div>
          </div>

          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartPoints} margin={{ top: 15, right: 20, left: 0, bottom: 35 }}>
                <CartesianGrid strokeDasharray="0" stroke="#f1f5f9" vertical={false} />
                <XAxis
                  dataKey={figLang === 'th' ? 'label_th' : 'label_en'}
                  stroke="#000000"
                  strokeWidth={2}
                  tick={{ fontSize: 10, fill: '#000000', fontWeight: 700 }}
                  tickLine={{ stroke: '#000000', strokeWidth: 1.5 }}
                  interval={Math.max(0, Math.floor(chartPoints.length / 14))}
                  angle={-30}
                  textAnchor="end"
                />
                <YAxis
                  stroke="#000000"
                  strokeWidth={2}
                  tick={{ fontSize: 11, fill: '#000000', fontWeight: 700 }}
                  tickLine={{ stroke: '#000000', strokeWidth: 1.5 }}
                />
                <Tooltip
                  formatter={(val: any, name: any) => [
                    `${val} ${figLang === 'th' ? 'ราย' : 'cases'}`,
                    name === 'obs_val'
                      ? figLang === 'th'
                        ? 'สังเกตการณ์จริง (Training)'
                        : 'Observed (Training)'
                      : name === 'lag_val'
                      ? figLang === 'th'
                        ? 'สัปดาห์ล่าสุดที่กันออก (Lag)'
                        : 'Lag-Excluded Week'
                      : name === 'fit_val'
                      ? figLang === 'th'
                        ? 'เส้นแนวโน้ม OLS'
                        : 'OLS Trend'
                      : figLang === 'th'
                      ? 'พยากรณ์ล่วงหน้า'
                      : 'Forecast',
                  ]}
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: '2px solid #000000' }}
                />
                <Area type="monotone" dataKey="pi_95_high" stroke="none" fill="#e11d48" fillOpacity={0.12} name="95% PI High" />
                <Area type="monotone" dataKey="pi_80_high" stroke="none" fill="#e11d48" fillOpacity={0.18} name="80% PI High" />
                <Line type="linear" dataKey="obs_val" stroke="#111c38" strokeWidth={2.4} dot={{ r: 3.5, fill: '#111c38', stroke: '#000000', strokeWidth: 1 }} name="obs_val" />
                <Line type="linear" dataKey="lag_val" stroke="#d97706" strokeWidth={2.2} dot={{ r: 5, fill: '#d97706', stroke: '#000000', strokeWidth: 1 }} name="lag_val" />
                <Line type="linear" dataKey="fit_val" stroke="#0d9488" strokeWidth={2.2} dot={false} name="fit_val" />
                <Line
                  type="linear"
                  dataKey="fc_val"
                  stroke="#e11d48"
                  strokeWidth={2.6}
                  strokeDasharray="5 5"
                  dot={{ r: 4.5, fill: '#e11d48', stroke: '#000000', strokeWidth: 1 }}
                  name="fc_val"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Scientific Disclosures */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 space-y-1.5">
            <div className="flex items-center gap-2 font-semibold text-slate-800">
              <Info className="w-4 h-4 text-teal-600" />
              <span>
                {lang === 'th'
                  ? 'ข้อกำหนดและคำชี้แจงทางสถิติ (Statistical Disclosures):'
                  : 'Statistical Disclosures:'}
              </span>
            </div>
            <p className="leading-relaxed">
              • {lang === 'th' ? result.disclosure_th : result.disclosure_en}
            </p>
            <p className="leading-relaxed text-slate-500">
              •{' '}
              {lang === 'th'
                ? 'โมเดลไม่กำหนดเงื่อนไขฤดูกาลข้ามหลายปี (No multi-year seasonality requirement) และคงช่องว่างของสัปดาห์ที่ไม่มีผู้ป่วยตามจริงโดยไม่เติมค่าเทียมข้ามช่วงที่ไม่มีข้อมูล'
                : 'No multi-year seasonality requirement is imposed; genuine coverage gaps are preserved without fabricating observations.'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
