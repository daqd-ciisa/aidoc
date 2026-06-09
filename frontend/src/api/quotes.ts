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

/** Descarga el PDF (cotización o propuesta) con el token, y dispara la descarga. */
export async function downloadQuotePdf(
  quoteId: string,
  filename: string
): Promise<void> {
  const res = await fetch(`/api/quotes/${quoteId}/pdf`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error("No se pudo generar el PDF");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".pdf") ? filename : `${filename}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ── Edición manual ────────────────────────────────────────────────────────────

export const updateQuote = (
  quoteId: string,
  quote: QuoteDraft,
  title?: string | null
) => apiPut<QuoteRead>(`/quotes/${quoteId}`, { quote, title: title ?? null });
