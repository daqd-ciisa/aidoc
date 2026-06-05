import { useEffect, useState } from "react";
import { Loader2, Receipt, ScrollText, Trash2 } from "lucide-react";
import { deleteQuote, listQuotes } from "../api/quotes";
import type { ProposalDraft, QuoteDraft, QuoteRead } from "../api/types";
import QuotePanel from "../components/QuotePanel";
import ProposalPanel from "../components/ProposalPanel";

function isProposal(data: QuoteDraft | ProposalDraft): data is ProposalDraft {
  return (data as ProposalDraft).kind === "proposal";
}

function fmtMoney(n: number | null, cur?: string | null): string {
  if (n == null) return "—";
  const s = n.toLocaleString("es-MX", { minimumFractionDigits: 2 });
  return cur ? `${cur} ${s}` : s;
}

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("es-MX", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function QuotesPage() {
  const [items, setItems] = useState<QuoteRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState<QuoteRead | null>(null);

  useEffect(() => {
    refresh();
  }, []);

  async function refresh() {
    setLoading(true);
    try {
      setItems(await listQuotes());
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }

  async function onDelete(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    await deleteQuote(id);
    if (open?.id === id) setOpen(null);
    refresh();
  }

  function patchOpen(data: QuoteDraft | ProposalDraft) {
    setItems((list) =>
      list.map((q) => (open && q.id === open.id ? { ...q, data } : q))
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-surface-50 px-8 py-7 dark:bg-surface-900">
      <div className="mx-auto max-w-4xl">
        <div className="mb-6">
          <h1 className="text-xl font-bold tracking-tight text-surface-900 dark:text-surface-50">
            Cotizaciones y propuestas
          </h1>
          <p className="mt-1 text-sm text-surface-500 dark:text-surface-400">
            Lo que generaste desde el chat. Abrí para editar o descargar el PDF.
          </p>
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-surface-300 py-16 text-center text-sm text-surface-400 dark:border-surface-700 dark:text-surface-500">
            Todavía no generaste ninguna cotización ni propuesta.
            <br />
            Generá una desde el Chat con “Cotización guiada”.
          </div>
        ) : (
          <div className="space-y-2.5">
            {items.map((q) => {
              const proposal = isProposal(q.data);
              const econ = proposal
                ? (q.data as ProposalDraft).economica
                : (q.data as QuoteDraft);
              const Icon = proposal ? ScrollText : Receipt;
              return (
                <div
                  key={q.id}
                  onClick={() => setOpen(q)}
                  className="group flex cursor-pointer items-center gap-4 rounded-xl border border-surface-200 bg-white px-4 py-3.5 shadow-soft transition hover:border-brand-300 hover:shadow-card dark:border-surface-800 dark:bg-surface-800/60 dark:hover:border-brand-600"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-400">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-semibold text-surface-800 dark:text-surface-100">
                        {q.title}
                      </span>
                      <span className="shrink-0 rounded-full bg-surface-100 px-2 py-0.5 text-[10px] font-medium text-surface-500 dark:bg-surface-700 dark:text-surface-400">
                        {proposal ? "Propuesta" : "Cotización"}
                      </span>
                    </div>
                    <div className="mt-0.5 truncate text-xs text-surface-400 dark:text-surface-500">
                      {econ.cliente || "Sin cliente"} · {fmtDate(q.created_at)}
                    </div>
                  </div>
                  <div className="shrink-0 text-right">
                    <div className="text-sm font-semibold tabular-nums text-surface-800 dark:text-surface-100">
                      {fmtMoney(econ.total, econ.moneda)}
                    </div>
                  </div>
                  <button
                    onClick={(e) => onDelete(q.id, e)}
                    title="Borrar"
                    className="shrink-0 rounded-md p-1.5 text-surface-400 opacity-0 transition hover:bg-red-50 hover:text-red-600 group-hover:opacity-100 dark:text-surface-500 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {open && isProposal(open.data) && (
        <ProposalPanel
          proposal={open.data}
          quoteId={open.id}
          title={open.title}
          onClose={() => setOpen(null)}
          onSaved={(updated) => patchOpen(updated)}
        />
      )}
      {open && !isProposal(open.data) && (
        <QuotePanel
          draft={open.data}
          quoteId={open.id}
          onClose={() => setOpen(null)}
          onSaved={(updated) => patchOpen(updated)}
        />
      )}
    </div>
  );
}
