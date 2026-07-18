import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getCATHealth } from './apiCAT';

const CAT_MODULES = [
  {
    key: 'case-status',
    title: 'Case Status',
    description: 'Search by case number, diary number, party name, or advocate name across any of the 19 CAT benches.',
    href: '/ecourts/cat/case-status',
  },
  {
    key: 'cause-list',
    title: 'Cause List',
    description: 'Browse the cause list for any bench on a specific date.',
    href: '/ecourts/cat/cause-list',
  },
  {
    key: 'orders',
    title: 'Orders',
    description: 'Retrieve daily orders by date, or final/oral orders for a specific case.',
    href: '/ecourts/cat/orders',
  },
  {
    key: 'judgments',
    title: 'Judgments',
    description: 'Full-text keyword search across CAT judgments, by bench or across all benches.',
    href: '/ecourts/cat/judgments',
  },
];

export default function CATTerminal() {
  const navigate = useNavigate();
  const [serviceOk, setServiceOk] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getCATHealth()
      .then((res) => { if (active) setServiceOk(res.data?.status === 'ok'); })
      .catch(() => { if (active) setServiceOk(false); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return (
    <div className="p-8 max-w-6xl">
      {/* ── Top bar: District / High / Supreme / CAT toggle ── */}
      <div className="mb-6 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => navigate('/ecourts')}
          className="rounded-2xl border border-primary/15 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:border-primary/40 hover:text-primary"
        >
          ← District Court
        </button>
        <button
          type="button"
          onClick={() => navigate('/ecourts/hc')}
          className="rounded-2xl border border-primary/15 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:border-primary/40 hover:text-primary"
        >
          ← High Court
        </button>
        <button
          type="button"
          onClick={() => navigate('/ecourts/sci')}
          className="rounded-2xl border border-primary/15 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:border-primary/40 hover:text-primary"
        >
          ← Supreme Court
        </button>
        <span className="rounded-2xl bg-primary px-4 py-2 text-sm font-bold text-white">
          Central Administrative Tribunal
        </span>
      </div>

      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <p className="text-[11px] font-black uppercase tracking-[0.28em] text-primary">Central Administrative Tribunal Case Search</p>
            <h1 className="mt-3 text-3xl font-black tracking-tight text-ink">Live access to CAT records across all 19 benches</h1>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              Search case status, cause lists, orders, and judgments across every Central Administrative
              Tribunal bench in India — powered by cis.cgat.gov.in.
            </p>
          </div>

          <div className="grid min-w-[200px] gap-3 sm:grid-cols-2 lg:w-[280px]">
            <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-4">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Benches</p>
              <p className="mt-2 text-2xl font-black text-ink">19</p>
            </div>
            <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-4">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Service</p>
              <p className="mt-2 text-2xl font-black text-ink">
                {loading ? '…' : serviceOk ? '✓' : '—'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Module cards */}
      <div className="mt-8 grid gap-4 lg:grid-cols-2">
        {CAT_MODULES.map((module) => (
          <div key={module.key} className="rounded-[24px] border border-primary/10 bg-white p-6 shadow-sm">
            <p className="text-lg font-black text-ink">{module.title}</p>
            <p className="mt-2 text-sm leading-6 text-slate-600">{module.description}</p>
            <button
              type="button"
              onClick={() => navigate(module.href)}
              className="mt-5 rounded-2xl border border-primary/15 px-4 py-3 text-sm font-semibold text-slate-600 transition-colors hover:border-primary/40 hover:text-primary"
            >
              Open {module.title}
            </button>
          </div>
        ))}
      </div>

      <div className="mt-8 rounded-[24px] border border-primary/10 bg-background-light p-6">
        <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">Note</p>
        <ul className="mt-3 space-y-2 text-sm leading-7 text-slate-600">
          <li>No CAPTCHA — CAT's public pages are open access, so searches are typically faster than DC/HC/SCI.</li>
          <li>Every search requires picking a bench first — CAT has no cross-bench case status search.</li>
        </ul>
        {serviceOk === false && (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
            CAT fetch service is currently unreachable. Ensure the backend scraper is running on the correct port.
          </div>
        )}
      </div>
    </div>
  );
}
