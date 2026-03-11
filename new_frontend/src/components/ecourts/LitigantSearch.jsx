import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../../services/api';

export default function LitigantSearch() {
  const [form, setForm] = useState({ name: '', state: '', district: '', act: '' });
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);

  function handleChange(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  }

  async function handleSearch(e) {
    e.preventDefault();
    if (!form.name.trim()) {
      setError('Please enter a party / litigant name.');
      return;
    }
    setError('');
    setLoading(true);
    setSearched(true);
    try {
      const params = new URLSearchParams({
        party_name: form.name.trim(),
        ...(form.state && { state: form.state }),
        ...(form.district && { district: form.district }),
        ...(form.act && { act: form.act }),
      });
      const r = await apiClient.get(`ecourts/litigants/search/?${params}`);
      setResults(r.data?.results ?? r.data ?? []);
    } catch (err) {
      setError(err.response?.data?.error || 'Search failed. Please try again.');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6">
        <h2 className="text-2xl font-black text-ink tracking-tight">Litigant Search</h2>
        <p className="text-sm text-slate-500 mt-0.5">Search cases by party or litigant name</p>
      </div>

      <div className="card p-6 mb-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold mb-1 text-slate-700">
              Party / Litigant Name *
            </label>
            <input
              name="name"
              required
              value={form.name}
              onChange={handleChange}
              className="input-base"
              placeholder="e.g., Suresh Kumar or ABC Pvt. Ltd."
            />
          </div>
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
                placeholder="Optional"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold mb-1 text-slate-700">Act / Section (optional)</label>
            <input
              name="act"
              value={form.act}
              onChange={handleChange}
              className="input-base"
              placeholder="e.g., IPC Section 420"
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
              <><span className="material-symbols-outlined animate-spin text-base">progress_activity</span> Searching…</>
            ) : (
              <><span className="material-symbols-outlined text-base">groups</span> Search Litigants</>
            )}
          </button>
        </form>
      </div>

      {/* Results */}
      {searched && !loading && (
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-3">
            {results.length > 0 ? `${results.length} case${results.length > 1 ? 's' : ''} found` : 'No results'}
          </p>
          <div className="space-y-3">
            {results.map((c) => (
              <Link
                key={c.cnr || c.id}
                to={`/ecourts/case/${encodeURIComponent(c.cnr)}`}
                className="card p-5 hover:border-primary/30 hover:shadow-md transition-all flex items-center justify-between group"
              >
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                      c.status === 'Disposed'
                        ? 'bg-slate-100 text-slate-500'
                        : 'bg-emerald-100 text-emerald-600'
                    }`}>
                      {c.status ?? 'Active'}
                    </span>
                    <span className="text-xs font-mono text-slate-400">{c.cnr}</span>
                  </div>
                  <p className="font-semibold text-ink">{c.case_title || c.title}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {c.case_type} {c.case_number}/{c.year} — {c.court || '—'}
                  </p>
                </div>
                <span className="material-symbols-outlined text-slate-300 group-hover:text-primary transition-colors">
                  chevron_right
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
