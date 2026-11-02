import React, { useState } from 'react';
import {
  BookOpen,
  Download,
  FileSpreadsheet,
  FileText,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Info,
  Database,
  ExternalLink,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { getExcelExportUrl, getPresentationPackUrl, getCsvExportUrl, downloadPresentationPackFile } from '../services/api';

export const MethodsExportPage: React.FC = () => {
  const { lang, figLang, purgeSession, isLoaded } = useApp();
  const [downloadingPack, setDownloadingPack] = useState<boolean>(false);

  const handleDownloadPack = async () => {
    if (downloadingPack) return;
    setDownloadingPack(true);
    try {
      await downloadPresentationPackFile('light', figLang);
    } catch (err: any) {
      alert(err?.message || 'ดาวน์โหลดล้มเหลว กรุณาลองใหม่อีกครั้ง');
    } finally {
      setDownloadingPack(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 className="font-bold text-slate-800 text-base">
            {lang === 'th' ? 'ระเบียบวิธีทางสถิติและการส่งออกข้อมูล (Methods & Export)' : 'Methodology & Data Export'}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {lang === 'th'
              ? 'คำอธิบายสูตรทางระบาดวิทยา มาตรฐานช่วงความเชื่อมั่น และข้อจำกัดของชุดข้อมูล DDS'
              : 'Scientific documentation, statistical formulas, and aggregate analytical data export packages.'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadPack}
            disabled={downloadingPack}
            className="px-3.5 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-xs transition flex items-center gap-1.5 disabled:opacity-60 cursor-pointer"
          >
            <Download className={`w-3.5 h-3.5 ${downloadingPack ? 'animate-bounce' : ''}`} />
            <span>
              {downloadingPack
                ? (lang === 'th' ? 'กำลังดาวน์โหลด...' : 'Downloading...')
                : (lang === 'th' ? 'Presentation Pack (.ZIP)' : 'Presentation Pack')}
            </span>
          </button>

          <a
            href={getExcelExportUrl()}
            download
            className="px-3.5 py-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium transition flex items-center gap-1.5"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-teal-600" />
            <span>{lang === 'th' ? 'สมุดงาน Excel (.XLSX)' : 'Excel Workbook'}</span>
          </a>
        </div>
      </div>

      {/* Methodology Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Card 1: Core Measures & Formulas */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-2.5 font-bold text-slate-800 text-sm border-b border-slate-100 pb-3">
            <span className="p-1.5 rounded-lg bg-teal-50 text-teal-600">
              <BookOpen className="w-4 h-4" />
            </span>
            <span>{lang === 'th' ? '1. สูตรและตัวชี้วัดระบาดวิทยาหลัก' : '1. Core Epidemiological Measures'}</span>
          </div>

          <div className="space-y-3 text-xs text-slate-600">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 font-mono">
              <span className="font-bold text-slate-800 block text-[11px] mb-1 font-sans">
                {lang === 'th' ? 'สัดส่วนการนอนโรงพยาบาล (Hospitalization Proportion %):' : 'Hospitalization Proportion (%):'}
              </span>
              <p className="text-teal-800 font-bold">H / (H + O) × 100</p>
              <p className="text-[11px] text-slate-500 font-sans mt-1">
                {lang === 'th'
                  ? 'H = ผู้ป่วยใน (IPD), O = ผู้ป่วยนอก (OPD) โดยผู้ป่วยไม่ระบุประเภท (Unknown ~52%) ถูกตัดออกจากตัวหารตามหลักระบาดวิทยา'
                  : 'H = IPD, O = OPD. Unknown patient types are excluded from the denominator to avoid diluting clinical severity.'}
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 font-mono">
              <span className="font-bold text-slate-800 block text-[11px] mb-1 font-sans">
                {lang === 'th' ? 'ความสมบูรณ์ของประเภทผู้ป่วย (Patient-type Completeness %):' : 'Patient-type Completeness (%):'}
              </span>
              <p className="text-blue-800 font-bold">(H + O) / C × 100</p>
              <p className="text-[11px] text-slate-500 font-sans mt-1">
                {lang === 'th'
                  ? 'C = ผู้ป่วยที่เข้าเกณฑ์ทั้งหมด (H + O + U)'
                  : 'Measures completeness of reported IPD/OPD status against total eligible surveillance episodes C.'}
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 font-mono">
              <span className="font-bold text-slate-800 block text-[11px] mb-1 font-sans">
                {lang === 'th' ? 'อัตราป่วยต่อแสนประชากร (Notification Rate per 100,000):' : 'Notification Rate per 100k:'}
              </span>
              <p className="text-navy-800 font-bold">(sum(C_selected) / sum(P_selected)) × 100,000</p>
              <p className="text-[11px] text-slate-500 font-sans mt-1">
                {lang === 'th'
                  ? 'รองรับจังหวัดเดียว หลายจังหวัด (รวมผู้ป่วยหารด้วยผลรวมประชากรจังหวัดชุดเดียวกัน) และทั่วประเทศ (ใช้รหัส 00 ครั้งเดียว ไม่บวกซ้ำกับรายจังหวัด) หากไม่มีประชากรปีนั้นจะใช้ปี 2568 (ล่าสุด) พร้อมระบุชัดเจน'
                  : 'Supports single province, multiple provinces (sum of cases / sum of matched populations), and nationwide (code 00 used once). Falls back to 2568 BE (2025 CE) if year is unavailable.'}
              </p>
            </div>
          </div>
        </div>

        {/* Card 2: Statistical Intervals & Regression */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-2.5 font-bold text-slate-800 text-sm border-b border-slate-100 pb-3">
            <span className="p-1.5 rounded-lg bg-teal-50 text-teal-600">
              <CheckCircle2 className="w-4 h-4" />
            </span>
            <span>{lang === 'th' ? '2. ช่วงความเชื่อมั่นและแบบจำลองสถิติ' : '2. Statistical Intervals & Modeling'}</span>
          </div>

          <div className="space-y-3 text-xs text-slate-600">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
              <span className="font-bold text-slate-800 block text-[11px] mb-1">
                Wilson Score Confidence Interval (95% CI):
              </span>
              <p className="text-slate-600 leading-relaxed">
                {lang === 'th'
                  ? 'ใช้สำหรับสัดส่วนทวินาม (Binomial Proportions) เช่น สัดส่วนการนอนโรงพยาบาล เพื่อหลีกเลี่ยงความคลาดเคลื่อนจาก Normal Approximation เมื่อขนาดตัวอย่างน้อยหรือสัดส่วนใกล้ 0 หรือ 1'
                  : 'Applied to all binomial proportions. Maintains accurate coverage near extreme values and prevents boundaries exceeding [0, 1].'}
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
              <span className="font-bold text-slate-800 block text-[11px] mb-1">
                Exact Poisson Confidence Interval (95% CI):
              </span>
              <p className="text-slate-600 leading-relaxed">
                {lang === 'th'
                  ? 'ใช้สำหรับการคำนวณอัตราต่อประชากร (Count Rates) โดยอิงตาม Chi-Square Quantile Distributions ตามมาตรฐานระบาดวิทยาสากล'
                  : 'Computed for population-based rates using exact Chi-square quantile transformations.'}
              </p>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
              <span className="font-bold text-slate-800 block text-[11px] mb-1">
                Continuous Weekly OLS & Prediction Intervals:
              </span>
              <p className="text-slate-600 leading-relaxed font-mono text-[11px]">
                Cases_t = beta0 + beta1 * t + error
              </p>
              <p className="text-slate-500 text-[11px] mt-1 leading-relaxed">
                {lang === 'th'
                  ? 'ดัชนีเวลา t เรียงลำดับต่อเนื่องข้ามปีปฏิทิน ไม่ใช้เลขสัปดาห์ 1-52 ที่รีเซ็ตทุกปี ช่วงการทำนาย (Prediction Intervals 80% และ 95%) สะท้อนความไม่แน่นอนของค่าสังเกตการณ์ในอนาคต'
                  : 'Time index t continues chronologically across year boundaries. Model-based prediction intervals depict variance of future weekly outcomes.'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Population & Data Quality Nuances Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-center gap-2.5 font-bold text-slate-800 text-sm border-b border-slate-100 pb-3">
          <span className="p-1.5 rounded-lg bg-amber-50 text-amber-600">
            <AlertTriangle className="w-4 h-4" />
          </span>
          <span>{lang === 'th' ? '3. ข้อจำกัดและข้อควรระวังของข้อมูล DDS และประชากร' : '3. Known Limitations & Caveats'}</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-slate-600">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
            <span className="font-bold text-slate-800 block">
              {lang === 'th' ? 'ฐานประชากร DOPA รายอำเภอ:' : 'No District Population in DOPA Book:'}
            </span>
            <p className="leading-relaxed">
              {lang === 'th'
                ? 'เล่มประชากรทางการ DOPA มีเฉพาะยอดรวมรายจังหวัดและรายปีอายุ ไม่มีตัวหารประชากรจำแนกรายอำเภอ ระบบจึงแสดงสถานะ Unavailable สำหรับอัตราต่อประชากรรายอำเภอ และไม่หารเฉลี่ยประชากรอย่างเด็ดขาด'
                : 'The official population workbook contains provincial and single-year age data without district denominators. District population rates are reported as Unavailable unless tidy district imports are supplied.'}
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
            <span className="font-bold text-slate-800 block">
              {lang === 'th' ? 'รหัสจังหวัด 0 และแถวซ้ำ:' : 'National Code 0 & Duplicates:'}
            </span>
            <p className="leading-relaxed">
              {lang === 'th'
                ? 'รหัสจังหวัด 0 คือยอดรวมทั่วประเทศ ต้องตัดออกไม่นำไปรวมกับยอดรวมจังหวัดเด็ดขาด แถวที่ซ้ำกันอย่างสมบูรณ์จะถูกยุบรวม และคอลัมน์ "รวม 0-5 ปี" จะถูกตัดออกเพื่อป้องกันการนับซ้ำ'
                : 'Province code 0 represents the national aggregate and is strictly isolated. Identical duplicate rows are collapsed, and subtotal columns like "0-5 years" are prevented from double counting.'}
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
            <span className="font-bold text-slate-800 block">
              {lang === 'th' ? 'ข้อมูลการเสียชีวิตที่เบาบาง (Sparse Deaths):' : 'Sparse Mortality Data:'}
            </span>
            <p className="leading-relaxed">
              {lang === 'th'
                ? 'การเสียชีวิตในชุดข้อมูลเกิดขึ้นน้อยมาก และมักอยู่นอกกลุ่มรายงานที่อนุมัติ จึงระงับการสร้างแบบจำลอง Mortality Regression เพื่อป้องกันการรายงานผลลัพธ์ที่ผิดพลาดทางสถิติ'
                : 'Sparse death records outside approved cases preclude valid mortality regression. Missing death dates do not imply confirmed survival.'}
            </p>
          </div>
        </div>
      </div>

      {/* Export Actions Card */}
      <div className="bg-slate-900 rounded-2xl p-6 text-white shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h4 className="font-bold text-white text-base">
            {lang === 'th' ? 'ส่งออกชุดข้อมูลสรุปและรายงานทางระบาดวิทยา' : 'Export Aggregate Analytical Datasets'}
          </h4>
          <p className="text-xs text-slate-400 mt-0.5">
            {lang === 'th'
              ? 'ดาวน์โหลดสไลด์ความละเอียดสูง (Publication Quality 1920×1080), สมุดงาน Excel ตารางมาตรฐาน หรือไฟล์ CSV รวม'
              : 'Download Publication Quality presentation slides (1920×1080), multi-sheet XLSX workbook, or CSV packages.'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleDownloadPack}
            disabled={downloadingPack}
            className="px-4 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-xs transition flex items-center gap-2 shadow-sm disabled:opacity-60 cursor-pointer"
          >
            <Download className={`w-4 h-4 ${downloadingPack ? 'animate-bounce' : ''}`} />
            <span>
              {downloadingPack
                ? (lang === 'th' ? 'กำลังเตรียมไฟล์ ZIP...' : 'Preparing ZIP...')
                : (lang === 'th' ? 'Presentation Pack ZIP' : 'Presentation Pack ZIP')}
            </span>
          </button>

          <a
            href={getExcelExportUrl()}
            download
            className="px-4 py-2 rounded-xl bg-navy-800 hover:bg-navy-700 text-slate-200 border border-navy-700 font-medium text-xs transition flex items-center gap-2"
          >
            <FileSpreadsheet className="w-4 h-4 text-teal-400" />
            <span>{lang === 'th' ? 'Excel (.XLSX)' : 'Excel (.XLSX)'}</span>
          </a>

          {isLoaded && (
            <button
              onClick={() => {
                if (window.confirm(lang === 'th' ? 'คุณต้องการล้างข้อมูลทั้งหมดในเซสชันนี้เพื่อความปลอดภัยหรือไม่?' : 'Purge all patient data from this session?')) {
                  purgeSession();
                }
              }}
              className="px-3.5 py-2 rounded-xl bg-rose-950/60 hover:bg-rose-900 text-rose-300 border border-rose-800/60 font-medium text-xs transition"
            >
              {lang === 'th' ? 'ล้างเซสชัน' : 'Purge Session'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
