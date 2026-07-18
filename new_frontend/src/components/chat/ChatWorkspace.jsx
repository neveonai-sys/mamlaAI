import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  createSession, deleteSession, getDraftSections, getMessages, listSessions,
  renameSession, streamChat, updateDraftSection, uploadDoc,
} from '../../services/chatApi';

const LAST_SESSION_KEY = 'adalat_chat_last_session';

// Empty-state prompts that surface the chat's capabilities (research / citation
// / doc Q&A / drafting). Clicking one drops it into the composer.
const SUGGESTIONS = [
  { icon: 'search',      text: 'Research a legal question',           fill: 'What does the law say about ' },
  { icon: 'verified',    text: 'Verify a citation on e-SCR',          fill: 'Verify this citation: ' },
  { icon: 'description', text: 'Ask about an uploaded document',      fill: 'In the document I uploaded, ' },
  { icon: 'edit_note',   text: 'Draft a document',                    fill: 'Draft a ' },
];

// ─── Model selection (Low/Med/High + metered Premium) ────────────────────────
const MODEL_LEVELS = [
  { value: 'low',    label: 'Low',    hint: 'Fastest, lightest · cheapest' },
  { value: 'medium', label: 'Medium', hint: 'Balanced (default)' },
  { value: 'high',   label: 'High',   hint: 'Strongest reasoning · more credits' },
];

const CAPABILITY_LABEL = {
  draft: 'Drafting', citation: 'Citation lookup', doc_qa: 'Document Q&A',
  research: 'Legal research', meta: 'About Adalat', general: 'General',
};

// Short display name for a model slug ("anthropic/claude-opus-4.8" -> "claude-opus-4.8")
function modelShort(model) {
  if (!model) return '';
  return model.includes('/') ? model.split('/').pop() : model;
}

function ToolChip({ capability }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary text-xs px-2 py-0.5">
      <span className="material-symbols-outlined text-[14px]">bolt</span>
      {CAPABILITY_LABEL[capability] || capability}
    </span>
  );
}

// In-chat draft canvas: sections render inline and can be edited + saved
// without leaving the chat (write-through to the ai_draft engine). Heavy edits
// (add / delete / reorder) still live in the drafting workspace via the link.
function DraftPreviewCard({ artifact }) {
  const draftId = artifact.draft_session_id;
  const [sections, setSections] = useState(artifact.sections || []);
  const [open, setOpen] = useState(null);      // expanded section index
  const [editIdx, setEditIdx] = useState(null); // section index being edited
  const [draftText, setDraftText] = useState('');
  const [saving, setSaving] = useState(false);
  const [savedIdx, setSavedIdx] = useState(null); // last successfully-saved index (for the tick)
  const [copied, setCopied] = useState(false);

  // Re-sync live content from the engine so edits (here or in the workspace)
  // survive reloads and reflect the current draft, not the generation snapshot.
  useEffect(() => {
    let cancelled = false;
    if (!draftId) return undefined;
    getDraftSections(draftId)
      .then(({ data }) => { if (!cancelled && data.sections?.length) setSections(data.sections); })
      .catch(() => { /* keep the snapshot we already have */ });
    return () => { cancelled = true; };
  }, [draftId]);

  function startEdit(i) {
    setEditIdx(i);
    setOpen(i);
    setDraftText(sections[i].content || '');
    setSavedIdx(null);
  }

  async function saveEdit(i) {
    const section = sections[i];
    setSaving(true);
    try {
      const { data } = await updateDraftSection(draftId, {
        section_id: section.section_id,
        section_name: section.section_name,
        content: draftText,
      });
      setSections(data.sections?.length
        ? data.sections
        : sections.map((s, j) => (j === i ? { ...s, content: draftText } : s)));
      setEditIdx(null);
      setSavedIdx(i);
    } catch (_) {
      setSavedIdx(null);
    } finally {
      setSaving(false);
    }
  }

  function copyAll() {
    const text = sections.map((s) => `${s.section_name}\n\n${s.content}`).join('\n\n');
    navigator.clipboard?.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  function downloadAll() {
    const text = sections.map((s) => `${s.section_name}\n\n${s.content}`).join('\n\n\n');
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const base = (artifact.draft_name || artifact.draft_for || 'draft').replace(/[^\w.-]+/g, '_');
    a.href = url;
    a.download = `${base}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const editable = !!draftId;
  return (
    <div className="mt-3 rounded-xl border border-primary/30 bg-primary/5 overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-3">
        <span className="material-symbols-outlined text-primary">edit_note</span>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 truncate">{artifact.draft_for || 'Draft'}</div>
          <div className="text-xs text-gray-500">
            {sections.length
              ? `Draft saved · ${sections.length} section${sections.length > 1 ? 's' : ''}${editable ? ' — click a section to view or edit' : ''}`
              : 'Draft created'}
          </div>
        </div>
        {sections.length > 0 && (
          <div className="flex items-center gap-1 shrink-0">
            <button onClick={copyAll} title="Copy draft" className="text-gray-400 hover:text-primary p-1">
              <span className="material-symbols-outlined text-[18px]">{copied ? 'check' : 'content_copy'}</span>
            </button>
            <button onClick={downloadAll} title="Download as .txt" className="text-gray-400 hover:text-primary p-1">
              <span className="material-symbols-outlined text-[18px]">download</span>
            </button>
          </div>
        )}
      </div>
      {sections.length > 0 && (
        <div className="border-t border-primary/20 divide-y divide-primary/10 bg-white/60">
          {sections.map((s, i) => (
            <div key={s.section_id || i}>
              <button
                onClick={() => setOpen(open === i ? null : i)}
                className="w-full flex items-center justify-between px-4 py-2 text-left text-xs font-medium text-gray-700 hover:bg-primary/5"
              >
                <span className="flex items-center gap-1.5">
                  {i + 1}. {s.section_name}
                  {savedIdx === i && <span className="material-symbols-outlined text-[14px] text-emerald-500">check_circle</span>}
                </span>
                <span className="material-symbols-outlined text-[16px] text-gray-400">
                  {open === i ? 'expand_less' : 'expand_more'}
                </span>
              </button>
              {open === i && (
                <div className="px-4 pb-3">
                  {editIdx === i ? (
                    <>
                      <textarea
                        value={draftText}
                        onChange={(e) => setDraftText(e.target.value)}
                        rows={Math.min(16, Math.max(4, draftText.split('\n').length + 1))}
                        className="w-full resize-y border border-gray-300 rounded-lg px-3 py-2 text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary/30"
                      />
                      <div className="flex items-center justify-end gap-2 mt-2">
                        <button
                          onClick={() => setEditIdx(null)}
                          disabled={saving}
                          className="text-xs text-gray-500 px-3 py-1.5 rounded-lg hover:bg-gray-100"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => saveEdit(i)}
                          disabled={saving}
                          className="text-xs text-white bg-primary px-3 py-1.5 rounded-lg disabled:opacity-40 inline-flex items-center gap-1"
                        >
                          {saving && <span className="material-symbols-outlined animate-spin text-[14px]">progress_activity</span>}
                          Save
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="text-xs text-gray-600 whitespace-pre-wrap">{s.content}</div>
                      {editable && (
                        <button
                          onClick={() => startEdit(i)}
                          className="mt-2 inline-flex items-center gap-1 text-xs text-primary font-medium hover:underline"
                        >
                          <span className="material-symbols-outlined text-[14px]">edit</span>
                          Edit
                        </button>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      {artifact.deep_link && (
        <div className="border-t border-primary/20 px-4 py-2 bg-white/40">
          <Link to={artifact.deep_link} className="inline-flex items-center gap-1 text-xs text-primary font-medium">
            <span className="material-symbols-outlined text-[15px]">open_in_new</span>
            Open in Drafting Workspace (reorder, add or delete sections)
          </Link>
        </div>
      )}
    </div>
  );
}

function CitationCard({ artifact }) {
  return (
    <div className="mt-3 rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3">
      <div className="flex items-center gap-1.5 text-xs text-emerald-700 mb-1">
        <span className="material-symbols-outlined text-[15px]">verified</span>
        Verified · {artifact.source || 'e-SCR portal'}
      </div>
      <div className="text-sm font-semibold text-gray-900">{artifact.case_title}</div>
      <div className="text-xs text-gray-600 mt-1 space-x-3">
        {artifact.neutral_citation && <span>Neutral: {artifact.neutral_citation}</span>}
        {artifact.scr_citation && <span>SCR: {artifact.scr_citation}</span>}
      </div>
      {artifact.pdf_url && (
        <a href={artifact.pdf_url} target="_blank" rel="noreferrer"
          className="inline-flex items-center gap-1 text-xs text-primary mt-2">
          <span className="material-symbols-outlined text-[15px]">picture_as_pdf</span>
          Open judgment
        </a>
      )}
    </div>
  );
}

function Message({ msg }) {
  const isUser = msg.role === 'user';
  const chips = msg.tool_trace?.length
    ? msg.tool_trace.map((s) => s.capability)
    : (msg.capability ? [msg.capability] : []);
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-[80%] rounded-2xl px-4 py-3 whitespace-pre-wrap text-sm leading-relaxed
        ${isUser ? 'bg-primary text-white' : 'bg-white border border-gray-200 text-gray-800'}`}>
        {!isUser && chips.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {chips.map((c, i) => <ToolChip key={i} capability={c} />)}
          </div>
        )}
        {msg.content}
        {!isUser && (msg.artifacts || []).map((a, i) => {
          if (a.type === 'draft') return <DraftPreviewCard key={i} artifact={a} />;
          if (a.type === 'citation') return <CitationCard key={i} artifact={a} />;
          return null;
        })}
        {!isUser && (msg.model || msg.premium) && (
          <div className="mt-2 flex items-center gap-2 text-[11px] text-gray-400">
            {msg.model && <span>{modelShort(msg.model)}</span>}
            {msg.premium && (
              <span className="inline-flex items-center gap-0.5 rounded-full bg-amber-100 text-amber-700 px-1.5 py-0.5 font-medium">
                <span className="material-symbols-outlined text-[12px]">workspace_premium</span>
                Premium
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function relTime(iso) {
  const d = new Date(iso);
  if (isNaN(d)) return '';
  const mins = Math.floor((Date.now() - d.getTime()) / 60000);
  if (mins < 1) return 'now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function ChatWorkspace() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [modelLevel, setModelLevel] = useState('medium');
  const [premium, setPremium] = useState(false);
  const [premiumInfoOpen, setPremiumInfoOpen] = useState(false);
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [connectorsOpen, setConnectorsOpen] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [menuOpenId, setMenuOpenId] = useState(null);   // session with its ⋯ menu open
  const [renamingId, setRenamingId] = useState(null);   // session being renamed inline
  const [renameText, setRenameText] = useState('');
  const sessionIdRef = useRef(null);
  const fileInputRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, sending]);

  // On mount: load session list + restore last session's transcript.
  useEffect(() => {
    refreshSessions();
    const last = localStorage.getItem(LAST_SESSION_KEY);
    if (last) openSession(last);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refreshSessions() {
    try {
      const { data } = await listSessions({ page_size: 30 });
      setSessions(data.results || []);
    } catch (_) { /* sidebar list is best-effort */ }
  }

  async function openSession(sessionId) {
    try {
      const { data } = await getMessages(sessionId);
      sessionIdRef.current = sessionId;
      setActiveSessionId(sessionId);
      localStorage.setItem(LAST_SESSION_KEY, sessionId);
      setMessages(data.results || []);
      setError('');
    } catch (_) {
      // stale/deleted session — start fresh
      localStorage.removeItem(LAST_SESSION_KEY);
      startNewChat();
    }
  }

  function startNewChat() {
    sessionIdRef.current = null;
    setActiveSessionId(null);
    localStorage.removeItem(LAST_SESSION_KEY);
    setMessages([]);
    setDocs([]);
    setError('');
  }

  function beginRename(session) {
    setMenuOpenId(null);
    setRenamingId(session.id);
    setRenameText(session.title || '');
  }

  async function commitRename(sessionId) {
    const title = renameText.trim();
    setRenamingId(null);
    if (!title) return;
    setSessions((prev) => prev.map((s) => (s.id === sessionId ? { ...s, title } : s))); // optimistic
    try {
      await renameSession(sessionId, title);
    } catch (_) {
      refreshSessions(); // revert to server truth on failure
    }
  }

  async function handleDelete(session) {
    setMenuOpenId(null);
    // eslint-disable-next-line no-alert
    if (!window.confirm(`Delete "${session.title || 'this chat'}"? This can't be undone.`)) return;
    setSessions((prev) => prev.filter((s) => s.id !== session.id)); // optimistic
    if (session.id === activeSessionId) startNewChat();
    try {
      await deleteSession(session.id);
    } catch (_) {
      refreshSessions();
    }
  }

  async function ensureSession() {
    if (sessionIdRef.current) return sessionIdRef.current;
    const { data } = await createSession({ model_level: modelLevel });
    sessionIdRef.current = data.id;
    setActiveSessionId(data.id);
    localStorage.setItem(LAST_SESSION_KEY, data.id);
    refreshSessions();
    return data.id;
  }

  function patchLast(patch) {
    setMessages((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      next[next.length - 1] = typeof patch === 'function' ? patch(last) : { ...last, ...patch };
      return next;
    });
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || sending) return;
    setError('');
    setInput('');
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: text },
      { role: 'assistant', content: '', capability: '', artifacts: [], tool_trace: [] },
    ]);
    setSending(true);
    try {
      const sessionId = await ensureSession();
      await streamChat(sessionId, text, { model_level: modelLevel, premium }, {
        onToolCall: (evt) => patchLast({ capability: evt.capability }),
        onToolResult: (evt) => patchLast((last) => ({
          ...last, artifacts: [...(last.artifacts || []), ...(evt.artifacts || [])],
        })),
        onToken: (chunk) => patchLast((last) => ({ ...last, content: (last.content || '') + chunk })),
        onDone: (evt) => patchLast((last) => ({
          ...last,
          content: evt.text || last.content,
          tool_trace: evt.tool_trace || last.tool_trace,
          artifacts: (evt.artifacts && evt.artifacts.length) ? evt.artifacts : last.artifacts,
          model: evt.model || '',
          premium: !!evt.premium,
        })),
        onError: (msg) => setError(msg),
      });
      // Bump this thread to the top of the sidebar (server already updated
      // last_message_at); refresh to pick up an auto-generated title too.
      setSessions((prev) => {
        const idx = prev.findIndex((s) => s.id === sessionId);
        if (idx <= 0) return prev;
        const next = [...prev];
        const [moved] = next.splice(idx, 1);
        return [moved, ...next];
      });
      refreshSessions();
    } catch (e) {
      setError('Something went wrong. Please retry.');
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    setError('');
    setUploading(true);
    try {
      const sessionId = await ensureSession();
      const { data } = await uploadDoc(sessionId, file);
      setDocs((prev) => [...prev, { id: data.doc_id, name: file.name }]);
      setMessages((prev) => [...prev, {
        role: 'assistant', capability: 'doc_qa', artifacts: [], tool_trace: [],
        content: `📎 Attached **${file.name}**. Indexing now — ask me anything about it in a few seconds.`,
      }]);
    } catch (e2) {
      setError('Upload failed. Please retry.');
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="flex h-full bg-background-light">
      {/* ── Sessions sidebar ── */}
      {sidebarOpen && (
        <div className="w-60 shrink-0 border-r border-gray-200 bg-white flex flex-col">
          <div className="p-3">
            <button
              onClick={startNewChat}
              className="w-full flex items-center justify-center gap-1.5 rounded-lg border border-primary/40 text-primary text-sm font-medium py-2 hover:bg-primary/5"
            >
              <span className="material-symbols-outlined text-[18px]">add</span>
              New chat
            </button>
          </div>
          <div className="flex-1 overflow-y-auto px-2 pb-3">
            {sessions.length === 0 && (
              <p className="text-xs text-gray-400 px-2 py-3">No conversations yet.</p>
            )}
            {sessions.map((s) => (
              <div
                key={s.id}
                className={`group relative rounded-lg mb-1
                  ${s.id === activeSessionId ? 'bg-primary/10' : 'hover:bg-gray-50'}`}
              >
                {renamingId === s.id ? (
                  <input
                    autoFocus
                    value={renameText}
                    onChange={(e) => setRenameText(e.target.value)}
                    onBlur={() => commitRename(s.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') { e.preventDefault(); commitRename(s.id); }
                      if (e.key === 'Escape') setRenamingId(null);
                    }}
                    className="w-full rounded-lg px-3 py-2 text-sm border border-primary/40 focus:outline-none focus:ring-2 focus:ring-primary/30"
                  />
                ) : (
                  <>
                    <button
                      onClick={() => openSession(s.id)}
                      className={`w-full text-left rounded-lg pl-3 pr-8 py-2 text-sm
                        ${s.id === activeSessionId ? 'text-primary font-medium' : 'text-gray-700'}`}
                      title={s.title}
                    >
                      <div className="truncate">{s.title || 'Untitled chat'}</div>
                      <div className="text-[11px] text-gray-400">{relTime(s.last_message_at)}</div>
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setMenuOpenId(menuOpenId === s.id ? null : s.id); }}
                      className={`absolute top-1.5 right-1 p-1 rounded text-gray-400 hover:text-gray-700 hover:bg-gray-200/60
                        ${menuOpenId === s.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}
                      title="Chat options"
                    >
                      <span className="material-symbols-outlined text-[18px]">more_horiz</span>
                    </button>
                    {menuOpenId === s.id && (
                      <div className="absolute right-1 top-8 w-36 bg-white border border-gray-200 rounded-lg shadow-lg z-20 py-1 text-sm">
                        <button
                          onClick={() => beginRename(s)}
                          className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-gray-50 text-left text-gray-700"
                        >
                          <span className="material-symbols-outlined text-[16px] text-gray-500">edit</span>
                          Rename
                        </button>
                        <button
                          onClick={() => handleDelete(s)}
                          className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-red-50 text-left text-red-600"
                        >
                          <span className="material-symbols-outlined text-[16px]">delete</span>
                          Delete
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Main chat column ── */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSidebarOpen((v) => !v)}
              className="text-gray-500 hover:text-gray-700"
              title={sidebarOpen ? 'Hide history' : 'Show history'}
            >
              <span className="material-symbols-outlined">{sidebarOpen ? 'left_panel_close' : 'left_panel_open'}</span>
            </button>
            <span className="material-symbols-outlined text-primary">forum</span>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">MamlaAI Chat</h1>
              <p className="text-xs text-gray-500">Draft, research, verify citations & interrogate documents — in one thread.</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <button
                onClick={() => setConnectorsOpen((v) => !v)}
                className="flex items-center gap-1 text-sm border border-gray-300 rounded-lg px-2 py-1.5 bg-white hover:bg-gray-50"
                title="Connectors"
              >
                <span className="material-symbols-outlined text-[18px]">hub</span>
                Connectors
              </button>
              {connectorsOpen && (
                <div className="absolute right-0 mt-1 w-56 bg-white border border-gray-200 rounded-lg shadow-lg z-10 py-1 text-sm">
                  <button
                    onClick={() => { setConnectorsOpen(false); fileInputRef.current?.click(); }}
                    className="w-full flex items-center gap-2 px-3 py-2 hover:bg-gray-50 text-left"
                  >
                    <span className="material-symbols-outlined text-[18px] text-gray-500">upload_file</span>
                    Upload from device
                  </button>
                  <div className="w-full flex items-center gap-2 px-3 py-2 text-gray-400 cursor-not-allowed">
                    <span className="material-symbols-outlined text-[18px]">add_to_drive</span>
                    Google Drive
                    <span className="ml-auto text-[10px] uppercase tracking-wide">soon</span>
                  </div>
                </div>
              )}
            </div>
            <select
              value={modelLevel}
              onChange={(e) => setModelLevel(e.target.value)}
              className="text-sm border border-gray-300 rounded-lg px-2 py-1.5 bg-white"
              title="Model strength"
            >
              {MODEL_LEVELS.map((m) => (
                <option key={m.value} value={m.value}>{m.label} · {m.hint}</option>
              ))}
            </select>
            <div className="relative">
              <label className="flex items-center gap-1.5 text-sm text-gray-700 cursor-pointer">
                <input type="checkbox" checked={premium} onChange={(e) => setPremium(e.target.checked)} />
                Premium
                <button
                  onClick={(e) => { e.preventDefault(); setPremiumInfoOpen((v) => !v); }}
                  className="text-gray-400 hover:text-gray-600"
                  title="What is Premium?"
                >
                  <span className="material-symbols-outlined text-[16px]">info</span>
                </button>
              </label>
              {premiumInfoOpen && (
                <div className="absolute right-0 mt-1 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-10 p-3 text-xs text-gray-600">
                  <div className="flex items-center gap-1 font-medium text-gray-900 mb-1">
                    <span className="material-symbols-outlined text-[16px] text-amber-500">workspace_premium</span>
                    Premium answers
                  </div>
                  <p>
                    Routes your message to <b>Claude Opus 4.8</b> — Anthropic's most capable model —
                    for the deepest legal reasoning.
                  </p>
                  <p className="mt-1">
                    Each premium message is metered against your <b>Case Companion quota / wallet credits</b>.
                    Standard messages use your regular chat quota.
                  </p>
                  <p className="mt-1 text-gray-400">Answers show a model badge so you always know what replied.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center text-gray-400">
              <span className="material-symbols-outlined text-5xl mb-3">gavel</span>
              <p className="max-w-md text-sm">
                Ask a legal question, draft a document, pull up a case, or interrogate an uploaded file.
                Everything stays in one conversation — and your chats are saved on the left.
              </p>
              <div className="mt-5 flex flex-wrap gap-2 justify-center max-w-lg">
                {SUGGESTIONS.map((sug) => (
                  <button
                    key={sug.text}
                    onClick={() => { setInput(sug.fill); }}
                    className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-white text-gray-600 text-xs px-3 py-1.5 hover:border-primary/40 hover:text-primary"
                  >
                    <span className="material-symbols-outlined text-[15px]">{sug.icon}</span>
                    {sug.text}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((msg, i) => <Message key={msg.id || i} msg={msg} />)}
          {sending && messages[messages.length - 1]?.content === '' && (
            <div className="flex justify-start mb-4">
              <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3">
                <span className="material-symbols-outlined animate-spin text-primary text-lg">progress_activity</span>
              </div>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="px-6 py-2 text-sm text-red-600 bg-red-50 border-t border-red-100">{error}</div>
        )}

        {/* Composer */}
        <div className="border-t border-gray-200 bg-white px-6 py-4">
          {docs.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-2">
              {docs.map((d) => (
                <span key={d.id} className="inline-flex items-center gap-1 rounded-full bg-gray-100 text-gray-600 text-xs px-2 py-1">
                  <span className="material-symbols-outlined text-[14px]">description</span>
                  {d.name}
                </span>
              ))}
            </div>
          )}
          <div className="flex items-end gap-3">
            <input ref={fileInputRef} type="file" className="hidden" onChange={handleUpload}
              accept=".pdf,.docx,.doc,.txt,.csv,.xlsx,.png,.jpg,.jpeg" />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="shrink-0 border border-gray-300 text-gray-600 rounded-xl px-3 py-3 disabled:opacity-40 hover:bg-gray-50"
              title="Attach a document"
            >
              <span className="material-symbols-outlined text-lg">
                {uploading ? 'progress_activity' : 'attach_file'}
              </span>
            </button>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              placeholder="Message Adalat…  (Enter to send, Shift+Enter for a new line)"
              className="flex-1 resize-none border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 max-h-40"
            />
            <button
              onClick={handleSend}
              disabled={sending || !input.trim()}
              className="shrink-0 bg-primary text-white rounded-xl px-4 py-3 disabled:opacity-40 flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-lg">send</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
