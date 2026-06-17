import { apiDelete, apiGet, apiPost, apiPut } from "./client";
import { authHeaders } from "../lib/auth";
import type {
  GuidedQuoteResult,
  PrecedentsResult,
  ProposalDraft,
  ProposalResult,
  QuoteDraft,
  QuoteRead,
  QuoteGenerated,
  ValidationReport,
} from "./types";

export interface GenerateQuoteBody {
  session_id?: string | null;
  document_ids?: string[] | null;
  instruction?: string | null;
  title?: string | null;
}

export const generateQuote = (body: GenerateQuoteBody) =>
  apiPost<QuoteGenerated>("/quotes/generate", body);

// ── Listado / gestión ──────────────────────────────────────────────────────────

export const listQuotes = () => apiGet<QuoteRead[]>("/quotes");
export const deleteQuote = (id: string) => apiDelete(`/quotes/${id}`);

// ── Flujo guiado por precedente ───────────────────────────────────────────────

export const findPrecedents = (request: string, topDocs?: number) =>
  apiPost<PrecedentsResult>("/quotes/precedents", {
    request,
    top_docs: topDocs ?? null,
  });

export interface FromPrecedentBody {
  request: string;
  document_ids: string[];
  session_id?: string | null;
  title?: string | null;
}

export const generateFromPrecedent = (body: FromPrecedentBody) =>
  apiPost<GuidedQuoteResult>("/quotes/from-precedent", body);

/** Genera la PROPUESTA COMPLETA (todas las secciones) desde el precedente. */
export const generateProposalFromPrecedent = (body: FromPrecedentBody) =>
  apiPost<ProposalResult>("/quotes/proposal-from-precedent", body);

// ── Flujo sin precedente (desde cero) ─────────────────────────────────────────

export interface FromScratchBody {
  request: string;
  session_id?: string | null;
  title?: string | null;
}

/** Genera una cotización económica DESDE CERO (sin precedente ni documentos). */
export const generateFromScratch = (body: FromScratchBody) =>
  apiPost<GuidedQuoteResult>("/quotes/from-scratch", body);

/** Genera la PROPUESTA COMPLETA DESDE CERO (sin precedente). */
export const generateProposalFromScratch = (body: FromScratchBody) =>
  apiPost<ProposalResult>("/quotes/proposal-from-scratch", body);

/** Guarda los cambios de una propuesta completa editada a mano. */
export const updateProposal = (
  quoteId: string,
  proposal: ProposalDraft,
  title?: string | null
) =>
  apiPut<QuoteRead>(`/quotes/${quoteId}/proposal`, {
    proposal,
    title: title ?? null,
  });

/** Descarga la cotización/propuesta con el token y dispara la descarga del archivo. */
async function downloadQuoteAs(
  quoteId: string,
  filename: string,
  format: "pdf" | "docx"
): Promise<void> {
  const res = await fetch(`/api/quotes/${quoteId}/${format}`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok)
    throw new Error(`No se pudo generar el ${format.toUpperCase()}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(`.${format}`) ? filename : `${filename}.${format}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Descarga el PDF (cotización o propuesta) con el token. */
export const downloadQuotePdf = (quoteId: string, filename: string) =>
  downloadQuoteAs(quoteId, filename, "pdf");

/** Descarga el Word (.docx) editable (cotización o propuesta) con el token. */
export const downloadQuoteDocx = (quoteId: string, filename: string) =>
  downloadQuoteAs(quoteId, filename, "docx");

// ── Validación contra fuentes aprobadas ─────────────────────────────────────────

/** Valida las afirmaciones técnicas de la cotización/propuesta contra el corpus
 * aprobado (doc_type=reference). Devuelve un veredicto con cita por afirmación. */
export const validateQuote = (quoteId: string) =>
  apiPost<ValidationReport>(`/quotes/${quoteId}/validate`);

// ── Edición manual ────────────────────────────────────────────────────────────

export const updateQuote = (
  quoteId: string,
  quote: QuoteDraft,
  title?: string | null
) => apiPut<QuoteRead>(`/quotes/${quoteId}`, { quote, title: title ?? null });
