import React from 'react';

export default function SecuritySection() {
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
