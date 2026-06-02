import { apiPost } from "./client";
import type {
  GuidedQuoteResult,
  PrecedentsResult,
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

// ── Flujo guiado por precedente ───────────────────────────────────────────────

export const findPrecedents = (request: string, topDocs?: number) =>
  apiPost<PrecedentsResult>("/quotes/precedents", {
    request,
    top_docs: topDocs ?? null,
  });

export interface FromPrecedentBody {
  request: string;
  document_id: string;
  session_id?: string | null;
  title?: string | null;
}

export const generateFromPrecedent = (body: FromPrecedentBody) =>
  apiPost<GuidedQuoteResult>("/quotes/from-precedent", body);
