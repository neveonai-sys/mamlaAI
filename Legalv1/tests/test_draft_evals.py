"""
Eval-harness tests. Offline, free, deterministic.

The important one is the calibration block: it feeds the ACTUAL drafts from the
intern benchmark through our scorer and asserts we reproduce the reviewers'
verdict. Reviewer scores were Mamla 3/10 and Jhana 7/10.

That test is the guard against the failure mode this whole programme is
vulnerable to — quietly loosening checks until our own output passes. If the
rubric stops agreeing with the lawyers about documents the lawyers already
judged, this goes red.
"""

import re
import json

import pytest

from ai_draft.drafting import checks as C
from ai_draft.evals.benchmark_drafts import JHANA_RENT_NOTICE, MAMLA_RENT_NOTICE
from ai_draft.evals.rubric import normalize_draft, score_deterministic
from ai_draft.evals.schema import DEFAULT_RUBRIC_WEIGHTS, load_suite

REVIEWER_MAMLA = 3.0
REVIEWER_JHANA = 7.0
TOLERANCE = 1.5   # we need the ranking and the magnitude, not the decimal


@pytest.fixture(scope='module')
def cases():
    return {c.id: c for c in load_suite()}


@pytest.fixture(scope='module')
def rent_case(cases):
    return cases['001_rent_arrears_notice']


# ---------------------------------------------------------------------------
# Calibration against the human verdict
# ---------------------------------------------------------------------------

def test_reproduces_reviewer_score_for_our_draft(rent_case):
    score = score_deterministic(normalize_draft(MAMLA_RENT_NOTICE), rent_case)
    assert abs(score.overall - REVIEWER_MAMLA) <= TOLERANCE, (
        f'scorer says {score.overall:.1f}, reviewers said {REVIEWER_MAMLA}. '
        f'The rubric has drifted from what a lawyer would say.'
    )


def test_reproduces_reviewer_score_for_competitor_draft(rent_case):
    score = score_deterministic(normalize_draft(JHANA_RENT_NOTICE), rent_case)
    assert abs(score.overall - REVIEWER_JHANA) <= TOLERANCE, (
        f'scorer says {score.overall:.1f}, reviewers said {REVIEWER_JHANA}.'
    )


def test_ranking_matches_the_reviewers(rent_case):
    """The gap is the point: a materially better draft must score materially higher."""
    ours = score_deterministic(normalize_draft(MAMLA_RENT_NOTICE), rent_case).overall
    theirs = score_deterministic(normalize_draft(JHANA_RENT_NOTICE), rent_case).overall
    assert theirs > ours + 2.0


def test_statute_misuse_is_a_hard_failure(rent_case):
    """A penal code in a civil notice zeroes the statute dimension. Not partial credit."""
    score = score_deterministic(normalize_draft(MAMLA_RENT_NOTICE), rent_case)
    assert 'statute' in score.hard_failures
    by = {s.name: s for s in score.subscores}
    assert by['statute'].score == 0.0
    assert any('BNSS' in f for f in by['statute'].findings)


def test_competitor_draft_passes_statute_and_format(rent_case):
    score = score_deterministic(normalize_draft(JHANA_RENT_NOTICE), rent_case)
    by = {s.name: s for s in score.subscores}
    assert by['statute'].score == 10.0
    assert by['format'].score >= 7.0


def test_both_drafts_fail_compliance_for_missing_advisories(rent_case):
    """Neither product produced assumptions or an issues list. Defect #4."""
    for draft in (MAMLA_RENT_NOTICE, JHANA_RENT_NOTICE):
        score = score_deterministic(normalize_draft(draft), rent_case)
        by = {s.name: s for s in score.subscores}
        assert by['compliance'].score < 5.0
        assert any('assumptions' in f for f in by['compliance'].findings)


# ---------------------------------------------------------------------------
# Engine-failure handling
# ---------------------------------------------------------------------------

def test_empty_draft_scores_zero_not_crash(rent_case):
    """Today the engine silently returns [] on a JSON error. That must score 0."""
    score = score_deterministic(normalize_draft([]), rent_case)
    assert score.overall == 0.0
    assert score.error
    assert len(score.hard_failures) == 4


def test_none_from_engine_is_handled(rent_case):
    score = score_deterministic(normalize_draft(None), rent_case)
    assert score.overall == 0.0
    assert 'None' in score.error


# ---------------------------------------------------------------------------
# Schema shapes
# ---------------------------------------------------------------------------

def test_normalize_accepts_legacy_bare_list():
    """Today's engine returns a bare array; the Phase 2 engine returns an object.
    The same scorer must read both, or before/after are not comparable."""
    d = normalize_draft([{'section_name': 'A', 'content': 'x'}])
    assert len(d.sections) == 1
    assert d.assumptions == [] and d.drafting_notes == []


def test_normalize_accepts_phase2_object():
    d = normalize_draft({
        'document_type': 'legal_notice.rent_arrears',
        'sections': [{'section_name': 'A', 'content': 'x'}],
        'assumptions': [{'assumption': 'tenancy is month-to-month'}],
        'drafting_notes': [{'issue': 'State Rent Act not identified'}],
    })
    assert d.document_type == 'legal_notice.rent_arrears'
    assert d.assumptions and d.drafting_notes
    assert 'month-to-month' in d.notes_text


# ---------------------------------------------------------------------------
# Fixture hygiene
# ---------------------------------------------------------------------------

def test_all_fixtures_load():
    suite = load_suite()
    assert len(suite) >= 4, 'the four benchmark prompts must all be present'


def test_every_fixture_has_a_prompt_and_valid_weights():
    for case in load_suite():
        assert case.prompt.strip(), f'{case.id} has no prompt'
        assert abs(sum(case.expect.rubric_weights.values()) - 1.0) < 0.001


def test_every_fixture_forbids_penal_statutes():
    """All four benchmark matters are civil, commercial or testamentary."""
    for case in load_suite():
        assert case.expect.forbid_penal_statutes, (
            f'{case.id}: none of the benchmark prompts is a criminal matter'
        )


def test_fixture_regexes_compile():
    for case in load_suite():
        assert isinstance(case.expect.must_not_match, tuple)  # __post_init__ compiled them


def test_default_weights_sum_to_one():
    assert abs(sum(DEFAULT_RUBRIC_WEIGHTS.values()) - 1.0) < 0.001


# ---------------------------------------------------------------------------
# Recorded-fixture replay (populated by `eval_drafts --record`)
# ---------------------------------------------------------------------------

def test_recorded_runs_replay_if_present(cases):
    """
    Re-score whatever `--record` captured. Skips cleanly when nothing has been
    recorded yet, so CI is green on a fresh clone.
    """
    from ai_draft.evals.runner import RECORDED_DIR

    files = sorted(RECORDED_DIR.glob('*.json'))
    if not files:
        pytest.skip('no recorded runs — run `manage.py eval_drafts --record` first')

    for path in files:
        blob = json.loads(path.read_text(encoding='utf-8'))
        case = cases.get(blob['case_id'])
        assert case, f'{path.name} references unknown case {blob["case_id"]}'
        score = score_deterministic(normalize_draft({
            'sections': blob.get('sections') or [],
            'assumptions': blob.get('assumptions') or [],
            'drafting_notes': blob.get('drafting_notes') or [],
        }), case)
        assert 0.0 <= score.overall <= 10.0


# ---------------------------------------------------------------------------
# Fixture-regex calibration
#
# `must_not_match` patterns are assertions about BAD drafting. When one is too
# loose it penalises a correct draft, and because the score feeds back into how
# we tune prompts, a false positive here actively pushes the product toward the
# defect it was meant to catch. Both cases below are regressions found by
# reading real generations rather than trusting the number.
# ---------------------------------------------------------------------------

CORRECT_REVOCATION_CLAUSE = (
    'I hereby revoke all wills, codicils and other testamentary dispositions made '
    'by me at any time prior to the date of execution of this Will. This revocation '
    'is confined strictly to testamentary instruments executed by me before the date '
    'of this Will, and nothing in this Will shall be read as an attempt to revoke, '
    'restrict, or fetter any testamentary instrument that I may execute after the '
    'date hereof, my power to make further or later wills and codicils being '
    'expressly reserved.'
)

DEFECTIVE_REVOCATION_CLAUSES = [
    'I hereby revoke all former wills and codicils made by me before or after this Will.',
    'I revoke all future wills and codicils that may be made by me.',
    'I hereby revoke any and all subsequent wills executed by me.',
]


def _will_patterns():
    case = [c for c in load_suite() if c.id.startswith('003')][0]
    return [re.compile(p) for p in case.expect.must_not_match]


def test_correct_revocation_clause_is_not_flagged():
    """
    A Will that expressly disclaims revoking LATER instruments is answering the
    reviewers' finding, not committing it. The original pattern
    `revok\\w*[^.]{0,120}\\b(after|subsequent|future)\\b` flagged exactly this
    clause and cost the draft its entire statute score.
    """
    hits = [p.pattern for p in _will_patterns() if p.search(CORRECT_REVOCATION_CLAUSE)]
    assert not hits, f'correct revocation clause flagged by {hits}'


@pytest.mark.parametrize('clause', DEFECTIVE_REVOCATION_CLAUSES)
def test_the_actual_defect_is_still_caught(clause):
    """Narrowing the pattern must not blunt it."""
    assert any(p.search(clause) for p in _will_patterns()), (
        f'defective clause slipped through: {clause!r}'
    )


# --- executor immunity -----------------------------------------------------
# The third false positive on this fixture, and the same class as the first two.
#
# The original pattern ended `[^.]{0,80}(?!.*good faith)`. That lookahead is
# inert: the quantifier before it is greedy WITH BACKTRACKING, so the engine
# retreats to a shorter match at which "good faith" no longer follows, and the
# pattern fires on every immunity clause — limited or not.

LIMITED_IMMUNITY_CLAUSES = [
    # Real output from the Phase 2 run. This is the reviewers' finding answered.
    'My Executor shall not be liable for any loss to my estate arising from any act '
    'done or omitted to be done in good faith in the honest exercise of the powers '
    'and discretions conferred by this Will, but nothing in this clause shall '
    'exonerate my Executor from liability for any act done in bad faith, wilful '
    'default or gross negligence.',
    'The Executor shall not be liable for any loss save such as arises from her own '
    'wilful default or gross negligence.',
]

BLANKET_IMMUNITY_CLAUSES = [
    'My Executor shall not be liable for any loss or damage whatsoever occasioned to '
    'the estate however arising.',
    'The Executrix shall not be liable for any loss to the estate in any circumstances.',
]


@pytest.mark.parametrize('clause', LIMITED_IMMUNITY_CLAUSES)
def test_limited_executor_immunity_is_not_flagged(clause):
    """A carve-out for bad faith is correct drafting, not the defect."""
    hits = [p.pattern for p in _will_patterns() if p.search(clause)]
    assert not hits, f'limited immunity clause flagged by {hits}'


@pytest.mark.parametrize('clause', BLANKET_IMMUNITY_CLAUSES)
def test_blanket_executor_immunity_is_still_caught(clause):
    """Overbroad immunity with no good-faith limit is the reviewers' finding."""
    assert any(p.search(clause) for p in _will_patterns()), (
        f'blanket immunity slipped through: {clause!r}'
    )


# --- restraint on alienation -----------------------------------------------
# The fourth false positive on this fixture, and the same class again: a
# `must_contain_clauses` entry written as a list of literal phrasings missed a
# textbook restraint because that draft used different word order. A check that
# scores correct drafting as a defect steers the product toward the defect, so
# these are matched as a concept — a negation governing an alienation verb.

RESTRAINED_LIFE_INTERESTS = [
    # Real output from the Phase 2 run.
    'Sunita Mehra shall NOT have the power to sell, transfer, mortgage, charge, '
    'lease for a term exceeding [PERIOD], or otherwise encumber or alienate the said '
    'flat or her life interest therein, it being my express intention that her '
    'interest is limited strictly to a life interest without any power of alienation.',
    'The life tenant shall not sell, mortgage or otherwise alienate the said property.',
    'She shall have no power to alienate the said flat.',
    'The life tenant shall not be entitled to alienate the property.',
]

UNRESTRAINED_LIFE_INTERESTS = [
    'My wife Sunita shall enjoy the said flat for her lifetime.',
    'The flat shall devolve upon my wife for the term of her natural life.',
]


def _alienation_expectation():
    """Just the restraint-on-alienation entry, isolated from the fixture.

    `must_contain_clauses` also carries the wife-predeceases entry; asserting
    against the whole tuple would test both clauses at once and fail for the
    wrong reason.
    """
    case = [c for c in load_suite() if c.id.startswith('003')][0]
    entries = [e for e in case.expect.must_contain_clauses
               if any('alienat' in str(a) for a in ([e] if isinstance(e, str) else e))]
    assert len(entries) == 1, f'expected one alienation entry, found {len(entries)}'
    return tuple(entries)


def _as_sections(text):
    return [{'section_name': 'BEQUEST', 'content': text}]


@pytest.mark.parametrize('clause', RESTRAINED_LIFE_INTERESTS)
def test_a_real_restraint_on_alienation_satisfies_the_check(clause):
    missing = C.find_missing_phrases(_as_sections(clause), _alienation_expectation())
    assert not missing, f'restraint clause reported missing: {clause[:80]!r}'


@pytest.mark.parametrize('clause', UNRESTRAINED_LIFE_INTERESTS)
def test_a_bare_life_interest_still_fails_the_check(clause):
    """Narrowing must not blunt: "for her lifetime" alone is the defect."""
    assert C.find_missing_phrases(_as_sections(clause), _alienation_expectation()), (
        f'bare life interest passed: {clause!r}'
    )


def test_regex_alternatives_are_opt_in_only():
    """A bare string stays a literal substring — no fixture changes meaning."""
    sections = _as_sections('The rate is 5% per annum.')
    assert not C.find_missing_phrases(sections, ['5% per annum'])
    # Regex metacharacters in a literal are matched literally, not compiled.
    assert C.find_missing_phrases(sections, ['5.* annum'])
    assert not C.find_missing_phrases(sections, ['re:5.*annum'])


def test_a_malformed_fixture_regex_reads_as_missing_not_a_crash():
    assert C.find_missing_phrases(_as_sections('anything'), ['re:(unclosed'])
