import React from 'react';
import { Link } from 'react-router-dom';

const FOUNDERS = [
  {
    initials: 'RM', name: 'RM', role: 'Co-Founder & CEO', college: 'IIT Kharagpur', linkedin: '#',
    bio: "Nearly two decades at the intersection of enterprise technology and institutional infrastructure. Mamla.AI began with a single observation: India's courts generate more structured data than almost any institution in the country, yet practicing counsel operates almost entirely without access to it.",
  },
  {
    initials: 'MS', name: 'MS', role: 'Co-Founder & CTO', college: 'NIT Durgapur', linkedin: '#',
    bio: "The engineering mind behind Mamla.AI's AI core — the models that draft, the pipelines that ingest court filings, and the real-time eCourt infrastructure. Believes the most important test of any AI system is whether a senior advocate would trust it the night before a hearing.",
  },
];

function LinkedInIcon() {
  return (
    <svg className="h-5 w-5 fill-current" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" />
    </svg>
  );
}

export default function AboutSection() {
  return (
    <section id="about" className="border-t border-slate-200 bg-white py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mx-auto mb-16 max-w-3xl text-center">
          <p className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">About Mamla.AI</p>
          <h2 className="mb-5 font-display text-3xl font-bold text-ink md:text-4xl">
            About Mamla AI &ndash;{' '}
            <span className="italic text-graphite">AI Legal Software Built for Indian Lawyers</span>
          </h2>
          <p className="text-sm leading-8 text-graphite">
            Mamla AI is an AI-powered legal software platform helping lawyers, law firms, litigants and law students streamline drafting, legal research, case management and court tracking. We combine deep understanding of Indian law with cutting-edge AI to give every advocate and law firm the tools they deserve.
          </p>
        </div>

        {/* Mission block */}
        <div className="mx-auto mb-20 flex max-w-4xl flex-col items-center gap-10 rounded-[28px] bg-background-dark p-8 text-white shadow-elevated md:flex-row md:p-12">
          <div className="flex-shrink-0">
            <div className="flex h-32 w-32 items-center justify-center rounded-full border-2 border-primary-soft/40 p-6">
              <span className="material-symbols-outlined text-5xl text-primary-soft">gavel</span>
            </div>
          </div>
          <div className="flex-1 text-center md:text-left">
            <h3 className="mb-5 font-display text-2xl font-bold text-primary-soft md:text-3xl">Our Mission</h3>
            <p className="mb-8 text-base leading-relaxed text-white/80">
              To bridge the gap between legal professionals and the common citizen. We leverage cutting-edge AI to
              simplify complex legal processes — drafting, research, case tracking and client management — making
              legal work faster, more affordable and more reliable across India.
            </p>
            <Link
              to="/features"
              className="inline-block rounded-xl bg-primary-soft px-8 py-3 font-bold text-primary-dark transition-transform hover:scale-105"
            >
              Explore What We Build
            </Link>
          </div>
        </div>

        {/* Team grid */}
        <h3 className="mb-12 text-center font-display text-3xl font-bold text-ink">The Team</h3>
        <div className="mx-auto grid max-w-4xl gap-10 sm:grid-cols-2">
          {FOUNDERS.map((m) => (
            <div key={m.initials} className="flex flex-col items-center rounded-[24px] border border-slate-200 bg-background-light p-8 text-center shadow-card transition-all hover:-translate-y-1 hover:shadow-elevated">
              <div className="mb-6 flex h-32 w-32 items-center justify-center rounded-full border-4 border-primary bg-background-dark font-display text-4xl font-bold text-primary-soft shadow-lg">
                {m.initials}
              </div>
              <h4 className="text-xl font-bold text-ink">{m.name}</h4>
              <p className="mb-3 font-medium text-primary">{m.role}</p>
              <span className="mb-4 inline-block rounded-lg bg-primary/10 px-3 py-1 text-[11px] font-bold text-primary">
                🎓 {m.college}
              </span>
              <p className="mb-5 text-[13px] leading-7 text-graphite">{m.bio}</p>
              <a href={m.linkedin} className="text-primary transition-colors hover:text-primary-dark" aria-label={`${m.name} on LinkedIn`}>
                <LinkedInIcon />
              </a>
            </div>
          ))}
        </div>

        {/* Company strip */}
        <div className="mt-16 flex flex-wrap items-center justify-between gap-6 rounded-[20px] bg-background-dark px-8 py-7">
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
