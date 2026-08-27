# Frontend Style Reference (Anthropic)

> Implemented in `frontend/` as a dependency-free interface served by FastAPI
> at `/`. It consumes `/ingest`, `/query`, `/sources`, and `/health` directly.

Key tokens to apply when the frontend is built:

- Canvas `#f0eee6`, cards `#faf9f5`, featured `#f5e3c7`, text `#141413`.
- Single accent (Clay `#d97757`) reserved for the primary action only.
- Serif (`Anthropic Serif`, fallback Georgia) for body at 20px; sans for UI chrome.
- Card radius 24px; filled buttons use bottom-only 8px radius; no shadows —
  elevation via surface tone + 1px `#cccbc8` borders.
- Persistent underlines on inline links.

The implementation also includes responsive layouts, keyboard submission,
accessible live regions, reduced-motion support, loading/error states, source
match cards, and clickable inline citation labels.
