import React from 'react';
import { AlertTriangle, Info } from 'lucide-react';
import { useApp } from '../context/AppContext';

export const SyntheticBanner: React.FC = () => {
  const { lang, isSynthetic, isLoaded } = useApp();

  if (!isLoaded || !isSynthetic) return null;

  return (
    <div className="bg-amber-500/15 border-b border-amber-500/30 px-6 py-2.5 text-amber-900 flex items-center justify-between shadow-xs">
      <div className="flex items-center gap-2.5 text-xs sm:text-sm font-medium">
        <span className="p-1 rounded-md bg-amber-500 text-white flex-shrink-0">
          <AlertTriangle className="w-4 h-4" />
        </span>
        <div>
          <span className="font-bold text-amber-950">
            {lang === 'th' ? 'โหมดข้อมูลสังเคราะห์เพื่อการทดสอบ (SYNTHETIC DATA)' : 'SYNTHETIC DEMONSTRATION DATASET'}
          </span>
          <span className="hidden md:inline ml-2 text-amber-800">
            {lang === 'th'
              ? '— ชุดข้อมูลจำลองขึ้นเพื่อการทดสอบระบบและสาธิตการใช้งาน มิใช่ข้อมูลผู้ป่วยจริงและห้ามนำไปอ้างอิงเป็นสถานการณ์จริง'
              : '— Generated strictly for testing and validation. Not real patient data; do not cite as real surveillance findings.'}
          </span>
        </div>
      </div>
      <div className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-amber-500/20 text-amber-900 border border-amber-500/40 whitespace-nowrap">
        {lang === 'th' ? 'ข้อมูลสังเคราะห์' : 'SYNTHETIC'}
      </div>
    </div>
  );
};
