# Frontend Style Reference (Anthropic) — saved for the frontend phase

> The frontend is intentionally NOT built in this deliverable (see requirement
> 21). This file preserves the provided Anthropic visual style so the separate
> frontend prompt can consume it. The backend exposes clean, typed APIs
> (`/ingest`, `/query`, `/sources`, `/health`) documented at `/docs` for that
> frontend to call.

Key tokens to apply when the frontend is built:

- Canvas `#f0eee6`, cards `#faf9f5`, featured `#f5e3c7`, text `#141413`.
- Single accent (Clay `#d97757`) reserved for the primary action only.
- Serif (`Anthropic Serif`, fallback Georgia) for body at 20px; sans for UI chrome.
- Card radius 24px; filled buttons use bottom-only 8px radius; no shadows —
  elevation via surface tone + 1px `#cccbc8` borders.
- Persistent underlines on inline links.

The full brand spec provided by the user should be pasted alongside the frontend
prompt when that phase begins.
