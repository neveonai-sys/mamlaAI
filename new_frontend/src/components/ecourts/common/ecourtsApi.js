/**
 * eCourts API client — wired to the v2 backend (ecourt_scrapped Django app).
 *
 * Backend prefix: /api/ecourts/v2/
 * All case lookups are POST-based (no URL-param style).
 */
import apiClient from '../../../services/api';

const BASE = 'ecourts/v2';

// ─── Response helpers ─────────────────────────────────────────────────────────

export function unwrapEcourtsPayload(response) {
  return response?.data?.data ?? response?.data ?? null;
}

/**
 * Normalise the raw FastAPI scraper response (nested dicts with dynamic keys
 * from eCourts HTML) into the flat shape that CaseDetail.jsx renders.
 */
export function normalizeCaseData(raw) {
  if (!raw) return null;
  if (Array.isArray(raw.petitioners)) return raw;

  const cd = raw.case_details || {};
  const cs = raw.case_status || {};

  // eCourts party strings pack multiple parties as "1) Foo 2) Bar 3) Baz" in
  // one element.  Split them out so each party gets its own card.
  function extractSegments(entry) {
    const rx = /\d+\)\s*([\s\S]+?)(?=\s*\d+\)\s|$)/g;
    const matches = [...entry.matchAll(rx)];
    if (matches.length) return matches.map((m) => m[1].trim()).filter(Boolean);
    const stripped = entry.replace(/^\d+\)\s*/, '').trim();
    return stripped ? [stripped] : [];
  }

  function parsePartyList(rawList) {
    const parties = [];
    const advocates = [];
    for (const entry of rawList || []) {
      for (const seg of extractSegments(entry)) {
        // "Name Advocate- AdvocateName"  or  "Name - Adv. Name"
        const advMatch = seg.match(/^(.+?)\s+Advocate[-\s:]+(.+)$/i);
        if (advMatch) {
          parties.push(advMatch[1].trim());
          const adv = advMatch[2].trim();
          if (adv && adv !== '-') advocates.push(adv);
        } else {
          parties.push(seg);
        }
      }
    }
    return { parties, advocates };
  }

  // The scraper emits case_history rows with dynamic column-header keys.
  // Reliable data: business_params.nextdate1 = Business on Date for this row.
  // The second date-shaped key in the row = Hearing Date (next scheduled).
  // Self-referential entries (k===v) identify judge name and case stage.
  function parseHistoryEntry(h) {
    const bp = h.business_params || {};
    const dateRx = /^\d{2}-\d{2}-\d{4}$/;

    // nextdate1 (YYYYMMDD) → "DD-MM-YYYY" → Business on Date for this row
    const nd = (bp.nextdate1 || '').replace(/\D/g, '');
    const businessDate =
      nd.length === 8
        ? `${nd.slice(6, 8)}-${nd.slice(4, 6)}-${nd.slice(0, 4)}`
        : bp.businessDate || '';

    // Date-shaped keys in the row: the one that differs from businessDate is
    // the Hearing Date (next scheduled appearance).
    const dateKeys = Object.keys(h).filter((k) => dateRx.test(k));
    const hearingDate = dateKeys.find((k) => k !== businessDate) || '';

    // Regex to detect long-form judge/court designation keys:
    // e.g. "Additional Sessions Judge-06", "Metropolitan Magistrate-IV"
    const JUDGE_TITLE_RX = /\b(judge|magistrate|sessions|district|additional|chief|family|metropolitan|special|civil|criminal)\b/i;

    let judge = '';
    let purpose = '';
    for (const [k, v] of Object.entries(h)) {
      if (k === 'business_params' || typeof v !== 'string') continue;
      if (dateRx.test(k)) continue;
      if (k.startsWith('col_')) continue;

      const isAllCaps = k === k.toUpperCase();
      // Short uppercase court abbreviation: JM, CJM, ADJ, CMM, JMFC, etc. (≤5 chars, no spaces/dots)
      const isShortAbbr = isAllCaps && k.length >= 2 && k.length <= 5 && !/[\s./\\]/.test(k);

      if (isShortAbbr) {
        // Abbreviation key — value may be full title ("JM cum AM-I"), same ("JM"), or empty → fall back to key
        judge = judge || (v.trim() || k);
      } else if (JUDGE_TITLE_RX.test(k)) {
        // Long-form judge designation key ("Additional Sessions Judge-06") — value often empty → fall back to key
        judge = judge || (v.trim() || k);
      } else if (v.trim() && !dateRx.test(v)) {
        // Non-date, non-empty value in any other key → purpose/stage
        // e.g. "Prosecution Evidence":"Prosecution Evidence", "Disposed":"Awaited for final form..."
        purpose = purpose || (k === v ? k : v.trim());
      }
    }
    return {
      business_date: businessDate,
      hearing_date: hearingDate,
      judge,
      purpose: purpose || bp.disposal_flag || '',
      business_params: bp,
    };
  }

  const pet = parsePartyList(raw.petitioner_and_advocate);
  const res = parsePartyList(raw.respondent_and_advocate);
  const courtJudge = cs['Court Number and Judge'] || '';
  const histEntries = (raw.case_history || []).map(parseHistoryEntry);
  const judges = [...new Set(histEntries.map((h) => h.judge).filter(Boolean))];

  const pFirst = pet.parties[0] || '';
  const rFirst = res.parties[0] || '';
  const rCount = res.parties.length;

  return {
    cnr: raw.cino || (cd['CNR Number'] || '').replace(/\s*\(.*$/, '').trim(),
    case_status: cs['Case Stage'] || cs['Case Status'] || '',
    case_title:
      pFirst && rFirst
        ? `${pFirst} vs ${rFirst}${rCount > 1 ? ` & ${rCount - 1} other${rCount > 2 ? 's' : ''}` : ''}`
        : pFirst || rFirst || '',
    court_name: raw.court_name || '',
    state: '',
    district: '',
    court_no: courtJudge.split(/\s*[-–—]\s*/)[0]?.trim() || '',
    bench_name:
      courtJudge.split(/\s*[-–—]\s*/).slice(1).join(' — ').trim() ||
      judges[0] ||
      '',
    case_type: cd['Case Type'] || '',
    case_number: cd['Registration Number'] || cd['Filing Number'] || '',
    filing_number: cd['Filing Number'] || '',
    e_filing_number: cd['e-Filing Number'] || '',
    e_filing_date: cd['e-Filing Date'] || '',
    purpose: '',
    judicial_section: '',
    filing_date: cd['Filing Date'] || '',
    registration_date: cd['Registration Date'] || '',
    first_hearing_date: cs['First Hearing Date'] || '',
    next_hearing_date: cs['Next Hearing Date'] || '',
    decision_date: cs['Decision Date'] || '',
    judges,
    petitioners: pet.parties,
    respondents: res.parties,
    petitioner_advocates: [...new Set(pet.advocates)],
    respondent_advocates: [...new Set(res.advocates)],
    listing_dates: [],
    hearing_history: histEntries,
    orders: (raw.interim_orders || []).map((o, i) => ({
      index: i,
      order_date: o['Order Date'] || '',
      order_type: o['Order Details'] || o['Order Type'] || 'Order',
      pdf_params: o.pdf_params || null,
    })),
    acts_and_sections: (raw.acts || []).map((a) =>
      [a['Under Act(s)'], a['Under Section(s)']].filter(Boolean).join(' — ')
    ),
    fir_details:
      raw.fir_details && Object.keys(raw.fir_details).length > 0
        ? raw.fir_details
        : null,
    case_transfer_details: raw.case_transfer_details || [],
    interlocutory_applications: [],
    ai_analysis: null,
    tagged_matters: [],
  };
}

// ─── Case endpoints ───────────────────────────────────────────────────────────

export const getCaseByCnr = (cnr) =>
  apiClient.post(`${BASE}/case/detail/`, { cnr_number: cnr });

export const refreshCase = (cnr) =>
  apiClient.post(`${BASE}/case/detail/`, { cnr_number: cnr });

export const downloadOrderPdf = (pdfParams) =>
  apiClient.post(`${BASE}/case/order-pdf/`, pdfParams, { responseType: 'blob' });

// ─── Dropdown / structure endpoints ───────────────────────────────────────────

export const getStates = () => apiClient.get(`${BASE}/states/`);

export const getDistricts = (stateCode) =>
  apiClient.post(`${BASE}/districts/`, { state_code: stateCode });

export const getComplexes = (stateCode, distCode) =>
  apiClient.post(`${BASE}/complexes/`, {
    state_code: stateCode,
    dist_code: distCode,
  });

export const getHighCourts = () =>
  Promise.resolve({ data: { high_courts: [] } });

export const getCourtStructure = () =>
  Promise.resolve({ data: { total_states: 0, high_courts: [] } });

// ─── Search stubs (v2 uses court-scoped search; unified search not available) ─

export const searchEcourts = () =>
  Promise.resolve({ data: { case_list: [], total: 0, total_pages: 0 } });

export const getEcourtsDefaults = () =>
  Promise.resolve({ data: { data: { case_list: [] } } });

export const getCauseList = (params) =>
  apiClient.post(`${BASE}/causelist/fetch/`, params);

export const getCauseListDates = () =>
  Promise.resolve({ data: { dates: [] } });

export const getCourts = (stateCode, distCode, courtComplexCode, estCode) =>
  apiClient.post(`${BASE}/courts/`, {
    state_code: stateCode,
    dist_code: distCode,
    court_complex_code: courtComplexCode,
    est_code: estCode,
  });

// ─── District-scoped stubs (v2 does not have these; prevents import errors) ──

const emptyStub = () => Promise.resolve({ data: { data: [] } });
export const getDcStates = emptyStub;
export const getDcDistricts = emptyStub;
export const getDcCourtComplexes = emptyStub;
export const getDcCourtsWithinComplex = emptyStub;
export const getDistrictCauseList = emptyStub;
export const searchDistrictCaseStatus = emptyStub;
export const searchDistrictCaveat = emptyStub;
export const searchDistrictCourtOrders = emptyStub;
