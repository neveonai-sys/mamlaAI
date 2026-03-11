import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  downloadOrder,
  getCaseByCnr,
  getCaseOrders,
  refreshCase,
  unwrapEcourtsPayload,
} from './common/ecourtsApi';

function DetailRow({ label, value, mono = false }) {
  if (!value) return null;
  return (
    <div className="grid grid-cols-3 gap-3 py-3 border-b border-primary/5 last:border-b-0">
      <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">{label}</p>
      <p className={`col-span-2 text-sm text-ink ${mono ? 'font-mono' : 'font-medium'}`}>{value}</p>
    </div>
  );
}

function formatDate(value, options = {}) {
  if (!value) return null;

  const normalizedValue = /^\d{2}-\d{2}-\d{4}$/.test(value)
    ? (() => {
        const [day, month, year] = value.split('-');
        return `${year}-${month}-${day}`;
      })()
    : value;

  const parsed = new Date(normalizedValue);
  if (Number.isNaN(parsed.getTime())) return value;

  return parsed.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    ...options,
  });
}

function normalizeStatus(status) {
  return (status || '').toString().trim().toUpperCase();
}

function statusBadgeClass(status) {
  switch (normalizeStatus(status)) {
    case 'DISPOSED':
      return 'bg-slate-100 text-slate-600';
    case 'PENDING':
      return 'bg-amber-100 text-amber-700';
    default:
      return 'bg-emerald-100 text-emerald-700';
  }
}

function PartyColumn({ title, parties, advocates, accentClass, onPartyClick, onAdvocateClick }) {
  if ((!parties || parties.length === 0) && (!advocates || advocates.length === 0)) {
    return null;
  }

  return (
    <div className={`rounded-2xl border border-primary/10 bg-background-light/70 p-5 ${accentClass}`}>
      <div className="mb-4 flex items-center gap-2">
        <span className="material-symbols-outlined text-base text-primary">groups</span>
        <h3 className="text-sm font-black uppercase tracking-[0.2em] text-slate-500">{title}</h3>
      </div>

      {parties?.length > 0 ? (
        <div className="space-y-2">
          {parties.map((party, index) => (
            <button
              key={`${title}-party-${index}`}
              type="button"
              onClick={() => onPartyClick?.(party)}
              className="flex w-full items-start gap-3 rounded-xl border border-primary/10 bg-white px-3 py-2 text-left transition-colors hover:border-primary/30 hover:bg-primary/5"
            >
              <span className="mt-0.5 text-[11px] font-black text-primary">{index + 1}</span>
              <span className="text-sm font-medium text-ink">{party}</span>
            </button>
          ))}
        </div>
      ) : null}

      {advocates?.length > 0 ? (
        <div className="mt-4 border-t border-primary/10 pt-4">
          <p className="mb-2 text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Advocates</p>
          <div className="flex flex-wrap gap-2">
            {advocates.map((advocate, index) => (
              <button
                key={`${title}-advocate-${index}`}
                type="button"
                onClick={() => onAdvocateClick?.(advocate)}
                className="rounded-full border border-primary/15 px-3 py-1.5 text-xs font-semibold text-slate-600 transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-primary"
              >
                {advocate}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function TimelineRow({ icon, title, subtitle, meta, accent = 'text-primary' }) {
  return (
    <div className="flex items-start gap-4 rounded-2xl border border-primary/10 bg-white px-4 py-4">
      <div className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 ${accent}`}>
        <span className="material-symbols-outlined text-lg">{icon}</span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold text-ink">{title}</p>
          {subtitle ? <p className="text-xs font-semibold text-primary">{subtitle}</p> : null}
        </div>
        {meta ? <p className="mt-1 text-xs text-slate-500">{meta}</p> : null}
      </div>
    </div>
  );
}

export default function CaseDetail() {
  const navigate = useNavigate();
  const { cnr } = useParams();
  const [caseData, setCaseData] = useState(null);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [downloadError, setDownloadError] = useState('');
  const [downloadingIndex, setDownloadingIndex] = useState(null);
  const [copied, setCopied] = useState(false);

  const fetchCase = useCallback(async () => {
    if (!cnr) return;

    setLoading(true);
    setError('');

    try {
      const [caseResponse, ordersResponse] = await Promise.allSettled([
        getCaseByCnr(encodeURIComponent(cnr)),
        getCaseOrders(encodeURIComponent(cnr)),
      ]);

      if (caseResponse.status !== 'fulfilled') {
        throw caseResponse.reason;
      }

      const nextCaseData = unwrapEcourtsPayload(caseResponse.value) || {};
      const nextOrders = ordersResponse.status === 'fulfilled'
        ? ordersResponse.value?.data?.orders || []
        : nextCaseData.orders || [];

      setCaseData(nextCaseData);
      setOrders(nextOrders);
    } catch (err) {
      setError(err.response?.data?.error || 'Case not found or data unavailable.');
      setCaseData(null);
      setOrders([]);
    } finally {
      setLoading(false);
    }
  }, [cnr]);

  useEffect(() => {
    fetchCase();
  }, [fetchCase]);

  async function handleRefresh() {
    if (!cnr) return;

    setRefreshing(true);
    setError('');
    try {
      await refreshCase(encodeURIComponent(cnr));
      await fetchCase();
    } catch (err) {
      setError(err.response?.data?.error || 'Refresh failed. Please try again.');
    } finally {
      setRefreshing(false);
    }
  }

  async function handleDownload(orderIndex) {
    if (!cnr) return;

    setDownloadError('');
    setDownloadingIndex(orderIndex);
    try {
      const response = await downloadOrder(encodeURIComponent(cnr), orderIndex);
      const blob = new Blob([response.data], {
        type: response.headers['content-type'] || 'application/pdf',
      });
      const blobUrl = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      const disposition = response.headers['content-disposition'] || '';
      const filenameMatch = disposition.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);

      anchor.href = blobUrl;
      anchor.download = filenameMatch?.[1] || `${cnr}-order-${orderIndex + 1}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      let message = 'Download failed. Please try again.';
      try {
        if (err.response?.data instanceof Blob) {
          const text = await err.response.data.text();
          const payload = JSON.parse(text);
          message = payload.error || payload.message || message;
        } else if (err.response?.data?.error) {
          message = err.response.data.error;
        }
      } catch {
        message = err.message || message;
      }
      setDownloadError(message);
    } finally {
      setDownloadingIndex(null);
    }
  }

  function handleCopyLink() {
    navigator.clipboard?.writeText(window.location.href).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    }).catch(() => {});
  }

  function goToLitigantSearch(query) {
    navigate(`/ecourts/litigants?q=${encodeURIComponent(query)}`);
  }

  function goToLawyerSearch(query) {
    navigate(`/ecourts/lawyers?q=${encodeURIComponent(query)}`);
  }

  const timelineItems = useMemo(() => {
    if (!caseData) return [];

    const listingItems = (caseData.listing_dates || []).map((item, index) => ({
      id: `listing-${index}`,
      icon: 'event_upcoming',
      title: formatDate(item.date) || item.date || 'Listing date',
      subtitle: item.purpose || 'Upcoming listing',
      meta: null,
      sortValue: item.date || '',
      kind: 'listing',
    }));

    const hearingItems = (caseData.hearing_history || []).map((item, index) => ({
      id: `hearing-${index}`,
      icon: 'history',
      title: formatDate(item.date) || item.date || 'Hearing date',
      subtitle: item.purpose || 'Hearing',
      meta: [item.business_on_date, item.judge ? `Before ${item.judge}` : null].filter(Boolean).join(' • '),
      sortValue: item.date || '',
      kind: 'hearing',
    }));

    return [...listingItems, ...hearingItems];
  }, [caseData]);

  const actsAndSections = useMemo(() => {
    if (!caseData?.acts_and_sections) return [];
    return Array.isArray(caseData.acts_and_sections)
      ? caseData.acts_and_sections
      : [caseData.acts_and_sections];
  }, [caseData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="material-symbols-outlined text-primary text-4xl animate-spin">progress_activity</span>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="p-8 max-w-3xl">
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <button type="button" onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-primary hover:underline">
            <span className="material-symbols-outlined text-sm">arrow_back</span>
            Back
          </button>
          <Link to="/ecourts/case-search" className="text-sm text-slate-500 hover:text-primary hover:underline">Case Search</Link>
          <Link to="/ecourts" className="text-sm text-slate-500 hover:text-primary hover:underline">eCourts Home</Link>
        </div>
        <div className="card p-8 text-center">
          <span className="material-symbols-outlined text-slate-300 text-5xl block mb-3">gavel</span>
          <p className="text-slate-500">{error || 'Case data not available.'}</p>
        </div>
      </div>
    );
  }

  const normalizedStatus = normalizeStatus(caseData.case_status);
  const statusLabel = caseData.case_status || 'Active';
  const partiesCount = (caseData.petitioners?.length || 0) + (caseData.respondents?.length || 0);

  return (
    <div className="p-8 max-w-6xl">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <button type="button" onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-primary hover:underline">
            <span className="material-symbols-outlined text-sm">arrow_back</span>
            Back
          </button>
          <Link to="/ecourts/case-search" className="text-sm text-slate-500 hover:text-primary hover:underline">Case Search</Link>
          <Link to="/ecourts" className="text-sm text-slate-500 hover:text-primary hover:underline">eCourts Home</Link>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleCopyLink}
            className="rounded-full border border-primary/15 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-primary"
          >
            {copied ? 'Link Copied' : 'Copy Link'}
          </button>
          <button type="button" onClick={handleRefresh} disabled={refreshing} className="btn-primary flex items-center gap-2 disabled:opacity-60">
            <span className={`material-symbols-outlined text-base ${refreshing ? 'animate-spin' : ''}`}>refresh</span>
            {refreshing ? 'Refreshing…' : 'Refresh Case'}
          </button>
        </div>
      </div>

      {error ? (
        <div className="mb-4 flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          <span className="material-symbols-outlined text-base">error</span>
          {error}
        </div>
      ) : null}

      <div className="card p-6 mb-6">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-xs px-2 py-0.5 rounded font-bold uppercase ${statusBadgeClass(normalizedStatus)}`}>
                {statusLabel}
              </span>
              <span className="text-xs font-mono text-slate-400">{caseData.cnr || cnr}</span>
            </div>
            <h1 className="text-2xl font-black text-ink">{caseData.case_title || 'Case Detail'}</h1>
            <p className="mt-2 text-sm text-slate-500">
              {[caseData.court_name, caseData.state, caseData.district].filter(Boolean).join(' • ') || 'Court details unavailable'}
            </p>
          </div>
          {caseData.next_hearing_date && (
            <div className="text-right flex-shrink-0">
              <p className="text-[10px] text-slate-400 uppercase tracking-wider">Next Hearing</p>
              <p className="font-bold text-primary">
                {formatDate(caseData.next_hearing_date)}
              </p>
            </div>
          )}
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-3">
            <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">Case Type</p>
            <p className="mt-1 text-sm font-semibold text-ink">{caseData.case_type || '—'}</p>
          </div>
          <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-3">
            <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">Case Number</p>
            <p className="mt-1 text-sm font-semibold text-ink">{caseData.case_number || '—'}</p>
          </div>
          <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-3">
            <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">Bench</p>
            <p className="mt-1 text-sm font-semibold text-ink">{caseData.bench_name || caseData.court_no || '—'}</p>
          </div>
          <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-3">
            <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">Parties</p>
            <p className="mt-1 text-sm font-semibold text-ink">{partiesCount || '—'}</p>
          </div>
        </div>

        <div className="mt-5 divide-y divide-primary/5">
          <DetailRow label="Court" value={caseData.court_name} />
          <DetailRow label="State / District" value={[caseData.state, caseData.district].filter(Boolean).join(' / ')} />
          <DetailRow label="Judges" value={caseData.judges?.join(', ')} />
          <DetailRow label="Purpose" value={caseData.purpose} />
          <DetailRow label="Judicial Section" value={caseData.judicial_section} />
          <DetailRow label="Filing Date" value={formatDate(caseData.filing_date)} />
          <DetailRow label="Registration Date" value={formatDate(caseData.registration_date)} />
          <DetailRow label="First Hearing" value={formatDate(caseData.first_hearing_date)} />
          <DetailRow label="Decision Date" value={formatDate(caseData.decision_date)} />
          <DetailRow label="CNR" value={caseData.cnr || cnr} mono />
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            <PartyColumn
              title="Petitioners"
              parties={caseData.petitioners || []}
              advocates={caseData.petitioner_advocates || []}
              accentClass=""
              onPartyClick={goToLitigantSearch}
              onAdvocateClick={goToLawyerSearch}
            />
            <PartyColumn
              title="Respondents"
              parties={caseData.respondents || []}
              advocates={caseData.respondent_advocates || []}
              accentClass=""
              onPartyClick={goToLitigantSearch}
              onAdvocateClick={goToLawyerSearch}
            />
          </div>

          {timelineItems.length > 0 ? (
            <div className="card p-6">
              <div className="mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">history</span>
                <h2 className="text-lg font-black text-ink">Timeline</h2>
              </div>
              <div className="space-y-3">
                {timelineItems.map((item) => (
                  <TimelineRow
                    key={item.id}
                    icon={item.icon}
                    title={item.title}
                    subtitle={item.subtitle}
                    meta={item.meta}
                    accent={item.kind === 'listing' ? 'text-primary' : 'text-slate-500'}
                  />
                ))}
              </div>
            </div>
          ) : null}

          {orders.length > 0 ? (
            <div className="card p-6">
              <div className="mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">description</span>
                <h2 className="text-lg font-black text-ink">Orders & Judgments</h2>
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">{orders.length}</span>
              </div>

              {downloadError ? (
                <div className="mb-4 flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
                  <span className="material-symbols-outlined text-base">error</span>
                  {downloadError}
                </div>
              ) : null}

              <div className="space-y-3">
                {orders.map((order) => (
                  <div key={order.index} className="flex flex-col gap-3 rounded-2xl border border-primary/10 bg-background-light/70 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        {order.order_date ? (
                          <span className="text-xs font-semibold text-primary">{formatDate(order.order_date) || order.order_date}</span>
                        ) : null}
                        {order.order_type ? (
                          <span className="rounded-full bg-white px-2 py-1 text-[11px] font-bold uppercase tracking-[0.15em] text-slate-500">{order.order_type}</span>
                        ) : null}
                      </div>
                      <p className="mt-2 break-all text-sm font-medium text-ink">{order.filename || `Order ${order.index + 1}`}</p>
                      {order.summary ? <p className="mt-1 text-xs text-slate-500">{order.summary}</p> : null}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleDownload(order.index)}
                      disabled={downloadingIndex === order.index}
                      className="rounded-full border border-primary/15 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-primary disabled:opacity-50"
                    >
                      {downloadingIndex === order.index ? 'Downloading…' : 'Download PDF'}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {caseData.interlocutory_applications?.length > 0 ? (
            <div className="card p-6">
              <div className="mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">pending_actions</span>
                <h2 className="text-lg font-black text-ink">Interlocutory Applications</h2>
              </div>
              <div className="space-y-3">
                {caseData.interlocutory_applications.map((item, index) => (
                  <div key={`ia-${index}`} className="rounded-2xl border border-primary/10 bg-background-light/70 px-4 py-4">
                    <p className="text-sm font-semibold text-ink">{item.reg_no || 'IA record'}</p>
                    {item.particular ? <p className="mt-1 text-sm text-slate-500">{item.particular}</p> : null}
                    <p className="mt-2 text-xs text-slate-400">
                      {[item.filing_date ? `Filed ${formatDate(item.filing_date) || item.filing_date}` : null, item.status].filter(Boolean).join(' • ') || 'Status unavailable'}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        <div className="space-y-6">
          {actsAndSections.length > 0 ? (
            <div className="card p-6">
              <div className="mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">gavel</span>
                <h2 className="text-base font-black text-ink">Acts & Sections</h2>
              </div>
              <div className="flex flex-wrap gap-2">
                {actsAndSections.map((item, index) => (
                  <span key={`act-${index}`} className="rounded-full border border-primary/15 bg-background-light px-3 py-1.5 text-xs font-semibold text-slate-600">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          {caseData.ai_analysis ? (
            <div className="card p-6">
              <div className="mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">lightbulb</span>
                <h2 className="text-base font-black text-ink">AI Analysis</h2>
              </div>
              {caseData.ai_analysis.caseSummary ? (
                <p className="text-sm text-slate-600">{caseData.ai_analysis.caseSummary}</p>
              ) : null}
              {caseData.ai_analysis.keyIssues?.length > 0 ? (
                <div className="mt-3 space-y-2">
                  {caseData.ai_analysis.keyIssues.map((issue, index) => (
                    <p key={`issue-${index}`} className="text-sm text-slate-500">• {issue}</p>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}

          {caseData.tagged_matters?.length > 0 ? (
            <div className="card p-6">
              <div className="mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">hub</span>
                <h2 className="text-base font-black text-ink">Tagged Matters</h2>
              </div>
              <div className="space-y-3">
                {caseData.tagged_matters.map((item, index) => (
                  <button
                    key={`tagged-${index}`}
                    type="button"
                    onClick={() => item.cnr && navigate(`/ecourts/case/${encodeURIComponent(item.cnr)}`)}
                    className="flex w-full items-center justify-between rounded-2xl border border-primary/10 bg-background-light/70 px-4 py-3 text-left transition-colors hover:border-primary/30 hover:bg-primary/5"
                  >
                    <div>
                      <p className="text-sm font-semibold text-ink">{item.case_number || item.cnr || 'Connected matter'}</p>
                      {item.type ? <p className="text-xs text-slate-400">{item.type}</p> : null}
                    </div>
                    <span className="material-symbols-outlined text-slate-300">chevron_right</span>
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <div className="card p-6">
            <div className="mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">travel_explore</span>
              <h2 className="text-base font-black text-ink">Continue Research</h2>
            </div>
            <div className="space-y-3">
              {caseData.petitioners?.slice(0, 2).map((party, index) => (
                <button
                  key={`petitioner-search-${index}`}
                  type="button"
                  onClick={() => goToLitigantSearch(party)}
                  className="flex w-full items-center justify-between rounded-2xl border border-primary/10 bg-background-light/70 px-4 py-3 text-left transition-colors hover:border-primary/30 hover:bg-primary/5"
                >
                  <div>
                    <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-400">Litigant Search</p>
                    <p className="mt-1 text-sm font-semibold text-ink">{party}</p>
                  </div>
                  <span className="material-symbols-outlined text-slate-300">north_east</span>
                </button>
              ))}
              {[...(caseData.petitioner_advocates || []), ...(caseData.respondent_advocates || [])].slice(0, 2).map((advocate, index) => (
                <button
                  key={`advocate-search-${index}`}
                  type="button"
                  onClick={() => goToLawyerSearch(advocate)}
                  className="flex w-full items-center justify-between rounded-2xl border border-primary/10 bg-background-light/70 px-4 py-3 text-left transition-colors hover:border-primary/30 hover:bg-primary/5"
                >
                  <div>
                    <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-400">Lawyer Search</p>
                    <p className="mt-1 text-sm font-semibold text-ink">{advocate}</p>
                  </div>
                  <span className="material-symbols-outlined text-slate-300">north_east</span>
                </button>
              ))}
              {!caseData.petitioners?.length && !(caseData.petitioner_advocates || []).length ? (
                <p className="text-sm text-slate-500">Search links will appear here when party or advocate data is available.</p>
              ) : null}
            </div>
          </div>
          </div>
      </div>
      )}
    </div>
  );
}
