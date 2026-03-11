import React, { useState } from 'react';
import apiClient from '../../services/api';

const COURTS = [
  'District Court', 'High Court', 'Taluka Court', 'CBI Court',
  'Consumer Forum', 'Family Court', 'Labour Court',
];

export default function CauseListBrowser() {
  const [form, setForm] = useState({
    state: '',
    district: '',
    court_name: '',
    bench: '',
    date: new Date().toISOString().slice(0, 10),
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);

  function handleChange(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  }

  async function handleSearch(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    setSearched(true);
    try {
      const params = new URLSearchParams({
        ...(form.state && { state: form.state }),
        ...(form.district && { district: form.district }),
        ...(form.court_name && { court_name: form.court_name }),
        ...(form.bench && { bench: form.bench }),
        date: form.date,
      });
      const r = await apiClient.get(`ecourts/cause-list/?${params}`);
      setResult(r.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to fetch cause list. Please try again.');
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  const items = result?.items ?? result ?? [];

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6">
        <h2 className="text-2xl font-black text-ink tracking-tight">Cause List Browser</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Browse daily cause lists for courts across India
        </p>
      </div>

      <div className="card p-6 mb-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold mb-1 text-slate-700">State</label>
              <input
                name="state"
                value={form.state}
                onChange={handleChange}
                className="input-base"
                placeholder="e.g., Maharashtra"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1 text-slate-700">District</label>
              <input
                name="district"
                value={form.district}
                onChange={handleChange}
                className="input-base"
                placeholder="e.g., Pune"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold mb-1 text-slate-700">Court</label>
              <select name="court_name" value={form.court_name} onChange={handleChange} className="input-base">
                <option value="">All Courts</option>
                {COURTS.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1 text-slate-700">Bench</label>
              <input
                name="bench"
                value={form.bench}
                onChange={handleChange}
                className="input-base"
                placeholder="e.g., Court No. 1"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold mb-1 text-slate-700">Date *</label>
            <input
              type="date"
              name="date"
              required
              value={form.date}
              onChange={handleChange}
              className="input-base w-48"
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              <span className="material-symbols-outlined text-base">error</span>
              {error}
            </div>
          )}

          <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2">
            {loading ? (
              <><span className="material-symbols-outlined animate-spin text-base">progress_activity</span> Loading…</>
            ) : (
              <><span className="material-symbols-outlined text-base">list_alt</span> Fetch Cause List</>
            )}
          </button>
        </form>
      </div>

      {/* Results */}
      {searched && !loading && (
        <div>
          {/* Header row */}
          {result?.court && (
            <div className="mb-4">
              <h3 className="font-bold text-ink">{result.court}</h3>
              <p className="text-xs text-slate-400">
                {result.date ? new Date(result.date).toLocaleDateString('en-IN', {
                  weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
                }) : form.date}
                {result.bench && ` — ${result.bench}`}
              </p>
            </div>
          )}
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-3">
            {items.length > 0 ? `${items.length} case${items.length > 1 ? 's' : ''} listed` : 'No cause list available for this selection'}
          </p>

          {items.length > 0 && (
            <div className="card overflow-hidden">
              <div className="divide-y divide-primary/5">
                {/* Header */}
                <div className="grid grid-cols-12 gap-3 px-5 py-3 bg-background-light">
                  <p className="col-span-1 text-[10px] font-bold text-slate-400 uppercase">Sl.</p>
                  <p className="col-span-4 text-[10px] font-bold text-slate-400 uppercase">Case No.</p>
                  <p className="col-span-5 text-[10px] font-bold text-slate-400 uppercase">Title</p>
                  <p className="col-span-2 text-[10px] font-bold text-slate-400 uppercase">Type</p>
                </div>

                {items.map((item, idx) => (
                  <div
                    key={item.cnr || idx}
                    className="grid grid-cols-12 gap-3 px-5 py-3 hover:bg-primary/5 transition-colors items-center"
                  >
                    <p className="col-span-1 text-xs text-slate-400">{item.serial_no || idx + 1}</p>
                    <div className="col-span-4">
                      <p className="text-xs font-semibold text-ink">
                        {item.case_type} {item.case_number}/{item.year}
                      </p>
                      {item.cnr && (
                        <p className="text-[10px] font-mono text-primary mt-0.5">
                          {item.cnr}
                        </p>
                      )}
                    </div>
                    <p className="col-span-5 text-xs text-slate-600 line-clamp-2">
                      {item.case_title || item.title || '—'}
                    </p>
                    <p className="col-span-2 text-[10px] text-slate-400">{item.purpose || '—'}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
