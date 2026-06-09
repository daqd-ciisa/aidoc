import { useEffect, useState } from "react";
import {
  ChevronDown,
  Loader2,
  Receipt,
  ScrollText,
  Trash2,
  X,
} from "lucide-react";
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

function econOf(q: QuoteRead): QuoteDraft {
  return isProposal(q.data) ? q.data.economica : q.data;
}
function clienteOf(q: QuoteRead): string {
  return econOf(q).cliente?.trim() || "Sin cliente";
}
const todayISO = (): string => new Date().toISOString().slice(0, 10);

const ctrlCls =
  "rounded-lg border border-surface-300 bg-white px-2.5 py-1.5 text-sm text-surface-700 outline-none transition focus:border-brand-400 focus:ring-2 focus:ring-brand-100 dark:border-surface-600 dark:bg-surface-900 dark:text-surface-200 dark:focus:border-brand-500 dark:focus:ring-brand-500/20";
const selectCls = `${ctrlCls} w-full cursor-pointer appearance-none pr-9`;
const dateCls = `${ctrlCls} cursor-pointer [color-scheme:light] dark:[color-scheme:dark]`;
const fLabelCls =
  "text-[11px] font-semibold uppercase tracking-wide text-surface-400 dark:text-surface-500";

/** Select estilizado (chevron propio, sin la apariencia nativa del navegador). */
function FilterSelect({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-w-[8.5rem] flex-col gap-1">
      <label className={fLabelCls}>{label}</label>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={selectCls}
        >
          {children}
        </select>
        <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-400 dark:text-surface-500" />
      </div>
    </div>
  );
}

export default function QuotesPage() {
  const [items, setItems] = useState<QuoteRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState<QuoteRead | null>(null);

  // Filtros
  const [fCliente, setFCliente] = useState("");
  const [fDesde, setFDesde] = useState("");
  const [fHasta, setFHasta] = useState("");
  const [fVig, setFVig] = useState<"all" | "vigente" | "vencida">("all");

  useEffect(() => {
    refresh();
  }, []);

  const clientes = Array.from(new Set(items.map(clienteOf))).sort((a, b) =>
    a.localeCompare(b, "es")
  );
  const today = todayISO();
  const filtered = items.filter((q) => {
    if (fCliente && clienteOf(q) !== fCliente) return false;
    const created = q.created_at.slice(0, 10);
    if (fDesde && created < fDesde) return false;
    if (fHasta && created > fHasta) return false;
    if (fVig !== "all") {
      const vh = econOf(q).valida_hasta;
      if (!vh) return false; // sin fecha de validez → no clasifica como vigente/vencida
      const vigente = vh >= today;
      if (fVig === "vigente" && !vigente) return false;
      if (fVig === "vencida" && vigente) return false;
    }
    return true;
  });
  const anyFilter = !!(fCliente || fDesde || fHasta || fVig !== "all");
  function clearFilters() {
    setFCliente("");
    setFDesde("");
    setFHasta("");
    setFVig("all");
  }

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
            Cotizaciones
          </h1>
          <p className="mt-1 text-sm text-surface-500 dark:text-surface-400">
            Lo que generaste desde el chat. Abrí para editar o descargar el PDF.
          </p>
        </div>

        {!loading && items.length > 0 && (
          <div className="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-surface-200 bg-white px-4 py-3 dark:border-surface-800 dark:bg-surface-800/60">
            <FilterSelect label="Empresa" value={fCliente} onChange={setFCliente}>
              <option value="">Todas</option>
              {clientes.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </FilterSelect>
            <div className="flex flex-col gap-1">
              <label className={fLabelCls}>Creada desde</label>
              <input
                type="date"
                value={fDesde}
                onChange={(e) => setFDesde(e.target.value)}
                className={dateCls}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className={fLabelCls}>Creada hasta</label>
              <input
                type="date"
                value={fHasta}
                onChange={(e) => setFHasta(e.target.value)}
                className={dateCls}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className={fLabelCls}>Validez</label>
              <div className="inline-flex rounded-lg border border-surface-300 bg-surface-100 p-0.5 dark:border-surface-600 dark:bg-surface-900">
                {(
                  [
                    ["all", "Todas"],
                    ["vigente", "Vigentes"],
                    ["vencida", "Vencidas"],
                  ] as ["all" | "vigente" | "vencida", string][]
                ).map(([v, lbl]) => (
                  <button
                    key={v}
                    onClick={() => setFVig(v)}
                    className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                      fVig === v
                        ? "bg-white text-brand-700 shadow-soft dark:bg-surface-700 dark:text-brand-300"
                        : "text-surface-500 hover:text-surface-800 dark:text-surface-400 dark:hover:text-surface-100"
                    }`}
                  >
                    {lbl}
                  </button>
                ))}
              </div>
            </div>
            {anyFilter && (
              <button
                onClick={clearFilters}
                className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium text-surface-500 transition hover:bg-surface-100 hover:text-surface-800 dark:text-surface-400 dark:hover:bg-surface-700 dark:hover:text-surface-100"
              >
                <X className="h-3.5 w-3.5" />
                Limpiar
              </button>
            )}
            <span className="ml-auto self-center text-xs text-surface-400 dark:text-surface-500">
              {filtered.length} de {items.length}
            </span>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-surface-300 py-16 text-center text-sm text-surface-400 dark:border-surface-700 dark:text-surface-500">
            Todavía no generaste ninguna cotización.
            <br />
            Generá una desde el Chat con “Cotización guiada”.
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-surface-300 py-16 text-center text-sm text-surface-400 dark:border-surface-700 dark:text-surface-500">
            No hay cotizaciones que coincidan con los filtros.
          </div>
        ) : (
          <div className="space-y-2.5">
            {filtered.map((q) => {
              const proposal = isProposal(q.data);
              const econ = proposal
                ? (q.data as ProposalDraft).economica
                : (q.data as QuoteDraft);
              const Icon = proposal ? ScrollText : Receipt;
              const vencida = econ.valida_hasta
                ? econ.valida_hasta < today
                : false;
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
                        {proposal ? "Completa" : "Económica"}
                      </span>
                      {vencida && (
                        <span className="shrink-0 rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-600 dark:bg-red-500/10 dark:text-red-400">
                          Vencida
                        </span>
                      )}
                    </div>
                    <div className="mt-0.5 truncate text-xs text-surface-400 dark:text-surface-500">
                      {econ.cliente || "Sin cliente"} · {fmtDate(q.created_at)}
                      {econ.valida_hasta &&
                        ` · vence ${fmtDate(`${econ.valida_hasta}T00:00:00`)}`}
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
