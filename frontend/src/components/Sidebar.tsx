import React from 'react';
import {
  FileSpreadsheet,
  LayoutDashboard,
  CalendarDays,
  MapPin,
  Users,
  TableProperties,
  TrendingUp,
  Presentation,
  BookOpen,
  Activity,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { useApp } from '../context/AppContext';

export const Sidebar: React.FC = () => {
  const { lang, activeTab, setActiveTab, isLoaded, isSynthetic, measures } = useApp();

  const navItems = [
    {
      id: 'import',
      step: 1,
      labelTh: '1. นำเข้าและจัดการไฟล์',
      labelEn: '1. Import & File Queue',
      icon: FileSpreadsheet,
      badge: isLoaded ? (lang === 'th' ? 'พร้อมใช้' : 'Ready') : lang === 'th' ? 'รอไฟล์' : 'Pending',
    },
    {
      id: 'overview',
      step: 2,
      labelTh: '2. ภาพรวมระบาดวิทยา',
      labelEn: '2. Epidemiological Overview',
      icon: LayoutDashboard,
    },
    {
      id: 'time',
      step: 3,
      labelTh: '3. แนวโน้มตามเวลา (Time)',
      labelEn: '3. Time & Epicurve',
      icon: CalendarDays,
    },
    {
      id: 'districts',
      step: 4,
      labelTh: '4. แผนที่และรายอำเภอ (Place)',
      labelEn: '4. Place & Choropleth Map',
      icon: MapPin,
    },
    {
      id: 'person',
      step: 5,
      labelTh: '5. บุคคลและกลุ่มอายุ (Person)',
      labelEn: '5. Person & Age Rates',
      icon: Users,
    },
    {
      id: 'tables',
      step: 6,
      labelTh: '6. ตารางสรุปมาตรฐาน (0–4)',
      labelEn: '6. Summary Tables (0–4)',
      icon: TableProperties,
    },
    {
      id: 'forecast',
      step: 7,
      labelTh: '7. พยากรณ์โรค (Forecast)',
      labelEn: '7. Weekly OLS Forecast',
      icon: TrendingUp,
    },
    {
      id: 'studio',
      step: 8,
      labelTh: '8. ห้องจัดสไลด์ (1–8)',
      labelEn: '8. Slide Studio (1–8)',
      icon: Presentation,
      highlight: true,
    },
    {
      id: 'methods',
      step: 9,
      labelTh: '9. ระเบียบวิธีและส่งออก',
      labelEn: '9. Methods & Export',
      icon: BookOpen,
    },
  ];

  return (
    <aside className="w-[300px] bg-gradient-to-b from-[#0c1629] via-[#101e36] to-[#0b1324] border-r border-slate-800/80 flex flex-col flex-shrink-0 min-h-screen text-slate-200 select-none shadow-xl">
      {/* Brand Header */}
      <div className="px-6 py-5 border-b border-white/10 flex items-center gap-3.5 bg-white/[0.03]">
        <div className="w-14 h-14 rounded-2xl bg-white p-1 flex items-center justify-center shadow-lg shadow-teal-500/20 ring-2 ring-teal-400/50 flex-shrink-0 overflow-hidden">
          <img
            src="/earth-plb-logo.png"
            alt="Earth PLB Logo"
            className="w-full h-full object-contain"
          />
        </div>
        <div className="min-w-0">
          <h1 className="font-bold text-white text-lg tracking-tight leading-snug">
            DDS <span className="text-teal-300 font-semibold">One-Click</span>
          </h1>
          <p className="text-xs text-teal-200 font-semibold tracking-wide">
            Earth PLB Edition
          </p>
          <p className="text-[11px] text-slate-300/80 font-normal truncate">
            {lang === 'th' ? 'ระบบวิเคราะห์ระบาดวิทยา' : 'Surveillance Analytics'}
          </p>
        </div>
      </div>

      {/* Dataset Status Card */}
      <div className="mx-4 my-3.5 p-4 rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur-xs">
        <div className="flex items-center justify-between text-xs mb-1.5">
          <span className="text-slate-300 font-medium">{lang === 'th' ? 'สถานะข้อมูล:' : 'Dataset:'}</span>
          {isLoaded ? (
            <span
              className={`inline-flex items-center gap-1.5 font-semibold px-2.5 py-0.5 rounded-full text-xs ${
                isSynthetic
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-400/30'
                  : 'bg-teal-500/20 text-teal-200 border border-teal-400/30'
              }`}
            >
              {isSynthetic ? (
                <>
                  <AlertTriangle className="w-4 h-4" />
                  {lang === 'th' ? 'ข้อมูลสาธิต' : 'Synthetic'}
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  {lang === 'th' ? 'ข้อมูลจริง' : 'Authentic'}
                </>
              )}
            </span>
          ) : (
            <span className="text-slate-400 italic">{lang === 'th' ? 'ยังไม่ได้โหลด' : 'Not Loaded'}</span>
          )}
        </div>
        {measures && (
          <div className="pt-2 border-t border-white/10 flex items-baseline justify-between">
            <span className="text-xs text-slate-300">{lang === 'th' ? 'ผู้ป่วยในขอบเขต:' : 'In Scope:'}</span>
            <span className="text-lg font-extrabold text-white font-mono tracking-tight">
              {measures.cases_C.toLocaleString()}{' '}
              <span className="text-xs font-normal text-teal-300">{lang === 'th' ? 'ราย' : 'cases'}</span>
            </span>
          </div>
        )}
      </div>

      {/* Navigation List */}
      <nav className="flex-1 px-3.5 py-1 space-y-1.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center justify-between px-4 py-3.5 rounded-xl text-sm transition-all duration-150 ${
                isActive
                  ? 'bg-gradient-to-r from-teal-600 to-teal-500 text-white font-semibold shadow-md shadow-teal-900/40 ring-1 ring-teal-400/50'
                  : item.highlight
                  ? 'bg-white/[0.06] text-teal-200 hover:bg-white/[0.12] hover:text-white font-medium border border-teal-500/20'
                  : 'text-slate-200 hover:bg-white/[0.07] hover:text-white font-medium'
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <Icon
                  className={`w-5 h-5 flex-shrink-0 ${
                    isActive ? 'text-white' : item.highlight ? 'text-teal-300' : 'text-slate-300'
                  }`}
                />
                <span className="truncate">{lang === 'th' ? item.labelTh : item.labelEn}</span>
              </div>
              {item.badge && (
                <span
                  className={`text-xs px-2 py-0.5 rounded-lg font-medium ${
                    isLoaded
                      ? 'bg-teal-950/80 text-teal-200 border border-teal-600/40'
                      : 'bg-slate-800 text-slate-300'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="px-5 py-4 border-t border-white/10 text-xs text-slate-300 bg-black/25 space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-white flex items-center gap-2">
            <img src="/earth-plb-logo.png" alt="Earth PLB" className="w-5 h-5 rounded-md bg-white p-0.5 object-contain" />
            <span>Earth PLB Analytics</span>
          </span>
          <span className="text-teal-300 font-medium">77 จว. • 878 อำเภอ</span>
        </div>
      </div>
    </aside>
  );
};
