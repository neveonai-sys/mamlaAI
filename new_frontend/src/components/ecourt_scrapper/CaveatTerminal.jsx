import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const CAVEAT_MODES = [
  { id: 'petitioner', label: 'Caveat by Petitioner' },
  { id: 'case_number', label: 'Caveat by Case Number' },
  { id: 'advocate', label: 'Caveat by Advocate' },
];

export default function CaveatTerminal() {
  const navigate = useNavigate();

  return (
    <div className="p-8 max-w-5xl">
      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <p className="text-[11px] font-black uppercase tracking-[0.28em] text-primary">Caveat</p>
            <h1 className="mt-3 text-3xl font-black tracking-tight text-ink">Caveat terminal is mapped, not yet scraped</h1>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              The stitched caveat modes are now part of the active terminal flow and their static reference payload is stored in Mongo. The scraper selectors and request handlers for caveat search are the next backend expansion item.
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/ecourts')}
            className="rounded-full border border-primary/15 px-4 py-2 text-xs font-black uppercase tracking-[0.18em] text-slate-500 transition-colors hover:border-primary/40 hover:text-primary"
          >
            Back to terminal
          </button>
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-2">
          {CAVEAT_MODES.map((mode) => (
            <div key={mode.id} className="rounded-[24px] border border-primary/10 bg-background-light p-5">
              <p className="text-lg font-black text-ink">{mode.label}</p>
              <p className="mt-2 text-sm text-slate-500">Mode: {mode.id}</p>
            </div>
          ))}
        </div>

        <div className="mt-8 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-800">
          This surface is intentionally explicit about current backend status. It avoids routing users through the retired partner API while the scraper-side caveat implementation is still pending.
        </div>
      </div>
    </div>
  );
}