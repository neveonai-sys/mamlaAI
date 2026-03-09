import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Typography, Paper, Grid, Chip, Stack, Divider, CircularProgress,
  Alert, Breadcrumbs, Link, IconButton, Tooltip,
} from '@mui/material';
import {
  Timeline, TimelineItem, TimelineSeparator, TimelineConnector, TimelineContent,
  TimelineDot, TimelineOppositeContent,
} from '@mui/lab';
import {
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  ArrowBack as ArrowBackIcon,
  ContentCopy as CopyIcon,
  Person as PersonIcon,
  Work as WorkIcon,
  Balance as BalanceIcon,
  History as HistoryIcon,
  Description as OrderIcon,
  Search as SearchIcon,
  IosShare as ShareIcon,
  PendingActions as PendingIcon,
  CheckCircleOutline as DisposedIcon,
  Schedule as ScheduleIcon,
  Event as EventIcon,
} from '@mui/icons-material';
import { getCaseByCnr, refreshCase, downloadOrder } from './ecourtsApi';

const STATUS_COLORS = {
  PENDING: 'warning',
  DISPOSED: 'success',
  TRANSFERRED: 'info',
};

const SHARE_SITES = [
  {
    label: 'X',
    color: '#000',
    href: (url, title) => `https://x.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`,
  },
  {
    label: 'FB',
    color: '#1877f2',
    href: (url) => `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`,
  },
  {
    label: 'in',
    color: '#0077b5',
    href: (url) => `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`,
  },
  {
    label: 'WA',
    color: '#25d366',
    href: (url, title) => `https://wa.me/?text=${encodeURIComponent(title + ' ' + url)}`,
  },
];

/** Numbered party list with an optional advocate sub-section */
function PartyColumn({ title, icon, borderColor, parties, advocates, onAdvocateClick }) {
  return (
    <Box
      sx={{
        flex: 1,
        borderLeft: `3px solid ${borderColor}`,
        pl: 2,
        py: 0.5,
      }}
    >
      <Stack direction="row" spacing={0.75} alignItems="center" sx={{ mb: 1 }}>
        {icon}
        <Typography variant="subtitle2" sx={{ fontWeight: 600, color: borderColor }}>
          {title}
        </Typography>
      </Stack>
      <Stack spacing={0.5} sx={{ mb: parties.length && advocates.length ? 1.5 : 0 }}>
        {parties.map((p, i) => (
          <Typography key={i} variant="body2">
            <Typography component="span" variant="caption" color="text.disabled" sx={{ mr: 0.5 }}>{i + 1}</Typography>
            {p}
          </Typography>
        ))}
      </Stack>
      {advocates.length > 0 && (
        <Box>
          <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.5 }}>
            <WorkIcon sx={{ fontSize: 13, color: 'text.secondary' }} />
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
              {title} Advocate{advocates.length > 1 ? 's' : ''}
            </Typography>
          </Stack>
          {advocates.map((a, i) => (
            <Typography key={i} variant="body2">
              <Typography component="span" variant="caption" color="text.disabled" sx={{ mr: 0.5 }}>{i + 1}</Typography>
              <Link sx={{ cursor: 'pointer' }} onClick={() => onAdvocateClick(a)}>{a}</Link>
            </Typography>
          ))}
        </Box>
      )}
    </Box>
  );
}

export default function CaseDetail() {
  const { cnr } = useParams();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [downloadError, setDownloadError] = useState(null);
  const [downloadingIdx, setDownloadingIdx] = useState(null);
  const [copied, setCopied] = useState(false);

  const fetchCase = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getCaseByCnr(cnr);
      setCaseData(resp.data?.data || null);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCase(); }, [cnr]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refreshCase(cnr);
      setTimeout(fetchCase, 2000);
    } catch (err) {
      setError(err.response?.data?.error || 'Refresh failed');
    } finally {
      setRefreshing(false);
    }
  };

  const handleCopyLink = () => {
    navigator.clipboard?.writeText(window.location.href).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  /**
   * Download an order PDF via Axios so the Authorization header is sent.
   * window.open() is a plain navigation and does NOT send the Bearer token,
   * which causes a 401. Fetching as a blob and triggering a <a> click works.
   */
  const handleDownload = async (orderIndex) => {
    setDownloadError(null);
    setDownloadingIdx(orderIndex);
    try {
      const resp = await downloadOrder(cnr, orderIndex);
      const blob = new Blob([resp.data], { type: resp.headers['content-type'] || 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      // Extract filename from Content-Disposition if present
      const disposition = resp.headers['content-disposition'] || '';
      const match = disposition.match(/filename="?([^"\s]+)"?/);
      a.download = match ? match[1] : `${cnr}-order-${orderIndex + 1}.pdf`;
      a.href = url;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      // When responseType:'blob', Axios puts a Blob (not a parsed object) in
      // err.response.data even when the server returns a JSON error body.
      // We must read the Blob as text and parse it ourselves.
      let errMsg = 'Download failed. Please try again.';
      try {
        if (err.response?.data instanceof Blob) {
          const text = await err.response.data.text();
          const json = JSON.parse(text);
          errMsg = json.error || json.message || errMsg;
        } else if (err.response?.data?.error) {
          errMsg = err.response.data.error;
        } else if (err.message) {
          errMsg = err.message;
        }
      } catch {
        // keep default message
      }
      setDownloadError(errMsg);
    } finally {
      setDownloadingIdx(null);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ maxWidth: 800, mx: 'auto', py: 4, px: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!caseData) return null;

  const {
    case_title, case_number, case_type, case_status, filing_date, registration_date,
    first_hearing_date, next_hearing_date, decision_date, judges = [],
    petitioners = [], respondents = [], petitioner_advocates = [], respondent_advocates = [],
    acts_and_sections, court_name, state, district, court_no, bench_name,
    purpose, judicial_section, orders = [], hearing_history = [],
    listing_dates = [], interlocutory_applications = [], tagged_matters = [],
    ai_analysis,
  } = caseData;

  const pageUrl = window.location.href;
  const actsArray = acts_and_sections
    ? (Array.isArray(acts_and_sections) ? acts_and_sections : [acts_and_sections])
    : [];

  return (
    <Box sx={{ maxWidth: 1280, mx: 'auto', px: { xs: 2, md: 3 }, py: 3 }}>
      {/* Breadcrumb row */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2.5 }}>
        <Tooltip title="Back">
          <IconButton size="small" onClick={() => navigate(-1)}>
            <ArrowBackIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Breadcrumbs sx={{ '& .MuiBreadcrumbs-separator': { mx: 0.5 } }}>
          <Link underline="hover" color="inherit" onClick={() => navigate('/ecourts')} sx={{ cursor: 'pointer', fontSize: 13 }}>
            Home
          </Link>
          <Link underline="hover" color="inherit" onClick={() => navigate(-1)} sx={{ cursor: 'pointer', fontSize: 13 }}>
            Cases
          </Link>
          <Typography color="text.primary" sx={{ fontSize: 13, fontFamily: 'monospace' }}>{cnr}</Typography>
        </Breadcrumbs>
      </Box>

      {/* ── Case Header ─────────────────────────────────────────────────────── */}
      <Paper
        elevation={0}
        sx={{
          border: '1px solid', borderColor: 'divider', borderRadius: 2,
          p: { xs: 2.5, md: 3 }, mb: 3,
          borderTop: '4px solid', borderTopColor: 'primary.main',
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 2 }}>
          <Typography variant="h5" sx={{ fontWeight: 700, lineHeight: 1.3, flex: 1 }}>
            {case_title}
          </Typography>
          <Stack direction="row" spacing={0.5} flexShrink={0}>
            {case_status && (
              <Chip
                label={case_status}
                color={STATUS_COLORS[case_status] || 'default'}
                size="small"
                sx={{ fontWeight: 600 }}
              />
            )}
            <Tooltip title="Refresh case data">
              <IconButton size="small" onClick={handleRefresh} disabled={refreshing}>
                {refreshing ? <CircularProgress size={16} /> : <RefreshIcon fontSize="small" />}
              </IconButton>
            </Tooltip>
          </Stack>
        </Box>

        {/* Court & Judge row */}
        <Stack direction="row" spacing={2} sx={{ mt: 1.5, mb: 1.5, flexWrap: 'wrap', rowGap: 0.5 }}>
          {court_name && (
            <Typography variant="body2" color="text.secondary">
              <Typography component="span" variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>Court: </Typography>
              {court_name}
            </Typography>
          )}
          {judges.length > 0 && (
            <Typography variant="body2" color="text.secondary">
              <Typography component="span" variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>Judge: </Typography>
              {judges.join(', ')}
            </Typography>
          )}
        </Stack>

        <Divider sx={{ mb: 1.5 }} />

        {/* Metadata strip */}
        <Stack direction="row" spacing={0} sx={{ flexWrap: 'wrap', gap: 1.5 }}>
          {case_type && (
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">Case Type</Typography>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>{case_type}</Typography>
            </Box>
          )}
          {case_number && (
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">Reg no</Typography>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>{case_number}</Typography>
            </Box>
          )}
          {filing_date && (
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">Filing no</Typography>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>{filing_date}</Typography>
            </Box>
          )}
          <Box>
            <Typography variant="caption" color="text.secondary" display="block">CNR</Typography>
            <Stack direction="row" spacing={0.5} alignItems="center">
              <Typography variant="body2" sx={{ fontWeight: 500, fontFamily: 'monospace' }}>{cnr}</Typography>
              <Tooltip title={copied ? 'Copied!' : 'Copy CNR'}>
                <IconButton size="small" sx={{ p: 0.25 }} onClick={handleCopyLink}>
                  <CopyIcon sx={{ fontSize: 14 }} />
                </IconButton>
              </Tooltip>
            </Stack>
          </Box>
          {judicial_section && (
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">Case Category</Typography>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>{judicial_section}</Typography>
            </Box>
          )}
          {next_hearing_date && (
            <Box>
              <Typography variant="caption" color="text.secondary" display="block">Next Hearing</Typography>
              <Typography variant="body2" sx={{ fontWeight: 600, color: 'primary.main' }}>{next_hearing_date}</Typography>
            </Box>
          )}
        </Stack>
      </Paper>

      {/* ── Two-column body ──────────────────────────────────────────────────── */}
      <Grid container spacing={3} alignItems="flex-start">

        {/* Left: main content */}
        <Grid item xs={12} md={8}>

          {/* Parties & Advocates */}
          <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 3, mb: 3 }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
              <BalanceIcon sx={{ color: 'primary.main', fontSize: 20 }} />
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Parties &amp; Advocates</Typography>
            </Stack>

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3} divider={<Divider orientation="vertical" flexItem />}>
              <PartyColumn
                title="Petitioner"
                icon={<PersonIcon sx={{ fontSize: 15, color: 'primary.main' }} />}
                borderColor="#1976d2"
                parties={petitioners}
                advocates={petitioner_advocates}
                onAdvocateClick={(a) => navigate(`/ecourts/lawyers/${encodeURIComponent(a)}`)}
              />
              <PartyColumn
                title="Respondent"
                icon={<PersonIcon sx={{ fontSize: 15, color: 'error.main' }} />}
                borderColor="#d32f2f"
                parties={respondents}
                advocates={respondent_advocates}
                onAdvocateClick={(a) => navigate(`/ecourts/lawyers/${encodeURIComponent(a)}`)}
              />
            </Stack>

            {actsArray.length > 0 && (
              <Box sx={{ mt: 2.5, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block', mb: 0.75 }}>
                  Acts &amp; Sections
                </Typography>
                <Typography variant="body2">{actsArray.join('; ')}</Typography>
              </Box>
            )}
          </Paper>

          {/* Case History with Orders */}
          <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 3, mb: 3 }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
              <HistoryIcon sx={{ color: 'primary.main', fontSize: 20 }} />
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Case History with Orders</Typography>
            </Stack>

            {hearing_history.length === 0 && listing_dates.length === 0 && !case_status ? (
              <Typography variant="body2" color="text.secondary" sx={{ pl: 1 }}>
                No hearing history available.
              </Typography>
            ) : (() => {
              // Parse date strings like "DD-MM-YYYY" or "YYYY-MM-DD" to comparable values
              const toMs = (d) => {
                if (!d) return 0;
                // DD-MM-YYYY
                if (/^\d{2}-\d{2}-\d{4}$/.test(d)) {
                  const [dd, mm, yyyy] = d.split('-');
                  return new Date(`${yyyy}-${mm}-${dd}`).getTime();
                }
                return new Date(d).getTime();
              };

              // Upcoming: listing_dates sorted by nearest first
              const upcoming = [...listing_dates]
                .sort((a, b) => toMs(a.date) - toMs(b.date))
                .map(ld => ({ ...ld, _kind: 'upcoming' }));

              // If next_hearing_date exists and isn't already in listing_dates, prepend it
              const upcomingDates = new Set(upcoming.map(u => u.date));
              if (next_hearing_date && !upcomingDates.has(next_hearing_date)) {
                upcoming.unshift({ date: next_hearing_date, purpose: purpose || null, _kind: 'upcoming' });
              }

              // Past hearings stay in API order (newest first)
              const past = hearing_history.map(h => ({ ...h, _kind: 'past' }));

              // Unified: upcoming (near→far) then past (newest→oldest)
              const allEntries = [...upcoming, ...past];
              const hasEntries = allEntries.length > 0;

              return (
                <Timeline position="right" sx={{ p: 0, m: 0, '& .MuiTimelineItem-root:before': { flex: 0, padding: 0 } }}>
                  {/* Status node at top */}
                  {case_status && (
                    <TimelineItem>
                      <TimelineSeparator>
                        <TimelineDot
                          color={case_status === 'DISPOSED' ? 'success' : 'warning'}
                          sx={{ boxShadow: 'none' }}
                        >
                          {case_status === 'DISPOSED'
                            ? <DisposedIcon sx={{ fontSize: 16 }} />
                            : <PendingIcon sx={{ fontSize: 16 }} />}
                        </TimelineDot>
                        {hasEntries && <TimelineConnector />}
                      </TimelineSeparator>
                      <TimelineContent sx={{ py: '6px', px: 2 }}>
                        <Box
                          sx={{
                            display: 'inline-block', px: 2, py: 1, borderRadius: 2,
                            bgcolor: case_status === 'DISPOSED' ? 'success.50' : 'warning.50',
                            border: '1px solid',
                            borderColor: case_status === 'DISPOSED' ? 'success.200' : 'warning.200',
                          }}
                        >
                          <Typography variant="body2" sx={{ fontWeight: 700, color: case_status === 'DISPOSED' ? 'success.800' : 'warning.800' }}>
                            {case_status}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">Final Status</Typography>
                        </Box>
                      </TimelineContent>
                    </TimelineItem>
                  )}

                  {/* All entries: upcoming then past — one continuous chain */}
                  {allEntries.map((entry, i) => {
                    const isUpcoming = entry._kind === 'upcoming';
                    const isLast = i === allEntries.length - 1;
                    return (
                      <TimelineItem key={i}>
                        <TimelineSeparator>
                          <TimelineDot
                            variant={isUpcoming ? 'filled' : 'outlined'}
                            sx={{
                              boxShadow: 'none',
                              borderWidth: 2,
                              bgcolor: isUpcoming ? 'primary.main' : 'transparent',
                              borderColor: isUpcoming ? 'primary.main' : 'primary.main',
                              p: isUpcoming ? '4px' : '5px',
                            }}
                          >
                            {isUpcoming && <ScheduleIcon sx={{ fontSize: 14, color: '#fff' }} />}
                          </TimelineDot>
                          {!isLast && <TimelineConnector />}
                        </TimelineSeparator>
                        <TimelineContent sx={{ py: '4px', px: 2, pb: isLast ? 0 : '12px' }}>
                          <Typography
                            variant="caption"
                            sx={{ fontWeight: 700, color: isUpcoming ? 'primary.main' : 'text.primary' }}
                          >
                            {entry.date}
                            {isUpcoming && (
                              <Typography component="span" variant="caption" sx={{ ml: 0.75, color: 'primary.light', fontWeight: 400 }}>
                                (upcoming)
                              </Typography>
                            )}
                          </Typography>
                          {entry.purpose && (
                            <Typography variant="body2" sx={{ fontWeight: isUpcoming ? 600 : 500 }}>
                              {entry.purpose}
                            </Typography>
                          )}
                          {entry.business_on_date && (
                            <Typography variant="caption" color="text.secondary" display="block">
                              {entry.business_on_date}
                            </Typography>
                          )}
                          {entry.judge && (
                            <Typography variant="caption" color="text.secondary" display="block">
                              Before: {entry.judge}
                            </Typography>
                          )}
                        </TimelineContent>
                      </TimelineItem>
                    );
                  })}
                </Timeline>
              );
            })()}
          </Paper>

          {/* Orders */}
          {orders.length > 0 && (
            <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 3, mb: 3 }}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
                <OrderIcon sx={{ color: 'primary.main', fontSize: 20 }} />
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  Orders &amp; Judgments
                  <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 1 }}>({orders.length})</Typography>
                </Typography>
              </Stack>

              {downloadError && (
                <Alert severity="error" onClose={() => setDownloadError(null)} sx={{ mb: 2 }}>
                  {downloadError}
                </Alert>
              )}

              <Stack spacing={1.5}>
                {orders.map((o) => (
                  <Box
                    key={o.index}
                    sx={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      p: 1.5, borderRadius: 1.5,
                      border: '1px solid', borderColor: 'divider',
                      '&:hover': { bgcolor: 'action.hover' },
                    }}
                  >
                    <Box sx={{ flex: 1, mr: 1 }}>
                      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                        {o.order_date && (
                          <Typography variant="caption" sx={{ fontWeight: 600, color: 'primary.main' }}>
                            {o.order_date}
                          </Typography>
                        )}
                        {o.order_type && (
                          <Chip label={o.order_type} size="small" variant="outlined" />
                        )}
                      </Stack>
                      {o.summary && (
                        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                          {o.summary}
                        </Typography>
                      )}
                    </Box>
                    <Tooltip title="Download PDF">
                      <span>
                        <IconButton
                          size="small"
                          disabled={downloadingIdx === o.index}
                          onClick={() => handleDownload(o.index)}
                        >
                          {downloadingIdx === o.index
                            ? <CircularProgress size={16} />
                            : <DownloadIcon fontSize="small" />}
                        </IconButton>
                      </span>
                    </Tooltip>
                  </Box>
                ))}
              </Stack>
            </Paper>
          )}

          {/* Interlocutory Applications */}
          {interlocutory_applications.length > 0 && (
            <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 3, mb: 3 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
                Interlocutory Applications
                <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                  ({interlocutory_applications.length})
                </Typography>
              </Typography>
              <Stack spacing={1.5}>
                {interlocutory_applications.map((ia, i) => (
                  <Box key={i} sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', borderRadius: 1.5 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>{ia.reg_no}</Typography>
                    {ia.particular && (
                      <Typography variant="body2" color="text.secondary">{ia.particular}</Typography>
                    )}
                    <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
                      {ia.filing_date && (
                        <Chip label={`Filed: ${ia.filing_date}`} size="small" variant="outlined" />
                      )}
                      {ia.status && (
                        <Chip label={ia.status} size="small" color={ia.status === 'DISPOSED' ? 'success' : 'warning'} variant="outlined" />
                      )}
                    </Stack>
                  </Box>
                ))}
              </Stack>
            </Paper>
          )}
        </Grid>

        {/* Right: sidebar */}
        <Grid item xs={12} md={4}>

          {/* Share This Case */}
          <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2.5, mb: 2.5 }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
              <ShareIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>Share This Case</Typography>
            </Stack>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {SHARE_SITES.map((site) => (
                <Tooltip key={site.label} title={`Share on ${site.label}`}>
                  <Box
                    component="a"
                    href={site.href(pageUrl, case_title || cnr)}
                    target="_blank"
                    rel="noopener noreferrer"
                    sx={{
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      width: 40, height: 40, borderRadius: '50%',
                      border: '1.5px solid', borderColor: site.color,
                      color: site.color,
                      fontWeight: 700, fontSize: 12, textDecoration: 'none',
                      transition: 'all 0.15s',
                      '&:hover': { bgcolor: site.color, color: '#fff' },
                    }}
                  >
                    {site.label}
                  </Box>
                </Tooltip>
              ))}
              <Tooltip title={copied ? 'Link copied!' : 'Copy link'}>
                <IconButton
                  size="small"
                  onClick={handleCopyLink}
                  sx={{
                    width: 40, height: 40,
                    border: '1.5px solid', borderColor: 'divider',
                    borderRadius: '50%',
                    color: copied ? 'success.main' : 'text.secondary',
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                >
                  <CopyIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </Tooltip>
            </Stack>
          </Paper>

          {/* Similar Case Search */}
          <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2.5, mb: 2.5 }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
              <SearchIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>Similar Case Search</Typography>
            </Stack>

            {/* Same Parties */}
            {[...petitioners, ...respondents].length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.75 }}>
                  <PersonIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    Same Parties
                  </Typography>
                </Stack>
                <Stack direction="row" flexWrap="wrap" useFlexGap gap={0.75}>
                  {/* Full title chip first */}
                  {case_title && (
                    <Chip
                      label={case_title.length > 40 ? case_title.slice(0, 40) + '…' : case_title}
                      size="small"
                      sx={{ cursor: 'pointer', maxWidth: '100%' }}
                      onClick={() => navigate(`/ecourts/litigants?q=${encodeURIComponent(petitioners[0] || '')}`)}
                    />
                  )}
                  {[...petitioners, ...respondents].slice(0, 4).map((p, i) => (
                    <Chip
                      key={i}
                      label={p}
                      size="small"
                      variant="outlined"
                      sx={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/ecourts/litigants?q=${encodeURIComponent(p)}`)}
                    />
                  ))}
                </Stack>
              </Box>
            )}

            {/* Lawyers */}
            {[...petitioner_advocates, ...respondent_advocates].length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.75 }}>
                  <WorkIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    Lawyers
                  </Typography>
                </Stack>
                <Stack direction="row" flexWrap="wrap" useFlexGap gap={0.75}>
                  {[...new Set([...petitioner_advocates, ...respondent_advocates])].slice(0, 5).map((a, i) => (
                    <Chip
                      key={i}
                      label={`Advocate ${a}`}
                      size="small"
                      variant="outlined"
                      sx={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/ecourts/lawyers/${encodeURIComponent(a)}`)}
                    />
                  ))}
                </Stack>
              </Box>
            )}

            {/* Judges */}
            {judges.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.75 }}>
                  <BalanceIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    Judges
                  </Typography>
                </Stack>
                <Stack direction="row" flexWrap="wrap" useFlexGap gap={0.75}>
                  {court_name && (
                    <Chip
                      label={court_name}
                      size="small"
                      variant="outlined"
                      sx={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/ecourts/search?q=${encodeURIComponent(court_name)}&type=general`)}
                    />
                  )}
                  {judges.slice(0, 3).map((j, i) => (
                    <Chip
                      key={i}
                      label={j}
                      size="small"
                      variant="outlined"
                      sx={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/ecourts/search?q=${encodeURIComponent(j)}&type=judge`)}
                    />
                  ))}
                </Stack>
              </Box>
            )}

            {/* Acts & Sections */}
            {actsArray.length > 0 && (
              <Box>
                <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.75 }}>
                  <OrderIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    Acts &amp; Sections
                  </Typography>
                </Stack>
                <Stack direction="row" flexWrap="wrap" useFlexGap gap={0.75}>
                  {actsArray.slice(0, 4).map((act, i) => (
                    <Chip
                      key={i}
                      label={act}
                      size="small"
                      variant="outlined"
                      sx={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/ecourts/search?q=${encodeURIComponent(act)}&type=general`)}
                    />
                  ))}
                </Stack>
              </Box>
            )}
          </Paper>

          {/* AI Analysis */}
          {ai_analysis && (
            <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2.5, mb: 2.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>AI Analysis</Typography>
              {ai_analysis.caseSummary && (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  {ai_analysis.caseSummary}
                </Typography>
              )}
              {ai_analysis.keyIssues?.length > 0 && (
                <Box>
                  <Typography variant="caption" sx={{ fontWeight: 700 }}>Key Issues</Typography>
                  {ai_analysis.keyIssues.map((issue, i) => (
                    <Typography key={i} variant="body2" color="text.secondary">• {issue}</Typography>
                  ))}
                </Box>
              )}
            </Paper>
          )}

          {/* Tagged Matters */}
          {tagged_matters.length > 0 && (
            <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>Tagged Matters</Typography>
              {tagged_matters.map((tm, i) => (
                <Box key={i} sx={{ mb: 1 }}>
                  <Chip label={tm.type || 'CONNECTED'} size="small" variant="outlined" sx={{ mr: 1 }} />
                  <Link
                    sx={{ cursor: 'pointer' }}
                    onClick={() => tm.cnr && navigate(`/ecourts/case/${tm.cnr}`)}
                  >
                    {tm.case_number || tm.cnr}
                  </Link>
                </Box>
              ))}
            </Paper>
          )}
        </Grid>
      </Grid>
    </Box>
  );
}
