import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../../services/api';

const BAR_COUNCILS = [
  'Bar Council of India', 'Andhra Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Delhi',
  'Gujarat', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh',
  'Maharashtra', 'Odisha', 'Punjab & Haryana', 'Rajasthan', 'Tamil Nadu', 'Telangana',
  'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
];

export default function LawyerSearch() {
  const [form, setForm] = useState({ name: '', bar_council: '', reg_number: '' });
  const [results, setResults] = useState([]);
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
      const params = new URLSearchParams();
      if (form.name.trim()) params.append('name', form.name.trim());
      if (form.bar_council) params.append('bar_council', form.bar_council);
      if (form.reg_number.trim()) params.append('reg_number', form.reg_number.trim());

      const r = await apiClient.get(`ecourts/lawyers/search/?${params}`);
      setResults(r.data?.results ?? r.data ?? []);
    } catch (err) {
      setError(err.response?.data?.error || 'Search failed. Please check your inputs.');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6">
        <h2 className="text-2xl font-black text-ink tracking-tight">Lawyer Search</h2>
        <p className="text-sm text-slate-500 mt-0.5">Find advocate registration and case records</p>
      </div>

      <div className="card p-6 mb-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold mb-1 text-slate-700">Advocate Name</label>
            <input
              name="name"
              value={form.name}
              onChange={handleChange}
              className="input-base"
              placeholder="e.g., Ramesh Gupta"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold mb-1 text-slate-700">Bar Council</label>
              <select name="bar_council" value={form.bar_council} onChange={handleChange} className="input-base">
                <option value="">Any Bar Council</option>
                {BAR_COUNCILS.map((b) => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1 text-slate-700">Registration Number</label>
              <input
                name="reg_number"
                value={form.reg_number}
                onChange={handleChange}
                className="input-base font-mono"
                placeholder="e.g., DL/123/2010"
              />
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              <span className="material-symbols-outlined text-base">error</span>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || (!form.name.trim() && !form.bar_council && !form.reg_number.trim())}
            className="btn-primary flex items-center gap-2"
          >
            {loading ? (
              <><span className="material-symbols-outlined animate-spin text-base">progress_activity</span> Searching…</>
            ) : (
              <><span className="material-symbols-outlined text-base">person_search</span> Search Lawyers</>
            )}
          </button>
        </form>
      </div>

      {/* Results */}
      {searched && !loading && (
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-3">
            {results.length > 0 ? `${results.length} result${results.length > 1 ? 's' : ''}` : 'No results found'}
          </p>
          <div className="space-y-3">
            {results.map((lawyer) => (
              <div
                key={lawyer.id || lawyer.reg_number}
                className="card p-5 flex items-start gap-4"
              >
                <div className="size-12 rounded-full bg-primary/10 text-primary font-bold text-sm flex items-center justify-center flex-shrink-0">
                  {(lawyer.name || 'L')[0].toUpperCase()}
                </div>
                <div className="flex-1">
                  <p className="font-bold text-ink">{lawyer.name}</p>
                  {lawyer.reg_number && (
                    <p className="text-xs font-mono text-slate-400 mt-0.5">{lawyer.reg_number}</p>
                  )}
                  <div className="flex flex-wrap gap-2 mt-2">
                    {lawyer.bar_council && (
                      <span className="badge-info">{lawyer.bar_council}</span>
                    )}
                    {lawyer.enrollment_year && (
                      <span className="badge-info">Enrolled {lawyer.enrollment_year}</span>
                    )}
                    {lawyer.active_cases_count !== undefined && (
                      <span className="badge-info">{lawyer.active_cases_count} active cases</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
