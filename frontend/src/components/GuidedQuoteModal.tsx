import { useState } from "react";
import {
  ArrowLeft,
  FileText,
  Loader2,
  Search,
  Sparkles,
  Wand2,
  X,
} from "lucide-react";
import { findPrecedents, generateFromPrecedent } from "../api/quotes";
import type { BasedOn, Precedent, QuoteDraft } from "../api/types";

type Step = "input" | "select" | "generating";

export default function GuidedQuoteModal({
  sessionId,
  onClose,
  onDrafted,
}: {
  sessionId: string | null;
  onClose: () => void;
  onDrafted: (
    draft: QuoteDraft,
    basedOn: BasedOn | null,
    quoteId: string
  ) => void;
}) {
  const [step, setStep] = useState<Step>("input");
  const [request, setRequest] = useState("");
  const [precedents, setPrecedents] = useState<Precedent[]>([]);
  const [chosen, setChosen] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function search() {
    if (!request.trim() || busy) return;
    setBusy(true);
    setErr(null);
    try {
      const res = await findPrecedents(request.trim());
      setPrecedents(res.precedents);
      setStep("select");
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function generate(documentId: string) {
    setChosen(documentId);
    setBusy(true);
    setErr(null);
    setStep("generating");
    try {
      const res = await generateFromPrecedent({
        request: request.trim(),
        document_id: documentId,
        session_id: sessionId,
      });
      onDrafted(res.quote, res.based_on, res.quote_id);
    } catch (e) {
      setErr(String(e));
      setStep("select");
    } finally {
      setBusy(false);
    }
  }

  const chosenName =
    precedents.find((p) => p.document_id === chosen)?.filename ?? "";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-surface-900/40 p-4 backdrop-blur-sm animate-fade-in dark:bg-black/60"
      onClick={onClose}
    >
      <div
        className="flex max-h-[88vh] w-full max-w-xl flex-col overflow-hidden rounded-2xl bg-white shadow-pop animate-scale-in dark:bg-surface-800"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-surface-200 px-6 py-4 dark:border-surface-700">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-400">
              <Wand2 className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-surface-900 dark:text-surface-50">
                Cotización guiada
              </h2>
              <p className="text-xs text-surface-400 dark:text-surface-500">
                Se basa en una cotización existente parecida
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-surface-400 transition hover:bg-surface-100 hover:text-surface-700 dark:text-surface-500 dark:hover:bg-surface-700 dark:hover:text-surface-200"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-5">
          {err && (
            <div className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600 ring-1 ring-red-100 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/20">
              {err}
            </div>
          )}

          {/* Paso 1: describir el pedido */}
          {step === "input" && (
            <div>
              <label className="mb-1.5 block text-sm font-medium text-surface-700 dark:text-surface-200">
                ¿Qué cotización necesitás?
              </label>
              <p className="mb-3 text-xs text-surface-400 dark:text-surface-500">
                Describila en lenguaje natural. Buscaremos en tu biblioteca una
                parecida para usarla de base.
              </p>
              <textarea
                value={request}
                onChange={(e) => setRequest(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) search();
                }}
                rows={4}
                autoFocus
                placeholder="Ej: cotización para desarrollo de una app web full stack de 2 meses, con despliegue en AWS…"
                className="w-full resize-none rounded-xl border border-surface-300 bg-white px-3.5 py-2.5 text-sm text-surface-800 placeholder:text-surface-400 transition focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-100 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-100 dark:placeholder:text-surface-500 dark:focus:border-brand-600 dark:focus:ring-brand-500/20"
              />
              <button
                onClick={search}
                disabled={!request.trim() || busy}
                className="btn-primary mt-4 w-full"
              >
                {busy ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                {busy ? "Buscando…" : "Buscar precedentes"}
              </button>
            </div>
          )}

          {/* Paso 2: elegir precedente (confirmación) */}
          {step === "select" && (
            <div>
              <button
                onClick={() => setStep("input")}
                className="mb-3 inline-flex items-center gap-1 text-xs font-medium text-surface-500 transition hover:text-surface-800 dark:text-surface-400 dark:hover:text-surface-100"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Cambiar pedido
              </button>
              <p className="mb-3 text-sm text-surface-700 dark:text-surface-200">
                {precedents.length > 0
                  ? "Elegí la cotización que querés usar como base:"
                  : "No encontramos una cotización parecida."}
              </p>

              <div className="space-y-2">
                {precedents.map((p) => (
                  <button
                    key={p.document_id}
                    onClick={() => generate(p.document_id)}
                    disabled={busy}
                    className="group flex w-full items-start gap-3 rounded-xl border border-surface-200 bg-white px-4 py-3 text-left transition hover:border-brand-300 hover:bg-brand-50 disabled:opacity-50 dark:border-surface-700 dark:bg-surface-900/50 dark:hover:border-brand-600 dark:hover:bg-surface-800"
                  >
                    <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface-100 text-surface-500 transition group-hover:bg-brand-100 group-hover:text-brand-600 dark:bg-surface-700 dark:text-surface-400 dark:group-hover:bg-brand-500/20 dark:group-hover:text-brand-300">
                      <FileText className="h-4 w-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center justify-between gap-2">
                        <span className="truncate text-sm font-medium text-surface-800 dark:text-surface-100">
                          {p.filename}
                        </span>
                        <span className="shrink-0 rounded-full bg-brand-50 px-2 py-0.5 text-[11px] font-semibold text-brand-700 dark:bg-brand-500/15 dark:text-brand-300">
                          {Math.round(p.score * 100)}% afinidad
                        </span>
                      </span>
                      <span className="mt-1 line-clamp-2 block text-xs text-surface-400 dark:text-surface-500">
                        {p.snippet}
                      </span>
                    </span>
                  </button>
                ))}
              </div>

              <p className="mt-4 text-center text-[11px] text-surface-400 dark:text-surface-500">
                La nueva cotización reutilizará ítems y precios del precedente,
                ajustados a tu pedido. Revisá los montos antes de enviarla.
              </p>
            </div>
          )}

          {/* Paso 3: generando */}
          {step === "generating" && (
            <div className="flex flex-col items-center justify-center py-10 text-center">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-400">
                <Sparkles className="h-6 w-6 animate-pulse" />
              </div>
              <p className="text-sm font-medium text-surface-700 dark:text-surface-200">
                Generando cotización…
              </p>
              {chosenName && (
                <p className="mt-1 text-xs text-surface-400 dark:text-surface-500">
                  Basándose en {chosenName}
                </p>
              )}
              <Loader2 className="mt-4 h-5 w-5 animate-spin text-brand-500" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
