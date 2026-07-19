// Feature cards shown on the Features page and the /website overview.
// `image` (optional) is a real product screenshot served from /screenshots/*.png
// (copied into dist via webpack.common.js). Missing files degrade gracefully.
export const FEATURES = [
  { icon: 'edit_note',       title: 'AI Legal Drafting',              tag: 'Core', image: '/screenshots/drafting.png',  desc: 'Generate petitions, affidavits, contracts, legal notices and court documents using AI trained on Indian legal workflows — court-formatted and ready to file.' },
  { icon: 'search',          title: 'eCourt Integration',             tag: 'Live', image: '/screenshots/ecourt.png',    desc: 'Track case status, hearing dates, orders and cause lists directly from Indian courts. eCourts case tracking for all 25 High Courts and District Courts.' },
  { icon: 'calendar_month',  title: 'Legal Calendar Software',        tag: 'Core', image: '/screenshots/calendar.png',  desc: 'Legal calendar software with hearing reminders, filing deadlines and court schedule tracking. Never miss a hearing date or filing deadline again.' },
  { icon: 'layers',          title: 'AI Document Analysis',           tag: 'Core', image: '/screenshots/doc-intel.png', desc: 'AI document review software for contracts, pleadings, judgments and legal notices — extract key clauses, identify risks, summarize holdings.' },
  { icon: 'track_changes',   title: 'Case Strategiser',               tag: 'Core', image: '/screenshots/cases.png',     desc: 'AI-powered legal research and case strategy assistant for Indian lawyers — analyse facts, identify applicable laws, suggest arguments and map outcomes.' },
  { icon: 'format_quote',    title: 'Citation Search',                tag: 'Core', desc: 'Search judgments, precedents, sections and case citations across Indian courts. Legal research software to build stronger arguments faster.' },
  { icon: 'people',          title: 'Legal CRM Software',             tag: 'Core', desc: 'Legal CRM software for lawyers and law firms — track every client from intake to resolution, communications, documents, billing milestones and case progress.' },
  { icon: 'shield',          title: 'Secure & Private',               tag: null,   desc: 'Enterprise-grade security for legal case files and client information. AES-256 encryption, DPDP Act 2023 compliant, India-hosted servers.' },
];
