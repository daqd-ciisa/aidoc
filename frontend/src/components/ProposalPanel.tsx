import { useState } from "react";
import {
  Check,
  ChevronDown,
  ExternalLink,
  FileDown,
  FileText,
  FileType2,
  Loader2,
  Plus,
  RefreshCw,
  ScrollText,
  Save,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  Trash2,
  X,
} from "lucide-react";
import type {
  BasedOn,
  ClaimVerdict,
  ProposalDraft,
  ProposalSection,
  QuoteItem,
  ValidationReport,
} from "../api/types";
import {
  downloadQuoteDocx,
  downloadQuotePdf,
  updateProposal,
  validateQuote,
} from "../api/quotes";

const IVA_RATE = 0.16;

function fmt(n: number | null, currency?: string | null): string {
  if (n == null) return "—";
  const s = n.toLocaleString("es-MX", { minimumFractionDigits: 2 });
  return currency ? `${currency} ${s}` : s;
}
function round2(n: number): number {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}
function toNum(s: string): number | null {
  if (s.trim() === "") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

const inputCls =
  "w-full rounded-lg border border-surface-300 bg-white px-2.5 py-1.5 text-sm text-surface-800 outline-none transition focus:border-brand-400 focus:ring-2 focus:ring-brand-100 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-100 dark:focus:border-brand-500 dark:focus:ring-brand-500/20";

const FUENTE_LABEL: Record<string, string> = {
  fijo: "Fijo",
  precedente: "Del precedente",
  generado: "Generado por IA",
};

export default function ProposalPanel({
  proposal,
  quoteId,
  title,
  basedOn,
  onClose,
  onSaved,
}: {
  proposal: ProposalDraft;
  quoteId: string;
  title: string;
  basedOn?: BasedOn[] | null;
  onClose: () => void;
  onSaved?: (updated: ProposalDraft) => void;
}) {
  const [form, setForm] = useState<ProposalDraft>(proposal);
  const [taxAuto, setTaxAuto] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [downloading, setDownloading] = useState<"pdf" | "docx" | null>(null);
  const [showValidation, setShowValidation] = useState(false);
  const [applied, setApplied] = useState<Set<string>>(new Set());
  const [revalidating, setRevalidating] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const econ = form.economica;
  const cur = econ.moneda;

  // Totales de la económica recalculados en vivo.
  const editItems = econ.items.map((it) => ({
    ...it,
    importe: round2((it.cantidad ?? 0) * (it.precio_unitario ?? 0)),
  }));
  const editSubtotal = round2(editItems.reduce((a, it) => a + (it.importe ?? 0), 0));
  const autoTax = round2(editSubtotal * IVA_RATE);
  const editTax = taxAuto ? autoTax : econ.impuestos ?? 0;
  const editTotal = round2(editSubtotal + editTax);

  function patchSection(key: string, contenido: string) {
    setForm((f) => ({
      ...f,
      secciones: f.secciones.map((s) =>
        s.key === key ? { ...s, contenido } : s
      ),
    }));
  }
  function patchEcon(patch: Partial<typeof econ>) {
    setForm((f) => ({ ...f, economica: { ...f.economica, ...patch } }));
  }
  function patchItem(i: number, patch: Partial<QuoteItem>) {
    setForm((f) => ({
      ...f,
      economica: {
        ...f.economica,
        items: f.economica.items.map((it, idx) =>
          idx === i ? { ...it, ...patch } : it
        ),
      },
    }));
  }
  function addItem() {
    setForm((f) => ({
      ...f,
      economica: {
        ...f.economica,
        items: [
          ...f.economica.items,
          { servicio: "", descripcion: null, cantidad: 1, precio_unitario: null, importe: null },
        ],
      },
    }));
  }
  function removeItem(i: number) {
    setForm((f) => ({
      ...f,
      economica: {
        ...f.economica,
        items: f.economica.items.filter((_, idx) => idx !== i),
      },
    }));
  }

  function buildUpdated(): ProposalDraft {
    return {
      ...form,
      economica: {
        ...form.economica,
        items: editItems,
        subtotal: editSubtotal,
        impuestos: editTax,
        total: editTotal,
      },
    };
  }

  async function save(): Promise<ProposalDraft | null> {
    setSaving(true);
    setSaved(false);
    setErr(null);
    const updated = buildUpdated();
    try {
      await updateProposal(quoteId, updated, title);
      setForm(updated);
      onSaved?.(updated);
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2500);
      return updated;
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
      return null;
    } finally {
      setSaving(false);
    }
  }

  // Modo B: reemplaza el texto original de la afirmación por la corrección de la
  // fuente, en las secciones y los ítems editables.
  function applyCorrection(v: ClaimVerdict) {
    if (!v.origen || !v.correccion) return;
    const from = v.origen;
    const to = v.correccion;
    const has = (s: string | null) => !!s && s.includes(from);
    const matched =
      form.secciones.some((sec) => has(sec.contenido)) ||
      form.economica.items.some((it) => has(it.servicio) || has(it.descripcion));
    if (!matched) {
      setErr(
        `No encontré el texto exacto para corregir automáticamente. ` +
          `Editá a mano con el dato correcto: "${to}"`
      );
      return;
    }
    const repl = (s: string | null) => (s && s.includes(from) ? s.split(from).join(to) : s);
    setForm((f) => ({
      ...f,
      secciones: f.secciones.map((sec) => ({ ...sec, contenido: repl(sec.contenido) ?? sec.contenido })),
      economica: {
        ...f.economica,
        items: f.economica.items.map((it) => ({
          ...it,
          servicio: repl(it.servicio) ?? it.servicio,
          descripcion: repl(it.descripcion),
        })),
      },
    }));
    setApplied((prev) => new Set(prev).add(v.afirmacion));
    setErr(null);
  }

  // Guarda los cambios y vuelve a validar para refrescar la leyenda.
  async function saveAndRevalidate() {
    const updated = await save();
    if (!updated) return;
    setRevalidating(true);
    try {
      const rep = await validateQuote(quoteId);
      setForm((f) => ({ ...f, validacion: rep }));
      setApplied(new Set());
      setShowValidation(true);
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    } finally {
      setRevalidating(false);
    }
  }

  async function saveAndDownload(format: "pdf" | "docx") {
    const updated = await save();
    if (!updated) return;
    setDownloading(format);
    try {
      if (format === "pdf") await downloadQuotePdf(quoteId, title || "cotizacion");
      else await downloadQuoteDocx(quoteId, title || "cotizacion");
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-surface-900/40 p-4 backdrop-blur-sm animate-fade-in dark:bg-black/60">
      <div
        className="flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-pop animate-scale-in dark:bg-surface-800"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-surface-200 px-6 py-4 dark:border-surface-700">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-400">
              <ScrollText className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-surface-900 dark:text-surface-50">
                Cotización
              </h2>
              <p className="text-xs text-surface-400 dark:text-surface-500">
                Editá las secciones y la económica, luego descargá el PDF
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

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {basedOn && basedOn.length > 0 && (
            <div className="mb-4 flex items-center gap-2 rounded-lg bg-brand-50 px-3 py-2 text-xs text-brand-700 ring-1 ring-brand-100 dark:bg-brand-500/10 dark:text-brand-300 dark:ring-brand-500/20">
              <FileText className="h-4 w-4 shrink-0" />
              <span>
                {basedOn.length > 1
                  ? "Generada combinando: "
                  : "Generada usando como base: "}
                <span className="font-semibold">
                  {basedOn.map((b) => b.filename).join(", ")}
                </span>
              </span>
            </div>
          )}

          {form.validacion && form.validacion.afirmaciones.length > 0 && (
            <div className="mb-4">
              <ValidationLegend
                report={form.validacion}
                open={showValidation}
                onToggle={() => setShowValidation((v) => !v)}
              />
              {showValidation && (
                <ValidationReportView
                  report={form.validacion}
                  onApply={applyCorrection}
                  applied={applied}
                />
              )}
              {applied.size > 0 && (
                <button
                  onClick={saveAndRevalidate}
                  disabled={saving || revalidating}
                  className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-xs font-medium text-white shadow-soft transition hover:bg-brand-600 disabled:opacity-50 dark:bg-brand-500 dark:hover:bg-brand-400"
                >
                  {revalidating ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <RefreshCw className="h-3.5 w-3.5" />
                  )}
                  Guardar y re-validar ({applied.size} corrección
                  {applied.size > 1 ? "es" : ""})
                </button>
              )}
            </div>
          )}

          {/* Cabecera */}
          <div className="mb-5 grid grid-cols-3 gap-4">
            <div>
              <label className="text-[11px] font-semibold uppercase tracking-wide text-surface-400 dark:text-surface-500">
                Cliente
              </label>
              <input
                className={`${inputCls} mt-1`}
                value={form.cliente ?? ""}
                onChange={(e) =>
                  setForm((f) => ({ ...f, cliente: e.target.value || null }))
                }
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold uppercase tracking-wide text-surface-400 dark:text-surface-500">
                Fecha
              </label>
              <input
                className={`${inputCls} mt-1`}
                value={form.fecha ?? ""}
                onChange={(e) =>
                  setForm((f) => ({ ...f, fecha: e.target.value || null }))
                }
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold uppercase tracking-wide text-surface-400 dark:text-surface-500">
                Moneda
              </label>
              <input
                className={`${inputCls} mt-1`}
                value={econ.moneda ?? ""}
                placeholder="MXN"
                onChange={(e) => patchEcon({ moneda: e.target.value || null })}
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold uppercase tracking-wide text-surface-400 dark:text-surface-500">
                Válida hasta
              </label>
              <input
                type="date"
                className={`${inputCls} mt-1`}
                value={econ.valida_hasta ?? ""}
                onChange={(e) => patchEcon({ valida_hasta: e.target.value || null })}
              />
            </div>
          </div>

          {/* Secciones */}
          <div className="space-y-5">
            {form.secciones.map((sec: ProposalSection) =>
              sec.key === "economica" ? (
                <Economica
                  key={sec.key}
                  titulo={sec.titulo}
                  items={econ.items}
                  editItems={editItems}
                  subtotal={editSubtotal}
                  tax={editTax}
                  total={editTotal}
                  taxAuto={taxAuto}
                  cur={cur}
                  onPatchItem={patchItem}
                  onAddItem={addItem}
                  onRemoveItem={removeItem}
                  onTax={(v) => {
                    setTaxAuto(false);
                    patchEcon({ impuestos: v });
                  }}
                  onTaxAuto={() => setTaxAuto(true)}
                />
              ) : (
                <div key={sec.key}>
                  <div className="mb-1 flex items-center gap-2">
                    <label className="text-sm font-bold text-surface-800 dark:text-surface-100">
                      {sec.titulo}
                    </label>
                    <span className="rounded-full bg-surface-100 px-1.5 py-0.5 text-[10px] font-medium text-surface-500 dark:bg-surface-700 dark:text-surface-400">
                      {FUENTE_LABEL[sec.fuente] ?? sec.fuente}
                    </span>
                  </div>
                  <textarea
                    className={`${inputCls} min-h-[90px] resize-y leading-relaxed`}
                    value={sec.contenido}
                    onChange={(e) => patchSection(sec.key, e.target.value)}
                  />
                </div>
              )
            )}
          </div>

          {err && (
            <div className="mt-4 rounded-lg bg-red-50 px-3 py-2.5 text-xs text-red-600 ring-1 ring-red-200 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/30">
              {err}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-surface-200 bg-surface-50 px-6 py-3.5 dark:border-surface-700 dark:bg-surface-900/50">
          {saved && (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 animate-fade-in dark:text-emerald-400">
              <Check className="h-3.5 w-3.5" />
              Guardado
            </span>
          )}
          <button
            onClick={() => save()}
            disabled={saving || downloading !== null}
            className="inline-flex items-center gap-1.5 rounded-lg border border-surface-300 bg-white px-3 py-1.5 text-xs font-medium text-surface-700 transition hover:border-brand-300 hover:bg-brand-50 disabled:opacity-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:border-brand-600 dark:hover:bg-brand-500/10"
          >
            {saving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Save className="h-3.5 w-3.5" />
            )}
            Guardar
          </button>
          <button
            onClick={() => saveAndDownload("docx")}
            disabled={saving || downloading !== null}
            className="inline-flex items-center gap-1.5 rounded-lg border border-surface-300 bg-white px-3 py-1.5 text-xs font-medium text-surface-700 transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 disabled:opacity-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:border-brand-600 dark:hover:bg-brand-500/10"
          >
            {downloading === "docx" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <FileType2 className="h-3.5 w-3.5" />
            )}
            Guardar y descargar Word
          </button>
          <button
            onClick={() => saveAndDownload("pdf")}
            disabled={saving || downloading !== null}
            className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3.5 py-1.5 text-xs font-medium text-white shadow-soft transition hover:bg-brand-600 disabled:opacity-50 dark:bg-brand-500 dark:hover:bg-brand-400"
          >
            {downloading === "pdf" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <FileDown className="h-3.5 w-3.5" />
            )}
            Guardar y descargar PDF
          </button>
        </div>
      </div>
    </div>
  );
}

function Economica({
  titulo,
  items,
  editItems,
  subtotal,
  tax,
  total,
  taxAuto,
  cur,
  onPatchItem,
  onAddItem,
  onRemoveItem,
  onTax,
  onTaxAuto,
}: {
  titulo: string;
  items: QuoteItem[];
  editItems: QuoteItem[];
  subtotal: number;
  tax: number;
  total: number;
  taxAuto: boolean;
  cur: string | null;
  onPatchItem: (i: number, patch: Partial<QuoteItem>) => void;
  onAddItem: () => void;
  onRemoveItem: (i: number) => void;
  onTax: (v: number | null) => void;
  onTaxAuto: () => void;
}) {
  return (
    <div>
      <label className="mb-1 block text-sm font-bold text-surface-800 dark:text-surface-100">
        {titulo}
      </label>
      <div className="overflow-hidden rounded-xl border border-surface-200 dark:border-surface-700">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-surface-200 bg-surface-50 text-left text-[11px] font-semibold uppercase tracking-wider text-surface-500 dark:border-surface-700 dark:bg-surface-900/50 dark:text-surface-400">
              <th className="px-3 py-2.5">Servicio</th>
              <th className="px-2 py-2.5 text-right">Cant.</th>
              <th className="px-2 py-2.5 text-right">P. unit.</th>
              <th className="px-3 py-2.5 text-right">Importe</th>
              <th className="w-10 px-2 py-2.5" />
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-100 dark:divide-surface-700">
            {items.map((it, i) => (
              <tr key={i} className="align-top">
                <td className="px-3 py-2.5">
                  <input
                    className={inputCls}
                    placeholder="Servicio"
                    value={it.servicio}
                    onChange={(e) => onPatchItem(i, { servicio: e.target.value })}
                  />
                  <input
                    className={`${inputCls} mt-1.5 text-xs`}
                    placeholder="Descripción (opcional)"
                    value={it.descripcion ?? ""}
                    onChange={(e) =>
                      onPatchItem(i, { descripcion: e.target.value || null })
                    }
                  />
                </td>
                <td className="px-2 py-2.5">
                  <input
                    type="number"
                    step="any"
                    className={`${inputCls} text-right`}
                    value={it.cantidad ?? ""}
                    onChange={(e) =>
                      onPatchItem(i, { cantidad: toNum(e.target.value) })
                    }
                  />
                </td>
                <td className="px-2 py-2.5">
                  <input
                    type="number"
                    step="any"
                    className={`${inputCls} text-right`}
                    value={it.precio_unitario ?? ""}
                    onChange={(e) =>
                      onPatchItem(i, { precio_unitario: toNum(e.target.value) })
                    }
                  />
                </td>
                <td className="px-3 py-2.5 text-right align-middle tabular-nums font-medium text-surface-800 dark:text-surface-100">
                  {fmt(editItems[i].importe)}
                </td>
                <td className="px-2 py-2.5 align-middle">
                  <button
                    onClick={() => onRemoveItem(i)}
                    title="Quitar ítem"
                    className="rounded-md p-1.5 text-surface-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button
          onClick={onAddItem}
          className="flex w-full items-center justify-center gap-1.5 border-t border-surface-200 bg-surface-50 py-2 text-xs font-medium text-brand-600 transition hover:bg-brand-50 dark:border-surface-700 dark:bg-surface-900/50 dark:text-brand-400 dark:hover:bg-brand-500/10"
        >
          <Plus className="h-3.5 w-3.5" />
          Agregar ítem
        </button>
      </div>

      <div className="mt-3 flex justify-end">
        <dl className="w-64 space-y-1.5 text-sm">
          <div className="flex items-center justify-between">
            <dt className="text-surface-500 dark:text-surface-400">Subtotal</dt>
            <dd className="tabular-nums text-surface-700 dark:text-surface-200">
              {fmt(subtotal, cur)}
            </dd>
          </div>
          <div className="flex items-center justify-between gap-2">
            <dt className="flex items-center gap-1.5 text-surface-500 dark:text-surface-400">
              Impuestos
              {taxAuto ? (
                <span className="text-[10px] font-medium text-surface-400 dark:text-surface-500">
                  IVA 16%
                </span>
              ) : (
                <button
                  onClick={onTaxAuto}
                  title="Calcular IVA 16% automáticamente"
                  className="text-[10px] font-medium text-brand-600 transition hover:text-brand-700 dark:text-brand-400"
                >
                  IVA 16%
                </button>
              )}
            </dt>
            <dd className="tabular-nums text-surface-700 dark:text-surface-200">
              <input
                type="number"
                step="any"
                className={`${inputCls} w-28 text-right`}
                value={tax}
                onChange={(e) => onTax(toNum(e.target.value))}
              />
            </dd>
          </div>
          <div className="flex items-center justify-between border-t border-surface-200 pt-1.5 text-base font-bold text-surface-900 dark:border-surface-700 dark:text-surface-50">
            <dt>Total</dt>
            <dd className="tabular-nums text-brand-700 dark:text-brand-300">
              {fmt(total, cur)}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  );
}

const ESTADO_CFG = {
  respaldado: {
    label: "Respaldado",
    icon: ShieldCheck,
    cls: "bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-500/30",
    dot: "text-emerald-500",
  },
  sin_respaldo: {
    label: "Sin respaldo",
    icon: ShieldAlert,
    cls: "bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/30",
    dot: "text-amber-500",
  },
  contradice: {
    label: "Contradice",
    icon: ShieldX,
    cls: "bg-red-50 text-red-700 ring-red-200 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/30",
    dot: "text-red-500",
  },
} as const;

function ValidationLegend({
  report,
  open,
  onToggle,
}: {
  report: ValidationReport;
  open: boolean;
  onToggle: () => void;
}) {
  const worst =
    report.contradichas > 0
      ? "contradice"
      : report.sin_respaldo > 0
        ? "sin_respaldo"
        : "respaldado";
  const cfg = ESTADO_CFG[worst];
  const Icon = cfg.icon;
  return (
    <button
      onClick={onToggle}
      className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium ring-1 ring-inset transition ${cfg.cls}`}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span>Validado contra fuentes aprobadas</span>
      <span className="font-normal opacity-80">
        · {report.respaldadas} respaldada(s) · {report.sin_respaldo} sin respaldo
        {report.contradichas > 0 ? ` · ${report.contradichas} contradicen` : ""}
      </span>
      <ChevronDown
        className={`ml-auto h-4 w-4 shrink-0 transition ${open ? "rotate-180" : ""}`}
      />
    </button>
  );
}

function ValidationReportView({
  report,
  onApply,
  applied,
}: {
  report: ValidationReport;
  onApply: (v: ClaimVerdict) => void;
  applied: Set<string>;
}) {
  if (report.corpus_vacio) {
    return (
      <div className="mt-5 flex items-start gap-2 rounded-lg bg-amber-50 px-3.5 py-3 text-xs text-amber-700 ring-1 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/30">
        <ShieldAlert className="h-4 w-4 shrink-0" />
        <span>
          No hay fuentes aprobadas indexadas para validar. Agregá documentación
          del fabricante en <b>Fuentes externas</b> y volvé a intentar.
        </span>
      </div>
    );
  }

  if (report.afirmaciones.length === 0) {
    return (
      <div className="mt-5 rounded-lg bg-surface-50 px-3.5 py-3 text-xs text-surface-500 ring-1 ring-surface-200 dark:bg-surface-900/50 dark:text-surface-400 dark:ring-surface-700">
        No se detectaron afirmaciones técnicas verificables en esta propuesta.
      </div>
    );
  }

  return (
    <div className="mt-2">
      <ul className="space-y-2">
        {report.afirmaciones.map((v: ClaimVerdict, i: number) => {
          const cfg = ESTADO_CFG[v.estado] ?? ESTADO_CFG.sin_respaldo;
          const Icon = cfg.icon;
          return (
            <li
              key={i}
              className="rounded-lg border border-surface-200 px-3 py-2.5 dark:border-surface-700"
            >
              <div className="flex items-start gap-2">
                <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${cfg.dot}`} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-surface-800 dark:text-surface-100">
                    {v.afirmacion}
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ring-1 ring-inset ${cfg.cls}`}
                    >
                      {cfg.label}
                    </span>
                    {v.fuente &&
                      (v.fuente_url ? (
                        <a
                          href={v.fuente_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-[11px] text-brand-600 hover:underline dark:text-brand-400"
                          title={v.fuente_url}
                        >
                          <ExternalLink className="h-3 w-3" />
                          {v.fuente}
                        </a>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] text-surface-500 dark:text-surface-400">
                          <FileText className="h-3 w-3" />
                          {v.fuente}
                        </span>
                      ))}
                  </div>
                  {v.motivo && (
                    <p className="mt-1 text-xs text-surface-500 dark:text-surface-400">
                      {v.motivo}
                    </p>
                  )}
                  {v.snippet && (
                    <p className="mt-1 border-l-2 border-surface-200 pl-2 text-[11px] italic text-surface-400 dark:border-surface-600 dark:text-surface-500">
                      “{v.snippet}”
                    </p>
                  )}
                  {v.estado === "contradice" && v.correccion && (
                    <div className="mt-2 flex flex-wrap items-center gap-2 rounded-md bg-surface-50 px-2.5 py-1.5 dark:bg-surface-900/50">
                      <span className="text-[11px] text-surface-600 dark:text-surface-300">
                        Corrección sugerida:{" "}
                        <span className="font-medium text-surface-800 dark:text-surface-100">
                          {v.correccion}
                        </span>
                      </span>
                      {applied.has(v.afirmacion) ? (
                        <span className="ml-auto inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                          <Check className="h-3 w-3" /> Aplicada
                        </span>
                      ) : v.origen ? (
                        <button
                          onClick={() => onApply(v)}
                          className="ml-auto inline-flex items-center rounded-md bg-brand px-2 py-0.5 text-[11px] font-medium text-white transition hover:bg-brand-600 dark:bg-brand-500 dark:hover:bg-brand-400"
                        >
                          Aplicar
                        </button>
                      ) : null}
                    </div>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
