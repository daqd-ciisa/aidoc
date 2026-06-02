import { useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  Bot,
  FileText,
  Filter,
  MessageSquarePlus,
  MessagesSquare,
  Receipt,
  Sparkles,
  Trash2,
  User,
  Wand2,
} from "lucide-react";
import {
  deleteSession,
  getSession,
  listSessions,
  streamChat,
} from "../api/chat";
import { listDocuments } from "../api/documents";
import { generateQuote } from "../api/quotes";
import type {
  BasedOn,
  Citation,
  DocumentRead,
  MessageRead,
  QuoteDraft,
  SessionRead,
} from "../api/types";
import QuotePanel from "../components/QuotePanel";
import GuidedQuoteModal from "../components/GuidedQuoteModal";

interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
  citations: Citation[] | null;
  error?: string;
}

const SUGGESTIONS = [
  "Resumí los puntos clave de mis documentos",
  "¿Qué servicios y precios se mencionan?",
  "Listá las fechas y plazos importantes",
];

function toDisplay(m: MessageRead): DisplayMessage {
  return { role: m.role, content: m.content, citations: m.citations };
}

function patchLast(
  msgs: DisplayMessage[],
  patch: Partial<DisplayMessage> | ((m: DisplayMessage) => Partial<DisplayMessage>)
): DisplayMessage[] {
  if (msgs.length === 0) return msgs;
  const copy = msgs.slice();
  const last = copy[copy.length - 1];
  const p = typeof patch === "function" ? patch(last) : patch;
  copy[copy.length - 1] = { ...last, ...p };
  return copy;
}

export default function ChatPage() {
  const [sessions, setSessions] = useState<SessionRead[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [docs, setDocs] = useState<DocumentRead[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [showDocPicker, setShowDocPicker] = useState(false);
  const [quote, setQuote] = useState<QuoteDraft | null>(null);
  const [basedOn, setBasedOn] = useState<BasedOn | null>(null);
  const [quoteId, setQuoteId] = useState<string | null>(null);
  const [showGuided, setShowGuided] = useState(false);
  const [quoteBusy, setQuoteBusy] = useState(false);
  const [quoteErr, setQuoteErr] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    refreshSessions();
    loadDocs();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function refreshSessions() {
    try {
      setSessions(await listSessions());
    } catch {
      /* ignore */
    }
  }

  async function loadDocs() {
    try {
      const all = await listDocuments();
      setDocs(all.filter((d) => d.status === "indexed"));
    } catch {
      /* ignore */
    }
  }

  async function openSession(id: string) {
    setSessionId(id);
    try {
      const detail = await getSession(id);
      setMessages(detail.messages.map(toDisplay));
    } catch {
      setMessages([]);
    }
  }

  function newChat() {
    setSessionId(null);
    setMessages([]);
  }

  async function onDeleteSession(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    await deleteSession(id);
    if (id === sessionId) newChat();
    refreshSessions();
  }

  function toggleDoc(id: string) {
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  async function send(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || streaming) return;
    setInput("");
    setMessages((m) => [
      ...m,
      { role: "user", content: msg, citations: null },
      { role: "assistant", content: "", citations: null },
    ]);
    setStreaming(true);

    await streamChat(
      {
        message: msg,
        session_id: sessionId,
        document_ids: selected.length ? selected : null,
      },
      {
        onMeta: (sid) => setSessionId(sid),
        onCitations: (c) => setMessages((m) => patchLast(m, { citations: c })),
        onToken: (t) =>
          setMessages((m) => patchLast(m, (prev) => ({ content: prev.content + t }))),
        onError: (d) => setMessages((m) => patchLast(m, { error: d })),
        onDone: () => refreshSessions(),
      }
    );

    setStreaming(false);
    refreshSessions();
  }

  async function onGenerateQuote() {
    if (quoteBusy) return;
    setQuoteBusy(true);
    setQuoteErr(null);
    try {
      const res = await generateQuote({
        session_id: sessionId,
        document_ids: selected.length ? selected : null,
      });
      setQuote(res.quote);
      setBasedOn(null);
      setQuoteId(res.quote_id);
    } catch (e) {
      setQuoteErr(String(e));
    } finally {
      setQuoteBusy(false);
    }
  }

  return (
    <div className="flex h-full">
      {/* Sesiones */}
      <div className="flex w-72 shrink-0 flex-col border-r border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-900">
        <div className="p-3">
          <button onClick={newChat} className="btn-primary w-full">
            <MessageSquarePlus className="h-4 w-4" />
            Nueva conversación
          </button>
        </div>
        <div className="px-4 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-surface-400 dark:text-surface-500">
          Historial
        </div>
        <div className="flex-1 overflow-y-auto px-2 pb-2">
          {sessions.map((s) => {
            const active = s.id === sessionId;
            return (
              <div
                key={s.id}
                onClick={() => openSession(s.id)}
                className={`group flex cursor-pointer items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition ${
                  active
                    ? "bg-brand-50 text-brand-800 dark:bg-brand-500/15 dark:text-brand-200"
                    : "text-surface-700 hover:bg-surface-100 dark:text-surface-300 dark:hover:bg-surface-800"
                }`}
              >
                <MessagesSquare
                  className={`h-4 w-4 shrink-0 ${
                    active
                      ? "text-brand-600 dark:text-brand-400"
                      : "text-surface-400 dark:text-surface-500"
                  }`}
                />
                <span className="flex-1 truncate">{s.title}</span>
                <button
                  onClick={(e) => onDeleteSession(s.id, e)}
                  className="text-surface-400 opacity-0 transition hover:text-red-500 group-hover:opacity-100 dark:text-surface-500 dark:hover:text-red-400"
                  title="Borrar conversación"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            );
          })}
          {sessions.length === 0 && (
            <p className="px-3 py-6 text-center text-xs text-surface-400 dark:text-surface-500">
              Sin conversaciones todavía.
            </p>
          )}
        </div>
      </div>

      {/* Conversación */}
      <div className="flex flex-1 flex-col bg-surface-50 dark:bg-surface-900">
        <div className="flex-1 overflow-y-auto px-6 py-8">
          {messages.length === 0 ? (
            <EmptyState onPick={(s) => send(s)} />
          ) : (
            <div className="mx-auto max-w-3xl space-y-6">
              {messages.map((m, i) => (
                <MessageBubble key={i} msg={m} streaming={streaming} />
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-surface-200 bg-white px-6 py-4 dark:border-surface-800 dark:bg-surface-900">
          <div className="mx-auto max-w-3xl">
            {quoteErr && (
              <div className="mb-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600 ring-1 ring-red-100 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-500/20">
                {quoteErr}
              </div>
            )}
            <div className="rounded-2xl border border-surface-300 bg-white shadow-soft transition focus-within:border-brand-300 focus-within:ring-2 focus-within:ring-brand-100 dark:border-surface-700 dark:bg-surface-800 dark:focus-within:border-brand-600 dark:focus-within:ring-brand-500/20">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
                rows={1}
                placeholder="Preguntá algo sobre tus documentos…"
                className="max-h-40 w-full resize-none rounded-2xl bg-transparent px-4 pt-3 text-sm text-surface-800 placeholder:text-surface-400 focus:outline-none dark:text-surface-100 dark:placeholder:text-surface-500"
              />
              <div className="flex items-center justify-between gap-2 px-2.5 pb-2.5 pt-1">
                <div className="flex items-center gap-1">
                  <DocPicker
                    docs={docs}
                    selected={selected}
                    open={showDocPicker}
                    onToggleOpen={() => setShowDocPicker((v) => !v)}
                    onToggle={toggleDoc}
                  />
                  <button
                    onClick={() => setShowGuided(true)}
                    className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-brand-700 transition hover:bg-brand-50 dark:text-brand-300 dark:hover:bg-brand-500/15"
                  >
                    <Wand2 className="h-3.5 w-3.5" />
                    Cotización guiada
                  </button>
                  <button
                    onClick={onGenerateQuote}
                    disabled={quoteBusy}
                    className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-surface-600 transition hover:bg-surface-100 hover:text-surface-900 disabled:opacity-40 dark:text-surface-400 dark:hover:bg-surface-700 dark:hover:text-surface-100"
                  >
                    <Receipt className="h-3.5 w-3.5" />
                    {quoteBusy ? "Generando…" : "Desde contexto"}
                  </button>
                </div>
                <button
                  onClick={() => send()}
                  disabled={streaming || !input.trim()}
                  className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-white shadow-soft transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-surface-300 disabled:shadow-none dark:bg-brand-500 dark:hover:bg-brand-400 dark:disabled:bg-surface-700"
                  title="Enviar"
                >
                  <ArrowUp className="h-4 w-4" strokeWidth={2.4} />
                </button>
              </div>
            </div>
            <p className="mt-2 text-center text-[11px] text-surface-400 dark:text-surface-500">
              AIDOC puede cometer errores. Verificá la información citada.
            </p>
          </div>
        </div>
      </div>

      {quote && (
        <QuotePanel
          draft={quote}
          basedOn={basedOn}
          quoteId={quoteId}
          onClose={() => {
            setQuote(null);
            setBasedOn(null);
            setQuoteId(null);
          }}
        />
      )}

      {showGuided && (
        <GuidedQuoteModal
          sessionId={sessionId}
          onClose={() => setShowGuided(false)}
          onDrafted={(d, b, id) => {
            setQuote(d);
            setBasedOn(b);
            setQuoteId(id);
            setShowGuided(false);
          }}
        />
      )}
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (s: string) => void }) {
  return (
    <div className="mx-auto mt-10 max-w-xl text-center animate-fade-in">
      <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand text-white shadow-card dark:bg-brand-500">
        <Sparkles className="h-7 w-7" strokeWidth={2} />
      </div>
      <h2 className="text-xl font-bold tracking-tight text-surface-900 dark:text-surface-50">
        ¿Qué querés saber de tus documentos?
      </h2>
      <p className="mt-2 text-sm text-surface-500 dark:text-surface-400">
        Hacé una pregunta y AIDOC responde citando las fuentes exactas.
      </p>
      <div className="mt-6 grid gap-2 sm:grid-cols-1">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="group flex items-center gap-3 rounded-xl border border-surface-200 bg-white px-4 py-3 text-left text-sm text-surface-700 shadow-soft transition hover:border-brand-300 hover:bg-brand-50 dark:border-surface-800 dark:bg-surface-800/50 dark:text-surface-300 dark:hover:border-brand-600 dark:hover:bg-surface-800"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-surface-100 text-surface-500 transition group-hover:bg-brand-100 group-hover:text-brand-600 dark:bg-surface-700 dark:text-surface-400 dark:group-hover:bg-brand-500/20 dark:group-hover:text-brand-300">
              <MessagesSquare className="h-4 w-4" />
            </span>
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageBubble({
  msg,
  streaming,
}: {
  msg: DisplayMessage;
  streaming: boolean;
}) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex gap-3 animate-fade-in ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg shadow-soft ${
          isUser
            ? "bg-surface-200 text-surface-600 dark:bg-surface-700 dark:text-surface-300"
            : "bg-brand text-white dark:bg-brand-500"
        }`}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Contenido */}
      <div className={`min-w-0 max-w-[80%] ${isUser ? "items-end" : ""}`}>
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? "bg-brand text-white dark:bg-brand-500"
              : "border border-surface-200 bg-white text-surface-800 shadow-soft dark:border-surface-800 dark:bg-surface-800 dark:text-surface-100"
          }`}
        >
          {msg.content ? (
            <p className="whitespace-pre-wrap">{msg.content}</p>
          ) : msg.error ? null : (
            <span className="inline-flex items-center gap-1.5 text-surface-400 dark:text-surface-500">
              <Bot className="h-3.5 w-3.5" />
              <span className="flex gap-1">
                <span className="h-1.5 w-1.5 animate-blink rounded-full bg-surface-400 dark:bg-surface-500" />
                <span
                  className="h-1.5 w-1.5 animate-blink rounded-full bg-surface-400 dark:bg-surface-500"
                  style={{ animationDelay: "0.2s" }}
                />
                <span
                  className="h-1.5 w-1.5 animate-blink rounded-full bg-surface-400 dark:bg-surface-500"
                  style={{ animationDelay: "0.4s" }}
                />
              </span>
            </span>
          )}
          {msg.error && (
            <p className="text-red-500 dark:text-red-300">⚠ {msg.error}</p>
          )}
        </div>

        {/* Citas */}
        {msg.citations && msg.citations.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {msg.citations.map((c) => (
              <span
                key={c.ref}
                title={c.snippet}
                className="inline-flex items-center gap-1.5 rounded-full border border-surface-200 bg-white px-2.5 py-1 text-xs text-surface-600 shadow-soft transition hover:border-brand-300 hover:text-brand-700 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-300 dark:hover:border-brand-600 dark:hover:text-brand-300"
              >
                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-brand-50 text-[10px] font-semibold text-brand-700 dark:bg-brand-500/20 dark:text-brand-300">
                  {c.ref}
                </span>
                <FileText className="h-3 w-3 text-surface-400 dark:text-surface-500" />
                <span className="max-w-[160px] truncate">{c.filename}</span>
                {c.page ? (
                  <span className="text-surface-400 dark:text-surface-500">
                    · p.{c.page}
                  </span>
                ) : null}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function DocPicker({
  docs,
  selected,
  open,
  onToggleOpen,
  onToggle,
}: {
  docs: DocumentRead[];
  selected: string[];
  open: boolean;
  onToggleOpen: () => void;
  onToggle: (id: string) => void;
}) {
  const filtering = selected.length > 0;
  return (
    <div className="relative">
      <button
        onClick={onToggleOpen}
        className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition ${
          filtering
            ? "bg-brand-50 text-brand-700 ring-1 ring-brand-200 dark:bg-brand-500/15 dark:text-brand-300 dark:ring-brand-500/30"
            : "text-surface-600 hover:bg-surface-100 hover:text-surface-900 dark:text-surface-400 dark:hover:bg-surface-700 dark:hover:text-surface-100"
        }`}
      >
        <Filter className="h-3.5 w-3.5" />
        {filtering ? `${selected.length} documento(s)` : "Todos los documentos"}
      </button>
      {open && (
        <div className="absolute bottom-10 left-0 z-10 max-h-64 w-80 overflow-y-auto rounded-xl border border-surface-200 bg-white p-1.5 shadow-pop animate-scale-in dark:border-surface-700 dark:bg-surface-800">
          {docs.length === 0 && (
            <p className="px-3 py-3 text-xs text-surface-400 dark:text-surface-500">
              No hay documentos indexados todavía.
            </p>
          )}
          {docs.map((d) => {
            const checked = selected.includes(d.id);
            return (
              <label
                key={d.id}
                className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition hover:bg-surface-50 dark:hover:bg-surface-700"
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggle(d.id)}
                  className="h-4 w-4 rounded border-surface-300 text-brand focus:ring-brand-300 dark:border-surface-600 dark:bg-surface-700"
                />
                <FileText className="h-4 w-4 shrink-0 text-surface-400 dark:text-surface-500" />
                <span className="truncate text-surface-700 dark:text-surface-300">
                  {d.filename}
                </span>
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}
