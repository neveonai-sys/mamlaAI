import React, { useEffect, useState, useCallback } from 'react';
import { useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../services/api';

const DAYS_OPTIONS = [7, 14, 30, 60, 90];

function StatCard({ label, value, sub, icon, accent }) {
  return (
    <div className="metric-card">
      <div className="flex items-start justify-between mb-2">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{label}</p>
        <span className={`material-symbols-outlined text-lg ${accent || 'text-primary'}`}>{icon}</span>
      </div>
      <span className="text-3xl font-bold text-ink leading-none">{value ?? '—'}</span>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  );
}

function FeatureRow({ feature, requests, unique_users, cost, maxRequests }) {
  const pct = maxRequests > 0 ? Math.round((requests / maxRequests) * 100) : 0;
  return (
    <tr className="border-b border-slate-100 hover:bg-ivory/60">
      <td className="py-3 pr-4 text-sm font-medium text-ink">{feature || '—'}</td>
      <td className="py-3 pr-4 text-sm text-slate-600">
        <div className="flex items-center gap-2">
          <div className="flex-1 bg-slate-100 rounded-full h-1.5 min-w-[80px]">
            <div className="bg-primary h-1.5 rounded-full" style={{ width: `${pct}%` }} />
          </div>
          <span className="text-xs font-semibold text-ink w-10 text-right">{requests}</span>
        </div>
      </td>
      <td className="py-3 pr-4 text-sm text-slate-600 text-right">{unique_users}</td>
      <td className="py-3 text-sm text-slate-600 text-right">{cost?.toFixed(6)}</td>
    </tr>
  );
}

function DailyChart({ data }) {
  if (!data?.length) return null;
  const maxCost = Math.max(...data.map((d) => d.cost), 0.000001);
  return (
    <div className="flex items-end gap-1 h-24 w-full overflow-x-auto">
      {data.map((d) => {
        const h = Math.max(Math.round((d.cost / maxCost) * 100), 2);
        return (
          <div
            key={d.date}
            className="flex flex-col items-center flex-1 min-w-[18px] group cursor-default"
            title={`${d.date}\nRequests: ${d.requests}\nCost: ${d.cost?.toFixed(6)}\nUsers: ${d.active_users}`}
          >
            <div
              className="w-full rounded-t bg-primary/60 group-hover:bg-primary transition-colors"
              style={{ height: `${h}%` }}
            />
            <span className="text-[9px] text-slate-400 mt-1 rotate-45 origin-top-left hidden group-hover:block">
              {d.date?.slice(5)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

const ALLOWED_TYPES = new Set(['owner', 'admin', 'Owner', 'Admin']);
const ADMIN_EMAILS = (process.env.REACT_APP_ADMIN_EMAILS || '')
  .split(',').map((e) => e.trim()).filter(Boolean);

export default function OwnerDashboard() {
  const navigate = useNavigate();
  const { user_type, email } = useSelector((s) => s.user);
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchData = useCallback(async (d) => {
    setLoading(true);
    setError('');
    try {
      const res = await apiClient.get(`analytics/owner/dashboard/?days=${d}`);
      setData(res.data);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to load analytics.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!ALLOWED_TYPES.has(user_type) && !ADMIN_EMAILS.includes(email)) {
      navigate('/not-authorized', { replace: true });
      return;
    }
    fetchData(days);
  }, [days, fetchData, navigate, user_type]);

  const maxRequests = data?.feature_adoption?.length
    ? Math.max(...data.feature_adoption.map((f) => f.requests))
    : 1;

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">Owner Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">Product usage, token spend &amp; feature adoption</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 font-medium">Last</span>
          {DAYS_OPTIONS.map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`text-xs px-3 py-1.5 rounded-lg font-semibold transition-colors ${
                days === d
                  ? 'bg-primary text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-primary/10 hover:text-primary'
              }`}
            >
              {d}d
            </button>
          ))}
          <button
            onClick={() => fetchData(days)}
            className="ml-2 p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 transition-colors"
            title="Refresh"
          >
            <span className="material-symbols-outlined text-lg">refresh</span>
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">{error}</div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="metric-card animate-pulse">
              <div className="h-3 bg-slate-200 rounded w-2/3 mb-3" />
              <div className="h-8 bg-slate-200 rounded w-1/2" />
            </div>
          ))}
        </div>
      )}

      {data && !loading && (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="DAU" value={data.dau} sub="Active users (24 h)" icon="person" />
            <StatCard label="MAU" value={data.mau} sub="Active users (30 d)" icon="group" />
            <StatCard label="Total Requests" value={data.total_requests?.toLocaleString()} sub={`Last ${data.period_days} days`} icon="bolt" />
            <StatCard
              label="Provider Cost"
              value={`$${data.total_provider_cost?.toFixed(4)}`}
              sub={`${(data.total_tokens ?? 0).toLocaleString()} tokens`}
              icon="payments"
              accent="text-amber-500"
            />
          </div>

          {/* Daily cost chart */}
          {data.daily_breakdown?.length > 0 && (
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
              <h2 className="text-sm font-bold text-ink mb-4">Daily Provider Cost</h2>
              <DailyChart data={data.daily_breakdown} />
              <div className="flex justify-between mt-2 text-[10px] text-slate-400">
                <span>{data.daily_breakdown[0]?.date}</span>
                <span>{data.daily_breakdown[data.daily_breakdown.length - 1]?.date}</span>
              </div>
            </div>
          )}

          {/* Feature adoption table */}
          {data.feature_adoption?.length > 0 && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100">
                <h2 className="text-sm font-bold text-ink">Feature Adoption</h2>
                <p className="text-xs text-slate-500 mt-0.5">Sorted by request volume</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50/60">
                      <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">Feature</th>
                      <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3">Requests</th>
                      <th className="text-right text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3">Unique Users</th>
                      <th className="text-right text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">Cost (USD)</th>
                    </tr>
                  </thead>
                  <tbody className="px-5">
                    {data.feature_adoption.map((f) => (
                      <tr key={f.feature} className="border-b border-slate-100 hover:bg-ivory/60">
                        <td className="py-3 px-5 text-sm font-medium text-ink">{f.feature || '—'}</td>
                        <td className="py-3 px-4 text-sm text-slate-600">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 bg-slate-100 rounded-full h-1.5 min-w-[80px]">
                              <div
                                className="bg-primary h-1.5 rounded-full"
                                style={{ width: `${Math.round((f.requests / maxRequests) * 100)}%` }}
                              />
                            </div>
                            <span className="text-xs font-semibold text-ink w-10 text-right">{f.requests}</span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-sm text-slate-600 text-right">{f.unique_users}</td>
                        <td className="py-3 px-5 text-sm text-slate-600 text-right font-mono">{f.cost?.toFixed(6)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Daily breakdown table */}
          {data.daily_breakdown?.length > 0 && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100">
                <h2 className="text-sm font-bold text-ink">Daily Breakdown</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50/60">
                      <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">Date</th>
                      <th className="text-right text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3">Requests</th>
                      <th className="text-right text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3">Tokens</th>
                      <th className="text-right text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3">Active Users</th>
                      <th className="text-right text-xs font-semibold text-slate-500 uppercase tracking-wider px-5 py-3">Cost (USD)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...data.daily_breakdown].reverse().map((d) => (
                      <tr key={d.date} className="border-b border-slate-100 hover:bg-ivory/60">
                        <td className="py-2.5 px-5 text-sm font-medium text-ink">{d.date}</td>
                        <td className="py-2.5 px-4 text-sm text-slate-600 text-right">{d.requests}</td>
                        <td className="py-2.5 px-4 text-sm text-slate-600 text-right">{d.tokens?.toLocaleString()}</td>
                        <td className="py-2.5 px-4 text-sm text-slate-600 text-right">{d.active_users}</td>
                        <td className="py-2.5 px-5 text-sm text-slate-600 text-right font-mono">{d.cost?.toFixed(6)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {!data.total_requests && (
            <div className="text-center py-16 text-slate-400">
              <span className="material-symbols-outlined text-5xl mb-3 block">bar_chart</span>
              <p className="text-sm font-medium">No usage data in this period yet.</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
