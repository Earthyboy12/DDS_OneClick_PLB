import React, { useState, useRef, useEffect } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Info,
  ShieldCheck,
  Database,
  RefreshCw,
  Trash2,
  Eye,
  ChevronDown,
  ChevronUp,
  Layers,
  Check,
  FileText,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import {
  getImportQueue,
  stageImportFiles,
  updateStagedImportFile,
  removeStagedImportFile,
  clearImportQueue,
  previewImportImpact,
  commitImportQueue,
  getImportSchema,
} from '../services/api';
import {
  StagedImportFileItem,
  ImportImpactPreview,
  FileCategory,
  ImportMode,
} from '../types';

export const ImportPage: React.FC = () => {
  const { lang, measures, loadSynthetic, refreshData, loading } = useApp();
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [stagedFiles, setStagedFiles] = useState<StagedImportFileItem[]>([]);
  const [canonicalFields, setCanonicalFields] = useState<
    Array<{ field: string; label_th: string; label_en: string; required?: boolean }>
  >([]);
  const [expandedFileId, setExpandedFileId] = useState<string | null>(null);
  const [importMode, setImportMode] = useState<ImportMode>('replace');
  const [impactPreview, setImpactPreview] = useState<ImportImpactPreview | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [maxUploadMb, setMaxUploadMb] = useState<number>(200);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getImportSchema()
      .then((res: any) => {
        setCanonicalFields(res.canonical_fields || []);
        if (res.max_upload_size_mb) {
          setMaxUploadMb(res.max_upload_size_mb);
        }
      })
      .catch(console.error);
    getImportQueue()
      .then((res) => setStagedFiles(res.queue || []))
      .catch(console.error);
  }, []);

  const handleFilesSelected = async (fileList: FileList | File[]) => {
    const filesArray = Array.from(fileList);
    if (filesArray.length === 0) return;

    for (const f of filesArray) {
      if (f.size > maxUploadMb * 1024 * 1024) {
        setErrorMessage(
          lang === 'th'
            ? `ไฟล์ ${f.name} มีขนาดเกินขีดจำกัด ${maxUploadMb} MB`
            : `File ${f.name} exceeds ${maxUploadMb} MB limit.`
        );
        return;
      }
    }

    try {
      setUploading(true);
      setErrorMessage(null);
      setImpactPreview(null);
      setUploadMessage(
        lang === 'th'
          ? `กำลังตรวจสอบและเตรียมไฟล์ (${filesArray.length} ไฟล์)...`
          : `Inspecting and staging ${filesArray.length} file(s)...`
      );
      const res = await stageImportFiles(filesArray);
      setStagedFiles(res.queue || []);
      if (res.staged_Now && res.staged_Now.length === 1) {
        setExpandedFileId(res.staged_Now[0].staged_id);
      }
      setUploadMessage(
        lang === 'th'
          ? `เพิ่มไฟล์เข้าคิวตรวจสอบ ${filesArray.length} ไฟล์เรียบร้อย กรุณาตรวจสอบการตั้งค่าและกดยืนยันการนำเข้า`
          : `Staged ${filesArray.length} file(s) in queue. Review settings and confirm import below.`
      );
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to stage files');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleUpdateConfig = async (
    stagedId: string,
    patch: {
      file_category?: FileCategory;
      selected_sheet?: string;
      encoding?: string;
      delimiter?: string;
      custom_mappings?: Record<string, string>;
    }
  ) => {
    try {
      setUploading(true);
      setErrorMessage(null);
      setImpactPreview(null);
      const res = await updateStagedImportFile(stagedId, patch);
      setStagedFiles(res.queue || []);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to update file config');
    } finally {
      setUploading(false);
    }
  };

  const handleRemoveStaged = async (stagedId: string) => {
    try {
      setUploading(true);
      setImpactPreview(null);
      const res = await removeStagedImportFile(stagedId);
      setStagedFiles(res.queue || []);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to remove file');
    } finally {
      setUploading(false);
    }
  };

  const handleClearQueue = async () => {
    try {
      setUploading(true);
      setImpactPreview(null);
      await clearImportQueue();
      setStagedFiles([]);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to clear queue');
    } finally {
      setUploading(false);
    }
  };

  const handlePreviewImpact = async () => {
    try {
      setUploading(true);
      setErrorMessage(null);
      const preview = await previewImportImpact(importMode);
      setImpactPreview(preview);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to preview import impact');
    } finally {
      setUploading(false);
    }
  };

  const handleCommitImport = async () => {
    try {
      setUploading(true);
      setErrorMessage(null);
      const res = await commitImportQueue(importMode);
      setStagedFiles([]);
      setImpactPreview(null);
      await refreshData();
      setUploadMessage(
        lang === 'th'
          ? `นำเข้าและรวมข้อมูลสำเร็จ (${importMode === 'append' ? 'โหมดเพิ่มเข้ากับเซสชันเดิม' : 'โหมดสร้างชุดข้อมูลวิเคราะห์ใหม่'}) — ผู้ป่วยเข้าเกณฑ์ C = ${res.audit_trail?.eligible_episodes_C?.toLocaleString() ?? 0} ราย`
          : `Successfully committed import (${importMode}) — Eligible cases C = ${res.audit_trail?.eligible_episodes_C?.toLocaleString() ?? 0}`
      );
    } catch (err: any) {
      setErrorMessage(err.message || 'Commit import failed');
    } finally {
      setUploading(false);
    }
  };

  const audit = measures?.audit_trail;
  const hasReadyFiles = stagedFiles.length > 0;

  return (
    <div className="space-y-6">
      {/* Privacy Notice Banner */}
      <div className="p-4 rounded-xl bg-slate-900 text-white flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-teal-500/20 text-teal-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div className="text-xs sm:text-sm">
            <span className="font-semibold text-teal-300">
              {lang === 'th' ? 'การคุ้มครองข้อมูลส่วนบุคคล (PDPA Compliant)' : 'Local Privacy Protection'}
            </span>
            <p className="text-slate-300 text-xs mt-0.5">
              {lang === 'th'
                ? 'ประมวลผลบนเครื่องของคุณแบบ Local เท่านั้น หมายเลข CID ถูกแฮชเพื่อคัดกรองระเบียนซ้ำข้ามไฟล์และถูกตัดออกจากผลลัพธ์ทั้งหมด'
                : 'Processed locally in memory. CIDs are cryptographically hashed for cross-file deduplication and stripped from all outputs.'}
            </p>
          </div>
        </div>
        <span className="hidden md:inline-block text-[11px] px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-mono">
          Multi-File .XLSX & .CSV
        </span>
      </div>

      {/* Main Upload & Synthetic Generator Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Multi-File Upload Card (7 cols) */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="p-2.5 rounded-xl bg-teal-50 text-teal-600">
                  <UploadCloud className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-800 text-base">
                    {lang === 'th'
                      ? 'นำเข้าข้อมูลหลายไฟล์พร้อมกัน (Multi-File Excel & CSV Import)'
                      : 'Multi-File Excel (.xlsx) & CSV (.csv) Import'}
                  </h3>
                  <p className="text-xs text-slate-500">
                    {lang === 'th'
                      ? 'เลือกหรือลากวางหลายไฟล์พร้อมกัน รองรับ .xlsx และ .csv (UTF-8, UTF-8 BOM, Thai CP874/TIS-620) คงเลข 0 นำหน้าเสมอ'
                      : 'Select or drag-and-drop multiple .xlsx and .csv files at once. Preserves leading zeros and resolves cross-file revisions.'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-semibold text-teal-700 bg-teal-50 border border-teal-200 px-2 py-0.5 rounded-md">
                  .XLSX
                </span>
                <span className="text-[11px] font-semibold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-md">
                  .CSV
                </span>
                <span className="text-[11px] font-semibold text-emerald-800 bg-emerald-50 border border-emerald-300 px-2 py-0.5 rounded-md">
                  ≤ {maxUploadMb} MB
                </span>
              </div>
            </div>

            <div
              onDragOver={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setDragActive(true);
              }}
              onDragLeave={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setDragActive(false);
              }}
              onDrop={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setDragActive(false);
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                  handleFilesSelected(e.dataTransfer.files);
                }
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-7 text-center cursor-pointer transition group ${
                dragActive
                  ? 'border-teal-500 bg-teal-50/40'
                  : 'border-slate-200 hover:border-teal-500 bg-slate-50/50 hover:bg-teal-50/20'
              }`}
            >
              <div className="flex items-center justify-center gap-3 mb-2">
                <FileSpreadsheet className="w-9 h-9 text-teal-600 transition group-hover:scale-105" />
                <FileText className="w-9 h-9 text-blue-600 transition group-hover:scale-105" />
              </div>
              <p className="text-sm font-semibold text-slate-700 group-hover:text-teal-900">
                {lang === 'th'
                  ? 'คลิกเพื่อเลือกหลายไฟล์ หรือลากไฟล์ .xlsx / .csv มาวางที่นี่'
                  : 'Click to select multiple files or drag and drop .xlsx / .csv files here'}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                {lang === 'th'
                  ? 'รองรับการนำเข้าแยกประเภทไฟล์ชัดเจน: (1) ข้อมูลผู้ป่วย (2) ข้อมูลประชากร (3) ตารางรหัสพื้นที่'
                  : 'Supports explicit separation of Patient Cases, Population Denominators, and Geography Crosswalks'}
              </p>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".xlsx,.xls,.csv"
                onChange={(e) => e.target.files && handleFilesSelected(e.target.files)}
                className="hidden"
              />
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 grid grid-cols-3 gap-2 text-[11px] text-slate-600">
            <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
              <span className="font-bold text-slate-800 block">1. ข้อมูลผู้ป่วย (Cases)</span>
              <span>จับคู่คอลัมน์ ตรวจซ้ำข้ามไฟล์ และเก็บ source_file/sheet/row</span>
            </div>
            <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
              <span className="font-bold text-slate-800 block">2. ประชากร (Population)</span>
              <span>อัปเดตตัวหารประชากรโดยไม่ปะปนกับแถวผู้ป่วย</span>
            </div>
            <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
              <span className="font-bold text-slate-800 block">3. รหัสพื้นที่ (Geography)</span>
              <span>เพิ่มตารางอ้างอิงรหัสจังหวัด/อำเภอโดยไม่ปนกับแถวผู้ป่วย</span>
            </div>
          </div>
        </div>

        {/* One-Click Synthetic Demo Card (5 cols) */}
        <div className="lg:col-span-5 bg-gradient-to-br from-navy-800 to-navy-900 rounded-2xl border border-navy-700 p-6 text-white shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2.5 rounded-xl bg-teal-500/20 text-teal-400">
                  <Sparkles className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-base">
                    {lang === 'th' ? 'ชุดข้อมูลสังเคราะห์ One-Click' : 'One-Click Synthetic Demo'}
                  </h3>
                  <p className="text-xs text-slate-400">
                    {lang === 'th' ? '20,172 รายการ พร้อมทดสอบทุกฟีเจอร์ทันที' : '20,172 records with realistic data nuances'}
                  </p>
                </div>
              </div>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-amber-400/20 text-amber-300 border border-amber-400/30">
                {lang === 'th' ? 'พร้อมใช้งาน' : 'Ready'}
              </span>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed mb-3">
              {lang === 'th'
                ? 'สร้างชุดข้อมูลเสมือนจริงเชื่อมกับฐานข้อมูล dds_reference.sqlite (77 จังหวัด, 878 อำเภอ, ประชากรปี 2013–2025) ทดสอบการคำนวณอัตราป่วยจังหวัดเดียว หลายจังหวัด และทั่วประเทศได้ทันที'
                : 'Generates a demonstration dataset connected to dds_reference.sqlite (77 provinces, 878 districts, 2013–2025 population snapshots).'}
            </p>

            <div className="space-y-1.5 text-xs text-slate-300 bg-navy-950/60 p-3 rounded-xl border border-navy-700/50">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-teal-400 flex-shrink-0" />
                <span>{lang === 'th' ? '20,172 ระเบียน + 150 แถวว่างท้ายตาราง' : '20,172 records + 150 trailing blank rows'}</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-teal-400 flex-shrink-0" />
                <span>{lang === 'th' ? 'เชื่อม dds_reference.sqlite (77 จังหวัด, 878 อำเภอ)' : 'Connected to dds_reference.sqlite'}</span>
              </div>
            </div>
          </div>

          <div className="mt-4">
            <button
              onClick={loadSynthetic}
              disabled={loading || uploading}
              className="w-full py-2.5 px-4 rounded-xl bg-teal-600 hover:bg-teal-500 active:scale-[0.99] text-white font-semibold text-sm transition shadow-lg shadow-teal-900/40 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading || uploading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>{lang === 'th' ? 'กำลังประมวลผล...' : 'Processing...'}</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>{lang === 'th' ? 'สร้างและโหลดข้อมูลสังเคราะห์ทันที' : 'Generate & Load Synthetic Data'}</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Upload / Error Messages */}
      {uploadMessage && (
        <div className="p-3 rounded-xl bg-teal-50 border border-teal-200 text-teal-800 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-teal-600 flex-shrink-0" />
          <span>{uploadMessage}</span>
        </div>
      )}
      {errorMessage && (
        <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* STAGED MULTI-FILE IMPORT QUEUE & PREVIEW WORKBENCH */}
      {stagedFiles.length > 0 && (
        <div className="bg-white rounded-2xl border-2 border-teal-500/80 p-6 shadow-md space-y-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-200 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-teal-600" />
                <h3 className="font-bold text-slate-900 text-base">
                  {lang === 'th'
                    ? `คิวตรวจสอบและตั้งค่าไฟล์ก่อนนำเข้า (${stagedFiles.length} ไฟล์)`
                    : `Staged Import Queue & Column Mapping (${stagedFiles.length} files)`}
                </h3>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                {lang === 'th'
                  ? 'ตรวจสอบประเภทไฟล์ ชีต Excel รหัสภาษา CSV และการจับคู่คอลัมน์ของแต่ละไฟล์ก่อนกดยืนยันการนำเข้า'
                  : 'Verify file category, Excel sheet, CSV encoding/delimiter, and column mapping for each file before confirming.'}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {/* Replace vs Append Mode Selector */}
              <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs">
                <button
                  onClick={() => {
                    setImportMode('replace');
                    setImpactPreview(null);
                  }}
                  className={`px-3 py-1.5 rounded-lg font-semibold transition ${
                    importMode === 'replace'
                      ? 'bg-navy-800 text-white shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {lang === 'th' ? 'สร้างชุดข้อมูลใหม่ (Replace)' : 'New Dataset (Replace)'}
                </button>
                <button
                  onClick={() => {
                    setImportMode('append');
                    setImpactPreview(null);
                  }}
                  className={`px-3 py-1.5 rounded-lg font-semibold transition ${
                    importMode === 'append'
                      ? 'bg-teal-700 text-white shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {lang === 'th' ? 'เพิ่มเข้ากับเซสชันเดิม (Append)' : 'Append to Current Session'}
                </button>
              </div>

              <button
                onClick={handleClearQueue}
                disabled={uploading}
                className="px-3 py-1.5 rounded-xl border border-rose-200 text-rose-700 hover:bg-rose-50 text-xs font-medium transition"
              >
                {lang === 'th' ? 'ล้างคิวทั้งหมด' : 'Clear Queue'}
              </button>
            </div>
          </div>

          {/* Per-file cards */}
          <div className="space-y-3">
            {stagedFiles.map((fileItem) => {
              const isExpanded = expandedFileId === fileItem.staged_id;
              return (
                <div
                  key={fileItem.staged_id}
                  className={`rounded-xl border transition ${
                    fileItem.status === 'ready'
                      ? 'border-slate-200 bg-slate-50/40'
                      : 'border-amber-300 bg-amber-50/30'
                  }`}
                >
                  <div className="p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <span
                        className={`px-2 py-1 rounded-lg font-mono text-xs font-bold uppercase ${
                          fileItem.file_format === 'csv'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-teal-100 text-teal-800'
                        }`}
                      >
                        .{fileItem.file_format}
                      </span>
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-bold text-slate-900 text-sm">{fileItem.filename}</span>
                          <span
                            className={`text-[11px] px-2 py-0.5 rounded-full font-semibold ${
                              fileItem.status === 'ready'
                                ? 'bg-emerald-100 text-emerald-800'
                                : fileItem.status === 'warning'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-rose-100 text-rose-800'
                            }`}
                          >
                            {fileItem.status === 'ready'
                              ? lang === 'th'
                                ? 'พร้อมนำเข้า (Ready)'
                                : 'Ready'
                              : fileItem.status === 'warning'
                              ? lang === 'th'
                                ? 'มีข้อสังเกต (Review)'
                                : 'Review Warnings'
                              : 'Error'}
                          </span>
                          <span className="text-xs text-slate-500 font-mono">
                            {fileItem.total_rows.toLocaleString()} {lang === 'th' ? 'แถวดิบ' : 'raw rows'}
                            {fileItem.trailing_blanks > 0 && ` (-${fileItem.trailing_blanks} blanks)`}
                          </span>
                        </div>

                        {/* Issues / Warnings */}
                        {fileItem.issues && fileItem.issues.length > 0 && (
                          <div className="mt-1.5 space-y-0.5">
                            {fileItem.issues.map((iss, i) => (
                              <div key={i} className="text-[11px] text-amber-800 flex items-center gap-1">
                                <AlertTriangle className="w-3 h-3 text-amber-600 flex-shrink-0" />
                                <span>{lang === 'th' ? iss.message_th : iss.message_en}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Per-file Controls */}
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      {/* File Category Selector */}
                      <div className="flex items-center gap-1">
                        <span className="text-[11px] text-slate-500 font-medium">
                          {lang === 'th' ? 'ประเภทไฟล์:' : 'Category:'}
                        </span>
                        <select
                          value={fileItem.file_category}
                          onChange={(e) =>
                            handleUpdateConfig(fileItem.staged_id, {
                              file_category: e.target.value as FileCategory,
                            })
                          }
                          className="px-2 py-1 rounded-lg border border-slate-300 bg-white text-slate-800 font-semibold"
                        >
                          <option value="cases">
                            {lang === 'th' ? 'ข้อมูลผู้ป่วย (Patient Cases)' : 'Patient Cases'}
                          </option>
                          <option value="population">
                            {lang === 'th' ? 'ข้อมูลประชากร (Population)' : 'Population Denominator'}
                          </option>
                          <option value="geography">
                            {lang === 'th' ? 'ตารางรหัสพื้นที่ (Geography Codes)' : 'Geography Crosswalk'}
                          </option>
                        </select>
                      </div>

                      {/* Excel Sheet Selector */}
                      {fileItem.file_format === 'xlsx' && fileItem.sheets && fileItem.sheets.length > 0 && (
                        <div className="flex items-center gap-1">
                          <span className="text-[11px] text-slate-500 font-medium">
                            {lang === 'th' ? 'ชีต (Sheet):' : 'Sheet:'}
                          </span>
                          <select
                            value={fileItem.selected_sheet || fileItem.sheets[0]}
                            onChange={(e) =>
                              handleUpdateConfig(fileItem.staged_id, {
                                selected_sheet: e.target.value,
                              })
                            }
                            className="px-2 py-1 rounded-lg border border-slate-300 bg-white text-slate-800 font-mono"
                          >
                            {fileItem.sheets.map((s: string) => (
                              <option key={s} value={s}>
                                {s}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}

                      {/* CSV Encoding & Delimiter Selectors */}
                      {fileItem.file_format === 'csv' && (
                        <>
                          <div className="flex items-center gap-1">
                            <span className="text-[11px] text-slate-500 font-medium">Encoding:</span>
                            <select
                              value={fileItem.encoding}
                              onChange={(e) =>
                                handleUpdateConfig(fileItem.staged_id, { encoding: e.target.value })
                              }
                              className="px-2 py-1 rounded-lg border border-slate-300 bg-white text-slate-800 font-mono"
                            >
                              <option value="auto">Auto ({fileItem.encoding_used})</option>
                              <option value="utf-8-sig">UTF-8 / BOM</option>
                              <option value="utf-8">UTF-8</option>
                              <option value="cp874">Thai (CP874 / TIS-620)</option>
                              <option value="tis-620">TIS-620</option>
                              <option value="latin1">Latin-1</option>
                            </select>
                          </div>
                          <div className="flex items-center gap-1">
                            <span className="text-[11px] text-slate-500 font-medium">Delimiter:</span>
                            <select
                              value={fileItem.delimiter}
                              onChange={(e) =>
                                handleUpdateConfig(fileItem.staged_id, { delimiter: e.target.value })
                              }
                              className="px-2 py-1 rounded-lg border border-slate-300 bg-white text-slate-800 font-mono"
                            >
                              <option value="auto">Auto</option>
                              <option value=",">Comma (,)</option>
                              <option value=";">Semicolon (;)</option>
                              <option value="\t">Tab (\t)</option>
                              <option value="|">Pipe (|)</option>
                            </select>
                          </div>
                        </>
                      )}

                      {/* Preview & Column Mapping Toggle */}
                      <button
                        onClick={() =>
                          setExpandedFileId(isExpanded ? null : fileItem.staged_id)
                        }
                        className="px-2.5 py-1 rounded-lg border border-slate-300 bg-white hover:bg-slate-100 text-slate-700 font-medium flex items-center gap-1"
                      >
                        <Eye className="w-3.5 h-3.5 text-teal-600" />
                        <span>{lang === 'th' ? 'ดูตัวอย่าง & จับคู่คอลัมน์' : 'Preview & Map'}</span>
                        {isExpanded ? (
                          <ChevronUp className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5" />
                        )}
                      </button>

                      {/* Remove File Button */}
                      <button
                        onClick={() => handleRemoveStaged(fileItem.staged_id)}
                        title={lang === 'th' ? 'ลบไฟล์นี้ออกจากคิว' : 'Remove file from queue'}
                        className="p-1.5 rounded-lg border border-rose-200 text-rose-600 hover:bg-rose-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Expanded Column Mapping & 5-Row Preview */}
                  {isExpanded && (
                    <div className="border-t border-slate-200 p-4 bg-white rounded-b-xl space-y-4 text-xs">
                      {fileItem.file_category === 'cases' && (
                        <div>
                          <h5 className="font-bold text-slate-800 mb-2">
                            {lang === 'th'
                              ? 'การจับคู่คอลัมน์เข้ากับโครงสร้างมาตรฐาน (Canonical Column Mapping):'
                              : 'Canonical Schema Column Mapping:'}
                          </h5>
                          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2.5">
                            {canonicalFields.map((fieldItem) => {
                              const currentMapped = fileItem.std_to_detected?.[fieldItem.field] || '';
                              return (
                                <div
                                  key={fieldItem.field}
                                  className={`p-2 rounded-lg border ${
                                    fieldItem.required && !currentMapped
                                      ? 'border-amber-300 bg-amber-50/40'
                                      : 'border-slate-200 bg-slate-50/60'
                                  }`}
                                >
                                  <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                                    {lang === 'th' ? fieldItem.label_th : fieldItem.label_en}
                                    {fieldItem.required && <span className="text-rose-600 ml-0.5">*</span>}
                                  </label>
                                  <select
                                    value={currentMapped}
                                    onChange={(e) => {
                                      const nextMap = { ...fileItem.std_to_detected };
                                      if (e.target.value) {
                                        nextMap[fieldItem.field] = e.target.value;
                                      } else {
                                        delete nextMap[fieldItem.field];
                                      }
                                      handleUpdateConfig(fileItem.staged_id, {
                                        custom_mappings: nextMap,
                                      });
                                    }}
                                    className="w-full px-2 py-1 rounded border border-slate-300 bg-white text-slate-800 font-mono text-[11px]"
                                  >
                                    <option value="">
                                      {lang === 'th' ? '-- ไม่ได้ระบุ --' : '-- Unmapped --'}
                                    </option>
                                    {fileItem.columns.map((col) => (
                                      <option key={col} value={col}>
                                        {col}
                                      </option>
                                    ))}
                                  </select>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* 5-Row Sample Data Preview */}
                      <div>
                        <h5 className="font-bold text-slate-800 mb-2">
                          {lang === 'th'
                            ? 'ตัวอย่างข้อมูล 5 แถวแรก (คงเลข 0 นำหน้าสำหรับรหัสจังหวัด/อำเภอ/รหัสประจำตัว):'
                            : 'First 5 Rows Preview (Preserving Leading Zeros):'}
                        </h5>
                        {fileItem.preview_rows && fileItem.preview_rows.length > 0 ? (
                          <div className="overflow-x-auto border border-slate-200 rounded-lg max-h-56">
                            <table className="w-full text-[11px] text-left font-mono">
                              <thead className="bg-slate-100 border-b border-slate-200 text-slate-700">
                                <tr>
                                  {fileItem.columns.slice(0, 12).map((col) => (
                                    <th key={col} className="py-1.5 px-2.5 whitespace-nowrap">
                                      {col}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-100">
                                {fileItem.preview_rows.map((row, idx) => (
                                  <tr key={idx} className="hover:bg-slate-50">
                                    {fileItem.columns.slice(0, 12).map((col) => (
                                      <td key={col} className="py-1.5 px-2.5 whitespace-nowrap text-slate-800">
                                        {String(row[col] ?? '')}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <p className="text-slate-400 italic">No preview rows available.</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Impact Preview Card (when requested) */}
          {impactPreview && (
            <div className="p-4 rounded-xl bg-teal-50/70 border border-teal-300 space-y-2 text-xs">
              <div className="font-bold text-teal-950 flex items-center justify-between">
                <span>
                  {lang === 'th'
                    ? 'สรุปผลกระทบก่อนยืนยันการรวมข้อมูล (Pre-Merge Impact Preview):'
                    : 'Pre-Commit Merge & Deduplication Impact Preview:'}
                </span>
                <span className="font-mono text-teal-800">
                  Mode: {impactPreview.import_mode.toUpperCase()}
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 pt-1">
                <div className="p-2.5 rounded-lg bg-white border border-teal-200">
                  <span className="text-[10px] text-slate-500 block">
                    {lang === 'th' ? 'ผู้ป่วยเดิมในเซสชัน' : 'Existing Cases'}
                  </span>
                  <span className="font-mono font-bold text-sm text-slate-800">
                    {impactPreview.existing_eligible_cases.toLocaleString()}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-white border border-teal-200">
                  <span className="text-[10px] text-slate-500 block">
                    {lang === 'th' ? 'แถวผู้ป่วยในคิว' : 'Staged Patient Rows'}
                  </span>
                  <span className="font-mono font-bold text-sm text-slate-800">
                    {impactPreview.incoming_raw_rows.toLocaleString()}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-white border border-teal-200">
                  <span className="text-[10px] text-slate-500 block">
                    {lang === 'th' ? 'ตัดแถวซ้ำทุกประการ' : 'Exact Duplicates Removed'}
                  </span>
                  <span className="font-mono font-bold text-sm text-amber-700">
                    -{impactPreview.exact_duplicates_removed.toLocaleString()}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-white border border-teal-200">
                  <span className="text-[10px] text-slate-500 block">
                    {lang === 'th' ? 'ยุบรวมประวัติแก้ไขข้ามไฟล์' : 'Revisions Superseded'}
                  </span>
                  <span className="font-mono font-bold text-sm text-blue-700">
                    -{impactPreview.cross_file_revisions_superseded.toLocaleString()}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-white border border-teal-200">
                  <span className="text-[10px] text-slate-500 block">
                    {lang === 'th' ? 'ผู้ป่วยเข้าเกณฑ์สุทธิ (C)' : 'Final Eligible (C)'}
                  </span>
                  <span className="font-mono font-bold text-sm text-teal-800">
                    {impactPreview.resulting_eligible_cases_C.toLocaleString()}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-white border border-teal-200">
                  <span className="text-[10px] text-slate-500 block">
                    {lang === 'th' ? 'เปลี่ยนแปลงสุทธิ' : 'Net Cases Delta'}
                  </span>
                  <span className="font-mono font-bold text-sm text-emerald-700">
                    {impactPreview.net_change_cases >= 0
                      ? `+${impactPreview.net_change_cases.toLocaleString()}`
                      : impactPreview.net_change_cases.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons: Preview Impact & Confirm Import */}
          <div className="flex flex-wrap items-center justify-end gap-3 pt-2">
            <button
              onClick={handlePreviewImpact}
              disabled={uploading || !hasReadyFiles}
              className="px-4 py-2.5 rounded-xl border border-teal-600 text-teal-700 hover:bg-teal-50 font-semibold text-xs transition flex items-center gap-1.5 disabled:opacity-50"
            >
              <Eye className="w-4 h-4" />
              <span>
                {lang === 'th'
                  ? 'ดูตัวอย่างผลกระทบก่อนยืนยัน (Preview Impact)'
                  : 'Preview Merge Impact'}
              </span>
            </button>

            <button
              onClick={handleCommitImport}
              disabled={uploading || !hasReadyFiles}
              className="px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs shadow-md shadow-teal-700/20 transition flex items-center gap-2 disabled:opacity-50"
            >
              <Check className="w-4 h-4" />
              <span>
                {lang === 'th'
                  ? `ยืนยันการนำเข้าข้อมูล (${importMode === 'append' ? 'เพิ่มเข้าเซสชันเดิม' : 'สร้างชุดข้อมูลใหม่'})`
                  : `Confirm & Commit Import (${importMode.toUpperCase()})`}
              </span>
            </button>
          </div>
        </div>
      )}

      {/* Auditable Data Ingestion & Eligibility Flow */}
      {audit && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h3 className="font-bold text-slate-800 text-base">
                {lang === 'th'
                  ? 'ขั้นตอนการคัดกรองและตรวจสอบที่มาของข้อมูล (Auditable Multi-File Eligibility & Provenance Flow)'
                  : 'Auditable Multi-File Ingestion & Eligibility Flow'}
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                {lang === 'th'
                  ? 'แสดงกระบวนการตั้งแต่แถวดิบ การตัดแถวซ้ำข้ามไฟล์ การยุบประวัติแก้ไข จนถึงผู้ป่วยเข้าเกณฑ์ C'
                  : 'Traceable pathway from raw imported files, cross-file deduplication, and revision resolution to eligible episodes C'}
              </p>
            </div>
            <span className="text-xs font-mono px-3 py-1 rounded-full bg-teal-50 text-teal-700 font-semibold border border-teal-200">
              C = {(audit.eligible_episodes_C ?? 0).toLocaleString()} {lang === 'th' ? 'ราย' : 'cases'}
            </span>
          </div>

          {/* Audit Flow Steps Grid */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-xs font-semibold text-slate-500 block mb-1">
                {lang === 'th' ? '1. แถวดิบที่นำเข้าทั้งหมด' : '1. Total Raw Imported Rows'}
              </span>
              <div className="text-xl font-bold text-slate-800 font-mono">
                {(audit.total_rows_imported ?? audit.eligible_episodes_C ?? 0).toLocaleString()}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                {lang === 'th' ? 'ตัดแถวว่างท้ายตาราง:' : 'Trailing blanks stripped:'}{' '}
                <span className="font-semibold text-slate-700">
                  -{(audit.trailing_blanks_removed ?? 0).toLocaleString()}
                </span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-xs font-semibold text-slate-500 block mb-1">
                {lang === 'th' ? '2. ตัดซ้ำ & ยุบประวัติแก้ไขข้ามไฟล์' : '2. Cross-File Deduplication'}
              </span>
              <div className="text-xl font-bold text-slate-800 font-mono">
                {(audit.authoritative_episodes_total ?? audit.eligible_episodes_C ?? 0).toLocaleString()}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                {lang === 'th' ? 'ซ้ำทุกประการ:' : 'Exact dup:'}{' '}
                <span className="font-semibold text-amber-700">
                  -{(audit.exact_duplicates_removed ?? 0).toLocaleString()}
                </span>{' '}
                | {lang === 'th' ? 'Revision เก่า:' : 'Revisions:'}{' '}
                <span className="font-semibold text-blue-700">
                  -{(audit.cross_file_revisions_superseded ?? audit.superseded_revisions_removed ?? 0).toLocaleString()}
                </span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-xs font-semibold text-slate-500 block mb-1">
                {lang === 'th' ? '3. กรองสถานะรายงาน' : '3. Status Filtering'}
              </span>
              <div className="text-xl font-bold text-slate-800 font-mono">
                {(audit.eligible_episodes_C ?? 0).toLocaleString()}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                {lang === 'th' ? 'ตัดยกเลิก/รอแก้ไข:' : 'Cancelled/pending:'}{' '}
                <span className="font-semibold text-rose-600">
                  -{((audit.cancelled_episodes_excluded ?? 0) + (audit.pending_or_other_excluded ?? 0)).toLocaleString()}
                </span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-teal-50 border border-teal-200">
              <span className="text-xs font-semibold text-teal-800 block mb-1">
                {lang === 'th' ? '4. ผู้ป่วยเข้าเกณฑ์ (C)' : '4. Eligible Episodes (C)'}
              </span>
              <div className="text-xl font-bold text-teal-900 font-mono">
                {(audit.eligible_episodes_C ?? 0).toLocaleString()}
              </div>
              <div className="text-[11px] text-teal-700 mt-1">
                IPD: {(audit.ipd_episodes_H ?? 0).toLocaleString()} | OPD: {(audit.opd_episodes_O ?? 0).toLocaleString()} | U:{' '}
                {(audit.unknown_patient_type_U ?? 0).toLocaleString()}
              </div>
            </div>
          </div>

          {/* Source Files Provenance Breakdown */}
          {audit.source_files_summary && audit.source_files_summary.length > 0 && (
            <div className="pt-2">
              <h4 className="text-xs font-bold text-slate-700 mb-2">
                {lang === 'th'
                  ? 'ตารางตรวจสอบที่มาของระเบียนตามไฟล์และชีตต้นทาง (Source File & Sheet Provenance):'
                  : 'Source File & Sheet Provenance Summary:'}
              </h4>
              <div className="overflow-x-auto border border-slate-200 rounded-xl">
                <table className="w-full text-xs text-left font-mono">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                    <tr>
                      <th className="py-2 px-3 font-semibold">{lang === 'th' ? 'ไฟล์ต้นทาง (source_file)' : 'source_file'}</th>
                      <th className="py-2 px-3 font-semibold">{lang === 'th' ? 'ชีตต้นทาง (source_sheet)' : 'source_sheet'}</th>
                      <th className="py-2 px-3 font-semibold text-right">
                        {lang === 'th' ? 'จำนวนแถวที่ไม่ว่าง' : 'Non-Empty Rows'}
                      </th>
                      <th className="py-2 px-3 font-semibold text-right">
                        {lang === 'th' ? 'ผู้ป่วยเข้าเกณฑ์สุทธิ (C)' : 'Eligible Episodes (C)'}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {audit.source_files_summary.map((sf, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/70">
                        <td className="py-2 px-3 font-semibold text-slate-900">{sf.source_file}</td>
                        <td className="py-2 px-3 text-slate-600">{sf.source_sheet}</td>
                        <td className="py-2 px-3 text-right text-slate-700">{(sf.non_empty_rows ?? 0).toLocaleString()}</td>
                        <td className="py-2 px-3 text-right font-bold text-teal-800">
                          {(sf.eligible_contributed ?? 0).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Key Data Quality Flags */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
            <div className="p-3.5 rounded-xl border border-amber-200 bg-amber-50/60">
              <div className="flex items-center gap-2 text-amber-900 font-semibold text-xs mb-1">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <span>{lang === 'th' ? 'ไม่ระบุประเภทผู้ป่วย (Missing Type)' : 'Missing Patient Type'}</span>
              </div>
              <div className="text-lg font-bold text-amber-950 font-mono">
                {(audit.patient_type_missing_pct ?? 0).toFixed(1)}%
              </div>
              <p className="text-[11px] text-amber-800 mt-0.5">
                {lang === 'th'
                  ? `${(audit.unknown_patient_type_U ?? 0).toLocaleString()} ราย (ไม่แปลงเป็น OPD ตามหลักระบาดวิทยา)`
                  : `${(audit.unknown_patient_type_U ?? 0).toLocaleString()} unknown cases; never converted to OPD`}
              </p>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50">
              <div className="flex items-center gap-2 text-slate-800 font-semibold text-xs mb-1">
                <Info className="w-4 h-4 text-slate-500" />
                <span>{lang === 'th' ? 'อายุผิดปกติที่ตรวจพบ (Suspicious Age)' : 'Suspicious Age Flags'}</span>
              </div>
              <div className="text-lg font-bold text-slate-900 font-mono">
                {(audit.suspicious_age_count ?? 0).toLocaleString()} {lang === 'th' ? 'ราย' : 'cases'}
              </div>
              <p className="text-[11px] text-slate-600 mt-0.5">
                {lang === 'th'
                  ? 'อายุ > 120 ปี หรือเป็นลบ (คงไว้ในชุดข้อมูลพร้อมติดธงเตือน)'
                  : 'Age > 120 or negative (flagged without silent deletion)'}
              </p>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50">
              <div className="flex items-center gap-2 text-slate-800 font-semibold text-xs mb-1">
                <Database className="w-4 h-4 text-slate-500" />
                <span>{lang === 'th' ? 'ผู้เสียชีวิตที่บันทึกไว้' : 'Recorded Deaths'}</span>
              </div>
              <div className="text-lg font-bold text-slate-900 font-mono">
                {audit.recorded_deaths_count ?? 0} {lang === 'th' ? 'ราย' : 'deaths'}
              </div>
              <p className="text-[11px] text-slate-600 mt-0.5">
                {lang === 'th'
                  ? 'ตรวจสอบจากวันที่เสียชีวิตในชุดข้อมูลทั้งหมด'
                  : 'Count of records with recorded death dates'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
