"""
ai_draft.drafting — the Indian-legal-drafting quality layer.

Modules land in phases (see plan `the-chat-interface-we-curious-volcano.md`):

  checks.py          deterministic primitives shared by the validator and the
                     eval rubric — statute misuse, truncation, missing phrases,
                     dropped instructions.  (Phase 0)
  classify.py        user query -> DraftContext(doc_type, branch).  (Phase 1)
  playbooks/         per-document-type skeleton, conventions, statute
                     allow/deny lists, pitfalls.  (Phase 1)
  prompt_builder.py  the single source of truth for every drafting prompt,
                     replacing the four duplicated inline prompts.  (Phase 1)
  draft_validator.py JSON repair ladder + post-generation linting.  (Phase 2)
  exemplars.py       structural precedent retrieval from draftdocs/.  (Phase 4)

Nothing here performs I/O or imports Django at module scope, so the primitives
stay unit-testable without a settings module.
"""
