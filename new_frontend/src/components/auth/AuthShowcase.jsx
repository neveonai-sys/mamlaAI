import React from 'react';

function ChamberShowcaseIllustration() {
  return (
    <svg viewBox="0 0 640 520" className="h-full w-full" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect x="36" y="40" width="568" height="440" rx="32" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.12)" />
      <rect x="72" y="82" width="496" height="48" rx="24" fill="rgba(8,17,31,0.55)" stroke="rgba(255,255,255,0.08)" />
      <circle cx="114" cy="106" r="7" fill="#D8E3F2" />
      <rect x="136" y="98" width="122" height="15" rx="7.5" fill="rgba(255,255,255,0.18)" />
      <rect x="420" y="94" width="108" height="22" rx="11" fill="rgba(255,255,255,0.12)" />
      <path d="M204 218C204 155.039 255.039 104 318 104C380.961 104 432 155.039 432 218H204Z" fill="#F8FBFF" />
      <path d="M248 218C248 179.34 279.34 148 318 148C356.66 148 388 179.34 388 218H248Z" fill="#D8E3F2" />
      <rect x="182" y="218" width="272" height="20" rx="10" fill="#CAD7E8" />
      <rect x="166" y="238" width="304" height="18" rx="9" fill="#FFFFFF" opacity="0.94" />
      <rect x="186" y="256" width="264" height="126" rx="26" fill="#0E203C" stroke="rgba(216,227,242,0.25)" />
      <rect x="214" y="284" width="24" height="76" rx="12" fill="#E6EEF8" />
      <rect x="270" y="284" width="24" height="76" rx="12" fill="#E6EEF8" />
      <rect x="326" y="284" width="24" height="76" rx="12" fill="#E6EEF8" />
      <rect x="382" y="284" width="24" height="76" rx="12" fill="#E6EEF8" />
      <rect x="120" y="382" width="396" height="18" rx="9" fill="#FFFFFF" opacity="0.94" />
      <rect x="100" y="404" width="436" height="18" rx="9" fill="#CAD7E8" />
      <rect x="94" y="328" width="84" height="112" rx="22" fill="rgba(8,17,31,0.55)" stroke="rgba(255,255,255,0.12)" />
      <rect x="462" y="154" width="108" height="86" rx="22" fill="rgba(8,17,31,0.55)" stroke="rgba(255,255,255,0.12)" />
      <rect x="478" y="176" width="76" height="10" rx="5" fill="rgba(255,255,255,0.2)" />
      <rect x="478" y="196" width="58" height="10" rx="5" fill="rgba(216,227,242,0.85)" />
      <rect x="478" y="216" width="44" height="10" rx="5" fill="rgba(255,255,255,0.14)" />
      <path d="M132 438C132 400.444 162.444 370 200 370C237.556 370 268 400.444 268 438V444H132V438Z" fill="#111827" />
      <circle cx="200" cy="354" r="34" fill="#F3F7FC" />
      <path d="M242 442C242 405.549 271.549 376 308 376C344.451 376 374 405.549 374 442V444H242V442Z" fill="#0F1727" />
      <circle cx="308" cy="360" r="34" fill="#F7FAFD" />
      <path d="M348 438C348 401.549 377.549 372 414 372C450.451 372 480 401.549 480 438V444H348V438Z" fill="#10243F" />
      <circle cx="414" cy="356" r="34" fill="#F7FAFD" />
      <path d="M84 458H556" stroke="rgba(255,255,255,0.18)" strokeWidth="2" strokeDasharray="8 10" />
    </svg>
  );
}

export default function AuthShowcase({ eyebrow, title, description, highlights }) {
  return (
    <div className="gradient-mesh court-grid relative hidden min-h-screen w-1/2 overflow-hidden text-white lg:flex">
      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(8,17,31,0.12),rgba(8,17,31,0.58))]" />
      <div className="absolute -left-16 top-16 h-56 w-56 rounded-full bg-white/10 blur-3xl" />
      <div className="absolute bottom-8 right-6 h-72 w-72 rounded-full bg-primary/20 blur-3xl" />

      <div className="relative z-10 flex w-full flex-col justify-between px-10 py-10 xl:px-12 xl:py-12">
        <div>
          <div className="mb-8 flex items-center gap-3 text-white">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/12 bg-white/8">
              <span className="material-symbols-outlined text-2xl text-primary-soft icon-filled">account_balance</span>
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-primary-soft/82">Supreme-ready</p>
              <span className="text-2xl font-semibold tracking-tight text-white">Mamla.AI</span>
            </div>
          </div>

          <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.28em] text-primary-soft/84">{eyebrow}</p>
          <h1 className="max-w-xl font-display text-[2.75rem] font-bold leading-[1.05] text-white xl:text-5xl">{title}</h1>
          <p className="mt-5 max-w-xl text-base font-medium leading-7 text-white/84 xl:text-lg xl:leading-8">{description}</p>
        </div>

        <div className="relative mt-8 h-[280px] rounded-[2rem] border border-white/10 bg-white/6 p-5 shadow-elevated backdrop-blur-sm xl:h-[320px] xl:p-6">
          <div className="absolute inset-0 rounded-[2rem] bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.14),transparent_42%)]" />
          <div className="absolute left-6 right-6 top-6 z-10 flex items-center justify-between rounded-2xl border border-white/10 bg-background-dark/72 px-4 py-3 backdrop-blur-sm">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-primary-soft/82">Chamber View</p>
              <p className="font-display text-2xl font-semibold text-white">Practice Console</p>
            </div>
            <div className="rounded-full border border-white/10 bg-white/10 px-3 py-1 text-xs font-semibold text-white/92">
              Live Workflow
            </div>
          </div>
          <div className="relative h-full pt-16">
            <ChamberShowcaseIllustration />
          </div>
        </div>

        <div className="mt-6 grid gap-3 md:grid-cols-3">
          {highlights.map((highlight) => (
            <div key={highlight.title} className="rounded-2xl border border-white/10 bg-white/7 p-4 backdrop-blur-sm">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary-soft/84">{highlight.title}</p>
              <p className="mt-2 text-sm font-medium leading-6 text-white/84">{highlight.text}</p>
            </div>
          ))}
        </div>

        <div className="mt-6 text-sm font-medium text-white/52">© 2026 Mamla.AI. Secure and encrypted for chamber operations.</div>
      </div>
    </div>
  );
}