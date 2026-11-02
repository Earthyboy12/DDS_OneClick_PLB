import React, { useEffect, useState } from 'react';
import { Languages, RefreshCw, Trash2, Download, Sparkles, Type } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { getPresentationPackUrl, downloadPresentationPackFile } from '../services/api';

interface HeaderProps {
  titleTh: string;
  titleEn: string;
}

type FontScale = 'normal' | 'large' | 'xlarge';

export const Header: React.FC<HeaderProps> = ({ titleTh, titleEn }) => {
  const { lang, setLang, figLang, isLoaded, purgeSession, refreshData, loading, loadSynthetic, measures } = useApp();
  const [downloadingPack, setDownloadingPack] = useState(false);
  const [fontScale, setFontScale] = useState<FontScale>(() => {
    const saved = localStorage.getItem('dds_font_scale') as FontScale | null;
    return saved && ['normal', 'large', 'xlarge'].includes(saved) ? saved : 'normal';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-font-scale', fontScale);
    localStorage.setItem('dds_font_scale', fontScale);
  }, [fontScale]);

  const toggleLang = () => {
    setLang(lang === 'th' ? 'en' : 'th');
  };

  const handlePurge = () => {
    if (
      window.confirm(
        lang === 'th'
          ? 'คุณต้องการลบข้อมูลทั้งหมดในเซสชันนี้เพื่อความปลอดภัยของข้อมูลผู้ป่วยหรือไม่?'
          : 'Are you sure you want to delete all patient session data?'
      )
    ) {
      purgeSession();
    }
  };

  return (
    <header className="bg-white/95 backdrop-blur-md border-b border-slate-200/90 px-7 py-4 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-20 shadow-xs">
      <div className="flex items-center gap-3.5">
        <img
          src="/earth-plb-logo.png"
          alt="Earth PLB Logo"
          className="w-11 h-11 rounded-xl border border-slate-200 bg-white p-0.5 shadow-2xs object-contain hidden sm:block"
        />
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            {lang === 'th' ? titleTh : titleEn}
          </h2>
          <p className="text-xs text-slate-600 mt-0.5 font-medium">
            {isLoaded && measures
              ? lang === 'th'
                ? `ขอบเขตข้อมูลปัจจุบัน: ${measures.scope_name_th || measures.province_name_th}`
                : `Active Surveillance Scope: ${measures.scope_name_en || measures.province_name_en}`
              : lang === 'th'
              ? 'ระบบสนับสนุนการวิเคราะห์และนำเสนอข้อมูลเฝ้าระวังโรคดิจิทัล — Earth PLB Edition'
              : 'Epidemiological Surveillance Analysis & Presentation Support System — Earth PLB Edition'}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {/* Senior-Friendly Font Size Switcher (ก- / ก+ : ปกติ • ใหญ่สบายตา • ใหญ่มาก) */}
        <div
          className="inline-flex items-center gap-1 bg-slate-100/90 p-1 rounded-xl border border-slate-200"
          title={lang === 'th' ? 'ปรับขนาดตัวอักษรให้อ่านสบายตา' : 'Adjust display font size'}
        >
          <span className="inline-flex items-center gap-1 px-2 text-xs font-semibold text-slate-600">
            <Type className="w-4 h-4 text-teal-700" />
            <span className="hidden xl:inline">{lang === 'th' ? 'ขนาดอักษร:' : 'Text Size:'}</span>
          </span>
          <button
            type="button"
            onClick={() => setFontScale('normal')}
            className={`px-2.5 py-1 rounded-lg text-xs font-bold transition ${
              fontScale === 'normal'
                ? 'bg-white text-teal-800 shadow-xs border border-slate-200/80'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            {lang === 'th' ? 'ก ปกติ' : 'A'}
          </button>
          <button
            type="button"
            onClick={() => setFontScale('large')}
            className={`px-2.5 py-1 rounded-lg text-xs font-bold transition ${
              fontScale === 'large'
                ? 'bg-teal-700 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            {lang === 'th' ? 'ก+ ใหญ่สบายตา' : 'A+ Large'}
          </button>
          <button
            type="button"
            onClick={() => setFontScale('xlarge')}
            className={`px-2.5 py-1 rounded-lg text-xs font-bold transition ${
              fontScale === 'xlarge'
                ? 'bg-teal-700 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            {lang === 'th' ? 'ก++ ใหญ่มาก' : 'A++ Max'}
          </button>
        </div>

        {!isLoaded && (
          <button
            onClick={loadSynthetic}
            disabled={loading}
            className="hidden sm:inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-teal-50 border border-teal-200 text-teal-800 hover:bg-teal-100 text-xs font-semibold transition"
          >
            <Sparkles className="w-4 h-4 text-teal-600" />
            <span>{lang === 'th' ? 'สาธิตข้อมูลสังเคราะห์' : 'Load Synthetic Demo'}</span>
          </button>
        )}

        {isLoaded && (
          <button
            onClick={async () => {
              if (downloadingPack) return;
              setDownloadingPack(true);
              try {
                await downloadPresentationPackFile('light', figLang);
              } catch (err: any) {
                alert(err?.message || 'ดาวน์โหลดล้มเหลว กรุณาลองใหม่อีกครั้ง');
              } finally {
                setDownloadingPack(false);
              }
            }}
            disabled={downloadingPack}
            className="hidden sm:inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-teal-700 to-teal-600 text-white hover:from-teal-800 hover:to-teal-700 text-xs font-semibold shadow-sm transition disabled:opacity-60 cursor-pointer"
          >
            <Download className={`w-4 h-4 ${downloadingPack ? 'animate-bounce' : ''}`} />
            <span>
              {downloadingPack
                ? (lang === 'th' ? 'กำลังดาวน์โหลด...' : 'Downloading...')
                : (lang === 'th'
                  ? `ดาวน์โหลดชุดสไลด์ (${figLang.toUpperCase()})`
                  : `Presentation Pack (${figLang.toUpperCase()})`)}
            </span>
          </button>
        )}

        <button
          onClick={refreshData}
          disabled={loading}
          title={lang === 'th' ? 'รีเฟรชข้อมูล' : 'Refresh'}
          className="p-2.5 rounded-xl text-slate-700 hover:text-slate-950 hover:bg-slate-100 transition border border-slate-200 bg-white"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-teal-600' : ''}`} />
        </button>

        <button
          onClick={toggleLang}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-800 transition"
        >
          <Languages className="w-4 h-4 text-teal-700" />
          <span>{lang === 'th' ? 'ไทย / EN' : 'EN / TH'}</span>
        </button>

        {isLoaded && (
          <button
            onClick={handlePurge}
            title={lang === 'th' ? 'ลบข้อมูลเซสชัน (เพื่อความปลอดภัย)' : 'Purge Session Data'}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-rose-200 bg-rose-50/80 hover:bg-rose-100 text-xs font-semibold text-rose-800 transition"
          >
            <Trash2 className="w-4 h-4" />
            <span className="hidden md:inline">{lang === 'th' ? 'ล้างข้อมูล' : 'Purge'}</span>
          </button>
        )}
      </div>
    </header>
  );
};
