"""
ai_draft.evals — the measurement instrument for drafting quality.

The intern benchmark scored our rent-arrears legal notice 3/10 against
Jhana.ai's 7/10. That number came from a human reading four drafts. This
package turns it into something a build can assert.

Two scorers:

  score_deterministic — pure functions over the parsed draft (see
      `ai_draft.drafting.checks`). Zero LLM calls, zero cost, runs in CI.
      On its own it catches all four documented defect classes, because each
      one is a structural fact about the text rather than a matter of taste.

  score_judge — one model call against a rubric, for the qualities that are
      genuinely judgement calls: does it read like an advocate wrote it.
      Costs money; run manually and pre-release. (Phase 5.)

Run it:

    python manage.py eval_drafts --suite all --record     # real calls, costs money
    pytest Legalv1/tests/test_draft_evals.py              # recorded fixtures, free

The `--record` run against unmodified code is the documented baseline. Every
later phase re-runs the same suite, so "3/10 -> X" is a table, not an anecdote.
"""
