// Shared navigation menu config for the public site (landing + hub pages).
// `to`   → internal react-router path (may include a #hash for in-page scroll)
// `href` → external link (http/mailto), rendered as a plain anchor.
export const PRODUCT_ITEMS = [
  { icon: 'edit_note',       label: 'AI Drafting',                 desc: 'Generate court-ready legal documents', to: '/features' },
  { icon: 'search',          label: 'AI Case Tracking',            desc: 'Live District & High Court case status', to: '/case-tracking' },
  { icon: 'layers',          label: 'Agentic Doc Analysis',        desc: 'AI-powered document intelligence',     to: '/features' },
  { icon: 'format_quote',    label: 'Citation Search',             desc: 'Find legal citations instantly',       to: '/features' },
  { icon: 'calendar_month',  label: 'Calendar Management',         desc: 'Smart hearing & deadline tracking',    to: '/features' },
  { icon: 'track_changes',   label: 'Case Strategiser',            desc: 'Build winning case strategies',        to: '/features' },
  { icon: 'people',          label: 'Client Lifecycle Management', desc: 'End-to-end client tracking',           to: '/features' },
];

export const SOLUTION_ITEMS = [
  { icon: 'balance',        label: 'For Lawyers',   desc: 'Streamline your practice',      to: '/solutions' },
  { icon: 'person',         label: 'For Litigants', desc: 'Understand your legal journey', to: '/solutions' },
  { icon: 'corporate_fare', label: 'For Law Firms', desc: 'Scale operations efficiently',  to: '/solutions' },
];

export const RESOURCE_ITEMS = [
  { icon: 'flash_on',     label: 'Live Law',                     desc: 'Real-time legal updates',     href: 'https://www.livelaw.in' },
  { icon: 'format_quote', label: 'Case Law Insights / Citation', desc: 'Precedent & citation search', to: '/resources' },
  { icon: 'list_alt',     label: 'Cause List Search',            desc: 'Daily court cause lists',     to: '/resources' },
  { icon: 'auto_awesome', label: 'AI in Law',                    desc: 'Blog & thought leadership',   to: '/resources' },
];
