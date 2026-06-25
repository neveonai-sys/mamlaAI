import React, { useEffect, useRef, useState } from 'react';
import MamlaLogoIcon from '../common/MamlaLogoIcon';
import { Link, useNavigate } from 'react-router-dom';
import { useIconFont } from '../../hooks/useIconFont';

// ─── Static data ──────────────────────────────────────────────────────────────

const STAT_CARDS = [
  { icon: 'gavel',           value: '4.8', unit: 'Cr', desc: 'Total pending cases across all district & High Courts in India',       source: 'NJDG Live · Updated daily' },
  { icon: 'check_circle',    value: '2.2', unit: 'L',  desc: 'Cases disposed this month across all High Courts and District Courts',  source: 'NJDG Live · Updated monthly' },
  { icon: 'account_balance', value: '72',  unit: 'K',  desc: 'Pending matters before the Supreme Court of India',                    source: 'SCI Portal · Updated weekly' },
  { icon: 'today',           value: '68',  unit: '',   desc: "Items on today's Supreme Court cause list",                            source: 'SC Daily Cause List' },
];

const NEWS_ITEMS = [
  { source: 'LiveLaw', tone: 'bg-primary/20 text-primary-soft',    text: 'SC bench issues directions on undertrial prisoners; seeks state compliance reports', time: '2 hours ago' },
  { source: 'B&B',     tone: 'bg-amber-500/20 text-amber-300',     text: 'Delhi HC: landlord cannot evict tenant without compliance of Rent Control Act provisions', time: '4 hours ago' },
  { source: 'SCI',     tone: 'bg-emerald-500/20 text-emerald-400', text: 'Constitution bench to take up PMLA provisions challenge; listed for July arguments', time: 'Yesterday' },
  { source: 'LiveLaw', tone: 'bg-primary/20 text-primary-soft',    text: 'BCI issues advisory on Bar Council elections; sets deadline for state bar council compliance', time: 'Yesterday' },
];

const FEATURES = [
  { icon: 'edit_note',       title: 'AI Legal Drafting',              tag: 'Core', desc: 'Generate petitions, affidavits, contracts, legal notices and court documents using AI trained on Indian legal workflows — court-formatted and ready to file.' },
  { icon: 'search',          title: 'eCourt Integration',             tag: 'Live', desc: 'Track case status, hearing dates, orders and cause lists directly from Indian courts. eCourts case tracking for all 25 High Courts and District Courts.' },
  { icon: 'calendar_month',  title: 'Legal Calendar Software',        tag: 'Core', desc: 'Legal calendar software with hearing reminders, filing deadlines and court schedule tracking. Never miss a hearing date or filing deadline again.' },
  { icon: 'layers',          title: 'AI Document Analysis',           tag: 'Core', desc: 'AI document review software for contracts, pleadings, judgments and legal notices — extract key clauses, identify risks, summarize holdings.' },
  { icon: 'track_changes',   title: 'Case Strategiser',               tag: 'Core', desc: 'AI-powered legal research and case strategy assistant for Indian lawyers — analyse facts, identify applicable laws, suggest arguments and map outcomes.' },
  { icon: 'format_quote',    title: 'Citation Search',                tag: 'Core', desc: 'Search judgments, precedents, sections and case citations across Indian courts. Legal research software to build stronger arguments faster.' },
  { icon: 'people',          title: 'Legal CRM Software',             tag: 'Core', desc: 'Legal CRM software for lawyers and law firms — track every client from intake to resolution, communications, documents, billing milestones and case progress.' },
  { icon: 'shield',          title: 'Secure & Private',               tag: null,   desc: 'Enterprise-grade security for legal case files and client information. AES-256 encryption, DPDP Act 2023 compliant, India-hosted servers.' },
];

const PERSONAS = [
  {
    icon: 'balance',
    title: 'For Lawyers',
    points: [
      'AI legal drafting, legal research & citation search',
      'Case calendar with hearing alerts & filing deadlines',
      'eCourt sync for live case status & cause lists',
      'Software for lawyers in India — solo & chamber',
    ],
  },
  {
    icon: 'person',
    title: 'For Litigants',
    points: [
      'Track court cases and case status online',
      'Understand legal documents in plain language',
      'AI guidance on legal rights and next steps',
      'Connect with lawyers and follow your matter',
    ],
  },
  {
    icon: 'school',
    title: 'For Law Students',
    points: [
      'Practice legal drafting with AI assistance',
      'Conduct legal research using Indian case law',
      'eCourts live case research — no bar enrolment needed',
      'Learn Indian law with AI-powered study tools',
    ],
  },
  {
    icon: 'corporate_fare',
    title: 'For Law Firms',
    points: [
      'Law firm management software with multi-lawyer support',
      'Client lifecycle dashboard — full matter tracking',
      'Firm-wide calendar coordination & deadline management',
      'Document analysis and legal workflow automation at scale',
    ],
  },
];

const LAWYER_PLANS = [
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
    name: 'Vakil Starter',
    subtitle: 'For solo practitioners',
    price: '₹349',
    period: '/month',
    cta: 'Join Beta',
    recommended: false,
    offer: '₹50 off first renewal',
    items: ['50 Legal Chat queries', '15 Doc Analysis sessions', '30 AI Drafts', '20 Drafting actions', '10 AI Suggestions', '3 Case Companion sessions', 'CNR Lookup (60/month)', 'Order Downloads (15/month)'],
  },
  {
    name: 'Vakil Pro',
    subtitle: 'For serious practitioners',
    price: '₹749',
    period: '/month',
    cta: 'Join Beta — Lock Price',
    recommended: true,
    offer: '₹50 off first renewal',
    items: ['150 Legal Chat queries', '40 Doc Analysis sessions', '70 AI Drafts', '60 Drafting actions', '25 AI Suggestions', '10 Case Companion sessions', 'Unlimited eCourts CNR Lookup', 'Order Downloads (50/month)'],
  },
  {
    name: 'Vakil Power',
    subtitle: 'Maximum capacity',
    price: '₹1,349',
    period: '/month',
    cta: 'Join Beta — Lock Price',
    recommended: false,
    offer: '₹50 off first renewal',
    items: ['400 Legal Chat queries', '100 Doc Analysis sessions', '150 AI Drafts', '150 Drafting actions', '75 AI Suggestions', '30 Case Companion sessions', 'Unlimited eCourts CNR Lookup', 'Order Downloads (150/month)', 'Priority support'],
  },
];

const NAGRIK_PLANS = [
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

const PRICING_PLANS = LAWYER_PLANS;

const FAQS = [
  { q: 'What is AI legal software?', a: "AI legal software uses artificial intelligence to automate and assist with legal tasks such as drafting documents, conducting legal research, tracking court cases, managing clients, and analysing legal documents. Mamla AI is an AI-powered legal practice management software built specifically for Indian lawyers, law firms, litigants and law students." },
  { q: 'What is the best legal practice management software in India?', a: "Mamla AI is a comprehensive AI legal practice management platform purpose-built for the Indian legal system. It combines AI legal drafting, eCourts case tracking, legal research, client lifecycle management, citation search and document analysis — all in one platform designed for advocates, chambers and law firms in India." },
  { q: 'How can lawyers automate legal drafting?', a: "Mamla AI's AI drafting tool allows lawyers to generate court-ready petitions, affidavits, contracts, legal notices and other documents in seconds. The AI is trained on Indian legal formats and court workflows, giving advocates a strong first draft that they can review and customise before filing." },
  { q: 'How does eCourts case tracking work?', a: "Mamla AI integrates directly with the eCourts ecosystem to pull live case status, hearing dates, orders and cause lists from all 25 High Courts and District Courts across India. Lawyers can track any CNR number, receive automated hearing reminders, and monitor their entire case portfolio from one dashboard." },
  { q: 'Can AI help with legal research?', a: "Yes. Mamla AI's Case Strategiser and Citation Search tools help Indian lawyers conduct faster legal research. You can search judgments, trace legal precedents, find relevant sections and build case arguments using AI — without manually sifting through law databases." },
  { q: 'How can law firms manage cases efficiently?', a: "Mamla AI provides law firm management software with multi-lawyer case management, client lifecycle tracking, firm-wide calendar coordination, document analysis at scale, and matter-level role-based access control — giving law firms a single platform to manage their entire practice." },
  { q: 'Is legal practice management software secure?', a: "Yes. Mamla AI uses AES-256 encryption for all data at rest and in transit. All data is stored on India-located servers in compliance with the Digital Personal Data Protection Act, 2023. Client matter data is never used to train AI models without explicit written consent." },
  { q: 'Can litigants track court cases online?', a: "Yes. Litigants on Mamla AI can track their case status, hearing dates and court orders directly through the platform's eCourts integration — without navigating government portals. Plain-language summaries help litigants understand what is happening in their matter." },
  { q: 'Is Mamla.AI drafting output admissible in court?', a: "AI-generated drafts are working tools, not final submissions. Every document must be reviewed, edited, and approved by the responsible advocate before filing. Mamla AI helps you get to a strong first draft faster — the professional judgement remains yours." },
  { q: 'Which courts and jurisdictions are currently supported?', a: 'eCourts case status, orders, and cause lists are available for all 25 High Courts and District Courts via live integration. Supreme Court and Tribunal feeds are being added progressively.' },
];

const LEGAL_DOCS = {
  terms: {
    title: 'Terms of Service',
    date: 'Effective Date: 1 January 2026 | Governing Law: Indian Law',
    sections: [
      { heading: '1. Acceptance of Terms', body: 'By accessing or using the Mamla.AI platform, operated by Neveon AI Technologies Pvt. Ltd. ("Company"), you agree to these Terms. This constitutes a legally binding agreement under the Information Technology Act, 2000.' },
      { heading: '2. Eligibility', body: 'The Platform is intended solely for enrolled advocates, law firms, and legal professionals in India. By registering, you represent that you are enrolled with a State Bar Council under the Advocates Act, 1961, or an authorised representative thereof.' },
      { heading: '3. Not Legal Advice', body: 'Mamla.AI provides AI-powered tools to assist legal professionals. The Platform does not provide legal advice and does not create an advocate-client relationship. All AI-generated content must be reviewed by a qualified legal professional before use in any legal proceeding.' },
      { heading: '4. Data Processing & Confidentiality', body: 'All data is processed under AES-256 encryption. Client matter content will not be used for training AI models without explicit opt-in consent. Data is stored within India in compliance with the Digital Personal Data Protection Act, 2023.' },
      { heading: '5. Limitation of Liability', body: "The Company's total aggregate liability shall not exceed the amount paid by you in the three months preceding the claim. The Company is not liable for consequences of using unreviewed AI-generated output in legal proceedings." },
      { heading: '6. Governing Law & Disputes', body: 'These Terms are governed by Indian law. Unresolved disputes shall be referred to arbitration under the Arbitration and Conciliation Act, 1996, with the seat at Kolkata, West Bengal.' },
      { heading: '7. Grievance Officer', body: 'Designated Grievance Officer: RM, Neveon AI Technologies Pvt. Ltd. Email: neveon.ai@gmail.com. Complaints acknowledged within 24 hours and resolved within 30 days (IT Act, 2000).' },
    ],
  },
  privacy: {
    title: 'Privacy Policy',
    date: 'Effective Date: 1 January 2026 | Compliance: DPDP Act 2023 & IT Act 2000',
    sections: [
      { heading: 'Data We Collect', body: 'Account data (name, email, Bar enrollment number), professional data (matter details, documents, drafts), usage data (session logs, feature interactions), and device data (IP address for security purposes).' },
      { heading: 'How We Use Your Data', body: 'To provide and improve the Platform; to process AI requests; to send service communications. We do not sell your data to third parties under any circumstances.' },
      { heading: 'AI & Training Data', body: 'Your matter-specific content is not used to train AI models unless you explicitly opt in via written agreement. Aggregate anonymised usage patterns may be used to improve the Platform.' },
      { heading: 'Data Storage & Security', body: 'All data is stored on servers in India. We apply AES-256 at rest and TLS 1.3 in transit. Access is restricted by role-based controls and periodic security audits are conducted.' },
      { heading: 'Your Rights (DPDP Act, 2023)', body: 'Right to access, correction, erasure (subject to legal holds), grievance redressal, and right to nominate a representative to exercise rights on your behalf.' },
      { heading: 'Contact for Privacy', body: 'Grievance Officer: RM — neveon.ai@gmail.com.' },
    ],
  },
  refund: {
    title: 'Refund & Cancellation Policy',
    date: 'Effective Date: 1 January 2026',
    sections: [
      { heading: 'Cancellations', body: 'You may cancel at any time. Cancellations take effect at the end of the current billing cycle. You retain full access until the cycle ends.' },
      { heading: 'Refunds', body: 'We offer a 7-day money-back guarantee for new subscribers. After the 7-day window, subscriptions are non-refundable except for documented technical failures (72+ continuous hours) or duplicate billing.' },
      { heading: 'Annual Plans', body: 'Annual plan refunds for unused months are available within 30 days of purchase on a pro-rata basis. After 30 days, no refund is available.' },
      { heading: 'How to Request', body: 'Email neveon.ai@gmail.com with your registered email and reason. Refunds are processed within 7–10 business days to your original payment method.' },
    ],
  },
  disclaimer: {
    title: 'Legal Disclaimer',
    date: null,
    sections: [
      { heading: 'Not Legal Advice', body: 'Mamla.AI is a technology platform for qualified legal professionals. Nothing on this Platform constitutes legal advice or creates an advocate-client relationship between Neveon AI Technologies Pvt. Ltd. and any user or their clients.' },
      { heading: 'AI Output Accuracy', body: 'AI-generated content may contain errors or outdated legal references. All output must be reviewed and approved by the responsible advocate before use in any court filing, legal notice, or client advice.' },
      { heading: 'Court Data', body: 'Case data and judicial statistics from government portals are provided for informational convenience only. Always verify directly on official portals before taking any procedural step.' },
      { heading: 'Professional Responsibility', body: 'The advocate remains solely responsible for the quality, accuracy, and ethical standing of all work product under the Advocates Act, 1961 and Bar Council of India Rules.' },
    ],
  },
};

// ─── Navbar dropdown ──────────────────────────────────────────────────────────

function NavDropdown({ label, items, isOpen, onToggle, onClose }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!isOpen) return;
    function handler(e) {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [isOpen, onClose]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={onToggle}
        className={`flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${
          isOpen ? 'bg-white/10 text-white' : 'text-white/70 hover:bg-white/8 hover:text-white'
        }`}
      >
        {label}
        <span className={`material-symbols-outlined text-base transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}>
          expand_more
        </span>
      </button>

      {isOpen && (
        <div className="app-fade-in absolute top-[calc(100%+8px)] left-0 z-[200] w-[min(260px,calc(100vw-2rem))] rounded-[14px] border border-white/10 bg-[#08111F] p-2 shadow-elevated" style={{maxWidth:'calc(100vw - 1rem)'}}>
          {items.map((item) => (
            <a
              key={item.label}
              href={item.href}
              onClick={onClose}
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-white/60 transition-colors hover:bg-white/6 hover:text-white"
            >
              <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg border border-white/8 bg-white/4">
                <span className="material-symbols-outlined text-base text-white/40">{item.icon}</span>
              </span>
              <div>
                <div className="text-[13.5px] font-medium text-white/80">{item.label}</div>
                {item.desc && <div className="mt-0.5 text-[11px] text-white/35">{item.desc}</div>}
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Legal modal ──────────────────────────────────────────────────────────────

function LegalModal({ docKey, onClose }) {
  const doc = LEGAL_DOCS[docKey];
  if (!doc) return null;
  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-ink/80 px-4 py-6 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative max-h-[85vh] w-full max-w-2xl overflow-hidden rounded-[28px] bg-white shadow-elevated"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white px-8 py-6">
          <h2 className="font-display text-xl font-bold text-background-dark">{doc.title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-background-light transition-colors hover:bg-slate-200"
          >
            <span className="material-symbols-outlined text-lg">close</span>
          </button>
        </div>
        <div className="max-h-[calc(85vh-80px)] overflow-y-auto px-8 py-7 custom-scrollbar">
          {doc.date && <p className="mb-5 text-[11px] italic text-slate-400">{doc.date}</p>}
          {doc.sections.map((section) => (
            <div key={section.heading} className="mb-5">
              <h3 className="mb-2 text-sm font-bold text-background-dark">{section.heading}</h3>
              <p className="text-sm leading-7 text-graphite">{section.body}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Sub-sections ─────────────────────────────────────────────────────────────

function FeaturesSection() {
  return (
    <section id="features" className="border-y border-slate-200 bg-white py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mb-14 text-center">
          <p className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">Product</p>
          <h2 className="font-display text-4xl font-bold text-ink md:text-5xl">
            AI Legal Practice Management Software Features
          </h2>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="group relative overflow-hidden rounded-[18px] border border-slate-200 bg-background-light p-6 transition-all hover:-translate-y-1 hover:border-primary/30 hover:shadow-elevated"
            >
              <div className="mb-5 flex items-start justify-between">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/8 transition-transform group-hover:scale-110">
                  <span className="material-symbols-outlined text-primary">{f.icon}</span>
                </div>
                {f.tag && (
                  <span className={`rounded px-2 py-0.5 text-[9px] font-black uppercase tracking-wider ${
                    f.tag === 'Live'
                      ? 'border border-emerald-500/20 bg-emerald-500/10 text-emerald-600'
                      : 'border border-slate-200 bg-white text-slate-400'
                  }`}>
                    {f.tag}
                  </span>
                )}
              </div>
              <h3 className="mb-2.5 text-sm font-bold text-ink">{f.title}</h3>
              <p className="text-[13px] leading-6 text-graphite">{f.desc}</p>
            </div>
          ))}
        </div>
        <p className="mt-6 text-center text-xs italic text-slate-400">
          Supreme Court &amp; Tribunal support — coming soon
        </p>
      </div>
    </section>
  );
}

function SolutionsSection() {
  return (
    <section id="solutions" className="bg-background-light py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mb-14 text-center">
          <p className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">Solutions</p>
          <h2 className="font-display text-4xl font-bold text-ink md:text-5xl">
            Legal Software Solutions for Lawyers, Law Firms, Litigants &amp; Law Students
          </h2>
        </div>
        <div className="grid gap-6 md:grid-cols-3">
          {PERSONAS.map((p) => (
            <div
              key={p.title}
              className="rounded-[20px] border border-slate-200 bg-white p-7 transition-all hover:-translate-y-1 hover:shadow-elevated"
            >
              <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-[14px] bg-primary/8">
                <span className="material-symbols-outlined text-2xl text-primary">{p.icon}</span>
              </div>
              <h3 className="mb-4 font-display text-xl font-bold text-ink">{p.title}</h3>
              <ul className="flex flex-col gap-3">
                {p.points.map((pt) => (
                  <li key={pt} className="flex items-start gap-2.5 text-sm text-graphite">
                    <span className="material-symbols-outlined mt-0.5 flex-shrink-0 text-base text-primary/50">check_circle</span>
                    {pt}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function PlanCard({ plan, dark }) {
  return (
    <div
      className={`relative flex flex-col rounded-[20px] border p-7 transition-all ${
        plan.recommended
          ? 'border-primary/30 bg-background-dark text-white shadow-elevated'
          : dark
          ? 'border-slate-700 bg-slate-800'
          : 'border-slate-200 bg-background-light'
      }`}
    >
      {plan.recommended && (
        <div className="absolute -top-px left-1/2 -translate-x-1/2 rounded-b-lg bg-primary px-4 py-1 text-[10px] font-black uppercase tracking-widest text-white">
          Recommended
        </div>
      )}
      <div className="mb-5">
        <p className={`mb-1.5 text-[10px] font-black uppercase tracking-[0.18em] ${plan.recommended ? 'text-primary-soft/70' : 'text-primary/70'}`}>
          {plan.name}
        </p>
        <div className="flex items-baseline gap-1">
          <span className={`font-display text-4xl font-bold ${plan.recommended ? 'text-white' : 'text-ink'}`}>
            {plan.price}
          </span>
          <span className={`text-sm ${plan.recommended ? 'text-white/50' : 'text-graphite'}`}>
            {plan.period}
          </span>
        </div>
        <p className={`mt-1 text-xs ${plan.recommended ? 'text-white/45' : 'text-graphite'}`}>
          {plan.subtitle}
        </p>
        {plan.offer && (
          <p className="mt-2 inline-block rounded-full bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 text-[10px] font-bold text-emerald-700">
            {plan.offer}
          </p>
        )}
      </div>
      <ul className="mb-4 flex flex-grow flex-col gap-2.5">
        {plan.items.map((item) => (
          <li key={item} className={`flex items-start gap-2 text-[13px] ${plan.recommended ? 'text-white/70' : 'text-graphite'}`}>
            <span className={`material-symbols-outlined mt-0.5 flex-shrink-0 text-base ${plan.recommended ? 'text-primary-soft/60' : 'text-emerald-500'}`}>
              check_circle
            </span>
            {item}
          </li>
        ))}
        {plan.blocked && plan.blocked.map((item) => (
          <li key={item} className="flex items-start gap-2 text-[13px] text-slate-400">
            <span className="material-symbols-outlined mt-0.5 flex-shrink-0 text-base text-slate-300">
              block
            </span>
            {item}
          </li>
        ))}
      </ul>
      <Link
        to="/signup"
        className={`mt-auto block rounded-[12px] py-3 text-center text-sm font-bold transition-all hover:-translate-y-0.5 ${
          plan.recommended
            ? 'bg-white text-background-dark hover:bg-primary-soft'
            : 'border border-primary/20 bg-white text-primary hover:bg-primary/5'
        }`}
      >
        {plan.cta}
      </Link>
    </div>
  );
}

function PricingSection() {
  const [activeTab, setActiveTab] = useState('lawyer');
  const plans = activeTab === 'lawyer' ? LAWYER_PLANS : NAGRIK_PLANS;
  const cols = plans.length === 2 ? 'md:grid-cols-2 max-w-3xl mx-auto' : 'md:grid-cols-2 lg:grid-cols-4';

  return (
    <section id="pricing" className="border-t border-slate-200 bg-white py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mb-4 text-center">
          <p className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">Pricing</p>
          <h2 className="font-display text-4xl font-bold text-ink md:text-5xl">
            Affordable AI Legal Software Pricing for Lawyers &amp; Law Firms
          </h2>
          <p className="mt-4 text-sm text-graphite">
            Choose the best legal practice management software plan for solo advocates, law firms, litigants and law students. Currently in private beta — join now to lock in early-adopter pricing.
          </p>
          {/* Tab toggle */}
          <div className="mt-8 inline-flex rounded-xl border border-slate-200 bg-slate-50 p-1 gap-1">
            <button
              onClick={() => setActiveTab('lawyer')}
              className={`rounded-lg px-5 py-2 text-sm font-bold transition-all ${
                activeTab === 'lawyer'
                  ? 'bg-background-dark text-white shadow-sm'
                  : 'text-slate-600 hover:text-ink'
              }`}
            >
              <span className="material-symbols-outlined text-base align-middle mr-1.5">balance</span>
              For Lawyers &amp; Firms
            </button>
            <button
              onClick={() => setActiveTab('nagrik')}
              className={`rounded-lg px-5 py-2 text-sm font-bold transition-all ${
                activeTab === 'nagrik'
                  ? 'bg-background-dark text-white shadow-sm'
                  : 'text-slate-600 hover:text-ink'
              }`}
            >
              <span className="material-symbols-outlined text-base align-middle mr-1.5">person</span>
              For Citizens (Nagrik)
            </button>
          </div>
        </div>

        {activeTab === 'nagrik' && (
          <p className="mt-4 text-center text-xs text-slate-500 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 max-w-xl mx-auto">
            <span className="material-symbols-outlined text-amber-500 text-sm align-middle mr-1">info</span>
            Nagrik plans give citizens access to legal information, document understanding, and eCourts tracking.
            Drafting, Case Companion, and AI Suggestions are professional tools reserved for lawyers.
          </p>
        )}

        <div className={`mt-10 grid gap-5 ${cols}`}>
          {plans.map((plan) => <PlanCard key={plan.name} plan={plan} />)}
        </div>

        <div className="mt-10 rounded-[16px] border border-slate-200 bg-background-light px-7 py-5 text-center">
          <p className="text-sm text-graphite">
            Running a law firm?{' '}
            <a href="mailto:neveon.ai@gmail.com" className="font-semibold text-primary hover:underline">
              Contact us for Firm Basic (₹2,049) and Firm Pro (₹4,549) plans →
            </a>
          </p>
        </div>
      </div>
    </section>
  );
}

function LiveCourtStats() {
  return (
    <section id="live-data" className="border-y border-slate-200 bg-background-light py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">Live Court Intelligence</div>
        <div className="mb-10 flex flex-wrap items-end justify-between gap-5">
          <h2 className="font-display text-4xl font-bold leading-tight text-ink md:text-5xl">
            Real-Time eCourts Case Tracking<br />&amp; Court Intelligence
          </h2>
          <p className="max-w-xs text-sm leading-7 text-graphite">
            Monitor case status, hearing dates, Supreme Court updates, High Court orders and legal news through a single legal intelligence dashboard — powered by live NJDG and eCourts data.
          </p>
        </div>
        <div className="grid gap-7 lg:grid-cols-[1fr_320px]">
          <div>
            <div className="grid gap-5 sm:grid-cols-2">
              {STAT_CARDS.map((card) => (
                <div
                  key={card.icon + card.value}
                  className="relative overflow-hidden rounded-[20px] border border-slate-200 bg-white p-6 transition-all hover:-translate-y-1 hover:shadow-card"
                >
                  <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(22,52,95,0.07),transparent_55%)]" />
                  <div className="relative">
                    <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10">
                      <span className="material-symbols-outlined text-primary">{card.icon}</span>
                    </div>
                    <p className="font-display text-4xl font-bold leading-none text-background-dark">
                      {card.value}<span className="text-xl font-semibold">{card.unit}</span>
                    </p>
                    <p className="mt-2 text-sm leading-6 text-graphite">{card.desc}</p>
                    <p className="mt-3 flex items-center gap-1.5 text-[10px] font-black uppercase tracking-[0.12em] text-primary">
                      <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
                      {card.source}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-5 flex flex-wrap items-center gap-3 rounded-[14px] border border-primary/10 bg-primary/5 px-4 py-3">
              <span className="text-[11px] font-black uppercase tracking-[0.14em] text-primary">Data sources</span>
              {['NJDG (njdg.ecourts.gov.in)', 'Supreme Court of India (main.sci.gov.in)', 'eCourts Services'].map((src, i, arr) => (
                <React.Fragment key={src}>
                  <span className="text-xs text-graphite">{src}</span>
                  {i < arr.length - 1 && <span className="text-slate-300">·</span>}
                </React.Fragment>
              ))}
            </div>
          </div>
          <div className="flex flex-col gap-3 rounded-[20px] bg-background-dark p-6">
            <div className="mb-1 flex items-center justify-between">
              <span className="text-[11px] font-black uppercase tracking-[0.2em] text-primary-soft/70">Legal Headlines</span>
              <span className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-400">
                <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" /> Live feed
              </span>
            </div>
            {NEWS_ITEMS.map((item, i) => (
              <div
                key={i}
                className="flex cursor-pointer gap-3 rounded-[14px] p-3 transition-colors"
                style={{ border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.05)' }}
              >
                <span className={`mt-0.5 flex-shrink-0 self-start rounded-md px-2 py-0.5 text-[9px] font-black uppercase tracking-[0.12em] ${item.tone}`}>
                  {item.source}
                </span>
                <div>
                  <p className="text-xs font-medium leading-5 text-slate-100">{item.text}</p>
                  <p className="mt-1 text-[11px] text-slate-400">{item.time}</p>
                </div>
              </div>
            ))}
            <a
              href="https://www.livelaw.in"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 block text-center text-xs font-semibold text-slate-400 transition-colors hover:text-primary-soft"
            >
              View all legal news →
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

function ResourcesSection() {
  const resources = [
    { icon: 'flash_on',     title: 'Live Law',                     highlight: true,  desc: 'Latest Supreme Court and High Court legal updates — real-time legal news, breaking orders and judicial developments as they happen.', href: 'https://www.livelaw.in' },
    { icon: 'search',       title: 'Citation Search',              highlight: false, desc: 'AI-powered legal research across Indian judgments and precedents. Search citations, trace reasoning and find relevant sections across courts.', href: '#live-data' },
    { icon: 'list_alt',     title: 'Cause List Search',            highlight: false, desc: "Search daily cause lists across Indian courts. Know what's scheduled before stepping into court — District Courts and High Courts.", href: '#features' },
    { icon: 'auto_awesome', title: 'AI in Law',                    highlight: false, desc: 'Insights on artificial intelligence in legal practice — written for Indian lawyers, not technologists. How AI is reshaping advocacy in India.', href: '#' },
  ];

  return (
    <section id="resources" className="border-t border-slate-200 bg-white py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mb-14 text-center">
          <p className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">Resources</p>
          <h2 className="font-display text-4xl font-bold text-ink md:text-5xl">
            Legal Research Resources &amp; AI Legal Insights
          </h2>
        </div>
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          {resources.map((r) => (
            <a
              key={r.title}
              href={r.href}
              target={r.href.startsWith('http') ? '_blank' : undefined}
              rel={r.href.startsWith('http') ? 'noopener noreferrer' : undefined}
              className={`group flex flex-col rounded-[18px] border p-7 transition-all hover:-translate-y-1 ${
                r.highlight
                  ? 'border-emerald-500/20 bg-emerald-500/5 hover:border-emerald-500/35 hover:shadow-elevated'
                  : 'border-slate-200 bg-background-light hover:border-primary/25 hover:shadow-elevated'
              }`}
            >
              {r.highlight && (
                <span className="mb-4 inline-flex w-fit items-center gap-1.5 rounded border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[9px] font-black uppercase tracking-wider text-emerald-600">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                  Live Updates
                </span>
              )}
              <span className={`material-symbols-outlined mb-4 text-2xl ${r.highlight ? 'text-emerald-500' : 'text-primary/60'}`}>
                {r.icon}
              </span>
              <h3 className="mb-2.5 text-base font-bold text-ink">{r.title}</h3>
              <p className="mb-5 flex-grow text-[13px] leading-6 text-graphite">{r.desc}</p>
              <span className={`flex items-center gap-1.5 text-xs font-semibold ${r.highlight ? 'text-emerald-600' : 'text-primary'}`}>
                Explore
                <span className="material-symbols-outlined text-sm">arrow_forward</span>
              </span>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}

function SecuritySection() {
  return (
    <section id="security" className="bg-background-light py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid items-center gap-16 lg:grid-cols-2">
          <div>
            <p className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">Enterprise Security</p>
            <h2 className="mb-5 font-display text-4xl font-bold text-ink">
              Secure Legal Practice Management Software
            </h2>
            <p className="mb-8 text-sm leading-8 text-graphite">
              Protect legal documents, client data and case records with enterprise-grade legal technology security. Your clients&apos; data is encrypted at rest and in transit — so you can focus on winning cases, not worrying about breaches.
            </p>
            <div className="space-y-4">
              {[
                { icon: 'shield',        text: 'AES-256 encryption for all documents, at rest and in transit' },
                { icon: 'verified_user', text: 'Enterprise-grade infrastructure with strict access controls' },
                { icon: 'lock',          text: 'Role-based access control (RBAC) — per-matter permissions' },
                { icon: 'policy',        text: 'DPDP Act 2023 and Bar Council aligned workflows' },
                { icon: 'dns',           text: 'All data stored on India-located servers only' },
              ].map((item) => (
                <div key={item.text} className="flex items-center gap-3">
                  <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-primary/10">
                    <span className="material-symbols-outlined text-base text-primary">{item.icon}</span>
                  </div>
                  <span className="text-sm font-medium text-ink/85">{item.text}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-5 rounded-[24px] bg-background-dark p-8 shadow-elevated">
            {[
              { label: 'Uptime SLA',   value: '99.9%'   },
              { label: 'Encryption',   value: 'AES-256' },
              { label: 'Data Centers', value: 'India'   },
              { label: 'Compliance',   value: 'DPDP'    },
            ].map((stat) => (
              <div key={stat.label} className="rounded-xl border border-white/10 bg-white/5 p-5">
                <p className="mb-1 text-[10px] font-black uppercase tracking-wider text-white/50">{stat.label}</p>
                <p className="font-sans text-2xl font-black text-primary-soft">{stat.value}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function AboutSection() {
  return (
    <section id="about" className="border-t border-slate-200 bg-white py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mb-14 text-center">
          <p className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">About Mamla.AI</p>
          <h2 className="mb-5 font-display text-4xl font-bold text-ink md:text-5xl">
            About Mamla AI &ndash;{' '}
            <span className="italic text-graphite">AI Legal Software Built for Indian Lawyers</span>
          </h2>
          <p className="mx-auto max-w-2xl text-sm leading-8 text-graphite">
            Mamla AI is an AI-powered legal software platform helping lawyers, law firms, litigants and law students streamline drafting, legal research, case management and court tracking. We combine deep understanding of Indian law with cutting-edge AI to give every advocate and law firm the tools they deserve — from AI legal drafting to eCourt integration, case strategy to client lifecycle management.
          </p>
        </div>

        <div className="mx-auto grid max-w-3xl gap-6 md:grid-cols-2">
          {[
            {
              initials: 'RM', name: 'RM', role: 'Co-Founder & CEO', college: 'IIT Kharagpur',
              bio: "Nearly two decades at the intersection of enterprise technology and institutional infrastructure. Mamla.AI began with a single observation: India's courts generate more structured data than almost any institution in the country, yet practicing counsel operates almost entirely without access to it.",
            },
            {
              initials: 'MS', name: 'MS', role: 'Co-Founder & CTO', college: 'NIT Durgapur',
              bio: "The engineering mind behind Mamla.AI's AI core — the models that draft, the pipelines that ingest court filings, and the real-time eCourt infrastructure. Believes the most important test of any AI system is whether a senior advocate would trust it the night before a hearing.",
            },
          ].map((m) => (
            <div key={m.initials} className="overflow-hidden rounded-[24px] border border-slate-200 bg-background-light shadow-card transition-all hover:-translate-y-1 hover:shadow-elevated">
              <div className="relative bg-background-dark p-7">
                <div className="absolute -right-8 -top-8 h-40 w-40 rounded-full" style={{ background: 'rgba(255,255,255,0.04)' }} />
                <div className="relative">
                  <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-[16px] border border-white/12 bg-white/8 font-display text-2xl font-bold text-primary-soft">
                    {m.initials}
                  </div>
                  <p className="font-display text-xl font-bold text-white">{m.name}</p>
                  <p className="mt-0.5 text-[11px] font-black uppercase tracking-[0.18em] text-primary-soft/70">{m.role}</p>
                </div>
              </div>
              <div className="p-7">
                <span className="mb-4 inline-block rounded-lg px-3 py-1 text-[11px] font-bold text-primary" style={{ background: 'rgba(22,52,95,0.09)' }}>
                  🎓 {m.college}
                </span>
                <p className="text-[13px] leading-7 text-graphite">{m.bio}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-wrap items-center justify-between gap-6 rounded-[20px] bg-background-dark px-8 py-7">
          <div>
            <p className="mb-1 text-[11px] font-black uppercase tracking-[0.18em] text-primary-soft/55">Company</p>
            <p className="font-display text-lg font-bold text-white">Neveon AI Technologies Pvt. Ltd.</p>
            <p className="mt-0.5 text-sm text-slate-300">The parent company behind Mamla.AI · Incorporated in India</p>
          </div>
          <a
            href="mailto:neveon.ai@gmail.com"
            className="inline-flex items-center gap-2 rounded-xl border border-white/12 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-white/10"
            style={{ background: 'rgba(255,255,255,0.08)' }}
          >
            <span className="material-symbols-outlined text-base text-primary-soft">mail</span>
            neveon.ai@gmail.com
          </a>
        </div>
      </div>
    </section>
  );
}

function FAQSection() {
  const [openIdx, setOpenIdx] = useState(null);
  return (
    <section id="faq" className="border-t border-slate-200 bg-background-light py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid gap-12 lg:grid-cols-[1fr_2fr] lg:items-start">
          <div>
            <p className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">FAQ</p>
            <h2 className="mb-5 font-display text-4xl font-bold leading-tight text-ink">Frequently Asked Questions about AI Legal Software</h2>
            <p className="mb-7 text-sm leading-7 text-graphite">
              Everything lawyers, law firms, litigants and law students need to know about AI legal practice management software before signing up.
            </p>
            <div className="rounded-[16px] border border-primary/12 bg-primary/5 p-5">
              <div className="mb-2 text-[11px] font-black uppercase tracking-[0.14em] text-primary">Still have questions?</div>
              <a href="mailto:neveon.ai@gmail.com" className="text-sm font-semibold text-primary hover:underline">
                neveon.ai@gmail.com
              </a>
            </div>
          </div>
          <div className="flex flex-col gap-1">
            {FAQS.map((faq, i) => (
              <div
                key={i}
                className={`overflow-hidden rounded-[16px] border transition-colors ${openIdx === i ? 'border-primary/15 bg-white' : 'border-transparent'}`}
              >
                <button
                  type="button"
                  onClick={() => setOpenIdx(openIdx === i ? null : i)}
                  className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left"
                >
                  <span className="text-sm font-semibold text-ink">{faq.q}</span>
                  <span className={`material-symbols-outlined flex-shrink-0 text-primary transition-transform duration-300 ${openIdx === i ? 'rotate-180' : ''}`}>
                    expand_more
                  </span>
                </button>
                {openIdx === i && (
                  <div className="px-5 pb-5 text-sm leading-7 text-graphite">{faq.a}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function ContactSection() {
  const [form, setForm] = useState({ name: '', email: '', jurisdiction: '', message: '' });
  const [status, setStatus] = useState('idle');

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus('sending');
    await new Promise((r) => setTimeout(r, 900));
    setStatus('success');
    setForm({ name: '', email: '', jurisdiction: '', message: '' });
  }

  const inputCls = 'rounded-xl border border-white/12 px-4 py-3 text-sm text-white placeholder:text-slate-500 outline-none transition-colors focus:border-primary-soft/60 w-full';
  const inputStyle = { background: 'rgba(255,255,255,0.07)' };

  return (
    <section id="contact" className="border-t bg-background-dark py-24 text-ivory" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid gap-12 lg:grid-cols-2 lg:items-start">
          <div>
            <p className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary-soft/65">Contact & Support</p>
            <h2 className="mb-5 font-display text-4xl font-bold leading-tight text-white md:text-5xl">
              Contact Mamla AI &ndash; AI Legal Software for Lawyers &amp; Law Firms
            </h2>
            <p className="mb-9 text-sm leading-7 text-white/60">
              Schedule a demo of Mamla AI and discover how AI-powered legal software can improve drafting, legal research, case management and client communication. Whether you&apos;re a solo practitioner or a senior counsel at the Supreme Court &mdash; we&apos;re here to help.
            </p>
            {[
              { icon: 'mail',        label: 'General & Support', value: 'neveon.ai@gmail.com',              href: 'mailto:neveon.ai@gmail.com' },
              { icon: 'business',    label: 'Company',            value: 'Neveon AI Technologies Pvt. Ltd.', href: null },
              { icon: 'location_on', label: 'Registered Office',  value: 'India (Remote-first operation)',   href: null },
              { icon: 'schedule',    label: 'Response Time',      value: 'Within 1 business day',            href: null },
            ].map((item) => (
              <div key={item.label} className="mb-6 flex items-start gap-4">
                <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl border border-white/10" style={{ background: 'rgba(255,255,255,0.07)' }}>
                  <span className="material-symbols-outlined text-xl text-primary-soft">{item.icon}</span>
                </div>
                <div>
                  <p className="text-[11px] font-black uppercase tracking-[0.18em] text-primary-soft/70">{item.label}</p>
                  {item.href
                    ? <a href={item.href} className="mt-1 block text-sm font-semibold text-primary-soft hover:underline">{item.value}</a>
                    : <p className="mt-1 text-sm font-semibold text-white">{item.value}</p>
                  }
                </div>
              </div>
            ))}
          </div>
          <div>
            <p className="mb-5 text-[11px] font-black uppercase tracking-[0.18em] text-primary-soft/60">Send a message</p>
            <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-white/70">Full Name</label>
                  <input name="name" type="text" value={form.name} onChange={handleChange} required placeholder="Adv. Priya Sharma" className={inputCls} style={inputStyle} />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-white/70">Professional Email</label>
                  <input name="email" type="email" value={form.email} onChange={handleChange} required placeholder="advocate@chambers.in" className={inputCls} style={inputStyle} />
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-white/70">High Court / Jurisdiction</label>
                <input name="jurisdiction" type="text" value={form.jurisdiction} onChange={handleChange} placeholder="e.g. Bombay HC, Supreme Court, Calcutta HC" className={inputCls} style={inputStyle} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-white/70">Message</label>
                <textarea
                  name="message"
                  value={form.message}
                  onChange={handleChange}
                  rows={4}
                  placeholder="Tell us about your practice area and what you're hoping Mamla.AI can solve…"
                  className={`${inputCls} resize-y`}
                  style={inputStyle}
                />
              </div>
              <button
                type="submit"
                disabled={status === 'sending'}
                className="self-start rounded-[14px] bg-white px-7 py-3.5 text-sm font-bold text-background-dark transition-all hover:-translate-y-0.5 hover:bg-primary-soft disabled:opacity-60"
              >
                {status === 'sending' ? 'Sending…' : 'Send Message →'}
              </button>
              {status === 'success' && (
                <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/15 px-4 py-3 text-sm font-semibold text-emerald-400">
                  ✓ Message sent! We&apos;ll respond within one business day.
                </div>
              )}
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Main export ──────────────────────────────────────────────────────────────

export default function LandingPage() {
  useIconFont();
  const [scrolled, setScrolled] = useState(false);
  const [openDD, setOpenDD] = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mobileAcc, setMobileAcc] = useState(null);
  const [openModal, setOpenModal] = useState(null);

  useEffect(() => {
    function onScroll() { setScrolled(window.scrollY > 20); }
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    function onResize() { if (window.innerWidth >= 768) setMobileOpen(false); }
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const productItems = [
    { icon: 'edit_note',       label: 'AI Drafting',                 desc: 'Generate court-ready legal documents', href: '#features' },
    { icon: 'search',          label: 'eCourt Integration',          desc: 'District & High Court live feed',      href: '#features' },
    { icon: 'layers',          label: 'Agentic Doc Analysis',        desc: 'AI-powered document intelligence',     href: '#features' },
    { icon: 'format_quote',    label: 'Citation Search',             desc: 'Find legal citations instantly',       href: '#features' },
    { icon: 'calendar_month',  label: 'Calendar Management',        desc: 'Smart hearing & deadline tracking',    href: '#features' },
    { icon: 'track_changes',   label: 'Case Strategiser',            desc: 'Build winning case strategies',        href: '#features' },
    { icon: 'people',          label: 'Client Lifecycle Management', desc: 'End-to-end client tracking',           href: '#features' },
  ];

  const solutionItems = [
    { icon: 'balance',        label: 'For Lawyers',   desc: 'Streamline your practice',     href: '#solutions' },
    { icon: 'person',         label: 'For Litigants', desc: 'Understand your legal journey', href: '#solutions' },
    { icon: 'corporate_fare', label: 'For Law Firms', desc: 'Scale operations efficiently',  href: '#solutions' },
  ];

  const resourceItems = [
    { icon: 'flash_on',     label: 'Live Law',                     desc: 'Real-time legal updates',     href: '#live-data' },
    { icon: 'format_quote', label: 'Case Law Insights / Citation', desc: 'Precedent & citation search', href: '#resources' },
    { icon: 'list_alt',     label: 'Cause List Search',            desc: 'Daily court cause lists',     href: '#resources' },
    { icon: 'auto_awesome', label: 'AI in Law',                    desc: 'Blog & thought leadership',   href: '#resources' },
  ];

  function closeDD() { setOpenDD(null); }

  return (
    <div className="bg-background-light text-ink antialiased">

      {/* ── NAVBAR ── */}
      <nav
        className={`fixed left-0 right-0 top-0 z-[100] transition-all duration-300 ${
          scrolled
            ? 'border-b bg-background-dark/95 shadow-[0_8px_32px_-8px_rgba(8,17,31,0.6)] backdrop-blur-xl'
            : 'bg-background-dark/60 backdrop-blur-md'
        }`}
        style={{ borderColor: scrolled ? 'rgba(255,255,255,0.08)' : 'transparent' }}
      >
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">

          {/* Logo */}
          <Link to="/" className="flex flex-shrink-0 items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/6">
              <MamlaLogoIcon dark size={30} />
            </div>
            <span className="font-display text-lg font-semibold tracking-tight text-white">Mamla.AI</span>
          </Link>

          {/* Desktop nav items */}
          <div className="hidden items-center gap-1 md:flex">
            <NavDropdown
              label="Product"
              items={productItems}
              isOpen={openDD === 'product'}
              onToggle={() => setOpenDD(openDD === 'product' ? null : 'product')}
              onClose={closeDD}
            />
            <NavDropdown
              label="Solutions"
              items={solutionItems}
              isOpen={openDD === 'solutions'}
              onToggle={() => setOpenDD(openDD === 'solutions' ? null : 'solutions')}
              onClose={closeDD}
            />
            <a href="#pricing" className="rounded-lg px-3 py-2 text-sm font-semibold text-white/70 transition-colors hover:bg-white/8 hover:text-white">
              Pricing
            </a>
            <NavDropdown
              label="Resources"
              items={resourceItems}
              isOpen={openDD === 'resources'}
              onToggle={() => setOpenDD(openDD === 'resources' ? null : 'resources')}
              onClose={closeDD}
            />
            <a href="#about" className="rounded-lg px-3 py-2 text-sm font-semibold text-white/70 transition-colors hover:bg-white/8 hover:text-white">
              About
            </a>
          </div>

          {/* Right: auth + burger */}
          <div className="flex items-center gap-3">
            <Link to="/login" className="px-4 py-2 text-sm font-semibold text-white/70 transition-colors hover:text-white">
              Sign in
            </Link>
            <Link
              to="/signup"
              className="rounded-lg bg-white px-5 py-2 text-sm font-bold text-primary-dark shadow-card transition-all hover:-translate-y-0.5 hover:bg-primary-soft"
            >
              Try Mamla AI
            </Link>
            <button
              type="button"
              onClick={() => setMobileOpen(!mobileOpen)}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/6 text-white md:hidden"
              aria-label="Toggle navigation"
            >
              <span className="material-symbols-outlined text-xl">{mobileOpen ? 'close' : 'menu'}</span>
            </button>
          </div>
        </div>

        {/* Mobile drawer */}
        {mobileOpen && (
          <div className="app-fade-in fixed inset-0 top-16 z-[99] overflow-y-auto bg-background-dark px-6 py-6 md:hidden">
            {[
              { key: 'product',   label: 'Product',   items: productItems },
              { key: 'solutions', label: 'Solutions', items: solutionItems },
              { key: 'resources', label: 'Resources', items: resourceItems },
            ].map((group) => (
              <div key={group.key} className="border-b border-white/6">
                <button
                  type="button"
                  onClick={() => setMobileAcc(mobileAcc === group.key ? null : group.key)}
                  className="flex w-full items-center justify-between py-4 text-base font-semibold text-white/75"
                >
                  {group.label}
                  <span className={`material-symbols-outlined text-white/40 transition-transform duration-200 ${mobileAcc === group.key ? 'rotate-180' : ''}`}>
                    expand_more
                  </span>
                </button>
                {mobileAcc === group.key && (
                  <div className="pb-4 pl-3">
                    {group.items.map((item) => (
                      <a
                        key={item.label}
                        href={item.href}
                        onClick={() => setMobileOpen(false)}
                        className="flex items-center gap-3 py-3 text-sm text-white/50"
                      >
                        <span className="material-symbols-outlined text-base text-white/25">{item.icon}</span>
                        {item.label}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {[{ label: 'Pricing', href: '#pricing' }, { label: 'About', href: '#about' }].map((item) => (
              <a
                key={item.label}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className="block border-b border-white/6 py-4 text-base font-semibold text-white/75"
              >
                {item.label}
              </a>
            ))}
            <div className="mt-7 flex flex-col gap-3">
              <Link to="/login" onClick={() => setMobileOpen(false)} className="block rounded-xl border border-white/12 py-3.5 text-center text-sm font-semibold text-white">
                Sign in
              </Link>
              <Link to="/signup" onClick={() => setMobileOpen(false)} className="block rounded-xl bg-white py-3.5 text-center text-sm font-bold text-primary-dark">
                Try Mamla AI
              </Link>
            </div>
          </div>
        )}
      </nav>

      {/* ── HERO ── */}
      <header className="gradient-mesh court-grid relative overflow-hidden pb-32 pt-36 text-white">
        <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(8,17,31,0.05),rgba(8,17,31,0.5))]" />
        <div className="float-slow absolute -left-16 top-24 h-72 w-72 rounded-full bg-white/5 blur-3xl" />
        <div className="float-slow absolute bottom-12 right-0 h-80 w-80 rounded-full bg-primary/15 blur-3xl" />

        <div className="relative mx-auto max-w-3xl px-6 text-center">
          <div className="app-rise-in mb-8 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/8 px-4 py-1.5 backdrop-blur-sm">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary-soft opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-primary-soft" />
            </span>
            <span className="text-xs font-bold uppercase tracking-widest text-primary-soft">Now in Private Beta</span>
          </div>

          <h1
            className="app-rise-in mb-6 font-display text-5xl font-bold leading-[1.06] tracking-tight md:text-7xl"
            style={{ animationDelay: '60ms' }}
          >
            AI Legal Software for{' '}
            <span className="block text-primary-soft">Lawyers, Law Firms &amp; Litigants</span>
          </h1>

          <p
            className="app-rise-in mx-auto mb-10 max-w-xl text-lg font-medium leading-8 text-white/75"
            style={{ animationDelay: '120ms' }}
          >
            Draft legal documents, manage cases, track court hearings, conduct legal research, automate client management and monitor eCourts &mdash; all from one AI-powered legal platform.
          </p>

          <div
            className="app-rise-in flex flex-col items-center justify-center gap-4 sm:flex-row"
            style={{ animationDelay: '180ms' }}
          >
            <Link
              to="/signup"
              className="inline-flex items-center gap-2 rounded-[12px] bg-white px-8 py-4 text-[15px] font-bold text-primary-dark shadow-elevated transition-all hover:-translate-y-0.5 hover:bg-primary-soft"
            >
              Get Started Free
              <span className="material-symbols-outlined text-lg">arrow_forward</span>
            </Link>
            <a
              href="#features"
              className="inline-flex items-center gap-2 rounded-[12px] border border-white/15 bg-white/8 px-8 py-4 text-[15px] font-medium text-white/80 backdrop-blur-sm transition-all hover:border-white/25 hover:bg-white/14"
            >
              See How It Works
            </a>
          </div>

          <div
            className="app-rise-in mt-16 grid grid-cols-3 gap-6 border-t border-white/10 pt-10"
            style={{ animationDelay: '240ms' }}
          >
            {[
              { value: '24/7',  label: 'Chamber Continuity' },
              { value: '10x',   label: 'Faster Review Cycles' },
              { value: 'RBAC',  label: 'Matter Security' },
            ].map((stat) => (
              <div key={stat.label} className="flex flex-col items-center gap-1">
                <span className="font-sans text-2xl font-bold text-white">{stat.value}</span>
                <span className="text-[11px] font-semibold uppercase tracking-[0.15em] text-white/55">{stat.label}</span>
              </div>
            ))}
          </div>
        </div>
      </header>

      {/* ── CONTENT SECTIONS ── */}
      <FeaturesSection />
      <SolutionsSection />
      <PricingSection />
      <LiveCourtStats />
      <ResourcesSection />
      <SecuritySection />
      <AboutSection />
      <FAQSection />
      <ContactSection />

      {/* ── BOTTOM CTA ── */}
      <section className="bg-background-dark py-24 text-ivory">
        <div className="mx-auto max-w-2xl px-6 text-center">
          <h2 className="mb-5 font-display text-4xl font-bold text-white md:text-5xl">
            Ready to Transform Your{' '}
            <span className="italic text-primary-soft">Legal Practice with AI?</span>
          </h2>
          <p className="mb-10 text-base font-medium leading-8 text-white/65">
            Join lawyers, law firms, litigants and law students already using Mamla AI — India&apos;s AI-powered legal practice management software — to work smarter, draft faster and never miss a hearing.
          </p>
          <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              to="/signup"
              className="inline-flex items-center gap-2 rounded-[12px] bg-white px-8 py-4 text-[15px] font-bold text-primary-dark shadow-elevated transition-all hover:-translate-y-0.5 hover:bg-primary-soft"
            >
              Try Mamla AI — It&apos;s Free
              <span className="material-symbols-outlined text-lg">arrow_forward</span>
            </Link>
            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-[12px] border border-white/15 bg-white/8 px-8 py-4 text-[15px] font-medium text-white/80 transition-all hover:bg-white/14"
            >
              Sign In
            </Link>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="border-t bg-background-dark text-white" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="mx-auto max-w-7xl px-6 py-16">
          <div className="grid gap-12 md:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr_1fr]">

            {/* Brand */}
            <div>
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/6">
                  <MamlaLogoIcon dark size={30} />
                </div>
                <span className="font-display text-lg font-semibold text-white">Mamla.AI</span>
              </div>
              <p className="mb-4 max-w-[240px] text-sm leading-7 text-slate-400">
                AI legal software for lawyers, law firms, litigants and law students in India. Legal drafting, eCourts tracking, legal research and case management — all in one platform.
              </p>
              <div className="flex flex-wrap gap-1.5">
                {['AES-256', 'DPDP Aligned', 'India Hosted'].map((badge) => (
                  <span key={badge} className="rounded-lg border border-white/10 px-2 py-1 text-[10px] font-black uppercase tracking-[0.1em] text-slate-400" style={{ background: 'rgba(255,255,255,0.05)' }}>
                    {badge}
                  </span>
                ))}
              </div>
              <p className="mt-4 text-[11px] text-slate-500">A product of Neveon AI Technologies Pvt. Ltd.</p>
            </div>

            {/* Product */}
            <div>
              <p className="mb-4 text-[11px] font-black uppercase tracking-[0.16em] text-slate-400">Product</p>
              <ul className="flex flex-col gap-2.5">
                {['Calendar Management', 'AI Drafting', 'Doc Analysis', 'Case Strategiser', 'Client Management', 'eCourt Integration', 'Citation Search'].map((item) => (
                  <li key={item}>
                    <a href="#features" className="text-xs text-white/50 transition-colors hover:text-white">{item}</a>
                  </li>
                ))}
              </ul>
            </div>

            {/* Solutions */}
            <div>
              <p className="mb-4 text-[11px] font-black uppercase tracking-[0.16em] text-slate-400">Solutions</p>
              <ul className="flex flex-col gap-2.5">
                {['For Lawyers', 'For Law Students', 'For Litigants', 'For Law Firms'].map((item) => (
                  <li key={item}>
                    <a href="#solutions" className="text-xs text-white/50 transition-colors hover:text-white">{item}</a>
                  </li>
                ))}
              </ul>
            </div>

            {/* Company */}
            <div>
              <p className="mb-4 text-[11px] font-black uppercase tracking-[0.16em] text-slate-400">Company</p>
              <ul className="flex flex-col gap-2.5">
                {[
                  { label: 'About',                 href: '#about' },
                  { label: 'Pricing',               href: '#pricing' },
                  { label: 'FAQ',                   href: '#faq' },
                  { label: 'Security',              href: '#security' },
                  { label: 'Contact',               href: '#contact' },
                  { label: 'neveon.ai@gmail.com',   href: 'mailto:neveon.ai@gmail.com' },
                ].map((item) => (
                  <li key={item.label}>
                    <a href={item.href} className="text-xs text-white/50 transition-colors hover:text-white">{item.label}</a>
                  </li>
                ))}
              </ul>
            </div>

            {/* Legal */}
            <div>
              <p className="mb-4 text-[11px] font-black uppercase tracking-[0.16em] text-slate-400">Legal</p>
              <ul className="flex flex-col gap-2.5">
                {[
                  { label: 'Terms of Service', modal: 'terms' },
                  { label: 'Privacy Policy',   modal: 'privacy' },
                  { label: 'Refund Policy',    modal: 'refund' },
                  { label: 'Legal Disclaimer', modal: 'disclaimer' },
                ].map((item) => (
                  <li key={item.label}>
                    <button type="button" onClick={() => setOpenModal(item.modal)} className="text-xs text-white/50 transition-colors hover:text-white">
                      {item.label}
                    </button>
                  </li>
                ))}
              </ul>
              <div className="mt-5 rounded-xl p-3" style={{ border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.04)' }}>
                <p className="mb-1 text-[10px] font-black uppercase tracking-[0.12em] text-white/35">Grievance Officer</p>
                <p className="text-xs font-semibold text-white/55">RM</p>
                <a href="mailto:neveon.ai@gmail.com" className="text-xs text-primary-soft/60 transition-colors hover:text-primary-soft">neveon.ai@gmail.com</a>
                <p className="mt-1 text-[10px] text-slate-500">Response within 30 days (IT Act, 2000)</p>
              </div>
            </div>
          </div>

          <div className="mt-12 flex flex-wrap items-center justify-between gap-4 border-t pt-8" style={{ borderColor: 'rgba(255,255,255,0.07)' }}>
            <p className="text-xs text-white/30">
              © 2026 Neveon AI Technologies Pvt. Ltd. All rights reserved. Mamla.AI is a registered product.
            </p>
            <div className="flex gap-5">
              {[
                { label: 'Terms',      modal: 'terms' },
                { label: 'Privacy',    modal: 'privacy' },
                { label: 'Refunds',    modal: 'refund' },
                { label: 'Disclaimer', modal: 'disclaimer' },
              ].map((item) => (
                <button key={item.label} type="button" onClick={() => setOpenModal(item.modal)} className="text-xs text-slate-500 transition-colors hover:text-white">
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </footer>

      {openModal && <LegalModal docKey={openModal} onClose={() => setOpenModal(null)} />}
    </div>
  );
}
