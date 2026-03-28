/**
 * Reusable location cascade selector for the v2 eCourts API.
 *
 * Provides: state → district → complex → establishment dropdowns.
 * The parent component receives the selected location context via onChange.
 */
import React, { useEffect, useRef, useState } from 'react';
import {
  getStates,
  getDistricts,
  getComplexes,
  getEstablishments,
} from './apiV2';

export default function LocationCascade({ onChange, error: externalError, className = '', initialValues, hideEstablishment = false }) {
  // Stable ref so cascade-restore effects don't re-run when parent re-renders
  const initRef = useRef(initialValues);
  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [complexes, setComplexes] = useState([]);
  const [establishments, setEstablishments] = useState([]);

  const [stateCode, setStateCode] = useState('');
  const [distCode, setDistCode] = useState('');
  const [complexCode, setComplexCode] = useState('');
  const [estCode, setEstCode] = useState('');

  const [loadingField, setLoadingField] = useState('');
  const [error, setError] = useState('');

  // Restore initial stateCode from saved session (once on mount, before states load)
  useEffect(() => {
    if (initRef.current?.state_code) setStateCode(initRef.current.state_code);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // After districts load, restore saved distCode (if user hasn't picked one yet)
  useEffect(() => {
    if (initRef.current?.dist_code && districts.length > 0 && !distCode) {
      setDistCode(initRef.current.dist_code);
    }
  }, [districts]); // eslint-disable-line react-hooks/exhaustive-deps

  // After complexes load, restore saved complexCode
  useEffect(() => {
    if (initRef.current?.court_complex_code && complexes.length > 0 && !complexCode) {
      setComplexCode(initRef.current.court_complex_code);
    }
  }, [complexes]); // eslint-disable-line react-hooks/exhaustive-deps

  // After establishments load, restore saved estCode
  useEffect(() => {
    if (initRef.current?.est_code && establishments.length > 0 && !estCode) {
      setEstCode(initRef.current.est_code);
    }
  }, [establishments]); // eslint-disable-line react-hooks/exhaustive-deps

  // Load states on mount
  useEffect(() => {
    let active = true;
    setLoadingField('states');
    getStates()
      .then((res) => {
        if (!active) return;
        setStates(res.data || []);
      })
      .catch((err) => {
        if (!active) return;
        setError(err.response?.data?.error || 'Unable to load states.');
      })
      .finally(() => {
        if (active) setLoadingField('');
      });
    return () => { active = false; };
  }, []);

  // Load districts when state changes
  useEffect(() => {
    setDistricts([]);
    setDistCode('');
    setComplexes([]);
    setComplexCode('');
    setEstablishments([]);
    setEstCode('');
    if (!stateCode) return;

    let active = true;
    setLoadingField('districts');
    getDistricts(stateCode)
      .then((res) => {
        if (!active) return;
        setDistricts(res.data || []);
      })
      .catch((err) => {
        if (!active) return;
        setError(err.response?.data?.error || 'Unable to load districts.');
      })
      .finally(() => {
        if (active) setLoadingField('');
      });
    return () => { active = false; };
  }, [stateCode]);

  // Load complexes when district changes
  useEffect(() => {
    setComplexes([]);
    setComplexCode('');
    setEstablishments([]);
    setEstCode('');
    if (!stateCode || !distCode) return;

    let active = true;
    setLoadingField('complexes');
    getComplexes(stateCode, distCode)
      .then((res) => {
        if (!active) return;
        setComplexes(res.data || []);
      })
      .catch((err) => {
        if (!active) return;
        setError(err.response?.data?.error || 'Unable to load complexes.');
      })
      .finally(() => {
        if (active) setLoadingField('');
      });
    return () => { active = false; };
  }, [stateCode, distCode]);

  // Load establishments when complex changes
  useEffect(() => {
    setEstablishments([]);
    setEstCode('');
    if (hideEstablishment) return;         // no establishment needed for this mode
    if (!stateCode || !distCode || !complexCode) return;

    let active = true;
    setLoadingField('establishments');
    getEstablishments(stateCode, distCode, complexCode)
      .then((res) => {
        if (!active) return;
        setEstablishments(res.data || []);
      })
      .catch((err) => {
        if (!active) return;
        setError(err.response?.data?.error || 'Unable to load establishments.');
      })
      .finally(() => {
        if (active) setLoadingField('');
      });
    return () => { active = false; };
  }, [stateCode, distCode, complexCode]);

  // Notify parent of location context changes
  useEffect(() => {
    if (onChange) {
      const isComplexComplete = !!(stateCode && distCode && complexCode);
      onChange({
        state_code: stateCode,
        dist_code: distCode,
        court_complex_code: complexCode,
        est_code: estCode,
        isComplete: hideEstablishment ? isComplexComplete : !!(stateCode && distCode && complexCode && estCode),
        isComplexComplete,
      });
    }
  }, [stateCode, distCode, complexCode, estCode, hideEstablishment]);

  const displayError = externalError || error;

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        {/* State */}
        <div>
          <label className="mb-1.5 block text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
            State {loadingField === 'states' && <span className="text-primary">loading…</span>}
          </label>
          <select
            value={stateCode}
            onChange={(e) => setStateCode(e.target.value)}
            className="input-base w-full"
          >
            <option value="">Select state</option>
            {states.map((s) => (
              <option key={s.code} value={s.code}>{s.name}</option>
            ))}
          </select>
        </div>

        {/* District */}
        <div>
          <label className="mb-1.5 block text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
            District {loadingField === 'districts' && <span className="text-primary">loading…</span>}
          </label>
          <select
            value={distCode}
            onChange={(e) => setDistCode(e.target.value)}
            className="input-base w-full"
            disabled={!stateCode}
          >
            <option value="">Select district</option>
            {districts.map((d) => (
              <option key={d.code} value={d.code}>{d.name}</option>
            ))}
          </select>
        </div>

        {/* Complex */}
        <div>
          <label className="mb-1.5 block text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
            Court Complex {loadingField === 'complexes' && <span className="text-primary">loading…</span>}
          </label>
          <select
            value={complexCode}
            onChange={(e) => setComplexCode(e.target.value)}
            className="input-base w-full"
            disabled={!distCode}
          >
            <option value="">Select complex</option>
            {complexes.map((c) => (
              <option key={c.code} value={c.code}>{c.name}</option>
            ))}
          </select>
        </div>

        {/* Establishment — hidden when parent mode doesn't need it */}
        {!hideEstablishment && (
        <div>
          <label className="mb-1.5 block text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
            Establishment {loadingField === 'establishments' && <span className="text-primary">loading…</span>}
          </label>
          <select
            value={estCode}
            onChange={(e) => setEstCode(e.target.value)}
            className="input-base w-full"
            disabled={!complexCode}
          >
            <option value="">Select establishment</option>
            {establishments.map((e) => (
              <option key={e.code} value={e.code}>{e.name}</option>
            ))}
          </select>
        </div>
        )}
      </div>

      {displayError && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {displayError}
        </div>
      )}
    </div>
  );
}
