import { apiDelete, apiGet } from "./client";
import { authHeaders, clearToken, notifyUnauthorized } from "../lib/auth";
import type { Citation, SessionDetail, SessionRead } from "./types";

export const listSessions = () => apiGet<SessionRead[]>("/chat/sessions");
export const getSession = (id: string) =>
  apiGet<SessionDetail>(`/chat/sessions/${id}`);
export const deleteSession = (id: string) => apiDelete(`/chat/sessions/${id}`);

export interface ChatRequestBody {
  message: string;
  session_id?: string | null;
  document_ids?: string[] | null;
}

export interface ChatHandlers {
  onMeta?: (sessionId: string) => void;
  onCitations?: (citations: Citation[]) => void;
  onToken?: (text: string) => void;
  onError?: (detail: string) => void;
  onDone?: (sessionId: string) => void;
}

interface SSEvent {
  event: string;
  data: string;
}

function parseEvent(raw: string): SSEvent | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}

function dispatch(ev: SSEvent, h: ChatHandlers): void {
  let data: any;
  try {
    data = JSON.parse(ev.data);
  } catch {
    return;
  }
  switch (ev.event) {
    case "meta":
      h.onMeta?.(data.session_id);
      break;
    case "citations":
      h.onCitations?.(data as Citation[]);
      break;
    case "token":
      h.onToken?.(data.text);
      break;
    case "error":
      h.onError?.(data.detail);
      break;
    case "done":
      h.onDone?.(data.session_id);
      break;
  }
}

/** Llama a POST /api/chat y procesa el stream SSE token a token. */
export async function streamChat(
  body: ChatRequestBody,
  handlers: ChatHandlers,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    if (res.status === 401) {
      clearToken();
      notifyUnauthorized();
    }
    handlers.onError?.(`HTTP ${res.status}`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const raw of parts) {
      const ev = parseEvent(raw);
      if (ev) dispatch(ev, handlers);
    }
  }
}
