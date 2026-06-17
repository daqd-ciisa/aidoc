import { useCallback, useEffect, useRef, useState } from "react";
import {
  BookMarked,
  CloudUpload,
  FileText,
  FileType2,
  FileCode2,
  FileSpreadsheet,
  File as FileIcon,
  Cloud,
  Share2,
  HardDriveDownload,
  RotateCw,
  Settings2,
  Trash2,
  Loader2,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  deleteDocument,
  listDocuments,
  reindexDocument,
  uploadDocuments,
} from "../api/documents";
import { importFromGoogleDrive } from "../api/connectors";
import { isGoogleDriveConfigured, pickFromDrive } from "../lib/googleDrive";
import type { DocumentRead } from "../api/types";
import StatusBadge from "../components/StatusBadge";
import GoogleSettingsModal from "../components/GoogleSettingsModal";
import OneDrivePickerModal from "../components/OneDrivePickerModal";
import SharePointPickerModal from "../components/SharePointPickerModal";
import type { ImportResult } from "../api/connectors";

const ACCEPT = ".pdf,.docx,.txt,.md,.xlsx,.csv";

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function iconFor(ext: string): { Icon: LucideIcon; tint: string } {
  const e = ext.replace(".", "").toLowerCase();
  if (e === "pdf")
    return {
      Icon: FileText,
      tint: "bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400",
    };
  if (e === "docx" || e === "doc")
    return {
      Icon: FileType2,
      tint: "bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400",
    };
  if (e === "md")
    return {
      Icon: FileCode2,
      tint: "bg-violet-50 text-violet-600 dark:bg-violet-500/10 dark:text-violet-400",
    };
  if (e === "txt")
    return {
      Icon: FileText,
      tint: "bg-surface-100 text-surface-500 dark:bg-surface-800 dark:text-surface-400",
    };
  if (e === "xlsx" || e === "csv")
    return {
      Icon: FileSpreadsheet,
      tint: "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400",
    };
  return {
    Icon: FileIcon,
    tint: "bg-surface-100 text-surface-500 dark:bg-surface-800 dark:text-surface-400",
  };
}

export default function LibraryPage() {
  const [docs, setDocs] = useState<DocumentRead[]>([]);
  const [busy, setBusy] = useState(false);
  const [driveBusy, setDriveBusy] = useState(false);
  const [showGoogleSettings, setShowGoogleSettings] = useState(false);
  const [showOneDrive, setShowOneDrive] = useState(false);
  const [showSharePoint, setShowSharePoint] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [asCatalog, setAsCatalog] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      setDocs(await listDocuments());
    } catch (e) {
      setNotice(String(e));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll mientras haya documentos en proceso.
  useEffect(() => {
    const active = docs.some(
      (d) => d.status === "pending" || d.status === "processing"
    );
    if (!active) return;
    const t = setInterval(refresh, 2500);
    return () => clearInterval(t);
  }, [docs, refresh]);

  async function handleFiles(files: FileList | File[] | null) {
    if (!files || files.length === 0) return;
    setBusy(true);
    setNotice(null);
    try {
      const res = await uploadDocuments(files, asCatalog ? "catalog" : "document");
      const parts = [`${res.documents.length} subido(s)`];
      if (res.duplicates.length) parts.push(`${res.duplicates.length} duplicado(s)`);
      if (res.rejected.length) parts.push(`${res.rejected.length} rechazado(s)`);
      setNotice(parts.join(" · "));
      await refresh();
    } catch (e) {
      setNotice(String(e));
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function importFromDrive() {
    if (driveBusy) return;
    if (!isGoogleDriveConfigured()) {
      setShowGoogleSettings(true);
      return;
    }
    setDriveBusy(true);
    setNotice(null);
    try {
      const { accessToken, files } = await pickFromDrive();
      if (files.length === 0) return; // el usuario canceló
      const res = await importFromGoogleDrive(accessToken, files);
      const parts = [`${res.documents.length} importado(s)`];
      if (res.duplicates.length) parts.push(`${res.duplicates.length} duplicado(s)`);
      if (res.rejected.length) parts.push(`${res.rejected.length} no soportado(s)`);
      if (res.failed.length) parts.push(`${res.failed.length} con error`);
      setNotice("Google Drive: " + parts.join(" · "));
      await refresh();
    } catch (e) {
      setNotice(String(e instanceof Error ? e.message : e));
    } finally {
      setDriveBusy(false);
    }
  }

  async function onReindex(id: string) {
    await reindexDocument(id);
    refresh();
  }

  async function onDelete(id: string) {
    await deleteDocument(id);
    refresh();
  }

  const indexed = docs.filter((d) => d.status === "indexed").length;
  const processing = docs.filter(
    (d) => d.status === "pending" || d.status === "processing"
  ).length;

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="mx-auto w-full max-w-5xl px-8 py-8">
        {/* Header */}
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-surface-900 dark:text-surface-50">
              Biblioteca
            </h1>
            <p className="mt-1 text-sm text-surface-500 dark:text-surface-400">
              Subí PDF, DOCX, XLSX, CSV, TXT o MD. Se indexan automáticamente para
              poder consultarlos en el chat.
            </p>
          </div>
          <div className="flex gap-2">
            <Stat label="Documentos" value={docs.length} />
            <Stat label="Indexados" value={indexed} accent />
            {processing > 0 && <Stat label="En proceso" value={processing} />}
          </div>
        </div>

        {/* Zona de carga */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            handleFiles(e.dataTransfer.files);
          }}
          onClick={() => inputRef.current?.click()}
          className={`mb-7 flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition ${
            dragging
              ? "border-brand bg-brand-50 dark:border-brand-400 dark:bg-brand-500/10"
              : "border-surface-300 bg-white hover:border-brand-300 hover:bg-surface-50 dark:border-surface-700 dark:bg-surface-800/50 dark:hover:border-brand-600 dark:hover:bg-surface-800"
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
          <div
            className={`mb-3 flex h-12 w-12 items-center justify-center rounded-full transition ${
              dragging
                ? "bg-brand text-white"
                : "bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-400"
            }`}
          >
            {busy ? (
              <Loader2 className="h-6 w-6 animate-spin" />
            ) : (
              <CloudUpload className="h-6 w-6" />
            )}
          </div>
          <p className="text-sm font-medium text-surface-700 dark:text-surface-200">
            {busy
              ? "Subiendo…"
              : "Arrastrá archivos acá o hacé clic para seleccionar"}
          </p>
          <p className="mt-1 text-xs text-surface-400 dark:text-surface-500">
            Formatos: PDF · DOCX · XLSX · CSV · TXT · MD
          </p>
        </div>

        {/* Tipo de documento a subir */}
        <label className="mb-7 -mt-4 flex cursor-pointer items-start gap-2.5 rounded-xl border border-surface-200 bg-white px-4 py-3 shadow-soft dark:border-surface-800 dark:bg-surface-800/40">
          <input
            type="checkbox"
            checked={asCatalog}
            onChange={(e) => setAsCatalog(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-surface-300 text-brand-600 focus:ring-brand-500 dark:border-surface-600 dark:bg-surface-700"
          />
          <span className="min-w-0">
            <span className="flex items-center gap-1.5 text-sm font-medium text-surface-700 dark:text-surface-200">
              <BookMarked className="h-4 w-4 text-amber-600 dark:text-amber-400" />
              Subir como catálogo de servicios / tarifario
            </span>
            <span className="mt-0.5 block text-xs text-surface-400 dark:text-surface-500">
              Los catálogos se usan SIEMPRE como fuente de números de parte y
              precios al generar cotizaciones, y no aparecen como precedentes.
            </span>
          </span>
        </label>

        {/* Importar desde la nube */}
        <div className="mb-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-surface-200 dark:bg-surface-800" />
          <span className="text-xs text-surface-400 dark:text-surface-500">
            o importá desde
          </span>
          <div className="flex items-center overflow-hidden rounded-lg border border-surface-300 shadow-soft dark:border-surface-700">
            <button
              onClick={importFromDrive}
              disabled={driveBusy}
              title="Elegí archivos de tu Google Drive"
              className="inline-flex items-center gap-2 bg-white px-3.5 py-2 text-sm font-medium text-surface-700 transition hover:bg-surface-50 disabled:opacity-50 dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-surface-700"
            >
              {driveBusy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <HardDriveDownload className="h-4 w-4 text-brand-600 dark:text-brand-400" />
              )}
              {driveBusy ? "Importando…" : "Google Drive"}
            </button>
            <button
              onClick={() => setShowGoogleSettings(true)}
              title="Configurar credenciales de Google Drive"
              className="border-l border-surface-300 bg-white px-2 py-2.5 text-surface-400 transition hover:bg-surface-50 hover:text-surface-700 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-500 dark:hover:bg-surface-700 dark:hover:text-surface-200"
            >
              <Settings2 className="h-4 w-4" />
            </button>
          </div>
          <button
            onClick={() => setShowOneDrive(true)}
            title="Importar archivos de tu OneDrive"
            className="inline-flex items-center gap-2 rounded-lg border border-surface-300 bg-white px-3.5 py-2 text-sm font-medium text-surface-700 shadow-soft transition hover:border-brand-300 hover:bg-surface-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:border-brand-600 dark:hover:bg-surface-700"
          >
            <Cloud className="h-4 w-4 text-brand-600 dark:text-brand-400" />
            OneDrive
          </button>
          <button
            onClick={() => setShowSharePoint(true)}
            title="Importar archivos de SharePoint"
            className="inline-flex items-center gap-2 rounded-lg border border-surface-300 bg-white px-3.5 py-2 text-sm font-medium text-surface-700 shadow-soft transition hover:border-brand-300 hover:bg-surface-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:border-brand-600 dark:hover:bg-surface-700"
          >
            <Share2 className="h-4 w-4 text-brand-600 dark:text-brand-400" />
            SharePoint
          </button>
          <div className="h-px flex-1 bg-surface-200 dark:bg-surface-800" />
        </div>

        {notice && (
          <div className="mb-5 flex items-center justify-between gap-3 rounded-lg bg-brand-50 px-4 py-2.5 text-sm text-brand-700 ring-1 ring-brand-100 dark:bg-brand-500/10 dark:text-brand-300 dark:ring-brand-500/20">
            <span>{notice}</span>
            <button
              onClick={() => setNotice(null)}
              className="text-brand-600 hover:text-brand-800 dark:text-brand-400 dark:hover:text-brand-200"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Tabla de documentos */}
        <div className="overflow-hidden rounded-xl border border-surface-200 bg-white shadow-soft dark:border-surface-800 dark:bg-surface-800/40">
          <table className="w-full table-fixed text-sm">
            <thead>
              <tr className="border-b border-surface-200 bg-surface-50 text-left text-[11px] font-semibold uppercase tracking-wider text-surface-500 dark:border-surface-800 dark:bg-surface-800/60 dark:text-surface-400">
                <th className="px-5 py-3">Documento</th>
                <th className="w-32 px-5 py-3">Estado</th>
                <th className="w-28 px-5 py-3">Fragmentos</th>
                <th className="w-28 px-5 py-3">Tamaño</th>
                <th className="w-44 px-5 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100 dark:divide-surface-800">
              {docs.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-5 py-16 text-center">
                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-surface-100 text-surface-400 dark:bg-surface-800 dark:text-surface-500">
                      <FileText className="h-6 w-6" />
                    </div>
                    <p className="mt-3 text-sm font-medium text-surface-600 dark:text-surface-300">
                      Todavía no hay documentos
                    </p>
                    <p className="mt-0.5 text-xs text-surface-400 dark:text-surface-500">
                      Subí tu primer archivo para empezar.
                    </p>
                  </td>
                </tr>
              )}
              {docs.map((d) => {
                const { Icon, tint } = iconFor(d.extension);
                return (
                  <tr
                    key={d.id}
                    className="group transition hover:bg-surface-50 dark:hover:bg-surface-800/60"
                  >
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div
                          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${tint}`}
                        >
                          <Icon className="h-[18px] w-[18px]" />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="truncate font-medium text-surface-800 dark:text-surface-100">
                              {d.filename}
                            </span>
                            {d.doc_type === "catalog" && (
                              <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700 ring-1 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/20">
                                <BookMarked className="h-3 w-3" />
                                Catálogo
                              </span>
                            )}
                          </div>
                          {d.error && (
                            <div
                              className="mt-0.5 truncate text-xs text-red-500 dark:text-red-400"
                              title={d.error}
                            >
                              {d.error.slice(0, 90)}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={d.status} />
                    </td>
                    <td className="px-5 py-3.5 tabular-nums text-surface-600 dark:text-surface-400">
                      {d.chunk_count}
                    </td>
                    <td className="px-5 py-3.5 tabular-nums text-surface-600 dark:text-surface-400">
                      {fmtSize(d.size_bytes)}
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex justify-end gap-1 opacity-60 transition group-hover:opacity-100">
                        {(d.status === "failed" || d.status === "indexed") && (
                          <button
                            onClick={() => onReindex(d.id)}
                            title="Reindexar"
                            className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-surface-600 transition hover:bg-brand-50 hover:text-brand-700 dark:text-surface-400 dark:hover:bg-brand-500/15 dark:hover:text-brand-300"
                          >
                            <RotateCw className="h-3.5 w-3.5" />
                            Reindexar
                          </button>
                        )}
                        <button
                          onClick={() => onDelete(d.id)}
                          title="Borrar"
                          className="inline-flex items-center justify-center rounded-md p-1.5 text-surface-500 transition hover:bg-red-50 hover:text-red-600 dark:text-surface-400 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {showGoogleSettings && (
        <GoogleSettingsModal
          onClose={() => setShowGoogleSettings(false)}
          onSaved={() => {
            setNotice("Google Drive configurado. Volvé a tocar el botón para importar.");
          }}
        />
      )}

      {showOneDrive && (
        <OneDrivePickerModal
          onClose={() => setShowOneDrive(false)}
          onImported={(res: ImportResult) => {
            const parts = [`${res.documents.length} importado(s)`];
            if (res.duplicates.length) parts.push(`${res.duplicates.length} duplicado(s)`);
            if (res.rejected.length) parts.push(`${res.rejected.length} no soportado(s)`);
            if (res.failed.length) parts.push(`${res.failed.length} con error`);
            setNotice("OneDrive: " + parts.join(" · "));
            refresh();
          }}
        />
      )}

      {showSharePoint && (
        <SharePointPickerModal
          onClose={() => setShowSharePoint(false)}
          onImported={(res: ImportResult) => {
            const parts = [`${res.documents.length} importado(s)`];
            if (res.duplicates.length) parts.push(`${res.duplicates.length} duplicado(s)`);
            if (res.rejected.length) parts.push(`${res.rejected.length} no soportado(s)`);
            if (res.failed.length) parts.push(`${res.failed.length} con error`);
            setNotice("SharePoint: " + parts.join(" · "));
            refresh();
          }}
        />
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border px-4 py-2 text-center ${
        accent
          ? "border-brand-100 bg-brand-50 dark:border-brand-500/30 dark:bg-brand-500/10"
          : "border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-800/40"
      }`}
    >
      <div
        className={`text-xl font-bold tabular-nums ${
          accent
            ? "text-brand-700 dark:text-brand-300"
            : "text-surface-800 dark:text-surface-100"
        }`}
      >
        {value}
      </div>
      <div className="text-[11px] font-medium uppercase tracking-wide text-surface-400 dark:text-surface-500">
        {label}
      </div>
    </div>
  );
}
