import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../../services/api';

const STATES = [
  'Andhra Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Delhi',
  'Gujarat', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala',
  'Madhya Pradesh', 'Maharashtra', 'Odisha', 'Punjab & Haryana', 'Rajasthan',
  'Tamil Nadu', 'Telangana', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
];

export default function CaseSearch() {
  const [searchType, setSearchType] = useState('cnr'); // cnr | party | case_number
  const [form, setForm] = useState({
    cnr: '',
    party_name: '',
    case_number: '',
    case_type: '',
    year: new Date().getFullYear(),
    state: '',
    district: '',
  });
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
      if (searchType === 'cnr') params.append('cnr', form.cnr.trim().toUpperCase());
      if (searchType === 'party') params.append('party_name', form.party_name.trim());
      if (searchType === 'case_number') {
        params.append('case_number', form.case_number.trim());
        params.append('case_type', form.case_type.trim());
        params.append('year', form.year);
      }
      if (form.state) params.append('state', form.state);
      if (form.district) params.append('district', form.district);

      const r = await apiClient.get(`ecourts/search/cases/?${params}`);
      setResults(r.data?.results ?? r.data ?? []);
    } catch (err) {
      setError(err.response?.data?.error || 'Search failed. Please check your inputs and try again.');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6">
        <h2 className="text-2xl font-black text-ink tracking-tight">Case Search</h2>
        <p className="text-sm text-slate-500 mt-0.5">Search cases across Indian eCourts</p>
      </div>

      <div className="card p-6 mb-6">
        {/* Type toggle */}
        <div className="flex gap-1 bg-background-light rounded-lg p-1 w-fit mb-5">
          {[
            { key: 'cnr', label: 'By CNR' },
            { key: 'party', label: 'By Party Name' },
            { key: 'case_number', label: 'By Case No.' },
          ].map((t) => (
            <button
              key={t.key}
              onClick={() => { setSearchType(t.key); setResults([]); setSearched(false); }}
              className={`px-3 py-1.5 text-xs font-semibold rounded transition-all ${
                searchType === t.key
                  ? 'bg-primary text-ivory shadow-sm'
                  : 'text-slate-500 hover:text-primary'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSearch} className="space-y-4">
          {searchType === 'cnr' && (
            <div>
              <label className="block text-xs font-semibold mb-1 text-slate-700">CNR Number *</label>
              <input
                name="cnr"
                required
                value={form.cnr}
                onChange={handleChange}
                className="input-base font-mono uppercase"
                placeholder="e.g., MHAU010001232024"
                maxLength={20}
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Case Number Record — unique 16–20 character identifier
              </p>
            </div>
          )}

          {searchType === 'party' && (
            <div>
              <label className="block text-xs font-semibold mb-1 text-slate-700">Party Name *</label>
              <input
                name="party_name"
                required
                value={form.party_name}
                onChange={handleChange}
                className="input-base"
                placeholder="e.g., Ramesh Kumar"
              />
            </div>
          )}

          {searchType === 'case_number' && (
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-semibold mb-1 text-slate-700">Case Type *</label>
                <input
                  name="case_type"
                  required
                  value={form.case_type}
                  onChange={handleChange}
                  className="input-base"
                  placeholder="CS / WP / CRL"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1 text-slate-700">Case Number *</label>
                <input
                  name="case_number"
                  required
                  value={form.case_number}
                  onChange={handleChange}
                  className="input-base"
                  placeholder="e.g., 00123"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1 text-slate-700">Year</label>
                <input
                  name="year"
                  type="number"
                  value={form.year}
                  onChange={handleChange}
                  className="input-base"
                  min={2000}
                  max={new Date().getFullYear()}
                />
              </div>
            </div>
          )}

          {/* State / district filters */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold mb-1 text-slate-700">State</label>
              <select name="state" value={form.state} onChange={handleChange} className="input-base">
                <option value="">All States</option>
                {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
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
              <><span className="material-symbols-outlined text-base">search</span> Search Cases</>
            )}
          </button>
        </form>
      </div>

      {/* Results */}
      {searched && !loading && (
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-3">
            {results.length > 0 ? `${results.length} result${results.length > 1 ? 's' : ''}` : 'No results'}
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
                  <p className="font-semibold text-ink">{c.case_title || c.title || 'Case'}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {c.case_type} {c.case_number}/{c.year} — {c.court || c.court_name || '—'}
                  </p>
                  {c.next_hearing_date && (
                    <p className="text-xs text-primary font-semibold mt-1 flex items-center gap-1">
                      <span className="material-symbols-outlined text-xs">event</span>
                      Next: {new Date(c.next_hearing_date).toLocaleDateString('en-IN')}
                    </p>
                  )}
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
