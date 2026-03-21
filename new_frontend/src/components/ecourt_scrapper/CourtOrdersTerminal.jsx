import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { ensureCaseLoaded, getCaseOrders } from './api';

function summarizeOrder(order, index) {
  const date = order?.order_date || order?.date || order?.dated || 'Date unavailable';
  const title = order?.order_number || order?.order_type || order?.particulars || `Order ${index + 1}`;
  return { date, title };
}

export default function CourtOrdersTerminal() {
  const navigate = useNavigate();
  const [cnr, setCnr] = useState('');
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [statusText, setStatusText] = useState('');

  async function handleSubmit(event) {
    event.preventDefault();
    const normalized = cnr.trim().toUpperCase();
    if (!normalized) {
      setError('Enter a CNR to load court orders.');
      return;
    }

    setLoading(true);
    setError('');
    setStatusText('');

    try {
      await ensureCaseLoaded(normalized);
      const response = await getCaseOrders(normalized);
      const nextOrders = response.data?.orders || [];
      setOrders(nextOrders);
      setStatusText(
        nextOrders.length > 0
          ? `${nextOrders.length} orders are available from the cached case scrape.`
          : 'The case loaded, but no orders were parsed from the scraper result.',
      );
    } catch (requestError) {
      setOrders([]);
      setError(requestError.response?.data?.error || requestError.message || 'Unable to load court orders.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <p className="text-[11px] font-black uppercase tracking-[0.28em] text-primary">Court Orders</p>
            <h1 className="mt-3 text-3xl font-black tracking-tight text-ink">Order access from cached scraper cases</h1>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              This first scraper slice resolves court orders through a CNR lookup, loads the cached case if needed, and then exposes the parsed order rows.
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

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-3 md:flex-row">
          <input
            type="text"
            value={cnr}
            onChange={(event) => setCnr(event.target.value.toUpperCase())}
            placeholder="Enter case CNR"
            className="input-base flex-1 font-mono uppercase"
          />
          <button type="submit" className="btn-primary md:min-w-[200px]" disabled={loading}>
            {loading ? 'Loading orders...' : 'Load orders'}
          </button>
          <button
            type="button"
            onClick={() => {
              const normalized = cnr.trim().toUpperCase();
              if (normalized) navigate(`/ecourts/case/${encodeURIComponent(normalized)}`);
            }}
            className="rounded-2xl border border-primary/15 px-5 py-3 text-sm font-semibold text-slate-600 transition-colors hover:border-primary/40 hover:text-primary"
          >
            Open case detail
          </button>
        </form>

        {error ? (
          <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        ) : null}
        {statusText ? (
          <div className="mt-5 rounded-2xl border border-primary/10 bg-background-light px-4 py-3 text-sm text-slate-600">{statusText}</div>
        ) : null}
      </div>

      <div className="mt-8 grid gap-4">
        {orders.map((order, index) => {
          const summary = summarizeOrder(order, index);
          return (
            <div key={`order-${index}`} className="rounded-[24px] border border-primary/10 bg-white p-5 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-400">{summary.date}</p>
                  <h2 className="mt-2 text-lg font-black text-ink">{summary.title}</h2>
                </div>
                <span className="rounded-full border border-primary/10 bg-background-light px-3 py-1 text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">
                  Order {index + 1}
                </span>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {Object.entries(order || {}).slice(0, 8).map(([key, value]) => (
                  <div key={key} className="rounded-2xl border border-primary/10 bg-background-light px-4 py-3">
                    <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">{key.replaceAll('_', ' ')}</p>
                    <p className="mt-2 text-sm text-slate-700">{Array.isArray(value) ? value.join(', ') : String(value || '—')}</p>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
        {orders.length === 0 ? (
          <div className="rounded-[24px] border border-dashed border-primary/15 bg-background-light px-4 py-6 text-sm text-slate-500">
            Load a case by CNR to inspect its parsed order rows.
          </div>
        ) : null}
      </div>
    </div>
  );
}