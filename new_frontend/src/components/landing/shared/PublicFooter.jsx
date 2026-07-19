import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import MamlaLogoIcon from '../../common/MamlaLogoIcon';
import LegalModal from './LegalModal';

// Shared site footer. Product/Solutions/Company links route to the dedicated
// hub pages; legal documents open in a modal (state kept local so every page
// that renders the footer gets working legal links).
export default function PublicFooter() {
  const [openModal, setOpenModal] = useState(null);

  const productLinks = [
    { label: 'AI Case Tracking',    to: '/case-tracking' },
    { label: 'Calendar Management', to: '/features' },
    { label: 'AI Drafting',         to: '/features' },
    { label: 'Doc Analysis',        to: '/features' },
    { label: 'Case Strategiser',    to: '/features' },
    { label: 'Client Management',   to: '/features' },
    { label: 'Citation Search',     to: '/features' },
  ];
  const solutionLinks = [
    { label: 'For Lawyers',      to: '/solutions' },
    { label: 'For Law Students', to: '/solutions' },
    { label: 'For Litigants',    to: '/solutions' },
    { label: 'For Law Firms',    to: '/solutions' },
  ];
  const companyLinks = [
    { label: 'About',    to: '/about' },
    { label: 'Pricing',  to: '/pricing' },
    { label: 'FAQ',      to: '/about#faq' },
    { label: 'Security', to: '/features#security' },
    { label: 'Contact',  to: '/about#contact' },
    { label: 'neveon.ai@gmail.com', href: 'mailto:neveon.ai@gmail.com' },
  ];

  return (
    <footer className="border-t bg-background-dark text-white" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
      <div className="mx-auto max-w-7xl px-6 py-16">
        <div className="grid gap-12 md:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr_1fr]">

          {/* Brand */}
          <div>
            <Link to="/" className="mb-4 flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/6">
                <MamlaLogoIcon dark size={30} />
              </div>
              <span className="font-display text-lg font-semibold text-white">Mamla.AI</span>
            </Link>
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
            <div className="mt-5 flex items-center gap-3">
              <a
                href="https://www.linkedin.com/company/mamla-ai"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Mamla.AI on LinkedIn"
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 text-slate-400 transition-colors hover:border-primary-soft/40 hover:text-white"
                style={{ background: 'rgba(255,255,255,0.05)' }}
              >
                <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className="h-4 w-4">
                  <path d="M20.45 20.45h-3.56v-5.57c0-1.33-.03-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.34V9h3.42v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.07 2.07 0 110-4.14 2.07 2.07 0 010 4.14zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.72v20.56C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.72V1.72C24 .77 23.2 0 22.22 0z" />
                </svg>
              </a>
              <span className="text-[11px] text-slate-500">Follow us on LinkedIn</span>
            </div>
            <p className="mt-4 text-[11px] text-slate-500">A product of Neveon AI Technologies Pvt. Ltd.</p>
          </div>

          {/* Product */}
          <div>
            <p className="mb-4 text-[11px] font-black uppercase tracking-[0.16em] text-slate-400">Product</p>
            <ul className="flex flex-col gap-2.5">
              {productLinks.map((item) => (
                <li key={item.label}>
                  <Link to={item.to} className="text-xs text-white/50 transition-colors hover:text-white">{item.label}</Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Solutions */}
          <div>
            <p className="mb-4 text-[11px] font-black uppercase tracking-[0.16em] text-slate-400">Solutions</p>
            <ul className="flex flex-col gap-2.5">
              {solutionLinks.map((item) => (
                <li key={item.label}>
                  <Link to={item.to} className="text-xs text-white/50 transition-colors hover:text-white">{item.label}</Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Company */}
          <div>
            <p className="mb-4 text-[11px] font-black uppercase tracking-[0.16em] text-slate-400">Company</p>
            <ul className="flex flex-col gap-2.5">
              {companyLinks.map((item) => (
                <li key={item.label}>
                  {item.href ? (
                    <a href={item.href} className="text-xs text-white/50 transition-colors hover:text-white">{item.label}</a>
                  ) : (
                    <Link to={item.to} className="text-xs text-white/50 transition-colors hover:text-white">{item.label}</Link>
                  )}
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

      {openModal && <LegalModal docKey={openModal} onClose={() => setOpenModal(null)} />}
    </footer>
  );
}
