import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import apiClient from '../../services/api';
import {
  getCase,
  getHearingNote,
  createHearingNote,
  updateHearingNote,
  createCaseTask,
  runHearingPrepAgent,
  runPostHearingAgent,
} from '../../services/casesApi';

function BriefSection({ title, icon, items, color = 'primary' }) {
  const [open, setOpen] = useState(true);
  if (!items || items.length === 0) return null;

  const colorMap = {
    primary:  'border-primary/20 bg-primary/5 text-primary',
    amber:    'border-amber-200 bg-amber-50 text-amber-800',
    emerald:  'border-emerald-200 bg-emerald-50 text-emerald-800',
    rose:     'border-rose-200 bg-rose-50 text-rose-700',
    violet:   'border-violet-200 bg-violet-50 text-violet-800',
  };

  return (
    <div className={`rounded-xl border ${colorMap[color]} mb-3`}>
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
      >
        <span className="flex items-center gap-2 text-sm font-semibold">
          <span className="material-symbols-outlined text-base icon-filled">{icon}</span>
          {title}
        </span>
        <span className="material-symbols-outlined text-base">{open ? 'expand_less' : 'expand_more'}</span>
      </button>
      {open && (
        <ul className="px-4 pb-3 space-y-1.5">
          {items.map((item, i) => (
            <li key={i} className="text-sm flex items-start gap-2">
              <span className="mt-1 h-1.5 w-1.5 rounded-full bg-current flex-shrink-0" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ChecklistItem({ text, checked, onChange }) {
  return (
    <label className="flex items-start gap-2.5 p-2 rounded-lg hover:bg-white/60 cursor-pointer transition-colors">
      <input type="checkbox" checked={checked} onChange={onChange}
        className="mt-0.5 h-4 w-4 rounded border-slate-300 text-primary cursor-pointer flex-shrink-0" />
      <span className={`text-sm ${checked ? 'line-through text-graphite/40' : 'text-ink'}`}>{text}</span>
    </label>
  );
}

export default function HearingWorkspace() {
  const { caseId, hearingId } = useParams();
  const navigate = useNavigate();
  const isNew = hearingId === 'new';

  const [caseData, setCaseData] = useState(null);
  const [hearingNote, setHearingNote] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // New hearing form (only shown when hearingId === 'new')
  const [newForm, setNewForm] = useState({ hearing_date: '', purpose: '', type: 'prep' });
  const [creating, setCreating] = useState(false);

  // Outcome recording
  const [outcomeText, setOutcomeText] = useState('');
  const [nextDate, setNextDate] = useState('');
  const [savingOutcome, setSavingOutcome] = useState(false);
  const [outcomeSaved, setOutcomeSaved] = useState(false);

  // Checklist state (from ai_brief.checklist)
  const [checklist, setChecklist] = useState([]);

  // AI Brief generation
  const [generatingBrief, setGeneratingBrief] = useState(false);
  const [briefError, setBriefError] = useState('');

  // Post-hearing agent
  const [runningPostAgent, setRunningPostAgent] = useState(false);
  const [agentTasks, setAgentTasks] = useState([]);
  const [agentError, setAgentError] = useState('');

  // P3-4: calendar event suggestion after outcome is saved with a next date
  const [calendarCreating, setCalendarCreating] = useState(false);
  const [calendarCreated, setCalendarCreated] = useState(false);

  // Task generation
  const [taskTitle, setTaskTitle] = useState('');
  const [addingTask, setAddingTask] = useState(false);
  const [taskAdded, setTaskAdded] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [caseRes] = await Promise.all([getCase(caseId)]);
      setCaseData(caseRes.data.case);

      if (!isNew) {
        const noteRes = await getHearingNote(caseId, hearingId);
        const note = noteRes.data.hearing_note;
        setHearingNote(note);
        if (note.outcome) setOutcomeText(note.outcome);
        if (note.next_date) setNextDate(note.next_date);
        // Hydrate checklist
        const items = note.ai_brief?.checklist || [];
        setChecklist(items.map(text => ({ text, checked: false })));
      }
    } catch (e) {
      setError(e?.response?.data?.error || 'Failed to load hearing.');
    } finally {
      setLoading(false);
    }
  }, [caseId, hearingId, isNew]);

  useEffect(() => { load(); }, [load]);

  async function handleCreate(e) {
    e.preventDefault();
    if (!newForm.hearing_date) return;
    setCreating(true);
    try {
      const res = await createHearingNote(caseId, newForm);
      const note = res.data.hearing_note;
      navigate(`/cases/${caseId}/hearings/${note._id}`, { replace: true });
    } catch (e) {
      setError(e?.response?.data?.error || 'Failed to create hearing record.');
    } finally {
      setCreating(false);
    }
  }

  async function handleGenerateBrief() {
    if (!hearingNote) return;
    setGeneratingBrief(true);
    setBriefError('');
    try {
      const res = await runHearingPrepAgent(
        caseId,
        hearingNote.hearing_date,
        hearingNote.purpose || 'general hearing preparation',
      );
      // Agent creates a new note — reload to get the stored ai_brief
      const noteRes = await getHearingNote(caseId, res.data.note_id || hearingNote._id);
      const updated = noteRes.data.hearing_note;
      setHearingNote(updated);
      const items = updated.ai_brief?.checklist || [];
      setChecklist(items.map(text => ({ text, checked: false })));
    } catch (e) {
      setBriefError(e?.response?.data?.error || 'Failed to generate brief. Please try again.');
    } finally {
      setGeneratingBrief(false);
    }
  }

  async function handleSaveOutcome(e) {
    e.preventDefault();
    if (!hearingNote) return;
    setSavingOutcome(true);
    setAgentError('');
    try {
      // Save outcome via direct update first
      const res = await updateHearingNote(caseId, hearingNote._id, {
        outcome: outcomeText,
        next_date: nextDate,
      });
      setHearingNote(res.data.hearing_note);
      setOutcomeSaved(true);
      setTimeout(() => setOutcomeSaved(false), 3000);
    } catch (_) {}
    setSavingOutcome(false);
  }

  async function handleSaveOutcomeWithAgent(e) {
    e.preventDefault();
    if (!hearingNote || !outcomeText.trim()) return;
    setRunningPostAgent(true);
    setAgentError('');
    setAgentTasks([]);
    try {
      const res = await runPostHearingAgent(
        caseId,
        hearingNote._id,
        outcomeText,
        nextDate,
      );
      const data = res.data;
      setAgentTasks(data.tasks_created || []);
      setOutcomeSaved(true);
      setTimeout(() => setOutcomeSaved(false), 4000);
      // Reload to reflect updated note
      const noteRes = await getHearingNote(caseId, hearingNote._id);
      setHearingNote(noteRes.data.hearing_note);
    } catch (e) {
      setAgentError(e?.response?.data?.error || 'Agent failed. Outcome was not saved.');
    } finally {
      setRunningPostAgent(false);
    }
  }

  async function handleCreateCalendarEvent() {
    if (!nextDate) return;
    setCalendarCreating(true);
    try {
      const title = `Court Hearing — ${caseData?.title || 'Case'}`;
      await apiClient.post('calendar/events/', {
        title,
        description: hearingNote?.purpose || '',
        start: nextDate,
        end: nextDate,
        allDay: true,
        eventType: 'Court Hearing',
        event_type: 'Court Hearing',
        Task_type: 'Court Hearing',
        taskType: 'Court Hearing',
        caseId,
        sendReminder: true,
        send_remainder: true,
      });
      setCalendarCreated(true);
    } catch (_) {}
    setCalendarCreating(false);
  }

  async function handleAddTask(e) {
    e.preventDefault();
    if (!taskTitle.trim()) return;
    setAddingTask(true);
    try {
      await createCaseTask(caseId, {
        title: taskTitle.trim(),
        source: 'manual',
        priority: 'Medium',
      });
      setTaskTitle('');
      setTaskAdded(true);
      setTimeout(() => setTaskAdded(false), 3000);
    } catch (_) {}
    setAddingTask(false);
  }

  function toggleChecklist(i) {
    setChecklist(prev => prev.map((item, idx) => idx === i ? { ...item, checked: !item.checked } : item));
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

  const brief = hearingNote?.ai_brief || {};

  return (
    <div className="max-w-4xl mx-auto py-4 px-2">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-graphite/60 mb-4">
        <Link to="/cases" className="hover:text-primary transition-colors">Case Registry</Link>
        <span className="material-symbols-outlined text-xs">chevron_right</span>
        <Link to={`/cases/${caseId}`} className="hover:text-primary transition-colors truncate max-w-xs">
          {caseData?.title || caseId}
        </Link>
        <span className="material-symbols-outlined text-xs">chevron_right</span>
        <span className="text-ink font-medium">
          {isNew ? 'New Hearing' : (hearingNote?.hearing_date || 'Hearing')}
        </span>
      </div>

      {/* ── NEW HEARING FORM ─────────────────────────────────────────────── */}
      {isNew ? (
        <div className="bg-ivory rounded-2xl border border-primary/10 shadow-subtle p-6">
          <h1 className="text-base font-semibold text-ink mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">gavel</span>
            Create Hearing Record
          </h1>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-graphite mb-1">Hearing Date *</label>
                <input type="date" className="form-input w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                  value={newForm.hearing_date}
                  onChange={e => setNewForm(f => ({ ...f, hearing_date: e.target.value }))} required />
              </div>
              <div>
                <label className="block text-xs font-semibold text-graphite mb-1">Entry Type</label>
                <select className="form-select w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                  value={newForm.type} onChange={e => setNewForm(f => ({ ...f, type: e.target.value }))}>
                  <option value="prep">Prep (before hearing)</option>
                  <option value="outcome">Outcome (after hearing)</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-graphite mb-1">Purpose / Agenda</label>
              <input className="form-input w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                placeholder="e.g. Arguments on injunction application, Cross-examination of PW-1"
                value={newForm.purpose}
                onChange={e => setNewForm(f => ({ ...f, purpose: e.target.value }))} />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => navigate(`/cases/${caseId}`)}
                className="px-4 py-2 rounded-xl text-sm font-medium text-graphite hover:bg-slate-100 transition">
                Cancel
              </button>
              <button type="submit" disabled={creating}
                className="px-4 py-2 rounded-xl text-sm font-semibold bg-primary text-white hover:bg-primary-dark disabled:opacity-50 transition">
                {creating ? 'Creating…' : 'Create & Open'}
              </button>
            </div>
          </form>
        </div>
      ) : (
        /* ── EXISTING HEARING ── */
        <div className="space-y-5">
          {/* Header */}
          <div className="bg-ivory rounded-2xl border border-primary/10 shadow-subtle p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs font-semibold rounded-full px-2.5 py-0.5 ${
                    hearingNote?.type === 'prep' ? 'bg-sky-100 text-sky-700' : 'bg-emerald-100 text-emerald-700'
                  }`}>{hearingNote?.type === 'prep' ? 'Prep' : 'Outcome'}</span>
                </div>
                <h1 className="text-lg font-semibold text-ink">
                  {hearingNote?.hearing_date}
                </h1>
                {hearingNote?.purpose && (
                  <p className="text-sm text-graphite/70 mt-0.5">{hearingNote.purpose}</p>
                )}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* LEFT: AI Brief */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-ink flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-base icon-filled">auto_awesome</span>
                  AI Brief
                </h2>
                {Object.keys(brief).length === 0 && (
                  <button
                    onClick={handleGenerateBrief}
                    disabled={generatingBrief}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-primary text-white hover:bg-primary-dark disabled:opacity-60 transition"
                  >
                    <span className="material-symbols-outlined text-sm">
                      {generatingBrief ? 'progress_activity' : 'auto_awesome'}
                    </span>
                    {generatingBrief ? 'Generating…' : 'Generate AI Brief'}
                  </button>
                )}
                {Object.keys(brief).length > 0 && (
                  <button
                    onClick={handleGenerateBrief}
                    disabled={generatingBrief}
                    className="flex items-center gap-1 text-xs text-graphite/50 hover:text-primary transition disabled:opacity-40"
                  >
                    <span className="material-symbols-outlined text-sm">refresh</span>
                    {generatingBrief ? 'Regenerating…' : 'Regenerate'}
                  </button>
                )}
              </div>

              {briefError && (
                <div className="rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs px-3 py-2 mb-3">{briefError}</div>
              )}

              {generatingBrief && Object.keys(brief).length === 0 && (
                <div className="rounded-xl border border-primary/10 bg-primary/5 p-6 text-center text-sm text-primary/70">
                  <span className="material-symbols-outlined animate-spin text-3xl block mb-2">progress_activity</span>
                  Pulling eCourts history, past notes, and documents…
                </div>
              )}

              {!generatingBrief && Object.keys(brief).length === 0 && !briefError && (
                <div className="rounded-xl border border-dashed border-slate-200 p-6 text-center text-sm text-graphite/50">
                  <span className="material-symbols-outlined text-3xl text-primary/30 block mb-2">auto_awesome</span>
                  Click "Generate AI Brief" to prepare for this hearing.
                </div>
              )}

              {Object.keys(brief).length > 0 && (
                <>
                  {brief.summary && (
                    <div className="rounded-xl border border-primary/10 bg-primary/5 text-primary text-xs px-4 py-2.5 mb-3">
                      {brief.summary}
                    </div>
                  )}
                  <BriefSection title="Applicable Law"       icon="balance"          items={brief.applicable_law}      color="primary" />
                  <BriefSection title="Arguments to Raise"  icon="record_voice_over" items={brief.arguments_for}       color="emerald" />
                  <BriefSection title="Watch Points"         icon="warning"          items={brief.watch_points}        color="amber" />
                  <BriefSection title="Suggested Questions"  icon="quiz"             items={brief.suggested_questions} color="violet" />

                  {brief.checklist && brief.checklist.length > 0 && (
                    <div className="rounded-xl border border-slate-200 bg-ivory mt-3">
                      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-100 text-sm font-semibold text-ink">
                        <span className="material-symbols-outlined text-base text-primary">checklist</span>
                        Checklist
                      </div>
                      <div className="p-2">
                        {checklist.map((item, i) => (
                          <ChecklistItem key={i} text={item.text} checked={item.checked}
                            onChange={() => toggleChecklist(i)} />
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* RIGHT: Outcome + Tasks */}
            <div className="space-y-5">
              {/* Outcome */}
              <div className="bg-ivory rounded-xl border border-primary/10 shadow-subtle p-4">
                <h2 className="text-sm font-semibold text-ink mb-3 flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-base">edit_note</span>
                  {hearingNote?.type === 'prep' ? 'Notes' : 'Outcome'}
                </h2>
                <form className="space-y-3">
                  <textarea
                    className="form-textarea w-full rounded-xl border border-slate-200 px-3 py-2 text-sm resize-none"
                    rows={5}
                    placeholder={hearingNote?.type === 'prep'
                      ? "Write pre-hearing notes, strategy, points to remember…"
                      : "What happened in court today? Orders passed, arguments heard, next steps…"}
                    value={outcomeText}
                    onChange={e => setOutcomeText(e.target.value)}
                  />
                  <div>
                    <label className="block text-xs font-semibold text-graphite mb-1">Next Hearing Date</label>
                    <input type="date" className="form-input w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                      value={nextDate} onChange={e => setNextDate(e.target.value)} />
                  </div>

                  {agentError && (
                    <div className="rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs px-3 py-2">{agentError}</div>
                  )}

                  {agentTasks.length > 0 && (
                    <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3">
                      <p className="text-xs font-semibold text-emerald-700 mb-1.5 flex items-center gap-1">
                        <span className="material-symbols-outlined text-sm">task_alt</span>
                        {agentTasks.length} follow-up task{agentTasks.length > 1 ? 's' : ''} created
                      </p>
                      <ul className="space-y-0.5">
                        {agentTasks.map((t, i) => (
                          <li key={i} className="text-xs text-emerald-800 flex items-start gap-1.5">
                            <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-emerald-500 flex-shrink-0" />
                            {t.title} <span className="text-emerald-500">({t.priority})</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* P3-4: Calendar suggestion — shown when next date set & outcome saved */}
                  {nextDate && outcomeSaved && !calendarCreated && (
                    <div className="rounded-xl border border-sky-200 bg-sky-50 p-3 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2 text-sm text-sky-700">
                        <span className="material-symbols-outlined text-base">calendar_month</span>
                        <span>Add <strong>{nextDate}</strong> as a court hearing reminder?</span>
                      </div>
                      <button type="button" onClick={handleCreateCalendarEvent} disabled={calendarCreating}
                        className="flex-shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-semibold bg-sky-600 text-white hover:bg-sky-700 disabled:opacity-50 transition">
                        <span className="material-symbols-outlined text-sm">add</span>
                        {calendarCreating ? 'Adding…' : 'Add to Calendar'}
                      </button>
                    </div>
                  )}
                  {calendarCreated && (
                    <p className="text-xs text-sky-600 flex items-center gap-1">
                      <span className="material-symbols-outlined text-sm">check_circle</span>
                      Calendar event created for {nextDate}
                    </p>
                  )}

                  <div className="flex items-center justify-end gap-2">
                    {outcomeSaved && (
                      <span className="text-xs text-emerald-600 flex items-center gap-1">
                        <span className="material-symbols-outlined text-sm">check_circle</span> Saved
                      </span>
                    )}
                    {/* Quick save — no agent */}
                    <button type="button" onClick={handleSaveOutcome} disabled={savingOutcome}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border border-primary/30 text-primary hover:bg-primary/5 disabled:opacity-50 transition">
                      <span className="material-symbols-outlined text-sm">save</span>
                      {savingOutcome ? 'Saving…' : 'Save'}
                    </button>
                    {/* Save + run PostHearingAgent */}
                    <button type="button" onClick={handleSaveOutcomeWithAgent}
                      disabled={runningPostAgent || !outcomeText.trim()}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-primary text-white hover:bg-primary-dark disabled:opacity-50 transition">
                      <span className="material-symbols-outlined text-sm">
                        {runningPostAgent ? 'progress_activity' : 'auto_awesome'}
                      </span>
                      {runningPostAgent ? 'Processing…' : 'Save + Generate Tasks'}
                    </button>
                  </div>
                </form>
              </div>

              {/* Quick task */}
              <div className="bg-ivory rounded-xl border border-primary/10 shadow-subtle p-4">
                <h2 className="text-sm font-semibold text-ink mb-3 flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-base">add_task</span>
                  Quick Task
                </h2>
                <form onSubmit={handleAddTask} className="flex gap-2">
                  <input
                    className="form-input flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm"
                    placeholder="e.g. File reply by Friday"
                    value={taskTitle} onChange={e => setTaskTitle(e.target.value)}
                  />
                  <button type="submit" disabled={addingTask || !taskTitle.trim()}
                    className="flex-shrink-0 px-3 py-2 rounded-xl text-xs font-semibold bg-primary/10 text-primary hover:bg-primary/20 transition disabled:opacity-50">
                    {addingTask ? '…' : 'Add'}
                  </button>
                </form>
                {taskAdded && (
                  <p className="mt-1.5 text-xs text-emerald-600 flex items-center gap-1">
                    <span className="material-symbols-outlined text-sm">check_circle</span> Task added to case.
                  </p>
                )}
                <p className="mt-2 text-[11px] text-graphite/50">
                  Tasks appear in the <Link to={`/cases/${caseId}`} className="text-primary hover:underline">case Tasks tab</Link>.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
