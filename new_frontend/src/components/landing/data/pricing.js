// Pricing plans shown on the Pricing page and the /website overview.
export const LAWYER_PLANS = [
  {
    name: 'Free Trial',
    subtitle: 'Explore with no commitment',
    price: '₹0',
    period: '30 days',
    cta: 'Start Free',
    recommended: false,
    items: ['24 Legal Chat queries', '8 Doc Analysis sessions', '20 AI Drafts', '12 Drafting actions', '5 AI Suggestions', '2 Case Companion sessions', 'eCourts CNR Lookup (50/month)', 'Order PDF Downloads (5/month)'],
  },
  {
    name: 'Law Student',
    subtitle: 'For students & interns',
    price: '₹220',
    period: '/month',
    cta: 'Join as Student',
    recommended: false,
    offer: '₹50 off first renewal',
    items: ['40 Legal Chat queries', '12 Doc Analysis sessions', '25 AI Drafts', '15 Drafting actions', '8 AI Suggestions', '1 Case Companion session', 'eCourts CNR Lookup (50/month)', 'Order Downloads (8/month)', 'College name verification'],
  },
  {
    name: 'Basic',
    subtitle: 'For solo practitioners getting started',
    price: '₹1,000',
    period: '/month',
    cta: 'Join Beta',
    recommended: false,
    items: ['200 Legal Chat queries', '50 Doc Analysis sessions', '90 AI Drafts', '75 Drafting actions', '30 AI Suggestions', '12 Case Companion sessions', 'Unlimited eCourts CNR Lookup', 'Order Downloads (60/month)'],
  },
  {
    name: 'Premium',
    subtitle: 'For high-volume practitioners',
    price: '₹3,000',
    period: '/month',
    cta: 'Join Beta — Lock Price',
    recommended: true,
    items: ['600 Legal Chat queries', '150 Doc Analysis sessions', '250 AI Drafts', '200 Drafting actions', '90 AI Suggestions', '40 Case Companion sessions', 'Unlimited eCourts CNR Lookup', 'Order Downloads (200/month)', 'Priority support'],
  },
];

export const NAGRIK_PLANS = [
  {
    name: 'Nagrik Free',
    subtitle: 'For citizens seeking legal help',
    price: '₹0',
    period: '30 days',
    cta: 'Start Free',
    recommended: false,
    items: ['5 Legal Chat queries', '2 Doc Analysis sessions', '1 AI Draft', 'eCourts CNR Lookup (10/month)', 'Track your case status', 'Plain-language summaries'],
    blocked: ['Drafting Actions — Lawyer only', 'AI Suggestions — Lawyer only', 'Case Companion — Lawyer only'],
  },
  {
    name: 'Nagrik Basic',
    subtitle: 'For active litigants',
    price: '₹129',
    period: '/month',
    cta: 'Join Beta',
    recommended: true,
    offer: '₹50 off first renewal',
    items: ['30 Legal Chat queries', '8 Doc Analysis sessions', '5 AI Drafts', 'eCourts CNR Lookup (30/month)', 'Order PDF Downloads (3/month)', 'Document upload & analysis'],
    blocked: ['Drafting Actions — Lawyer only', 'AI Suggestions — Lawyer only', 'Case Companion — Lawyer only'],
  },
];
