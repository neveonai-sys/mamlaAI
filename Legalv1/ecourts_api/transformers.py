"""
Transform eCourts partner API responses into the shapes our frontend expects.

The external API uses camelCase; our scraper used snake_case with a slightly
different structure.  These helpers normalise the data so the frontend can
consume either backend transparently.
"""
import logging

logger = logging.getLogger("django")

# ── Static lookup tables ─────────────────────────────────────────────

CASE_TYPE_NAMES = {
    "CC": "Civil Case",
    "CS": "Civil Suit",
    "COP": "Company Petition",
    "CMA": "Civil Misc. Appeal",
    "CMAppl": "Civil Misc. Application",
    "CRL_A": "Criminal Appeal",
    "CRL_MA": "Criminal Misc. Application",
    "CRL_MISC": "Criminal Misc.",
    "CR_MISC": "Criminal Misc.",
    "CW": "Civil Writ",
    "CWJC": "Civil Writ Jurisdiction Case",
    "EP": "Execution Petition",
    "FA": "First Appeal",
    "FAO": "First Appeal from Order",
    "MA": "Misc. Application",
    "MCA": "Misc. Civil Application",
    "MJC": "Misc. Judicial Case",
    "OA": "Original Application",
    "OP": "Original Petition",
    "OS": "Original Suit",
    "RA": "Review Application",
    "RFA": "Regular First Appeal",
    "RSA": "Regular Second Appeal",
    "SA": "Second Appeal",
    "SB": "Special Bench",
    "SC": "Special Case",
    "SCA": "Special Civil Application",
    "SLP": "Special Leave Petition",
    "ST": "Sessions Trial",
    "WA": "Writ Appeal",
    "WP": "Writ Petition",
    "WP_C": "Writ Petition (Civil)",
    "WP_CRL": "Writ Petition (Criminal)",
    "BA": "Bail Application",
    "ABA": "Anticipatory Bail Application",
    "CRLA": "Criminal Leave to Appeal",
    "RCC": "Regular Criminal Case",
    "SCC": "Summary Criminal Case",
    "MC": "Misc. Case",
    "TS": "Title Suit",
    "MFA": "Misc. First Appeal",
    "ARBIT": "Arbitration",
    "ARBP": "Arbitration Petition",
    "CP": "Civil Petition",
    "CONT_CAS": "Contempt Case",
    "COMP": "Complaint",
    "MTC": "Motor Accident Claims Tribunal",
    "MACT": "Motor Accident Claims Tribunal",
    "RP": "Review Petition",
    "LP": "Leave Petition",
    "TA": "Tax Appeal",
    "ITA": "Income Tax Appeal",
    "EFA": "Election First Appeal",
    "PC": "Probate Case",
    "GC": "Guardianship Case",
    "HMA": "Hindu Marriage Act",
    "CRPC": "Criminal Procedure Code",
    "CPC": "Civil Procedure Code",
    "NI_ACT": "Negotiable Instruments Act",
}

COURT_ESTABLISHMENT_PREFIXES = {
    "AN": "Andaman & Nicobar",
    "AP": "Andhra Pradesh",
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "BR": "Bihar",
    "CG": "Chhattisgarh",
    "CH": "Chandigarh",
    "DD": "Daman & Diu",
    "DL": "Delhi",
    "DN": "Dadra & Nagar Haveli",
    "GA": "Goa",
    "GJ": "Gujarat",
    "HP": "Himachal Pradesh",
    "HR": "Haryana",
    "JH": "Jharkhand",
    "JK": "Jammu & Kashmir",
    "KA": "Karnataka",
    "KL": "Kerala",
    "LA": "Ladakh",
    "MH": "Maharashtra",
    "ML": "Meghalaya",
    "MN": "Manipur",
    "MP": "Madhya Pradesh",
    "MZ": "Mizoram",
    "NL": "Nagaland",
    "OD": "Odisha",
    "PB": "Punjab",
    "PY": "Puducherry",
    "RJ": "Rajasthan",
    "SK": "Sikkim",
    "TG": "Telangana",
    "TN": "Tamil Nadu",
    "TR": "Tripura",
    "UK": "Uttarakhand",
    "UP": "Uttar Pradesh",
    "WB": "West Bengal",
    "TS": "Telangana",
}

COURT_TYPE_CODES = {
    "HC": "High Court",
    "DC": "District Court",
    "DD": "District & Divisional",
    "SC": "Sessions Court",
    "MC": "Magistrate Court",
    "FC": "Family Court",
    "TC": "Tribunal Court",
    "CC": "Civil Court",
    "AC": "Additional Court",
    "MZ": "Muzaffarpur",
    "PT": "Patna",
    "RN": "Ranchi",
    "BH": "Bhagalpur",
    "GY": "Gaya",
    "DH": "Darbhanga",
}


def _parse_court_code(code: str) -> str:
    """Best-effort decode of court establishment codes like RJHC, MPHC03."""
    if not code or len(code) < 4:
        return code
    for prefix_len in (2, 3):
        prefix = code[:prefix_len]
        rest = code[prefix_len:]
        state = COURT_ESTABLISHMENT_PREFIXES.get(prefix)
        if state:
            ct_code = rest.rstrip("0123456789")
            bench = rest[len(ct_code):]
            court_type = COURT_TYPE_CODES.get(ct_code, ct_code)
            label = f"{state} {court_type}"
            if bench:
                label += f" (Bench {bench})"
            return label
    return code


def transform_case_detail(raw: dict) -> dict:
    """
    Convert the /api/partner/case/{cnr} response into our internal shape.
    Input:  raw["data"] from the external API.
    Output: flat dict with case_type, case_status, parties, orders, etc.
    """
    data = raw.get("data", {})
    court = data.get("courtCaseData", {})
    entity = data.get("entityInfo", {})
    files = data.get("files", {})
    ai = data.get("caseAiAnalysis", {})

    petitioners = court.get("petitioners", [])
    respondents = court.get("respondents", [])

    title_parts = []
    if petitioners:
        title_parts.append(", ".join(petitioners[:2]))
    title_parts.append("vs.")
    if respondents:
        title_parts.append(", ".join(respondents[:2]))
    case_title = " ".join(title_parts)

    orders = []
    for idx, f in enumerate(files.get("files", [])):
        order_entry = {
            "index": idx,
            "filename": f.get("pdfFile", ""),
            "order_date": None,
            "order_type": None,
        }
        ai_part = f.get("aiAnalysis") or {}
        if ai_part:
            order_entry["order_date"] = ai_part.get("orderDate")
            order_entry["order_type"] = ai_part.get("orderType")
            order_entry["summary"] = ai_part.get("summary")
        orders.append(order_entry)

    judgment_orders = court.get("judgmentOrders", [])
    for jo in judgment_orders:
        existing_fnames = {o["filename"] for o in orders}
        fname = jo.get("orderUrl", "")
        if fname and fname not in existing_fnames:
            orders.append({
                "index": len(orders),
                "filename": fname,
                "order_date": jo.get("orderDate"),
                "order_type": jo.get("orderType"),
            })

    hearing_history = []
    for h in court.get("historyOfCaseHearings", []):
        hearing_history.append({
            "date": h.get("hearingDate"),
            "judge": h.get("judge"),
            "purpose": h.get("purpose"),
            "business_on_date": h.get("businessOnDate"),
        })

    listing_dates = []
    for ld in court.get("listingDates", []):
        listing_dates.append({
            "date": ld.get("date"),
            "purpose": ld.get("purpose"),
        })

    ias = []
    for ia in court.get("interlocutoryApplications", []):
        ias.append({
            "reg_no": ia.get("regNo"),
            "particular": ia.get("particular"),
            "filing_date": ia.get("filingDate"),
            "status": ia.get("status"),
        })

    tagged = []
    for tm in court.get("taggedMatters", []):
        tagged.append({
            "type": tm.get("type"),
            "case_number": tm.get("caseNumber"),
            "cnr": tm.get("cnr"),
        })

    return {
        "cnr": court.get("cnr", ""),
        "case_title": case_title,
        "case_number": court.get("caseNumber"),
        "case_type": court.get("caseType"),
        "case_status": court.get("caseStatus"),
        "filing_date": court.get("filingDate"),
        "registration_date": court.get("registrationDate"),
        "first_hearing_date": court.get("firstHearingDate"),
        "next_hearing_date": court.get("nextHearingDate"),
        "decision_date": court.get("decisionDate"),
        "judges": court.get("judges", []),
        "petitioners": petitioners,
        "respondents": respondents,
        "petitioner_advocates": court.get("petitionerAdvocates", []),
        "respondent_advocates": court.get("respondentAdvocates", []),
        "acts_and_sections": court.get("actsAndSections"),
        "court_name": court.get("courtName"),
        "state": court.get("state"),
        "district": court.get("district"),
        "court_no": court.get("courtNo"),
        "bench_name": court.get("benchName"),
        "purpose": court.get("purpose"),
        "judicial_section": court.get("judicialSection"),
        "orders": orders,
        "hearing_history": hearing_history,
        "listing_dates": listing_dates,
        "interlocutory_applications": ias,
        "tagged_matters": tagged,
        "ai_analysis": ai or None,
        "entity_info": {
            "next_date_of_hearing": entity.get("nextDateOfHearing"),
            "date_created": entity.get("dateCreated"),
            "date_modified": entity.get("dateModified"),
        },
    }


def _build_facet_labels(results: list, facets: dict) -> dict:
    """
    Build code→name lookup tables from result rows so the facet sidebar can
    display human-readable names instead of raw codes.

    Handles all known facet types from the eCourts partner search API:
      caseType / caseStatus / courtCode / STATECODE / DISTRICTCODE / judicialSection
    """
    # --- Scan raw results to build dynamic code→name mappings -------------
    court_code_map = {}
    state_map = {}      # any kind of state identifier → name
    district_map = {}   # any kind of district identifier → name

    for r in results:
        # Court code → name
        cc = r.get("courtCode")
        cn = r.get("courtName")
        if cc and cn:
            court_code_map[str(cc)] = cn

        # State: try every possible field combo to pair a code with a name
        for code_key in ("stateCode", "STATECODE", "state_code"):
            sc = r.get(code_key)
            if sc is not None:
                sn = r.get("stateName") or r.get("state_name")
                if sn:
                    state_map[str(sc)] = sn
        # Also pair 2-letter state code with name
        s2 = r.get("state")
        sn2 = r.get("stateName") or r.get("state_name")
        if s2 and sn2:
            state_map[str(s2)] = sn2

        # District
        for code_key in ("districtCode", "DISTRICTCODE", "district_code"):
            dc = r.get(code_key)
            if dc is not None:
                dn = r.get("districtName") or r.get("district_name") or r.get("district")
                if dn:
                    district_map[str(dc)] = dn

    # --- Load 2-letter-code → name mapping from cache / free API ----------
    alpha_to_name = {}
    try:
        from ecourts_scraper.cache.cache_manager import EcourtsCacheManager
        cache = EcourtsCacheManager()
        cached_states = cache.get("api:court_structure:states")
        state_list = cached_states.get("data", []) if cached_states else []
        if not state_list:
            from ecourts_api import client as _client
            raw_states = _client.get_states()
            state_list = [
                {"state_code": s["state"], "name": s["stateName"]}
                for s in raw_states
            ]
        for s in state_list:
            code = s.get("state_code")
            name = s.get("name")
            if code and name:
                alpha_to_name[str(code)] = name
                state_map.setdefault(str(code), name)
    except Exception as exc:
        logger.debug("Could not load states for facet labels: %s", exc)

    # Cross-reference: if results have both a numeric stateCode AND a 2-letter
    # state field, link the numeric code to the name via the alpha table.
    for r in results:
        numeric = None
        alpha = None
        for nk in ("stateCode", "STATECODE", "state_code"):
            v = r.get(nk)
            if v is not None:
                numeric = str(v)
                break
        for ak in ("state", "stateAlpha"):
            v = r.get(ak)
            if v and isinstance(v, str) and len(v) <= 3:
                alpha = str(v)
                break
        if numeric and alpha and numeric not in state_map:
            resolved = alpha_to_name.get(alpha)
            if resolved:
                state_map[numeric] = resolved

    # --- Build labels for each facet --------------------------------------
    enriched = {}
    for key, facet in facets.items():
        enriched[key] = dict(facet)
        values = facet.get("values") or {}
        if not values:
            continue

        key_lower = key.lower()
        labels = {}

        if key_lower in ("casetype", "case_type"):
            labels = {v: CASE_TYPE_NAMES.get(v, v) for v in values}

        elif key_lower in ("courtcode", "court_code"):
            for v in values:
                sv = str(v)
                labels[v] = court_code_map.get(sv) or _parse_court_code(sv)

        elif key_lower in ("statecode", "state_code", "state"):
            for v in values:
                sv = str(v)
                labels[v] = state_map.get(sv, sv)

        elif key_lower in ("districtcode", "district_code", "district"):
            for v in values:
                sv = str(v)
                labels[v] = district_map.get(sv, sv)

        if labels:
            enriched[key]["labels"] = labels

    return enriched


def enrich_cached_facets(transformed_data: dict) -> dict:
    """
    Re-apply facet labels to already-transformed search data (e.g. from cache).
    Uses static mappings, court-code parsing, and state name tables.
    Idempotent -- safe to call on data that already has labels.
    """
    facets = transformed_data.get("facets", {})
    if not facets:
        return transformed_data

    # If labels already exist on all facets, skip expensive lookups
    all_labeled = all(
        not isinstance(f, dict) or not f.get("values") or f.get("labels")
        for f in facets.values()
    )
    if all_labeled:
        return transformed_data

    case_list = transformed_data.get("case_list", [])

    court_code_map = {}
    state_map = {}
    district_map = {}
    for c in case_list:
        cc = c.get("court_code")
        cn = c.get("court_name")
        if cc and cn and cn != cc:
            court_code_map[str(cc)] = cn

        # Build numeric code → name mappings from stored case data
        sc = c.get("state_code")
        sn = c.get("state_name")
        if sc and sn:
            state_map[str(sc)] = sn
        # Also map 2-letter alpha code to name
        sa = c.get("state_alpha")
        if sa and sn:
            state_map[str(sa)] = sn

        dc = c.get("district_code")
        dn = c.get("district_name")
        if dc and dn:
            district_map[str(dc)] = dn

    # Supplement from cached states table (2-letter code → name)
    try:
        from ecourts_scraper.cache.cache_manager import EcourtsCacheManager
        _cache = EcourtsCacheManager()
        cached_states = _cache.get("api:court_structure:states")
        state_list = cached_states.get("data", []) if cached_states else []
        if not state_list:
            from ecourts_api import client as _client
            raw_states = _client.get_states()
            state_list = [
                {"state_code": s["state"], "name": s["stateName"]}
                for s in raw_states
            ]
        for s in state_list:
            code = s.get("state_code")
            name = s.get("name")
            if code and name:
                state_map.setdefault(str(code), name)
    except Exception:
        pass

    enriched = {}
    for key, facet in facets.items():
        enriched[key] = dict(facet) if isinstance(facet, dict) else facet
        if not isinstance(facet, dict):
            continue
        values = facet.get("values") or {}
        if not values:
            continue

        key_lower = key.lower()
        labels = {}

        if key_lower in ("casetype", "case_type"):
            labels = {v: CASE_TYPE_NAMES.get(v, v) for v in values}
        elif key_lower in ("courtcode", "court_code"):
            for v in values:
                labels[v] = court_code_map.get(str(v)) or _parse_court_code(str(v))
        elif key_lower in ("statecode", "state_code", "state"):
            for v in values:
                labels[v] = state_map.get(str(v), str(v))
        elif key_lower in ("districtcode", "district_code", "district"):
            for v in values:
                labels[v] = district_map.get(str(v), str(v))

        if labels:
            enriched[key]["labels"] = labels

    result = dict(transformed_data)
    result["facets"] = enriched
    return result


def transform_search_results(raw: dict) -> dict:
    """
    Convert /api/partner/search response into our internal search shape.
    """
    data = raw.get("data", {})
    results = data.get("results", [])

    case_list = []
    for r in results:
        pets = r.get("petitioners", [])
        resps = r.get("respondents", [])
        title_parts = []
        if pets:
            title_parts.append(", ".join(pets[:2]))
        title_parts.append("vs.")
        if resps:
            title_parts.append(", ".join(resps[:2]))

        case_list.append({
            "cnr": r.get("cnr", ""),
            "case_title": " ".join(title_parts),
            "case_type": r.get("caseType"),
            "case_status": r.get("caseStatus"),
            "filing_date": r.get("filingDate"),
            "next_hearing_date": r.get("nextHearingDate"),
            "judges": r.get("judges", []),
            "petitioners": pets,
            "respondents": resps,
            "petitioner_advocates": r.get("petitionerAdvocates", []),
            "respondent_advocates": r.get("respondentAdvocates", []),
            "acts_and_sections": r.get("actsAndSections"),
            "court_code": r.get("courtCode"),
            "court_name": r.get("courtName") or r.get("courtCode"),
            "state_code": r.get("stateCode") or r.get("STATECODE"),
            "state_alpha": r.get("state"),
            "state_name": r.get("stateName") or r.get("state"),
            "district_code": r.get("districtCode") or r.get("DISTRICTCODE"),
            "district_name": r.get("districtName") or r.get("district"),
            "judicial_section": r.get("judicialSection"),
        })

    raw_facets = data.get("facets", {})
    facets = _build_facet_labels(results, raw_facets)

    return {
        "case_list": case_list,
        "total": data.get("totalHits", len(case_list)),
        "page": data.get("page", 1),
        "page_size": data.get("pageSize", 20),
        "total_pages": data.get("totalPages", 1),
        "has_next_page": data.get("hasNextPage", False),
        "facets": facets,
    }


def transform_causelist_results(raw: dict) -> dict:
    """Convert /api/partner/causelist/search response."""
    data = raw.get("data", {})
    results = data.get("results", [])

    entries = []
    for r in results:
        entries.append({
            "id": r.get("id"),
            "court_type": r.get("courtType"),
            "list_type": r.get("listType"),
            "bench": r.get("bench"),
            "court_no": r.get("courtNo"),
            "date": r.get("date"),
            "case_number": r.get("caseNumber", []),
            "party": r.get("party"),
            "petitioners": r.get("petitioners", []),
            "respondents": r.get("respondents", []),
            "advocates": r.get("advocates", []),
            "judge": r.get("judge", []),
            "district": r.get("district"),
            "state": r.get("state"),
            "status": r.get("status"),
            "district_code": r.get("districtCode"),
            "court_name": r.get("courtName"),
        })

    return {
        "entries": entries,
        "query": data.get("query"),
        "returned_count": data.get("returnedCount", len(entries)),
        "limit": data.get("limit"),
        "offset": data.get("offset"),
    }


def transform_states(raw_list: list) -> list:
    """Convert court-structure/states response."""
    return [
        {"state_code": s["state"], "name": s["stateName"]}
        for s in raw_list
    ]


def transform_districts(raw_list: list) -> list:
    """Convert court-structure/.../districts response."""
    return [
        {"district_code": d["districtCode"], "name": d["districtName"]}
        for d in raw_list
    ]


def transform_complexes(raw_list: list) -> list:
    """Convert court-structure/.../complexes response."""
    return [
        {"complex_code": c["courtComplexCode"], "name": c["courtComplexName"]}
        for c in raw_list
    ]


def transform_courts(raw_list: list) -> list:
    """Convert court-structure/.../courts response."""
    return [
        {
            "court_id": c.get("court"),
            "court_no": c.get("courtNo"),
            "court_name": c.get("courtName"),
            "court_division": c.get("courtDivision"),
            "judge_name": c.get("judgeName"),
        }
        for c in raw_list
    ]
