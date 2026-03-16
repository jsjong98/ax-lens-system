"use client";

import { useEffect, useRef, useState } from "react";
import { Upload, FileSpreadsheet, CheckCircle2, AlertCircle, RefreshCw, Layers } from "lucide-react";
import {
  getCurrentFile,
  uploadExcel,
  getExcelSheets,
  selectExcelSheet,
  type UploadCurrentInfo,
  type ExcelSheet,
} from "@/lib/api";

interface Props {
  onUploaded?: (taskCount: number) => void;
}

export default function ExcelUploader({ onUploaded }: Props) {
  const [current, setCurrent]   = useState<UploadCurrentInfo | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [success, setSuccess]   = useState<string | null>(null);
  const [error, setError]       = useState<string | null>(null);
  const [sheets, setSheets]     = useState<ExcelSheet[]>([]);
  const [selectedSheet, setSelectedSheet] = useState<string>("");
  const [sheetLoading, setSheetLoading]   = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getCurrentFile().then((info) => {
      setCurrent(info);
      if (info.filename) {
        getExcelSheets()
          .then((res) => {
            setSheets(res.sheets);
            const rec = res.sheets.find((s) => s.recommended);
            if (rec) setSelectedSheet(rec.name);
          })
          .catch(() => {});
      }
    }).catch(() => {});
  }, []);

  const handleFile = async (file: File) => {
    if (!file.name.endsWith(".xlsx")) {
      setError(".xlsx 파일만 업로드 가능합니다.");
      return;
    }
    setUploading(true);
    setError(null);
    setSuccess(null);
    setProgress(0);

    try {
      const res = await uploadExcel(file, setProgress);
      setCurrent({ filename: res.filename, size_kb: Math.round(file.size / 1024), task_count: res.task_count });

      // 시트 목록 설정
      if (res.sheets && res.sheets.length > 0) {
        setSheets(res.sheets);
        const rec = res.sheets.find((s) => s.recommended);
        if (rec) {
          setSelectedSheet(rec.name);
          setSuccess(`"${res.filename}" 업로드 완료 — 시트 "${rec.name}" 자동 선택 (Task ${res.task_count}개)`);
        } else {
          setSuccess(`"${res.filename}" 업로드 완료 — 시트를 선택하세요`);
        }
      } else {
        setSuccess(`"${res.filename}" 업로드 완료 — Task ${res.task_count}개 로드됨`);
      }

      onUploaded?.(res.task_count);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
      setProgress(0);
    }
  };

  const handleSheetSelect = async (sheetName: string) => {
    setSelectedSheet(sheetName);
    setSheetLoading(true);
    setError(null);

    try {
      const res = await selectExcelSheet(sheetName);
      setCurrent((prev) => prev ? { ...prev, task_count: res.task_count } : prev);
      setSuccess(`시트 "${sheetName}" 로드 완료 — Task ${res.task_count}개`);
      onUploaded?.(res.task_count);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSheetLoading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <FileSpreadsheet className="h-5 w-5 text-emerald-600" />
          <span className="font-semibold text-gray-900 text-sm">입력 엑셀 파일</span>
        </div>
        {current?.filename && (
          <button
            onClick={() => inputRef.current?.click()}
            className="flex items-center gap-1 text-xs hover:underline"
            style={{ color: "#A62121" }}
          >
            <RefreshCw className="h-3.5 w-3.5" /> 교체
          </button>
        )}
      </div>

      <div className="px-5 py-4 space-y-3">
        {/* 현재 파일 정보 */}
        {current?.filename ? (
          <div className="flex items-center gap-3 rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-3">
            <FileSpreadsheet className="h-8 w-8 text-emerald-600 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-emerald-800 truncate">{current.filename}</p>
              <p className="text-xs text-emerald-600 mt-0.5">
                {current.size_kb} KB · Task {current.task_count}개
              </p>
            </div>
          </div>
        ) : (
          <p className="text-xs text-gray-400">로드된 파일 없음</p>
        )}

        {/* 시트 선택 */}
        {sheets.length > 0 && (
          <div className="rounded-lg border border-gray-200 overflow-hidden">
            <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 border-b border-gray-200">
              <Layers className="h-4 w-4 text-gray-500" />
              <span className="text-xs font-medium text-gray-600">시트 선택</span>
              {sheetLoading && (
                <span className="text-[10px] text-gray-400 ml-auto">로딩 중...</span>
              )}
            </div>
            <div className="divide-y divide-gray-100">
              {sheets.map((s) => (
                <button
                  key={s.name}
                  onClick={() => !s.is_guide && handleSheetSelect(s.name)}
                  disabled={s.is_guide || sheetLoading}
                  className={`w-full flex items-center justify-between px-3 py-2 text-left text-xs transition ${
                    s.is_guide
                      ? "opacity-40 cursor-not-allowed bg-gray-50"
                      : selectedSheet === s.name
                        ? "bg-red-50 border-l-2 border-red-500"
                        : "hover:bg-gray-50"
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className={`font-medium truncate ${
                      selectedSheet === s.name ? "text-red-700" : "text-gray-700"
                    }`}>
                      {s.name}
                    </span>
                    {s.is_guide && (
                      <span className="px-1.5 py-0.5 rounded bg-gray-200 text-gray-500 text-[10px]">가이드</span>
                    )}
                    {s.recommended && (
                      <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 text-[10px]">추천</span>
                    )}
                  </div>
                  <span className="text-gray-400 flex-shrink-0">
                    {s.is_guide ? "-" : `${s.task_count}개`}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 드래그&드롭 업로드 영역 */}
        {!current?.filename && (
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-8 transition-colors"
            style={{
              borderColor: dragging ? "#D95578" : "#DEDEDE",
              backgroundColor: dragging ? "#FFF5F7" : "#F5F5F5",
            }}
            onMouseEnter={(e) => { if (!dragging) { (e.currentTarget as HTMLElement).style.borderColor = "#F2A0AF"; (e.currentTarget as HTMLElement).style.backgroundColor = "#FFF5F7"; } }}
            onMouseLeave={(e) => { if (!dragging) { (e.currentTarget as HTMLElement).style.borderColor = "#DEDEDE"; (e.currentTarget as HTMLElement).style.backgroundColor = "#F5F5F5"; } }}
          >
            <Upload className="h-8 w-8" style={{ color: dragging ? "#A62121" : "#AAAAAA" }} />
            <div className="text-center">
              <p className="text-sm font-medium text-gray-700">
                클릭하거나 파일을 드래그해서 업로드
              </p>
              <p className="mt-0.5 text-xs text-gray-400">
                HR As-Is 템플릿 형식의 .xlsx 파일
              </p>
            </div>
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); e.target.value = ""; }}
        />

        {/* 진행 바 */}
        {uploading && (
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs text-gray-500">
              <span>업로드 중...</span>
              <span>{progress}%</span>
            </div>
              <div className="h-2 rounded-full bg-gray-200">
              <div
                className="h-2 rounded-full transition-all duration-200"
                style={{ width: `${progress}%`, backgroundColor: "#A62121" }}
              />
            </div>
          </div>
        )}

        {/* 성공 메시지 */}
        {success && (
          <div className="flex items-center gap-2 rounded-lg bg-emerald-50 border border-emerald-200 px-3 py-2 text-xs text-emerald-700">
            <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
            {success}
          </div>
        )}

        {/* 에러 메시지 */}
        {error && (
          <div className="flex items-center gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
