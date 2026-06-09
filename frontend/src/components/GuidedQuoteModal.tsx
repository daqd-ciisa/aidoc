import { useState } from "react";
import {
  ArrowLeft,
  Check,
  FileText,
  Loader2,
  Search,
  Sparkles,
  Wand2,
  X,
} from "lucide-react";
import {
  findPrecedents,
  generateProposalFromPrecedent,
  generateProposalFromScratch,
} from "../api/quotes";
import type { BasedOn, Precedent, ProposalDraft } from "../api/types";

type Step = "input" | "select" | "generating";
type Source = "precedent" | "scratch";

type GenResult = { based_on: BasedOn | null; based_on_all?: BasedOn[] | null };
const allOf = (res: GenResult): BasedOn[] =>
  res.based_on_all ?? (res.based_on ? [res.based_on] : []);

export default function GuidedQuoteModal({
  sessionId,
  onClose,
  onProposal,
}: {
  sessionId: string | null;
  onClose: () => void;
  onProposal: (
    proposal: ProposalDraft,
    basedOn: BasedOn[] | null,
    quoteId: string,
    title: string
  ) => void;
}) {
  const [step, setStep] = useState<Step>("input");
  const [source, setSource] = useState<Source>("precedent");
  const [request, setRequest] = useState("");
  const [precedents, setPrecedents] = useState<Precedent[]>([]);
  const [chosen, setChosen] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function search() {
    if (!request.trim() || busy) return;
    setBusy(true);
    setErr(null);
    try {
      // Mostramos un pool más amplio (no solo el top 3): con multi-selección, un
      // pedido mixto (p. ej. producto + servicio) necesita ver candidatos de ambas
      // categorías para poder combinarlos.
      const res = await findPrecedents(request.trim(), 6);
      setPrecedents(res.precedents);
      setChosen(res.precedents.length > 0 ? [res.precedents[0].document_id] : []);
      setStep("select");
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  function toggle(documentId: string) {
    setChosen((c) =>
      c.includes(documentId)
        ? c.filter((x) => x !== documentId)
        : [...c, documentId]
    );
  }

  async function generate() {
    if (chosen.length === 0 || busy) return;
    setBusy(true);
    setErr(null);
    setStep("generating");
    const body = {
      request: request.trim(),
      document_ids: chosen,
      session_id: sessionId,
    };
    try {
      const res = await generateProposalFromPrecedent(body);
      onProposal(res.proposal, allOf(res), res.quote_id, res.title);
    } catch (e) {
      setErr(String(e));
      setStep("select");
    } finally {
      setBusy(false);
    }
  }

  async function generateScratch() {
    if (!request.trim() || busy) return;
    setBusy(true);
    setErr(null);
    setStep("generating");
    const body = { request: request.trim(), session_id: sessionId };
    try {
      const res = await generateProposalFromScratch(body);
      onProposal(res.proposal, allOf(res), res.quote_id, res.title);
    } catch (e) {
      setErr(String(e));
      setStep("input");
    } finally {
      setBusy(false);
    }
  }

  const chosenNames = precedents
    .filter((p) => chosen.includes(p.document_id))
    .map((p) => p.filename);

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
                A partir de un precedente o desde cero
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
                ¿En qué se basa?
              </label>
              <div className="mb-3 grid grid-cols-2 gap-2">
                {(
                  [
                    ["precedent", "Con precedente", "Busca una cotización parecida"],
                    ["scratch", "Desde cero", "Sin precedente, solo tu pedido"],
                  ] as [Source, string, string][]
                ).map(([s, label, hint]) => (
                  <button
                    key={s}
                    onClick={() => setSource(s)}
                    className={`rounded-xl border px-3 py-2.5 text-left transition ${
                      source === s
                        ? "border-brand-400 bg-brand-50 dark:border-brand-500 dark:bg-brand-500/15"
                        : "border-surface-200 bg-white hover:border-surface-300 dark:border-surface-700 dark:bg-surface-900/50 dark:hover:border-surface-600"
                    }`}
                  >
                    <div className="text-sm font-semibold text-surface-800 dark:text-surface-100">
                      {label}
                    </div>
                    <div className="text-[11px] text-surface-400 dark:text-surface-500">
                      {hint}
                    </div>
                  </button>
                ))}
              </div>
              <p className="mb-3 text-xs text-surface-400 dark:text-surface-500">
                {source === "precedent"
                  ? "Describí el pedido en lenguaje natural. Buscaremos en tu biblioteca una cotización parecida para usarla de base."
                  : "Describí el pedido en lenguaje natural. Armaremos un borrador desde cero (sin precedente) con los precios en blanco para que los completes."}
              </p>
              <textarea
                value={request}
                onChange={(e) => setRequest(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                    if (source === "scratch") generateScratch();
                    else search();
                  }
                }}
                rows={4}
                autoFocus
                placeholder="Ej: cotización para desarrollo de una app web full stack de 2 meses, con despliegue en AWS…"
                className="w-full resize-none rounded-xl border border-surface-300 bg-white px-3.5 py-2.5 text-sm text-surface-800 placeholder:text-surface-400 transition focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-100 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-100 dark:placeholder:text-surface-500 dark:focus:border-brand-600 dark:focus:ring-brand-500/20"
              />
              <button
                onClick={source === "scratch" ? generateScratch : search}
                disabled={!request.trim() || busy}
                className="btn-primary mt-4 w-full"
              >
                {busy ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : source === "scratch" ? (
                  <Wand2 className="h-4 w-4" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                {busy
                  ? source === "scratch"
                    ? "Generando…"
                    : "Buscando…"
                  : source === "scratch"
                    ? "Generar desde cero"
                    : "Buscar precedentes"}
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
                  ? "Elegí una o varias cotizaciones para usar como base:"
                  : "No encontramos una cotización parecida."}
              </p>

              <div className="space-y-2">
                {precedents.map((p) => {
                  const sel = chosen.includes(p.document_id);
                  return (
                    <button
                      key={p.document_id}
                      onClick={() => toggle(p.document_id)}
                      disabled={busy}
                      className={`group flex w-full items-start gap-3 rounded-xl border px-4 py-3 text-left transition disabled:opacity-50 ${
                        sel
                          ? "border-brand-400 bg-brand-50 ring-1 ring-brand-200 dark:border-brand-500 dark:bg-brand-500/15 dark:ring-brand-500/30"
                          : "border-surface-200 bg-white hover:border-brand-300 hover:bg-brand-50/50 dark:border-surface-700 dark:bg-surface-900/50 dark:hover:border-brand-600 dark:hover:bg-surface-800"
                      }`}
                    >
                      <span
                        className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition ${
                          sel
                            ? "bg-brand-500 text-white dark:bg-brand-500"
                            : "bg-surface-100 text-surface-500 group-hover:bg-brand-100 group-hover:text-brand-600 dark:bg-surface-700 dark:text-surface-400 dark:group-hover:bg-brand-500/20 dark:group-hover:text-brand-300"
                        }`}
                      >
                        {sel ? (
                          <Check className="h-4 w-4" />
                        ) : (
                          <FileText className="h-4 w-4" />
                        )}
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
                        {p.motivo && (
                          <span className="mt-1 block text-xs text-surface-600 dark:text-surface-300">
                            {p.motivo}
                          </span>
                        )}
                        <span className="mt-1 line-clamp-2 block text-xs text-surface-400 dark:text-surface-500">
                          {p.snippet}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>

              {precedents.length > 0 && (
                <>
                  <button
                    onClick={generate}
                    disabled={chosen.length === 0 || busy}
                    className="btn-primary mt-4 w-full"
                  >
                    <Wand2 className="h-4 w-4" />
                    {chosen.length > 1
                      ? `Generar combinando ${chosen.length} precedentes`
                      : "Generar"}
                  </button>
                  <p className="mt-3 text-center text-[11px] text-surface-400 dark:text-surface-500">
                    Si elegís varios, se usa el más cercano como base y se completan
                    los datos faltantes con los otros. Revisá los montos antes de
                    enviarla.
                  </p>
                </>
              )}

              {(precedents.length === 0 ||
                (precedents[0]?.score ?? 0) < 0.5) && (
                <button
                  onClick={generateScratch}
                  disabled={busy}
                  className="mt-3 w-full rounded-xl border border-dashed border-surface-300 px-3 py-2.5 text-xs font-medium text-surface-500 transition hover:border-brand-300 hover:text-brand-600 disabled:opacity-50 dark:border-surface-600 dark:text-surface-400 dark:hover:border-brand-600 dark:hover:text-brand-300"
                >
                  {precedents.length === 0
                    ? "Generar desde cero (sin precedente)"
                    : "¿Ninguno encaja? Generar desde cero"}
                </button>
              )}
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
              {chosenNames.length > 0 && (
                <p className="mt-1 text-xs text-surface-400 dark:text-surface-500">
                  Basándose en {chosenNames.join(", ")}
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
