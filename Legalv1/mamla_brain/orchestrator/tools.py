"""
Tool registry for MamlaAI Chat.

Each capability is a thin wrapper around code that already exists elsewhere — no
drafting/RAG logic is reimplemented. A tool returns one of two normalised
shapes, which `loop.run_turn` knows how to emit:

  {'kind': 'answer', 'answer': str, 'artifacts': [...], 'citations': [...], 'tool_trace': [...]}
      a ready answer (e.g. draft deep-link, or a "please attach a document" nudge)

  {'kind': 'stream', 'messages': [...], 'artifacts': [...], 'citations': [...], 'tool_trace': [...]}
      LLM messages the loop should stream, plus the citations to attach

`dispatch()` maps a routed capability to its tool. draft / research / doc_qa are
dedicated tools; citation and general fall through to the loop's grounded
general path (citation gets a dedicated tool in Phase 3).
"""
import logging
import re

from .grounding import augment_system_with_grounding
from .prompts_v2 import build_orchestrator_system

logger = logging.getLogger('django')


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _citations_from_context(context_items):
    """Mirror mamla_brain.views._citations_from_context for v2."""
    citations = []
    for item in (context_items or [])[:5]:
        citation = dict(item.get('citation', {}))
        citation['source_type'] = item.get('source_type')
        if item.get('source_type') == 'knowledge_base':
            citation['act'] = item.get('act', '')
            citation['section'] = item.get('section_number', '')
        citations.append(citation)
    return citations


def _stream_messages(session, text, history, context_text, task_hint):
    """Assemble streamable LLM messages: grounded persona + history + context+question."""
    system = build_orchestrator_system(session.get('domain_key', 'legal'))
    system = f'{system}\n\n{task_hint}'
    system = augment_system_with_grounding(system, text)  # verification-gated citations
    messages = [{'role': 'system', 'content': system}]
    for turn in history:
        messages.append({'role': turn['role'], 'content': turn['content']})
    if context_text:
        messages.append({'role': 'user', 'content': f'CONTEXT (use only this; do not add outside facts):\n{context_text}\n\nQUESTION:\n{text}'})
    else:
        messages.append({'role': 'user', 'content': text})
    return messages


_RESEARCH_HINT = (
    "TASK: Legal research. Answer-first: lead with the answer, then the analysis. "
    "Ground every legal proposition in the CONTEXT provided (statutes/sections from "
    "the knowledge base). If the context does not cover the point, say so and say what "
    "authority is needed — do not fill the gap from memory. Give a confidence level."
)
_DOC_QA_HINT = (
    "TASK: Answer strictly about the user's uploaded document(s). Every factual claim "
    "must be attributable to a passage in the CONTEXT (cite the document/page). If the "
    "document does not answer the question, say so plainly — do not speculate."
)


# ---------------------------------------------------------------------------
# Draft tool
# ---------------------------------------------------------------------------
def _infer_draft_for(text: str) -> str:
    from ..llm_router import call_llm, parse_json_response
    prompt = (
        "From the user's request, name the single Indian legal document type to draft, "
        "in 1-4 words (e.g. 'Anticipatory Bail Application', 'Legal Notice', "
        "'Rent Agreement'). Respond ONLY as JSON: {\"draft_for\": \"<type>\"}."
    )
    try:
        response = call_llm(
            [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': text}],
            tier='t1',
        )
        payload = parse_json_response(response.get('text'), fallback={}) or {}
        label = str(payload.get('draft_for', '')).strip()
        if label:
            return label[:80]
    except Exception as exc:
        logger.warning('[tools.draft] infer draft_for failed: %s', exc)
    return 'Legal Document'


# ---------------------------------------------------------------------------
# What we need to ask for before drafting is worth generating. Keyed by the
# lowercased draft_for label; falls back to a generic prompt for anything not
# in the table. This is what turns "yes" into a real conversation instead of
# an instant, fact-free document.
# ---------------------------------------------------------------------------
_DRAFT_FIELD_HINTS = {
    'rent agreement': "the landlord's & tenant's full names, the property address, monthly rent & security deposit, start date & lease term, and the city (for stamp duty)",
    'lease deed': "the lessor's & lessee's full names, the property address, rent & deposit, start date & lease term, and the city (for stamp duty)",
    'bail application': "the applicant's name, FIR number & police station, the court, sections invoked, and current custody status",
    'anticipatory bail application': "the applicant's name, FIR number & police station, the court, sections invoked, and the apprehended grounds for arrest",
    'legal notice': "the sender's & recipient's names/addresses, the dispute or grievance, and the relief or deadline you want to state",
    'affidavit': "the deponent's name & address, and the facts to be sworn",
    'power of attorney': "the principal's & agent's full names/addresses, and the specific powers being granted",
    'divorce petition': "both spouses' names, the marriage date & place, grounds for divorce, and any children/property involved",
    'writ petition': "the petitioner's & respondent's names, the order or action being challenged, and the relief sought",
    'sale deed': "the seller's & buyer's full names, the property description, sale consideration, and the city (for stamp duty)",
    'will': "the testator's name, the beneficiaries and what each inherits, and the executor's name",
}
_GENERIC_FIELD_HINT = "the parties involved, the key facts and dates, the court or forum (if any), and the relief you want"


def field_hint_for(draft_for: str) -> str:
    return _DRAFT_FIELD_HINTS.get((draft_for or '').strip().lower(), _GENERIC_FIELD_HINT)


def run_draft(session, text, history, tier_cfg):
    """
    Turn 1 of confirm-first drafting: never generate from a single message.
    Ask for the specific facts this document needs — a bare "yes" isn't
    enough to produce something worth filing, so we ask before we write.
    """
    from . import store

    draft_for = _infer_draft_for(text)
    store.set_pending_draft(session['_id'], draft_for, text)
    hint = field_hint_for(draft_for)
    answer = (
        f"I can draft a **{draft_for}** for you. To make it accurate, tell me {hint}.\n\n"
        "Share whatever you have — even partial details help — and I'll draft it from that. "
        "If you'd rather start from a generic, clearly-labelled template you can fill in yourself, "
        "just say **use placeholders**."
    )
    return {
        'kind': 'answer', 'answer': answer, 'artifacts': [], 'citations': [],
        'tool_trace': [{'capability': 'draft', 'status': 'pending_details', 'draft_for': draft_for}],
    }


def run_draft_generate(session, text, history, tier_cfg, use_placeholders=False):
    """
    Generate via the existing ai_draft engine and return an INLINE preview
    (full sections) so the draft lives in the chat; the drafting workspace
    deep-link is an option, not the destination.

    `use_placeholders` is set when the user gave up supplying details (two
    bare "yes"es) or explicitly asked for a generic template — the engine is
    told to fill every missing fact with a labelled [PLACEHOLDER] instead of
    inventing plausible-sounding names/dates/amounts.
    """
    from ai_draft.routes.creatupdateAIdrafts import CreateupdatefetchAIdrafts
    from . import store

    pending = session.get('pending_draft') or {}
    draft_for = pending.get('draft_for') or _infer_draft_for(text)
    # Original request + anything the user added on this turn (skip echoing
    # back bare confirmations or the "use placeholders" instruction itself).
    query = (pending.get('query') or '').strip()
    extra = text.strip()
    if extra and not is_affirmative(extra) and not _PLACEHOLDER_RE.search(extra):
        query = f'{query}\n\nAdditional details from the user: {extra}' if query else extra
    query = query or text
    if use_placeholders:
        query = (
            f'{query}\n\nThe user has not provided full details. Generate a generic, clearly-labelled '
            'template using [PLACEHOLDER] brackets for every missing fact (names, addresses, amounts, '
            'dates) so they can fill it in themselves — do not invent plausible-sounding specifics.'
        )

    owner_id = session['owner_id']
    engine = CreateupdatefetchAIdrafts(owner_id)
    try:
        # `draft_for` on the chat path is a document-type LABEL ('Rent Agreement'),
        # unlike the drafting workspace where the same argument carries case/client
        # association. Pass it as the type hint too, so chat gets the playbook.
        draft_session_id = engine.start_new_session(
            query, draft_for, location={},
            language=session.get('language') or 'English',
            document_type=draft_for,
        )
    except Exception as exc:
        logger.error('[tools.draft] start_new_session failed: %s', exc)
        draft_session_id = ''

    store.clear_pending_draft(session['_id'])

    if not draft_session_id:
        return {
            'kind': 'answer',
            'answer': ("I couldn't generate the draft just now. Tell me the document type and the key facts "
                       "(parties, court/forum, relief sought) and I'll try again."),
            'artifacts': [], 'citations': [],
            'tool_trace': [{'capability': 'draft', 'status': 'error'}],
        }

    draft_id = str(draft_session_id)
    sections = []
    raw_list = []
    try:
        raw = engine.retrieve_sections_of_draft(draft_id)
        # retrieve_sections_of_draft returns {'mssg': [ {section_id, section_name,
        # content, ...}, ... ], ...}; keep section_id so the chat canvas can edit.
        raw_list = raw.get('mssg') if isinstance(raw, dict) else raw
        if not isinstance(raw_list, list):
            raw_list = []
        sections = [
            {'section_id': s.get('section_id', ''), 'section_name': s.get('section_name', ''),
             'content': s.get('content', '')}
            for s in raw_list if isinstance(s, dict)
        ]
    except Exception as exc:
        logger.warning('[tools.draft] could not fetch sections for preview: %s', exc)

    # Name the draft after the chat thread (+ timestamp) so, if the user later
    # opens it in the drafting workspace, it carries the conversation's name.
    from datetime import datetime
    chat_title = (session.get('title') or 'MamlaAI Chat').strip()
    draft_name = f"{chat_title} · {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
    try:
        engine.auto_save_initial_draft(draft_id, draft_name, raw_list)
    except Exception as exc:
        logger.warning('[tools.draft] could not name draft %s: %s', draft_id, exc)

    artifact = {
        'type': 'draft', 'draft_for': draft_for, 'draft_session_id': draft_id,
        'draft_name': draft_name, 'deep_link': f'/drafting/{draft_id}',
        'section_count': len(sections), 'sections': sections, 'placeholders': use_placeholders,
    }
    if use_placeholders:
        answer = (
            f"Since I don't have the specifics yet, here's a generic **{draft_for}** template"
            + (f" ({len(sections)} sections)" if sections else "")
            + " — every [PLACEHOLDER] needs your real details before this is usable. Expand a section "
            "below to review it, or open it in the drafting workspace to edit."
        )
    else:
        answer = (
            f"Here's the first draft of your **{draft_for}**"
            + (f" ({len(sections)} sections)" if sections else "")
            + " — expand any section below to review it. You can refine it right here, or open it "
            "in the drafting workspace for full editing. Placeholders in [CAPS] need your details, "
            "and please verify every citation and section number against the primary source before filing."
        )
    return {
        'kind': 'answer', 'answer': answer, 'artifacts': [artifact], 'citations': [],
        'tool_trace': [{'capability': 'draft', 'status': 'ok', 'draft_for': draft_for, 'draft_session_id': draft_id}],
    }


# Bare confirmations ("yes", "ok go ahead", "yes please draft it") — never
# enough on their own to generate; they only re-affirm intent to draft. Allows
# several stacked affirm words, nothing else.
_AFFIRM_WORD = (
    r'(?:yes|yeah|yep|ok(?:ay)?|sure|please|confirm(?:ed)?|go\s+ahead|proceed|'
    r'generate(?:\s+it)?|draft(?:\s+it)?|make\s+it|do\s+it|haan|ha|theek\s+hai)'
)
_AFFIRM_ONLY_RE = re.compile(
    rf'^\s*(?:{_AFFIRM_WORD}[\s,.!]*)+$',
    re.IGNORECASE,
)

# Explicit opt-out of giving details — generate a placeholder template now.
_PLACEHOLDER_RE = re.compile(
    r'\b(use\s+placeholders?|generic\s+template|just\s+(draft|generate)\s+it|'
    r"skip\s+(the\s+)?questions?|don'?t\s+have\s+(the\s+)?details|no\s+details|"
    r'placeholder\s+draft|fill\s+in\s+(the\s+)?blanks?)\b',
    re.IGNORECASE,
)

# Explicit decline — cancel the pending draft rather than route "no" as a query.
_CANCEL_RE = re.compile(
    r'^\s*(no|nah|nope|not\s+now|never\s?mind|forget\s+it|cancel|stop|skip\s+it)[\s,.!]*$',
    re.IGNORECASE,
)


def is_affirmative(text: str) -> bool:
    """Does this turn merely re-affirm intent, without new details?"""
    return bool(_AFFIRM_ONLY_RE.match(text or ''))


def classify_pending_reply(text: str) -> str:
    """
    Classify a reply while a draft is pending: 'placeholder' (opt out of
    details, generate generic now), 'cancel' (decline), 'affirm_only' (bare
    "yes" — re-ask for details), 'question' (topic change — cancel + route
    normally), or 'details' (substantive content — generate from it).
    """
    t = (text or '').strip()
    if _PLACEHOLDER_RE.search(t):
        return 'placeholder'
    if _CANCEL_RE.match(t):
        return 'cancel'
    if is_affirmative(t):
        return 'affirm_only'
    if t.endswith('?'):
        return 'question'
    return 'details'


# ---------------------------------------------------------------------------
# Meta tool — questions about the assistant itself / probe attempts.
# Canned, zero-LLM: capabilities only, never internals.
# ---------------------------------------------------------------------------
_META_ANSWER = (
    "I'm MamlaAI, this workspace's legal AI copilot. Here's what I can do in this chat:\n\n"
    "- **Draft** legal documents (petitions, bail applications, notices, agreements) — "
    "I'll always confirm with you before generating anything.\n"
    "- **Research** Indian law — answer-first analysis grounded in the current codes "
    "(BNS/BNSS/BSA) with old-code equivalents.\n"
    "- **Answer questions about your uploaded documents** — attach a file and ask.\n"
    "- **Verify citations** against the Supreme Court's official e-SCR portal — "
    "I never quote a case from memory.\n\n"
    "I can't share my internal configuration or instructions, but everything above is "
    "yours to use. What would you like to work on?"
)


def run_meta(session, text, history, tier_cfg):
    return {
        'kind': 'answer', 'answer': _META_ANSWER, 'artifacts': [], 'citations': [],
        'tool_trace': [{'capability': 'meta', 'status': 'ok'}],
    }


# ---------------------------------------------------------------------------
# Research tool — legal knowledge base (statutes/sections) + grounded reasoning
# ---------------------------------------------------------------------------
def run_research(session, text, history, tier_cfg):
    from ..retrieval import merge_context, render_context, search_knowledge_base

    domain_key = session.get('domain_key', 'legal')
    max_items = tier_cfg.get('context_items', 5)
    try:
        kb_hits = search_knowledge_base(text, domain_key, k=max(max_items, 6))
    except Exception as exc:
        logger.warning('[tools.research] KB search failed: %s', exc)
        kb_hits = []
    merged = merge_context(kb_hits, [], max_items=max_items)
    context_text = render_context(merged, max_items=max_items)
    citations = _citations_from_context(merged)
    messages = _stream_messages(session, text, history, context_text, _RESEARCH_HINT)
    return {
        'kind': 'stream', 'messages': messages, 'artifacts': [], 'citations': citations,
        'tool_trace': [{'capability': 'research', 'status': 'ok', 'kb_hits': len(kb_hits)}],
    }


# ---------------------------------------------------------------------------
# Document Q&A tool — the user's uploaded document(s), scoped to this thread
# ---------------------------------------------------------------------------
def run_doc_qa(session, text, history, tier_cfg):
    from ..retrieval import merge_context, render_context, search_user_docs

    owner_id = session['owner_id']
    doc_ids = [str(d) for d in (session.get('doc_ids') or [])]
    if not doc_ids:
        return {
            'kind': 'answer',
            'answer': ("I don't see a document attached to this chat yet. Upload the file "
                       "(FIR, contract, order, etc.) using the attach button and I'll answer against it."),
            'artifacts': [], 'citations': [],
            'tool_trace': [{'capability': 'doc_qa', 'status': 'no_docs'}],
        }

    max_items = tier_cfg.get('context_items', 5)
    try:
        doc_hits = search_user_docs(text, owner_id, doc_ids=doc_ids, matter=session.get('matter'), k=10)
    except Exception as exc:
        logger.warning('[tools.doc_qa] doc search failed: %s', exc)
        doc_hits = []
    merged = merge_context([], doc_hits, max_items=max_items)
    context_text = render_context(merged, max_items=max_items)
    citations = _citations_from_context(merged)
    messages = _stream_messages(session, text, history, context_text, _DOC_QA_HINT)
    return {
        'kind': 'stream', 'messages': messages, 'artifacts': [], 'citations': citations,
        'tool_trace': [{'capability': 'doc_qa', 'status': 'ok', 'doc_hits': len(doc_hits)}],
    }


# ---------------------------------------------------------------------------
# Citation tool — verify a specific case/citation against the live e-SCR portal
# ---------------------------------------------------------------------------
def run_citation(session, text, history, tier_cfg):
    from ai_draft.citation_grounding import extract_candidate
    from ecourt_scrapped.services import citation_client

    candidate = extract_candidate(text)
    if not candidate:
        return {
            'kind': 'answer',
            'answer': ("Tell me the specific case name or citation you want me to verify "
                       "(e.g. 'State of U.P. v. Ram Prakash' or '2024 INSC 45'). The official "
                       "e-SCR portal verifies a specific citation — it can't search by topic."),
            'artifacts': [], 'citations': [],
            'tool_trace': [{'capability': 'citation', 'status': 'no_candidate'}],
        }

    try:
        result = citation_client.lookup_citation(candidate)
    except Exception as exc:
        logger.warning('[tools.citation] lookup failed for %r: %s', candidate, exc)
        result = None

    if not result or not result.get('case_title'):
        return {
            'kind': 'answer',
            'answer': (f"I could not verify \"{candidate}\" against the Supreme Court's official "
                       "e-SCR portal, so I won't quote a case title or citation from memory. "
                       "Please double-check the citation, or try again shortly."),
            'artifacts': [], 'citations': [],
            'tool_trace': [{'capability': 'citation', 'status': 'not_found', 'candidate': candidate}],
        }

    verified = {
        'type': 'citation',
        'case_title': result.get('case_title'),
        'neutral_citation': result.get('nc_display'),
        'scr_citation': result.get('scr_citation'),
        'cnr': result.get('cnr'),
        'pdf_url': result.get('pdf_url') or result.get('pdf_link'),
        'source': 'Supreme Court e-SCR portal',
    }
    bits = [f"**{verified['case_title']}**"]
    if verified['neutral_citation']:
        bits.append(f"Neutral citation: {verified['neutral_citation']}")
    if verified['scr_citation']:
        bits.append(f"SCR: {verified['scr_citation']}")
    answer = "Verified against the Supreme Court's official e-SCR portal:\n\n" + "\n".join(bits)
    return {
        'kind': 'answer', 'answer': answer, 'artifacts': [verified],
        'citations': [{'source_type': 'e-scr', **verified}],
        'tool_trace': [{'capability': 'citation', 'status': 'verified', 'candidate': candidate}],
    }


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
_TOOLS = {
    'draft': run_draft,          # confirm-first: asks before generating
    'research': run_research,
    'doc_qa': run_doc_qa,
    'citation': run_citation,
    'meta': run_meta,            # canned capabilities answer, zero LLM
}


def dispatch(capability, session, text, history, tier_cfg):
    """Return a normalised tool result, or None to use the grounded general path."""
    handler = _TOOLS.get(capability)
    if not handler:
        return None
    return handler(session, text, history, tier_cfg)
