import { useState } from "react";
import {
  AlertTriangle,
  FileDown,
  FileText,
  Loader2,
  Pencil,
  Plus,
  Receipt,
  RotateCw,
  Save,
  Trash2,
  X,
} from "lucide-react";
import type { BasedOn, QuoteDraft, QuoteItem } from "../api/types";
import { downloadQuotePdf, updateQuote } from "../api/quotes";

function fmt(n: number | null, currency?: string | null): string {
  if (n == null) return "—";
  const s = n.toLocaleString("es-MX", { minimumFractionDigits: 2 });
  return currency ? `${currency} ${s}` : s;
}

function round2(n: number): number {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

// IVA por defecto en México (16%).
const IVA_RATE = 0.16;

function toNum(s: string): number | null {
  if (s.trim() === "") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

const inputCls =
  "w-full rounded-lg border border-surface-300 bg-white px-2.5 py-1.5 text-sm text-surface-800 outline-none transition focus:border-brand-400 focus:ring-2 focus:ring-brand-100 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-100 dark:focus:border-brand-500 dark:focus:ring-brand-500/20";

function fmtDateISO(iso: string | null): string | null {
  if (!iso) return null;
  try {
    return new Date(`${iso}T00:00:00`).toLocaleDateString("es-MX", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-[11px] font-semibold uppercase tracking-wide text-surface-400 dark:text-surface-500">
        {label}
      </dt>
      <dd className="mt-0.5 text-sm font-medium text-surface-800 dark:text-surface-100">
        {value || "—"}
      </dd>
    </div>
  );
}

function EditField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string | null;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="text-[11px] font-semibold uppercase tracking-wide text-surface-400 dark:text-surface-500">
        {label}
      </label>
      <input
        className={`${inputCls} mt-1`}
        value={value ?? ""}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

export default function QuotePanel({
  draft,
  onClose,
  basedOn,
  quoteId,
  onSaved,
}: {
  draft: QuoteDraft;
  onClose: () => void;
  basedOn?: BasedOn[] | null;
  quoteId?: string | null;
  onSaved?: (updated: QuoteDraft) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<QuoteDraft>(draft);
  // Si está en true, los impuestos se autocalculan como IVA 16% del subtotal;
  // pasa a false en cuanto el usuario edita el campo a mano.
  const [taxAuto, setTaxAuto] = useState(true);
  const [saving, setSaving] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function download() {
    if (!quoteId) return;
    setDownloading(true);
    setErr(null);
    try {
      const name = draft.cliente ? `Cotizacion ${draft.cliente}` : "cotizacion";
      await downloadQuotePdf(quoteId, name);
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    } finally {
      setDownloading(false);
    }
  }

  const cur = (editing ? form : draft).moneda;

  // Totales recalculados en vivo durante la edición.
  const editItems = form.items.map((it) => ({
    ...it,
    importe: round2((it.cantidad ?? 0) * (it.precio_unitario ?? 0)),
  }));
  const editSubtotal = round2(editItems.reduce((a, it) => a + (it.importe ?? 0), 0));
  // Impuestos: por defecto IVA 16% del subtotal (se recalcula al cambiar el
  // subtotal); editable y sobrescribible manualmente.
  const autoTax = round2(editSubtotal * IVA_RATE);
  const editTax = taxAuto ? autoTax : form.impuestos ?? 0;
  const editTotal = round2(editSubtotal + editTax);

  function startEdit() {
    setForm(draft);
    setErr(null);
    setTaxAuto(true);
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
    setErr(null);
  }

  function patchItem(i: number, patch: Partial<QuoteItem>) {
    setForm((f) => ({
      ...f,
      items: f.items.map((it, idx) => (idx === i ? { ...it, ...patch } : it)),
    }));
  }

  function addItem() {
    setForm((f) => ({
      ...f,
      items: [
        ...f.items,
        {
          servicio: "",
          descripcion: null,
          cantidad: 1,
          precio_unitario: null,
          importe: null,
        },
      ],
    }));
  }

  function removeItem(i: number) {
    setForm((f) => ({ ...f, items: f.items.filter((_, idx) => idx !== i) }));
  }

  async function save() {
    if (!quoteId) return;
    setSaving(true);
    setErr(null);
    const updated: QuoteDraft = {
      ...form,
      items: editItems,
      subtotal: editSubtotal,
      impuestos: editTax,
      total: editTotal,
    };
    try {
      await updateQuote(quoteId, updated);
      onSaved?.(updated);
      setEditing(false);
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-surface-900/40 p-4 backdrop-blur-sm animate-fade-in dark:bg-black/60"
      onClick={editing ? undefined : onClose}
    >
      <div
        className="max-h-[88vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-pop animate-scale-in dark:bg-surface-800"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-surface-200 px-6 py-4 dark:border-surface-700">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-400">
              <Receipt className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-surface-900 dark:text-surface-50">
                Cotización
              </h2>
              <p className="text-xs text-surface-400 dark:text-surface-500">
                {editing
                  ? "Editá los campos y guardá los cambios"
                  : "Generada a partir de tus documentos"}
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

        <div className="px-6 py-5">
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

          {/* Datos de cabecera */}
          {editing ? (
            <div className="mb-5 grid grid-cols-3 gap-4">
              <EditField
                label="Cliente"
                value={form.cliente}
                onChange={(v) => setForm((f) => ({ ...f, cliente: v || null }))}
              />
              <EditField
                label="Moneda"
                value={form.moneda}
                placeholder="MXN"
                onChange={(v) => setForm((f) => ({ ...f, moneda: v || null }))}
              />
              <EditField
                label="Vigencia"
                value={form.vigencia}
                placeholder="30 días"
                onChange={(v) => setForm((f) => ({ ...f, vigencia: v || null }))}
              />
              <div>
                <label className="text-[11px] font-semibold uppercase tracking-wide text-surface-400 dark:text-surface-500">
                  Válida hasta
                </label>
                <input
                  type="date"
                  className={`${inputCls} mt-1`}
                  value={form.valida_hasta ?? ""}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, valida_hasta: e.target.value || null }))
                  }
                />
              </div>
            </div>
          ) : (
            <dl className="mb-5 grid grid-cols-3 gap-4 rounded-xl bg-surface-50 px-4 py-3 ring-1 ring-surface-200 dark:bg-surface-900/50 dark:ring-surface-700">
              <Field label="Cliente" value={draft.cliente} />
              <Field label="Moneda" value={draft.moneda} />
              <Field label="Vigencia" value={draft.vigencia} />
              <Field label="Válida hasta" value={fmtDateISO(draft.valida_hasta)} />
            </dl>
          )}

          {/* Ítems */}
          <div className="overflow-hidden rounded-xl border border-surface-200 dark:border-surface-700">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-200 bg-surface-50 text-left text-[11px] font-semibold uppercase tracking-wider text-surface-500 dark:border-surface-700 dark:bg-surface-900/50 dark:text-surface-400">
                  <th className="px-4 py-2.5">Servicio</th>
                  <th className="px-4 py-2.5 text-right">Cant.</th>
                  <th className="px-4 py-2.5 text-right">P. unit.</th>
                  <th className="px-4 py-2.5 text-right">Importe</th>
                  {editing && <th className="w-10 px-2 py-2.5" />}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100 dark:divide-surface-700">
                {!editing && draft.items.length === 0 && (
                  <tr>
                    <td
                      colSpan={4}
                      className="px-4 py-6 text-center text-surface-400 dark:text-surface-500"
                    >
                      Sin ítems extraídos.
                    </td>
                  </tr>
                )}

                {!editing &&
                  draft.items.map((it, i) => (
                    <tr key={i}>
                      <td className="px-4 py-3">
                        <div className="font-medium text-surface-800 dark:text-surface-100">
                          {it.servicio}
                        </div>
                        {it.descripcion && (
                          <div className="mt-0.5 text-xs text-surface-500 dark:text-surface-400">
                            {it.descripcion}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-surface-600 dark:text-surface-400">
                        {fmt(it.cantidad)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-surface-600 dark:text-surface-400">
                        {fmt(it.precio_unitario)}
                      </td>
                      <td className="px-4 py-3 text-right font-medium tabular-nums text-surface-800 dark:text-surface-100">
                        {fmt(it.importe)}
                      </td>
                    </tr>
                  ))}

                {editing &&
                  form.items.map((it, i) => (
                    <tr key={i} className="align-top">
                      <td className="px-3 py-2.5">
                        <input
                          className={inputCls}
                          placeholder="Servicio"
                          value={it.servicio}
                          onChange={(e) =>
                            patchItem(i, { servicio: e.target.value })
                          }
                        />
                        <input
                          className={`${inputCls} mt-1.5 text-xs`}
                          placeholder="Descripción (opcional)"
                          value={it.descripcion ?? ""}
                          onChange={(e) =>
                            patchItem(i, { descripcion: e.target.value || null })
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
                            patchItem(i, { cantidad: toNum(e.target.value) })
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
                            patchItem(i, {
                              precio_unitario: toNum(e.target.value),
                            })
                          }
                        />
                      </td>
                      <td className="px-4 py-2.5 text-right align-middle tabular-nums font-medium text-surface-800 dark:text-surface-100">
                        {fmt(editItems[i].importe)}
                      </td>
                      <td className="px-2 py-2.5 align-middle">
                        <button
                          onClick={() => removeItem(i)}
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
            {editing && (
              <button
                onClick={addItem}
                className="flex w-full items-center justify-center gap-1.5 border-t border-surface-200 bg-surface-50 py-2 text-xs font-medium text-brand-600 transition hover:bg-brand-50 dark:border-surface-700 dark:bg-surface-900/50 dark:text-brand-400 dark:hover:bg-brand-500/10"
              >
                <Plus className="h-3.5 w-3.5" />
                Agregar ítem
              </button>
            )}
          </div>

          {/* Totales */}
          <div className="mt-4 flex justify-end">
            <dl className="w-64 space-y-1.5 text-sm">
              <div className="flex items-center justify-between">
                <dt className="text-surface-500 dark:text-surface-400">Subtotal</dt>
                <dd className="tabular-nums text-surface-700 dark:text-surface-200">
                  {fmt(editing ? editSubtotal : draft.subtotal, cur)}
                </dd>
              </div>
              <div className="flex items-center justify-between gap-2">
                <dt className="flex items-center gap-1.5 text-surface-500 dark:text-surface-400">
                  Impuestos
                  {editing &&
                    (taxAuto ? (
                      <span className="text-[10px] font-medium text-surface-400 dark:text-surface-500">
                        IVA 16%
                      </span>
                    ) : (
                      <button
                        onClick={() => setTaxAuto(true)}
                        title="Volver al IVA 16% automático"
                        className="inline-flex items-center gap-0.5 text-[10px] font-medium text-brand-600 transition hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300"
                      >
                        <RotateCw className="h-3 w-3" />
                        16%
                      </button>
                    ))}
                </dt>
                <dd className="tabular-nums text-surface-700 dark:text-surface-200">
                  {editing ? (
                    <input
                      type="number"
                      step="any"
                      className={`${inputCls} w-28 text-right`}
                      value={editTax}
                      onChange={(e) => {
                        setTaxAuto(false);
                        setForm((f) => ({ ...f, impuestos: toNum(e.target.value) }));
                      }}
                    />
                  ) : (
                    fmt(draft.impuestos, cur)
                  )}
                </dd>
              </div>
              <div className="flex items-center justify-between border-t border-surface-200 pt-1.5 text-base font-bold text-surface-900 dark:border-surface-700 dark:text-surface-50">
                <dt>Total</dt>
                <dd className="tabular-nums text-brand-700 dark:text-brand-300">
                  {fmt(editing ? editTotal : draft.total, cur)}
                </dd>
              </div>
            </dl>
          </div>

          {/* Condiciones */}
          {editing ? (
            <div className="mt-5">
              <label className="text-[11px] font-semibold uppercase tracking-wide text-surface-400 dark:text-surface-500">
                Condiciones
              </label>
              <textarea
                className={`${inputCls} mt-1 min-h-[64px] resize-y`}
                value={form.condiciones ?? ""}
                placeholder="Condiciones comerciales (opcional)"
                onChange={(e) =>
                  setForm((f) => ({ ...f, condiciones: e.target.value || null }))
                }
              />
            </div>
          ) : (
            draft.condiciones && (
              <div className="mt-5">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-surface-400 dark:text-surface-500">
                  Condiciones
                </p>
                <p className="mt-1 text-sm text-surface-700 dark:text-surface-300">
                  {draft.condiciones}
                </p>
              </div>
            )
          )}

          {!editing && draft.no_encontrado.length > 0 && (
            <div className="mt-4 flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2.5 text-xs text-amber-700 ring-1 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/30">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                No se encontró en los documentos:{" "}
                {draft.no_encontrado.join(", ")}
              </span>
            </div>
          )}

          {err && (
            <div className="mt-4 rounded-lg bg-red-50 px-3 py-2.5 text-xs text-red-600 ring-1 ring-red-200 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/30">
              {err}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-3 border-t border-surface-200 bg-surface-50 px-6 py-3.5 dark:border-surface-700 dark:bg-surface-900/50">
          {editing ? (
            <>
              <button
                onClick={cancelEdit}
                disabled={saving}
                className="inline-flex items-center gap-1.5 rounded-lg border border-surface-300 bg-white px-3 py-1.5 text-xs font-medium text-surface-600 transition hover:bg-surface-100 disabled:opacity-50 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-300 dark:hover:bg-surface-700"
              >
                Cancelar
              </button>
              <button
                onClick={save}
                disabled={saving}
                className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3.5 py-1.5 text-xs font-medium text-white shadow-soft transition hover:bg-brand-600 disabled:opacity-50 dark:bg-brand-500 dark:hover:bg-brand-400"
              >
                {saving ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Save className="h-3.5 w-3.5" />
                )}
                {saving ? "Guardando…" : "Guardar cambios"}
              </button>
            </>
          ) : (
            <>
              {quoteId ? (
                <button
                  onClick={startEdit}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-surface-300 bg-white px-3 py-1.5 text-xs font-medium text-surface-700 transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200 dark:hover:border-brand-600 dark:hover:bg-brand-500/10"
                >
                  <Pencil className="h-3.5 w-3.5" />
                  Editar
                </button>
              ) : (
                <span className="text-xs text-surface-400 dark:text-surface-500">
                  Descargá la cotización en PDF con plantilla genérica.
                </span>
              )}
              {quoteId ? (
                <button
                  onClick={download}
                  disabled={downloading}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-xs font-medium text-white shadow-soft transition hover:bg-brand-600 disabled:opacity-50 dark:bg-brand-500 dark:hover:bg-brand-400"
                >
                  {downloading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <FileDown className="h-3.5 w-3.5" />
                  )}
                  Descargar PDF
                </button>
              ) : (
                <button
                  disabled
                  title="Disponible al guardar la cotización"
                  className="inline-flex items-center gap-1.5 rounded-lg border border-surface-300 bg-white px-3 py-1.5 text-xs font-medium text-surface-400 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-500"
                >
                  <FileDown className="h-3.5 w-3.5" />
                  Descargar PDF
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
