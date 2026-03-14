import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import apiClient from '../../services/api';
import { updateFeatureQuota } from '../../features/entitlementsSlice';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';

const TALKDOC_ACCEPT = '.pdf,.doc,.docx,.txt,.csv,.xlsx,.png,.jpg,.jpeg,.webp,.bmp,.gif,.tif,.tiff';

function quotaNoticeClassName(tone) {
  if (tone === 'error') return 'border-red-200 bg-red-50 text-red-700';
  if (tone === 'warning') return 'border-amber-200 bg-amber-50 text-amber-800';
  return 'border-sky-200 bg-sky-50 text-sky-700';
}

function getTalkdocFeatureMeta(featureCode) {
  if (featureCode === 'general_legal_chat') {
    return {
      label: 'General legal chat',
      blockedMessage: 'General legal chat is exhausted for now. Add wallet credits or wait for reset to continue.',
      unavailableMessage: 'General legal chat is not available for this account right now.',
      unitSingular: 'chat',
      unitPlural: 'chats',
    };
  }

  return {
    label: 'Document analysis',
    blockedMessage: 'Mamla Brain usage is exhausted for now. Add wallet credits to continue document analysis.',
    unavailableMessage: 'Mamla Brain access is not available for this account right now.',
    unitSingular: 'analysis',
    unitPlural: 'analyses',
  };
}

function buildBrainQuotaNotice(quota, featureCode = 'brain_doc_analysis') {
  if (!quota) return null;

  const remaining = typeof quota.remaining_included === 'number' ? quota.remaining_included : null;
  const walletBalance = typeof quota.wallet_credits_balance === 'number' ? quota.wallet_credits_balance : 0;
  const sessionTurnsRemaining = typeof quota.session_turns_remaining === 'number' ? quota.session_turns_remaining : null;
  const sessionTurnLimit = typeof quota.session_turn_limit === 'number' ? quota.session_turn_limit : null;
  const meta = getTalkdocFeatureMeta(featureCode);

  if (quota.allowed === false) {
    return {
      tone: 'error',
      message: quota.next_cta === 'top_up_credits'
        ? meta.blockedMessage
        : meta.unavailableMessage,
    };
  }

  if (sessionTurnsRemaining !== null && sessionTurnLimit !== null) {
    if (sessionTurnsRemaining <= 2) {
      return {
        tone: 'warning',
        message: `${sessionTurnsRemaining} of ${sessionTurnLimit} included session ${sessionTurnsRemaining === 1 ? 'chat' : 'chats'} left before the next ${meta.label.toLowerCase()} charge${walletBalance ? `, plus ${walletBalance} wallet credit${walletBalance === 1 ? '' : 's'}` : ''}.`,
      };
    }

    if (sessionTurnsRemaining === sessionTurnLimit - 1) {
      return {
        tone: 'info',
        message: `This ${meta.label.toLowerCase()} charge now covers up to ${sessionTurnLimit} chats in the current session.`,
      };
    }
  }

  if (remaining !== null && remaining <= 2) {
    return {
      tone: 'warning',
      message: `${remaining} included ${meta.label.toLowerCase()} ${remaining === 1 ? meta.unitSingular : meta.unitPlural} left${walletBalance ? `, plus ${walletBalance} wallet credit${walletBalance === 1 ? '' : 's'}` : ''}.`,
    };
  }

  return null;
}

function nowTimestampString() {
  return new Date().toISOString().replace('T', ' ').replace('Z', '');
}

function normalizeDoc(doc) {
  const status = doc.status || (doc.indexed ? 'indexed' : 'uploaded');
  return {
    ...doc,
    id: doc.id || doc.doc_id,
    doc_id: doc.doc_id || doc.id,
    name: doc.name || doc.filename || doc.name_original || 'Document',
    filename: doc.filename || doc.name || doc.name_original || 'Document',
    status,
    indexed: status === 'indexed' || Boolean(doc.indexed),
    ingest_stage: doc.ingest_stage || (status === 'indexed' ? 'indexed' : status),
    matter: doc.matter || {},
    preview_url: doc.preview_url || '',
    created_at: doc.created_at || '',
    updated_at: doc.updated_at || '',
    mimetype: doc.mimetype || 'application/octet-stream',
    error: doc.error || '',
  };
}

function normalizeSession(session) {
  return {
    ...session,
    id: session.id || session.session_id,
    title: session.title || 'Untitled chat',
    doc_ids: session.doc_ids || [],
    doc_count: session.doc_count ?? (session.doc_ids || []).length,
    has_docs: Boolean(session.has_docs || (session.doc_ids || []).length),
    matter: session.matter || {},
    created_at: session.created_at || '',
    last_message_at: session.last_message_at || '',
  };
}

function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function buildMatter(caseId, clientId) {
  const matter = {};
  const cleanCaseId = caseId.trim();
  const cleanClientId = clientId.trim();
  if (cleanCaseId) matter.caseid = [cleanCaseId];
  if (cleanClientId) matter.clientid = [cleanClientId];
  if (cleanCaseId || cleanClientId) matter.personal = 'false';
  return matter;
}

function formatMatterLabel(matter) {
  const caseId = Array.isArray(matter?.caseid) ? matter.caseid[0] : matter?.caseid;
  const clientId = Array.isArray(matter?.clientid) ? matter.clientid[0] : matter?.clientid;
  if (caseId && clientId) return `Case ${caseId} · Client ${clientId}`;
  if (caseId) return `Case ${caseId}`;
  if (clientId) return `Client ${clientId}`;
  return 'General legal chat';
}

function getClientLabel(client) {
  if (!client || typeof client !== 'object') return '';
  const first = client.Fname || client.fname || '';
  const last = client.Lname || client.lname || '';
  const phone = client.phone_number || client.phonenumber || '';
  const email = client.email || '';
  const label = [first, last].filter(Boolean).join(' ').trim();
  if (label && phone) return `${label} · ${phone}`;
  if (label && email) return `${label} · ${email}`;
  return label || phone || '';
}

function getClientValue(client) {
  if (!client) return '';
  if (typeof client === 'string') return client.trim();
  const directId = client.client_id || client.clientid || client.id || client.user_id || '';
  if (directId) return String(directId).trim();
  const phone = client.phone_number || client.phonenumber || client.phone || '';
  if (phone) return String(phone).trim();
  const email = client.email || '';
  if (email) return String(email).trim();
  return [client.Fname || client.fname || '', client.Lname || client.lname || ''].filter(Boolean).join(' ').trim();
}

function buildClientOption(client) {
  const value = getClientValue(client);
  const label = getClientLabel(client);
  return {
    value,
    label,
    displayValue: label || value,
  };
}

function getClientName(client) {
  const option = buildClientOption(client);
  return option.displayValue || 'Unnamed';
}

function getDocStatusMeta(doc) {
  if (doc.status === 'indexed') {
    return { label: 'Indexed', tone: 'bg-emerald-100 text-emerald-700 border-emerald-200' };
  }
  if (doc.status === 'failed') {
    return { label: 'Failed', tone: 'bg-red-100 text-red-700 border-red-200' };
  }
  if (['extracting', 'chunking', 'embedding', 'indexing', 'processing'].includes(doc.ingest_stage || doc.status)) {
    return { label: 'Processing', tone: 'bg-sky-100 text-sky-700 border-sky-200' };
  }
  return { label: 'Queued', tone: 'bg-amber-100 text-amber-700 border-amber-200' };
}

function TalkDocContextSelector({ rows, selectedRowId, onSelectRow, onAddCustomRow, onClearSelection }) {
  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-3">
        <label className="block text-sm font-semibold text-slate-700">Case / Client Context</label>
        <div className="flex items-center gap-2">
          <button type="button" className="rounded-lg border border-primary/10 px-3 py-2 text-xs font-semibold text-slate-600 transition-colors hover:bg-primary/5" onClick={onAddCustomRow}>
            Add Entry
          </button>
          <button type="button" className="rounded-lg border border-primary/10 px-3 py-2 text-xs font-semibold text-slate-600 transition-colors hover:bg-primary/5" onClick={onClearSelection}>
            General
          </button>
        </div>
      </div>
      <div className="overflow-hidden rounded-xl border border-primary/10 bg-white">
        <div className="grid grid-cols-[44px_1fr_1fr] gap-0 border-b border-primary/10 bg-ivory/70 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
          <div className="py-3" />
          <div className="px-3 py-3">Case ID</div>
          <div className="px-3 py-3">Client</div>
        </div>
        <div className="max-h-64 overflow-y-auto custom-scrollbar divide-y divide-primary/10">
          {rows.map((row) => (
            <label key={row.id} className="grid cursor-pointer grid-cols-[44px_1fr_1fr] gap-0 items-center hover:bg-primary/5">
              <span className="flex items-center justify-center py-3">
                <input
                  type="radio"
                  name="talkdoc-context-row"
                  checked={selectedRowId === row.id}
                  onChange={() => onSelectRow(row.id)}
                />
              </span>
              <span className="px-3 py-3 text-sm text-slate-700">{row.case_id || '-'}</span>
              <span className="px-3 py-3 text-sm text-slate-700">{row.client_name || '-'}</span>
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

function SetupWindow({
  docs,
  sessions,
  docSearch,
  onDocSearchChange,
  sessionQuery,
  onSessionQueryChange,
  contextRows,
  selectedContextRowId,
  onSelectContextRow,
  onAddCustomContextRow,
  onClearContextSelection,
  composerSelectedDocIds,
  onToggleComposerDoc,
  onUpload,
  uploading,
  onDeleteDoc,
  deletingDocId,
  onCreateSession,
  onOpenSession,
  onDeleteSession,
  onStartRename,
  onCommitRename,
  onCancelRename,
  renamingSessionId,
  renameValue,
  onRenameValueChange,
  caseOptions,
  docFilterCaseId,
  docFilterClientId,
  onDocFilterCaseIdChange,
  onDocFilterClientIdChange,
  docFilterClientOptions,
  onClearDocFilters,
  onResetComposer,
}) {
  return (
    <div className="min-h-full bg-[radial-gradient(circle_at_top_left,_rgba(180,94,8,0.08),_transparent_32%),linear-gradient(180deg,#fcfaf8_0%,#f6f1ea_100%)]">
      <div className="mx-auto flex w-full max-w-[1600px] flex-col px-4 py-6 sm:px-6 lg:px-8">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-primary">Talk To Docs</p>
            <h1 className="mt-2 text-3xl font-bold text-ink">Document Intelligence &amp; Q&amp;A</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Start here to upload or delete documents, set case or client context, and reopen or remove older chats before entering the focused work window.
            </p>
          </div>
          <button
            type="button"
            onClick={onResetComposer}
            className="rounded-xl border border-primary/15 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition-colors hover:bg-primary/5"
          >
            New Session Setup
          </button>
        </div>

        <div className="mb-6 rounded-[24px] border border-primary/10 bg-white/90 p-5 shadow-[0_18px_60px_rgba(28,20,13,0.06)] backdrop-blur-sm">
          <div className="grid gap-4 xl:grid-cols-[1.6fr_auto]">
            <TalkDocContextSelector
              rows={contextRows}
              selectedRowId={selectedContextRowId}
              onSelectRow={onSelectContextRow}
              onAddCustomRow={onAddCustomContextRow}
              onClearSelection={onClearContextSelection}
            />
            <div className="flex items-end">
              <button
                type="button"
                onClick={onCreateSession}
                className="w-full rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-ivory shadow-sm transition-colors hover:bg-primary/90 xl:w-auto"
              >
                Enter Work Window
              </button>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            {composerSelectedDocIds.length === 0 && (
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">No documents selected yet</span>
            )}
            {composerSelectedDocIds.map((docId) => {
              const doc = docs.find((item) => item.doc_id === docId);
              return (
                <button
                  key={docId}
                  type="button"
                  onClick={() => onToggleComposerDoc(docId)}
                  className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary transition-colors hover:bg-primary/15"
                >
                  {doc?.filename || doc?.name || `Document ${docId.slice(-4)}`}
                </button>
              );
            })}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="flex min-h-[640px] flex-col">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h2 className="text-xl font-semibold text-ink">Document Library</h2>
              <label className="inline-flex cursor-pointer items-center justify-center rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-ivory transition-colors hover:bg-primary/90">
                {uploading ? 'Uploading…' : 'Upload Documents'}
                <input type="file" multiple className="hidden" accept={TALKDOC_ACCEPT} onChange={onUpload} />
              </label>
            </div>

            <div className="flex flex-1 flex-col overflow-hidden rounded-[24px] border border-primary/10 bg-white shadow-sm">
              <div className="border-b border-primary/10 bg-ivory/80 px-4 py-3">
                <div className="flex flex-wrap items-center gap-3">
                  <input
                    value={docSearch}
                    onChange={(event) => onDocSearchChange(event.target.value)}
                    placeholder="Search uploaded documents"
                    className="min-w-[14rem] flex-1 rounded-xl border border-primary/10 bg-white px-3 py-2.5 text-sm text-ink placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                  <input
                    list="talkdoc-doc-filter-case-options"
                    value={docFilterCaseId}
                    onChange={(event) => onDocFilterCaseIdChange(event.target.value)}
                    placeholder="Filter by case"
                    className="min-w-[10rem] rounded-xl border border-primary/10 bg-white px-3 py-2.5 text-sm text-ink placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                  <datalist id="talkdoc-doc-filter-case-options">
                    {caseOptions.map((option) => (
                      <option key={option.value} value={option.value} label={option.label} />
                    ))}
                  </datalist>
                  <input
                    list="talkdoc-doc-filter-client-options"
                    value={docFilterClientId}
                    onChange={(event) => onDocFilterClientIdChange(event.target.value)}
                    placeholder="Filter by client"
                    className="min-w-[10rem] rounded-xl border border-primary/10 bg-white px-3 py-2.5 text-sm text-ink placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                  <datalist id="talkdoc-doc-filter-client-options">
                    {docFilterClientOptions.map((option) => (
                      <option key={option.value} value={option.value} label={option.label} />
                    ))}
                  </datalist>
                  {(docFilterCaseId || docFilterClientId) && (
                    <button
                      type="button"
                      onClick={onClearDocFilters}
                      className="rounded-xl border border-primary/10 bg-white px-3 py-2.5 text-xs font-semibold text-slate-600 transition-colors hover:bg-primary/5"
                    >
                      Clear Filters
                    </button>
                  )}
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-500">
                    {docs.length} total docs
                  </span>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
                <div className="grid gap-3 md:grid-cols-2">
                  {docs.map((doc) => {
                    const isSelected = composerSelectedDocIds.includes(doc.doc_id);
                    const meta = getDocStatusMeta(doc);
                    return (
                      <div
                        key={doc.doc_id}
                        className={`rounded-2xl border p-4 transition-colors ${
                          isSelected ? 'border-primary/30 bg-primary/5' : 'border-primary/10 bg-white hover:border-primary/20'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase ${meta.tone}`}>
                              {meta.label}
                            </span>
                            <p className="mt-2 line-clamp-2 text-sm font-semibold text-ink">{doc.filename || doc.name}</p>
                            {doc.original_name && doc.original_name !== (doc.filename || doc.name) && (
                              <p className="mt-1 text-[11px] text-slate-500">Original: {doc.original_name}</p>
                            )}
                            {doc.matter && (doc.matter.caseid || doc.matter.clientid) && (
                              <p className="mt-1 text-[11px] text-slate-500">{formatMatterLabel(doc.matter)}</p>
                            )}
                            <p className="mt-1 text-[11px] text-slate-500">Updated {formatDate(doc.updated_at || doc.created_at)}</p>
                            {doc.error && <p className="mt-2 text-[11px] text-red-600">{doc.error}</p>}
                          </div>
                        </div>

                        <div className="mt-4 flex gap-2">
                          <button
                            type="button"
                            onClick={() => onToggleComposerDoc(doc.doc_id)}
                            className={`flex-1 rounded-xl px-3 py-2 text-xs font-semibold transition-colors ${
                              isSelected
                                ? 'bg-primary text-ivory'
                                : 'border border-primary/10 bg-slate-50 text-slate-700 hover:bg-primary/5'
                            }`}
                          >
                            {isSelected ? 'Selected' : 'Use In Session'}
                          </button>
                          <button
                            type="button"
                            onClick={() => onDeleteDoc(doc.doc_id)}
                            disabled={deletingDocId === doc.doc_id}
                            className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-600 transition-colors hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {deletingDocId === doc.doc_id ? 'Deleting…' : 'Delete'}
                          </button>
                        </div>
                      </div>
                    );
                  })}

                  {docs.length === 0 && (
                    <div className="rounded-2xl border border-dashed border-primary/15 bg-ivory/70 p-8 text-center text-sm text-slate-500 md:col-span-2">
                      No documents match the current search.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </section>

          <section className="flex min-h-[640px] flex-col">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h2 className="text-xl font-semibold text-ink">Saved Chats</h2>
              <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">Delete and rename from here</span>
            </div>

            <div className="flex flex-1 flex-col overflow-hidden rounded-[24px] border border-primary/10 bg-white shadow-sm">
              <div className="border-b border-primary/10 bg-ivory/80 px-4 py-3">
                <input
                  value={sessionQuery}
                  onChange={(event) => onSessionQueryChange(event.target.value)}
                  placeholder="Search old chats"
                  className="w-full rounded-xl border border-primary/10 bg-white px-3 py-2.5 text-sm text-ink placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div className="flex-1 overflow-y-auto p-4 custom-scrollbar space-y-3">
                {sessions.map((session) => (
                  <div key={session.id} className="rounded-2xl border border-primary/10 bg-white p-4 transition-colors hover:border-primary/20">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        {renamingSessionId === session.id ? (
                          <input
                            value={renameValue}
                            onChange={(event) => onRenameValueChange(event.target.value)}
                            onBlur={() => onCommitRename(session.id)}
                            onKeyDown={(event) => {
                              if (event.key === 'Enter') onCommitRename(session.id);
                              if (event.key === 'Escape') onCancelRename();
                            }}
                            autoFocus
                            className="w-full rounded-lg border border-primary/15 bg-ivory px-2.5 py-2 text-sm font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-primary/20"
                          />
                        ) : (
                          <button type="button" onClick={() => onOpenSession(session.id)} className="w-full text-left">
                            <p className="line-clamp-2 text-sm font-semibold text-ink">{session.title}</p>
                          </button>
                        )}
                        <p className="mt-1 text-[11px] text-slate-500">{formatMatterLabel(session.matter)}</p>
                        <p className="mt-1 text-[11px] text-slate-400">Updated {formatDate(session.last_message_at || session.created_at)}</p>
                      </div>
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold text-slate-500">
                        {session.doc_count || 0} docs
                      </span>
                    </div>

                    <div className="mt-4 flex gap-2">
                      <button
                        type="button"
                        onClick={() => onOpenSession(session.id)}
                        className="flex-1 rounded-xl bg-[#1c2433] px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-[#27324a]"
                      >
                        Open
                      </button>
                      <button
                        type="button"
                        onClick={() => onStartRename(session)}
                        className="rounded-xl border border-primary/10 px-3 py-2 text-xs font-semibold text-slate-600 transition-colors hover:bg-primary/5"
                      >
                        Rename
                      </button>
                      <button
                        type="button"
                        onClick={() => onDeleteSession(session.id)}
                        className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-600 transition-colors hover:bg-red-100"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}

                {sessions.length === 0 && (
                  <div className="rounded-2xl border border-dashed border-primary/15 bg-ivory/70 p-8 text-center text-sm text-slate-500">
                    No saved chats match the current search.
                  </div>
                )}
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function DocumentViewer({ sessionDocs, previewDoc, previewUrl, previewLoading, previewError, onSelectDoc, onBackToSetup, onOpenPreview, onUpload, uploading }) {
  return (
    <section className="flex h-full min-h-0 flex-col" data-purpose="document-viewer-section">
      <h2 className="mb-3 text-xl font-semibold text-ink">Document Viewer</h2>
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-primary/10 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-primary/10 bg-[#1c2433] px-4 py-3 text-white">
          <div className="flex items-center gap-3 min-w-0">
            <button type="button" onClick={onBackToSetup} className="rounded-lg p-2 text-slate-300 transition-colors hover:bg-white/10 hover:text-white">
              <span className="material-symbols-outlined text-lg">arrow_back</span>
            </button>
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold">{previewDoc?.filename || previewDoc?.name || 'No document selected'}</div>
              <div className="text-xs text-slate-300">{previewDoc ? 'Focused reading window' : 'Choose a document from this chat session'}</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="hidden max-w-[24rem] items-center gap-2 overflow-x-auto rounded-xl bg-white/5 px-2 py-1 md:flex">
              {sessionDocs.map((doc) => (
                <button
                  key={doc.doc_id}
                  type="button"
                  onClick={() => onSelectDoc(doc.doc_id)}
                  className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                    previewDoc?.doc_id === doc.doc_id ? 'bg-white text-[#1c2433]' : 'text-slate-200 hover:bg-white/10'
                  }`}
                >
                  {doc.filename || doc.name}
                </button>
              ))}
            </div>
            {previewDoc && (
              <button
                type="button"
                onClick={onOpenPreview}
                className="rounded-lg bg-white/10 px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-white/20"
              >
                Open
              </button>
            )}
            <label className="inline-flex cursor-pointer items-center justify-center rounded-lg bg-white/10 px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-white/20">
              {uploading ? 'Uploading…' : 'Upload To Chat'}
              <input type="file" multiple className="hidden" accept={TALKDOC_ACCEPT} onChange={onUpload} />
            </label>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto bg-ivory p-6 custom-scrollbar">
          <div className="mx-auto flex min-h-full w-full max-w-5xl flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-[0_18px_45px_rgba(28,20,13,0.08)]">
            {!previewDoc && (
              <div className="flex min-h-[32rem] items-center justify-center p-8 text-center text-sm text-slate-500">
                This session does not have a selected document yet.
              </div>
            )}
            {previewDoc && previewLoading && (
              <div className="flex min-h-[32rem] items-center justify-center p-8 text-sm text-slate-500">Loading preview…</div>
            )}
            {previewDoc && !previewLoading && previewError && (
              <div className="flex min-h-[32rem] items-center justify-center p-8 text-center text-sm text-slate-500">{previewError}</div>
            )}
            {previewDoc && !previewLoading && !previewError && previewDoc.mimetype?.includes('pdf') && previewUrl && (
              <iframe title={previewDoc.filename || previewDoc.name} src={previewUrl} className="min-h-[48rem] w-full flex-1 border-0 bg-white" />
            )}
            {previewDoc && !previewLoading && !previewError && previewDoc.mimetype?.startsWith('image/') && previewUrl && (
              <div className="flex min-h-[32rem] items-center justify-center bg-[#f4efe9] p-6">
                <img src={previewUrl} alt={previewDoc.filename || previewDoc.name} className="max-h-[48rem] max-w-full rounded-lg object-contain shadow-sm" />
              </div>
            )}
            {previewDoc && !previewLoading && !previewError && !previewDoc.mimetype?.includes('pdf') && !previewDoc.mimetype?.startsWith('image/') && (
              <div className="flex min-h-[32rem] items-center justify-center p-8 text-center text-sm text-slate-500">
                Inline preview is optimized for PDFs. Use Open for this file type.
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function ChatWindow({
  activeSession,
  messages,
  input,
  onInputChange,
  onSend,
  chatLoading,
  onDeleteSession,
  onStartRename,
  renamingSessionId,
  renameValue,
  onRenameValueChange,
  onCommitRename,
  onCancelRename,
  onJumpToCitation,
  quotaNotice,
  sendDisabled,
  sendPlaceholder,
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, chatLoading]);

  return (
    <section className="flex h-full min-h-0 flex-col" data-purpose="chat-interface-section">
      <h2 className="mb-3 text-xl font-semibold text-ink">Chat with Documents</h2>
      <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-primary/10 bg-white shadow-sm">
        <div className="z-10 flex items-center justify-between gap-3 border-b border-primary/10 bg-white px-4 py-3">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-[#1c2433] text-xs text-[#e6b75c]">M</div>
            <div className="min-w-0">
              {renamingSessionId === activeSession?.id ? (
                <input
                  value={renameValue}
                  onChange={(event) => onRenameValueChange(event.target.value)}
                  onBlur={() => onCommitRename(activeSession.id)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') onCommitRename(activeSession.id);
                    if (event.key === 'Escape') onCancelRename();
                  }}
                  autoFocus
                  className="w-full rounded-lg border border-primary/15 bg-ivory px-2.5 py-1.5 text-sm font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              ) : (
                <div className="truncate font-semibold text-ink">{activeSession?.title || 'Multi-Document RAG Q&A'}</div>
              )}
              <div className="truncate text-xs text-slate-500">{formatMatterLabel(activeSession?.matter)}</div>
            </div>
          </div>
          <div className="flex items-center gap-2 text-slate-500">
            <button type="button" onClick={() => onStartRename(activeSession)} className="rounded-lg p-2 transition-colors hover:bg-primary/5 hover:text-primary">
              <span className="material-symbols-outlined text-lg">edit_square</span>
            </button>
            <button type="button" onClick={() => onDeleteSession(activeSession?.id)} className="rounded-lg p-2 transition-colors hover:bg-red-50 hover:text-red-600">
              <span className="material-symbols-outlined text-lg">delete</span>
            </button>
          </div>
        </div>

        {quotaNotice && (
          <div className={`border-b px-4 py-3 text-xs font-medium ${quotaNoticeClassName(quotaNotice.tone)}`}>
            {quotaNotice.message}
          </div>
        )}

        <div className="flex flex-1 flex-col overflow-y-auto bg-white p-4 custom-scrollbar">
          {messages.length === 0 && (
            <div className="mb-6 max-w-[85%] self-start rounded-2xl rounded-tl-none border border-slate-100 bg-slate-50 px-5 py-4 text-sm text-slate-700 shadow-sm">
              <div className="mb-1 text-sm font-semibold text-ink">Mamla.AI</div>
              Ask about the selected documents in this chat. Citation chips will point back to the source document when available.
            </div>
          )}

          {messages.map((message, index) => (
            <div key={`${message.id || message.created_at || index}`} className={`mb-5 flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {message.role === 'assistant' && <div className="mt-1 mr-3 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#1c2433] font-serif text-[#e6b75c]">M</div>}
              <div className={`max-w-[85%] ${message.role === 'user' ? 'self-end' : ''}`}>
                <div className={`rounded-2xl px-5 py-4 text-sm leading-7 shadow-sm ${message.role === 'user' ? 'rounded-br-none bg-slate-200 text-gray-800' : 'rounded-tl-none border border-slate-100 bg-slate-50 text-gray-800'}`}>
                  {message.role === 'assistant' && <div className="mb-1 text-sm font-semibold text-ink">Mamla.AI</div>}
                  <p className="whitespace-pre-wrap">{message.content || message.text}</p>
                  {message.citations?.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {message.citations.map((citation, citationIndex) => (
                        <button
                          key={`${citation.doc_id || citation.doc_name}-${citationIndex}`}
                          type="button"
                          onClick={() => onJumpToCitation(citation)}
                          className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 transition-colors hover:bg-blue-100"
                        >
                          {citation.doc_name || citation.filename || 'Source'} · p.{citation.page || '?'}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {chatLoading && (
            <div className="mb-5 flex justify-start">
              <div className="mt-1 mr-3 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#1c2433] font-serif text-[#e6b75c]">M</div>
              <div className="rounded-2xl rounded-tl-none border border-slate-100 bg-slate-50 px-5 py-4 shadow-sm">
                <div className="flex gap-1">
                  {[0, 150, 300].map((delay) => (
                    <span key={delay} className="h-2 w-2 animate-bounce rounded-full bg-primary" style={{ animationDelay: `${delay}ms` }} />
                  ))}
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        <div className="border-t border-slate-100 bg-white p-4">
          <div className="relative flex items-center">
            <input
              value={input}
              onChange={(event) => onInputChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault();
                  onSend();
                }
              }}
              placeholder={sendDisabled ? sendPlaceholder : 'Ask a question about your documents...'}
              disabled={sendDisabled}
              className="w-full rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 pr-14 text-sm text-gray-700 shadow-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:cursor-not-allowed disabled:opacity-60"
            />
            <button
              type="button"
              onClick={onSend}
              disabled={chatLoading || !input.trim() || sendDisabled}
              className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center justify-center rounded-lg bg-[#1c2433] p-2 text-white shadow-sm transition-colors hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span className="material-symbols-outlined text-lg">send</span>
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function DocumentWorkspace() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { trial, wallet, features } = useSelector((s) => s.entitlements);
  const [docs, setDocs] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(id || '');
  const [messages, setMessages] = useState([]);
  const [composerCaseId, setComposerCaseId] = useState('');
  const [composerClientId, setComposerClientId] = useState('');
  const [composerClientInput, setComposerClientInput] = useState('');
  const [contextRows, setContextRows] = useState([]);
  const [selectedContextRowId, setSelectedContextRowId] = useState('');
  const [composerSelectedDocIds, setComposerSelectedDocIds] = useState([]);
  const [sessionQuery, setSessionQuery] = useState('');
  const [docSearch, setDocSearch] = useState('');
  const [docFilterCaseId, setDocFilterCaseId] = useState('');
  const [docFilterClientId, setDocFilterClientId] = useState('');
  const [input, setInput] = useState('');
  const [uploading, setUploading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [previewDocId, setPreviewDocId] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState('');
  const [previewUrl, setPreviewUrl] = useState('');
  const [caseOptions, setCaseOptions] = useState([]);
  const [clientOptions, setClientOptions] = useState([]);
  const [caseClientMap, setCaseClientMap] = useState({});
  const [renamingSessionId, setRenamingSessionId] = useState('');
  const [renameValue, setRenameValue] = useState('');
  const [error, setError] = useState('');
  const [mode, setMode] = useState(id ? 'workspace' : 'setup');
  const [deletingDocId, setDeletingDocId] = useState('');
  const [chatQuotaNotice, setChatQuotaNotice] = useState(null);

  const composerMatter = useMemo(() => buildMatter(composerCaseId, composerClientId), [composerCaseId, composerClientId]);

  const filteredDocs = useMemo(() => {
    const query = docSearch.trim().toLowerCase();
    if (!query) return docs;
    return docs.filter((doc) => (doc.filename || doc.name || '').toLowerCase().includes(query));
  }, [docSearch, docs]);

  const filteredSessions = useMemo(() => {
    const query = sessionQuery.trim().toLowerCase();
    if (!query) return sessions;
    return sessions.filter((session) => {
      const title = session.title?.toLowerCase() || '';
      const matter = formatMatterLabel(session.matter).toLowerCase();
      return title.includes(query) || matter.includes(query);
    });
  }, [sessionQuery, sessions]);

  const filteredClientOptions = useMemo(() => {
    if (!composerCaseId) return clientOptions;
    return caseClientMap[composerCaseId] || [];
  }, [caseClientMap, clientOptions, composerCaseId]);

  const filteredDocClientOptions = useMemo(() => {
    if (!docFilterCaseId) return clientOptions;
    return caseClientMap[docFilterCaseId] || [];
  }, [caseClientMap, clientOptions, docFilterCaseId]);

  const selectedClientLabel = useMemo(() => {
    if (!composerClientId) return '';
    const match = clientOptions.find((option) => option.value === composerClientId);
    return match?.label || match?.displayValue || composerClientInput || composerClientId;
  }, [clientOptions, composerClientId, composerClientInput]);

  const clientCaseMap = useMemo(() => {
    const next = {};
    Object.entries(caseClientMap).forEach(([caseId, clients]) => {
      clients.forEach((client) => {
        if (!next[client.value]) {
          next[client.value] = [];
        }
        next[client.value].push(caseId);
      });
    });
    return next;
  }, [caseClientMap]);

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === currentSessionId) || null,
    [currentSessionId, sessions],
  );

  const sessionDocs = useMemo(() => {
    if (!activeSession) return [];
    const ordered = new Map(docs.map((doc) => [doc.doc_id, doc]));
    return (activeSession.doc_ids || []).map((docId) => ordered.get(docId)).filter(Boolean);
  }, [activeSession, docs]);

  const previewDoc = useMemo(() => {
    if (!previewDocId) return null;
    return docs.find((doc) => doc.doc_id === previewDocId) || null;
  }, [docs, previewDocId]);
  const activeFeatureCode = activeSession?.has_docs ? 'brain_doc_analysis' : 'general_legal_chat';
  const activeQuota = features?.[activeFeatureCode] || null;
  const documentQuota = features?.brain_doc_analysis || null;
  const legalChatQuota = features?.general_legal_chat || null;
  const activeFeatureMeta = useMemo(() => getTalkdocFeatureMeta(activeFeatureCode), [activeFeatureCode]);
  const brainQuotaNotice = useMemo(
    () => chatQuotaNotice || buildBrainQuotaNotice(activeQuota, activeFeatureCode),
    [activeFeatureCode, activeQuota, chatQuotaNotice],
  );
  const sendDisabled = activeQuota?.allowed === false;
  const sendPlaceholder = activeSession?.has_docs
    ? 'Mamla Brain access is unavailable for document analysis in this chat right now.'
    : 'General legal chat is unavailable for this session right now.';

  async function withBlocking(message, action) {
    dispatch(beginBlocking({ message }));
    try {
      return await action();
    } finally {
      dispatch(stopBlocking());
    }
  }

  async function fetchDocs() {
    try {
      const params = {};
      if (docFilterCaseId.trim()) params.caseid = docFilterCaseId.trim();
      if (docFilterClientId.trim()) params.clientid = docFilterClientId.trim();
      const response = await apiClient.get('talkdoc/documents/', { params });
      const rows = (response.data?.results ?? response.data?.items ?? response.data ?? []).map(normalizeDoc);
      setDocs(rows);
    } catch {
      setError('Could not load documents.');
    }
  }

  async function fetchSessions(preferredId = '') {
    try {
      const response = await apiClient.get('talkdoc/sessions/');
      const rows = (response.data?.results ?? response.data?.items ?? response.data ?? []).map(normalizeSession);
      setSessions(rows);

      const sessionId = preferredId || currentSessionId || id || '';
      if (sessionId) {
        const match = rows.find((session) => session.id === sessionId);
        if (match) {
          setCurrentSessionId(match.id);
          return match;
        }
      }

      return null;
    } catch {
      setError('Could not load saved chats.');
      return null;
    }
  }

  async function fetchCaseClientOptions() {
    try {
      const response = await apiClient.get('users/filter_with_details/');
      const payload = response.data || {};
      const nextCaseOptions = [];
      const nextClientOptions = [];
      const nextCaseClientMap = {};
      const nextContextRows = [];
      const seenCases = new Set();
      const seenClients = new Set();

      (payload.caseIds_without_client || []).forEach((caseId) => {
        if (!caseId || seenCases.has(caseId)) return;
        seenCases.add(caseId);
        nextCaseOptions.push({ value: caseId, label: caseId });
      });

      Object.entries(payload.case_client_map || {}).forEach(([caseId, clientEntry]) => {
        if (caseId && !seenCases.has(caseId)) {
          seenCases.add(caseId);
          nextCaseOptions.push({ value: caseId, label: caseId });
        }
        const clients = Array.isArray(clientEntry) ? clientEntry : [clientEntry];
        nextCaseClientMap[caseId] = [];
        clients.forEach((client) => {
          const option = buildClientOption(client);
          if (!option.value) {
            nextContextRows.push({
              id: `${caseId}-empty`,
              case_id: caseId,
              client_id: '',
              client_name: getClientName(client),
            });
            return;
          }
          if (!seenClients.has(option.value)) {
            seenClients.add(option.value);
            nextClientOptions.push(option);
          }
          nextCaseClientMap[caseId].push(option);
          nextContextRows.push({
            id: `${caseId}-${option.value}`,
            case_id: caseId,
            client_id: option.value,
            client_name: getClientName(client),
          });
        });

        if (clients.length === 0) {
          nextContextRows.push({
            id: caseId,
            case_id: caseId,
            client_id: '',
            client_name: 'Unnamed',
          });
        }
      });

      (payload.clientIds_without_case || []).forEach((client) => {
        const option = buildClientOption(client);
        if (!option.value || seenClients.has(option.value)) return;
        seenClients.add(option.value);
        nextClientOptions.push(option);
        nextContextRows.push({
          id: `client-${option.value}`,
          case_id: '',
          client_id: option.value,
          client_name: getClientName(client),
        });
      });

      setCaseOptions(nextCaseOptions.sort((a, b) => a.value.localeCompare(b.value)));
      setClientOptions(nextClientOptions.sort((a, b) => a.value.localeCompare(b.value)));
      setCaseClientMap(nextCaseClientMap);
      setContextRows(nextContextRows);
    } catch {
      setCaseOptions([]);
      setClientOptions([]);
      setCaseClientMap({});
      setContextRows([]);
    }
  }

  function selectContextRow(rowId) {
    setSelectedContextRowId(rowId);
    const row = contextRows.find((item) => item.id === rowId);
    if (!row) {
      setComposerCaseId('');
      setComposerClientId('');
      setComposerClientInput('');
      return;
    }
    setComposerCaseId(row.case_id || '');
    setComposerClientId(row.client_id || '');
    setComposerClientInput(row.client_name || row.client_id || '');
  }

  function addCustomContextRow() {
    const caseId = window.prompt('Case ID (optional)') || '';
    const clientName = window.prompt('Client name') || '';
    if (!caseId.trim() && !clientName.trim()) return;
    const clientId = window.prompt('Client ID / phone / email (optional)') || '';
    const newRow = {
      id: `custom-${Date.now()}`,
      case_id: caseId.trim(),
      client_id: clientId.trim(),
      client_name: clientName.trim() || clientId.trim() || 'Unnamed',
    };
    setContextRows((current) => [...current, newRow]);
    setSelectedContextRowId(newRow.id);
    setComposerCaseId(newRow.case_id || '');
    setComposerClientId(newRow.client_id || '');
    setComposerClientInput(newRow.client_name || newRow.client_id || '');
  }

  function clearContextSelection() {
    setSelectedContextRowId('');
    setComposerCaseId('');
    setComposerClientId('');
    setComposerClientInput('');
  }

  function handleComposerCaseChange(value) {
    setComposerCaseId(value);

    if (!value) {
      setComposerClientId('');
      setComposerClientInput('');
      return;
    }

    const linkedClients = caseClientMap[value] || [];
    if (linkedClients.length === 1) {
      setComposerClientId(linkedClients[0].value);
      setComposerClientInput(linkedClients[0].displayValue || linkedClients[0].label || linkedClients[0].value);
      return;
    }

    if (composerClientId && !linkedClients.some((option) => option.value === composerClientId)) {
      setComposerClientId('');
      setComposerClientInput('');
    }
  }

  function handleComposerClientChange(value) {
    setComposerClientInput(value);

    if (!value) {
      setComposerClientId('');
      return;
    }

    const matchedOption = filteredClientOptions.find((option) => option.displayValue === value)
      || clientOptions.find((option) => option.displayValue === value)
      || filteredClientOptions.find((option) => option.value === value)
      || clientOptions.find((option) => option.value === value);

    const resolvedClientValue = matchedOption?.value || value;
    setComposerClientId(resolvedClientValue);

    const matchingCases = clientCaseMap[resolvedClientValue] || [];
    if (matchingCases.length === 1) {
      setComposerCaseId(matchingCases[0]);
    }
  }

  function handleDocFilterCaseChange(value) {
    setDocFilterCaseId(value);

    if (!value) {
      return;
    }

    const linkedClients = caseClientMap[value] || [];
    if (linkedClients.length === 1) {
      setDocFilterClientId(linkedClients[0].value);
      return;
    }

    if (docFilterClientId && !linkedClients.some((option) => option.value === docFilterClientId)) {
      setDocFilterClientId('');
    }
  }

  function handleDocFilterClientChange(value) {
    setDocFilterClientId(value);

    if (!value) {
      return;
    }

    const matchingCases = clientCaseMap[value] || [];
    if (matchingCases.length === 1) {
      setDocFilterCaseId(matchingCases[0]);
    }
  }

  async function loadMessages(sessionId, { blockUi = false } = {}) {
    const load = async () => {
      try {
        const response = await apiClient.get(`talkdoc/session_messages/?session_id=${sessionId}`);
        setMessages(response.data?.results ?? response.data?.messages ?? []);
      } catch {
        setMessages([]);
        setError('Could not load session messages.');
      }
    };

    if (blockUi) {
      await withBlocking('Opening chat session...', load);
      return;
    }

    await load();
  }

  useEffect(() => {
    fetchSessions(id || '');
    fetchCaseClientOptions();
  }, []);

  useEffect(() => {
    if (id) return;

    const params = new URLSearchParams(location.search);
    const nextCaseId = params.get('caseid')?.trim() || '';
    const nextClientIdFromQuery = params.get('clientid')?.trim() || '';
    const linkedClients = nextCaseId ? (caseClientMap[nextCaseId] || []) : [];
    const resolvedClientId = nextClientIdFromQuery || (linkedClients.length === 1 ? linkedClients[0].value : '');
    const resolvedClientInput = resolvedClientId
      ? (clientOptions.find((option) => option.value === resolvedClientId)?.displayValue
        || clientOptions.find((option) => option.value === resolvedClientId)?.label
        || resolvedClientId)
      : '';

    if (!nextCaseId && !resolvedClientId) return;

    setMode('setup');
    setCurrentSessionId('');
    setMessages([]);
    setSelectedContextRowId('');
    setDocFilterCaseId(nextCaseId);
    setDocFilterClientId(resolvedClientId);
    setComposerCaseId(nextCaseId);
    setComposerClientId(resolvedClientId);
    setComposerClientInput(resolvedClientInput);
  }, [caseClientMap, clientOptions, id, location.search]);

  useEffect(() => {
    fetchDocs();
  }, [docFilterCaseId, docFilterClientId]);

  useEffect(() => {
    if (!currentSessionId) {
      setMessages([]);
      return;
    }
    loadMessages(currentSessionId, { blockUi: true });
  }, [currentSessionId]);

  useEffect(() => {
    if (id) {
      setMode('workspace');
    }
  }, [id]);

  useEffect(() => {
    if (mode !== 'workspace') return undefined;
    if (previewDocId) return undefined;
    if (sessionDocs.length > 0) {
      setPreviewDocId(sessionDocs[0].doc_id);
    }
    return undefined;
  }, [mode, previewDocId, sessionDocs]);

  useEffect(() => {
    if (!previewDoc) {
      setPreviewLoading(false);
      setPreviewError('');
      setPreviewUrl((current) => {
        if (current) URL.revokeObjectURL(current);
        return '';
      });
      return undefined;
    }

    let disposed = false;
    setPreviewLoading(true);
    setPreviewError('');

    async function loadPreview() {
      try {
        const response = await apiClient.get(`talkdoc/documents/${previewDoc.doc_id}/file/`, {
          responseType: 'blob',
        });
        if (disposed) return;
        const nextUrl = URL.createObjectURL(response.data);
        setPreviewUrl((current) => {
          if (current) URL.revokeObjectURL(current);
          return nextUrl;
        });
      } catch (err) {
        if (disposed) return;
        setPreviewError(err.response?.data?.error || 'Preview is unavailable for this file right now.');
      } finally {
        if (!disposed) setPreviewLoading(false);
      }
    }

    loadPreview();

    return () => {
      disposed = true;
    };
  }, [previewDoc]);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  useEffect(() => {
    const hasPending = docs.some((doc) => !['indexed', 'failed'].includes(doc.status));
    if (!hasPending) return undefined;
    const intervalId = window.setInterval(() => {
      fetchDocs();
    }, 8000);
    return () => window.clearInterval(intervalId);
  }, [docs]);

  function resetComposer() {
    setMode('setup');
    setCurrentSessionId('');
    setMessages([]);
    clearContextSelection();
    setComposerSelectedDocIds([]);
    setDocFilterCaseId('');
    setDocFilterClientId('');
    setPreviewDocId('');
    setInput('');
    setError('');
    setChatQuotaNotice(null);
    setRenamingSessionId('');
    setRenameValue('');
    navigate('/documents');
  }

  function openSession(sessionId) {
    setCurrentSessionId(sessionId);
    setMode('workspace');
    setPreviewDocId('');
    setError('');
    setChatQuotaNotice(null);
    navigate(`/documents/${sessionId}`);
  }

  async function handleUpload(event, { attachToActiveSession = false } = {}) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    setUploading(true);
    setError('');
    try {
      await withBlocking(files.length > 1 ? 'Uploading documents...' : 'Uploading document...', async () => {
        const uploadedIds = [];
        const targetMatter = attachToActiveSession && activeSession ? (activeSession.matter || {}) : composerMatter;

        for (const file of files) {
          const formData = new FormData();
          formData.append('file', file);
          if (Object.keys(targetMatter).length > 0) {
            formData.append('matter', JSON.stringify(targetMatter));
          }
          const response = await apiClient.post('talkdoc/upload/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
          const uploadedDoc = normalizeDoc(response.data);
          setDocs((current) => [uploadedDoc, ...current.filter((doc) => doc.doc_id !== uploadedDoc.doc_id)]);
          uploadedIds.push(uploadedDoc.doc_id);
          if (!attachToActiveSession) {
            setComposerSelectedDocIds((current) => (current.includes(uploadedDoc.doc_id) ? current : [...current, uploadedDoc.doc_id]));
          }
          setPreviewDocId(uploadedDoc.doc_id);
        }

        if (attachToActiveSession && activeSession && uploadedIds.length > 0) {
          await attachDocIdsToSession(activeSession.id, uploadedIds);
          await fetchSessions(activeSession.id);
        }

        if (!attachToActiveSession && uploadedIds.length > 0) {
          setComposerSelectedDocIds((current) => Array.from(new Set([...current, ...uploadedIds])));
        }

        await fetchDocs();
      });
    } catch (err) {
      if (err.response?.status === 413) {
        setError('Upload rejected because the file is larger than the current server limit.');
      } else {
        setError(err.response?.data?.error || 'Upload failed. Please try again.');
      }
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  }

  async function createSession() {
    try {
      setError('');
      const response = await withBlocking('Creating document session...', () => apiClient.post('talkdoc/create_session/', {
        doc_ids: composerSelectedDocIds,
        matter: composerMatter,
      }));
      const session = normalizeSession(response.data);
      setSessions((current) => [session, ...current.filter((item) => item.id !== session.id)]);
      setCurrentSessionId(session.id);
      setMessages([]);
      setMode('workspace');
      setPreviewDocId(session.doc_ids?.[0] || composerSelectedDocIds[0] || '');
      navigate(`/documents/${session.id}`);
      return session.id;
    } catch {
      setError('Could not create the session.');
      return null;
    }
  }

  async function renameSession(sessionId) {
    const nextTitle = renameValue.trim();
    if (!nextTitle) {
      setRenamingSessionId('');
      setRenameValue('');
      return;
    }
    try {
      await apiClient.post(`talkdoc/rename_session/${sessionId}`, { title: nextTitle });
      setSessions((current) => current.map((session) => (
        session.id === sessionId ? { ...session, title: nextTitle } : session
      )));
      setRenamingSessionId('');
      setRenameValue('');
    } catch (err) {
      setError(err.response?.data?.error || 'Could not rename the chat session.');
    }
  }

  async function deleteSession(sessionId) {
    if (!sessionId) return;
    if (!window.confirm('Delete this chat session?')) return;
    try {
      await withBlocking('Deleting chat session...', () => apiClient.delete(`talkdoc/sessions/${sessionId}`));
      setSessions((current) => current.filter((session) => session.id !== sessionId));
      if (currentSessionId === sessionId) {
        resetComposer();
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Could not delete the chat session.');
    }
  }

  async function attachDocIdsToSession(sessionId, docIds) {
    if (!sessionId || !docIds.length) return;
    const response = await apiClient.post(`talkdoc/sessions/${sessionId}/docs`, { add: docIds });
    const nextDocIds = response.data?.doc_ids || docIds;
    setSessions((current) => current.map((session) => (
      session.id === sessionId
        ? { ...session, doc_ids: nextDocIds, doc_count: nextDocIds.length, has_docs: nextDocIds.length > 0 }
        : session
    )));
  }

  async function deleteDocument(docId) {
    if (!docId) return;
    if (!window.confirm('Delete this document from Talk To Docs?')) return;
    setDeletingDocId(docId);
    try {
      await withBlocking('Removing document...', () => apiClient.delete(`talkdoc/documents/${docId}/`));
      setDocs((current) => current.filter((doc) => doc.doc_id !== docId));
      setComposerSelectedDocIds((current) => current.filter((idValue) => idValue !== docId));
      setSessions((current) => current.map((session) => {
        if (!(session.doc_ids || []).includes(docId)) return session;
        const nextDocIds = session.doc_ids.filter((idValue) => idValue !== docId);
        return { ...session, doc_ids: nextDocIds, doc_count: nextDocIds.length, has_docs: nextDocIds.length > 0 };
      }));
      if (previewDocId === docId) {
        const nextDocId = sessionDocs.find((doc) => doc.doc_id !== docId)?.doc_id || '';
        setPreviewDocId(nextDocId);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Could not delete the document.');
    } finally {
      setDeletingDocId('');
    }
  }

  async function handleSend() {
    if (!input.trim() || chatLoading || !activeSession || sendDisabled) return;

    const text = input.trim();
    setInput('');
    setMessages((current) => [...current, { role: 'user', content: text }]);
    setChatLoading(true);
    setError('');
    setChatQuotaNotice(null);

    try {
      const response = await withBlocking('Analyzing your question...', () => apiClient.post('talkdoc/query/', {
        session_id: activeSession.id,
        query: text,
      }));
      const responseQuota = response.data?.quota || null;
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: response.data?.answer || response.data?.message || 'No response',
          citations: response.data?.citations || [],
        },
      ]);
      if (responseQuota) {
        dispatch(updateFeatureQuota(responseQuota));
        setChatQuotaNotice(buildBrainQuotaNotice(responseQuota, activeFeatureCode));
      }
      setSessions((current) => current.map((session) => (
        session.id === activeSession.id
          ? {
            ...session,
            last_message_at: nowTimestampString(),
          }
          : session
      )));
    } catch (err) {
      const nextQuota = err.response?.data?.quota || null;
      if (nextQuota) {
        setChatQuotaNotice(buildBrainQuotaNotice(nextQuota, activeFeatureCode));
        dispatch(updateFeatureQuota(nextQuota));
      }
      setMessages((current) => [
        ...current,
        { role: 'assistant', content: err.response?.data?.error || 'Sorry, I could not process that request.' },
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  function openPreview() {
    if (!previewUrl) return;
    window.open(previewUrl, '_blank', 'noopener,noreferrer');
  }

  function jumpToCitation(citation) {
    if (citation?.doc_id) {
      setPreviewDocId(citation.doc_id);
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-background-light">
      {error && <div className="border-b border-red-200 bg-red-50 px-5 py-3 text-sm text-red-600">{error}</div>}
      {(typeof documentQuota?.remaining_included === 'number' || typeof legalChatQuota?.remaining_included === 'number') && (
        <div className={`border-b px-5 py-3 text-sm ${typeof activeQuota?.remaining_included === 'number' && activeQuota.remaining_included <= 2 ? 'border-amber-200 bg-amber-50 text-amber-800' : 'border-primary/10 bg-white text-slate-600'}`}>
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-ink">Mamla Brain {trial?.active ? 'trial' : 'usage'}</span>
            {typeof documentQuota?.remaining_included === 'number' && (
              <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
                {documentQuota.remaining_included} document analyses left
              </span>
            )}
            {typeof legalChatQuota?.remaining_included === 'number' && (
              <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">
                {legalChatQuota.remaining_included} general legal chats left
              </span>
            )}
            {wallet?.balance ? (
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                {wallet.balance} credits available for overage
              </span>
            ) : null}
            {activeSession && (
              <span className="text-xs font-medium text-slate-500">
                Active mode: {activeFeatureMeta.label.toLowerCase()}
              </span>
            )}
          </div>
        </div>
      )}

      {mode === 'setup' && (
        <SetupWindow
          docs={filteredDocs}
          sessions={filteredSessions}
          docSearch={docSearch}
          onDocSearchChange={setDocSearch}
          sessionQuery={sessionQuery}
          onSessionQueryChange={setSessionQuery}
          contextRows={contextRows}
          selectedContextRowId={selectedContextRowId}
          onSelectContextRow={selectContextRow}
          onAddCustomContextRow={addCustomContextRow}
          onClearContextSelection={clearContextSelection}
          docFilterCaseId={docFilterCaseId}
          docFilterClientId={docFilterClientId}
          onDocFilterCaseIdChange={handleDocFilterCaseChange}
          onDocFilterClientIdChange={handleDocFilterClientChange}
          docFilterClientOptions={filteredDocClientOptions}
          onClearDocFilters={() => {
            setDocFilterCaseId('');
            setDocFilterClientId('');
          }}
          composerSelectedDocIds={composerSelectedDocIds}
          onToggleComposerDoc={(docId) => {
            setComposerSelectedDocIds((current) => (current.includes(docId) ? current.filter((item) => item !== docId) : [...current, docId]));
          }}
          onUpload={handleUpload}
          uploading={uploading}
          onDeleteDoc={deleteDocument}
          deletingDocId={deletingDocId}
          onCreateSession={createSession}
          onOpenSession={openSession}
          onDeleteSession={deleteSession}
          onStartRename={(session) => {
            setRenamingSessionId(session.id);
            setRenameValue(session.title || '');
          }}
          onCommitRename={renameSession}
          onCancelRename={() => {
            setRenamingSessionId('');
            setRenameValue('');
          }}
          renamingSessionId={renamingSessionId}
          renameValue={renameValue}
          onRenameValueChange={setRenameValue}
          caseOptions={caseOptions}
          clientOptions={filteredDocClientOptions}
          onResetComposer={resetComposer}
        />
      )}

      {mode === 'workspace' && (
        <main className="mx-auto flex h-full w-full max-w-[1600px] flex-1 flex-col px-4 py-6 sm:px-6 lg:px-8">
          <div className="mb-6">
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-primary">Talk To Docs</p>
            <h1 className="mt-2 text-3xl font-bold text-ink">Document Intelligence &amp; Q&amp;A</h1>
          </div>

          <div className="grid min-h-0 flex-1 grid-cols-1 gap-8 lg:grid-cols-2 lg:grid-rows-1 lg:gap-8">
            <DocumentViewer
              sessionDocs={sessionDocs}
              previewDoc={previewDoc}
              previewUrl={previewUrl}
              previewLoading={previewLoading}
              previewError={previewError}
              onSelectDoc={setPreviewDocId}
              onBackToSetup={resetComposer}
              onOpenPreview={openPreview}
              onUpload={(event) => handleUpload(event, { attachToActiveSession: true })}
              uploading={uploading}
            />

            <ChatWindow
              activeSession={activeSession}
              messages={messages}
              input={input}
              onInputChange={setInput}
              onSend={handleSend}
              chatLoading={chatLoading}
              onDeleteSession={deleteSession}
              onStartRename={(session) => {
                setRenamingSessionId(session.id);
                setRenameValue(session.title || '');
              }}
              renamingSessionId={renamingSessionId}
              renameValue={renameValue}
              onRenameValueChange={setRenameValue}
              onCommitRename={renameSession}
              onCancelRename={() => {
                setRenamingSessionId('');
                setRenameValue('');
              }}
              onJumpToCitation={jumpToCitation}
              quotaNotice={brainQuotaNotice}
              sendDisabled={sendDisabled}
              sendPlaceholder={sendPlaceholder}
            />
          </div>
        </main>
      )}
    </div>
  );
}