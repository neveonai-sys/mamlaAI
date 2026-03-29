import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import {
  addDays,
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  parseISO,
  startOfMonth,
  startOfWeek,
  subMonths,
  addMinutes,
} from 'date-fns';
import apiClient from '../../services/api';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';

const EVENT_TYPE_OPTIONS = [
  'Court Hearing',
  'Client Consultation',
  'Filing Deadline',
  'Deposition',
  'Internal',
];

const MEETING_TYPE_OPTIONS = ['InPerson', 'VideoCall', 'VoiceCall', 'Other'];
const REMINDER_OPTIONS = ['None', 'Email', 'WhatsApp', 'Both'];
const OCCURRENCE_OPTIONS = ['only once', 'this and following', 'entire series'];
const DEFAULT_RENDER_EVENT_DURATION_MINUTES = 60;
const TIME_INPUT_STEP_SECONDS = 900;
const OCCURRENCE_LABELS = {
  'only once': 'Only this event',
  'this and following': 'This and following events',
  'entire series': 'All events in the series',
};

function normalizeTimeToQuarterHour(value) {
  if (!value || !value.includes(':')) return value || '09:00';
  const [hoursText, minutesText] = value.split(':');
  const hours = Number(hoursText);
  const minutes = Number(minutesText);
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return '09:00';
  const totalMinutes = (hours * 60) + minutes;
  const rounded = Math.round(totalMinutes / 15) * 15;
  const normalizedHours = Math.floor((rounded % (24 * 60)) / 60);
  const normalizedMinutes = rounded % 60;
  return `${String(normalizedHours).padStart(2, '0')}:${String(normalizedMinutes).padStart(2, '0')}`;
}

function isSeriesEventShape(event) {
  return Boolean(
    event?.is_series ||
    (Array.isArray(event?.series_key) && event.series_key.length > 1) ||
    Number(event?.series_length || 0) > 1 ||
    (event?.recurring && event?.series_start_date && event?.series_end_date && event.series_start_date !== event.series_end_date)
  );
}

function createEmptyForm(seed = {}) {
  const today = format(new Date(), 'yyyy-MM-dd');
  return {
    id: seed.id || '',
    title: seed.title || '',
    description: seed.description || '',
    startDate: seed.startDate || today,
    endDate: seed.endDate || seed.startDate || today,
    startTime: normalizeTimeToQuarterHour(seed.startTime || '09:00'),
    endTime: normalizeTimeToQuarterHour(seed.endTime || '10:00'),
    allDay: Boolean(seed.allDay),
    eventType: seed.eventType || 'Court Hearing',
    meetingType: seed.meetingType || 'InPerson',
    caseId: seed.caseId || '',
    clientName: seed.clientName || '',
    location: seed.location || '',
    partyBEmail: seed.partyBEmail || '',
    leadCounsel: seed.leadCounsel || '',
    attendeesText: seed.attendeesText || '',
    sendReminder: seed.sendReminder || 'None',
    recurring: Boolean(seed.recurring),
    occurrence: seed.occurrence || 'only once',
    seriesLength: Number(seed.seriesLength || 0),
    isSeries: Boolean(seed.isSeries),
    seriesScopeOptions: Array.isArray(seed.seriesScopeOptions) ? seed.seriesScopeOptions : ['only once'],
    internalNotes: seed.internalNotes || '',
    timezone: seed.timezone || 'Asia/Kolkata',
    conflictStatus: seed.conflictStatus || 'clear',
    resolutionSummary: seed.resolutionSummary || '',
    courtName: seed.courtName || '',
    courtNumber: seed.courtNumber || '',
    judgeName: seed.judgeName || '',
  };
}

function parseDateValue(value) {
  if (!value) return null;
  try {
    return parseISO(value);
  } catch {
    return null;
  }
}

function formatDateLabel(value, pattern = 'MMM dd, yyyy') {
  const parsed = parseDateValue(value);
  return parsed ? format(parsed, pattern) : value || '—';
}

function buildMiniCalendarDays(monthDate) {
  return eachDayOfInterval({
    start: startOfWeek(startOfMonth(monthDate), { weekStartsOn: 0 }),
    end: endOfWeek(endOfMonth(monthDate), { weekStartsOn: 0 }),
  });
}

function getEventTypeMeta(value) {
  const normalized = String(value || '').toLowerCase();
  if (normalized.includes('deadline')) {
    return {
      surface: 'bg-amber-50 border-amber-300 text-amber-900',
      dot: 'bg-amber-500',
      chip: 'bg-amber-100 text-amber-800',
      fcBg: '#fff1db',
      fcBorder: '#d18414',
      fcText: '#8f4c08',
    };
  }
  if (normalized.includes('consult')) {
    return {
      surface: 'bg-sky-50 border-sky-300 text-sky-900',
      dot: 'bg-sky-500',
      chip: 'bg-sky-100 text-sky-800',
      fcBg: '#eaf3ff',
      fcBorder: '#2f6db3',
      fcText: '#1f4f87',
    };
  }
  if (normalized.includes('deposition')) {
    return {
      surface: 'bg-emerald-50 border-emerald-300 text-emerald-900',
      dot: 'bg-emerald-500',
      chip: 'bg-emerald-100 text-emerald-800',
      fcBg: '#e7f5eb',
      fcBorder: '#1f7a43',
      fcText: '#13522d',
    };
  }
  if (normalized.includes('internal')) {
    return {
      surface: 'bg-violet-50 border-violet-300 text-violet-900',
      dot: 'bg-violet-500',
      chip: 'bg-violet-100 text-violet-800',
      fcBg: '#efe9f8',
      fcBorder: '#7652a6',
      fcText: '#54387d',
    };
  }
  if (normalized.includes('court') || normalized.includes('hearing') || normalized.includes('case date')) {
    return {
      surface: 'bg-rose-50 border-rose-300 text-rose-900',
      dot: 'bg-rose-500',
      chip: 'bg-rose-100 text-rose-800',
      fcBg: '#fdebea',
      fcBorder: '#c2342c',
      fcText: '#7c1f1a',
    };
  }
  return {
    surface: 'bg-primary/5 border-primary/20 text-primary',
    dot: 'bg-primary',
    chip: 'bg-primary/10 text-primary',
    fcBg: '#f4ebe2',
    fcBorder: '#b45e08',
    fcText: '#8d4707',
  };
}

function buildDisplayTime(event) {
  if (event.allDay) return 'All day';
  const start = parseDateValue(event.start);
  const end = parseDateValue(event.end);
  if (!start || !end) return 'Time TBD';
  return `${format(start, 'hh:mm a')} - ${format(end, 'hh:mm a')}`;
}

function coerceEventDateTimes(event) {
  const allDay = Boolean(event.allDay);
  const startValue = event.start || (allDay ? event.startdate : `${event.startdate || ''}T${event.starttime || '09:00'}`);
  const endValue = event.end || (allDay ? event.enddate : `${event.enddate || ''}T${event.endtime || event.starttime || '10:00'}`);

  let start = parseDateValue(startValue);
  let end = parseDateValue(endValue);

  if (!start && event.startdate) {
    start = parseDateValue(allDay ? event.startdate : `${event.startdate}T${event.starttime || '09:00'}`);
  }
  if (!end && event.enddate) {
    end = parseDateValue(allDay ? event.enddate : `${event.enddate}T${event.endtime || event.starttime || '10:00'}`);
  }

  if (start && !end) {
    end = allDay ? addDays(start, 1) : addMinutes(start, DEFAULT_RENDER_EVENT_DURATION_MINUTES);
  }
  if (start && end && end <= start) {
    end = allDay ? addDays(start, 1) : addMinutes(start, DEFAULT_RENDER_EVENT_DURATION_MINUTES);
  }

  return {
    start,
    end,
    startText: start ? format(start, allDay ? 'yyyy-MM-dd' : "yyyy-MM-dd'T'HH:mm") : startValue,
    endText: end ? format(end, allDay ? 'yyyy-MM-dd' : "yyyy-MM-dd'T'HH:mm") : endValue,
  };
}

function normalizeEventFromApi(event) {
  const eventType = event.eventType || event.event_type || event.Task_type || event.taskType || 'Court Hearing';
  const meta = getEventTypeMeta(eventType);
  const { start, end, startText, endText } = coerceEventDateTimes(event);
  const isSeries = isSeriesEventShape(event);
  const seriesScopeOptions = Array.isArray(event.series_scope_options) && event.series_scope_options.length > 0
    ? event.series_scope_options
    : isSeries ? OCCURRENCE_OPTIONS : ['only once'];
  return {
    id: event.id,
    title: event.title || 'Untitled event',
    start: startText,
    end: endText,
    allDay: Boolean(event.allDay),
    backgroundColor: meta.fcBg,
    borderColor: meta.fcBorder,
    textColor: meta.fcText,
    extendedProps: {
      ...event,
      start: startText,
      end: endText,
      eventType,
      recurring: Boolean(event.recurring) || isSeries,
      isSeries,
      seriesLength: Number(event.series_length || (Array.isArray(event.series_key) ? event.series_key.length : 0) || (isSeries ? 2 : 1)),
      seriesScopeOptions,
      displayTime: buildDisplayTime({ ...event, start: startText, end: endText }),
      normalizedStart: startText,
      normalizedEnd: endText,
    },
  };
}

function formFromEvent(event) {
  const start = parseDateValue(event.start);
  const end = parseDateValue(event.end);
  const attendeesText = Array.isArray(event.attendees) ? event.attendees.join(', ') : '';
  return createEmptyForm({
    id: event.id,
    title: event.title,
    description: event.description,
    startDate: start ? format(start, 'yyyy-MM-dd') : '',
    endDate: end ? format(end, 'yyyy-MM-dd') : '',
    startTime: event.allDay || !start ? '09:00' : normalizeTimeToQuarterHour(format(start, 'HH:mm')),
    endTime: event.allDay || !end ? '10:00' : normalizeTimeToQuarterHour(format(end, 'HH:mm')),
    allDay: event.allDay,
    eventType: event.eventType || event.event_type || event.Task_type || 'Court Hearing',
    meetingType: event.meetingType || event.meetingtype || 'InPerson',
    caseId: event.caseId || '',
    clientName: event.clientName || '',
    location: event.location || '',
    partyBEmail: event.partyBEmail || '',
    leadCounsel: event.leadCounsel || event.assigned_counsel || '',
    attendeesText,
    sendReminder: event.sendReminder || event.send_remainder || 'None',
    recurring: Boolean(event.recurring) || isSeriesEventShape(event),
    occurrence: event.occurrence || 'only once',
    seriesLength: Number(event.series_length || (Array.isArray(event.series_key) ? event.series_key.length : 0)),
    isSeries: isSeriesEventShape(event),
    seriesScopeOptions: Array.isArray(event.series_scope_options) && event.series_scope_options.length > 0 ? event.series_scope_options : (isSeriesEventShape(event) ? OCCURRENCE_OPTIONS : ['only once']),
    internalNotes: event.internalNotes || '',
    timezone: event.timezone || 'Asia/Kolkata',
    conflictStatus: event.conflict_status || 'clear',
    resolutionSummary: event.resolution_summary || '',
    courtName: event.courtName || '',
    courtNumber: event.courtNumber || '',
    judgeName: event.judgeName || '',
  });
}

function buildPayloadFromForm(form, { includeId = true } = {}) {
  const attendees = form.attendeesText
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);

  const payload = {
    title: form.title.trim(),
    description: form.description.trim(),
    start: form.allDay ? form.startDate : `${form.startDate}T${form.startTime || '09:00'}`,
    end: form.allDay ? form.endDate : `${form.endDate}T${form.endTime || '10:00'}`,
    allDay: Boolean(form.allDay),
    eventType: form.eventType,
    event_type: form.eventType,
    Task_type: form.eventType,
    taskType: form.eventType,
    meetingType: form.meetingType,
    meetingtype: form.meetingType,
    caseId: form.caseId.trim(),
    clientName: form.clientName.trim(),
    location: form.location.trim(),
    partyBEmail: form.partyBEmail.trim(),
    leadCounsel: form.leadCounsel.trim(),
    assigned_counsel: form.leadCounsel.trim(),
    attendees,
    sendReminder: form.sendReminder,
    send_remainder: form.sendReminder,
    recurring: Boolean(form.isSeries || form.recurring || form.endDate > form.startDate),
    occurrence: form.occurrence,
    internalNotes: form.internalNotes.trim(),
    timezone: form.timezone,
    conflict_status: form.conflictStatus,
    resolution_summary: form.resolutionSummary,
    courtName: form.courtName.trim(),
    courtNumber: form.courtNumber.trim(),
    judgeName: form.judgeName.trim(),
  };

  if (includeId && form.id) payload.id = form.id;
  return payload;
}

function validateForm(form) {
  if (!form.title.trim()) return 'Title is required.';
  if (!form.startDate || !form.endDate) return 'Start and end dates are required.';
  if (new Date(form.endDate) < new Date(form.startDate)) return 'End date cannot be before start date.';
  if (!form.allDay && form.startDate === form.endDate) {
    const startValue = Number(form.startTime.slice(0, 2)) * 60 + Number(form.startTime.slice(3, 5));
    const endValue = Number(form.endTime.slice(0, 2)) * 60 + Number(form.endTime.slice(3, 5));
    if (endValue <= startValue) return 'End time must be after start time.';
  }
  if (form.partyBEmail) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/i;
    if (!emailRegex.test(form.partyBEmail)) return 'Party B email is invalid.';
  }
  return '';
}

function buildUpdatedFields(initialForm, nextForm) {
  const mappings = [
    ['title', ['title']],
    ['description', ['description']],
    ['startDate', ['startDate']],
    ['endDate', ['endDate']],
    ['startTime', ['startTime']],
    ['endTime', ['endTime']],
    ['allDay', ['allDay']],
    ['eventType', ['eventType', 'event_type', 'Task_type', 'taskType']],
    ['meetingType', ['meetingType', 'meetingtype']],
    ['caseId', ['caseId']],
    ['clientName', ['clientName']],
    ['location', ['location']],
    ['partyBEmail', ['partyBEmail']],
    ['leadCounsel', ['leadCounsel', 'assigned_counsel']],
    ['attendeesText', ['attendees']],
    ['sendReminder', ['sendReminder', 'send_remainder']],
    ['internalNotes', ['internalNotes']],
    ['timezone', ['timezone']],
    ['courtName', ['courtName']],
    ['courtNumber', ['courtNumber']],
    ['judgeName', ['judgeName']],
    ['recurring', ['recurring']],
  ];

  const updatedFields = [];
  mappings.forEach(([formKey, apiKeys]) => {
    if (initialForm[formKey] !== nextForm[formKey]) {
      apiKeys.forEach((apiKey) => {
        if (!updatedFields.includes(apiKey)) updatedFields.push(apiKey);
      });
    }
  });
  return updatedFields;
}

function cx(...values) {
  return values.filter(Boolean).join(' ');
}

function getConflictSummaryText(report) {
  if (!report) return '';
  const summary = report.summary;
  if (typeof summary === 'string') return summary;
  if (Array.isArray(summary)) return summary.filter(Boolean).join(' ');
  if (summary && typeof summary === 'object') return summary.label || summary.message || summary.start || '';
  return report.has_conflicts ? 'Review recommendations before saving.' : 'No overlaps were detected for this schedule.';
}

function getConflictSlotText(slot) {
  if (!slot) return '';
  if (typeof slot === 'string') return slot;
  if (slot && typeof slot === 'object') return slot.label || [slot.start, slot.end].filter(Boolean).join(' - ');
  return String(slot);
}

function getConflictReasonText(reason) {
  if (!reason) return 'Scheduling conflict detected.';
  if (typeof reason === 'string') return reason;
  if (reason && typeof reason === 'object') return reason.label || reason.message || JSON.stringify(reason);
  return String(reason);
}

function getConflictReasonList(report) {
  const directReasons = Array.isArray(report?.reasons) ? report.reasons : [];
  if (directReasons.length > 0) {
    return directReasons.map(getConflictReasonText);
  }

  const nestedReasons = Array.isArray(report?.conflicts)
    ? report.conflicts.flatMap((conflict) => (Array.isArray(conflict?.reasons) ? conflict.reasons : []))
    : [];

  const deduped = [];
  nestedReasons.map(getConflictReasonText).forEach((reason) => {
    if (reason && !deduped.includes(reason)) {
      deduped.push(reason);
    }
  });
  return deduped;
}

function getConflictDisplayStatus(event) {
  return event?.extendedProps?.conflict_status || event?.extendedProps?.conflictStatus || 'clear';
}

function eventsOverlap(firstEvent, secondEvent) {
  const first = coerceEventDateTimes(firstEvent.extendedProps || firstEvent);
  const second = coerceEventDateTimes(secondEvent.extendedProps || secondEvent);
  if (!first.start || !first.end || !second.start || !second.end) return false;
  return first.start < second.end && second.start < first.end;
}

function deriveConflictEventIds(events) {
  const conflictingIds = new Set();
  for (let index = 0; index < events.length; index += 1) {
    for (let compareIndex = index + 1; compareIndex < events.length; compareIndex += 1) {
      const first = events[index];
      const second = events[compareIndex];
      if (first.allDay || second.allDay) continue;
      if (!eventsOverlap(first, second)) continue;
      conflictingIds.add(first.id);
      conflictingIds.add(second.id);
    }
  }
  return conflictingIds;
}

function buildConflictResolutionText(report) {
  const reasons = getConflictReasonList(report);
  if (reasons.length === 0) return 'Saved despite an overlapping schedule.';
  return `Saved despite conflict: ${reasons.join(', ')}.`;
}

function ModalShell({ open, title, subtitle, children, onClose, width = 'max-w-5xl' }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4 py-6">
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={onClose} />
      <div className={cx('relative w-full overflow-hidden rounded-[28px] border border-primary/10 bg-white shadow-2xl', width)}>
        <div className="border-b border-primary/10 bg-ivory/90 px-6 py-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-primary">Legal Calendar</p>
              <h2 className="mt-1 text-2xl font-black text-ink">{title}</h2>
              {subtitle ? <p className="mt-1 text-sm text-slate-500">{subtitle}</p> : null}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-primary/10 p-2 text-slate-500 transition-colors hover:bg-primary/5 hover:text-primary"
            >
              <span className="material-symbols-outlined text-base">close</span>
            </button>
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}

function Toast({ toast, onClose }) {
  if (!toast.open) return null;
  return (
    <div className="fixed bottom-5 right-5 z-[60] max-w-sm rounded-2xl border border-primary/10 bg-white px-4 py-3 shadow-xl">
      <div className="flex items-start gap-3">
        <div
          className={cx(
            'mt-0.5 flex h-8 w-8 items-center justify-center rounded-full',
            toast.severity === 'error' ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'
          )}
        >
          <span className="material-symbols-outlined text-base">
            {toast.severity === 'error' ? 'error' : 'check_circle'}
          </span>
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-ink">{toast.message}</p>
        </div>
        <button type="button" onClick={onClose} className="text-slate-400 transition-colors hover:text-slate-600">
          <span className="material-symbols-outlined text-base">close</span>
        </button>
      </div>
    </div>
  );
}

function EventField({ label, children, hint }) {
  return (
    <label className="block space-y-2">
      <span className="block text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">{label}</span>
      {children}
      {hint ? <span className="block text-xs text-slate-400">{hint}</span> : null}
    </label>
  );
}

export default function CalendarPage() {
  const calendarRef = useRef(null);
  const dispatch = useDispatch();
  const { firstname, lastname, email, user_type } = useSelector((state) => state.user);
  const fullName = `${firstname || ''} ${lastname || ''}`.trim() || email || 'Lead counsel';
  const readOnly = user_type === 'Client';

  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [checkingConflicts, setCheckingConflicts] = useState(false);
  const [selectedDate, setSelectedDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [miniCalendarDate, setMiniCalendarDate] = useState(new Date());
  const [activeView, setActiveView] = useState('dayGridMonth');
  const [currentRange, setCurrentRange] = useState({
    start: format(startOfMonth(new Date()), 'yyyy-MM-dd'),
    end: format(endOfMonth(new Date()), 'yyyy-MM-dd'),
    label: format(new Date(), 'MMMM yyyy'),
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [visibleTypes, setVisibleTypes] = useState(
    EVENT_TYPE_OPTIONS.reduce((acc, item) => ({ ...acc, [item]: true }), {})
  );
  const [editorOpen, setEditorOpen] = useState(false);
  const [editorMode, setEditorMode] = useState('create');
  const [eventForm, setEventForm] = useState(createEmptyForm({ leadCounsel: fullName }));
  const [initialForm, setInitialForm] = useState(createEmptyForm({ leadCounsel: fullName }));
  const [toast, setToast] = useState({ open: false, severity: 'success', message: '' });
  const [filterData, setFilterData] = useState({
    mappedRows: [],
    casesWithoutClient: [],
    clientsWithoutCase: [],
  });
  const [conflictReport, setConflictReport] = useState(null);
  const [conflictDialogOpen, setConflictDialogOpen] = useState(false);

  const isEditingSeries = editorMode === 'edit' && Boolean(eventForm.isSeries || eventForm.recurring || eventForm.seriesLength > 1);

  const monthlyDays = useMemo(() => buildMiniCalendarDays(miniCalendarDate), [miniCalendarDate]);

  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      const eventType = event.extendedProps.eventType || 'Court Hearing';
      const visible = visibleTypes[eventType] ?? true;
      const haystack = [
        event.title,
        event.extendedProps.caseId,
        event.extendedProps.clientName,
        event.extendedProps.location,
        event.extendedProps.description,
      ]
        .join(' ')
        .toLowerCase();
      return visible && haystack.includes(searchTerm.toLowerCase());
    });
  }, [events, searchTerm, visibleTypes]);

  const conflictEventIds = useMemo(() => deriveConflictEventIds(filteredEvents), [filteredEvents]);

  const agendaEvents = useMemo(() => {
    return filteredEvents
      .filter((event) => String(event.start || '').slice(0, 10) === selectedDate)
      .sort((first, second) => String(first.start).localeCompare(String(second.start)));
  }, [filteredEvents, selectedDate]);

  const upcomingDeadlines = useMemo(() => {
    return filteredEvents
      .filter((event) => String(event.extendedProps.eventType || '').toLowerCase().includes('deadline'))
      .sort((first, second) => String(first.start).localeCompare(String(second.start)))
      .slice(0, 4);
  }, [filteredEvents]);

  const conflictCount = useMemo(() => {
    const explicitConflicts = filteredEvents.filter((event) => getConflictDisplayStatus(event) !== 'clear').map((event) => event.id);
    return new Set([...explicitConflicts, ...conflictEventIds]).size;
  }, [conflictEventIds, filteredEvents]);

  const caseOptions = useMemo(() => {
    return [
      ...filterData.mappedRows.map((row) => row.caseId),
      ...filterData.casesWithoutClient,
    ].filter((value, index, arr) => value && arr.indexOf(value) === index);
  }, [filterData]);

  const clientOptions = useMemo(() => {
    return [
      ...filterData.mappedRows.map((row) => row.clientName),
      ...filterData.clientsWithoutCase,
    ].filter((value, index, arr) => value && arr.indexOf(value) === index);
  }, [filterData]);

  async function withBlocking(message, action) {
    dispatch(beginBlocking({ message }));
    try {
      return await action();
    } finally {
      dispatch(stopBlocking());
    }
  }

  async function fetchEvents(startDate = currentRange.start, endDate = currentRange.end, { blockUi = false } = {}) {
    setLoading(true);
    const load = async () => {
      try {
        const response = await apiClient.get(`calendar/events/?start_date=${startDate}&end_date=${endDate}&page_size=500`);
        const results = Array.isArray(response.data?.results) ? response.data.results : [];
        setEvents(results.map(normalizeEventFromApi));
      } catch {
        setToast({ open: true, severity: 'error', message: 'Unable to load calendar events right now.' });
      } finally {
        setLoading(false);
      }
    };

    if (blockUi) {
      await withBlocking('Loading calendar...', load);
      return;
    }

    await load();
  }

  async function fetchCaseClientData() {
    try {
      const response = await apiClient.get('users/filter_with_details/');
      const data = response.data || {};
      const mappedRows = Object.entries(data.case_client_map || {})
        .filter(([caseId, client]) => caseId && client)
        .map(([caseId, client], index) => ({
          id: `${caseId}-${index}`,
          caseId,
          clientName: `${client.Fname || ''} ${client.Lname || ''}`.trim() || client.email || client.phone_number || '',
          email: client.email || '',
          phone: client.phone_number || '',
        }));

      setFilterData({
        mappedRows,
        casesWithoutClient: data.caseIds_without_client || [],
        clientsWithoutCase: data.clientIds_without_case || [],
      });
    } catch {
      setFilterData({ mappedRows: [], casesWithoutClient: [], clientsWithoutCase: [] });
    }
  }

  useEffect(() => {
    fetchEvents(currentRange.start, currentRange.end, { blockUi: true });
    fetchCaseClientData();
  }, []);

  useEffect(() => {
    if (calendarRef.current && activeView !== 'agenda') {
      calendarRef.current.getApi().changeView(activeView);
    }
  }, [activeView]);

  function pushCalendarDate(date) {
    setSelectedDate(format(date, 'yyyy-MM-dd'));
    setMiniCalendarDate(date);
    if (calendarRef.current && activeView !== 'agenda') {
      calendarRef.current.getApi().gotoDate(date);
    }
  }

  function handleDatesSet(info) {
    const startDate = format(info.view.currentStart, 'yyyy-MM-dd');
    const endDate = format(addDays(info.view.currentEnd, -1), 'yyyy-MM-dd');
    const label = activeView === 'timeGridDay'
      ? format(info.view.currentStart, 'MMMM dd, yyyy')
      : format(info.view.currentStart, 'MMMM yyyy');

    setCurrentRange({ start: startDate, end: endDate, label });
    setMiniCalendarDate(info.view.currentStart);
    fetchEvents(startDate, endDate);
  }

  function openCreateDialog(seed = {}) {
    const nextForm = createEmptyForm({
      leadCounsel: fullName,
      startDate: seed.startDate || format(new Date(), 'yyyy-MM-dd'),
      endDate: seed.endDate || seed.startDate || format(new Date(), 'yyyy-MM-dd'),
      startTime: normalizeTimeToQuarterHour(seed.startTime || '09:00'),
      endTime: normalizeTimeToQuarterHour(seed.endTime || '10:00'),
      allDay: Boolean(seed.allDay),
      recurring: seed.endDate && seed.startDate ? seed.endDate > seed.startDate : false,
      isSeries: seed.endDate && seed.startDate ? seed.endDate > seed.startDate : false,
      seriesLength: seed.endDate && seed.startDate && seed.endDate > seed.startDate ? 2 : 0,
      seriesScopeOptions: ['only once'],
    });
    setEditorMode('create');
    setEventForm(nextForm);
    setInitialForm(nextForm);
    setConflictReport(null);
    setEditorOpen(true);
  }

  function openEditDialog(event) {
    const nextForm = formFromEvent(event);
    setEditorMode('edit');
    setEventForm(nextForm);
    setInitialForm(nextForm);
    setConflictReport(null);
    setEditorOpen(true);
  }

  function handleDateSelect(selectionInfo) {
    setSelectedDate(selectionInfo.startStr.slice(0, 10));
    if (readOnly) return;
    openCreateDialog({
      startDate: selectionInfo.startStr.slice(0, 10),
      endDate: selectionInfo.endStr ? selectionInfo.endStr.slice(0, 10) : selectionInfo.startStr.slice(0, 10),
      startTime: selectionInfo.allDay ? '09:00' : selectionInfo.startStr.split('T')[1]?.slice(0, 5) || '09:00',
      endTime: selectionInfo.allDay ? '10:00' : selectionInfo.endStr?.split('T')[1]?.slice(0, 5) || '10:00',
      allDay: selectionInfo.allDay,
    });
  }

  function handleDateClick(info) {
    setSelectedDate(info.dateStr.slice(0, 10));
  }

  function handleEventClick(info) {
    openEditDialog({ id: info.event.id, title: info.event.title, ...info.event.extendedProps });
  }

  function updateFormField(field, value) {
    const normalizedValue = field === 'startTime' || field === 'endTime'
      ? normalizeTimeToQuarterHour(value)
      : value;
    setEventForm((previous) => ({
      ...previous,
      [field]: normalizedValue,
      recurring: field === 'startDate' || field === 'endDate'
        ? (field === 'startDate' ? previous.endDate > normalizedValue : normalizedValue > previous.startDate)
        : previous.recurring,
      isSeries: field === 'startDate' || field === 'endDate'
        ? (field === 'startDate' ? previous.endDate > normalizedValue : normalizedValue > previous.startDate)
        : previous.isSeries,
      conflictStatus: field === 'conflictStatus' ? value : 'clear',
      resolutionSummary:
        field === 'resolutionSummary'
          ? value
          : field === 'conflictStatus'
            ? previous.resolutionSummary
            : '',
    }));
  }

  function handleCaseSelect(value) {
    const matched = filterData.mappedRows.find((row) => row.caseId === value);
    setEventForm((previous) => ({
      ...previous,
      caseId: value,
      clientName: matched?.clientName || previous.clientName,
      partyBEmail: matched?.email || previous.partyBEmail,
      conflictStatus: 'clear',
      resolutionSummary: '',
    }));
  }

  function handleClientSelect(value) {
    const matched = filterData.mappedRows.find((row) => row.clientName === value);
    setEventForm((previous) => ({
      ...previous,
      clientName: value,
      caseId: matched?.caseId || previous.caseId,
      partyBEmail: matched?.email || previous.partyBEmail,
      conflictStatus: 'clear',
      resolutionSummary: '',
    }));
  }

  async function runConflictCheck(form = eventForm, showDialog = true) {
    setCheckingConflicts(true);
    try {
      const response = await withBlocking('Checking scheduling conflicts...', () => apiClient.post('calendar/conflicts/check/', buildPayloadFromForm(form)));
      const report = response.data;
      setConflictReport(report);
      if (report?.has_conflicts && showDialog) setConflictDialogOpen(true);
      if (!report?.has_conflicts && showDialog) {
        setToast({ open: true, severity: 'success', message: 'No conflicts detected for the selected slot.' });
      }
      return report;
    } catch {
      setToast({ open: true, severity: 'error', message: 'Conflict check failed. Please try again.' });
      return null;
    } finally {
      setCheckingConflicts(false);
    }
  }

  async function persistEvent(form, options = {}) {
    const validationError = validateForm(form);
    if (validationError) {
      setToast({ open: true, severity: 'error', message: validationError });
      return;
    }

    if (!options.skipConflictCheck) {
      const report = await runConflictCheck(form, true);
      if (report?.has_conflicts) return;
    }

    setSaving(true);
    try {
      await withBlocking('Saving calendar event...', async () => {
        const payload = buildPayloadFromForm(form, { includeId: editorMode === 'edit' });
        if (options.allowConflict) {
          payload.conflict_status = 'conflict';
          payload.resolution_summary = buildConflictResolutionText(conflictReport);
        }
        const shouldReloadRange = Boolean(
          form.recurring ||
          form.startDate !== form.endDate ||
          (editorMode === 'edit' && form.occurrence && form.occurrence !== 'only once')
        );
        let response;
        if (editorMode === 'edit' && form.id) {
          if (form.recurring && form.occurrence === 'entire series') {
            response = await apiClient.put(`calendar/events/${form.id}/`, {
              ...payload,
              updatedFields: buildUpdatedFields(initialForm, form),
              occurrence: form.occurrence,
              recurring: form.recurring,
            });
          } else {
            response = await apiClient.put(`calendar/events/${form.id}/`, payload);
          }
        } else {
          response = await apiClient.post('calendar/events/', payload);
        }

        const returnedEvent = response.data?.event;
        if (shouldReloadRange) {
          await fetchEvents(currentRange.start, currentRange.end);
        } else if (returnedEvent) {
          const normalized = normalizeEventFromApi(returnedEvent);
          setEvents((previous) => {
            if (editorMode === 'edit') {
              return previous.map((item) => (item.id === normalized.id ? normalized : item));
            }
            return [...previous, normalized];
          });
        } else {
          fetchEvents();
        }

        setEditorOpen(false);
        setConflictDialogOpen(false);
        setConflictReport(null);
        setToast({
          open: true,
          severity: 'success',
          message: options.allowConflict
            ? (editorMode === 'edit' ? 'Event saved with a conflict flag.' : 'Event created with a conflict flag.')
            : (editorMode === 'edit' ? 'Event updated successfully.' : 'Event created successfully.'),
        });
      });
    } catch (error) {
      setToast({
        open: true,
        severity: 'error',
        message: error.response?.data?.error || 'Unable to save the event right now.',
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!eventForm.id || readOnly) return;
    setSaving(true);
    try {
      await withBlocking('Deleting calendar event...', async () => {
        const shouldReloadRange = Boolean(eventForm.recurring || (eventForm.occurrence && eventForm.occurrence !== 'only once'));
        await apiClient.delete(`calendar/events/${eventForm.id}/`, {
          data: {
            title: eventForm.title,
            partyBEmail: eventForm.partyBEmail,
            occurrence: eventForm.occurrence,
            recurring: eventForm.recurring,
          },
        });
        if (shouldReloadRange) {
          await fetchEvents(currentRange.start, currentRange.end);
        } else {
          setEvents((previous) => previous.filter((item) => item.id !== eventForm.id));
        }
        setEditorOpen(false);
        setToast({ open: true, severity: 'success', message: 'Event deleted successfully.' });
      });
    } catch (error) {
      setToast({
        open: true,
        severity: 'error',
        message: error.response?.data?.error || error.response?.data?.mssg || 'Unable to delete the event.',
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleEventMove(changeInfo) {
    try {
      const movingEvent = {
        id: changeInfo.event.id,
        ...changeInfo.event.extendedProps,
        title: changeInfo.event.title,
        start: changeInfo.event.startStr,
        end: changeInfo.event.endStr,
        allDay: changeInfo.event.allDay,
      };
      await withBlocking('Updating calendar event...', async () => {
        await apiClient.put(`calendar/events/${changeInfo.event.id}/`, movingEvent);
        if (movingEvent.recurring) {
          await fetchEvents(currentRange.start, currentRange.end);
        } else {
          setEvents((previous) =>
            previous.map((item) => (item.id === changeInfo.event.id ? normalizeEventFromApi(movingEvent) : item))
          );
        }
        setToast({ open: true, severity: 'success', message: 'Event timing updated.' });
      });
    } catch {
      changeInfo.revert();
      setToast({ open: true, severity: 'error', message: 'Unable to move the event.' });
    }
  }

  function applyView(view) {
    setActiveView(view);
    if (view !== 'agenda' && calendarRef.current) {
      calendarRef.current.getApi().changeView(view);
    }
  }

  function renderEventContent(eventInfo) {
    return (
      <div className="overflow-hidden px-0.5">
        {!eventInfo.event.allDay ? (
          <div className="text-[10px] font-extrabold opacity-80">{eventInfo.timeText}</div>
        ) : null}
        <div className="truncate text-[11px] font-extrabold">{eventInfo.event.title}</div>
      </div>
    );
  }

  function eventDidMount(info) {
    const meta = getEventTypeMeta(info.event.extendedProps.eventType);
    info.el.style.background = meta.fcBg;
    info.el.style.border = `1px solid ${meta.fcBorder}`;
    info.el.style.color = meta.fcText;
    info.el.style.borderRadius = '12px';
    info.el.style.boxShadow = '0 8px 18px rgba(28, 20, 13, 0.08)';
  }

  return (
    <div className="min-h-full bg-[radial-gradient(circle_at_top_left,_rgba(180,94,8,0.10),_transparent_30%),linear-gradient(180deg,#fbf8f3_0%,#f3ede5_100%)] p-4 sm:p-6 lg:p-8">
      <style>{`
        .legal-calendar .fc { --fc-border-color: rgba(180, 94, 8, 0.12); --fc-page-bg-color: #fffdfa; --fc-neutral-bg-color: rgba(180, 94, 8, 0.05); --fc-list-event-hover-bg-color: rgba(180, 94, 8, 0.08); --fc-today-bg-color: rgba(180, 94, 8, 0.08); }
        .legal-calendar .fc .fc-toolbar.fc-header-toolbar { display: none; }
        .legal-calendar .fc .fc-daygrid-day-top, .legal-calendar .fc .fc-col-header-cell-cushion, .legal-calendar .fc .fc-timegrid-axis-cushion, .legal-calendar .fc .fc-timegrid-slot-label-cushion, .legal-calendar .fc .fc-daygrid-day-number { color: #1c140d; font-weight: 800; text-decoration: none; }
        .legal-calendar .fc .fc-day-other .fc-daygrid-day-number { color: rgba(28, 20, 13, 0.35); }
        .legal-calendar .fc .fc-scrollgrid, .legal-calendar .fc-theme-standard td, .legal-calendar .fc-theme-standard th { border-color: rgba(180, 94, 8, 0.10); }
        .legal-calendar .fc .fc-view-harness { min-height: 680px; }
        .legal-calendar .fc .fc-button { display: none; }
        .legal-calendar .fc .fc-event-title { font-weight: 800; }
      `}</style>

      <Toast toast={toast} onClose={() => setToast((previous) => ({ ...previous, open: false }))} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_minmax(0,1fr)] xl:grid-cols-[300px_minmax(0,1fr)_320px]">
        <aside className="overflow-hidden rounded-[28px] border border-primary/10 bg-[linear-gradient(180deg,#fffdfa_0%,#f7f0e8_100%)] shadow-[0_20px_40px_rgba(49,31,14,0.08)]">
          <div className="flex flex-col gap-6 p-6">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-ivory shadow-lg shadow-primary/20">
                <span className="material-symbols-outlined icon-filled">gavel</span>
              </div>
              <div>
                <h1 className="text-xl font-black text-ink">Mamla.AI</h1>
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-primary">Legal Calendar</p>
              </div>
            </div>

            {!readOnly ? (
              <button
                type="button"
                onClick={() => openCreateDialog({ startDate: selectedDate, endDate: selectedDate })}
                className="btn-primary flex items-center justify-center gap-2 rounded-full py-3 shadow-lg shadow-primary/20"
              >
                <span className="material-symbols-outlined text-base">add</span>
                Create Event
              </button>
            ) : null}

            <section className="rounded-[24px] border border-primary/10 bg-white p-4 shadow-sm">
              <div className="mb-4 flex items-center justify-between gap-3">
                <h2 className="text-sm font-extrabold text-ink">{format(miniCalendarDate, 'MMMM yyyy')}</h2>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setMiniCalendarDate(subMonths(miniCalendarDate, 1))}
                    className="rounded-full border border-primary/10 p-2 text-slate-500 transition-colors hover:bg-primary/5 hover:text-primary"
                  >
                    <span className="material-symbols-outlined text-base">chevron_left</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setMiniCalendarDate(addMonths(miniCalendarDate, 1))}
                    className="rounded-full border border-primary/10 p-2 text-slate-500 transition-colors hover:bg-primary/5 hover:text-primary"
                  >
                    <span className="material-symbols-outlined text-base">chevron_right</span>
                  </button>
                </div>
              </div>

              <div className="mb-2 grid grid-cols-7 gap-1 text-center text-[10px] font-extrabold uppercase tracking-[0.18em] text-slate-400">
                {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((day, index) => (
                  <div key={`${day}-${index}`}>{day}</div>
                ))}
              </div>

              <div className="grid grid-cols-7 gap-1">
                {monthlyDays.map((day) => {
                  const selected = selectedDate === format(day, 'yyyy-MM-dd');
                  const today = isSameDay(day, new Date());
                  return (
                    <button
                      key={day.toISOString()}
                      type="button"
                      onClick={() => pushCalendarDate(day)}
                      className={cx(
                        'h-9 rounded-xl text-sm font-semibold transition-colors',
                        selected ? 'bg-primary text-ivory shadow-sm' : '',
                        !selected && today ? 'bg-primary/10 text-primary' : '',
                        !selected && !today && isSameMonth(day, miniCalendarDate) ? 'text-ink hover:bg-primary/5' : '',
                        !selected && !today && !isSameMonth(day, miniCalendarDate) ? 'text-slate-300 hover:bg-primary/5' : ''
                      )}
                    >
                      {format(day, 'd')}
                    </button>
                  );
                })}
              </div>
            </section>

            <section>
              <div className="mb-3 flex items-center justify-between">
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-500">Case Calendars</p>
              </div>
              <div className="space-y-2">
                {EVENT_TYPE_OPTIONS.map((option) => {
                  const meta = getEventTypeMeta(option);
                  return (
                    <label key={option} className="flex items-center gap-3 rounded-2xl border border-primary/10 bg-white px-3 py-2 text-sm text-ink shadow-sm">
                      <input
                        type="checkbox"
                        checked={visibleTypes[option] ?? true}
                        onChange={(event) => setVisibleTypes((previous) => ({ ...previous, [option]: event.target.checked }))}
                      />
                      <span className={cx('h-2.5 w-2.5 rounded-full', meta.dot)} />
                      <span className="font-semibold">{option}</span>
                    </label>
                  );
                })}
              </div>
            </section>

            <section className="rounded-[24px] border border-ink/10 bg-ink px-4 py-5 text-ivory shadow-[0_18px_30px_rgba(28,20,13,0.20)]">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[#f3b97d]">auto_awesome</span>
                <p className="font-bold">Conflict Intelligence</p>
              </div>
              <p className="mt-3 text-sm leading-6 text-ivory/70">
                {conflictCount > 0
                  ? `${conflictCount} events in this view currently overlap another event.`
                  : 'No unresolved conflicts in the current range.'}
              </p>
            </section>
          </div>
        </aside>

        <section className="overflow-hidden rounded-[28px] border border-primary/10 bg-white shadow-[0_20px_40px_rgba(49,31,14,0.08)]">
          <div className="border-b border-primary/10 bg-white/85 px-6 py-5 backdrop-blur-sm">
            <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="text-3xl font-black tracking-tight text-ink">{currentRange.label}</h2>
                  <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-bold text-primary">
                    {filteredEvents.length} live events
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-500">
                  Hearings, deadlines, and consultations — all in one place.
                </p>
              </div>

              <div className="flex w-full max-w-xl flex-col gap-3">
                <div className="flex items-center gap-3 rounded-full border border-primary/10 bg-primary/5 px-4 py-3">
                  <span className="material-symbols-outlined text-slate-400">search</span>
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(event) => setSearchTerm(event.target.value)}
                    placeholder="Search cases, clients, locations, or notes"
                    className="w-full bg-transparent text-sm text-ink placeholder:text-slate-400 outline-none"
                  />
                </div>

                <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                  <div className="flex flex-wrap gap-2">
                    {[
                      ['dayGridMonth', 'Month'],
                      ['timeGridWeek', 'Week'],
                      ['timeGridDay', 'Day'],
                      ['agenda', 'Agenda'],
                    ].map(([value, label]) => (
                      <button
                        key={value}
                        type="button"
                        onClick={() => applyView(value)}
                        className={cx(
                          'rounded-full px-4 py-2 text-sm font-bold transition-colors',
                          activeView === value ? 'bg-primary text-ivory shadow-sm' : 'bg-primary/5 text-slate-600 hover:bg-primary/10'
                        )}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => pushCalendarDate(new Date())}
                      className="rounded-full border border-primary/10 p-2 text-slate-500 transition-colors hover:bg-primary/5 hover:text-primary"
                    >
                      <span className="material-symbols-outlined text-base">today</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => fetchEvents()}
                      className="rounded-full border border-primary/10 p-2 text-slate-500 transition-colors hover:bg-primary/5 hover:text-primary"
                    >
                      <span className="material-symbols-outlined text-base">refresh</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="p-6">
            <div className="mb-5 grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="rounded-[24px] border border-primary/10 bg-ivory px-5 py-4">
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-500">Hearings & Meetings</p>
                <p className="mt-2 text-3xl font-black text-ink">{filteredEvents.length}</p>
              </div>
              <div className="rounded-[24px] border border-primary/10 bg-ivory px-5 py-4">
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-500">Deadlines</p>
                <p className="mt-2 text-3xl font-black text-amber-700">{upcomingDeadlines.length}</p>
              </div>
              <div className="rounded-[24px] border border-primary/10 bg-ivory px-5 py-4">
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-500">Conflicts</p>
                <p className={cx('mt-2 text-3xl font-black', conflictCount > 0 ? 'text-rose-700' : 'text-emerald-700')}>
                  {conflictCount}
                </p>
              </div>
            </div>

            {activeView === 'agenda' ? (
              <div className="space-y-3">
                {agendaEvents.length === 0 ? (
                  <div className="rounded-[24px] border border-primary/10 bg-ivory px-5 py-6 text-sm text-slate-500">
                    No events scheduled for {formatDateLabel(selectedDate, 'MMMM dd, yyyy')}.
                  </div>
                ) : null}
                {agendaEvents.map((event) => {
                  const meta = getEventTypeMeta(event.extendedProps.eventType);
                  return (
                    <button
                      key={event.id}
                      type="button"
                      onClick={() => openEditDialog({ id: event.id, title: event.title, ...event.extendedProps })}
                      className="w-full rounded-[24px] border border-primary/10 bg-white p-5 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
                    >
                      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                        <div>
                          <p className={cx('inline-flex rounded-full px-3 py-1 text-[11px] font-bold uppercase tracking-[0.18em]', meta.chip)}>
                            {event.extendedProps.eventType}
                          </p>
                          <h3 className="mt-3 text-xl font-bold text-ink">{event.title}</h3>
                          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
                            {event.extendedProps.description || 'No notes captured for this event yet.'}
                          </p>
                        </div>
                        <div className="space-y-2 lg:text-right">
                          <p className={cx('inline-flex rounded-full px-3 py-1 text-xs font-bold', meta.chip)}>
                            {event.extendedProps.displayTime}
                          </p>
                          <p className="text-xs text-slate-500">{event.extendedProps.location || 'Location TBD'}</p>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className={cx('legal-calendar transition-opacity', loading ? 'opacity-60' : 'opacity-100')}>
                <FullCalendar
                  ref={calendarRef}
                  plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
                  initialView={activeView}
                  events={filteredEvents}
                  selectable={!readOnly}
                  editable={!readOnly}
                  eventStartEditable={!readOnly}
                  eventDurationEditable={!readOnly}
                  selectMirror
                  datesSet={handleDatesSet}
                  select={handleDateSelect}
                  dateClick={handleDateClick}
                  eventClick={handleEventClick}
                  eventDrop={handleEventMove}
                  eventResize={handleEventMove}
                  eventContent={renderEventContent}
                  eventDidMount={eventDidMount}
                  headerToolbar={false}
                  height="auto"
                />
              </div>
            )}
          </div>
        </section>

        <aside className="hidden xl:block overflow-hidden rounded-[28px] border border-primary/10 bg-[linear-gradient(180deg,#fffdfa_0%,#f7f0e8_100%)] shadow-[0_20px_40px_rgba(49,31,14,0.08)]">
          <div className="flex h-full flex-col gap-5 p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-500">Agenda Overview</p>
                <h3 className="mt-2 text-2xl font-black text-ink">{formatDateLabel(selectedDate, 'MMM dd, yyyy')}</h3>
              </div>
              <button type="button" className="rounded-full border border-primary/10 p-2 text-slate-500 transition-colors hover:bg-primary/5 hover:text-primary">
                <span className="material-symbols-outlined text-base">notifications_none</span>
              </button>
            </div>

            <div className="space-y-3">
              {agendaEvents.length === 0 ? (
                <div className="rounded-[24px] border border-primary/10 bg-white px-4 py-5 text-sm text-slate-500">
                  No events booked for this date.
                </div>
              ) : null}
              {agendaEvents.slice(0, 5).map((event, index) => {
                const meta = getEventTypeMeta(event.extendedProps.eventType);
                return (
                  <button
                    key={event.id}
                    type="button"
                    onClick={() => openEditDialog({ id: event.id, title: event.title, ...event.extendedProps })}
                    className={cx(
                      'w-full rounded-[22px] border px-4 py-4 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md',
                      meta.surface,
                      index === 0 ? 'ring-2 ring-primary/20' : ''
                    )}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-xs font-black uppercase tracking-[0.18em]">{event.extendedProps.displayTime}</p>
                      <span className="text-[11px] font-semibold opacity-70">{event.extendedProps.location || 'TBD'}</span>
                    </div>
                    <h4 className="mt-3 text-base font-bold">{event.title}</h4>
                    <p className="mt-1 text-sm opacity-80 line-clamp-2">{event.extendedProps.description || event.extendedProps.eventType}</p>
                  </button>
                );
              })}
            </div>

            <div className="border-t border-primary/10 pt-5">
              <div className="flex items-center justify-between gap-3">
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-500">Deadlines</p>
                <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800">
                  {upcomingDeadlines.length} tracked
                </span>
              </div>
              <div className="mt-3 space-y-3">
                {upcomingDeadlines.length === 0 ? (
                  <div className="rounded-[22px] border border-primary/10 bg-white px-4 py-5 text-sm text-slate-500">
                    No urgent deadlines in this view.
                  </div>
                ) : null}
                {upcomingDeadlines.map((event) => (
                  <div key={event.id} className="rounded-[22px] border border-primary/10 bg-white px-4 py-4 shadow-sm">
                    <p className="text-xs font-black uppercase tracking-[0.18em] text-amber-700">
                      {formatDateLabel(event.start, 'MMM dd')} · {event.extendedProps.displayTime}
                    </p>
                    <h4 className="mt-2 text-sm font-bold text-ink">{event.title}</h4>
                    <p className="mt-1 text-xs text-slate-500">{event.extendedProps.caseId || 'General matter'}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </aside>
      </div>

      <ModalShell
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        title={editorMode === 'edit' ? 'Update Event' : 'Create Event'}
        subtitle="Case-aware scheduling with conflict checks and clear series editing controls."
      >
        <div className="max-h-[calc(100vh-180px)] overflow-y-auto custom-scrollbar px-6 py-6">
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.2fr_0.8fr]">
            <div className="space-y-6">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="md:col-span-2">
                  <EventField label="Title">
                    <input
                      type="text"
                      value={eventForm.title}
                      onChange={(event) => updateFormField('title', event.target.value)}
                      placeholder="Case hearing, filing deadline, client consult..."
                      className="input-base"
                    />
                  </EventField>
                </div>

                <EventField label="Event Type">
                  <select value={eventForm.eventType} onChange={(event) => updateFormField('eventType', event.target.value)} className="input-base">
                    {EVENT_TYPE_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </EventField>

                <EventField label="Format">
                  <select value={eventForm.meetingType} onChange={(event) => updateFormField('meetingType', event.target.value)} className="input-base">
                    {MEETING_TYPE_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </EventField>

                <EventField label="Starts">
                  <input type="date" value={eventForm.startDate} onChange={(event) => updateFormField('startDate', event.target.value)} className="input-base" />
                </EventField>

                <EventField label="Ends">
                  <input type="date" value={eventForm.endDate} onChange={(event) => updateFormField('endDate', event.target.value)} className="input-base" />
                </EventField>

                <EventField label="Start Time">
                  <input type="time" step={TIME_INPUT_STEP_SECONDS} value={eventForm.startTime} onChange={(event) => updateFormField('startTime', event.target.value)} className="input-base" disabled={eventForm.allDay} />
                </EventField>

                <EventField label="End Time">
                  <input type="time" step={TIME_INPUT_STEP_SECONDS} value={eventForm.endTime} onChange={(event) => updateFormField('endTime', event.target.value)} className="input-base" disabled={eventForm.allDay} />
                </EventField>

                <label className="flex items-center gap-3 rounded-2xl border border-primary/10 bg-ivory px-4 py-3 text-sm font-semibold text-ink md:col-span-2">
                  <input type="checkbox" checked={eventForm.allDay} onChange={(event) => updateFormField('allDay', event.target.checked)} />
                  All-day event
                </label>

                <EventField label="Case ID">
                  <input list="calendar-case-options" value={eventForm.caseId} onChange={(event) => handleCaseSelect(event.target.value)} className="input-base" placeholder="Select or type a case id" />
                  <datalist id="calendar-case-options">
                    {caseOptions.map((option) => <option key={option} value={option} />)}
                  </datalist>
                </EventField>

                <EventField label="Client Name">
                  <input list="calendar-client-options" value={eventForm.clientName} onChange={(event) => handleClientSelect(event.target.value)} className="input-base" placeholder="Select or type a client" />
                  <datalist id="calendar-client-options">
                    {clientOptions.map((option) => <option key={option} value={option} />)}
                  </datalist>
                </EventField>

                <EventField label="Court Name">
                  <input type="text" value={eventForm.courtName} onChange={(event) => updateFormField('courtName', event.target.value)} className="input-base" placeholder="High Court of Delhi" />
                </EventField>

                <EventField label="Court Number">
                  <input type="text" value={eventForm.courtNumber} onChange={(event) => updateFormField('courtNumber', event.target.value)} className="input-base" placeholder="Court 4" />
                </EventField>

                <EventField label="Judge Name">
                  <input type="text" value={eventForm.judgeName} onChange={(event) => updateFormField('judgeName', event.target.value)} className="input-base" placeholder="Justice Sharma" />
                </EventField>

                <EventField label="Assigned Counsel">
                  <input type="text" value={eventForm.leadCounsel} onChange={(event) => updateFormField('leadCounsel', event.target.value)} className="input-base" placeholder="Lead counsel" />
                </EventField>

                <EventField label="Location">
                  <input type="text" value={eventForm.location} onChange={(event) => updateFormField('location', event.target.value)} className="input-base" placeholder="Court room or meeting location" />
                </EventField>

                <EventField label="Participants">
                  <input type="email" value={eventForm.partyBEmail} onChange={(event) => updateFormField('partyBEmail', event.target.value)} className="input-base" placeholder="opposing.counsel@example.com" />
                </EventField>

                <EventField label="Reminder">
                  <select value={eventForm.sendReminder} onChange={(event) => updateFormField('sendReminder', event.target.value)} className="input-base">
                    {REMINDER_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </EventField>

                <EventField label="Attendees" hint="Separate multiple attendees with commas.">
                  <input type="text" value={eventForm.attendeesText} onChange={(event) => updateFormField('attendeesText', event.target.value)} className="input-base" placeholder="Client, junior counsel, clerk" />
                </EventField>

                {isEditingSeries ? (
                  <EventField label="This Event Or Series" hint="Choose how broadly to apply this change.">
                    <select value={eventForm.occurrence} onChange={(event) => updateFormField('occurrence', event.target.value)} className="input-base">
                      {(eventForm.seriesScopeOptions || OCCURRENCE_OPTIONS).map((option) => (
                        <option key={option} value={option}>{OCCURRENCE_LABELS[option] || option}</option>
                      ))}
                    </select>
                  </EventField>
                ) : (
                  <div className="rounded-2xl border border-primary/10 bg-ivory px-4 py-3 text-sm text-slate-600 md:col-span-2">
                    If the end date is later than the start date, Mamla creates one linked event per day automatically. When you later edit one of those events, you can choose whether the change applies just to that date, that date and everything after it, or the full series.
                  </div>
                )}

                <div className="md:col-span-2">
                  <EventField label="Description">
                    <textarea value={eventForm.description} onChange={(event) => updateFormField('description', event.target.value)} rows={4} className="input-base" placeholder="Add hearing notes, prep items, or required documents" />
                  </EventField>
                </div>

                <div className="md:col-span-2">
                  <EventField label="Internal Notes">
                    <textarea value={eventForm.internalNotes} onChange={(event) => updateFormField('internalNotes', event.target.value)} rows={3} className="input-base" placeholder="Internal reminders, case prep items, or staffing notes" />
                  </EventField>
                </div>
              </div>
            </div>

            <div className="space-y-5">
              <div className="rounded-[24px] border border-primary/10 bg-[radial-gradient(circle_at_top_left,_rgba(180,94,8,0.08),_transparent_40%),#fcfaf8] p-5">
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-primary">Preview</p>
                <h3 className="mt-3 text-xl font-black text-ink">{eventForm.title || 'Untitled matter'}</h3>
                <p className="mt-2 text-sm text-slate-500">{formatDateLabel(eventForm.startDate, 'MMM dd, yyyy')} · {eventForm.allDay ? 'All day' : `${eventForm.startTime} to ${eventForm.endTime}`}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <span className={cx('rounded-full px-3 py-1 text-xs font-bold', getEventTypeMeta(eventForm.eventType).chip)}>
                    {eventForm.eventType}
                  </span>
                  {(eventForm.isSeries || eventForm.endDate > eventForm.startDate) ? <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800">Daily series</span> : null}
                  {eventForm.caseId ? <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-bold text-primary">Case {eventForm.caseId}</span> : null}
                  {eventForm.clientName ? <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">{eventForm.clientName}</span> : null}
                </div>
              </div>

              <div className="rounded-[24px] border border-primary/10 bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-500">Conflict Check</p>
                    <h3 className="mt-2 text-lg font-black text-ink">Check for scheduling conflicts</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-500">Checks the selected time against existing events, assigned counsel, and overlapping case commitments before you save.</p>
                  </div>
                  <span className="material-symbols-outlined text-primary">shield</span>
                </div>

                <button type="button" onClick={() => runConflictCheck()} disabled={checkingConflicts} className="btn-primary mt-4 w-full rounded-xl py-3">
                  {checkingConflicts ? 'Checking…' : 'Check Conflicts'}
                </button>

                {conflictReport ? (
                  <div className={cx(
                    'mt-4 rounded-2xl border px-4 py-4 text-sm',
                    conflictReport.has_conflicts ? 'border-rose-200 bg-rose-50 text-rose-900' : 'border-emerald-200 bg-emerald-50 text-emerald-900'
                  )}>
                    <p className="font-bold">{conflictReport.has_conflicts ? 'Conflicts detected' : 'Schedule is clear'}</p>
                    <p className="mt-2 leading-6">
                      {getConflictSummaryText(conflictReport)}
                    </p>
                  </div>
                ) : null}
              </div>

              {eventForm.resolutionSummary ? (
                <div className="rounded-[24px] border border-emerald-200 bg-emerald-50 p-5 text-sm text-emerald-900">
                  <p className="font-bold">Suggested resolution</p>
                  <p className="mt-2 leading-6">{eventForm.resolutionSummary}</p>
                </div>
              ) : null}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-primary/10 bg-ivory/80 px-6 py-4">
          <div className="flex items-center gap-3">
            {editorMode === 'edit' && !readOnly ? (
              <button type="button" onClick={handleDelete} disabled={saving} className="rounded-xl border border-rose-200 bg-white px-4 py-2.5 text-sm font-semibold text-rose-700 transition-colors hover:bg-rose-50 disabled:opacity-50">
                Delete Event
              </button>
            ) : null}
          </div>
          <div className="flex items-center gap-3">
            <button type="button" onClick={() => setEditorOpen(false)} className="btn-ghost">
              Cancel
            </button>
            {!readOnly ? (
              <button type="button" onClick={() => persistEvent(eventForm)} disabled={saving} className="btn-primary rounded-xl px-5 py-2.5">
                {saving ? 'Saving…' : editorMode === 'edit' ? 'Save Changes' : 'Create Event'}
              </button>
            ) : null}
          </div>
        </div>
      </ModalShell>

      <ModalShell
        open={conflictDialogOpen}
        onClose={() => setConflictDialogOpen(false)}
        title="Scheduling Conflict"
        subtitle="This slot overlaps existing events. Adjust the date or time manually, then run the conflict check again."
        width="max-w-3xl"
      >
        <div className="px-6 py-6">
          <div className="rounded-[24px] border border-rose-200 bg-rose-50 p-5">
            <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-rose-700">Detected Issues</p>
            <div className="mt-3 space-y-2 text-sm text-rose-900">
              {getConflictReasonList(conflictReport).length > 0 ? (
                getConflictReasonList(conflictReport).map((reason, index) => (
                  <div key={`${reason}-${index}`} className="rounded-xl bg-white/70 px-4 py-3">{reason}</div>
                ))
              ) : (
                <div className="rounded-xl bg-white/70 px-4 py-3">The selected slot conflicts with existing scheduling constraints.</div>
              )}
            </div>
          </div>

          <div className="mt-5 rounded-[24px] border border-primary/10 bg-white p-5 text-sm text-slate-600 shadow-sm">
            <p className="font-bold text-ink">What to do next</p>
            <p className="mt-2 leading-6">Update the event timing yourself in the form, then run the conflict check again. Mamla will not auto-reschedule or reassign this event right now.</p>
          </div>

          {conflictReport?.recommendations ? (
            <div className="mt-5 rounded-[24px] border border-primary/10 bg-ivory p-5 text-sm text-slate-600">
              <p className="font-bold text-ink">Backend recommendations</p>
              {conflictReport.recommendations.next_available_slot ? (
                <p className="mt-2">Suggested slot: {getConflictSlotText(conflictReport.recommendations.next_available_slot)}</p>
              ) : null}
            </div>
          ) : null}

          <div className="mt-5 flex flex-wrap justify-end gap-3">
            {!readOnly ? (
              <button
                type="button"
                onClick={() => persistEvent({ ...eventForm, conflictStatus: 'conflict', resolutionSummary: buildConflictResolutionText(conflictReport) }, { skipConflictCheck: true, allowConflict: true })}
                disabled={saving}
                className="rounded-xl border border-rose-200 bg-white px-5 py-2.5 text-sm font-semibold text-rose-700 transition-colors hover:bg-rose-50 disabled:opacity-50"
              >
                {saving ? 'Saving…' : 'Save Anyway'}
              </button>
            ) : null}
            <button type="button" onClick={() => setConflictDialogOpen(false)} className="btn-primary rounded-xl px-5 py-2.5">
              Continue Editing
            </button>
          </div>
        </div>
      </ModalShell>
    </div>
  );
}