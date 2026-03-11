import React from 'react';
import { Link } from 'react-router-dom';

const ECOURTS_TOOLS = [
  {
    title: 'Case Search',
    desc: 'Search cases by CNR number, party name, or advocate name across Indian courts.',
    icon: 'manage_search',
    to: '/ecourts/case-search',
    color: 'bg-blue-50 text-blue-600',
  },
  {
    title: 'Lawyer Search',
    desc: 'Find advocate information, bar registration, and cases associated with a lawyer.',
    icon: 'person_search',
    to: '/ecourts/lawyers',
    color: 'bg-primary/10 text-primary',
  },
  {
    title: 'Litigant Search',
    desc: 'Look up cases filed by or against specific individuals or organizations.',
    icon: 'groups',
    to: '/ecourts/litigants',
    color: 'bg-emerald-50 text-emerald-600',
  },
  {
    title: 'Cause List',
    desc: 'Browse daily cause lists for your court and bench combination.',
    icon: 'list_alt',
    to: '/ecourts/cause-list',
    color: 'bg-violet-50 text-violet-600',
  },
];

export default function EcourtsHome() {
  return (
    <div className="p-8 max-w-5xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-3">
          <div className="size-12 bg-primary/10 rounded-xl flex items-center justify-center">
            <span className="material-symbols-outlined text-primary text-2xl">balance</span>
          </div>
          <div>
            <h2 className="text-2xl font-black text-ink tracking-tight">eCourts India</h2>
            <p className="text-sm text-slate-500">Real-time access to Indian court case data</p>
          </div>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-start gap-3 mt-4">
          <span className="material-symbols-outlined text-amber-600 text-lg mt-0.5 flex-shrink-0">info</span>
          <p className="text-sm text-amber-700">
            Data is sourced from the eCourts partner API. Information is subject to the availability
            and accuracy of the official eCourts portal.
          </p>
        </div>
      </div>

      {/* Tool cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        {ECOURTS_TOOLS.map((tool) => (
          <Link
            key={tool.to}
            to={tool.to}
            className="card p-6 hover:shadow-md hover:border-primary/30 transition-all group flex gap-5 items-start"
          >
            <div className={`size-12 ${tool.color} rounded-xl flex items-center justify-center flex-shrink-0`}>
              <span className="material-symbols-outlined text-2xl">{tool.icon}</span>
            </div>
            <div>
              <h3 className="font-bold text-ink group-hover:text-primary transition-colors">
                {tool.title}
              </h3>
              <p className="text-sm text-slate-500 mt-1 leading-relaxed">{tool.desc}</p>
              <div className="mt-3 flex items-center gap-1 text-primary text-xs font-semibold">
                Open
                <span className="material-symbols-outlined text-sm group-hover:translate-x-1 transition-transform">
                  arrow_forward
                </span>
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Quick CNR lookup shortcut */}
      <div className="mt-8 card p-5">
        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Quick CNR Lookup</p>
        <div className="flex gap-3">
          <input
            id="cnr-quick"
            type="text"
            maxLength={20}
            placeholder="Enter CNR number (e.g., MHAU010001232024)"
            className="input-base flex-1 font-mono uppercase"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && e.target.value.trim()) {
                window.location.href = `/ecourts/case/${encodeURIComponent(e.target.value.trim().toUpperCase())}`;
              }
            }}
          />
          <button
            className="btn-primary flex items-center gap-2"
            onClick={() => {
              const val = document.getElementById('cnr-quick')?.value?.trim().toUpperCase();
              if (val) window.location.href = `/ecourts/case/${encodeURIComponent(val)}`;
            }}
          >
            <span className="material-symbols-outlined text-base">search</span>
            Search
          </button>
        </div>
      </div>
    </div>
  );
}
