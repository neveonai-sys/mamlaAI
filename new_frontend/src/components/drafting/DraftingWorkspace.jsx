import React, { useState, useEffect, useRef, useMemo } from 'react';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import { useParams, useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import apiClient from '../../services/api';
import { usePostHog } from '@posthog/react';
import { getCase } from '../../services/casesApi';
import DOMPurify from 'dompurify';
import { refreshEntitlements } from '../../features/entitlementsActions';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import { saveAndShare } from '../../utils/nativeFileUtils';

function buildQuotaNotice(quota, fallbackMessage = '') {
  if (!quota) return null;

  const remaining = typeof quota.remaining_included === 'number' ? quota.remaining_included : null;
  const walletBalance = typeof quota.wallet_credits_balance === 'number' ? quota.wallet_credits_balance : 0;
  const walletCharged = typeof quota.wallet_credits_charged === 'number' ? quota.wallet_credits_charged : 0;

  if (quota.allowed === false) {
    if (quota.next_cta === 'top_up_credits') {
      return {
        tone: 'error',
        message: fallbackMessage || 'This draft has exhausted its included AI suggestions. Add wallet credits to continue.',
      };
    }
    return {
      tone: 'error',
      message: fallbackMessage || 'This draft cannot use more AI suggestions right now.',
    };
  }

  if (walletCharged > 0) {
    return {
      tone: 'info',
      message: `${walletCharged} wallet credit${walletCharged === 1 ? '' : 's'} used for this suggestion. ${walletBalance} credit${walletBalance === 1 ? '' : 's'} remaining.`,
    };
  }

  if (remaining !== null && remaining <= 2) {
    return {
      tone: 'warning',
      message: `${remaining} included AI suggestion${remaining === 1 ? '' : 's'} left on this draft before credit usage starts.`,
    };
  }

  return null;
}

// Conversation entries from the backend have no stable id — assign one from their
// index (entries are only ever appended, never reordered/removed, so this is stable).
function withConversationIds(entries) {
  return (entries ?? []).map((entry, index) => ({ ...entry, id: index }));
}

function quotaNoticeClassName(tone) {
  if (tone === 'error') return 'border-red-200 bg-red-50 text-red-700';
  if (tone === 'warning') return 'border-amber-200 bg-amber-50 text-amber-800';
  return 'border-sky-200 bg-sky-50 text-sky-700';
}

// ─── Inline formatting toolbar — compact, lives inside the sections-meta row ──
function EditorToolbar() {
  const [moreOpen, setMoreOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!moreOpen) return undefined;
    function handler(e) {
      if (ref.current && !ref.current.contains(e.target)) setMoreOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [moreOpen]);

  function exec(cmd, value) {
    document.execCommand(cmd, false, value);
  }

  const moreOptions = [
    { cmd: 'underline', icon: 'format_underlined', label: 'Underline' },
    { cmd: 'insertUnorderedList', icon: 'format_list_bulleted', label: 'Bulleted list' },
    { cmd: 'justifyLeft', icon: 'format_align_left', label: 'Align left' },
    { cmd: 'justifyCenter', icon: 'format_align_center', label: 'Align center' },
  ];

  return (
    <div className="flex items-center gap-1 bg-white border border-primary/10 rounded-lg p-1 shadow-sm flex-shrink-0">
      {[
        { cmd: 'bold', icon: 'format_bold' },
        { cmd: 'italic', icon: 'format_italic' },
      ].map((b) => (
        <button
          key={b.cmd}
          onMouseDown={(e) => { e.preventDefault(); exec(b.cmd); }}
          className="p-1.5 hover:bg-primary/5 rounded text-slate-600 hover:text-primary transition-colors"
        >
          <span className="material-symbols-outlined text-lg">{b.icon}</span>
        </button>
      ))}
      <div className="w-px h-4 bg-primary/10 mx-1" />
      <div ref={ref} className="relative">
        <button
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => setMoreOpen((current) => !current)}
          className={`p-1.5 rounded transition-colors flex items-center gap-0.5 ${moreOpen ? 'bg-primary/5 text-primary' : 'text-slate-600 hover:bg-primary/5 hover:text-primary'}`}
        >
          <span className="material-symbols-outlined text-lg">more_horiz</span>
        </button>
        {moreOpen && (
          <div className="app-fade-in absolute left-0 top-[calc(100%+6px)] z-20 flex items-center gap-1 rounded-lg border border-primary/10 bg-white p-1 shadow-lg">
            {moreOptions.map((b) => (
              <button
                key={b.cmd}
                title={b.label}
                onMouseDown={(e) => { e.preventDefault(); exec(b.cmd); }}
                className="p-1.5 hover:bg-primary/5 rounded text-slate-600 hover:text-primary transition-colors"
              >
                <span className="material-symbols-outlined text-lg">{b.icon}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Left sidebar with doc outline ───────────────────────────────────────────
function DraftSidebar({ sections, activeSectionIdx, onSelectSection }) {
  return (
    <aside className="w-60 flex flex-col border-r border-primary/10 bg-ivory flex-shrink-0 xl:w-64">
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto custom-scrollbar">
        <div className="pt-2 pb-2 px-3">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Document Outline</p>
        </div>
        {sections.length > 0 ? (
          sections.map((sec, i) => (
            <button
              key={i}
              onClick={() => onSelectSection(i)}
              className={`w-full text-left px-3 py-1.5 text-xs rounded transition-colors border-l-2 ${
                activeSectionIdx === i
                  ? 'text-ink font-bold border-primary'
                  : 'text-slate-500 hover:text-ink border-transparent'
              }`}
            >
              {sec.section_name || sec.section_title || sec.title || `Section ${i + 1}`}
            </button>
          ))
        ) : (
          <p className="text-xs text-slate-400 px-3 py-2 italic">No outline yet</p>
        )}
      </nav>
    </aside>
  );
}

// ─── AI assistant right panel ─────────────────────────────────────────────────
function AIPanel({ onPrompt, loading, messages, quotaNotice, promptDisabled, sections, activeSectionIdx, onSectionChange, onClose, width, onWidthChange, appliedSuggestionIds, onApplySuggestion }) {
  const [input, setInput] = useState('');
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  function handleSend() {
    if (!input.trim() || loading || promptDisabled) return;
    onPrompt(input.trim());
    setInput('');
  }

  function handleResizeStart(e) {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = width;
    function onMouseMove(moveEvent) {
      const delta = startX - moveEvent.clientX;
      const next = Math.min(640, Math.max(320, startWidth + delta));
      onWidthChange(next);
    }
    function onMouseUp() {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    }
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }

  const SUGGESTIONS = [
    'Refine this clause for compliance',
    'Generate an executive summary',
    'Add indemnification clause',
    'Check for ambiguous language',
  ];

  const activeSectionName = sections?.[activeSectionIdx]?.section_name
    || sections?.[activeSectionIdx]?.section_title
    || (sections?.length > 0 ? `Section ${activeSectionIdx + 1}` : null);

  return (
    <aside className="relative flex flex-col border-l border-primary/10 bg-ivory flex-shrink-0" style={{ width }}>
      <div
        onMouseDown={handleResizeStart}
        className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-primary/20 active:bg-primary/30 transition-colors z-10"
        title="Drag to resize"
      />
      <div className="p-4 border-b border-primary/10 flex items-center justify-between flex-shrink-0">
        <h3 className="font-bold text-sm flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-xl">auto_awesome</span>
          AI Assistant
        </h3>
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-slate-400 hover:bg-primary/5 hover:text-primary transition-colors"
          title="Close AI Assistant"
        >
          <span className="material-symbols-outlined text-lg">close</span>
        </button>
      </div>

      {/* Section target selector */}
      {sections && sections.length > 0 && (
        <div className="mx-4 mt-3 flex-shrink-0">
          <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">
            Refining section
          </label>
          <select
            value={activeSectionIdx}
            onChange={(e) => onSectionChange(Number(e.target.value))}
            disabled={promptDisabled || loading}
            className="w-full rounded-lg border border-primary/20 bg-white px-3 py-1.5 text-xs font-medium text-ink focus:outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {sections.map((sec, i) => (
              <option key={sec.section_id || i} value={i}>
                {sec.section_name || sec.section_title || `Section ${i + 1}`}
              </option>
            ))}
          </select>
          {activeSectionName && (
            <p className="text-[10px] text-slate-400 mt-1">
              All AI suggestions will update <span className="font-semibold text-primary">{activeSectionName}</span>. Switch sections above before sending.
            </p>
          )}
        </div>
      )}

      {quotaNotice && (
        <div className={`mx-4 mt-4 rounded-xl border px-3 py-2 text-xs font-medium ${quotaNoticeClassName(quotaNotice.tone)}`}>
          {quotaNotice.message}
        </div>
      )}

      {/* Conversation */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
        {messages.length === 0 && (
          <div className="bg-white border border-primary/10 rounded-xl p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-3">
              <span className="material-symbols-outlined text-primary text-lg">lightbulb</span>
              <span className="text-xs font-bold text-ink uppercase tracking-wider">Suggested Actions</span>
            </div>
            <div className="grid grid-cols-1 gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => onPrompt(s)}
                  disabled={promptDisabled || loading}
                  className="flex items-center justify-between px-3 py-2 text-xs font-medium bg-primary/5 text-primary rounded-lg border border-primary/10 hover:bg-primary/10 transition-colors text-left"
                >
                  {s}
                  <span className="material-symbols-outlined text-sm flex-shrink-0">chevron_right</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => {
          const isApplied = msg.role === 'assistant' && appliedSuggestionIds?.has(msg.id);
          return (
            <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-primary text-ivory rounded-br-sm'
                    : 'bg-white border border-primary/10 text-ink rounded-bl-sm'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
              {msg.role === 'assistant' && msg.id != null && !msg.isError && (
                isApplied ? (
                  <span className="mt-1.5 inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600">
                    <span className="material-symbols-outlined text-sm">check_circle</span>
                    Applied to draft
                  </span>
                ) : (
                  <button
                    onClick={() => onApplySuggestion(msg)}
                    className="mt-1.5 inline-flex items-center gap-1 rounded-lg bg-primary/10 px-2.5 py-1 text-[11px] font-semibold text-primary hover:bg-primary/20 transition-colors"
                  >
                    <span className="material-symbols-outlined text-sm">check</span>
                    Apply to draft
                  </button>
                )
              )}
            </div>
          );
        })}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-primary/10 rounded-2xl rounded-bl-sm px-4 py-3">
              <div className="flex gap-1 items-center">
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-primary/10 flex-shrink-0">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={promptDisabled ? 'AI suggestions are unavailable for this draft right now.' : 'Ask AI to refine, add clauses, check compliance…'}
            rows={2}
            className="flex-1 bg-primary/5 border border-primary/20 rounded-lg px-3 py-2 text-xs text-ink
                       placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/30
                       resize-none transition-all disabled:cursor-not-allowed disabled:opacity-60"
            disabled={promptDisabled}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim() || promptDisabled}
            className="flex-shrink-0 size-9 bg-primary text-ivory rounded-lg flex items-center justify-center
                       hover:bg-primary/90 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span className="material-symbols-outlined text-base">send</span>
          </button>
        </div>
        <p className="text-[10px] text-slate-400 mt-1.5 text-center">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </aside>
  );
}

function HistoryDialog({ open, items, onClose }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-ink/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-3xl max-h-[80vh] overflow-hidden rounded-2xl bg-white shadow-2xl border border-primary/10">
        <div className="flex items-center justify-between px-5 py-4 border-b border-primary/10">
          <div>
            <h3 className="font-bold text-ink">Section History</h3>
            <p className="text-xs text-slate-500 mt-1">Previous versions for the selected section</p>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-primary/5 rounded-lg transition-colors">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>
        <div className="p-5 overflow-y-auto custom-scrollbar max-h-[calc(80vh-74px)] space-y-4">
          {items.length === 0 ? (
            <div className="rounded-xl border border-dashed border-primary/20 bg-ivory px-4 py-8 text-center text-sm text-slate-500">
              No saved history for this section yet.
            </div>
          ) : (
            items.map((item, index) => (
              <div key={index} className="rounded-xl border border-primary/10 bg-ivory/40 p-4">
                <div className="flex items-center justify-between gap-3 mb-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Version {items.length - index}</p>
                  <p className="text-xs text-slate-400">
                    {item.updated_on || item.created_on ? new Date(item.updated_on || item.created_on).toLocaleString('en-IN') : 'Timestamp unavailable'}
                  </p>
                </div>
                <div className="prose prose-sm max-w-none text-slate-700 whitespace-pre-wrap break-words">
                  {item.content || item.section_content || item.previous_content || item.updated_content || 'No content recorded'}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function ConfirmLeaveDialog({ open, onConfirm, onCancel }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-ink/30 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative w-full max-w-md rounded-2xl bg-white shadow-2xl border border-primary/10 p-6">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-50 text-amber-600">
            <span className="material-symbols-outlined">warning</span>
          </div>
          <div>
            <h3 className="text-lg font-bold text-ink">Leave this draft?</h3>
            <p className="mt-1 text-sm text-slate-500">Go back to the documents view only after saving the changes you want to keep.</p>
          </div>
        </div>
        <div className="mt-6 flex items-center justify-end gap-3">
          <button type="button" className="btn-ghost text-sm" onClick={onCancel}>Stay Here</button>
          <button type="button" className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-ivory hover:bg-primary/90" onClick={onConfirm}>
            Leave Draft
          </button>
        </div>
      </div>
    </div>
  );
}

function DraftForSelector({ rows, selectedIds, onToggle, onToggleAll, onAddCustom, disabled }) {
  if (disabled) return null;
  const allSelected = rows.length > 0 && selectedIds.length === rows.length;
  const partiallySelected = selectedIds.length > 0 && selectedIds.length < rows.length;

  return (
    <div>
      <div className="flex items-center justify-between mb-3 gap-3">
        <label className="block text-sm font-semibold text-slate-700">Draft For</label>
        <button type="button" className="btn-ghost text-xs" onClick={onAddCustom}>Add Entry</button>
      </div>
      <div className="rounded-xl border border-primary/10 overflow-hidden bg-white">
        <div className="grid grid-cols-[44px_1fr_1fr_1fr] gap-0 border-b border-primary/10 bg-ivory/70 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
          <label className="flex items-center justify-center py-3">
            <input
              type="checkbox"
              checked={allSelected}
              ref={(node) => {
                if (node) node.indeterminate = partiallySelected;
              }}
              onChange={(e) => onToggleAll(e.target.checked)}
            />
          </label>
          <div className="py-3 px-3">Case ID</div>
          <div className="py-3 px-3">Title</div>
          <div className="py-3 px-3">Client Name</div>
        </div>
        <div className="max-h-64 overflow-y-auto custom-scrollbar divide-y divide-primary/10">
          {rows.map((row) => (
            <label key={row.id} className="grid grid-cols-[44px_1fr_1fr_1fr] gap-0 items-center px-0 py-0 hover:bg-primary/5 cursor-pointer">
              <span className="flex items-center justify-center py-3">
                <input
                  type="checkbox"
                  checked={selectedIds.includes(row.id)}
                  onChange={(e) => onToggle(row.id, e.target.checked)}
                />
              </span>
              <span className="py-3 px-3 text-sm text-slate-700">{row.case_id || '-'}</span>
              <span className="py-3 px-3 text-sm text-slate-700">{row.case_title || '-'}</span>
              <span className="py-3 px-3 text-sm text-slate-700">{row.client_name || '-'}</span>
            </label>
          ))}
          {rows.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-slate-400">No case/client entries available.</div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main DraftingWorkspace ───────────────────────────────────────────────────
export default function DraftingWorkspace() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const dispatch = useDispatch();
  const posthog = usePostHog();
  const { user_type } = useSelector((s) => s.user);
  const { trial, wallet, features } = useSelector((s) => s.entitlements);

  // ── State ──
  const [phase, setPhase] = useState('init'); // 'init' | 'editing'
  const [sessionId, setSessionId] = useState(id || null);
  const [sections, setSections] = useState([]);
  const [activeSectionIdx, setActiveSectionIdx] = useState(0);
  const [savedDrafts, setSavedDrafts] = useState([]);

  // Pre-fill context from DraftContextAgent (passed via router state)
  const [caseContext, setCaseContext] = useState(null);
  const [filterData, setFilterData] = useState(null);
  // Full AI conversation log for this draft (all sections), persisted server-side
  // in `conversation_history` — restored on load so users can see past AI-assisted changes.
  const [conversationHistory, setConversationHistory] = useState([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [draftTitle, setDraftTitle] = useState(() => buildTimestampedDraftName());
  const [saveStatus, setSaveStatus] = useState(''); // 'saving' | 'saved' | 'error'
  const [savingDraft, setSavingDraft] = useState(false);
  const [draftForData, setDraftForData] = useState([]);
  const [aiSuggestionCount, setAiSuggestionCount] = useState(0);
  const [suggestionQuota, setSuggestionQuota] = useState(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [sectionHistory, setSectionHistory] = useState([]);
  const [currentSavedDraftId, setCurrentSavedDraftId] = useState(null);
  const [lastSavedAt, setLastSavedAt] = useState('');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [leaveDialogOpen, setLeaveDialogOpen] = useState(false);
  const [showOutlinePanel] = useState(false);
  const [showAiPanel, setShowAiPanel] = useState(false);
  const [aiPanelWidth, setAiPanelWidth] = useState(340);
  const [appliedSuggestionIds, setAppliedSuggestionIds] = useState(() => new Set());
  const [headerHidden, setHeaderHidden] = useState(false);
  const lastScrollTopRef = useRef(0);

  function handleEditorScroll(e) {
    const top = e.currentTarget.scrollTop;
    const last = lastScrollTopRef.current;
    if (top <= 8) {
      setHeaderHidden(false);
    } else if (top > last + 4) {
      setHeaderHidden(true);
    } else if (top < last - 4) {
      setHeaderHidden(false);
    }
    lastScrollTopRef.current = top;
  }

  // Init form state
  const [query, setQuery] = useState('');
  const [sourceFile, setSourceFile] = useState(null);
  const [selectedDocType, setSelectedDocType] = useState('');
  const [initLoading, setInitLoading] = useState(false);
  const [error, setError] = useState('');

  // Init tabs: 0 = New Draft, 1 = Load Draft (Load Template tab retired, kept dormant below)
  const [initTab, setInitTab] = useState(0);
  const [draftSearch, setDraftSearch] = useState('');

  // Template tab state
  const [templateTypes, setTemplateTypes] = useState([]);
  const [templateNames, setTemplateNames] = useState([]);
  const [selectedTemplateType, setSelectedTemplateType] = useState('');
  const [selectedTemplateName, setSelectedTemplateName] = useState('');
  const [templateSource, setTemplateSource] = useState('existing'); // 'existing' | 'upload'
  const [templateFile, setTemplateFile] = useState(null);
  const [templateLoading, setTemplateLoading] = useState(false);
  const [draftPage, setDraftPage] = useState(0);
  const [draftPageSize, setDraftPageSize] = useState(10);
  const [draftTotalCount, setDraftTotalCount] = useState(0);
  const [draftSearchField, setDraftSearchField] = useState('draft_name');

  // Intake fields: case/client, location, language
  const [isPersonal, setIsPersonal] = useState(false);
  const [selectedCaseId, setSelectedCaseId] = useState('');
  const [selectedClientId, setSelectedClientId] = useState('');
  const [selectedState, setSelectedState] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [selectedCourt, setSelectedCourt] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState('English');

  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [courts, setCourts] = useState([]);
  const [languages, setLanguages] = useState([]);
  const [draftForRows, setDraftForRows] = useState([]);
  const [selectedDraftForIds, setSelectedDraftForIds] = useState([]);

  const isClientUser = user_type === 'Client';
  const remainingSuggestionCount = Math.max(0, 7 - aiSuggestionCount);
  const draftingQuota = features?.brain_drafting_actions;
  const suggestionQuotaNotice = buildQuotaNotice(suggestionQuota, error);
  const suggestionPromptDisabled = suggestionQuota?.allowed === false;

  // AI Assistant conversation scoped to the section currently being refined —
  // derived from the persisted conversation_history so switching sections shows that
  // section's own history, and re-opening a draft restores prior AI-assisted turns.
  const activeSectionAiId = sections[activeSectionIdx]?.section_id;
  const aiMessages = useMemo(
    () => conversationHistory
      .filter((entry) => entry.section_id === activeSectionAiId)
      .map((entry) => ({ id: entry.id, role: entry.role, content: entry.content, section_id: entry.section_id, isError: entry.isError })),
    [conversationHistory, activeSectionAiId],
  );

  // Send-to-client modal state
  const [showSendModal, setShowSendModal] = useState(false);
  const [sendToEmails, setSendToEmails] = useState('');
  const [sendCcEmails, setSendCcEmails] = useState('');
  const [sendNote, setSendNote] = useState('');
  const [sendLoading, setSendLoading] = useState(false);
  const [sendFormat, setSendFormat] = useState('docx');
  const [sendResult, setSendResult] = useState(null); // { ok: bool, message: str }

  function normalizeDraftForEntries(draftFor) {
    if (!draftFor) return [];
    if (Array.isArray(draftFor)) return draftFor;
    if (typeof draftFor === 'object' && Object.keys(draftFor).length > 0) return [draftFor];
    return [];
  }

  function getDraftForSummary(draftFor) {
    const entries = normalizeDraftForEntries(draftFor);
    return {
      clientNames: entries.map((item) => item.client_name || item.clientname || item.client_id || item.clientid).filter(Boolean).join(', '),
      caseIds: entries.map((item) => item.case_id || item.caseid).filter(Boolean).join(', '),
    };
  }

  function normalizeSavedDraftRows(rows) {
    return (rows || []).map((row) => ({
      ...row,
      id: row.id || row.draft_id,
      draft_id: row.draft_id || row.id,
      draft_name: row.draft_name || row.title || 'Untitled Draft',
      session_id: row.session_id,
      draft_for: row.draft_for || [],
      created_on: row.created_on || row.created_at || null,
      last_updated_on: row.last_updated_on || row.updated_at || null,
    }));
  }

  function buildTimestampedDraftName() {
    return `Draft ${new Date().toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })}`;
  }

  function formatSavedAt(value) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function syncCurrentSavedDraftMeta(draftId, savedAt) {
    setCurrentSavedDraftId(draftId || null);
    setLastSavedAt(savedAt || '');
  }

  function resolveDraftTitle(...candidates) {
    const picked = candidates.find((value) => typeof value === 'string' && value.trim());
    if (!picked) return buildTimestampedDraftName();
    const normalized = picked.trim();
    if (normalized.toLowerCase() === 'draft' || normalized.toLowerCase() === 'untitled draft') {
      return buildTimestampedDraftName();
    }
    return normalized;
  }

  function resetToDraftSelection() {
    setPhase('init');
    setSections([]);
    setSessionId(null);
    setCurrentSavedDraftId(null);
    setLastSavedAt('');
    setHasUnsavedChanges(false);
    setConversationHistory([]);
    setAppliedSuggestionIds(new Set());
    setDraftForData([]);
    setDraftTitle(buildTimestampedDraftName());
    setLeaveDialogOpen(false);
    navigate('/drafting');
  }

  function requestBackToSelection() {
    setLeaveDialogOpen(true);
  }

  function buildSelectedDraftFor() {
    return draftForRows
      .filter((row) => selectedDraftForIds.includes(row.id))
      .map((row) => ({ case_id: row.case_id || '', case_title: row.case_title || '', client_name: row.client_name || '', client_id: row.client_id || '' }));
  }

  function handleToggleDraftFor(id, checked) {
    setSelectedDraftForIds((current) => checked ? [...current, id] : current.filter((item) => item !== id));
  }

  function handleToggleAllDraftFor(checked) {
    setSelectedDraftForIds(checked ? draftForRows.map((row) => row.id) : []);
  }

  function handleAddDraftForRow() {
    const caseId = window.prompt('Case ID (optional)') || '';
    const clientName = window.prompt('Client name') || '';
    if (!caseId && !clientName) return;
    const clientId = window.prompt('Client ID (optional)') || '';
    const newRow = {
      id: `custom-${Date.now()}`,
      case_id: caseId.trim(),
      client_name: clientName.trim() || 'Unnamed',
      client_id: clientId.trim(),
    };
    setDraftForRows((current) => [...current, newRow]);
    setSelectedDraftForIds((current) => [...current, newRow.id]);
  }

  async function refreshSavedDrafts({ page = draftPage, pageSize = draftPageSize, searchField = draftSearchField, searchQuery = draftSearch } = {}) {
    try {
      const params = { page: page + 1, page_size: pageSize };
      if (searchQuery?.trim()) {
        params.search_field = searchField;
        params.search_query = searchQuery.trim();
      }
      const r = await apiClient.get('aidrafts/get_user_saved_drafts', { params });
      const rows = normalizeSavedDraftRows(r.data?.saved_drafts || r.data?.results || []);
      const total = r.data?.pagination?.total_count ?? r.data?.count ?? rows.length;
      setSavedDrafts(rows);
      setDraftTotalCount(total);
    } catch {
      try {
        const r2 = await apiClient.get('aidrafts/get_user_saved_drafts_v2');
        const allRows = normalizeSavedDraftRows(r2.data?.saved_drafts ?? []);
        const filtered = !searchQuery?.trim()
          ? allRows
          : allRows.filter((row) => {
              const summary = getDraftForSummary(row.draft_for);
              const q = searchQuery.toLowerCase();
              if (searchField === 'draft_name') return (row.draft_name || '').toLowerCase().includes(q);
              if (searchField === 'caseid') return summary.caseIds.toLowerCase().includes(q);
              if (searchField === 'clientid') return summary.clientNames.toLowerCase().includes(q);
              return (row.draft_name || '').toLowerCase().includes(q);
            });
        const start = page * pageSize;
        const nextRows = filtered.slice(start, start + pageSize);
        setSavedDrafts(nextRows);
        setDraftTotalCount(filtered.length);
      } catch {
        setSavedDrafts([]);
        setDraftTotalCount(0);
      }
    }
  }

  async function refreshDraftSections(targetSessionId = sessionId) {
    if (!targetSessionId) return null;
    const response = await apiClient.get('aidrafts/get_draft_sections', {
      params: { session_id: targetSessionId },
    });
    const nextSections = response.data?.draft_sections ?? [];
    setSections(nextSections);
    setAiSuggestionCount(response.data?.ai_suggested_update_count ?? 0);
    setConversationHistory(withConversationIds(response.data?.conversation_history));
    setAppliedSuggestionIds(new Set());
    setSuggestionQuota(null);
    return nextSections;
  }

  async function fetchDraftFor(targetSessionId = sessionId) {
    if (!targetSessionId) return;
    try {
      const response = await apiClient.get('aidrafts/get_draft_for', {
        params: { session_id: targetSessionId },
      });
      const draftFor = response.data?.draft_for || [];
      setDraftForData(Array.isArray(draftFor) ? draftFor : Object.values(draftFor));
    } catch {
      setDraftForData([]);
    }
  }

  // ── Load filter data + saved drafts ──
  useEffect(() => {
    apiClient.get('users/filter_with_details/').then((r) => setFilterData(r.data)).catch(() => {});
    refreshSavedDrafts();
    apiClient.get('users/get-states/').then((r) => {
      const raw = r.data?.states ?? r.data ?? [];
      // Normalise: old API returned plain strings, new returns [{state_code,name}]
      setStates(raw.map((s) => (typeof s === 'string' ? s : s.name)));
    }).catch(() => {});
    apiClient.get('aidrafts/get_supported_languages').then((r) => {
      setLanguages(r.data?.languages ?? r.data ?? []);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!filterData) return;
    const rows = [];
    const map = filterData.case_client_map || {};
    Object.entries(map).forEach(([caseId, client]) => {
      rows.push({
        id: caseId,
        case_id: caseId,
        case_title: client.case_title || '',
        client_id: client.client_id || client.phone_number || '',
        client_name: `${client.Fname || ''} ${client.Lname || ''}`.trim() || 'Unnamed',
      });
    });
    // clientIds_without_case rows removed — orphan clients no longer surfaced in UI
    (filterData.caseIds_without_client || []).forEach((entry) => {
      // entry is now {case_id, case_title} — defensive fallback for old string shape
      const caseId = entry?.case_id || entry;
      if (!caseId) return;
      rows.push({
        id: caseId,
        case_id: caseId,
        case_title: entry?.case_title || '',
        client_id: '',
        client_name: '(No client)',
      });
    });
    setDraftForRows(rows);
    if (!isClientUser) {
      setSelectedDraftForIds([]);
    }
  }, [filterData, isClientUser]);

  useEffect(() => {
    if (initTab !== 1) return;
    refreshSavedDrafts();
  }, [draftPage, draftPageSize, draftSearch, draftSearchField, initTab]);

  useEffect(() => {
    if (!hasUnsavedChanges) return undefined;
    const handleBeforeUnload = (event) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedChanges]);

  // Load districts when state changes
  useEffect(() => {
    if (!selectedState) { setDistricts([]); setSelectedDistrict(''); return; }
    apiClient.get(`users/get-districts/?state_code=${encodeURIComponent(selectedState)}`).then((r) => {
      const raw = r.data?.districts ?? r.data ?? [];
      // Normalise: old API returned plain strings, new returns [{dist_code,name}]
      setDistricts(raw.map((d) => (typeof d === 'string' ? d : d.name)));
      setSelectedDistrict('');
      setSelectedCourt('');
      setCourts([]);
    }).catch(() => {});
  }, [selectedState]);

  // Load courts when district changes
  useEffect(() => {
    if (!selectedState || !selectedDistrict) { setCourts([]); setSelectedCourt(''); return; }
    apiClient.get(`users/get-courts/?state=${encodeURIComponent(selectedState)}&district=${encodeURIComponent(selectedDistrict)}`).then((r) => {
      setCourts(r.data?.courts ?? r.data ?? []);
      setSelectedCourt('');
    }).catch(() => {});
  }, [selectedState, selectedDistrict]);

  // Fetch template types when Load Template tab is first opened
  useEffect(() => {
    if (initTab !== 2 || templateTypes.length > 0) return;
    apiClient.get('drafts/get-all-drafts/').then((r) => {
      setTemplateTypes(r.data?.dir_list ?? []);
    }).catch(() => {});
  }, [initTab]);

  // Fetch template names when a type is selected
  useEffect(() => {
    if (!selectedTemplateType) { setTemplateNames([]); setSelectedTemplateName(''); return; }
    apiClient.get('drafts/draft-items', { params: { type: selectedTemplateType } }).then((r) => {
      setTemplateNames(r.data?.all_drafts_list ?? []);
      setSelectedTemplateName('');
    }).catch(() => {});
  }, [selectedTemplateType]);

  // ── Consume DraftContextAgent prefill from router state ──
  useEffect(() => {
    const prefill = location.state?.prefill;
    if (!prefill || id) return; // don't override if loading existing draft
    setCaseContext(prefill);
    if (prefill.context_summary) setQuery(prefill.context_summary);
    if (prefill.draft_type) setSelectedDocType(prefill.draft_type);
    const loc = prefill.location || {};
    if (loc.state) setSelectedState(loc.state);
    if (loc.district) setSelectedDistrict(loc.district);
    if (loc.court) setSelectedCourt(loc.court);
    const caseId = prefill.draft_for?.case_id;
    if (caseId) setSelectedCaseId(caseId);
  }, [location.state, id]);

  // ── If opened via ?case_id= URL param, pre-set case and doc type ──
  useEffect(() => {
    const caseIdParam = searchParams.get('case_id');
    if (!caseIdParam || id || location.state?.prefill) return;
    const STAGE_TO_TYPE = {
      Filing: 'Petition / Plaint',
      Pleadings: 'Written Statement',
      Evidence: 'Affidavit',
      Arguments: 'Written Submissions',
      Appeal: 'Memorandum of Appeal',
    };
    getCase(caseIdParam).then((res) => {
      const caseData = res.data;
      setSelectedCaseId(caseIdParam);
      const stage = caseData?.stage;
      if (stage && STAGE_TO_TYPE[stage]) setSelectedDocType(STAGE_TO_TYPE[stage]);
    }).catch(() => {});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── If launched with an id, load that draft ──
  useEffect(() => {
    if (id) {
      apiClient.get('aidrafts/get_draft_sections', { params: { session_id: id } }).then((r) => {
        setSections(r.data?.draft_sections ?? []);
        setAiSuggestionCount(r.data?.ai_suggested_update_count ?? 0);
        setConversationHistory(withConversationIds(r.data?.conversation_history));
        setAppliedSuggestionIds(new Set());
        // NOTE: get_draft_sections never returns a `title` field — the real display
        // name only comes from the get_user_saved_drafts_v2 lookup below. Setting it
        // here from an always-undefined field used to stomp the correct title with a
        // fresh timestamp placeholder in a race against that lookup.
        setSessionId(id);
        setPhase('editing');
        setHasUnsavedChanges(false);
        fetchDraftFor(id);
      }).catch(() => setError('Could not load draft.'));

      apiClient.get('aidrafts/get_user_saved_drafts_v2').then((response) => {
        const rows = normalizeSavedDraftRows(response.data?.saved_drafts ?? []);
        const matched = rows.find((row) => row.session_id === id);
        if (matched) {
          syncCurrentSavedDraftMeta(matched.draft_id, matched.last_updated_on || matched.created_on);
          setDraftTitle(resolveDraftTitle(matched.draft_name));
        }
      }).catch(() => {});
    }
  }, [id]);

  // ── Helper: case-client map from filterData ──
  const caseClientMap = filterData?.case_client_map || {};
  const caseIds = Object.keys(caseClientMap);

  function handleCaseChange(caseId) {
    setSelectedCaseId(caseId);
    if (caseId && caseClientMap[caseId]) {
      const clientInfo = caseClientMap[caseId];
      // client_id may be a field like phone or _id — use what's available
      setSelectedClientId(clientInfo.client_id || clientInfo.phone_number || '');
    } else {
      setSelectedClientId('');
    }
  }

  // ── Create new draft ──
  async function handleCreateDraft(e) {
    e.preventDefault();
    if (!query.trim() && !sourceFile) {
      setError('Please upload a document or add a description (or both).');
      return;
    }
    setInitLoading(true);
    setError('');
    dispatch(beginBlocking({ message: 'Generating your draft. This can take a few moments...' }));
    try {
      const payload = {
        user_query: query,
        document_type: selectedDocType,
        language: selectedLanguage || 'English',
      };

      if (!isClientUser && !isPersonal && buildSelectedDraftFor().length > 0) {
        payload.draft_for = buildSelectedDraftFor();
      } else if (!isClientUser && !isPersonal && selectedCaseId) {
        const clientInfo = caseClientMap[selectedCaseId] || {};
        payload.draft_for = [{
          case_id: selectedCaseId,
          client_id: selectedClientId || clientInfo.client_id || '',
          client_name: `${clientInfo.Fname || ''} ${clientInfo.Lname || ''}`.trim(),
        }];
      }

      if (selectedState) {
        payload.location = {
          state: selectedState,
          district: selectedDistrict || '',
          court: selectedCourt || '',
        };
      }

      let res;
      if (sourceFile) {
        const formData = new FormData();
        formData.append('file', sourceFile);
        formData.append('draft_for', JSON.stringify(payload.draft_for || []));
        formData.append('language', payload.language);
        if (query.trim()) {
          formData.append('user_query', query.trim());
        }
        if (payload.location) {
          formData.append('location', JSON.stringify(payload.location));
        }
        res = await apiClient.post('aidrafts/start_session_for_casedocument', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      } else {
        res = await apiClient.post('aidrafts/initial_request/', payload);
      }
      if (res.data?.quota) {
        refreshEntitlements(dispatch);
      }
      const newSessionId = res.data?.session_id || res.data?.id;
      if (!newSessionId) throw new Error('No session ID returned');

      // Fetch the sections
      const sectRes = await apiClient.get('aidrafts/get_draft_sections', { params: { session_id: newSessionId } });
      setSections(sectRes.data?.draft_sections ?? []);
      setAiSuggestionCount(sectRes.data?.ai_suggested_update_count ?? 0);
      setConversationHistory(withConversationIds(sectRes.data?.conversation_history));
      setAppliedSuggestionIds(new Set());
      setSessionId(newSessionId);
      setDraftTitle(resolveDraftTitle(res.data?.draft_name, res.data?.title));
      setDraftForData(payload.draft_for || []);
      syncCurrentSavedDraftMeta(res.data?.draft_id, res.data?.last_updated_on || res.data?.draft_saved_at);
      setHasUnsavedChanges(false);
      posthog?.capture('draft_created', {
        input_method: sourceFile && query.trim() ? 'upload_and_write' : sourceFile ? 'upload' : 'write',
        document_type: payload.document_type,
      });
      setPhase('editing');
      navigate(`/drafting/${newSessionId}`, { replace: true });
      setQuery('');
      setSourceFile(null);
    } catch (err) {
      if (err.response?.data?.quota) {
        refreshEntitlements(dispatch);
      }
      setError(err.response?.data?.error || err.message || 'Failed to create draft.');
    } finally {
      dispatch(stopBlocking());
      setInitLoading(false);
    }
  }

  // ── Load saved draft ──
  async function handleLoadDraft(draft) {
    dispatch(beginBlocking({ message: 'Loading saved draft...' }));
    try {
      const sId = draft.session_id || draft.id;
      const dId = draft.draft_id;
      const res = await apiClient.get('aidrafts/load_saved_draft', { params: { session_id: sId, draft_id: dId } });
      setSections(res.data?.draft_sections ?? []);
      setSessionId(sId);
      setDraftTitle(resolveDraftTitle(draft.draft_name, draft.title));
      setAiSuggestionCount(0);
      setConversationHistory([]);
      syncCurrentSavedDraftMeta(dId, draft.last_updated_on || draft.created_on);
      setHasUnsavedChanges(false);
      fetchDraftFor(sId);
      // load_saved_draft returns a content snapshot only — pull the live session's
      // AI-suggestion count and conversation log separately so both stay accurate.
      refreshDraftSections(sId).catch(() => {});
      setPhase('editing');
      navigate(`/drafting/${sId}`, { replace: true });
    } catch {
      setError('Could not load the selected draft.');
    } finally {
      dispatch(stopBlocking());
    }
  }

  // ── Start from an existing server template or uploaded DOCX ──
  async function handleLoadTemplate(e) {
    e.preventDefault();
    if (!selectedTemplateType) { setError('Please select a document type.'); return; }
    if (templateSource === 'existing' && !selectedTemplateName) { setError('Please select a template name.'); return; }
    if (templateSource === 'upload' && !templateFile) { setError('Please choose a .docx file to upload.'); return; }
    setTemplateLoading(true);
    setError('');
    dispatch(beginBlocking({ message: 'Preparing draft from template...' }));
    try {
      const fd = new FormData();
      fd.append('draft_type', selectedTemplateType);
      if (templateSource === 'upload') {
        fd.append('file', templateFile);
      } else {
        fd.append('existing_template_name', selectedTemplateName);
      }
      const selectedDraftFor = !isClientUser && !isPersonal ? buildSelectedDraftFor() : [];
      if (selectedDraftFor.length > 0) {
        fd.append('draft_for', JSON.stringify(selectedDraftFor));
      } else if (!isClientUser && !isPersonal && selectedCaseId) {
        const clientInfo = caseClientMap[selectedCaseId] || {};
        fd.append('draft_for', JSON.stringify([{
          case_id: selectedCaseId,
          client_id: selectedClientId || clientInfo.client_id || '',
          client_name: `${clientInfo.Fname || ''} ${clientInfo.Lname || ''}`.trim(),
        }]));
      }
      const res = await apiClient.post('aidrafts/upload_template', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      if (res.data?.quota) {
        refreshEntitlements(dispatch);
      }
      const newSId = res.data?.session_id || res.data?.id;
      if (!newSId) throw new Error('No session ID returned');
      const sectRes = await apiClient.get('aidrafts/get_draft_sections', { params: { session_id: newSId } });
      setSections(sectRes.data?.draft_sections ?? []);
      setAiSuggestionCount(sectRes.data?.ai_suggested_update_count ?? 0);
      setConversationHistory(withConversationIds(sectRes.data?.conversation_history));
      setAppliedSuggestionIds(new Set());
      setSessionId(newSId);
      setDraftTitle(resolveDraftTitle(selectedTemplateName, selectedTemplateType));
      setDraftForData(selectedDraftFor.length > 0 ? selectedDraftFor : (!isPersonal && selectedCaseId ? [{
        case_id: selectedCaseId,
        client_id: selectedClientId || '',
        client_name: `${(caseClientMap[selectedCaseId] || {}).Fname || ''} ${(caseClientMap[selectedCaseId] || {}).Lname || ''}`.trim(),
      }] : []));
      syncCurrentSavedDraftMeta(res.data?.draft_id, res.data?.last_updated_on || res.data?.draft_saved_at);
      setHasUnsavedChanges(false);
      setPhase('editing');
      navigate(`/drafting/${newSId}`, { replace: true });
    } catch (err) {
      if (err.response?.data?.quota) {
        refreshEntitlements(dispatch);
      }
      setError(err.response?.data?.error || err.message || 'Failed to load template.');
    } finally {
      dispatch(stopBlocking());
      setTemplateLoading(false);
    }
  }

  async function handleDownloadSampleTemplate() {
    try {
      const res = await apiClient.get('aidrafts/download_template', { responseType: 'blob' });
      await saveAndShare(res.data, 'sample_template.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
    } catch {
      alert('Download failed. Please try again.');
    }
  }

  // ── Save section content ──
  async function handleSaveSection(idx, html) {
    if (!sessionId) return;
    setSaveStatus('saving');
    const currentSection = sections[idx];
    try {
      await apiClient.post('aidrafts/update_section', {
        session_id: sessionId,
        section_id: currentSection?.section_id,
        section_name: currentSection?.section_name || currentSection?.section_title || `Section ${idx + 1}`,
        content: html,
      });
      setSaveStatus('saved');
      setHasUnsavedChanges(false);
      setSections((current) => current.map((section, index) => (
        index === idx
          ? { ...section, content: html, section_content: html }
          : section
      )));
      setTimeout(() => setSaveStatus(''), 2000);
    } catch {
      setSaveStatus('error');
    }
  }

  async function handleRenameSection(idx, nextTitle) {
    if (!sessionId || !nextTitle.trim()) return;
    const currentSection = sections[idx];
    try {
      await apiClient.post('aidrafts/update_section', {
        session_id: sessionId,
        section_id: currentSection?.section_id,
        section_name: nextTitle.trim(),
        content: currentSection?.content || currentSection?.section_content || '',
      });
      setSections((current) => current.map((section, index) => (
        index === idx
          ? { ...section, section_name: nextTitle.trim(), section_title: nextTitle.trim() }
          : section
      )));
      setSaveStatus('saved');
      setHasUnsavedChanges(false);
    } catch {
      setError('Failed to update section title.');
    }
  }

  // ── AI prompt ──
  // NOTE: suggestions are never applied to the draft automatically — the assistant's
  // reply is only added to the conversation log here. Section content only changes
  // when the user explicitly clicks "Apply to draft" (see handleApplySuggestion).
  async function handleAIPrompt(prompt) {
    if (!sessionId || suggestionPromptDisabled) return;
    posthog?.capture('ai_suggestion_requested', { session_id: sessionId });
    const activeSection = sections[activeSectionIdx];
    const sectionId = activeSection?.section_id;
    setConversationHistory((h) => [...h, { id: h.length, role: 'user', content: prompt, section_id: sectionId }]);
    setAiLoading(true);
    setError('');
    try {
      const res = await apiClient.post('aidrafts/refine_section/', {
        session_id: sessionId,
        section_index: activeSectionIdx,
        section_title: activeSection?.section_title || activeSection?.title || '',
        instruction: prompt,
      });
      const refined = res.data?.refined_content || res.data?.content || '';
      setAiSuggestionCount(res.data?.ai_update_count ?? aiSuggestionCount);
      setSuggestionQuota(res.data?.quota || null);
      if (res.data?.quota) {
        refreshEntitlements(dispatch);
      }
      setConversationHistory((h) => [...h, { id: h.length, role: 'assistant', content: refined, section_id: sectionId }]);
    } catch (err) {
      const nextQuota = err.response?.data?.quota || null;
      setSuggestionQuota(nextQuota);
      if (nextQuota) {
        refreshEntitlements(dispatch);
      }
      if (nextQuota) {
        setError(buildQuotaNotice(nextQuota, err.response?.data?.error)?.message || err.response?.data?.error || 'AI suggestions are unavailable right now.');
      }
      setConversationHistory((h) => [
        ...h,
        { id: h.length, role: 'assistant', content: err.response?.data?.error || 'Sorry, I could not process that request.', section_id: sectionId, isError: true },
      ]);
    } finally {
      setAiLoading(false);
    }
  }

  // ── Apply an AI suggestion to the draft (only happens on explicit user action) ──
  function handleApplySuggestion(entry) {
    if (!entry?.content || entry.section_id == null) return;
    setSections((secs) =>
      secs.map((s) => (
        s.section_id === entry.section_id ? { ...s, section_content: entry.content, content: entry.content } : s
      )),
    );
    setHasUnsavedChanges(true);
    setAppliedSuggestionIds((current) => new Set(current).add(entry.id));
  }

  // ── Export draft ──
  async function handleExport(format = 'docx') {
    if (!sessionId) return;
    try {
      const res = await apiClient.post('aidrafts/export/', { session_id: sessionId, format }, { responseType: 'blob' });
      const mimeType = format === 'pdf'
        ? 'application/pdf'
        : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
      await saveAndShare(res.data, `${draftTitle}.${format}`, mimeType);
    } catch {
      alert('Export failed. Please try again.');
    }
  }

  async function handleSaveDraft() {
    if (!sessionId) return;
    if (!draftTitle.trim()) {
      setError('Draft name cannot be empty.');
      return;
    }
    setSavingDraft(true);
    setError('');
    try {
      const response = await apiClient.post('aidrafts/save_draft', {
        session_id: sessionId,
        draft_id: currentSavedDraftId,
        draft_name: draftTitle.trim(),
        draft_sections: sections,
        draft_for: draftForData,
      });
      posthog?.capture('draft_saved', { session_id: sessionId });
      setSaveStatus('saved');
      setHasUnsavedChanges(false);
      syncCurrentSavedDraftMeta(response.data?.draft_id, response.data?.last_updated_on || response.data?.saved_at);
      refreshSavedDrafts();
      setTimeout(() => setSaveStatus(''), 2000);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to save draft.');
      setSaveStatus('error');
    } finally {
      setSavingDraft(false);
    }
  }

  async function handleRevertDraft() {
    if (!sessionId) return;
    try {
      await apiClient.post('aidrafts/revert_to_original', { session_id: sessionId });
      await refreshDraftSections(sessionId);
      setSaveStatus('saved');
    } catch {
      setError('Failed to revert draft.');
    }
  }

  async function handleSendDraft(e) {
    e.preventDefault();
    setSendLoading(true);
    setSendResult(null);
    try {
      const toList = sendToEmails.split(/[,;\s]+/).map((s) => s.trim()).filter(Boolean);
      const ccList = sendCcEmails.split(/[,;\s]+/).map((s) => s.trim()).filter(Boolean);
      await apiClient.post('aidrafts/send_draft/', {
        session_id: sessionId,
        to_emails: toList,
        cc_emails: ccList,
        note: sendNote.trim(),
        format: sendFormat,
      });
      setSendResult({ ok: true, message: `Draft sent to ${toList.join(', ')} as ${sendFormat.toUpperCase()}` });
    } catch (err) {
      setSendResult({ ok: false, message: err.response?.data?.error || 'Failed to send. Please try again.' });
    } finally {
      setSendLoading(false);
    }
  }

  async function handleAddSection() {
    if (!sessionId) return;
    const sectionName = window.prompt('Section name');
    if (!sectionName?.trim()) return;
    try {
      const response = await apiClient.post('aidrafts/add_section', {
        session_id: sessionId,
        section_name: sectionName.trim(),
        content: '',
      });
      const newSection = response.data?.section;
      if (newSection) {
        setSections((current) => [...current, newSection]);
        setActiveSectionIdx(sections.length);
        setHasUnsavedChanges(true);
      } else {
        await refreshDraftSections(sessionId);
      }
    } catch {
      setError('Failed to add section.');
    }
  }

  async function handleDeleteSection(sectionId) {
    if (!sessionId || !sectionId) return;
    if (!window.confirm('Delete this section?')) return;
    try {
      await apiClient.post('aidrafts/delete_section', { session_id: sessionId, section_id: sectionId });
      setSections((current) => {
        const next = current.filter((section) => section.section_id !== sectionId);
        const nextIndex = Math.max(0, Math.min(activeSectionIdx, next.length - 1));
        setActiveSectionIdx(nextIndex);
        return next;
      });
      setHasUnsavedChanges(true);
    } catch {
      setError('Failed to delete section.');
    }
  }

  async function persistReorderedSections(reordered, nextIndex, previousSections, previousIndex) {
    setSections(reordered);
    setActiveSectionIdx(nextIndex);
    try {
      await apiClient.post('aidrafts/update_section_order', {
        session_id: sessionId,
        draft_sections: reordered,
      });
      setHasUnsavedChanges(false);
    } catch {
      setSections(previousSections);
      setActiveSectionIdx(previousIndex);
      setError('Failed to update section order.');
    }
  }

  async function handleMoveSection(fromIndex, direction) {
    const toIndex = fromIndex + direction;
    if (toIndex < 0 || toIndex >= sections.length) return;
    const previousSections = [...sections];
    const reordered = [...sections];
    const [moved] = reordered.splice(fromIndex, 1);
    reordered.splice(toIndex, 0, moved);
    await persistReorderedSections(reordered, toIndex, previousSections, fromIndex);
  }

  async function handleDragEnd(result) {
    if (!result.destination) return;
    const fromIndex = result.source.index;
    const toIndex = result.destination.index;
    if (fromIndex === toIndex) return;

    const previousSections = [...sections];
    const reordered = [...sections];
    const [moved] = reordered.splice(fromIndex, 1);
    reordered.splice(toIndex, 0, moved);
    await persistReorderedSections(reordered, toIndex, previousSections, activeSectionIdx);
  }

  async function handleShowHistory(sectionId) {
    if (!sessionId || !sectionId) return;
    try {
      const response = await apiClient.get('aidrafts/get_section_history', {
        params: { session_id: sessionId, section_id: sectionId },
      });
      setSectionHistory(response.data?.history ?? []);
      setHistoryOpen(true);
    } catch {
      setError('Failed to fetch section history.');
    }
  }

  const activeSection = sections[activeSectionIdx];

  // ──────────────────────────────────────────────────────────────────────────
  // INIT PHASE — choose document type & describe what to draft
  // ──────────────────────────────────────────────────────────────────────────
  if (phase === 'init') {
    const docCategories = filterData?.document_categories || [];
    return (
      <div className="flex h-full">


        {/* Center: init form */}
        <div className="flex-1 flex items-start justify-center p-10 overflow-y-auto">
          <div className="w-full max-w-2xl">
            <div className="mb-8">
              <div className="flex items-center gap-2 text-sm text-slate-500 mb-4">
                <span>Documents</span>
                <span className="material-symbols-outlined text-xs">chevron_right</span>
                <span className="font-medium text-ink">AI Drafting</span>
              </div>
              <h1 className="text-2xl font-black text-ink mb-2">Legal Document Workshop</h1>
              <p className="text-slate-500 text-sm">
                Create from scratch, load a saved draft, or let AI guide you step by step.
              </p>
            </div>

            {/* Tab bar */}
            <div className="flex gap-1 bg-ivory border border-primary/10 rounded-lg p-1 w-fit mb-6">
              {[
                { label: 'New Draft', icon: 'auto_awesome' },
                { label: 'Load Draft', icon: 'folder_open' },
              ].map((tab, i) => (
                <button
                  key={tab.label}
                  type="button"
                  onClick={() => { if (tab.onClick) { tab.onClick(); } else { setInitTab(i); setError(''); } }}
                  className={`relative flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded transition-all ${
                    tab.premium
                      ? 'bg-gradient-to-r from-primary to-amber-500 text-ivory shadow-md shadow-primary/30 hover:shadow-lg hover:shadow-primary/40'
                      : initTab === i
                        ? 'bg-primary text-ivory shadow-sm'
                        : 'text-slate-600 hover:text-primary'
                  }`}
                >
                  <span className="material-symbols-outlined text-sm">{tab.icon}</span>
                  {tab.label}
                  {tab.premium && (
                    <span className="ml-1 px-1.5 py-0.5 rounded-full bg-white/25 text-ivory text-[9px] font-bold tracking-wide">
                      PREMIUM
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* ── Tab 0: New Draft ── */}
            {initTab === 0 && (
              <form onSubmit={handleCreateDraft} className="space-y-6">
                {/* Case context banner — shown when navigated from CaseHub via DraftContextAgent */}
                {caseContext && (
                  <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2 text-sm text-primary">
                      <span className="material-symbols-outlined text-base mt-0.5">auto_awesome</span>
                      <div>
                        <span className="font-semibold">Case context loaded:</span>{' '}
                        <span className="text-primary/80">{caseContext.draft_for?.case_title || 'Case'}</span>
                        {caseContext.context_summary && (
                          <p className="text-xs text-primary/60 mt-0.5 line-clamp-2">{caseContext.context_summary}</p>
                        )}
                      </div>
                    </div>
                    <button type="button" onClick={() => { setCaseContext(null); setQuery(''); }}
                      className="text-primary/40 hover:text-primary/70 transition flex-shrink-0">
                      <span className="material-symbols-outlined text-sm">close</span>
                    </button>
                  </div>
                )}
                {/* Document type selector */}
                {docCategories.length > 0 && (
                  <div>
                    <label className="block text-sm font-semibold mb-3 text-slate-700">
                      Document Category
                    </label>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => setSelectedDocType('')}
                        className={`px-3 py-1.5 text-xs font-semibold rounded-full border transition-all ${
                          !selectedDocType
                            ? 'bg-primary text-ivory border-primary'
                            : 'bg-white text-slate-600 border-slate-200 hover:border-primary/50'
                        }`}
                      >
                        Auto-detect
                      </button>
                      {docCategories.map((cat) => (
                        <button
                          key={cat}
                          type="button"
                          onClick={() => setSelectedDocType(cat)}
                          className={`px-3 py-1.5 text-xs font-semibold rounded-full border transition-all ${
                            selectedDocType === cat
                              ? 'bg-primary text-ivory border-primary'
                              : 'bg-white text-slate-600 border-slate-200 hover:border-primary/50'
                          }`}
                        >
                          {cat}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Personal vs Case toggle */}
                {!isClientUser && <div>
                  <label className="block text-sm font-semibold mb-3 text-slate-700">Draft For</label>
                  <div className="flex gap-2">
                    {[
                      { key: false, label: 'Linked to a Case' },
                      { key: true, label: 'Personal / General' },
                    ].map((opt) => (
                      <button
                        key={String(opt.key)}
                        type="button"
                        onClick={() => {
                          setIsPersonal(opt.key);
                          setSelectedCaseId('');
                          setSelectedClientId('');
                        }}
                        className={`flex-1 py-2 text-xs font-semibold rounded-lg border transition-all ${
                          isPersonal === opt.key
                            ? 'bg-primary text-ivory border-primary'
                            : 'bg-white text-slate-600 border-slate-200 hover:border-primary/50'
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>}

                {!isClientUser && !isPersonal && (
                  <DraftForSelector
                    rows={draftForRows}
                    selectedIds={selectedDraftForIds}
                    onToggle={handleToggleDraftFor}
                    onToggleAll={handleToggleAllDraftFor}
                    onAddCustom={handleAddDraftForRow}
                  />
                )}

                {/* Location: state / district / court */}
                <div>
                  <label className="block text-sm font-semibold mb-3 text-slate-700">
                    Jurisdiction <span className="text-slate-400 font-normal text-xs">(optional)</span>
                  </label>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs font-semibold mb-1 text-slate-700">State</label>
                      <select
                        value={selectedState}
                        onChange={(e) => setSelectedState(e.target.value)}
                        className="input-base"
                      >
                        <option value="">Any</option>
                        {states.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold mb-1 text-slate-700">District</label>
                      <select
                        value={selectedDistrict}
                        onChange={(e) => setSelectedDistrict(e.target.value)}
                        disabled={!selectedState || districts.length === 0}
                        className="input-base disabled:opacity-50"
                      >
                        <option value="">Any</option>
                        {districts.map((d) => (
                          <option key={d} value={d}>{d}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold mb-1 text-slate-700">Court</label>
                      <select
                        value={selectedCourt}
                        onChange={(e) => setSelectedCourt(e.target.value)}
                        disabled={!selectedDistrict || courts.length === 0}
                        className="input-base disabled:opacity-50"
                      >
                        <option value="">Any</option>
                        {courts.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                {/* Language */}
                {languages.length > 0 && (
                  <div>
                    <label className="block text-sm font-semibold mb-2 text-slate-700">Language</label>
                    <div className="flex flex-wrap gap-2">
                      {languages.map((lang) => (
                        <button
                          key={lang}
                          type="button"
                          onClick={() => setSelectedLanguage(lang)}
                          className={`px-3 py-1.5 text-xs font-semibold rounded-full border transition-all ${
                            selectedLanguage === lang
                              ? 'bg-primary text-ivory border-primary'
                              : 'bg-white text-slate-600 border-slate-200 hover:border-primary/50'
                          }`}
                        >
                          {lang}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Source: upload document (optional) and/or description (optional) — at least one required */}
                <div>
                  <label className="block text-sm font-semibold mb-2 text-slate-700">
                    Upload Source Document <span className="text-slate-400 font-normal text-xs">(optional)</span>
                  </label>
                  <div className="rounded-xl border border-dashed border-primary/25 bg-ivory/40 p-5">
                    <input
                      type="file"
                      accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg"
                      onChange={(e) => setSourceFile(e.target.files?.[0] || null)}
                      className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20 cursor-pointer"
                    />
                    <p className="text-xs text-slate-400 mt-3">Supported formats: PDF, DOC, DOCX, TXT, PNG, JPG. Scanned images are read via OCR.</p>
                    {sourceFile && (
                      <p className="text-xs text-primary mt-2 flex items-center gap-2">
                        Selected: {sourceFile.name}
                        <button type="button" onClick={() => setSourceFile(null)} className="text-slate-400 hover:text-red-500">
                          <span className="material-symbols-outlined text-sm align-middle">close</span>
                        </button>
                      </p>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-semibold mb-2 text-slate-700">
                    Describe Your Document <span className="text-slate-400 font-normal text-xs">(optional)</span>
                  </label>
                  <textarea
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="E.g., Draft an employment agreement for a senior software engineer in Delhi with a 6-month probation period and non-compete clause…"
                    rows={6}
                    className="input-base resize-none"
                  />
                  <p className="text-xs text-slate-400 mt-1.5">
                    Be specific about parties, jurisdiction, and key terms for the best results. If you've uploaded a document, this description is used as extra context alongside it.
                  </p>
                </div>

                {error && (
                  <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                    <span className="material-symbols-outlined text-base">error</span>
                    {error}
                  </div>
                )}

                <div className="flex gap-3">
                  <button
                    type="submit"
                    disabled={initLoading}
                    className="btn-primary flex items-center gap-2 py-3 px-6"
                  >
                    {initLoading ? (
                      <>
                        <span className="material-symbols-outlined text-base animate-spin">progress_activity</span>
                        Generating Draft…
                      </>
                    ) : (
                      <>
                        <span className="material-symbols-outlined text-base">auto_awesome</span>
                        Generate Draft
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}

            {/* ── Tab 1: Load Draft ── */}
            {initTab === 1 && (
              <div className="space-y-4">
                <div className="grid grid-cols-[180px_1fr] gap-3">
                  <div>
                    <label className="block text-sm font-semibold mb-2 text-slate-700">Search Field</label>
                    <select value={draftSearchField} onChange={(e) => { setDraftPage(0); setDraftSearchField(e.target.value); }} className="input-base">
                      <option value="draft_name">Draft Name</option>
                      <option value="caseid">Case ID</option>
                      <option value="clientid">Client Name</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold mb-2 text-slate-700">Search Saved Drafts</label>
                    <input
                      value={draftSearch}
                      onChange={(e) => { setDraftPage(0); setDraftSearch(e.target.value); }}
                      placeholder="Search saved drafts…"
                      className="input-base"
                    />
                  </div>
                </div>
                <div className="space-y-2 max-h-[500px] overflow-y-auto custom-scrollbar">
                  {savedDrafts
                    .map((d) => (
                      <button
                        key={d.draft_id || d.session_id}
                        onClick={() => handleLoadDraft(d)}
                        className="w-full text-left px-4 py-3 bg-white border border-primary/10 rounded-xl hover:border-primary/30 hover:bg-primary/5 transition-all"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="text-sm font-semibold text-ink truncate">{d.draft_name || 'Untitled Draft'}</p>
                            {getDraftForSummary(d.draft_for).clientNames && (
                              <p className="text-xs text-slate-400 mt-0.5">{getDraftForSummary(d.draft_for).clientNames}</p>
                            )}
                            {getDraftForSummary(d.draft_for).caseIds && (
                              <p className="text-xs text-slate-400">Case: {getDraftForSummary(d.draft_for).caseIds}</p>
                            )}
                          </div>
                          <div className="text-right flex-shrink-0">
                            {d.last_updated_on && (
                              <p className="text-xs text-slate-400">
                                {new Date(d.last_updated_on).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                              </p>
                            )}
                            {d.created_on && !d.last_updated_on && (
                              <p className="text-xs text-slate-400">
                                {new Date(d.created_on).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                              </p>
                            )}
                          </div>
                        </div>
                      </button>
                    ))}
                  {savedDrafts.length === 0 && (
                    <div className="text-center py-12 text-slate-400">
                      <span className="material-symbols-outlined text-4xl block mb-2">folder_open</span>
                      <p className="text-sm">No saved drafts yet.</p>
                      <p className="text-xs mt-1">Create a draft first, then save it to access it here.</p>
                    </div>
                  )}
                </div>
                <div className="flex items-center justify-between gap-3 pt-2">
                  <p className="text-xs text-slate-400">Showing {savedDrafts.length} of {draftTotalCount} drafts</p>
                  <div className="flex items-center gap-2">
                    <select value={draftPageSize} onChange={(e) => { setDraftPage(0); setDraftPageSize(Number(e.target.value)); }} className="input-base py-2 text-xs min-w-[90px]">
                      {[5, 10, 20, 50].map((size) => <option key={size} value={size}>{size}/page</option>)}
                    </select>
                    <button type="button" className="btn-ghost text-xs" onClick={() => setDraftPage((current) => Math.max(0, current - 1))} disabled={draftPage === 0}>Prev</button>
                    <span className="text-xs text-slate-500">Page {draftPage + 1}</span>
                    <button type="button" className="btn-ghost text-xs" onClick={() => setDraftPage((current) => current + 1)} disabled={(draftPage + 1) * draftPageSize >= draftTotalCount}>Next</button>
                  </div>
                </div>
                {error && (
                  <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                    <span className="material-symbols-outlined text-base">error</span>
                    {error}
                  </div>
                )}
              </div>
            )}

            {/* ── Tab 2: Load Template ── */}
            {initTab === 2 && (
              <form onSubmit={handleLoadTemplate} className="space-y-6">
                {/* Template source toggle */}
                <div>
                  <label className="block text-sm font-semibold mb-3 text-slate-700">Template Source</label>
                  <div className="flex gap-2">
                    {[
                      { key: 'existing', label: 'Use Existing Template' },
                      { key: 'upload', label: 'Upload My Own (.docx)' },
                    ].map((opt) => (
                      <button
                        key={opt.key}
                        type="button"
                        onClick={() => setTemplateSource(opt.key)}
                        className={`flex-1 py-2 text-xs font-semibold rounded-lg border transition-all ${
                          templateSource === opt.key
                            ? 'bg-primary text-ivory border-primary'
                            : 'bg-white text-slate-600 border-slate-200 hover:border-primary/50'
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Document type */}
                <div>
                  <label className="block text-sm font-semibold mb-2 text-slate-700">Document Type</label>
                  <select
                    value={selectedTemplateType}
                    onChange={(e) => setSelectedTemplateType(e.target.value)}
                    className="input-base"
                  >
                    <option value="">
                      {templateTypes.length === 0 ? 'Loading…' : 'Select a type…'}
                    </option>
                    {templateTypes.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>

                {/* Template name — existing templates only */}
                {templateSource === 'existing' && (
                  <div>
                    <label className="block text-sm font-semibold mb-2 text-slate-700">Template Name</label>
                    <select
                      value={selectedTemplateName}
                      onChange={(e) => setSelectedTemplateName(e.target.value)}
                      disabled={!selectedTemplateType || templateNames.length === 0}
                      className="input-base disabled:opacity-50"
                    >
                      <option value="">
                        {!selectedTemplateType ? 'Select a type first…' : templateNames.length === 0 ? 'No templates found' : 'Select a template…'}
                      </option>
                      {templateNames.map((n) => (
                        <option key={n} value={n}>{n}</option>
                      ))}
                    </select>
                  </div>
                )}

                {/* File upload — upload mode only */}
                {templateSource === 'upload' && (
                  <div>
                    <label className="block text-sm font-semibold mb-2 text-slate-700">Upload Template File</label>
                    <input
                      type="file"
                      accept=".docx"
                      onChange={(e) => setTemplateFile(e.target.files?.[0] || null)}
                      className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20 cursor-pointer"
                    />
                    <p className="text-xs text-slate-400 mt-1">Accepts .docx files only</p>
                  </div>
                )}

                {!isClientUser && (
                  <DraftForSelector
                    rows={draftForRows}
                    selectedIds={selectedDraftForIds}
                    onToggle={handleToggleDraftFor}
                    onToggleAll={handleToggleAllDraftFor}
                    onAddCustom={handleAddDraftForRow}
                  />
                )}

                {error && (
                  <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                    <span className="material-symbols-outlined text-base">error</span>
                    {error}
                  </div>
                )}

                <div className="flex gap-3">
                  <button
                    type="submit"
                    disabled={templateLoading}
                    className="btn-primary flex items-center gap-2 py-3 px-6"
                  >
                    {templateLoading ? (
                      <>
                        <span className="material-symbols-outlined text-base animate-spin">progress_activity</span>
                        Loading Template…
                      </>
                    ) : (
                      <>
                        <span className="material-symbols-outlined text-base">upload_file</span>
                        Use This Template
                      </>
                    )}
                  </button>
                  <button
                    type="button"
                    className="btn-ghost border border-primary/20 rounded-lg flex items-center gap-2 py-3 px-5"
                    onClick={handleDownloadSampleTemplate}
                  >
                    <span className="material-symbols-outlined text-base">download</span>
                    Download Sample
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>

      </div>
    );
  }

  // ──────────────────────────────────────────────────────────────────────────
  // EDITING PHASE — 3-pane layout matching Stitch
  // ──────────────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full overflow-hidden relative">
      <HistoryDialog open={historyOpen} items={sectionHistory} onClose={() => setHistoryOpen(false)} />
      <ConfirmLeaveDialog open={leaveDialogOpen} onConfirm={resetToDraftSelection} onCancel={() => setLeaveDialogOpen(false)} />

      {/* Hover strip: lets users recall the auto-hidden header without scrolling up */}
      <div className="absolute top-0 left-0 right-0 h-2 z-30" onMouseEnter={() => setHeaderHidden(false)} />

      {/* Workspace header — single row, auto-hides on scroll-down for more editor/AI-panel space.
          overflow stays visible while shown so the info popover / formatting dropdown aren't clipped;
          only clipped (via max-h-0 + overflow-hidden) while collapsing out of view. */}
      <div className={`flex-shrink-0 transition-[max-height,opacity] duration-200 ease-in-out ${headerHidden ? 'max-h-0 overflow-hidden opacity-0' : 'max-h-16 overflow-visible opacity-100'}`}>
      <header className="flex items-center justify-between border-b border-primary/10 bg-ivory px-6 py-2.5 z-10">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <button className="hover:text-primary transition-colors" onClick={requestBackToSelection}>
              Documents
            </button>
            <span className="material-symbols-outlined text-xs">chevron_right</span>
            <input
              value={draftTitle}
              onChange={(e) => {
                setDraftTitle(e.target.value);
                setHasUnsavedChanges(true);
              }}
              className="bg-transparent font-semibold text-ink truncate max-w-xs outline-none border-b border-transparent focus:border-primary"
            />
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {saveStatus === 'saving' && (
            <span className="text-xs text-slate-400 flex items-center gap-1">
              <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>
              Saving…
            </span>
          )}
          {saveStatus === 'saved' && (
            <span className="text-xs text-emerald-600 flex items-center gap-1">
              <span className="material-symbols-outlined text-sm">check_circle</span>
              Saved
            </span>
          )}

          <EditorToolbar />

          <div className="h-5 w-px bg-primary/10 mx-0.5" />

          {/* Compact status cluster: last saved / suggestions left / quota / sections / location — merged into one hover popover to stop header clipping */}
          <div className="group relative flex items-center gap-1 rounded-full px-2 py-1 text-slate-400 hover:bg-primary/5 hover:text-primary transition-colors cursor-default">
            <span className="material-symbols-outlined text-base">info</span>
            <span className="hidden 2xl:inline text-xs">{remainingSuggestionCount} suggestions left</span>
            <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-150 absolute right-0 top-[calc(100%+8px)] z-20 w-64 rounded-xl border border-primary/10 bg-white p-3 shadow-lg space-y-2">
              {lastSavedAt && (
                <p className="flex items-center gap-1.5 text-xs text-slate-500">
                  <span className="material-symbols-outlined text-sm">schedule</span>
                  Last saved {formatSavedAt(lastSavedAt)}
                </p>
              )}
              <p className="flex items-center gap-1.5 text-xs text-slate-600">
                <span className="material-symbols-outlined text-sm">auto_awesome</span>
                {remainingSuggestionCount} AI suggestions left on this draft
              </p>
              {typeof draftingQuota?.remaining_included === 'number' && (
                <p className="flex items-center gap-1.5 text-xs font-semibold text-primary">
                  <span className="material-symbols-outlined text-sm">workspace_premium</span>
                  {draftingQuota.remaining_included} Brain drafting actions left
                </p>
              )}
              <p className="flex items-center gap-1.5 text-xs text-slate-600">
                <span className="material-symbols-outlined text-sm">article</span>
                {sections.length} sections
              </p>
              <p className="flex items-center gap-1.5 text-xs text-slate-600">
                <span className="material-symbols-outlined text-sm">place</span>
                Location locked from draft setup
              </p>
              {draftForData.length > 0 && (
                <p className="flex items-center gap-1.5 text-xs text-primary">
                  <span className="material-symbols-outlined text-sm">group</span>
                  {draftForData.map((item) => item.client_name || item.clientid || item.client_id || item.case_id).filter(Boolean).join(', ')}
                </p>
              )}
            </div>
          </div>

          <button
            className={`relative flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold shadow-sm transition-all ${
              showAiPanel
                ? 'bg-primary/10 text-primary'
                : 'bg-gradient-to-r from-primary to-amber-500 text-ivory shadow-primary/30 hover:shadow-lg hover:shadow-primary/40'
            }`}
            onClick={() => setShowAiPanel((current) => !current)}
          >
            <span className="material-symbols-outlined text-base">auto_awesome</span>
            {showAiPanel ? 'Hide Assistant' : 'AI Assistant'}
            {!showAiPanel && remainingSuggestionCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-ivory px-1 text-[9px] font-bold text-primary shadow">
                {remainingSuggestionCount}
              </span>
            )}
          </button>

          <div className="h-5 w-px bg-primary/10 mx-0.5" />

          <button
            className="btn-ghost flex items-center gap-1.5 text-xs"
            onClick={handleSaveDraft}
            disabled={savingDraft}
          >
            <span className="material-symbols-outlined text-base">save</span>
            <span className="hidden lg:inline">{savingDraft ? 'Saving…' : 'Save Draft'}</span>
          </button>
          <button
            className="btn-ghost flex items-center gap-1.5 text-xs"
            onClick={handleRevertDraft}
          >
            <span className="material-symbols-outlined text-base">history</span>
            <span className="hidden lg:inline">Revert</span>
          </button>
          <div className="h-5 w-px bg-primary/10 mx-1" />
          <button
            className="flex items-center gap-1.5 bg-primary text-ivory px-3 py-1.5 rounded-lg text-xs font-bold shadow-sm hover:bg-primary/90 transition-all"
            onClick={() => handleExport('docx')}
          >
            <span className="material-symbols-outlined text-base">download</span>
            <span className="hidden lg:inline">Export</span>
          </button>
          {!isClientUser && sessionId && (
            <button
              className="flex items-center gap-1.5 bg-amber-500 text-white px-3 py-1.5 rounded-lg text-xs font-bold shadow-sm hover:bg-amber-600 transition-all"
              onClick={() => { setSendResult(null); setShowSendModal(true); }}
            >
              <span className="material-symbols-outlined text-base">forward_to_inbox</span>
              <span className="hidden lg:inline">Send to Client</span>
            </button>
          )}
        </div>
      </header>
      </div>

      {suggestionQuotaNotice && (
        <div className={`border-b px-6 py-3 text-sm ${quotaNoticeClassName(suggestionQuotaNotice.tone)}`}>
          {suggestionQuotaNotice.message}
        </div>
      )}

      {/* 3-pane body */}
      <div className="flex flex-1 overflow-hidden">


        {/* Center: Editor */}
        <main className="flex-1 flex flex-col bg-background-light overflow-hidden">
          {(remainingSuggestionCount <= 2 || (trial?.active && typeof draftingQuota?.remaining_included === 'number' && draftingQuota.remaining_included <= 3)) && (
            <div className="border-b border-amber-200 bg-amber-50 px-6 py-3 text-sm text-amber-800">
              {remainingSuggestionCount <= 2 ? `This draft is nearing its 7-suggestion limit. ${remainingSuggestionCount} suggestion${remainingSuggestionCount === 1 ? '' : 's'} left before credits or upgrade are needed.` : `Brain drafting usage is running low. ${draftingQuota.remaining_included} premium action${draftingQuota.remaining_included === 1 ? '' : 's'} left${wallet?.balance ? ` and ${wallet.balance} credits available` : ''}.`}
            </div>
          )}
          <div
            className="flex-1 overflow-y-auto p-5 md:p-8 custom-scrollbar"
            onScroll={handleEditorScroll}
          >
            <div className="mx-auto max-w-[1040px] rounded-[1.25rem] border border-primary/5 bg-white p-8 shadow-xl editor-container min-h-[1100px] md:p-12 xl:p-14">
              <button
                onClick={handleAddSection}
                className="mb-6 flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-primary/20 py-3 text-sm font-semibold text-primary hover:border-primary/40 hover:bg-primary/5 transition-colors"
              >
                <span className="material-symbols-outlined text-lg">post_add</span>
                Add New Section
              </button>
              {sections.length > 0 ? (
                <DragDropContext onDragEnd={handleDragEnd}>
                  <Droppable droppableId="draft-sections">
                    {(provided) => (
                      <div ref={provided.innerRef} {...provided.droppableProps}>
                        {sections.map((sec, i) => (
                          <Draggable key={sec.section_id || `section-${i}`} draggableId={String(sec.section_id || `section-${i}`)} index={i}>
                            {(dragProvided) => (
                              <div ref={dragProvided.innerRef} {...dragProvided.draggableProps} style={dragProvided.draggableProps.style} className="mb-8 rounded-lg border border-transparent bg-white/60">
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="min-w-0 flex items-start gap-2">
                        <span {...dragProvided.dragHandleProps} className="mt-0.5 rounded p-1.5 text-slate-500 hover:bg-primary/5 hover:text-primary cursor-grab active:cursor-grabbing">
                          <span className="material-symbols-outlined text-base">drag_indicator</span>
                        </span>
                        <div className="min-w-0 flex-1">
                        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400 mb-1">Section {i + 1}</p>
                        <input
                          value={sec.section_name || sec.section_title || `Section ${i + 1}`}
                          onChange={(e) => {
                            setHasUnsavedChanges(true);
                            setSections((current) => current.map((section, index) => (
                              index === i
                                ? { ...section, section_name: e.target.value, section_title: e.target.value }
                                : section
                            )));
                          }}
                          onBlur={(e) => handleRenameSection(i, e.target.value)}
                          onFocus={() => setActiveSectionIdx(i)}
                          className="w-full bg-transparent text-lg font-bold text-ink outline-none border-b border-transparent focus:border-primary"
                        />
                        </div>
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <button className="p-1.5 rounded hover:bg-primary/5 text-slate-500 hover:text-primary" onClick={() => handleMoveSection(i, -1)} disabled={i === 0}>
                          <span className="material-symbols-outlined text-base">arrow_upward</span>
                        </button>
                        <button className="p-1.5 rounded hover:bg-primary/5 text-slate-500 hover:text-primary" onClick={() => handleMoveSection(i, 1)} disabled={i === sections.length - 1}>
                          <span className="material-symbols-outlined text-base">arrow_downward</span>
                        </button>
                        <button className="p-1.5 rounded hover:bg-primary/5 text-slate-500 hover:text-primary" onClick={() => handleShowHistory(sec.section_id)}>
                          <span className="material-symbols-outlined text-base">manage_history</span>
                        </button>
                        <button className="p-1.5 rounded hover:bg-red-50 text-slate-500 hover:text-red-600" onClick={() => handleDeleteSection(sec.section_id)}>
                          <span className="material-symbols-outlined text-base">delete</span>
                        </button>
                      </div>
                    </div>
                    <div
                      contentEditable
                      suppressContentEditableWarning
                      className={`font-serif text-ink leading-8 text-base outline-none min-h-[60px]
                                  focus:border-l-2 focus:border-primary/30 focus:pl-2 transition-all ${
                                    activeSectionIdx === i ? 'border-l-2 border-primary/30 pl-2' : ''
                                  }`}
                      onFocus={() => setActiveSectionIdx(i)}
                      onInput={() => setHasUnsavedChanges(true)}
                      onBlur={(e) => handleSaveSection(i, e.currentTarget.innerHTML)}
                      dangerouslySetInnerHTML={{
                        __html: DOMPurify.sanitize(sec.content || sec.section_content || ''),
                      }}
                    />
                    {activeSectionIdx === i && (
                      <p className="mt-2 text-xs text-slate-400">AI suggestions and refinements apply to this active section.</p>
                    )}
                              </div>
                            )}
                          </Draggable>
                        ))}
                        {provided.placeholder}
                      </div>
                    )}
                  </Droppable>
                </DragDropContext>
              ) : (
                <div className="flex items-center justify-center h-64">
                  <span className="material-symbols-outlined text-primary text-4xl animate-spin">
                    progress_activity
                  </span>
                </div>
              )}
            </div>
          </div>
        </main>

        {/* Right: AI Panel */}
        {showAiPanel && (
          <AIPanel
            onPrompt={handleAIPrompt}
            loading={aiLoading}
            messages={aiMessages}
            quotaNotice={suggestionQuotaNotice}
            promptDisabled={suggestionPromptDisabled}
            sections={sections}
            activeSectionIdx={activeSectionIdx}
            onSectionChange={setActiveSectionIdx}
            onClose={() => setShowAiPanel(false)}
            width={aiPanelWidth}
            onWidthChange={setAiPanelWidth}
            appliedSuggestionIds={appliedSuggestionIds}
            onApplySuggestion={handleApplySuggestion}
          />
        )}
      </div>

      {/* ── Send to Client modal ─────────────────────────────────────────── */}
      {showSendModal && (
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
          style={{ background: 'rgba(10,20,40,0.65)', backdropFilter: 'blur(4px)' }}
          onClick={(e) => { if (e.target === e.currentTarget && !sendLoading) setShowSendModal(false); }}
        >
          <div className="w-full max-w-md rounded-2xl bg-white shadow-elevated overflow-hidden">
            {/* Header */}
            <div className="bg-background-dark px-6 py-4 flex items-center justify-between">
              <div>
                <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/50">AI Draft</p>
                <h3 className="text-lg font-black text-white mt-0.5">Send to Client</h3>
              </div>
              <button
                onClick={() => setShowSendModal(false)}
                disabled={sendLoading}
                className="rounded-xl p-1.5 text-white/40 hover:bg-white/10 hover:text-white transition-colors"
              >
                <span className="material-symbols-outlined text-xl">close</span>
              </button>
            </div>
            <div className="h-0.5 bg-gradient-to-r from-[#FF9800] via-[#FF9800]/60 to-transparent" />

            {sendResult ? (
              <div className="px-6 py-8 flex flex-col items-center gap-4 text-center">
                <span
                  className={`material-symbols-outlined text-5xl ${sendResult.ok ? 'text-emerald-500' : 'text-red-400'}`}
                >
                  {sendResult.ok ? 'check_circle' : 'error'}
                </span>
                <p className="text-sm font-semibold text-ink">{sendResult.message}</p>
                {sendResult.ok && (
                  <p className="text-xs text-slate-400">The attachment was sent successfully.</p>
                )}
                <button
                  onClick={() => setShowSendModal(false)}
                  className="mt-2 rounded-xl bg-primary px-6 py-2 text-sm font-bold text-white"
                >
                  Done
                </button>
              </div>
            ) : (
              <form onSubmit={handleSendDraft} className="px-6 py-5 space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1.5">Attachment Format</label>
                  <div className="flex gap-2">
                    {[{ val: 'docx', icon: 'description', label: 'DOCX' }, { val: 'pdf', icon: 'picture_as_pdf', label: 'PDF' }].map(({ val, icon, label }) => (
                      <button
                        key={val} type="button"
                        onClick={() => setSendFormat(val)}
                        className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl border text-xs font-bold transition-all ${
                          sendFormat === val
                            ? 'bg-primary text-white border-primary'
                            : 'bg-slate-50 text-slate-600 border-slate-200 hover:border-primary/40'
                        }`}
                      >
                        <span className="material-symbols-outlined text-base">{icon}</span>
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1.5">
                    To <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={sendToEmails}
                    onChange={(e) => setSendToEmails(e.target.value)}
                    placeholder="client@email.com, another@email.com"
                    required
                    className="w-full rounded-xl border border-primary/20 bg-slate-50 px-3 py-2 text-sm text-ink placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/30"
                  />
                  <p className="mt-1 text-[10px] text-slate-400">Comma-separated. Max 5 recipients.</p>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1.5">CC</label>
                  <input
                    type="text"
                    value={sendCcEmails}
                    onChange={(e) => setSendCcEmails(e.target.value)}
                    placeholder="optional@email.com"
                    className="w-full rounded-xl border border-primary/20 bg-slate-50 px-3 py-2 text-sm text-ink placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/30"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1.5">Note to client</label>
                  <textarea
                    value={sendNote}
                    onChange={(e) => setSendNote(e.target.value)}
                    placeholder="Optional message that will appear in the email body…"
                    rows={3}
                    className="w-full rounded-xl border border-primary/20 bg-slate-50 px-3 py-2 text-sm text-ink placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/30 resize-none"
                  />
                </div>
                <p className="text-[11px] text-slate-400">
                  The draft will be sent as a single <strong>{sendFormat.toUpperCase()}</strong> attachment.
                </p>
                <div className="flex justify-end gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => setShowSendModal(false)}
                    disabled={sendLoading}
                    className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={sendLoading || !sendToEmails.trim()}
                    className="rounded-xl bg-primary px-5 py-2 text-sm font-bold text-white hover:bg-primary/90 disabled:opacity-50 flex items-center gap-1.5"
                  >
                    {sendLoading ? (
                      <>
                        <span className="material-symbols-outlined text-base animate-spin">progress_activity</span>
                        Sending…
                      </>
                    ) : (
                      <>
                        <span className="material-symbols-outlined text-base">send</span>
                        Send Draft
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
