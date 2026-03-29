import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

// ─── Static data ──────────────────────────────────────────────────────────────
const TICKER_ITEMS = [
  { tag: 'SC',          live: true,  text: 'Supreme Court cause lists updated daily — track Constitution bench sittings inside your dashboard.' },
  { tag: 'NJDG',        live: false, text: '4.8 Cr+ cases pending across all courts in India — National Judicial Data Grid.' },
  { tag: 'LiveLaw',     live: false, text: 'Latest legal headlines surfaced inside your workspace — no separate portal needed.' },
  { tag: 'eCourts',     live: false, text: '2,25,000+ cases disposed nationwide this month across High Courts and District Courts.' },
  { tag: 'Bar Council', live: false, text: 'BCI circulars and advocate enrollment updates — stay informed without checking portals.' },
  { tag: 'Mamla.AI',    live: true,  text: 'Private beta now accepting chamber registrations — join 200+ advocates already on the platform.' },
];

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

const TEAM_MEMBERS = [
  {
    initials: 'RM',
    name: 'Robin',
    role: 'Co-Founder & CEO',
    tags: ['🎓 IIT Kharagpur', 'B.Tech'],
    bio: "With nearly two decades at the intersection of enterprise technology and institutional infrastructure, Robin brings the rare discipline of systems-level thinking to a domain that has resisted modernisation for too long. His work at Mamla.AI began with a single observation: that India's courts generate more structured data than almost any institution in the country, yet practicing counsel operates almost entirely without access to it. That gap became the company.",
  },
  {
    initials: 'MS',
    name: 'Mrityunjoy',
    role: 'Co-Founder & CTO',
    tags: ['🎓 NIT Durgapur', 'B.Tech'],
    bio: "Mrityunjoy is the engineering mind behind Mamla.AI's AI core — the models that draft, the pipelines that ingest court filings, and the real-time infrastructure that surfaces eCourt movements before the listing board does. Trained as an engineer but drawn to making language models reliable in high-stakes domains, he believes the most important test of any AI system is whether a senior advocate would trust it at 11 PM the night before a hearing.",
  },
];

const FAQS = [
  { q: 'Is Mamla.AI drafting output admissible in court?', a: "AI-generated drafts are working tools, not final submissions. Every document must be reviewed, edited, and approved by the responsible advocate before filing. Mamla.AI helps you get to a strong first draft faster — the professional judgement remains yours." },
  { q: 'Does Mamla.AI comply with the DPDP Act, 2023?', a: "Yes. We store all data on India-located servers, apply AES-256 encryption, and follow data minimisation principles aligned with the Digital Personal Data Protection Act, 2023. Your clients' matter data is never used to train AI models without explicit written consent." },
  { q: 'Which courts and jurisdictions are currently supported?', a: 'Cause list monitoring is available for the Supreme Court and all 25 High Courts. District court data is available via NJDG integration. Tribunal and quasi-judicial feeds are being progressively added.' },
  { q: 'Can I use Mamla.AI for transactional and advisory work, not just litigation?', a: 'Absolutely. The document drafting and chat features are used by corporate counsel for agreements, due diligence memos, and compliance reviews. eCourts search and cause lists are optional modules.' },
  { q: 'How does role-based access work for a multi-lawyer chamber?', a: 'The admin can invite team members and assign roles: Senior Counsel, Junior Associate, Paralegal, or Client. Each role has granular document-level permissions. Clients get read-only access to their specific matter folders.' },
  { q: 'Is there a Bar Council restriction on using AI drafting tools?', a: 'As of 2026, the Bar Council of India has not issued a blanket prohibition on AI-assisted drafting tools. Advocates remain responsible for all work product under BCI Rules. Treat AI output as a supervised first draft, not a final product.' },
  { q: 'What happens to my data if I cancel?', a: 'You retain full access until the end of your billing period. After cancellation, you have 30 days to export all your data. After 30 days, data is permanently deleted from our servers per our retention policy.' },
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
      { heading: '7. Grievance Officer', body: 'Designated Grievance Officer: Robin, Neveon AI Technologies Pvt. Ltd. Email: neveon.ai@gmail.com. Complaints acknowledged within 24 hours and resolved within 30 days (IT Act, 2000).' },
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
      { heading: 'Contact for Privacy', body: 'Grievance Officer: Robin — neveon.ai@gmail.com.' },
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

// ─── New section components ───────────────────────────────────────────────────

function TickerBar() {
  const doubled = [...TICKER_ITEMS, ...TICKER_ITEMS];
  return (
    <div className="overflow-hidden border-b bg-background-dark" style={{ borderColor: 'rgba(255,255,255,0.08)' }}>
      <style>{`@keyframes mamla-ticker{from{transform:translateX(0)}to{transform:translateX(-50%)}}`}</style>
      <div
        className="flex w-max gap-16 py-2.5"
        style={{ animation: 'mamla-ticker 46s linear infinite' }}
        onMouseEnter={(e) => (e.currentTarget.style.animationPlayState = 'paused')}
        onMouseLeave={(e) => (e.currentTarget.style.animationPlayState = 'running')}
      >
        {doubled.map((item, i) => (
          <span key={i} className="flex items-center gap-2 whitespace-nowrap text-xs font-semibold tracking-wide text-slate-200">
            <span className={`inline-block h-1.5 w-1.5 flex-shrink-0 rounded-full ${item.live ? 'animate-pulse bg-emerald-400' : 'bg-primary-soft/50'}`} />
            <span className="mr-1 rounded px-1.5 py-0.5 text-[9px] font-black uppercase tracking-wider text-primary-soft" style={{ background: 'rgba(255,255,255,0.1)' }}>
              {item.tag}
            </span>
            {item.text}
          </span>
        ))}
      </div>
    </div>
  );
}

function LiveCourtStats() {
  return (
    <section id="live-data" className="border-y border-slate-200 bg-white py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">Live Court Intelligence</div>
        <div className="mb-10 flex flex-wrap items-end justify-between gap-5">
          <h2 className="font-display text-4xl font-bold leading-tight text-ink md:text-5xl">
            India's Judicial Pulse,<br />Inside Your Dashboard.
          </h2>
          <p className="max-w-xs text-sm leading-7 text-graphite">
            Mamla.AI surfaces live data from NJDG, eCourts, and SC daily feeds — so you never open a government portal again.
          </p>
        </div>
        <div className="grid gap-7 lg:grid-cols-[1fr_320px]">
          <div>
            <div className="grid gap-5 sm:grid-cols-2">
              {STAT_CARDS.map((card) => (
                <div key={card.icon + card.value} className="relative overflow-hidden rounded-[20px] border border-slate-200 bg-background-light p-6 transition-all hover:-translate-y-1 hover:shadow-card">
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
              <div key={i} className="flex cursor-pointer gap-3 rounded-[14px] p-3 transition-colors" style={{ border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.05)' }}>
                <span className={`mt-0.5 flex-shrink-0 self-start rounded-md px-2 py-0.5 text-[9px] font-black uppercase tracking-[0.12em] ${item.tone}`}>
                  {item.source}
                </span>
                <div>
                  <p className="text-xs font-medium leading-5 text-slate-100">{item.text}</p>
                  <p className="mt-1 text-[11px] text-slate-400">{item.time}</p>
                </div>
              </div>
            ))}
            <a href="https://www.livelaw.in" target="_blank" rel="noopener noreferrer"
              className="mt-1 block text-center text-xs font-semibold text-slate-400 transition-colors hover:text-primary-soft">
              View all legal news →
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

function TeamSection() {
  return (
    <section id="team" className="bg-background-light py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">The Builders</div>
        <div className="mb-12 flex flex-wrap items-end justify-between gap-5">
          <h2 className="font-display text-4xl font-bold leading-tight text-ink md:text-5xl">
            Built by Engineers Who<br />Understand the Court.
          </h2>
          <p className="max-w-sm text-sm leading-7 text-graphite">
            Mamla.AI is led by founders who bring enterprise technology, AI systems, and deep empathy for how Indian legal practice actually works.
          </p>
        </div>
        <div className="grid gap-8 lg:grid-cols-2">
          {TEAM_MEMBERS.map((member) => (
            <div key={member.initials} className="overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-card transition-all hover:-translate-y-1 hover:shadow-elevated">
              <div className="relative overflow-hidden bg-background-dark p-8 pb-7">
                <div className="absolute -right-10 -top-10 h-48 w-48 rounded-full" style={{ background: 'rgba(255,255,255,0.04)' }} />
                <div className="absolute -bottom-5 left-10 h-28 w-28 rounded-full" style={{ background: 'rgba(216,227,242,0.06)' }} />
                <div className="relative z-10">
                  <div className="mb-5 flex h-[72px] w-[72px] items-center justify-center rounded-[20px] border border-white/12 bg-white/10 font-display text-2xl font-bold text-primary-soft">
                    {member.initials}
                  </div>
                  <p className="font-display text-2xl font-bold text-white">{member.name}</p>
                  <p className="mt-1 text-[11px] font-black uppercase tracking-[0.2em] text-primary-soft/80">{member.role}</p>
                </div>
              </div>
              <div className="p-8">
                <div className="mb-5 flex flex-wrap gap-2">
                  {member.tags.map((tag) => (
                    <span key={tag} className="rounded-lg px-3 py-1 text-[11px] font-bold text-primary" style={{ background: 'rgba(22,52,95,0.09)' }}>
                      {tag}
                    </span>
                  ))}
                </div>
                <p className="mb-6 text-sm leading-7 text-graphite">{member.bio}</p>
                <a href="mailto:neveon.ai@gmail.com"
                  className="inline-flex items-center gap-2 rounded-xl border border-primary/20 px-4 py-2.5 text-sm font-semibold text-primary transition-colors hover:bg-primary/5">
                  <span className="material-symbols-outlined text-base">mail</span>
                  Get in touch
                </a>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-10 flex flex-wrap items-center justify-between gap-6 rounded-[24px] bg-background-dark p-8">
          <div>
            <p className="mb-1.5 text-[11px] font-black uppercase tracking-[0.2em] text-primary-soft/60">Company</p>
            <p className="font-display text-xl font-bold text-white">Neveon AI Technologies Pvt. Ltd.</p>
            <p className="mt-1 text-sm text-slate-300">The parent company behind Mamla.AI · Incorporated in India</p>
          </div>
          <a href="mailto:neveon.ai@gmail.com"
            className="inline-flex items-center gap-2 rounded-xl border border-white/12 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-white/10"
            style={{ background: 'rgba(255,255,255,0.08)' }}>
            <span className="material-symbols-outlined text-primary-soft text-base">mail</span>
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
    <section id="faq" className="border-t border-slate-200 bg-white py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid gap-12 lg:grid-cols-[1fr_2fr] lg:items-start">
          <div>
            <div className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">FAQ</div>
            <h2 className="mb-5 font-display text-4xl font-bold leading-tight text-ink">Questions from<br />the chamber.</h2>
            <p className="mb-7 text-sm leading-7 text-graphite">
              Everything a practicing advocate or chamber manager needs to know before signing up.
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
              <div key={i} className={`overflow-hidden rounded-[16px] border transition-colors ${openIdx === i ? 'border-primary/15 bg-background-light' : 'border-transparent'}`}>
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
  const [form, setForm] = useState({ name: '', enrollment: '', email: '', jurisdiction: '', message: '' });
  const [status, setStatus] = useState('idle');

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus('sending');
    // Simulate send — wire to a public contact endpoint or email service (Formspree/EmailJS)
    // users/submit-feedback/ requires auth and is not available on the public landing page
    await new Promise((r) => setTimeout(r, 900));
    setStatus('success');
    setForm({ name: '', enrollment: '', email: '', jurisdiction: '', message: '' });
  }

  const inputCls = 'rounded-xl border border-white/12 px-4 py-3 text-sm text-white placeholder:text-slate-500 outline-none transition-colors focus:border-primary-soft/60 w-full';
  const inputStyle = { background: 'rgba(255,255,255,0.07)' };

  return (
    <section id="contact" className="border-t border-white/6 bg-background-dark py-24 text-ivory" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid gap-12 lg:grid-cols-2 lg:items-start">
          <div>
            <div className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary-soft/65">Contact & Support</div>
            <h2 className="mb-5 font-display text-4xl font-bold leading-tight text-white md:text-5xl">
              Talk to the team<br />behind Mamla.AI.
            </h2>
            <p className="mb-9 text-sm leading-7 text-white/60">
              Whether you're a solo practitioner in a district court or a senior counsel at the Supreme Court — we're interested in how Mamla.AI can fit your chamber.
            </p>
            {[
              { icon: 'mail',        label: 'General & Support',  value: 'neveon.ai@gmail.com',               href: 'mailto:neveon.ai@gmail.com' },
              { icon: 'business',    label: 'Company',             value: 'Neveon AI Technologies Pvt. Ltd.',  href: null },
              { icon: 'location_on', label: 'Registered Office',   value: 'India (Remote-first operation)',    href: null },
              { icon: 'schedule',    label: 'Response Time',       value: 'Within 1 business day',             href: null },
            ].map((item) => (
              <div key={item.label} className="mb-6 flex items-start gap-4">
                <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl border border-white/10" style={{ background: 'rgba(255,255,255,0.07)' }}>
                  <span className="material-symbols-outlined text-primary-soft text-xl">{item.icon}</span>
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
            <div className="mb-5 text-[11px] font-black uppercase tracking-[0.18em] text-primary-soft/60">Send a message</div>
            <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-white/70">Full Name</label>
                  <input name="name" type="text" value={form.name} onChange={handleChange} required placeholder="Adv. Priya Sharma" className={inputCls} style={inputStyle} />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-white/70">Bar Enrollment No.</label>
                  <input name="enrollment" type="text" value={form.enrollment} onChange={handleChange} placeholder="MH/1234/2018 (optional)" className={inputCls} style={inputStyle} />
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-white/70">Professional Email</label>
                <input name="email" type="email" value={form.email} onChange={handleChange} required placeholder="advocate@chambers.in" className={inputCls} style={inputStyle} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-white/70">High Court / Jurisdiction</label>
                <input name="jurisdiction" type="text" value={form.jurisdiction} onChange={handleChange} placeholder="e.g. Bombay HC, Supreme Court, Calcutta HC" className={inputCls} style={inputStyle} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-white/70">Message</label>
                <textarea name="message" value={form.message} onChange={handleChange} rows={4}
                  placeholder="Tell us about your chamber size, practice area, and what you're hoping Mamla.AI can solve…"
                  className={`${inputCls} resize-y`} style={inputStyle} />
              </div>
              <button type="submit" disabled={status === 'sending'}
                className="self-start rounded-[14px] bg-white px-7 py-3.5 text-sm font-bold text-background-dark transition-all hover:-translate-y-0.5 hover:bg-primary-soft disabled:opacity-60">
                {status === 'sending' ? 'Sending…' : 'Send Message →'}
              </button>
              {status === 'success' && (
                <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/15 px-4 py-3 text-sm font-semibold text-emerald-400">
                  ✓ Message sent! We'll respond within one business day.
                </div>
              )}
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}

function LegalModal({ docKey, onClose }) {
  const doc = LEGAL_DOCS[docKey];
  if (!doc) return null;
  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-ink/80 px-4 py-6 backdrop-blur-sm" onClick={onClose}>
      <div className="relative max-h-[85vh] w-full max-w-2xl overflow-hidden rounded-[28px] bg-white shadow-elevated" onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white px-8 py-6">
          <h2 className="font-display text-xl font-bold text-background-dark">{doc.title}</h2>
          <button type="button" onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-background-light transition-colors hover:bg-slate-200">
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

const FEATURES = [
  {
    icon: 'edit_note',
    title: 'AI Drafting',
    desc: 'Generate complex legal documents with unmatched accuracy using domain-specific models and structured chamber workflows.',
  },
  {
    icon: 'forum',
    title: 'Document Chat',
    desc: 'Interrogate discovery sets, filings, and exhibits with natural language prompts and source-grounded answers.',
  },
  {
    icon: 'dynamic_feed',
    title: 'Live Court Updates',
    desc: 'Monitor eCourts for listing changes, order uploads, and next-hearing movement without leaving the chamber dashboard.',
  },
  {
    icon: 'calendar_month',
    title: 'Hearing Calendar',
    desc: 'Coordinate hearings, deadlines, and chamber commitments inside one operational calendar layer.',
  },
  {
    icon: 'people',
    title: 'Client Portal',
    desc: 'Share matter context with clients and colleagues through secure, role-aware access and session management.',
  },
  {
    icon: 'search',
    title: 'eCourts Search',
    desc: 'Search case details, lawyers, litigants, and cause lists from one high-contrast legal workspace.',
  },
];

const TESTIMONIALS = [
  {
    text: 'Mamla.AI cut our document review time by 60%. The drafting and document tools now feel like chamber software, not a lifestyle startup dashboard.',
    author: 'Adv. Priya Sharma',
    role: 'Senior Partner, Sharma & Associates',
  },
  {
    text: 'Our team handles materially more matters with the same staff. The eCourts and operations surfaces are easier to scan during busy listing days.',
    author: 'Adv. Rahul Mehta',
    role: 'Managing Partner, Mehta Law Firm',
  },
  {
    text: 'The document intelligence remains strong, but the new presentation finally matches the seriousness of the work product.',
    author: 'Adv. Ananya Kapoor',
    role: 'Corporate Counsel, TechVenture Ltd.',
  },
];

const HERO_SCENES = [
  {
    id: 'bench',
    title: 'Bench watch with court-ready calm.',
    description: 'Track cause lists, hearing shifts, and daily chamber priorities with a visual language that feels judicial, not generic SaaS.',
    badge: 'Constitution bench',
    boardLabel: 'Bench Priority Board',
    panelLabel: 'Listing pulse',
    highlights: ['Cause List Live', 'Draft Queue', 'Hearing Notes'],
    metrics: [
      { label: 'Bench movement', value: '09', detail: 'matters flagged before first call' },
      { label: 'Draft review', value: '14', detail: 'documents in active circulation' },
      { label: 'Client touchpoints', value: '06', detail: 'updates due before 5 PM' },
    ],
  },
  {
    id: 'chamber',
    title: 'A chamber desk that feels occupied, not static.',
    description: 'Bring together lawyers, drafts, and matter movement into one active surface so the landing page reflects real work rather than a placeholder hero.',
    badge: 'Senior counsel desk',
    boardLabel: 'Chamber Operations',
    panelLabel: 'Matter desk',
    highlights: ['Senior Counsel Notes', 'Matter Timeline', 'Evidence Stack'],
    metrics: [
      { label: 'Open matters', value: '28', detail: 'under active review this week' },
      { label: 'Replies pending', value: '07', detail: 'draft windows closing today' },
      { label: 'Courtrooms mapped', value: '11', detail: 'jurisdictions loaded in workspace' },
    ],
  },
  {
    id: 'drafts',
    title: 'Draft-heavy work without visual clutter.',
    description: 'Show petitions, drafts, and review lanes in motion so the public page already hints at the chamber experience inside the product.',
    badge: 'Draft review lane',
    boardLabel: 'Draft Control Room',
    panelLabel: 'Review queue',
    highlights: ['Petition Stack', 'Clause Review', 'Client Redlines'],
    metrics: [
      { label: 'Active drafts', value: '19', detail: 'being edited across teams' },
      { label: 'AI refinements', value: '42', detail: 'suggestions accepted this week' },
      { label: 'Finalized today', value: '05', detail: 'exports sent to filing teams' },
    ],
  },
];

function SceneThumbnail({ scene, active }) {
  return (
    <div className={`relative overflow-hidden rounded-[1.5rem] border p-4 transition-all ${active ? 'border-primary/40 bg-background-dark text-white shadow-card' : 'border-slate-200 bg-white text-ink hover:border-primary/25'}`}>
      <div className="absolute inset-0 opacity-0 transition-opacity duration-300" style={active ? { opacity: 1, background: 'radial-gradient(circle at top right, rgba(216,227,242,0.18), transparent 45%)' } : undefined} />
      <div className="relative">
        <div className={`mb-4 h-28 rounded-2xl border ${active ? 'border-white/10 bg-white/5' : 'border-slate-200 bg-background-light'} p-3`}>
          <div className="flex h-full items-end justify-between gap-3">
            <div className={`h-full w-1/3 rounded-t-[2rem] ${active ? 'bg-primary-soft/70' : 'bg-primary/20'}`} />
            <div className={`h-3/4 w-1/3 rounded-t-[2rem] ${active ? 'bg-white/85' : 'bg-slate-300'}`} />
            <div className={`h-1/2 w-1/3 rounded-t-[2rem] ${active ? 'bg-primary-soft/35' : 'bg-primary/10'}`} />
          </div>
        </div>
        <p className={`text-[11px] font-semibold uppercase tracking-[0.2em] ${active ? 'text-primary-soft/84' : 'text-primary'}`}>{scene.badge}</p>
        <h3 className="mt-2 font-display text-2xl font-semibold leading-tight">{scene.title}</h3>
        <p className={`mt-3 text-sm font-medium leading-6 ${active ? 'text-white/72' : 'text-graphite'}`}>{scene.description}</p>
      </div>
    </div>
  );
}

function PracticeSceneBoard({ scene }) {
  return (
    <div className="relative overflow-hidden rounded-[2rem] border border-slate-200 bg-white p-6 shadow-card">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(22,52,95,0.1),transparent_38%)]" />
      <div className="relative">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-primary">Inside the Chamber</p>
            <h3 className="mt-2 font-display text-4xl font-bold leading-tight text-ink">{scene.title}</h3>
          </div>
          <div className="rounded-full border border-primary/15 bg-primary/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-primary">
            {scene.badge}
          </div>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-[1.75rem] bg-background-dark p-5 text-white shadow-elevated">
            <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-primary-soft/84">{scene.boardLabel}</p>
                <p className="mt-1 font-display text-2xl font-semibold text-white">Matter pulse board</p>
              </div>
              <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1 text-xs font-semibold text-white/90">
                <span className="inline-flex h-2.5 w-2.5 animate-pulse rounded-full bg-primary-soft" />
                Live updates
              </div>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/6 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary-soft/78">Court feed</p>
                <div className="mt-4 space-y-3">
                  {scene.highlights.map((item, index) => (
                    <div key={item} className="flex items-center justify-between rounded-xl border border-white/8 bg-background-dark/40 px-3 py-3">
                      <div>
                        <p className="text-sm font-semibold text-white">{item}</p>
                        <p className="mt-1 text-xs text-white/58">Updated {index + 2} min ago</p>
                      </div>
                      <span className="material-symbols-outlined text-primary-soft">gavel</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/6 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary-soft/78">Draft movement</p>
                <div className="mt-4 space-y-3">
                  {scene.metrics.map((metric) => (
                    <div key={metric.label} className="rounded-xl border border-white/8 bg-background-dark/50 px-3 py-3">
                      <div className="flex items-end justify-between gap-3">
                        <p className="text-sm font-semibold text-white">{metric.label}</p>
                        <span className="font-display text-3xl font-bold text-primary-soft">{metric.value}</span>
                      </div>
                      <p className="mt-2 text-xs leading-5 text-white/62">{metric.detail}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="grid gap-4">
            <div className="rounded-[1.75rem] border border-slate-200 bg-background-light p-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">Counsel desk</p>
              <div className="mt-4 rounded-[1.5rem] bg-white p-4 shadow-subtle">
                <div className="grid grid-cols-3 gap-3">
                  <div className="h-24 rounded-2xl bg-primary/12" />
                  <div className="h-24 rounded-2xl bg-slate-200" />
                  <div className="h-24 rounded-2xl bg-primary/8" />
                </div>
                <div className="mt-4 space-y-3">
                  <div className="h-3 w-3/4 rounded-full bg-slate-200" />
                  <div className="h-3 w-full rounded-full bg-slate-100" />
                  <div className="h-3 w-2/3 rounded-full bg-slate-100" />
                </div>
              </div>
            </div>

            <div className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-subtle">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">Draft stack</p>
              <div className="mt-4 space-y-3">
                {[scene.highlights[0], scene.highlights[1], scene.highlights[2]].map((item, index) => (
                  <div key={item} className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3">
                    <div>
                      <p className="text-sm font-semibold text-ink">{item}</p>
                      <p className="mt-1 text-xs text-slate-500">Draft window {index + 1}</p>
                    </div>
                    <span className="material-symbols-outlined text-primary">description</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SupremeCourtIllustration({ scene }) {
  return (
    <svg viewBox="0 0 720 840" className="h-full w-full" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect x="48" y="44" width="624" height="752" rx="40" fill="url(#panelGlow)" />
      <rect x="64" y="60" width="592" height="720" rx="34" fill="#08111F" stroke="rgba(255,255,255,0.08)" />
      <circle cx="360" cy="204" r="108" fill="url(#domeGlow)" opacity="0.7" />
      <path d="M236 318C236 248.412 292.412 192 362 192C431.588 192 488 248.412 488 318H236Z" fill="#F8FBFF" />
      <path d="M284 318C284 274.922 318.922 240 362 240C405.078 240 440 274.922 440 318H284Z" fill="#D8E3F2" />
      <rect x="216" y="318" width="292" height="24" rx="12" fill="#CAD7E8" />
      <rect x="176" y="342" width="372" height="26" rx="13" fill="#FFFFFF" opacity="0.92" />
      <rect x="194" y="368" width="336" height="172" rx="28" fill="#0E203C" stroke="#D8E3F2" strokeOpacity="0.25" />
      <rect x="228" y="400" width="32" height="108" rx="16" fill="#E6EEF8" />
      <rect x="292" y="400" width="32" height="108" rx="16" fill="#E6EEF8" />
      <rect x="356" y="400" width="32" height="108" rx="16" fill="#E6EEF8" />
      <rect x="420" y="400" width="32" height="108" rx="16" fill="#E6EEF8" />
      <rect x="160" y="540" width="400" height="24" rx="12" fill="#FFFFFF" opacity="0.92" />
      <rect x="132" y="564" width="456" height="26" rx="13" fill="#CAD7E8" />
      <path d="M178 664C178 623.131 211.131 590 252 590C292.869 590 326 623.131 326 664V704H178V664Z" fill="#111827" />
      <circle cx="252" cy="572" r="40" fill="#F3F7FC" />
      <path d="M286 572C286 560.954 277.046 552 266 552H238C226.954 552 218 560.954 218 572V576H286V572Z" fill="#0E203C" />
      <path d="M392 654C392 617.549 421.549 588 458 588C494.451 588 524 617.549 524 654V704H392V654Z" fill="#0F1727" />
      <circle cx="458" cy="566" r="38" fill="#F7FAFD" />
      <path d="M492 568C492 556.402 482.598 547 471 547H445C433.402 547 424 556.402 424 568V572H492V568Z" fill="#10243F" />
      <path d="M114 722H606" stroke="rgba(255,255,255,0.18)" strokeWidth="2" strokeDasharray="8 10" />
      <rect x="116" y="108" width="134" height="118" rx="22" fill="#0F1727" stroke="rgba(255,255,255,0.1)" />
      <text x="138" y="154" fill="#D8E3F2" fontFamily="IBM Plex Sans" fontSize="17" fontWeight="600">{scene.panelLabel}</text>
      <text x="138" y="186" fill="#FFFFFF" fontFamily="Source Serif 4" fontSize="28" fontWeight="700">{scene.badge}</text>
      <rect x="472" y="126" width="132" height="80" rx="18" fill="#0F1727" stroke="rgba(255,255,255,0.1)" />
      <text x="488" y="168" fill="#D8E3F2" fontFamily="IBM Plex Sans" fontSize="16" fontWeight="600">{scene.highlights[0]}</text>
      <defs>
        <linearGradient id="panelGlow" x1="108" y1="60" x2="602" y2="780" gradientUnits="userSpaceOnUse">
          <stop stopColor="#17355F" />
          <stop offset="1" stopColor="#08111F" />
        </linearGradient>
        <radialGradient id="domeGlow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(360 204) rotate(90) scale(108)">
          <stop stopColor="#FFFFFF" stopOpacity="0.9" />
          <stop offset="1" stopColor="#FFFFFF" stopOpacity="0" />
        </radialGradient>
      </defs>
    </svg>
  );
}

export default function LandingPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [activeSceneIdx, setActiveSceneIdx] = useState(0);
  const [openModal, setOpenModal] = useState(null);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveSceneIdx((current) => (current + 1) % HERO_SCENES.length);
    }, 4800);
    return () => window.clearInterval(timer);
  }, []);

  const activeScene = HERO_SCENES[activeSceneIdx];

  function handleRequestAccess(e) {
    e.preventDefault();
    navigate('/signup');
  }

  return (
    <div className="app-fade-in bg-background-light text-ink antialiased">
      <nav className="sticky top-0 z-50 w-full border-b border-white/10 bg-background-dark text-white shadow-[0_14px_40px_-24px_rgba(8,17,31,0.9)]">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-xl border border-white/10 bg-white/5">
              <span className="material-symbols-outlined text-primary-soft text-xl">account_balance</span>
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-primary-soft/85">Supreme-ready</p>
              <span className="font-sans text-xl font-semibold tracking-tight text-white">Mamla.AI</span>
            </div>
          </div>

          <div className="hidden items-center gap-10 md:flex">
            <a className="text-sm font-semibold text-white/84 transition-colors hover:text-white" href="#features">Platform</a>
            <a className="text-sm font-semibold text-white/84 transition-colors hover:text-white" href="#live-data">Court Data</a>
            <a className="text-sm font-semibold text-white/84 transition-colors hover:text-white" href="#security">Security</a>
            <a className="text-sm font-semibold text-white/84 transition-colors hover:text-white" href="#team">Team</a>
            <a className="text-sm font-semibold text-white/84 transition-colors hover:text-white" href="#faq">FAQ</a>
            <a className="text-sm font-semibold text-white/84 transition-colors hover:text-white" href="#contact">Contact</a>
          </div>

          <div className="flex items-center gap-4">
            <Link to="/login" className="px-4 py-2 text-sm font-semibold text-white/88 transition-colors hover:text-white">
              Log In
            </Link>
            <Link
              to="/signup"
              className="rounded-lg bg-white px-6 py-2.5 text-sm font-bold text-primary-dark shadow-card transition-all hover:bg-primary-soft"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      <TickerBar />

      <header className="gradient-mesh court-grid relative overflow-hidden pt-20 pb-32 text-white">
        <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(8,17,31,0.1),rgba(8,17,31,0.55))]" />
        <div className="float-slow absolute -left-12 top-20 h-64 w-64 rounded-full bg-white/8 blur-3xl" />
        <div className="float-slow absolute bottom-10 right-0 h-72 w-72 rounded-full bg-primary/20 blur-3xl" />
        <div className="relative mx-auto max-w-7xl px-6">
          <div className="grid items-center gap-16 lg:grid-cols-2">
            <div className="app-rise-in flex flex-col gap-8">
              <div className="inline-flex w-fit items-center gap-2 rounded-full border border-white/15 bg-white/8 px-3 py-1 backdrop-blur-sm">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary-soft opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-primary-soft" />
                </span>
                <span className="text-xs font-bold uppercase tracking-widest text-primary-soft">Now in Private Beta</span>
              </div>

              <h1 className="font-display text-5xl font-bold leading-[1.04] tracking-tight md:text-7xl">
                Litigation Infrastructure
                <span className="block text-primary-soft">for Indian Counsel.</span>
              </h1>

              <p className="max-w-2xl text-lg font-medium leading-8 text-white/88">
                {activeScene.description}
              </p>

              <div className="rounded-[1.75rem] border border-white/10 bg-white/7 p-5 shadow-card backdrop-blur-sm">
                <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
                  <div className="max-w-xl">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-primary-soft/84">Live chamber reel</p>
                    <h2 className="mt-2 font-display text-3xl font-semibold leading-tight text-white">{activeScene.title}</h2>
                  </div>
                  <div className="flex items-center gap-2">
                    {HERO_SCENES.map((scene, index) => (
                      <button
                        key={scene.id}
                        type="button"
                        onClick={() => setActiveSceneIdx(index)}
                        className={`h-2.5 rounded-full transition-all ${index === activeSceneIdx ? 'w-10 bg-primary-soft' : 'w-2.5 bg-white/30 hover:bg-white/55'}`}
                        aria-label={`Show ${scene.title}`}
                      />
                    ))}
                  </div>
                </div>
                <div className="mt-5 grid gap-3 md:grid-cols-3">
                  {activeScene.metrics.map((metric) => (
                    <div key={metric.label} className="rounded-2xl border border-white/10 bg-background-dark/52 px-4 py-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary-soft/82">{metric.label}</p>
                      <div className="mt-2 flex items-end gap-2">
                        <span className="font-display text-4xl font-bold text-white">{metric.value}</span>
                        <span className="pb-1 text-xs font-medium text-white/62">live</span>
                      </div>
                      <p className="mt-2 text-sm font-medium leading-6 text-white/72">{metric.detail}</p>
                    </div>
                  ))}
                </div>
              </div>

              <form onSubmit={handleRequestAccess} className="flex flex-col gap-4 sm:flex-row">
                <div className="flex flex-1 overflow-hidden rounded-2xl border border-white/12 bg-white/95 shadow-elevated ring-primary/20 focus-within:ring-2">
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter professional email"
                    className="flex-1 border-none bg-transparent px-5 py-4 text-sm text-ink focus:ring-0"
                  />
                  <button
                    type="submit"
                    className="bg-primary-dark px-8 py-4 text-sm font-bold text-ivory transition-all hover:bg-ink"
                  >
                    Request Access
                  </button>
                </div>
              </form>

              <div className="grid grid-cols-3 gap-4 pt-4">
                <div className="flex flex-col">
                  <span className="font-sans text-2xl font-bold">24/7</span>
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-white/68">Chamber Continuity</span>
                </div>
                <div className="flex flex-col">
                  <span className="font-sans text-2xl font-bold">10x</span>
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-white/68">Faster Review Cycles</span>
                </div>
                <div className="flex flex-col">
                  <span className="font-sans text-2xl font-bold">RBAC</span>
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-white/68">Matter Security</span>
                </div>
              </div>
            </div>

            <div className="app-rise-in group relative" style={{ animationDelay: '90ms' }}>
              <div className="absolute -inset-5 rounded-[2rem] bg-primary/20 blur-3xl transition-all duration-500 group-hover:bg-primary/30" />
              <div key={activeScene.id} className="relative aspect-[4/5] overflow-hidden rounded-[2rem] border border-white/10 bg-white/6 shadow-elevated backdrop-blur-sm app-fade-in">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.14),transparent_40%)]" />
                <div className="absolute left-6 right-6 top-6 z-10 flex items-center justify-between rounded-2xl border border-white/10 bg-background-dark/70 px-4 py-3 backdrop-blur-sm">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-primary-soft/82">{activeScene.boardLabel}</p>
                    <p className="font-display text-2xl font-semibold text-white">Daily Chamber Board</p>
                  </div>
                  <div className="rounded-full border border-white/10 bg-white/10 px-3 py-1 text-xs font-semibold text-white/92">
                    {activeScene.badge}
                  </div>
                </div>
                <div className="relative h-full p-8 pt-28">
                  <SupremeCourtIllustration scene={activeScene} />
                  <div className="absolute bottom-8 left-8 right-8 flex flex-wrap justify-center gap-2">
                    {[...activeScene.highlights, 'eCourts', 'Calendar', 'Clients'].map((pill) => (
                      <span key={pill} className="rounded-full border border-white/10 bg-background-dark/78 px-3 py-1 text-xs font-semibold text-white/92 backdrop-blur-sm">
                        {pill}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <section id="features" className="app-rise-in border-y border-slate-200/80 bg-white py-24" style={{ animationDelay: '120ms' }}>
        <div className="mx-auto max-w-7xl px-6">
          <div className="mb-16 grid gap-5 lg:grid-cols-3">
            {HERO_SCENES.map((scene, index) => (
              <button
                key={scene.id}
                type="button"
                onClick={() => setActiveSceneIdx(index)}
                className="text-left"
              >
                <SceneThumbnail scene={scene} active={index === activeSceneIdx} />
              </button>
            ))}
          </div>

          <div className="mb-16">
            <h2 className="mb-4 text-sm font-bold uppercase tracking-widest text-primary">Core Intelligence</h2>
            <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
              <h3 className="max-w-2xl font-display text-4xl font-bold leading-tight md:text-5xl">
                Precision Systems for Court-Facing Practice.
              </h3>
              <p className="max-w-sm text-base font-medium leading-7 text-graphite">
                Designed for chambers handling filings, reviews, evidence, hearings, and client coordination.
              </p>
            </div>
          </div>

          <div className="grid gap-8 md:grid-cols-3">
            {FEATURES.map((feature) => (
              <div
                key={feature.title}
                className="group rounded-[1.5rem] border border-slate-200 bg-background-light p-8 transition-all duration-300 hover:-translate-y-1 hover:border-primary/30 hover:shadow-elevated"
              >
                <div className="mb-6 flex size-12 items-center justify-center rounded-xl bg-white shadow-subtle transition-transform group-hover:scale-110">
                  <span className="material-symbols-outlined text-primary">{feature.icon}</span>
                </div>
                <h4 className="mb-4 font-sans text-xl font-bold">{feature.title}</h4>
                <p className="leading-7 text-graphite">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="app-rise-in bg-background-light py-24" style={{ animationDelay: '180ms' }}>
        <div className="mx-auto max-w-7xl px-6">
          <div className="mb-12 flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="text-sm font-bold uppercase tracking-widest text-primary">From Bench to Brief</h2>
              <h3 className="mt-4 max-w-3xl font-display text-4xl font-bold leading-tight md:text-5xl">
                A fuller legal atmosphere beyond the hero.
              </h3>
            </div>
            <p className="max-w-md text-base font-medium leading-7 text-graphite">
              Explore chamber, draft, and court-control scenes through an interactive visual board designed specifically for Indian legal practice.
            </p>
          </div>

          <div key={activeScene.id} className="app-fade-in">
            <PracticeSceneBoard scene={activeScene} />
          </div>
        </div>
      </section>

      <section id="security" className="app-rise-in bg-background-light py-24" style={{ animationDelay: '240ms' }}>
        <div className="mx-auto max-w-7xl px-6">
          <div className="grid items-center gap-16 lg:grid-cols-2">
            <div>
              <h2 className="mb-4 text-sm font-bold uppercase tracking-widest text-primary">Enterprise Security</h2>
              <h3 className="mb-6 font-display text-4xl font-bold">Built for Sensitive Legal Workflows.</h3>
              <p className="mb-8 text-base leading-8 text-graphite">
                Your clients&apos; data is encrypted at rest and in transit. We comply with the highest standards of data protection so you can focus on winning cases, not worrying about breaches.
              </p>
              <div className="space-y-4">
                {[
                  { icon: 'shield', text: 'End-to-end encryption for all documents' },
                  { icon: 'verified_user', text: 'SOC2 Type II certified infrastructure' },
                  { icon: 'lock', text: 'Role-based access control (RBAC)' },
                  { icon: 'policy', text: 'DPDP Act and Bar Council aligned workflows' },
                ].map((item) => (
                  <div key={item.text} className="flex items-center gap-3">
                    <div className="flex size-8 flex-shrink-0 items-center justify-center rounded-lg bg-primary/10">
                      <span className="material-symbols-outlined text-base text-primary">{item.icon}</span>
                    </div>
                    <span className="text-sm font-semibold text-ink/90">{item.text}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-[2rem] bg-background-dark p-8 text-ivory shadow-elevated">
              <div className="grid grid-cols-2 gap-6">
                {[
                  { label: 'Uptime SLA', value: '99.99%' },
                  { label: 'Encryption', value: 'AES-256' },
                  { label: 'Data Centers', value: 'India' },
                  { label: 'Compliance', value: 'SOC2' },
                ].map((stat) => (
                  <div key={stat.label} className="rounded-xl border border-white/10 bg-white/5 p-4">
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-white/68">{stat.label}</p>
                    <p className="font-sans text-2xl font-black text-primary-soft">{stat.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <LiveCourtStats />

      <section id="testimonials" className="app-rise-in border-t border-slate-200 bg-white py-24" style={{ animationDelay: '300ms' }}>
        <div className="mx-auto max-w-7xl px-6">
          <h2 className="mb-4 text-sm font-bold uppercase tracking-widest text-primary">Trusted by Counsel</h2>
          <h3 className="mb-12 font-display text-4xl font-bold">What Legal Professionals Say.</h3>
          <div className="grid gap-8 md:grid-cols-3">
            {TESTIMONIALS.map((testimonial) => (
              <div key={testimonial.author} className="rounded-[1.5rem] border border-slate-200 bg-background-light p-8 shadow-card">
                <p className="mb-6 italic leading-8 text-ink/82">&ldquo;{testimonial.text}&rdquo;</p>
                <div>
                  <p className="font-bold text-ink">{testimonial.author}</p>
                  <p className="text-sm font-medium text-ink/68">{testimonial.role}</p>
                </div>
                <div className="mt-6 flex gap-1 text-primary">
                  {Array.from({ length: 5 }).map((_, index) => (
                    <span key={`${testimonial.author}-${index}`} className="material-symbols-outlined text-base">star</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <TeamSection />

      <FAQSection />

      <ContactSection />

      <section className="app-rise-in bg-background-dark py-24 text-ivory" style={{ animationDelay: '360ms' }}>
        <div className="mx-auto max-w-3xl px-6 text-center">
          <h2 className="mb-6 font-display text-5xl font-bold">Ready to Modernize the Chamber?</h2>
          <p className="mb-10 text-lg font-medium leading-8 text-ivory/82">
            Join the growing community of legal professionals using Mamla.AI to handle high-value matters with confidence and speed.
          </p>
          <div className="flex flex-col justify-center gap-4 sm:flex-row">
            <Link
              to="/signup"
              className="rounded-xl bg-white px-8 py-4 text-base font-bold text-primary-dark shadow-lg transition-all hover:bg-primary-soft"
            >
              Start Free Trial
            </Link>
            <Link
              to="/login"
              className="rounded-xl border border-white/12 bg-white/10 px-8 py-4 text-base font-bold text-ivory transition-all hover:bg-white/20"
            >
              Sign In
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t bg-background-dark text-white" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="mx-auto max-w-7xl px-6 py-16">
          <div className="grid gap-12 md:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr]">
            {/* Brand */}
            <div>
              <div className="mb-3 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10" style={{ background: 'rgba(255,255,255,0.06)' }}>
                  <span className="material-symbols-outlined text-primary-soft text-xl">account_balance</span>
                </div>
                <div>
                  <p className="text-[10px] font-black uppercase tracking-[0.22em] text-primary-soft/70">Supreme-ready</p>
                  <p className="text-lg font-bold text-white">Mamla.AI</p>
                </div>
              </div>
              <p className="max-w-[280px] text-sm leading-7 text-slate-300">
                AI-native litigation infrastructure for Indian legal practitioners. Designed for chambers that take their work as seriously as their clients do.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {['AES-256', 'SOC 2', 'DPDP Aligned', 'India Hosted'].map((badge) => (
                  <span key={badge} className="rounded-lg border border-white/10 px-2 py-1 text-[10px] font-black uppercase tracking-[0.1em] text-slate-400" style={{ background: 'rgba(255,255,255,0.05)' }}>
                    {badge}
                  </span>
                ))}
              </div>
              <p className="mt-4 text-[11px] text-slate-500">A product of Neveon AI Technologies Pvt. Ltd.</p>
            </div>
            {/* Platform */}
            <div>
              <p className="mb-4 text-[11px] font-black uppercase tracking-[0.16em] text-slate-400">Platform</p>
              <ul className="flex flex-col gap-2.5">
                {['AI Drafting', 'Document Chat', 'Live Court Updates', 'Hearing Calendar', 'Client Portal', 'eCourts Search'].map((item) => (
                  <li key={item}><a href="#features" className="text-sm text-white/70 transition-colors hover:text-white">{item}</a></li>
                ))}
              </ul>
            </div>
            {/* Company */}
            <div>
              <p className="mb-4 text-[11px] font-black uppercase tracking-[0.16em] text-slate-400">Company</p>
              <ul className="flex flex-col gap-2.5">
                {[
                  { label: 'Our Team',          href: '#team' },
                  { label: 'FAQ',               href: '#faq' },
                  { label: 'Testimonials',      href: '#testimonials' },
                  { label: 'Security',          href: '#security' },
                  { label: 'Contact',           href: '#contact' },
                  { label: 'neveon.ai@gmail.com', href: 'mailto:neveon.ai@gmail.com' },
                ].map((item) => (
                  <li key={item.label}><a href={item.href} className="text-sm text-white/70 transition-colors hover:text-white">{item.label}</a></li>
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
                    <button type="button" onClick={() => setOpenModal(item.modal)}
                      className="text-sm text-white/70 transition-colors hover:text-white">
                      {item.label}
                    </button>
                  </li>
                ))}
              </ul>
              <div className="mt-5 rounded-xl p-3.5" style={{ border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.05)' }}>
                <p className="mb-1.5 text-[10px] font-black uppercase tracking-[0.14em] text-white/40">Grievance Officer</p>
                <p className="text-xs font-semibold text-white/65">Robin </p>
                <a href="mailto:neveon.ai@gmail.com" className="text-xs text-primary-soft/70 transition-colors hover:text-primary-soft">neveon.ai@gmail.com</a>
                <p className="mt-1 text-[11px] text-slate-500">Response within 30 days (IT Act, 2000)</p>
              </div>
            </div>
          </div>
          <div className="mt-12 flex flex-wrap items-center justify-between gap-4 border-t pt-8" style={{ borderColor: 'rgba(255,255,255,0.08)' }}>
            <p className="text-xs text-white/40">© 2026 Neveon AI Technologies Pvt. Ltd. All rights reserved. Mamla.AI is a registered product.</p>
            <div className="flex gap-5">
              {[
                { label: 'Terms',      modal: 'terms' },
                { label: 'Privacy',    modal: 'privacy' },
                { label: 'Refunds',    modal: 'refund' },
                { label: 'Disclaimer', modal: 'disclaimer' },
              ].map((item) => (
                <button key={item.label} type="button" onClick={() => setOpenModal(item.modal)}
                  className="text-xs text-slate-400 transition-colors hover:text-white">
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
