import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import apiClient from '../../services/api';
import { usePostHog } from '@posthog/react';

const TALKDOC_ACCEPT = '.pdf,.doc,.docx,.txt,.csv,.xlsx,.png,.jpg,.jpeg,.webp';

// ─── Small helpers ─────────────────────────────────────────────────────────────

function fmtTime(ts) {
  if (!ts) return '';
  try {
    return new Date(ts).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  } catch { return ''; }
}

// Strip the embedded JSON signal from the AI message so only prose is shown.
// Uses bracket-matching so casual {} usage in normal prose is never touched.
function stripJsonSignal(text) {
  if (!text) return '';
  // Remove code-fenced blocks first
  let cleaned = text.replace(/```json[\s\S]*?```/g, '').replace(/```[\s\S]*?```/g, '');
  // Find the first occurrence of the "ready" key that marks the signal block
  const readyIdx = cleaned.search(/"ready"\s*:/);
  if (readyIdx === -1) return cleaned.trim();
  // Walk backwards to find the opening brace of the JSON object
  let openBrace = readyIdx - 1;
  while (openBrace >= 0 && cleaned[openBrace] !== '{') openBrace--;
  if (openBrace < 0) return cleaned.trim();
  // Walk forward from the opening brace to find its matching closing brace
  let depth = 0;
  let closeBrace = openBrace;
  for (let i = openBrace; i < cleaned.length; i++) {
    if (cleaned[i] === '{') depth++;
    else if (cleaned[i] === '}') {
      depth--;
      if (depth === 0) { closeBrace = i; break; }
    }
  }
  return (cleaned.slice(0, openBrace) + cleaned.slice(closeBrace + 1)).trim();
}

// ─── Typing indicator ─────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex items-end gap-2 mb-4">
      <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
        <span className="material-symbols-outlined text-primary text-sm">smart_toy</span>
      </div>
      <div className="bg-white border border-primary/10 rounded-2xl rounded-bl-sm px-4 py-3 shadow-subtle">
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map(i => (
            <span
              key={i}
              className="w-1.5 h-1.5 bg-primary/40 rounded-full animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Draft Plan card ──────────────────────────────────────────────────────────
function DraftPlanCard({ draftPlan, onContinue, onGenerate, generating }) {
  const sections = draftPlan?.sections_plan || [];
  const keyFacts = draftPlan?.key_facts || {};
  const draftType = draftPlan?.draft_type || 'Legal Document';

  return (
    <div className="my-4 rounded-2xl border border-primary/20 bg-primary/5 p-4 shadow-subtle">
      <div className="flex items-start gap-2 mb-3">
        <span className="material-symbols-outlined text-primary text-lg mt-0.5">task_alt</span>
        <div>
          <p className="text-sm font-bold text-ink">Draft Plan Ready</p>
          <p className="text-xs text-graphite/70 mt-0.5">
            {draftType.charAt(0).toUpperCase() + draftType.slice(1)}
          </p>
        </div>
      </div>

      {sections.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-semibold text-graphite/70 uppercase tracking-wide mb-2">Sections</p>
          <div className="flex flex-wrap gap-1.5">
            {sections.map((s, i) => (
              <span key={i} className="px-2.5 py-1 rounded-full bg-white border border-primary/15 text-xs font-medium text-slate-700">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {Object.keys(keyFacts).length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-graphite/70 uppercase tracking-wide mb-2">Key Facts</p>
          <div className="space-y-1">
            {Object.entries(keyFacts).filter(([, v]) => v).map(([k, v]) => (
              <div key={k} className="flex items-start gap-2 text-xs">
                <span className="text-graphite/50 capitalize min-w-[100px]">{k.replace(/_/g, ' ')}:</span>
                <span className="text-ink font-medium">{String(v)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center gap-2">
        <button
          onClick={onGenerate}
          disabled={generating}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary text-ivory text-sm font-semibold hover:bg-primary/90 transition disabled:opacity-60 disabled:cursor-not-allowed shadow-sm"
        >
          {generating ? (
            <>
              <span className="material-symbols-outlined text-base animate-spin">progress_activity</span>
              Generating…
            </>
          ) : (
            <>
              <span className="material-symbols-outlined text-base">auto_awesome</span>
              Generate Draft
            </>
          )}
        </button>
        <button
          onClick={onContinue}
          className="px-4 py-2 rounded-xl border border-primary/15 text-sm font-medium text-slate-600 hover:bg-primary/5 transition"
        >
          Continue Conversation
        </button>
      </div>
    </div>
  );
}

// ─── Chat message ─────────────────────────────────────────────────────────────
function ChatMessage({ msg }) {
  const isUser = msg.role === 'user';
  const displayText = isUser ? msg.content : stripJsonSignal(msg.content);
  if (!displayText) return null;

  return (
    <div className={`flex items-end gap-2 mb-4 ${isUser ? 'flex-row-reverse' : ''}`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
          <span className="material-symbols-outlined text-primary text-sm">smart_toy</span>
        </div>
      )}
      <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
        <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? 'bg-primary text-ivory rounded-br-sm'
            : 'bg-white border border-primary/10 text-ink rounded-bl-sm shadow-subtle'
        }`}>
          {displayText}
        </div>
        {msg.ts && (
          <span className="text-[10px] text-slate-400 px-1">{fmtTime(msg.ts)}</span>
        )}
      </div>
    </div>
  );
}

// ─── Start screen ─────────────────────────────────────────────────────────────
function StartScreen({ onStart, loading }) {
  const [cases, setCases] = useState([]);
  const [selectedCaseId, setSelectedCaseId] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadedDocIds, setUploadedDocIds] = useState([]);
  const [uploadedFileNames, setUploadedFileNames] = useState([]);
  const [activeCard, setActiveCard] = useState(null); // 'case' | 'doc' | 'scratch'
  const fileRef = useRef(null);

  useEffect(() => {
    apiClient.get('cases/list/')
      .then(r => setCases(r.data?.cases || []))
      .catch(() => {});
  }, []);

  async function handleDocUpload(e) {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setUploading(true);
    try {
      const ids = [];
      for (const file of files) {
        const form = new FormData();
        form.append('file', file);
        const res = await apiClient.post('talkdoc/upload/', form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        const docId = res.data.doc_id || res.data.id;
        if (docId) ids.push(docId);
      }
      setUploadedDocIds(prev => [...prev, ...ids]);
      setUploadedFileNames(prev => [...prev, ...files.map(f => f.name)]);
    } catch (err) {
      console.error('Upload failed', err);
    }
    setUploading(false);
  }

  return (
    <div className="flex flex-1 items-start justify-center overflow-y-auto p-8 bg-[radial-gradient(circle_at_top_left,_rgba(180,94,8,0.06),_transparent_32%)]">
      <div className="w-full max-w-2xl">
        <div className="mb-8">
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-4">
            <span>Documents</span>
            <span className="material-symbols-outlined text-xs">chevron_right</span>
            <span>AI Drafting</span>
            <span className="material-symbols-outlined text-xs">chevron_right</span>
            <span className="font-medium text-ink">Guided Draft</span>
          </div>
          <h1 className="text-2xl font-black text-ink mb-2">Guided Legal Drafting</h1>
          <p className="text-slate-500 text-sm">
            Our AI will ask you the right questions one by one to build a complete, high-quality legal draft.
          </p>
        </div>

        <div className="space-y-4">
          {/* Card: Start with a Case */}
          <div
            className={`rounded-2xl border-2 transition-all cursor-pointer ${
              activeCard === 'case' ? 'border-primary bg-primary/5' : 'border-primary/10 bg-white hover:border-primary/30'
            }`}
            onClick={() => setActiveCard('case')}
          >
            <div className="p-5">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <span className="material-symbols-outlined text-primary">folder_open</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-bold text-ink">Start with a Case</p>
                  <p className="text-xs text-graphite/60 mt-1">AI pre-fills context from your case file — you skip those questions.</p>
                </div>
              </div>

              {activeCard === 'case' && (
                <div className="mt-4 space-y-3">
                  <select
                    value={selectedCaseId}
                    onChange={e => setSelectedCaseId(e.target.value)}
                    className="w-full rounded-xl border border-primary/15 bg-white px-3 py-2.5 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="">Select a case…</option>
                    {cases.map(c => (
                      <option key={c._id} value={c._id}>
                        {c.title || c.case_title || c._id}
                      </option>
                    ))}
                  </select>
                  <button
                    disabled={!selectedCaseId || loading}
                    onClick={() => onStart({ case_id: selectedCaseId })}
                    className="w-full py-2.5 rounded-xl bg-primary text-ivory text-sm font-semibold hover:bg-primary/90 transition disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Starting…' : 'Start with this Case'}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Card: Start with Documents */}
          <div
            className={`rounded-2xl border-2 transition-all cursor-pointer ${
              activeCard === 'doc' ? 'border-primary bg-primary/5' : 'border-primary/10 bg-white hover:border-primary/30'
            }`}
            onClick={() => setActiveCard('doc')}
          >
            <div className="p-5">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <span className="material-symbols-outlined text-primary">attach_file</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-bold text-ink">Start with Documents</p>
                  <p className="text-xs text-graphite/60 mt-1">Upload any related documents — AI extracts facts from them automatically.</p>
                </div>
              </div>

              {activeCard === 'doc' && (
                <div className="mt-4 space-y-3">
                  <label className="flex items-center justify-center gap-2 w-full py-8 rounded-xl border-2 border-dashed border-primary/20 bg-primary/5 cursor-pointer hover:bg-primary/10 transition text-sm font-medium text-slate-600">
                    <input
                      ref={fileRef}
                      type="file"
                      multiple
                      accept={TALKDOC_ACCEPT}
                      onChange={handleDocUpload}
                      className="hidden"
                    />
                    {uploading ? (
                      <>
                        <span className="material-symbols-outlined text-base animate-spin">progress_activity</span>
                        Uploading…
                      </>
                    ) : (
                      <>
                        <span className="material-symbols-outlined text-base">upload</span>
                        {uploadedFileNames.length ? `${uploadedFileNames.length} file(s) uploaded — Add more` : 'Click to upload documents'}
                      </>
                    )}
                  </label>
                  {uploadedFileNames.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {uploadedFileNames.map((name, i) => (
                        <span key={i} className="px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-xs font-medium text-emerald-700">
                          {name}
                        </span>
                      ))}
                    </div>
                  )}
                  <button
                    disabled={uploadedDocIds.length === 0 || loading}
                    onClick={() => onStart({ document_ids: uploadedDocIds })}
                    className="w-full py-2.5 rounded-xl bg-primary text-ivory text-sm font-semibold hover:bg-primary/90 transition disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Starting…' : 'Start with these Documents'}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Card: Start from Scratch */}
          <div
            className={`rounded-2xl border-2 transition-all ${
              activeCard === 'scratch' ? 'border-primary bg-primary/5' : 'border-primary/10 bg-white hover:border-primary/30'
            }`}
          >
            <div className="p-5 flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
                <span className="material-symbols-outlined text-primary">edit_note</span>
              </div>
              <div className="flex-1">
                <p className="text-sm font-bold text-ink">Start from Scratch</p>
                <p className="text-xs text-graphite/60 mt-1">Tell AI what kind of document you need — it will guide you step by step.</p>
                <button
                  disabled={loading}
                  onClick={() => { setActiveCard('scratch'); onStart({}); }}
                  className="mt-3 px-4 py-2 rounded-xl bg-primary text-ivory text-sm font-semibold hover:bg-primary/90 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Starting…' : 'Start Conversation'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function GuidedDraftingPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const posthog = usePostHog();

  const [phase, setPhase] = useState('start'); // 'start' | 'chat' | 'generating'
  const [convId, setConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [ready, setReady] = useState(false);
  const [draftPlan, setDraftPlan] = useState(null);
  const [loading, setLoading] = useState(false);      // start / message / generate in flight
  const [typing, setTyping] = useState(false);         // AI typing indicator
  const [input, setInput] = useState('');
  const [error, setError] = useState('');
  const [generating, setGenerating] = useState(false);
  const [turnCount, setTurnCount] = useState(0);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const midChatFileRef = useRef(null);
  const [midDocUploading, setMidDocUploading] = useState(false);

  // Scroll to bottom whenever messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, typing]);

  // Auto-start if ?case_id= present in URL
  useEffect(() => {
    const caseId = searchParams.get('case_id');
    if (caseId && phase === 'start') {
      handleStart({ case_id: caseId });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleStart = useCallback(async (opts = {}) => {
    setLoading(true);
    setError('');
    try {
      const body = {};
      if (opts.case_id) body.case_id = opts.case_id;
      if (opts.document_ids?.length) body.document_ids = opts.document_ids;

      const res = await apiClient.post('aidrafts/guide/start/', body);
      const { conv_id, message } = res.data;

      setConvId(conv_id);
      setMessages([{ role: 'assistant', content: message, ts: new Date().toISOString() }]);
      posthog?.capture('guided_draft_started', { has_case: !!opts.case_id });
      setPhase('chat');
      setTurnCount(1);
      setTimeout(() => inputRef.current?.focus(), 100);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to start guided drafting. Please try again.');
    }
    setLoading(false);
  }, []);

  async function handleSendMessage(e) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || typing) return;

    const userMsg = { role: 'user', content: text, ts: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setTyping(true);
    setError('');

    try {
      const res = await apiClient.post('aidrafts/guide/message/', { conv_id: convId, message: text });
      const { reply, ready: isReady, draft_plan } = res.data;

      const aiMsg = { role: 'assistant', content: reply, ts: new Date().toISOString() };
      setMessages(prev => [...prev, aiMsg]);
      setTurnCount(prev => prev + 1);

      if (isReady) {
        setReady(true);
        setDraftPlan(draft_plan);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'AI is temporarily unavailable. Please try again.');
    }
    setTyping(false);
  }

  async function handleMidDocUpload(e) {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setMidDocUploading(true);
    try {
      const uploadedIds = [];
      for (const file of files) {
        const form = new FormData();
        form.append('file', file);
        const uploadRes = await apiClient.post('talkdoc/upload/', form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        const docId = uploadRes.data?.doc_id || uploadRes.data?.id;
        if (docId) uploadedIds.push(docId);
      }
      if (!uploadedIds.length) throw new Error('No document IDs returned');

      setTyping(true);
      const res = await apiClient.post('aidrafts/guide/upload_doc/', { conv_id: convId, document_ids: uploadedIds });
      const aiMsg = { role: 'assistant', content: res.data.reply, ts: new Date().toISOString() };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err) {
      setError(err.response?.data?.error || 'Document upload failed. Please try again.');
    }
    setMidDocUploading(false);
    setTyping(false);
    // reset file input
    if (midChatFileRef.current) midChatFileRef.current.value = '';
  }

  async function handleGenerate() {
    setGenerating(true);
    setError('');
    try {
      const res = await apiClient.post('aidrafts/guide/generate/', { conv_id: convId });
      navigate(`/drafting/${res.data.session_id}`);
    } catch (err) {
      setError(err.response?.data?.error || 'Draft generation failed. Please try again.');
      setGenerating(false);
    }
  }

  function handleContinueConversation() {
    setReady(false);
    setDraftPlan(null);
    setTimeout(() => inputRef.current?.focus(), 100);
  }

  // ── Render: start screen ────────────────────────────────────────────────────
  if (phase === 'start') {
    return (
      <div className="flex flex-col h-full">
        {error && (
          <div className="px-6 pt-4">
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 flex items-center gap-2">
              <span className="material-symbols-outlined text-base">error</span>
              {error}
            </div>
          </div>
        )}
        <StartScreen onStart={handleStart} loading={loading} />
      </div>
    );
  }

  // ── Render: chat pane ───────────────────────────────────────────────────────
  const nearCap = turnCount >= 8;

  return (
    <div className="flex flex-col h-full bg-[radial-gradient(circle_at_top_right,_rgba(180,94,8,0.05),_transparent_40%)]">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-primary/10 bg-ivory/90 backdrop-blur-sm flex-shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => { navigate('/drafting'); }}
            className="p-1.5 rounded-lg text-slate-500 hover:bg-primary/5 hover:text-primary transition"
          >
            <span className="material-symbols-outlined text-lg">arrow_back</span>
          </button>
          <div>
            <div className="flex items-center gap-2">
              <p className="text-sm font-bold text-ink">Guided Legal Draft</p>
              <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-[10px] font-semibold uppercase tracking-wide">
                Recommended
              </span>
            </div>
            <p className="text-xs text-graphite/60">AI gathers requirements one question at a time</p>
          </div>
        </div>
        {nearCap && (
          <span className="text-xs text-amber-600 font-medium border border-amber-200 bg-amber-50 rounded-full px-3 py-1">
            Almost done — {10 - turnCount} turn{10 - turnCount === 1 ? '' : 's'} left
          </span>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="px-5 pt-3 flex-shrink-0">
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 flex items-center gap-2">
            <span className="material-symbols-outlined text-base">error</span>
            {error}
            <button onClick={() => setError('')} className="ml-auto text-red-400 hover:text-red-600">
              <span className="material-symbols-outlined text-sm">close</span>
            </button>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-5 custom-scrollbar">
        <div className="max-w-2xl mx-auto">
          {messages.filter(m => m.role !== 'system').map((msg, i) => (
            <ChatMessage key={i} msg={msg} />
          ))}

          {/* Draft Plan card (shown after ready signal, below the last AI message) */}
          {ready && draftPlan && !generating && (
            <DraftPlanCard
              draftPlan={draftPlan}
              onContinue={handleContinueConversation}
              onGenerate={handleGenerate}
              generating={generating}
            />
          )}

          {/* Generating state */}
          {generating && (
            <div className="flex items-center justify-center gap-3 py-8 text-sm text-primary font-medium">
              <span className="material-symbols-outlined text-lg animate-spin">progress_activity</span>
              Generating your draft — this may take a moment…
            </div>
          )}

          {typing && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input bar */}
      <div className="flex-shrink-0 border-t border-primary/10 bg-ivory/90 backdrop-blur-sm px-5 py-4">
        <div className="max-w-2xl mx-auto">
          {ready && !generating && (
            <div className="flex items-center gap-2 mb-3 text-xs text-graphite/60 bg-primary/5 border border-primary/15 rounded-xl px-3 py-2">
              <span className="material-symbols-outlined text-sm text-primary">info</span>
              Draft plan is ready. Click <strong className="text-primary">Generate Draft</strong> above or keep chatting to refine.
            </div>
          )}
          <form onSubmit={handleSendMessage} className="flex items-end gap-2">
            {/* Attach document button */}
            <label className={`p-2.5 rounded-xl border border-primary/15 text-slate-500 hover:text-primary hover:bg-primary/5 transition cursor-pointer flex-shrink-0 ${midDocUploading ? 'opacity-50 pointer-events-none' : ''}`}
              title="Attach document">
              <input
                ref={midChatFileRef}
                type="file"
                multiple
                accept={TALKDOC_ACCEPT}
                onChange={handleMidDocUpload}
                className="hidden"
              />
              {midDocUploading
                ? <span className="material-symbols-outlined text-lg animate-spin">progress_activity</span>
                : <span className="material-symbols-outlined text-lg">attach_file</span>
              }
            </label>

            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder="Type your answer… (Enter to send, Shift+Enter for new line)"
              rows={1}
              disabled={typing || generating}
              className="flex-1 resize-none rounded-xl border border-primary/15 bg-white px-4 py-3 text-sm text-ink placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-60 disabled:cursor-not-allowed"
              style={{ minHeight: '44px', maxHeight: '120px' }}
              onInput={e => {
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
              }}
            />

            <button
              type="submit"
              disabled={!input.trim() || typing || generating}
              className="p-2.5 rounded-xl bg-primary text-ivory hover:bg-primary/90 transition disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0 shadow-sm"
            >
              <span className="material-symbols-outlined text-lg">send</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
