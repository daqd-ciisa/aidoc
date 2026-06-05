export type UserRole = "superadmin" | "admin" | "member";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  organization_id: string | null;
  is_active: boolean;
  created_at: string;
}

export type DocumentStatus = "pending" | "processing" | "indexed" | "failed";

export interface DocumentRead {
  id: string;
  filename: string;
  extension: string;
  mime_type: string | null;
  size_bytes: number;
  status: DocumentStatus;
  chunk_count: number;
  source: string;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface UploadResult {
  documents: DocumentRead[];
  duplicates: string[];
  rejected: string[];
}

export interface Citation {
  ref: number;
  document_id: string;
  filename: string;
  page: number | null;
  chunk_index: number;
  snippet: string;
  score: number;
}

export interface SessionRead {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface MessageRead {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[] | null;
  created_at: string;
}

export interface SessionDetail extends SessionRead {
  messages: MessageRead[];
}

export interface QuoteItem {
  servicio: string;
  descripcion: string | null;
  cantidad: number | null;
  precio_unitario: number | null;
  importe: number | null;
}

export interface QuoteDraft {
  cliente: string | null;
  moneda: string | null;
  items: QuoteItem[];
  subtotal: number | null;
  impuestos: number | null;
  total: number | null;
  vigencia: string | null;
  condiciones: string | null;
  notas: string | null;
  no_encontrado: string[];
}

export interface QuoteGenerated {
  quote_id: string;
  title: string;
  quote: QuoteDraft;
  citations: Citation[];
}

// ── Propuesta completa ──────────────────────────────────────────────────────────

export interface ProposalSection {
  key: string;
  titulo: string;
  contenido: string;
  fuente: string; // "fijo" | "precedente" | "generado"
}

export interface ProposalDraft {
  kind: "proposal";
  cliente: string | null;
  fecha: string | null;
  secciones: ProposalSection[];
  economica: QuoteDraft;
}

export interface ProposalResult {
  quote_id: string;
  title: string;
  proposal: ProposalDraft;
  based_on: BasedOn | null;
  citations: Citation[];
}

export interface QuoteRead {
  id: string;
  title: string;
  session_id: string | null;
  data: QuoteDraft | ProposalDraft;
  created_at: string;
  updated_at: string;
}

export interface Precedent {
  document_id: string;
  filename: string;
  score: number;
  snippet: string;
  motivo?: string | null;
}

export interface PrecedentsResult {
  precedents: Precedent[];
}

export interface BasedOn {
  document_id: string;
  filename: string;
  score: number | null;
}

export interface GuidedQuoteResult {
  quote_id: string;
  title: string;
  quote: QuoteDraft;
  based_on: BasedOn | null;
  citations: Citation[];
}
