import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

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
            <a className="text-sm font-semibold text-white/84 transition-colors hover:text-white" href="#features">Solutions</a>
            <a className="text-sm font-semibold text-white/84 transition-colors hover:text-white" href="#security">Security</a>
            <a className="text-sm font-semibold text-white/84 transition-colors hover:text-white" href="#testimonials">Testimonials</a>
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

      <footer className="border-t border-slate-200 bg-background-light py-12">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-6 px-6 md:flex-row">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined icon-filled text-primary">account_balance</span>
            <span className="font-sans font-bold">Mamla.AI</span>
          </div>
          <p className="text-sm font-medium text-ink/58">© 2026 Mamla.AI. All rights reserved. Secure and encrypted for chamber operations.</p>
          <div className="flex gap-6">
            <a href="#" className="text-sm font-medium text-ink/68 transition-colors hover:text-primary">Privacy</a>
            <a href="#" className="text-sm font-medium text-ink/68 transition-colors hover:text-primary">Terms</a>
            <a href="#" className="text-sm font-medium text-ink/68 transition-colors hover:text-primary">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
