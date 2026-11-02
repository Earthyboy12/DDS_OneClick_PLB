import React, { useEffect, useState, useMemo } from 'react';
import {
  Download,
  Settings,
  RefreshCw,
  Languages,
  Layers,
  MapPin,
  TrendingUp,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { getStudioFigures, getFigureRenderUrl, getPresentationPackUrl, downloadPresentationPackFile } from '../services/api';
import { StudioFigureItem } from '../types';

export const PresentationStudioPage: React.FC = () => {
  const { lang, figLang, setFigLang, isLoaded, filterVersion } = useApp();
  const [downloadingPack, setDownloadingPack] = useState<boolean>(false);
  const [figures, setFigures] = useState<StudioFigureItem[]>([]);
  const [selectedFigId, setSelectedFigId] = useState<number>(1);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [preset, setPreset] = useState<'full_16_9' | 'half_slide'>('full_16_9');
  const [exportFormat, setExportFormat] = useState<'png' | 'svg' | 'pdf'>('png');
  const [transparent, setTransparent] = useState<boolean>(false);
  const [customTitle, setCustomTitle] = useState<string>('');
  const [customSubtitle, setCustomSubtitle] = useState<string>('');
  const [customFootnote, setCustomFootnote] = useState<string>('');
  const [placeLevel, setPlaceLevel] = useState<'auto' | 'province' | 'district'>('auto');
  const [placeMetric, setPlaceMetric] = useState<'cases' | 'rate'>('cases');
  const [previewKey, setPreviewKey] = useState<number>(1);

  useEffect(() => {
    if (isLoaded) {
      getStudioFigures()
        .then((data) => {
          setFigures(data);
        })
        .catch(console.error);
    }
  }, [isLoaded, filterVersion]);

  const selectedFig = figures.find((f) => f.id === selectedFigId) || figures[0];

  const currentPreviewUrl = useMemo(() => {
    if (!selectedFig) return '';
    return (
      getFigureRenderUrl(selectedFig.id, {
        format: 'png',
        theme,
        preset,
        transparent,
        lang: figLang,
        title: customTitle || undefined,
        subtitle: customSubtitle || undefined,
        footnote: customFootnote || undefined,
        placeLevel: selectedFig.id === 2 ? placeLevel : undefined,
        placeMetric: selectedFig.id === 2 || selectedFig.id === 8 ? placeMetric : undefined,
      }) + `&_t=${previewKey}_${filterVersion}`
    );
  }, [selectedFig, theme, preset, transparent, figLang, customTitle, customSubtitle, customFootnote, placeLevel, placeMetric, previewKey, filterVersion]);

  const downloadUrl = useMemo(() => {
    if (!selectedFig) return '';
    return getFigureRenderUrl(selectedFig.id, {
      format: exportFormat,
      theme,
      preset,
      transparent,
      lang: figLang,
      title: customTitle || undefined,
      subtitle: customSubtitle || undefined,
      footnote: customFootnote || undefined,
      placeLevel: selectedFig.id === 2 ? placeLevel : undefined,
      placeMetric: selectedFig.id === 2 || selectedFig.id === 8 ? placeMetric : undefined,
    });
  }, [selectedFig, exportFormat, theme, preset, transparent, figLang, customTitle, customSubtitle, customFootnote, placeLevel, placeMetric, filterVersion]);

  return (
    <div className="space-y-6">
      {/* Studio Header Card */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h3 className="font-extrabold text-slate-950 text-base">
              {lang === 'th' ? 'ห้องจัดสไลด์ 4K' : '4K Presentation Studio'}
            </h3>
            <span className="text-xs px-2.5 py-0.5 rounded border border-slate-900 bg-slate-100 text-slate-900 font-bold font-mono">
              3840×2160 UHD • ไร้ลายน้ำ
            </span>
          </div>
          <p className="text-xs text-slate-600 font-medium mt-1">
            {lang === 'th'
              ? 'ส่งออกแผนภาพความละเอียดสูง 3840×2160 ครบ 8 ภาพ รองรับทั้งระดับจังหวัดและอำเภอ'
              : 'Export publication-grade figures at 3840×2160 UHD resolution (no watermarks) across all 8 figures.'}
          </p>
        </div>

        {/* Big One-Click Presentation Pack Button */}
        <button
          onClick={async () => {
            if (downloadingPack) return;
            setDownloadingPack(true);
            try {
              await downloadPresentationPackFile(theme, figLang);
            } catch (err: any) {
              alert(err?.message || 'ดาวน์โหลดล้มเหลว กรุณาลองใหม่อีกครั้ง');
            } finally {
              setDownloadingPack(false);
            }
          }}
          disabled={downloadingPack}
          className="px-4 py-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 active:scale-[0.99] text-white text-xs font-bold shadow-md transition flex items-center gap-2 disabled:opacity-60 cursor-pointer"
        >
          <Download className={`w-4 h-4 ${downloadingPack ? 'animate-bounce' : ''}`} />
          <span>
            {downloadingPack
              ? (lang === 'th' ? 'กำลังสร้างชุดสไลด์...' : 'Generating Pack...')
              : (lang === 'th'
                ? `ดาวน์โหลดสไลด์ทั้งหมด (${figLang.toUpperCase()} .ZIP)`
                : `Download All Slides (${figLang.toUpperCase()} .ZIP)`)}
          </span>
        </button>
      </div>

      {/* Main Studio Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Figure Carousel / List (4 cols) */}
        <div className="lg:col-span-4 space-y-2">
          <span className="text-xs font-extrabold text-slate-900 block px-1 uppercase tracking-wide">
            {lang === 'th' ? 'รายการแผนภูมิทั้ง 8 สไลด์ (Figures 1–8):' : 'Mandatory Figures Gallery (8 Slides):'}
          </span>

          <div className="space-y-2 max-h-[660px] overflow-y-auto pr-1">
            {figures.map((fig) => {
              const isSelected = selectedFigId === fig.id;
              return (
                <button
                  key={fig.id}
                  onClick={() => {
                    setSelectedFigId(fig.id);
                    setCustomTitle('');
                    setCustomSubtitle('');
                    setCustomFootnote('');
                    setPreviewKey(Date.now());
                  }}
                  className={`w-full text-left p-3.5 rounded-xl border-2 transition flex items-start gap-3 ${
                    isSelected
                      ? 'bg-blue-50 border-slate-900 shadow-xs'
                      : 'bg-white border-slate-300 hover:border-slate-500 hover:bg-slate-50'
                  }`}
                >
                  <div
                    className={`w-7 h-7 rounded-md flex items-center justify-center font-extrabold text-xs flex-shrink-0 font-mono ${
                      isSelected ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-800 border border-slate-400'
                    }`}
                  >
                    0{fig.id}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h5
                      className={`text-xs font-extrabold truncate ${
                        isSelected ? 'text-slate-950' : 'text-slate-900'
                      }`}
                    >
                      {figLang === 'th' ? fig.name_th : fig.name_en}
                    </h5>
                    <p className="text-[11px] text-slate-600 truncate mt-0.5 font-medium">
                      {figLang === 'th' ? fig.description_th : fig.description_en}
                    </p>
                    {fig.disabled_reason && (
                      <span className="inline-block mt-1 text-[10px] text-amber-800 font-bold">
                        {fig.disabled_reason}
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Column: Workbench & Live 4K Slide Preview (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          {/* Controls Bar */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-4 shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-2.5">
              {/* Graph Language Selector (TH / EN) */}
              <div className="flex items-center bg-slate-100 border border-slate-900 p-1 rounded-lg">
                <span className="px-2 text-[11px] font-bold text-slate-900 flex items-center gap-1">
                  <Languages className="w-3.5 h-3.5 text-slate-900" />
                  {lang === 'th' ? 'ภาษากราฟ:' : 'Slide Lang:'}
                </span>
                <button
                  onClick={() => {
                    setFigLang('th');
                    setPreviewKey(Date.now());
                  }}
                  className={`px-2.5 py-1 rounded font-extrabold transition ${
                    figLang === 'th' ? 'bg-slate-900 text-white shadow-xs' : 'text-slate-800 hover:bg-slate-200'
                  }`}
                >
                  ไทย (TH)
                </button>
                <button
                  onClick={() => {
                    setFigLang('en');
                    setPreviewKey(Date.now());
                  }}
                  className={`px-2.5 py-1 rounded font-extrabold transition ${
                    figLang === 'en' ? 'bg-slate-900 text-white shadow-xs' : 'text-slate-800 hover:bg-slate-200'
                  }`}
                >
                  English (EN)
                </button>
              </div>

              {/* Theme */}
              <div className="flex items-center bg-slate-100 border border-slate-900 p-1 rounded-lg">
                <button
                  onClick={() => {
                    setTheme('light');
                    setPreviewKey(Date.now());
                  }}
                  className={`px-3 py-1 rounded font-bold transition ${
                    theme === 'light' ? 'bg-slate-900 text-white shadow-xs' : 'text-slate-700'
                  }`}
                >
                  {lang === 'th' ? 'สไลด์ขาว (Light)' : 'Light'}
                </button>
                <button
                  onClick={() => {
                    setTheme('dark');
                    setPreviewKey(Date.now());
                  }}
                  className={`px-3 py-1 rounded font-bold transition ${
                    theme === 'dark' ? 'bg-slate-900 text-white shadow-xs' : 'text-slate-700'
                  }`}
                >
                  {lang === 'th' ? 'สไลด์เข้ม (Dark)' : 'Dark'}
                </button>
              </div>

              {/* Preset */}
              <div className="flex items-center bg-slate-100 border border-slate-900 p-1 rounded-lg">
                <button
                  onClick={() => {
                    setPreset('full_16_9');
                    setPreviewKey(Date.now());
                  }}
                  className={`px-2.5 py-1 rounded font-bold transition ${
                    preset === 'full_16_9' ? 'bg-slate-900 text-white shadow-xs' : 'text-slate-700'
                  }`}
                >
                  16:9 (3840×2160)
                </button>
                <button
                  onClick={() => {
                    setPreset('half_slide');
                    setPreviewKey(Date.now());
                  }}
                  className={`px-2.5 py-1 rounded font-bold transition ${
                    preset === 'half_slide' ? 'bg-slate-900 text-white shadow-xs' : 'text-slate-700'
                  }`}
                >
                  Half Slide
                </button>
              </div>

              {/* Format selection */}
              <select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value as any)}
                className="px-2.5 py-1.5 rounded-lg border border-slate-200/90 bg-white text-slate-900 font-bold focus:outline-none"
              >
                <option value="png">PNG (3840×2160 4K)</option>
                <option value="svg">Vector SVG</option>
                <option value="pdf">Vector PDF</option>
              </select>
            </div>

            {/* Download single slide button */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPreviewKey(Date.now())}
                title="Refresh Preview"
                className="p-1.5 rounded-lg border border-slate-200/90 hover:bg-slate-100 text-slate-900"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
              <a
                href={downloadUrl}
                download
                className="px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-bold flex items-center gap-1.5 shadow-xs transition"
              >
                <Download className="w-3.5 h-3.5" />
                <span>
                  {lang === 'th'
                    ? `ดาวน์โหลด (${exportFormat.toUpperCase()} • ${figLang.toUpperCase()})`
                    : `Download (${exportFormat.toUpperCase()} • ${figLang.toUpperCase()})`}
                </span>
              </a>
            </div>
          </div>

          {/* Contextual Level & Metric Controls for Figure 2 and Figure 8 */}
          {(selectedFig?.id === 2 || selectedFig?.id === 8) && (
            <div className="bg-blue-50 border border-slate-200/90 p-3.5 rounded-xl flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 font-extrabold text-slate-950">
                <Layers className="w-4 h-4 text-slate-900" />
                <span>
                  {selectedFig.id === 2
                    ? lang === 'th'
                      ? 'ตัวเลือกสำหรับ Figure 2 (ระดับพื้นที่ & ตัวชี้วัด):'
                      : 'Options for Figure 2 (Level & Metric):'
                    : lang === 'th'
                    ? 'ตัวเลือกสำหรับ Figure 8 (ตัวชี้วัด):'
                    : 'Options for Figure 8 (Metric):'}
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {selectedFig.id === 2 && (
                  <div className="inline-flex rounded-lg bg-white p-0.5 border border-slate-900">
                    <button
                      onClick={() => {
                        setPlaceLevel('auto');
                        setPreviewKey(Date.now());
                      }}
                      className={`px-2.5 py-1 rounded text-xs font-bold ${
                        placeLevel === 'auto' ? 'bg-slate-900 text-white' : 'text-slate-800'
                      }`}
                    >
                      {lang === 'th' ? 'อัตโนมัติ (Auto)' : 'Auto'}
                    </button>
                    <button
                      onClick={() => {
                        setPlaceLevel('province');
                        setPreviewKey(Date.now());
                      }}
                      className={`px-2.5 py-1 rounded text-xs font-bold ${
                        placeLevel === 'province' ? 'bg-slate-900 text-white' : 'text-slate-800'
                      }`}
                    >
                      {lang === 'th' ? 'ระดับจังหวัด' : 'Province'}
                    </button>
                    <button
                      onClick={() => {
                        setPlaceLevel('district');
                        setPreviewKey(Date.now());
                      }}
                      className={`px-2.5 py-1 rounded text-xs font-bold ${
                        placeLevel === 'district' ? 'bg-slate-900 text-white' : 'text-slate-800'
                      }`}
                    >
                      {lang === 'th' ? 'ระดับอำเภอ' : 'District'}
                    </button>
                  </div>
                )}

                <div className="inline-flex rounded-lg bg-white p-0.5 border border-slate-900">
                  <button
                    onClick={() => {
                      setPlaceMetric('cases');
                      setPreviewKey(Date.now());
                    }}
                    className={`px-2.5 py-1 rounded text-xs font-bold ${
                      placeMetric === 'cases' ? 'bg-slate-900 text-white' : 'text-slate-800'
                    }`}
                  >
                    {lang === 'th' ? 'จำนวนเคส (Cases)' : 'Cases'}
                  </button>
                  <button
                    onClick={() => {
                      setPlaceMetric('rate');
                      setPreviewKey(Date.now());
                    }}
                    className={`px-2.5 py-1 rounded text-xs font-bold ${
                      placeMetric === 'rate' ? 'bg-slate-900 text-white' : 'text-slate-800'
                    }`}
                  >
                    {lang === 'th' ? 'อุบัติการณ์ (Incidence/100k)' : 'Incidence / 100k'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Slide Preview Frame */}
          <div className="bg-slate-900 rounded-2xl p-4 shadow-md border border-slate-200/90 flex flex-col items-center justify-center min-h-[380px] relative">
            <div className="w-full flex items-center justify-between text-slate-300 text-xs px-2 mb-2 font-mono font-bold">
              <span>
                Slide 0{selectedFig?.id} ({figLang.toUpperCase()}): {figLang === 'th' ? selectedFig?.name_th : selectedFig?.name_en}
              </span>
              <span className="text-[11px] text-teal-300">3840×2160 UHD • No Watermarks</span>
            </div>

            {currentPreviewUrl ? (
              <div className="w-full relative rounded-lg overflow-hidden border-2 border-slate-700 shadow-2xl bg-white">
                <img
                  key={currentPreviewUrl}
                  src={currentPreviewUrl}
                  alt={selectedFig?.name_en}
                  className="w-full h-auto object-contain block"
                  loading="lazy"
                />
              </div>
            ) : (
              <div className="text-slate-400 text-xs flex items-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-teal-400" />
                <span>Generating high-resolution preview...</span>
              </div>
            )}
          </div>

          {/* Custom Labels & Captions */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs space-y-3 text-xs">
            <div className="flex items-center justify-between font-extrabold text-slate-900">
              <span className="flex items-center gap-1.5">
                <Settings className="w-4 h-4 text-slate-900" />
                {lang === 'th'
                  ? 'ปรับแต่งข้อความหัวเรื่องและเชิงอรรถสไลด์ (Editable Captions)'
                  : 'Customize Slide Titles & Footnotes'}
              </span>
              <span className="text-slate-500 font-semibold">Optional</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="text-[11px] font-bold text-slate-700 block mb-1">
                  {lang === 'th' ? 'หัวเรื่องสไลด์ (Slide Title):' : 'Custom Title:'}
                </label>
                <input
                  type="text"
                  placeholder={lang === 'th' ? 'ใช้ชื่อเริ่มต้นตามภาษาที่เลือก' : 'Default standard title'}
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                  onBlur={() => setPreviewKey(Date.now())}
                  className="w-full px-3 py-1.5 rounded-lg border-2 border-slate-300 text-xs focus:border-slate-900 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-700 block mb-1">
                  {lang === 'th' ? 'หัวเรื่องย่อย (Subtitle):' : 'Custom Subtitle:'}
                </label>
                <input
                  type="text"
                  placeholder={lang === 'th' ? 'ใช้ขอบเขตข้อมูลเริ่มต้น' : 'Default scope subtitle'}
                  value={customSubtitle}
                  onChange={(e) => setCustomSubtitle(e.target.value)}
                  onBlur={() => setPreviewKey(Date.now())}
                  className="w-full px-3 py-1.5 rounded-lg border-2 border-slate-300 text-xs focus:border-slate-900 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-slate-700 block mb-1">
                  {lang === 'th' ? 'เชิงอรรถ (Footnote):' : 'Custom Footnote:'}
                </label>
                <input
                  type="text"
                  placeholder={lang === 'th' ? 'ใช้คำชี้แจงมาตรฐานระบาดวิทยา' : 'Default epidemiological footnote'}
                  value={customFootnote}
                  onChange={(e) => setCustomFootnote(e.target.value)}
                  onBlur={() => setPreviewKey(Date.now())}
                  className="w-full px-3 py-1.5 rounded-lg border-2 border-slate-300 text-xs focus:border-slate-900 focus:outline-none"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
