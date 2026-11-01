# BlackGrid — OpenCode Agent Handoff
**Status:** Instructions for staged implementation; begin only after owner approves phase P0/P1.

## Read in order
1. `docs/PRD.md` — source of truth on product outcomes and non-negotiables.
2. `docs/OPEN_CODE_HANDOFF.md` — implementation protocol.
3. `README.md` — high-level overview (PRD wins on conflict).
4. Existing source, tests and migration history before editing.

## Your mission
Build a **unified, AI-optional** Minecraft management platform, not an AI bot running a server. One authenticated core API owns policies; Discord, dashboard, supervisor, OpenCode and Minecraft adapters are clients/workers.

## Hard prohibitions
- Do not deploy to blackgrid.online or replace its site until owner-approved cutover.
- Do not delete or overwrite an existing world, archive or backups.
- Do not let AI tools obtain shell, Docker socket, unrestricted RCON, admin database credentials, or Discord token.
- Do not merge model reasoning with access control. No natural-language approvals.
- Do not grant permission to auto-apply self-developed code, modify core security policy, or manipulate election results.
- Do not assume Paper, Fabric and NeoForge share a plugin API.
- Do not build core features that require OpenCode online.
- Do not implement destructive 'cleanup' commands for player worlds.

## First assignment: planning review only
Before coding, inspect repository and return:
1. PRD consistency gaps and proposed ADRs.
2. Proposed monorepo structure with service boundaries.
3. Concrete database schema and lifecycle diagrams.
4. API/tool contracts for: server inventory, capacity change, provision, stop, archive, snapshot, Discord resource reconciliation, vote authorization, ticket and AI action proposal.
5. Threat model: Discord interactions, game chat/books, plugin supply chain, prompt injection, console, SSRF, auth and persistence.
6. Phase P1 implementation plan with tests, migrations and rollback.
Do not silently redefine requirements. Record questions and unresolved parameters in `docs/decisions/`.

## Implementation work protocol (after owner approval)
- Implement one phase at a time on a separate branch/PR; small reviewable changes.
- Each phase PR includes goals, design choices, schema migrations, tests, security impact, rollback plan and demo steps.
- Tests must prove both normal and fail-closed paths, including OpenCode offline.
- Configuration and secrets must be externally supplied; no committed credentials.
- APIs use versioned request/response schemas and idempotency keys for operations.
- All administrative mutations are audited and checked against server-side policies.
- If an acceptance test fails, do not call the phase complete.
- For unknown settings: choose safe disabled defaults or document the decision instead of inventing production policy.
- Keep PRD and ADRs in sync when an approved design decision changes.
