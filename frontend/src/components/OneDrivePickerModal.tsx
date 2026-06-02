import { useCallback, useEffect, useState } from "react";
import {
  ChevronRight,
  Cloud,
  ExternalLink,
  FileText,
  Folder,
  Loader2,
  X,
} from "lucide-react";
import type { DriveFile, ImportResult } from "../api/connectors";
import { importFromOneDrive } from "../api/connectors";
import {
  getOneDriveToken,
  isOneDriveConfigured,
  listChildren,
  setOneDriveClientId,
  type DriveItem,
} from "../lib/oneDrive";

type Step = "config" | "loading" | "browse" | "importing";
interface Crumb {
  id?: string;
  name: string;
}

export default function OneDrivePickerModal({
  onClose,
  onImported,
}: {
  onClose: () => void;
  onImported: (res: ImportResult) => void;
}) {
  const [step, setStep] = useState<Step>(
    isOneDriveConfigured() ? "loading" : "config"
  );
  const [clientId, setClientId] = useState("");
  const [token, setToken] = useState<string | null>(null);
  const [crumbs, setCrumbs] = useState<Crumb[]>([{ name: "OneDrive" }]);
  const [items, setItems] = useState<DriveItem[]>([]);
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async (tok: string, folderId?: string) => {
    setErr(null);
    try {
      setItems(await listChildren(tok, folderId));
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    }
  }, []);

  const connect = useCallback(async () => {
    setStep("loading");
    setErr(null);
    try {
      const tok = await getOneDriveToken();
      setToken(tok);
      setStep("browse");
      await load(tok);
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
      setStep(isOneDriveConfigured() ? "browse" : "config");
    }
  }, [load]);

  useEffect(() => {
    if (isOneDriveConfigured()) connect();
  }, [connect]);

  function saveConfig() {
    if (!clientId.trim()) return;
    setOneDriveClientId(clientId);
    connect();
  }

  async function openFolder(item: DriveItem) {
    if (!token) return;
    setCrumbs((c) => [...c, { id: item.id, name: item.name }]);
    await load(token, item.id);
  }

  async function goTo(idx: number) {
    if (!token) return;
    const next = crumbs.slice(0, idx + 1);
    setCrumbs(next);
    await load(token, next[next.length - 1].id);
  }

  function toggle(item: DriveItem) {
    setSelected((s) => {
      const copy = { ...s };
      if (copy[item.id]) delete copy[item.id];
      else copy[item.id] = item.name;
      return copy;
    });
  }

  async function doImport() {
    if (!token) return;
    const files: DriveFile[] = Object.entries(selected).map(([id, name]) => ({
      id,
      name,
    }));
    if (files.length === 0) return;
    setStep("importing");
    try {
      const res = await importFromOneDrive(token, files);
      onImported(res);
      onClose();
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
      setStep("browse");
    }
  }

  const selectedCount = Object.keys(selected).length;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-surface-900/40 p-4 backdrop-blur-sm animate-fade-in dark:bg-black/60"
      onClick={onClose}
    >
      <div
        className="flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl bg-white shadow-pop animate-scale-in dark:bg-surface-800"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-surface-200 px-6 py-4 dark:border-surface-700">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-400">
              <Cloud className="h-5 w-5" />
            </div>
            <h2 className="text-base font-bold text-surface-900 dark:text-surface-50">
              Importar de OneDrive
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-surface-400 transition hover:bg-surface-100 hover:text-surface-700 dark:text-surface-500 dark:hover:bg-surface-700 dark:hover:text-surface-200"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {err && (
          <div className="mx-6 mt-4 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600 ring-1 ring-red-100 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/20">
            {err}
          </div>
        )}

        {/* Config */}
        {step === "config" && (
          <div className="px-6 py-5">
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-surface-500 dark:text-surface-400">
              Client ID (App registration de Azure, SPA)
            </label>
            <input
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              placeholder="00000000-0000-0000-0000-000000000000"
              className="w-full rounded-lg border border-surface-300 bg-white px-3 py-2 text-sm text-surface-800 placeholder:text-surface-400 focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-100 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-100 dark:placeholder:text-surface-500 dark:focus:border-brand-600 dark:focus:ring-brand-500/20"
            />
            <div className="mt-3 rounded-lg bg-surface-50 px-3 py-2.5 text-xs text-surface-500 ring-1 ring-surface-200 dark:bg-surface-900/50 dark:text-surface-400 dark:ring-surface-700">
              En Azure Portal → Registros de aplicaciones → Nueva: tipo{" "}
              <b>SPA</b>, URI de redirección{" "}
              <code className="rounded bg-surface-200 px-1 dark:bg-surface-700">
                {window.location.origin}
              </code>
              , permiso de Graph <b>Files.Read</b> (delegado). Cuentas: personales
              + organización.
              <a
                href="https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade"
                target="_blank"
                rel="noreferrer"
                className="mt-1.5 flex items-center gap-1 font-medium text-brand-600 hover:underline dark:text-brand-400"
              >
                Abrir Registros de aplicaciones <ExternalLink className="h-3 w-3" />
              </a>
            </div>
            <button
              onClick={saveConfig}
              disabled={!clientId.trim()}
              className="btn-primary mt-4 w-full"
            >
              Guardar y conectar
            </button>
          </div>
        )}

        {/* Loading */}
        {step === "loading" && (
          <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
            <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
            <p className="mt-3 text-sm text-surface-500 dark:text-surface-400">
              Conectando con Microsoft…
            </p>
          </div>
        )}

        {/* Browse */}
        {step === "browse" && (
          <>
            <div className="flex flex-wrap items-center gap-1 border-b border-surface-200 px-6 py-2.5 text-xs text-surface-500 dark:border-surface-700 dark:text-surface-400">
              {crumbs.map((c, i) => (
                <span key={i} className="flex items-center gap-1">
                  {i > 0 && <ChevronRight className="h-3 w-3 text-surface-300" />}
                  <button
                    onClick={() => goTo(i)}
                    className="rounded px-1 py-0.5 hover:text-surface-800 hover:underline dark:hover:text-surface-100"
                  >
                    {c.name}
                  </button>
                </span>
              ))}
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-2">
              {items.length === 0 && (
                <p className="px-3 py-6 text-center text-xs text-surface-400 dark:text-surface-500">
                  Carpeta vacía.
                </p>
              )}
              {items.map((it) =>
                it.isFolder ? (
                  <button
                    key={it.id}
                    onClick={() => openFolder(it)}
                    className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition hover:bg-surface-50 dark:hover:bg-surface-700"
                  >
                    <Folder className="h-4 w-4 shrink-0 text-brand-500 dark:text-brand-400" />
                    <span className="flex-1 truncate text-surface-700 dark:text-surface-200">
                      {it.name}
                    </span>
                    <ChevronRight className="h-4 w-4 text-surface-300" />
                  </button>
                ) : (
                  <label
                    key={it.id}
                    className="flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition hover:bg-surface-50 dark:hover:bg-surface-700"
                  >
                    <input
                      type="checkbox"
                      checked={Boolean(selected[it.id])}
                      onChange={() => toggle(it)}
                      className="h-4 w-4 rounded border-surface-300 text-brand focus:ring-brand-300 dark:border-surface-600 dark:bg-surface-700"
                    />
                    <FileText className="h-4 w-4 shrink-0 text-surface-400 dark:text-surface-500" />
                    <span className="flex-1 truncate text-surface-700 dark:text-surface-200">
                      {it.name}
                    </span>
                  </label>
                )
              )}
            </div>
            <div className="flex items-center justify-between gap-3 border-t border-surface-200 bg-surface-50 px-6 py-3 dark:border-surface-700 dark:bg-surface-900/50">
              <span className="text-xs text-surface-500 dark:text-surface-400">
                {selectedCount} seleccionado(s)
              </span>
              <button
                onClick={doImport}
                disabled={selectedCount === 0}
                className="btn-primary"
              >
                Importar
              </button>
            </div>
          </>
        )}

        {/* Importing */}
        {step === "importing" && (
          <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
            <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
            <p className="mt-3 text-sm text-surface-500 dark:text-surface-400">
              Importando documentos…
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
