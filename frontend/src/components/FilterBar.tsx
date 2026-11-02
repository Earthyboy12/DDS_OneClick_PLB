import React, { useEffect, useState } from 'react';
import {
  Filter,
  RotateCcw,
  Languages,
  CheckCircle2,
  AlertCircle,
  Globe,
  MapPin,
  Layers,
  X,
  Plus,
  Info,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { getReferenceDistricts } from '../services/api';
import { ReferenceDistrict, GeographyScopeMode } from '../types';

export const FilterBar: React.FC = () => {
  const {
    lang,
    figLang,
    setFigLang,
    isLoaded,
    measures,
    filters,
    filterOptions,
    referenceProvinces,
    updateFilters,
    resetFilters,
    loading,
  } = useApp();

  const [refDistricts, setRefDistricts] = useState<ReferenceDistrict[]>([]);
  const [bangkokMissing, setBangkokMissing] = useState<boolean>(false);
  const [districtProvFilter, setDistrictProvFilter] = useState<string>('');

  const selectedProvs = filters.province_codes || [];
  const effectiveDistProv =
    districtProvFilter ||
    (filters.district_code && filters.district_code.length === 4 ? filters.district_code.slice(0, 2) : '') ||
    (selectedProvs.length === 1 && selectedProvs[0] !== '00' ? selectedProvs[0] : '');

  useEffect(() => {
    if (isLoaded && filters.scope_mode === 'district' && effectiveDistProv && effectiveDistProv !== 'Unknown') {
      getReferenceDistricts(effectiveDistProv)
        .then((res) => {
          setRefDistricts(res.districts || []);
          setBangkokMissing(Boolean(res.bangkok_lookup_missing));
        })
        .catch(console.error);
    } else {
      setRefDistricts([]);
      setBangkokMissing(false);
    }
  }, [isLoaded, filters.scope_mode, effectiveDistProv]);

  if (!isLoaded || !measures) return null;

  const denom = measures.denominator_info;
  const datasetProvs: Array<{ province_code: string; name_th: string; name_en: string; cases: number }> =
    filterOptions?.provinces_in_data || [];
  const datasetYears: number[] = filterOptions?.years_in_data || [];
  const refYears: number[] = [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014, 2013];
  const allYears = Array.from(new Set([...datasetYears, ...refYears, 2026])).sort((a, b) => b - a);

  const hasActiveFilter = Boolean(
    filters.scope_mode !== 'all_imported' ||
      selectedProvs.length > 0 ||
      filters.district_code ||
      filters.year ||
      filters.sex ||
      filters.nationality ||
      filters.patient_type ||
      filters.comparator_province_code ||
      filters.address_type !== 'residence'
  );

  const handleScopeModeChange = (mode: GeographyScopeMode) => {
    if (mode === 'all_imported') {
      updateFilters({ scope_mode: 'all_imported', province_codes: [], province_code: null, district_code: null });
    } else if (mode === 'national') {
      updateFilters({ scope_mode: 'national', province_codes: ['00'], province_code: '00', district_code: null });
    } else if (mode === 'provinces') {
      const validDsProvs = datasetProvs.map((p) => p.province_code).filter((c) => c !== 'Unknown' && c !== '00');
      const initialProvs = selectedProvs.filter((p) => p !== '00').length > 0
        ? selectedProvs.filter((p) => p !== '00')
        : validDsProvs.slice(0, 1);
      updateFilters({
        scope_mode: 'provinces',
        province_codes: initialProvs,
        province_code: initialProvs.join(',') || null,
        district_code: null,
      });
    } else if (mode === 'district') {
      const validDsProvs = datasetProvs.map((p) => p.province_code).filter((c) => c !== 'Unknown' && c !== '00');
      const initProv = effectiveDistProv || validDsProvs[0] || '11';
      setDistrictProvFilter(initProv);
      updateFilters({
        scope_mode: 'district',
        province_codes: [initProv],
        province_code: initProv,
        district_code: null,
      });
    }
  };

  const handleToggleProvince = (pCode: string) => {
    if (!pCode || pCode === '00') return;
    const current = selectedProvs.filter((c) => c !== '00');
    const next = current.includes(pCode) ? current.filter((c) => c !== pCode) : [...current, pCode];
    updateFilters({
      scope_mode: 'provinces',
      province_codes: next,
      province_code: next.join(',') || null,
      district_code: null,
    });
  };

  const handleSelectAllDatasetProvinces = () => {
    const validDsProvs = datasetProvs.map((p) => p.province_code).filter((c) => c !== 'Unknown' && c !== '00');
    updateFilters({
      scope_mode: 'provinces',
      province_codes: validDsProvs,
      province_code: validDsProvs.join(',') || null,
      district_code: null,
    });
  };

  const getProvinceLabel = (code: string) => {
    const p = referenceProvinces.find((r) => r.province_code === code);
    if (!p) return code;
    return lang === 'th' ? p.province_name_th : p.province_name_en;
  };

  return (
    <div className="bg-[#f8faf9] border-b border-slate-200/90 px-7 py-3.5 text-xs shadow-2xs">
      <div className="max-w-[1480px] mx-auto space-y-3">
        {/* Row 1: Geography Scope Mode Selector + Demographic & Year Filters */}
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="inline-flex items-center gap-1.5 font-bold text-slate-800 mr-1">
            <Filter className="w-4 h-4 text-teal-700" />
            <span>{lang === 'th' ? 'ขอบเขตพื้นที่:' : 'Geography Scope:'}</span>
          </span>

          {/* 4 Clear Geography Scope Buttons */}
          <div className="inline-flex rounded-xl border border-slate-300/90 bg-white p-1 shadow-2xs gap-0.5">
            <button
              type="button"
              disabled={loading}
              onClick={() => handleScopeModeChange('all_imported')}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg font-semibold transition ${
                filters.scope_mode === 'all_imported'
                  ? 'bg-navy-800 text-white shadow-xs'
                  : 'text-slate-700 hover:bg-slate-100'
              }`}
              title={lang === 'th' ? 'แสดงผู้ป่วยทั้งหมดที่นำเข้า' : 'All imported records'}
            >
              <Layers className="w-4 h-4" />
              <span>{lang === 'th' ? 'ข้อมูลทั้งหมดที่นำเข้า' : 'All Imported'}</span>
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={() => handleScopeModeChange('national')}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg font-semibold transition ${
                filters.scope_mode === 'national'
                  ? 'bg-teal-700 text-white shadow-xs'
                  : 'text-slate-700 hover:bg-slate-100'
              }`}
              title={lang === 'th' ? 'ใช้ยอดประชากรทั่วประเทศ (77 จังหวัด / รหัส 00 เพียงครั้งเดียว)' : 'Nationwide (77 provinces, code 00 used once)'}
            >
              <Globe className="w-4 h-4" />
              <span>{lang === 'th' ? 'ทั่วประเทศ (77 จว.)' : 'Nationwide'}</span>
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={() => handleScopeModeChange('provinces')}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg font-semibold transition ${
                filters.scope_mode === 'provinces'
                  ? 'bg-teal-700 text-white shadow-xs'
                  : 'text-slate-700 hover:bg-slate-100'
              }`}
              title={lang === 'th' ? 'เลือกจังหวัดเดียวหรือหลายจังหวัด (รวมผู้ป่วย / รวมประชากรจังหวัดชุดเดียวกัน)' : 'Select single or multiple provinces'}
            >
              <MapPin className="w-4 h-4" />
              <span>
                {lang === 'th'
                  ? `เลือกจังหวัด (${selectedProvs.filter((p) => p !== '00').length})`
                  : `Province(s) (${selectedProvs.filter((p) => p !== '00').length})`}
              </span>
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={() => handleScopeModeChange('district')}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg font-semibold transition ${
                filters.scope_mode === 'district'
                  ? 'bg-teal-700 text-white shadow-xs'
                  : 'text-slate-700 hover:bg-slate-100'
              }`}
              title={lang === 'th' ? 'เลือกเฉพาะอำเภอ (ไม่หารด้วยประชากรจังหวัด)' : 'Select specific district'}
            >
              <span>{lang === 'th' ? 'เลือกอำเภอ' : 'District'}</span>
            </button>
          </div>

          {/* Address Family */}
          <select
            value={filters.address_type}
            disabled={loading}
            onChange={(e) =>
              updateFilters({
                address_type: e.target.value as 'residence' | 'illness',
                district_code: null,
              })
            }
            className="px-3 py-1.5 rounded-xl border border-slate-300 bg-white text-slate-800 font-semibold shadow-2xs"
          >
            <option value="residence">
              {lang === 'th' ? 'ที่อยู่ปัจจุบัน (Residence)' : 'Residence Address'}
            </option>
            <option value="illness">
              {lang === 'th' ? 'ที่อยู่ขณะป่วย (Illness)' : 'Illness Address'}
            </option>
          </select>

          {/* Year Selector */}
          <select
            value={filters.year ?? ''}
            disabled={loading}
            onChange={(e) =>
              updateFilters({ year: e.target.value ? Number(e.target.value) : null })
            }
            className="px-3 py-1.5 rounded-xl border border-slate-300 bg-white text-slate-800 font-semibold shadow-2xs"
          >
            <option value="">{lang === 'th' ? 'ทุกปี (ใช้ประชากรปีมัธยฐาน)' : 'All Years (Median Pop Year)'}</option>
            {allYears.map((yr) => (
              <option key={yr} value={yr}>
                {lang === 'th' ? `พ.ศ. ${yr + 543} (${yr})` : `Year ${yr}`}
                {yr > 2025 ? (lang === 'th' ? ' — ใช้ประชากรปี 2568 (ล่าสุด)' : ' — Uses 2025 pop') : ''}
              </option>
            ))}
          </select>

          {/* Sex Selector */}
          <select
            value={filters.sex || ''}
            disabled={loading}
            onChange={(e) => updateFilters({ sex: e.target.value || null })}
            className="px-3 py-1.5 rounded-xl border border-slate-300 bg-white text-slate-800 font-semibold shadow-2xs"
          >
            <option value="">{lang === 'th' ? 'ทุกเพศ (All Sex)' : 'All Sexes'}</option>
            <option value="ชาย">{lang === 'th' ? 'ชาย (Male)' : 'Male'}</option>
            <option value="หญิง">{lang === 'th' ? 'หญิง (Female)' : 'Female'}</option>
            <option value="Unknown">{lang === 'th' ? 'ไม่ระบุเพศ (Unknown)' : 'Unknown Sex'}</option>
          </select>

          {/* Nationality Selector */}
          <select
            value={filters.nationality || ''}
            disabled={loading}
            onChange={(e) => updateFilters({ nationality: e.target.value || null })}
            className="px-3 py-1.5 rounded-xl border border-slate-300 bg-white text-slate-800 font-semibold shadow-2xs"
          >
            <option value="">{lang === 'th' ? 'ทุกสัญชาติ (All Nat.)' : 'All Nationalities'}</option>
            <option value="Thai">{lang === 'th' ? 'ไทย (Thai)' : 'Thai'}</option>
            <option value="Non-Thai">{lang === 'th' ? 'ต่างชาติ (Non-Thai)' : 'Non-Thai'}</option>
            <option value="Unknown">{lang === 'th' ? 'ไม่ระบุสัญชาติ (Unknown)' : 'Unknown'}</option>
          </select>

          {/* Optional Comparator Province (Default: None) */}
          <select
            value={filters.comparator_province_code || ''}
            disabled={loading}
            onChange={(e) =>
              updateFilters({ comparator_province_code: e.target.value || null })
            }
            className="px-3 py-1.5 rounded-xl border border-slate-300 bg-white text-slate-700 font-semibold max-w-[210px] shadow-2xs"
          >
            <option value="">
              {lang === 'th' ? 'เปรียบเทียบจังหวัด: ไม่เลือก' : 'Comparator: None'}
            </option>
            {referenceProvinces.map((p) => (
              <option key={`comp-${p.province_code}`} value={p.province_code}>
                {lang === 'th' ? `เทียบกับ: [${p.province_code}] ${p.province_name_th}` : `vs [${p.province_code}] ${p.province_name_en}`}
              </option>
            ))}
          </select>

          {hasActiveFilter && (
            <button
              onClick={resetFilters}
              disabled={loading}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-slate-200 hover:bg-slate-300 text-slate-800 font-semibold transition"
            >
              <RotateCcw className="w-4 h-4" />
              <span>{lang === 'th' ? 'ล้างตัวกรอง' : 'Reset'}</span>
            </button>
          )}

          {/* Graph Language Selector (TH / EN) */}
          <div className="ml-auto flex items-center gap-1.5 bg-white px-3 py-1 rounded-xl border border-slate-300 shadow-2xs">
            <Languages className="w-4 h-4 text-teal-700" />
            <span className="text-xs text-slate-700 font-semibold">
              {lang === 'th' ? 'ภาษากราฟ:' : 'Graph Lang:'}
            </span>
            <button
              onClick={() => setFigLang('th')}
              className={`px-2.5 py-1 rounded-lg text-xs font-bold transition ${
                figLang === 'th' ? 'bg-teal-700 text-white' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              ไทย (TH)
            </button>
            <button
              onClick={() => setFigLang('en')}
              className={`px-2.5 py-1 rounded-lg text-xs font-bold transition ${
                figLang === 'en' ? 'bg-teal-700 text-white' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              EN
            </button>
          </div>
        </div>

        {/* Row 1B: Conditional Multi-Province or District Picker */}
        {filters.scope_mode === 'provinces' && (
          <div className="flex flex-wrap items-center gap-2 bg-white px-3 py-2 rounded-lg border border-teal-200">
            <span className="font-semibold text-teal-800 flex items-center gap-1">
              <Plus className="w-3.5 h-3.5" />
              {lang === 'th' ? 'เลือกจังหวัดเดียวหรือหลายจังหวัด:' : 'Add/Remove Province(s):'}
            </span>
            <select
              value=""
              disabled={loading}
              onChange={(e) => {
                if (e.target.value) handleToggleProvince(e.target.value);
              }}
              className="px-2.5 py-1 rounded-md border border-slate-300 bg-slate-50 text-slate-800 font-medium"
            >
              <option value="">
                {lang === 'th' ? '+ คลิกเพื่อเพิ่มจังหวัดในขอบเขต...' : '+ Add province to scope...'}
              </option>
              {datasetProvs.length > 0 && (
                <optgroup label={lang === 'th' ? 'จังหวัดที่พบผู้ป่วยในชุดข้อมูล' : 'Provinces in Dataset'}>
                  {datasetProvs
                    .filter((p) => p.province_code !== 'Unknown')
                    .map((p) => (
                      <option key={`add-ds-${p.province_code}`} value={p.province_code}>
                        [{p.province_code}] {lang === 'th' ? p.name_th : p.name_en} ({p.cases.toLocaleString()} ราย)
                      </option>
                    ))}
                </optgroup>
              )}
              <optgroup label={lang === 'th' ? 'จังหวัดอ้างอิงทั้งหมด (77 จังหวัด)' : 'All 77 Reference Provinces'}>
                {referenceProvinces.map((p) => (
                  <option key={`add-ref-${p.province_code}`} value={p.province_code}>
                    [{p.province_code}] {lang === 'th' ? p.province_name_th : p.province_name_en}
                  </option>
                ))}
              </optgroup>
            </select>

            {datasetProvs.filter((p) => p.province_code !== 'Unknown').length > 0 && (
              <button
                type="button"
                onClick={handleSelectAllDatasetProvinces}
                className="px-2 py-1 rounded bg-teal-50 hover:bg-teal-100 text-teal-700 border border-teal-200 font-medium transition"
              >
                {lang === 'th'
                  ? `เลือกทุกจังหวัดที่พบในชุดข้อมูล (${datasetProvs.filter((p) => p.province_code !== 'Unknown').length} จว.)`
                  : `Select all provinces in dataset (${datasetProvs.filter((p) => p.province_code !== 'Unknown').length})`}
              </button>
            )}

            {/* Selected Province Pills */}
            <div className="flex flex-wrap items-center gap-1.5">
              {selectedProvs
                .filter((c) => c !== '00')
                .map((code) => (
                  <span
                    key={code}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-teal-600 text-white font-medium text-[11px]"
                  >
                    <span>
                      [{code}] {getProvinceLabel(code)}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleToggleProvince(code)}
                      className="hover:bg-teal-700 rounded-full p-0.5"
                      title={lang === 'th' ? 'นำจังหวัดนี้ออก' : 'Remove province'}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              {selectedProvs.filter((c) => c !== '00').length === 0 && (
                <span className="text-amber-700 italic">
                  {lang === 'th' ? 'กรุณาเลือกอย่างน้อย 1 จังหวัด' : 'Please select at least 1 province'}
                </span>
              )}
            </div>
          </div>
        )}

        {filters.scope_mode === 'district' && (
          <div className="flex flex-wrap items-center gap-2 bg-white px-3 py-2 rounded-lg border border-teal-200">
            <span className="font-semibold text-teal-800">
              {lang === 'th' ? 'เลือกจังหวัดและอำเภอ:' : 'Select Province & District:'}
            </span>
            <select
              value={effectiveDistProv}
              disabled={loading}
              onChange={(e) => {
                const pv = e.target.value;
                setDistrictProvFilter(pv);
                updateFilters({
                  scope_mode: 'district',
                  province_codes: pv ? [pv] : [],
                  province_code: pv || null,
                  district_code: null,
                });
              }}
              className="px-2.5 py-1 rounded-md border border-slate-300 bg-slate-50 text-slate-800 font-medium"
            >
              <option value="">{lang === 'th' ? '-- เลือกจังหวัด --' : '-- Select Province --'}</option>
              {referenceProvinces.map((p) => (
                <option key={`dprov-${p.province_code}`} value={p.province_code}>
                  [{p.province_code}] {lang === 'th' ? p.province_name_th : p.province_name_en}
                </option>
              ))}
            </select>

            <select
              value={filters.district_code || ''}
              disabled={loading || (!refDistricts.length && !bangkokMissing)}
              onChange={(e) =>
                updateFilters({
                  scope_mode: 'district',
                  district_code: e.target.value || null,
                })
              }
              className="px-2.5 py-1 rounded-md border border-slate-300 bg-slate-50 text-slate-800 font-medium"
            >
              <option value="">
                {bangkokMissing
                  ? lang === 'th'
                    ? 'กทม. (10): ไม่มีตารางรหัสเขตในฐานข้อมูลอ้างอิง'
                    : 'Bangkok (10): No district table in reference DB'
                  : lang === 'th'
                  ? '-- เลือกอำเภอ/เขต --'
                  : '-- Select District --'}
              </option>
              {refDistricts.map((d) => (
                <option key={d.district_code} value={d.district_code}>
                  [{d.district_code}] {d.district_name_th}
                </option>
              ))}
            </select>
            <span className="text-[11px] text-amber-700">
              {lang === 'th'
                ? '* การเลือกเฉพาะอำเภอจะแสดงจำนวนผู้ป่วยและสัดส่วนผู้ป่วยใน (IPD %) โดยไม่นำประชากรจังหวัดมาหาร'
                : '* District scope shows case counts & IPD % without dividing by provincial population'}
            </span>
          </div>
        )}

        {/* Row 2: Active Numerator, Denominator, Population Year & Geography Scope Bar with Tooltip */}
        <div
          className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-600 pt-1.5 border-t border-slate-200/80"
          title={
            lang === 'th'
              ? `ขอบเขตพื้นที่: ${measures.scope_name_th}\nตัวเศษ (Numerator): ผู้ป่วย C = ${measures.cases_C.toLocaleString()} ราย (IPD = ${measures.ipd_H.toLocaleString()} ราย)\nตัวหาร (Denominator): ${
                  denom?.available && denom.population ? `${denom.population.toLocaleString()} คน` : 'ไม่สามารถคำนวณได้'
                }\nปีประชากร: ${denom?.population_year_be ? `พ.ศ. ${denom.population_year_be} (ค.ศ. ${denom.reference_year})` : '-'}\nหมายเหตุ: ${denom?.reason_th || ''}`
              : `Scope: ${measures.scope_name_en}\nNumerator: C = ${measures.cases_C.toLocaleString()} cases (IPD = ${measures.ipd_H.toLocaleString()})\nDenominator: ${
                  denom?.available && denom.population ? denom.population.toLocaleString() : 'Unavailable'
                }\nPopulation Year: ${denom?.reference_year || '-'}\nNote: ${denom?.reason_en || ''}`
          }
        >
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="font-semibold text-slate-800 inline-flex items-center gap-1">
              <Info className="w-3.5 h-3.5 text-teal-600" />
              {lang === 'th' ? 'ขอบเขต:' : 'Scope:'}{' '}
              <span className="text-teal-700">
                {lang === 'th' ? measures.scope_name_th : measures.scope_name_en}
              </span>
            </span>
            <span className="text-slate-400">|</span>
            <span>
              {lang === 'th' ? 'ตัวเศษ (ผู้ป่วย C):' : 'Numerator (C):'}{' '}
              <strong className="text-slate-900 font-mono">{measures.cases_C.toLocaleString()}</strong>{' '}
              {lang === 'th' ? 'ราย' : 'cases'} (IPD:{' '}
              <strong className="text-slate-800 font-mono">{measures.ipd_H.toLocaleString()}</strong>)
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            {denom?.available ? (
              <span className="inline-flex items-center gap-1 text-emerald-700 font-medium bg-emerald-50 px-2.5 py-0.5 rounded-md border border-emerald-200">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>
                  {lang === 'th'
                    ? `ตัวหารประชากร: ${denom.population?.toLocaleString()} คน | ปีประชากร: พ.ศ. ${denom.population_year_be} (ค.ศ. ${denom.reference_year})${
                        denom.is_fallback_year ? ' [ใช้ปีล่าสุด 2568]' : ''
                      } | อัตราป่วย: ${measures.case_notification_rate?.toFixed(2)} ต่อแสน`
                    : `Denominator: ${denom.population?.toLocaleString()} | Pop Year: ${denom.reference_year} (B.E. ${denom.population_year_be})${
                        denom.is_fallback_year ? ' [Latest 2025 fallback]' : ''
                      } | Rate: ${measures.case_notification_rate?.toFixed(2)} / 100k`}
                </span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-amber-800 font-medium bg-amber-50 px-2.5 py-0.5 rounded-md border border-amber-200">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                <span>
                  {lang === 'th'
                    ? denom?.reason_th || 'ไม่คำนวณอัตราต่อประชากรในขอบเขตนี้ (แสดงจำนวนผู้ป่วยและสัดส่วน IPD % ตามปกติ)'
                    : denom?.reason_en || 'Population rate unavailable for this scope (counts and IPD % remain active)'}
                </span>
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
