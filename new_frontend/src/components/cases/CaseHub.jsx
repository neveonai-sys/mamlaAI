import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useSelector } from 'react-redux';
import apiClient from '../../services/api';
import {
  getCase, updateCase, closeCase,
  listHearingNotes, createHearingNote,
  listCaseNotes, createCaseNote, deleteCaseNote,
  listCaseTasks, createCaseTask, updateCaseTask,
  runDraftContextAgent,
  runCaseClosureAgent,
} from '../../services/casesApi';

// ─── Status / Stage constants ─────────────────────────────────────────────────
const STATUS_STYLE = {
  Active:   'bg-emerald-100 text-emerald-800',
  Settled:  'bg-sky-100 text-sky-800',
  Disposed: 'bg-slate-100 text-slate-700',
  Appeal:   'bg-amber-100 text-amber-800',
  Archived: 'bg-rose-100 text-rose-700',
};
const STAGE_OPTIONS    = ['Filing', 'Pleadings', 'Evidence', 'Arguments', 'Judgment', 'Closed'];
const PRIORITY_STYLE   = { High: 'text-red-600', Medium: 'text-amber-600', Low: 'text-emerald-600' };
const TASK_STATUS_OPTS = ['Pending', 'InProgress', 'Done', 'Cancelled'];

function StatusBadge({ status }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_STYLE[status] || 'bg-slate-100 text-slate-600'}`}>
      {status}
    </span>
  );
}

function SectionCard({ title, icon, children, action }) {
  return (
    <div className="bg-ivory rounded-xl border border-primary/10 shadow-subtle overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
        <h3 className="text-sm font-semibold text-ink flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-lg">{icon}</span>
          {title}
        </h3>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

// ─── HEARINGS TAB ──────────────────────────────────────────────────────────────
function HearingsTab({ caseId, caseData, userType }) {
  const navigate = useNavigate();
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ hearing_date: '', purpose: '', type: 'prep' });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await listHearingNotes(caseId);
      setNotes(res.data.hearing_notes || []);
    } catch (_) {}
    setLoading(false);
  }, [caseId]);

  useEffect(() => { load(); }, [load]);

  async function handleAdd(e) {
    e.preventDefault();
    if (!form.hearing_date) return;
    setSaving(true);
    try {
      const res = await createHearingNote(caseId, form);
      const note = res.data.hearing_note;
      setNotes(prev => [note, ...prev]);
      setShowAdd(false);
      setForm({ hearing_date: '', purpose: '', type: 'prep' });
    } catch (_) {}
    setSaving(false);
  }

  if (loading) return <div className="py-8 text-center text-sm text-graphite/50">Loading…</div>;

  return (
    <div className="space-y-3">
      {userType !== 'Client' && (
        <div className="flex justify-end">
          <button onClick={() => setShowAdd(v => !v)}
            className="flex items-center gap-1.5 text-sm font-medium text-primary hover:underline">
            <span className="material-symbols-outlined text-lg">add</span>
            Add Hearing
          </button>
        </div>
      )}

      {showAdd && (
        <form onSubmit={handleAdd} className="rounded-xl border border-primary/20 bg-primary/5 p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-graphite mb-1">Date *</label>
              <input type="date" className="form-input w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                value={form.hearing_date} onChange={e => setForm(f => ({ ...f, hearing_date: e.target.value }))} required />
            </div>
            <div>
              <label className="block text-xs font-semibold text-graphite mb-1">Type</label>
              <select className="form-select w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                value={form.type} onChange={e => setForm(f => ({ ...f, type: e.target.value }))}>
                <option value="prep">Prep</option>
                <option value="outcome">Outcome</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-graphite mb-1">Purpose</label>
            <input className="form-input w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              placeholder="e.g. Arguments on injunction application"
              value={form.purpose} onChange={e => setForm(f => ({ ...f, purpose: e.target.value }))} />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowAdd(false)}
              className="px-3 py-1.5 text-xs font-medium text-graphite hover:bg-slate-100 rounded-lg">Cancel</button>
            <button type="submit" disabled={saving}
              className="px-3 py-1.5 text-xs font-semibold bg-primary text-white rounded-lg hover:bg-primary-dark disabled:opacity-50">
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      )}

      {notes.length === 0 ? (
        <p className="text-sm text-graphite/50 text-center py-6">No hearing records yet.</p>
      ) : notes.map(n => (
        <button key={n._id}
          onClick={() => navigate(`/cases/${caseId}/hearings/${n._id}`)}
          className="w-full text-left p-4 rounded-xl border border-primary/10 bg-ivory hover:border-primary/30 hover:shadow-subtle transition-all group">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-sm font-semibold text-ink group-hover:text-primary transition-colors">
                {n.hearing_date}
                <span className={`ml-2 text-xs font-normal rounded px-1.5 py-0.5 ${
                  n.type === 'prep' ? 'bg-sky-100 text-sky-700' : 'bg-emerald-100 text-emerald-700'
                }`}>{n.type}</span>
              </p>
              {n.purpose && <p className="text-xs text-graphite/70 mt-0.5">{n.purpose}</p>}
              {n.outcome && <p className="text-xs text-graphite mt-1 line-clamp-2">{n.outcome}</p>}
            </div>
            <span className="material-symbols-outlined text-primary/40 group-hover:text-primary/70 transition-colors flex-shrink-0">chevron_right</span>
          </div>
          {n.next_date && (
            <p className="mt-2 text-[11px] text-graphite/60">
              <span className="material-symbols-outlined text-xs align-middle">event</span> Next: {n.next_date}
            </p>
          )}
        </button>
      ))}
    </div>
  );
}

// ─── NOTES TAB ─────────────────────────────────────────────────────────────────
function NotesTab({ caseId, userType }) {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [content, setContent] = useState('');
  const [visibility, setVisibility] = useState('internal');
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await listCaseNotes(caseId);
      setNotes(res.data.notes || []);
    } catch (_) {}
    setLoading(false);
  }, [caseId]);

  useEffect(() => { load(); }, [load]);

  async function handleAdd(e) {
    e.preventDefault();
    if (!content.trim()) return;
    setSaving(true);
    try {
      const res = await createCaseNote(caseId, {
        content: content.trim(),
        visibility: userType === 'Client' ? 'shared' : visibility,
      });
      setNotes(prev => [res.data.note, ...prev]);
      setContent('');
    } catch (_) {}
    setSaving(false);
  }

  async function handleDelete(noteId) {
    try {
      await deleteCaseNote(caseId, noteId);
      setNotes(prev => prev.filter(n => n._id !== noteId));
    } catch (_) {}
  }

  if (loading) return <div className="py-8 text-center text-sm text-graphite/50">Loading…</div>;

  return (
    <div className="space-y-4">
      <form onSubmit={handleAdd} className="space-y-2">
        <textarea
          className="form-textarea w-full rounded-xl border border-slate-200 px-3 py-2 text-sm resize-none"
          rows={3} placeholder="Write a note…"
          value={content} onChange={e => setContent(e.target.value)}
        />
        <div className="flex items-center justify-between gap-3">
          {userType !== 'Client' && (
            <div className="flex items-center gap-2 text-xs text-graphite">
              <label className="flex items-center gap-1 cursor-pointer">
                <input type="radio" name="vis" value="internal" checked={visibility === 'internal'}
                  onChange={() => setVisibility('internal')} />
                Internal
              </label>
              <label className="flex items-center gap-1 cursor-pointer">
                <input type="radio" name="vis" value="shared" checked={visibility === 'shared'}
                  onChange={() => setVisibility('shared')} />
                Shared with client
              </label>
            </div>
          )}
          <button type="submit" disabled={saving || !content.trim()}
            className="ml-auto px-3 py-1.5 text-xs font-semibold bg-primary text-white rounded-lg hover:bg-primary-dark disabled:opacity-50 transition">
            {saving ? 'Adding…' : 'Add Note'}
          </button>
        </div>
      </form>

      {notes.length === 0 ? (
        <p className="text-sm text-graphite/50 text-center py-4">No notes yet.</p>
      ) : notes.map(n => (
        <div key={n._id} className="p-3 rounded-xl border border-slate-100 bg-ivory">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <p className="text-sm text-ink whitespace-pre-wrap">{n.content}</p>
              <div className="mt-1.5 flex items-center gap-2 text-[11px] text-graphite/60">
                <span>{n.author_role}</span>
                <span>·</span>
                <span>{n.created_at ? new Date(n.created_at).toLocaleDateString() : ''}</span>
                <span className={`rounded px-1 py-0.5 font-medium ${
                  n.visibility === 'shared' ? 'bg-sky-50 text-sky-700' : 'bg-slate-100 text-slate-500'
                }`}>{n.visibility}</span>
              </div>
            </div>
            {userType !== 'Client' && (
              <button onClick={() => handleDelete(n._id)}
                className="p-1 rounded hover:bg-red-50 text-graphite/40 hover:text-red-500 transition flex-shrink-0">
                <span className="material-symbols-outlined text-sm">delete</span>
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── TASKS TAB ─────────────────────────────────────────────────────────────────
function TasksTab({ caseId, userType }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ title: '', due_date: '', priority: 'Medium' });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await listCaseTasks(caseId);
      setTasks(res.data.tasks || []);
    } catch (_) {}
    setLoading(false);
  }, [caseId]);

  useEffect(() => { load(); }, [load]);

  async function handleAdd(e) {
    e.preventDefault();
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      const res = await createCaseTask(caseId, {
        title: form.title.trim(),
        due_date: form.due_date,
        priority: form.priority,
      });
      setTasks(prev => [...prev, res.data.task]);
      setShowAdd(false);
      setForm({ title: '', due_date: '', priority: 'Medium' });
    } catch (_) {}
    setSaving(false);
  }

  async function handleStatusChange(taskId, status) {
    try {
      const res = await updateCaseTask(caseId, taskId, { status });
      setTasks(prev => prev.map(t => t._id === taskId ? res.data.task : t));
    } catch (_) {}
  }

  if (loading) return <div className="py-8 text-center text-sm text-graphite/50">Loading…</div>;

  return (
    <div className="space-y-3">
      {userType !== 'Client' && (
        <div className="flex justify-end">
          <button onClick={() => setShowAdd(v => !v)}
            className="flex items-center gap-1.5 text-sm font-medium text-primary hover:underline">
            <span className="material-symbols-outlined text-lg">add</span>
            Add Task
          </button>
        </div>
      )}

      {showAdd && (
        <form onSubmit={handleAdd} className="rounded-xl border border-primary/20 bg-primary/5 p-4 space-y-3">
          <input className="form-input w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            placeholder="Task title *" value={form.title}
            onChange={e => setForm(f => ({ ...f, title: e.target.value }))} required />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-graphite mb-1">Due Date</label>
              <input type="date" className="form-input w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                value={form.due_date} onChange={e => setForm(f => ({ ...f, due_date: e.target.value }))} />
            </div>
            <div>
              <label className="block text-xs font-semibold text-graphite mb-1">Priority</label>
              <select className="form-select w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                value={form.priority} onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}>
                {['High', 'Medium', 'Low'].map(p => <option key={p}>{p}</option>)}
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={() => setShowAdd(false)}
              className="px-3 py-1.5 text-xs font-medium text-graphite hover:bg-slate-100 rounded-lg">Cancel</button>
            <button type="submit" disabled={saving}
              className="px-3 py-1.5 text-xs font-semibold bg-primary text-white rounded-lg hover:bg-primary-dark disabled:opacity-50">
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      )}

      {tasks.length === 0 ? (
        <p className="text-sm text-graphite/50 text-center py-6">No tasks yet.</p>
      ) : tasks.map(t => (
        <div key={t._id} className="flex items-start gap-3 p-3 rounded-xl border border-slate-100 bg-ivory">
          <input type="checkbox"
            className="mt-0.5 h-4 w-4 rounded border-slate-300 text-primary cursor-pointer flex-shrink-0"
            checked={t.status === 'Done'}
            onChange={e => handleStatusChange(t._id, e.target.checked ? 'Done' : 'Pending')}
            disabled={userType === 'Client'}
          />
          <div className="flex-1 min-w-0">
            <p className={`text-sm font-medium ${t.status === 'Done' ? 'line-through text-graphite/40' : 'text-ink'}`}>
              {t.title}
            </p>
            <div className="mt-1 flex items-center flex-wrap gap-2 text-[11px] text-graphite/60">
              {t.due_date && <span><span className="material-symbols-outlined text-xs align-middle text-amber-500">event</span> {t.due_date}</span>}
              <span className={`font-semibold ${PRIORITY_STYLE[t.priority] || ''}`}>{t.priority}</span>
              {t.source === 'agent' && <span className="bg-violet-100 text-violet-700 rounded px-1 py-0.5 font-medium">AI</span>}
            </div>
          </div>
          {userType !== 'Client' && (
            <select
              className="form-select text-xs border border-slate-200 rounded-lg px-2 py-1 flex-shrink-0"
              value={t.status}
              onChange={e => handleStatusChange(t._id, e.target.value)}
            >
              {TASK_STATUS_OPTS.map(s => <option key={s}>{s}</option>)}
            </select>
          )}
        </div>
      ))}
    </div>
  );
}

// ─── CLOSE CASE MODAL ──────────────────────────────────────────────────────────
function CloseCaseModal({ caseId, onClose, onClosed }) {
  const [resType, setResType] = useState('Settled');
  const [summary, setSummary] = useState('');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');
  const [agentResult, setAgentResult] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!summary.trim()) { setErr('Please enter a closure summary.'); return; }
    setSaving(true); setErr('');
    try {
      // CaseClosureAgent: archives case, generates AI summary, cancels tasks, creates shared client note
      const res = await runCaseClosureAgent(caseId, resType, summary);
      setAgentResult(res.data);
      onClosed(); // signal parent to reload
    } catch (e) {
      setErr(e?.response?.data?.error || 'Failed to close case.');
    } finally { setSaving(false); }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 backdrop-blur-sm p-4">
      <div className="bg-ivory rounded-2xl shadow-elevated w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h2 className="text-base font-semibold text-ink">Close / Archive Case</h2>
          <button onClick={onClose}><span className="material-symbols-outlined text-graphite">close</span></button>
        </div>
        {agentResult ? (
          <div className="px-6 py-4 space-y-4">
            <div className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-3">
              <span className="material-symbols-outlined text-emerald-600 text-xl mt-0.5">check_circle</span>
              <div>
                <p className="text-sm font-semibold text-emerald-700">Case successfully closed</p>
                <p className="text-xs text-emerald-600 mt-0.5">AI summary generated and shared with the client.</p>
              </div>
            </div>
            {agentResult.case_summary?.timeline_summary && (
              <p className="text-xs text-graphite leading-relaxed border border-slate-100 rounded-xl p-3 bg-white">
                {agentResult.case_summary.timeline_summary}
              </p>
            )}
            {agentResult.stats && (
              <div className="flex gap-4 text-xs text-graphite">
                <span><strong>{agentResult.stats.hearings ?? 0}</strong> hearings</span>
                <span><strong>{agentResult.stats.drafts ?? 0}</strong> drafts</span>
                <span><strong>{agentResult.stats.tasks_cancelled ?? 0}</strong> tasks cancelled</span>
              </div>
            )}
            <div className="flex justify-end">
              <button type="button" onClick={onClose}
                className="px-4 py-2 rounded-xl text-sm font-semibold bg-primary text-white hover:bg-primary-dark transition">Done</button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-graphite mb-1">Resolution Type</label>
              <select className="form-select w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                value={resType} onChange={e => setResType(e.target.value)}>
                {['Settled', 'Disposed', 'Appeal', 'Archived'].map(r => <option key={r}>{r}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-graphite mb-1">Closure Summary</label>
              <textarea className="form-textarea w-full rounded-xl border border-slate-200 px-3 py-2 text-sm resize-none"
                rows={4} placeholder="Brief summary of how the matter concluded…"
                value={summary} onChange={e => setSummary(e.target.value)} />
            </div>
            <p className="text-xs text-graphite/60 flex items-start gap-1">
              <span className="material-symbols-outlined text-sm mt-0.5">info</span>
              The AI will generate a case summary, cancel pending tasks, and notify the client.
            </p>
            {err && <p className="text-xs text-red-600">{err}</p>}
            <div className="flex justify-end gap-2">
              <button type="button" onClick={onClose}
                className="px-4 py-2 rounded-xl text-sm font-medium text-graphite hover:bg-slate-100 transition">Cancel</button>
              <button type="submit" disabled={saving}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold bg-rose-600 text-white hover:bg-rose-700 transition disabled:opacity-50">
                <span className="material-symbols-outlined text-sm">{saving ? 'progress_activity' : 'archive'}</span>
                {saving ? 'Closing…' : 'Close & Archive'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

// ─── DRAFTS TAB ──────────────────────────────────────────────────────────────
function DraftsTab({ caseId, onNewDraft }) {
  const navigate = useNavigate();
  const [drafts, setDrafts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiClient.get('aidrafts/get_user_saved_drafts_v2')
      .then(r => {
        const all = r.data?.saved_drafts ?? [];
        const scoped = all.filter(d =>
          (d.draft_for || []).some(item => (item.case_id || '').trim() === caseId)
        );
        setDrafts(scoped);
      })
      .catch(() => setDrafts([]))
      .finally(() => setLoading(false));
  }, [caseId]);

  function fmtDate(v) {
    if (!v) return '';
    try { return new Date(v).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }); }
    catch { return v; }
  }

  if (loading) return (
    <div className="flex items-center justify-center py-12">
      <span className="material-symbols-outlined animate-spin text-primary text-3xl">progress_activity</span>
    </div>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-semibold text-ink">Case Drafts ({drafts.length})</p>
        <div className="flex items-center gap-2">
          <button onClick={onNewDraft}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-primary text-white hover:bg-primary-dark transition">
            <span className="material-symbols-outlined text-sm">add</span>
            New Draft
          </button>
        </div>
      </div>
      {drafts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center text-graphite/60 gap-3">
          <span className="material-symbols-outlined text-4xl text-primary/20">edit_note</span>
          <p className="text-sm">No drafts for this case yet.</p>
          <button onClick={onNewDraft} className="text-xs text-primary font-medium hover:underline">Start a draft from case context</button>
        </div>
      ) : (
        <div className="space-y-2">
          {drafts.map(d => (
            <button key={d.session_id || d.draft_id} onClick={() => navigate(`/drafting/${d.session_id}`)}
              className="w-full text-left p-3 rounded-xl border border-primary/10 bg-white hover:border-primary/30 hover:shadow-subtle transition-all group">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-ink truncate group-hover:text-primary transition-colors">
                    {d.draft_name || 'Untitled Draft'}
                  </p>
                  <p className="text-[11px] text-graphite/60 mt-0.5">
                    {fmtDate(d.created_at)}
                  </p>
                </div>
                <span className="material-symbols-outlined text-graphite/30 group-hover:text-primary/60 text-base flex-shrink-0">open_in_new</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── DOCUMENTS TAB ────────────────────────────────────────────────────────────────────
function DocumentsTab({ caseId }) {
  const navigate = useNavigate();
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const fileInputRef = useRef(null);

  function fetchDocs() {
    setLoading(true);
    apiClient.get(`talkdoc/documents/?caseid=${caseId}`)
      .then(r => setDocs(r.data?.results ?? r.data?.items ?? r.data ?? []))
      .catch(() => setDocs([]))
      .finally(() => setLoading(false));
  }

  useEffect(() => { fetchDocs(); }, [caseId]);

  async function handleFileChange(e) {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setUploading(true);
    setUploadError('');
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('matter', JSON.stringify({ caseid: [caseId], personal: 'false' }));
        await apiClient.post('talkdoc/upload/', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      }
      fetchDocs();
    } catch (err) {
      setUploadError(err.response?.data?.error || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  }

  if (loading) return <div className="py-8 text-center text-sm text-graphite/50"><span className="material-symbols-outlined animate-spin text-primary text-3xl">progress_activity</span></div>;

  return (
    <div>
      <input ref={fileInputRef} type="file" accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg" multiple className="hidden" onChange={handleFileChange} />
      <div className="flex justify-end gap-2 mb-3">
        <button onClick={() => fileInputRef.current?.click()} disabled={uploading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border border-primary/20 bg-primary/5 text-primary hover:bg-primary/10 transition disabled:opacity-60">
          <span className="material-symbols-outlined text-sm">{uploading ? 'progress_activity' : 'upload'}</span>
          {uploading ? 'Uploading…' : 'Upload'}
        </button>
        <button onClick={() => navigate('/chat')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-primary text-white hover:bg-primary-dark transition">
          <span className="material-symbols-outlined text-sm">chat</span>
          Chat
        </button>
      </div>
      {uploadError && <p className="text-xs text-red-600 mb-2">{uploadError}</p>}
      {docs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center text-graphite/60 gap-3">
          <span className="material-symbols-outlined text-4xl text-primary/20">folder_open</span>
          <p className="text-sm">No documents for this case yet.</p>
          <button onClick={() => fileInputRef.current?.click()} className="text-xs text-primary font-medium hover:underline">Upload a document</button>
        </div>
      ) : docs.map(d => (
        <div key={d.id || d.doc_id}
          className="w-full text-left p-3 rounded-xl border border-primary/10 bg-white mb-2">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-medium text-ink truncate">{d.filename || d.name}</p>
            <span className={`text-[11px] rounded px-1.5 py-0.5 font-semibold flex-shrink-0 ${
              d.indexed ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
            }`}>{d.status || (d.indexed ? 'Indexed' : 'Processing')}</span>
          </div>
          <p className="text-[11px] text-graphite/50 mt-0.5">{d.created_at ? new Date(d.created_at).toLocaleDateString('en-IN') : ''}</p>
        </div>
      ))}
    </div>
  );
}

// ─── CALENDAR TAB ─────────────────────────────────────────────────────────────────────
function CalendarTab({ caseId }) {
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get(`calendar/events/?case_id=${caseId}&upcoming=true`)
      .then(r => setEvents(r.data?.results ?? []))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, [caseId]);

  if (loading) return <div className="py-8 text-center text-sm text-graphite/50"><span className="material-symbols-outlined animate-spin text-primary text-3xl">progress_activity</span></div>;

  return (
    <div>
      <div className="flex justify-end mb-3">
        <button onClick={() => navigate(`/calendar?case_id=${caseId}`)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-primary text-white hover:bg-primary-dark transition">
          <span className="material-symbols-outlined text-sm">add</span>
          Add Event
        </button>
      </div>
      {events.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center text-graphite/60 gap-3">
          <span className="material-symbols-outlined text-4xl text-primary/20">calendar_month</span>
          <p className="text-sm">No upcoming events for this case.</p>
          <button onClick={() => navigate(`/calendar?case_id=${caseId}`)} className="text-xs text-primary font-medium hover:underline">Schedule a hearing</button>
        </div>
      ) : events.map(e => (
        <div key={e.id} className="p-3 rounded-xl border border-primary/10 bg-white mb-2">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-medium text-ink">{e.title}</p>
            <span className="text-[11px] bg-rose-100 text-rose-700 rounded px-1.5 py-0.5 font-semibold flex-shrink-0">{e.eventType || e.Task_type || 'Event'}</span>
          </div>
          <p className="text-[11px] text-graphite/60 mt-0.5">{e.start ? new Date(e.start).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''}</p>
        </div>
      ))}
    </div>
  );
}

// ─── ECOURTS TAB ────────────────────────────────────────────────────────────────────────
function isHCCnr(cnr) {
  return typeof cnr === 'string' && /HC/i.test(cnr.slice(0, 8));
}

function ECourtsTab({ caseId, caseData }) {
  const navigate = useNavigate();
  const [courtType, setCourtType] = useState(() => isHCCnr(caseData.cnr) ? 'HC' : 'DC');
  const [cnrResult, setCnrResult] = useState(null);
  const [cnrLoading, setCnrLoading] = useState(false);
  const [lastChecked, setLastChecked] = useState(null);
  const [ecourtsForm, setEcourtsForm] = useState(caseData.ecourts_params || {});
  const [saving, setSaving] = useState(false);

  async function handleCnrRefresh() {
    setCnrLoading(true);
    try {
      let res;
      if (courtType === 'HC') {
        res = await apiClient.get(`ecourts/v2/hc/case/cnr/${caseData.cnr}/`);
      } else {
        // Use same endpoint as CaseDetail page (case/detail with cnr_number)
        res = await apiClient.post('ecourts/v2/case/detail/', { cnr_number: caseData.cnr });
      }
      setCnrResult(res.data);
      setLastChecked(new Date().toLocaleTimeString('en-IN'));
    } catch (_) {}
    setCnrLoading(false);
  }

  async function handleSaveEcourtsParams() {
    setSaving(true);
    try {
      await updateCase(caseId, { ecourts_params: ecourtsForm });
    } catch (_) {}
    setSaving(false);
  }

  // Auto-fetch CNR status when the tab opens (if CNR is stored on the case)
  useEffect(() => {
    if (caseData.cnr) handleCnrRefresh();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const CourtTypeToggle = () => (
    <div className="inline-flex rounded-lg border border-slate-200 overflow-hidden text-xs font-semibold">
      {['DC', 'HC'].map(type => (
        <button key={type} onClick={() => setCourtType(type)}
          className={`px-3 py-1 transition ${courtType === type ? 'bg-primary text-white' : 'bg-white text-graphite/60 hover:bg-slate-50'}`}>
          {type}
        </button>
      ))}
    </div>
  );

  if (caseData.cnr) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 flex-wrap">
          <CourtTypeToggle />
          <span className="font-mono text-sm bg-slate-100 rounded px-2 py-1">{caseData.cnr}</span>
          {lastChecked && <span className="text-xs text-graphite/50">Last checked: {lastChecked}</span>}
          <button
            onClick={() => navigate(courtType === 'HC' ? `/ecourts/hc/case/${caseData.cnr}` : `/ecourts/case/${caseData.cnr}`)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-primary text-white hover:bg-primary-dark transition ml-auto">
            <span className="material-symbols-outlined text-sm">open_in_new</span>
            Open in eCourts
          </button>
          <button onClick={handleCnrRefresh} disabled={cnrLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border border-primary/20 bg-primary/5 text-primary hover:bg-primary/10 transition disabled:opacity-50">
            <span className={`material-symbols-outlined text-sm${cnrLoading ? ' animate-spin' : ''}`}>refresh</span>
            {cnrLoading ? 'Checking…' : 'Refresh'}
          </button>
        </div>
        {cnrLoading && !cnrResult && (
          <p className="text-xs text-graphite/50">Fetching latest case status…</p>
        )}
        {cnrResult && (
          <div className="p-3 rounded-xl border border-slate-100 bg-ivory text-xs text-graphite whitespace-pre-wrap font-mono max-h-60 overflow-y-auto">
            {JSON.stringify(cnrResult, null, 2).slice(0, 800)}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <CourtTypeToggle />
        <p className="text-xs text-graphite/60">No CNR on record. Save eCourts search parameters to query later, or search directly.</p>
      </div>
      <div className="space-y-2">
        <input className="form-input w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
          placeholder="Search type (e.g. cnr, party, filing)"
          value={ecourtsForm.search_type || ''}
          onChange={e => setEcourtsForm(f => ({ ...f, search_type: e.target.value }))} />
        <input className="form-input w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
          placeholder="Search value"
          value={ecourtsForm.search_value || ''}
          onChange={e => setEcourtsForm(f => ({ ...f, search_value: e.target.value }))} />
      </div>
      <div className="flex gap-2">
        <button onClick={handleSaveEcourtsParams} disabled={saving}
          className="px-3 py-1.5 rounded-xl text-xs font-semibold border border-primary/20 bg-primary/5 text-primary hover:bg-primary/10 disabled:opacity-50 transition">
          {saving ? 'Saving…' : 'Save to Case'}
        </button>
        <button
          onClick={() => navigate(
            courtType === 'HC'
              ? `/ecourts/hc/case-status?q=${encodeURIComponent(ecourtsForm.search_value || '')}`
              : `/ecourts/case-search?q=${encodeURIComponent(ecourtsForm.search_value || '')}`
          )}
          className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-primary text-white hover:bg-primary-dark transition">
          Run Search
        </button>
      </div>
    </div>
  );
}

// ─── CASE HUB ─────────────────────────────────────────────────────────────────────────────
const TABS = [
  { id: 'hearings',  label: 'Hearings',  icon: 'gavel' },
  { id: 'notes',     label: 'Notes',     icon: 'notes' },
  { id: 'tasks',     label: 'Tasks',     icon: 'checklist' },
  { id: 'drafts',    label: 'Drafts',    icon: 'edit_note' },
  { id: 'documents', label: 'Documents', icon: 'folder_open' },
  { id: 'calendar',  label: 'Calendar',  icon: 'calendar_month' },
  { id: 'ecourts',   label: 'eCourts',   icon: 'balance' },
];

export default function CaseHub() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const userType = useSelector(s => s.user.user_type) || 'Lawyer';

  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('hearings');
  const [showClose, setShowClose] = useState(false);
  const [editStage, setEditStage] = useState(false);
  const [stageSaving, setStageSaving] = useState(false);
  const [draftContextLoading, setDraftContextLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const res = await getCase(caseId);
      setCaseData(res.data.case);
    } catch (e) {
      setError(e?.response?.data?.error || 'Failed to load case.');
    } finally { setLoading(false); }
  }, [caseId]);

  useEffect(() => { load(); }, [load]);

  async function handleNewDraft() {
    setDraftContextLoading(true);
    try {
      const res = await runDraftContextAgent(caseId, 'petition');
      const ctx = res.data.draft_context;
      // Navigate to drafting with pre-fill context in router state
      navigate('/drafting', { state: { prefill: ctx, case_id: caseId } });
    } catch (_) {
      // Fall back to plain navigation if agent fails
      navigate(`/drafting?case_id=${caseId}`);
    } finally {
      setDraftContextLoading(false);
    }
  }

  async function handleStageChange(newStage) {
    setStageSaving(true);
    try {
      const res = await updateCase(caseId, { stage: newStage });
      setCaseData(res.data.case);
    } catch (_) {}
    setStageSaving(false);
    setEditStage(false);
  }

  if (loading) return (
    <div className="flex items-center justify-center h-80">
      <span className="material-symbols-outlined animate-spin text-primary text-4xl">progress_activity</span>
    </div>
  );

  if (error) return (
    <div className="max-w-3xl mx-auto py-6 px-2">
      <div className="rounded-xl border border-red-200 bg-red-50 text-red-700 p-4 text-sm">{error}</div>
    </div>
  );

  if (!caseData) return null;

  const isLawyer = userType === 'Lawyer';
  const isClosed = ['Settled', 'Disposed', 'Archived'].includes(caseData.status);

  return (
    <div className="max-w-6xl mx-auto py-4 px-2">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-graphite/60 mb-4">
        <Link to="/cases" className="hover:text-primary transition-colors">Case Registry</Link>
        <span className="material-symbols-outlined text-xs">chevron_right</span>
        <span className="text-ink font-medium truncate">{caseData.title}</span>
      </div>

      {/* Case Header */}
      <div className="bg-ivory rounded-2xl border border-primary/10 shadow-subtle p-5 mb-5">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <StatusBadge status={caseData.status} />
              {caseData.case_type && (
                <span className="text-xs border border-slate-200 rounded px-1.5 py-0.5 text-graphite/70">
                  {caseData.case_type}
                </span>
              )}
            </div>
            <h1 className="text-lg font-semibold text-ink leading-snug">{caseData.title}</h1>
            <button
              onClick={() => navigator.clipboard.writeText(caseData.case_ref || '')}
              title="Copy case reference"
              className="inline-flex items-center gap-1 mt-0.5 text-xs bg-primary/5 border border-primary/15 text-primary/70 rounded px-2 py-0.5 hover:bg-primary/10 transition font-mono cursor-copy"
            >
              {caseData.case_ref || 'MC-????-??????'}
              <span className="material-symbols-outlined text-[11px]">content_copy</span>
            </button>
            {caseData.brief && (
              <p className="text-sm text-graphite/80 mt-2 leading-relaxed">{caseData.brief}</p>
            )}
          </div>

          {/* Quick meta */}
          <div className="flex-shrink-0 text-right space-y-1.5">
            {/* Stage */}
            <div className="flex items-center justify-end gap-1.5 text-xs text-graphite">
              <span className="font-semibold">Stage:</span>
              {isLawyer && !isClosed && editStage ? (
                <select
                  className="form-select text-xs border border-slate-200 rounded-lg px-2 py-0.5"
                  defaultValue={caseData.stage}
                  onChange={e => handleStageChange(e.target.value)}
                  disabled={stageSaving}
                  autoFocus
                  onBlur={() => setEditStage(false)}
                >
                  {STAGE_OPTIONS.map(s => <option key={s}>{s}</option>)}
                </select>
              ) : (
                <button onClick={() => isLawyer && !isClosed && setEditStage(true)}
                  className={`text-primary font-medium ${isLawyer && !isClosed ? 'hover:underline cursor-pointer' : ''}`}>
                  {caseData.stage || '—'}
                </button>
              )}
            </div>
            {caseData.next_hearing && (
              <p className="text-xs text-graphite/70">
                <span className="font-semibold">Next hearing:</span>{' '}
                <span className="text-amber-700">{caseData.next_hearing}</span>
              </p>
            )}
            {caseData.cnr && (
              <p className="text-xs text-graphite/50 font-mono">{caseData.cnr}</p>
            )}
          </div>
        </div>

        {/* Action buttons */}
        {isLawyer && (
          <div className="mt-4 flex flex-wrap gap-2 pt-4 border-t border-slate-100">
            <button
              onClick={() => navigate(`/cases/${caseId}/hearings/new`)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-primary text-white text-xs font-semibold hover:bg-primary-dark transition shadow-subtle"
            >
              <span className="material-symbols-outlined text-sm">gavel</span>
              Prep Hearing
            </button>
            <button
              onClick={handleNewDraft}
              disabled={draftContextLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-primary/30 text-primary text-xs font-semibold hover:bg-primary/5 transition disabled:opacity-60"
            >
              <span className="material-symbols-outlined text-sm">
                {draftContextLoading ? 'progress_activity' : 'edit_note'}
              </span>
              {draftContextLoading ? 'Building context…' : 'New Draft'}
            </button>
            <button
              onClick={() => setActiveTab('documents')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-primary/30 text-primary text-xs font-semibold hover:bg-primary/5 transition"
            >
              <span className="material-symbols-outlined text-sm">description</span>
              Documents
            </button>
            {!isClosed && (
              <button
                onClick={() => setShowClose(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-rose-200 text-rose-600 text-xs font-semibold hover:bg-rose-50 transition ml-auto"
              >
                <span className="material-symbols-outlined text-sm">archive</span>
                Close Case
              </button>
            )}
          </div>
        )}
      </div>

      {/* Tab nav */}
      <div className="flex gap-1 mb-4 bg-ivory rounded-xl border border-primary/10 p-1 shadow-subtle w-fit">
        {TABS.map(tab => (
          <button key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-primary text-white shadow-subtle'
                : 'text-graphite hover:bg-primary/5'
            }`}
          >
            <span className="material-symbols-outlined text-base">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'hearings' && (
          <HearingsTab caseId={caseId} caseData={caseData} userType={userType} />
        )}
        {activeTab === 'notes' && (
          <NotesTab caseId={caseId} userType={userType} />
        )}
        {activeTab === 'tasks' && (
          <TasksTab caseId={caseId} userType={userType} />
        )}
        {activeTab === 'drafts' && (
          <DraftsTab caseId={caseId} onNewDraft={handleNewDraft} />
        )}
        {activeTab === 'documents' && (
          <DocumentsTab caseId={caseId} />
        )}
        {activeTab === 'calendar' && (
          <CalendarTab caseId={caseId} />
        )}
        {activeTab === 'ecourts' && (
          <ECourtsTab caseId={caseId} caseData={caseData} />
        )}
      </div>

      {showClose && (
        <CloseCaseModal
          caseId={caseId}
          onClose={() => setShowClose(false)}
          onClosed={() => { load(); setShowClose(false); }}
        />
      )}
    </div>
  );
}
