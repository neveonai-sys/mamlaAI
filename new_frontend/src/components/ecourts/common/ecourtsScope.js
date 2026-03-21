const HIGH_COURT_SCOPE_KEYS = ['courtType', 'highCourtId', 'benchCode', 'registrationYear'];
const DISTRICT_COURT_SCOPE_KEYS = ['courtType', 'stateName', 'districtName', 'courtId'];

function readScopeValue(source, key) {
  if (!source) {
    return '';
  }

  if (typeof source.get === 'function') {
    return source.get(key) || '';
  }

  return source[key] || '';
}

export function buildEcourtsScopeParams(scope = {}) {
  const courtType = readScopeValue(scope, 'courtType') || 'high_court';

  if (courtType === 'district_court') {
    const params = { courtType };
    for (const key of DISTRICT_COURT_SCOPE_KEYS.slice(1)) {
      const value = readScopeValue(scope, key);
      if (value) {
        params[key] = value;
      }
    }
    return params;
  }

  const params = { courtType: courtType || 'high_court' };
  for (const key of HIGH_COURT_SCOPE_KEYS.slice(1)) {
    const value = readScopeValue(scope, key);
    if (value) {
      params[key] = value;
    }
  }
  return params;
}

export function buildScopedSearchPath(basePath, query, scope = {}) {
  const params = new URLSearchParams(buildEcourtsScopeParams(scope));
  if (query) {
    params.set('q', query);
  }
  const serialized = params.toString();
  return serialized ? `${basePath}?${serialized}` : basePath;
}

export function buildScopedCaseDetailPath(cnr, scope = {}) {
  const normalizedCnr = encodeURIComponent(cnr || '');
  const params = new URLSearchParams(buildEcourtsScopeParams(scope));
  const serialized = params.toString();
  return serialized ? `/ecourts/case/${normalizedCnr}?${serialized}` : `/ecourts/case/${normalizedCnr}`;
}
