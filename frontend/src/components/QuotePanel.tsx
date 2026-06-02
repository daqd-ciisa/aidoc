import { AlertTriangle, FileDown, FileText, Receipt, X } from "lucide-react";
import type { BasedOn, QuoteDraft } from "../api/types";

function fmt(n: number | null, currency?: string | null): string {
  if (n == null) return "—";
  const s = n.toLocaleString("es-MX", { minimumFractionDigits: 2 });
  return currency ? `${currency} ${s}` : s;
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

export default function QuotePanel({
  draft,
  onClose,
  basedOn,
  quoteId,
}: {
  draft: QuoteDraft;
  onClose: () => void;
  basedOn?: BasedOn | null;
  quoteId?: string | null;
}) {
  const cur = draft.moneda;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-surface-900/40 p-4 backdrop-blur-sm animate-fade-in dark:bg-black/60"
      onClick={onClose}
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
                Generada a partir de tus documentos
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
          {basedOn && (
            <div className="mb-4 flex items-center gap-2 rounded-lg bg-brand-50 px-3 py-2 text-xs text-brand-700 ring-1 ring-brand-100 dark:bg-brand-500/10 dark:text-brand-300 dark:ring-brand-500/20">
              <FileText className="h-4 w-4 shrink-0" />
              <span>
                Generada usando como base:{" "}
                <span className="font-semibold">{basedOn.filename}</span>
              </span>
            </div>
          )}
          <dl className="mb-5 grid grid-cols-3 gap-4 rounded-xl bg-surface-50 px-4 py-3 ring-1 ring-surface-200 dark:bg-surface-900/50 dark:ring-surface-700">
            <Field label="Cliente" value={draft.cliente} />
            <Field label="Moneda" value={draft.moneda} />
            <Field label="Vigencia" value={draft.vigencia} />
          </dl>

          <div className="overflow-hidden rounded-xl border border-surface-200 dark:border-surface-700">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-200 bg-surface-50 text-left text-[11px] font-semibold uppercase tracking-wider text-surface-500 dark:border-surface-700 dark:bg-surface-900/50 dark:text-surface-400">
                  <th className="px-4 py-2.5">Servicio</th>
                  <th className="px-4 py-2.5 text-right">Cant.</th>
                  <th className="px-4 py-2.5 text-right">P. unit.</th>
                  <th className="px-4 py-2.5 text-right">Importe</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100 dark:divide-surface-700">
                {draft.items.length === 0 && (
                  <tr>
                    <td
                      colSpan={4}
                      className="px-4 py-6 text-center text-surface-400 dark:text-surface-500"
                    >
                      Sin ítems extraídos.
                    </td>
                  </tr>
                )}
                {draft.items.map((it, i) => (
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
              </tbody>
            </table>
          </div>

          {/* Totales */}
          <div className="mt-4 flex justify-end">
            <dl className="w-64 space-y-1.5 text-sm">
              <div className="flex justify-between">
                <dt className="text-surface-500 dark:text-surface-400">Subtotal</dt>
                <dd className="tabular-nums text-surface-700 dark:text-surface-200">
                  {fmt(draft.subtotal, cur)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-surface-500 dark:text-surface-400">Impuestos</dt>
                <dd className="tabular-nums text-surface-700 dark:text-surface-200">
                  {fmt(draft.impuestos, cur)}
                </dd>
              </div>
              <div className="flex justify-between border-t border-surface-200 pt-1.5 text-base font-bold text-surface-900 dark:border-surface-700 dark:text-surface-50">
                <dt>Total</dt>
                <dd className="tabular-nums text-brand-700 dark:text-brand-300">
                  {fmt(draft.total, cur)}
                </dd>
              </div>
            </dl>
          </div>

          {draft.condiciones && (
            <div className="mt-5">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-surface-400 dark:text-surface-500">
                Condiciones
              </p>
              <p className="mt-1 text-sm text-surface-700 dark:text-surface-300">
                {draft.condiciones}
              </p>
            </div>
          )}

          {draft.no_encontrado.length > 0 && (
            <div className="mt-4 flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2.5 text-xs text-amber-700 ring-1 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/30">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                No se encontró en los documentos:{" "}
                {draft.no_encontrado.join(", ")}
              </span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-3 border-t border-surface-200 bg-surface-50 px-6 py-3.5 dark:border-surface-700 dark:bg-surface-900/50">
          <p className="text-xs text-surface-400 dark:text-surface-500">
            Descargá la cotización en PDF con plantilla genérica.
          </p>
          {quoteId ? (
            <a
              href={`/api/quotes/${quoteId}/pdf`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-xs font-medium text-white shadow-soft transition hover:bg-brand-600 dark:bg-brand-500 dark:hover:bg-brand-400"
            >
              <FileDown className="h-3.5 w-3.5" />
              Descargar PDF
            </a>
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
        </div>
      </div>
    </div>
  );
}
