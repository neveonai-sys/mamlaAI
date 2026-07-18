"""
MamlaAI Chat orchestrator package.

A unified, Claude/GPT-style chat surface that sits on top of the existing
Mamla.AI capabilities (drafting, document intelligence, citation search,
case-companion research) and dispatches to them as callable tools.

Built additively alongside the existing `mamla_brain` v1 chat (`/api/brain/v1/`)
— the v1 endpoints are untouched. This layer lives under `/api/brain/v2/`.

Phase roadmap (see plan `you-have-the-overview-magical-wolf.md`):
  P0  chat shell + data model            <- this package, initial cut
  P1  capability router + tool loop + SSE streaming
  P2  doc-intel + research tools
  P3  citation tools + Bharatiya Nyaya Sanhita statute layer
  P4  model tiers, premium metering, connectors
"""
