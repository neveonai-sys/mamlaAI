/**
 * HCCourtSelector — 2-level High Court + Bench dropdown.
 * Replaces LocationCascade for HC context.
 *
 * Props:
 *   onChange({ hc, bench, hcLabel, benchLabel, isComplete })
 *   initialValues: { hc, bench }
 *   disabled: bool
 *   className: string
 */
import React, { useEffect, useRef, useState } from 'react';
import { getHCCourts } from './apiHC';

export default function HCCourtSelector({ onChange, initialValues, disabled = false, className = '' }) {
  const initRef = useRef(initialValues);

  const [courts, setCourts] = useState({});    // { hc_slug: { name, benches: {...} } }
  const [hcKey, setHcKey] = useState('');
  const [benchKey, setBenchKey] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Load HC list on mount
  useEffect(() => {
    let active = true;
    setLoading(true);
    getHCCourts()
      .then((res) => {
        if (!active) return;
        setCourts(res.data || {});
        // Restore initialValues after data loads
        if (initRef.current?.hc) setHcKey(initRef.current.hc);
      })
      .catch((err) => {
        if (!active) return;
        setError(err.response?.data?.error || 'Unable to load High Courts.');
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  // Restore bench after courts load + hcKey is set
  useEffect(() => {
    if (initRef.current?.bench && hcKey && courts[hcKey] && !benchKey) {
      setBenchKey(initRef.current.bench);
    }
  }, [hcKey, courts]); // eslint-disable-line react-hooks/exhaustive-deps

  // Notify parent on every valid change
  useEffect(() => {
    const hcMeta = courts[hcKey];
    const benchLabel = hcMeta?.benches?.[benchKey] || '';
    onChange({
      hc: hcKey,
      bench: benchKey,
      hcLabel: hcMeta?.name || '',
      benchLabel,
      isComplete: Boolean(hcKey && benchKey),
    });
  }, [hcKey, benchKey]); // eslint-disable-line react-hooks/exhaustive-deps

  const hcOptions = Object.entries(courts).sort((a, b) => a[1].name.localeCompare(b[1].name));
  const benchOptions = hcKey && courts[hcKey]
    ? Object.entries(courts[hcKey].benches).sort((a, b) => a[1].localeCompare(b[1]))
    : [];

  function handleHcChange(e) {
    setHcKey(e.target.value);
    setBenchKey('');
  }

  return (
    <div className={`flex flex-col gap-3 sm:flex-row ${className}`}>
      {error && (
        <p className="w-full text-xs text-red-600">{error}</p>
      )}

      <div className="flex-1">
        <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">
          High Court
        </label>
        <select
          value={hcKey}
          onChange={handleHcChange}
          disabled={disabled || loading}
          className="input-base w-full"
        >
          <option value="">{loading ? 'Loading…' : 'Select High Court'}</option>
          {hcOptions.map(([slug, meta]) => (
            <option key={slug} value={slug}>{meta.name}</option>
          ))}
        </select>
      </div>

      <div className="flex-1">
        <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">
          Bench
        </label>
        <select
          value={benchKey}
          onChange={(e) => setBenchKey(e.target.value)}
          disabled={disabled || !hcKey}
          className="input-base w-full"
        >
          <option value="">{!hcKey ? 'Select HC first' : 'Select Bench'}</option>
          {benchOptions.map(([slug, label]) => (
            <option key={slug} value={slug}>{label}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
