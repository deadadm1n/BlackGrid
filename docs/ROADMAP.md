# BlackGrid — Reconciled delivery roadmap

**Status:** implementation-ready sequencing proposal, NOT authorization to code/deploy. All phases require owner approval and acceptance tests. See [PRD](PRD.md), [DECISIONS](DECISIONS.md) and [CONTRACTS](CONTRACTS.md). This replaces the obsolete ordering where website governance and AI Discord administration were implicit.

## Delivery principles
- First build one deterministic, secure Core; Discord, web and optional AI are adapters to it.
- Ship independently testable vertical slices, not feature lists that cannot be used until P8.
- Run automatic tests plus real runtime exercises for every phase. Never claim environmental tests passed when unavailable.
- No live blackgrid.online cutover, guild-wide reorganization, real player votes or THE HUNT implementation without explicit owner go-ahead.
- Open design settings become safe, disabled or setup-required state instead of invented rules.
- Maintain separation of approval for concept, development, test, release and deployment.

## P0 — Specification and architecture freeze (next)
**Deliver:** normalized authority matrix; final technical stack ADRs; versioned Core↔Web/Discord/Supervisor/AI schemas, database migrations, threat model, instance topology, capacity policy, explicit defaults/unknowns, issue tracker and phased acceptance matrix. Review this roadmap against each canonical subject spec; clean orphaned references, numbering and inconsistent requirements.
**Gate:** no critical ambiguity in who authorizes operational actions; unanswered product decisions recorded and surfaced for owner confirmation. Approval to implement P1 is separate.

## P1 — Core, identity, security and live configuration
**Deliver:** Core API, Postgres, secure sessions, Discord OAuth2-only community login, rules version acknowledgement, linked Minecraft identity scaffolding, global scoped RBAC/ABAC, audit, durable jobs/outbox, revisioned live settings engine and dashboard shell with permission editor/autonomy matrix (controls may be disabled until AI connected).
**Gate:** no unauthorized mutation, grant/deny preview, rollback of configuration changes, settings update propagation without routine restart, crash-safe outbox, Core runs without AI. Owner-only recovery channel independent of Discord/community OAuth.

## P2 — Minecraft supervisor and recovery foundation
**Deliver:** isolated Paper instance adapter, provision/start/stop/retire, resource admission, backups/snapshots, integrity manifests, restore proof, health/console/metrics, capacity controls in live dashboard, independent supervisor contract.
**Gate:** single instance lifecycle survives service restart, world never silently deleted, resource races cannot oversubscribe, recover from tested backup; owner-only console access audited.

## P3 — Discord administration, onboarding and network integration
**Deliver:** first-party bot, rule acceptance, scoped guild/channel/role mapping, initial channel templates, chat relay, Discord worker outbox and reconciliation, moderation service, permissions/AI action gating interface (AI need not be online), second Minecraft instance, automatic channel provisioning on approved server creation.
**Gate:** no duplicate channels on retries, bot hierarchy errors explained, privileged intents handled, private channel access respected, Core works when Discord disconnects, admin cannot be impersonated by chat text.

## P4 — Community governance on Discord AND web
**Deliver:** proposal forum, website browser/detail/forms, discussions/comments with scoped bidirectional synchronization, advisory/development/implementation ballots, immutable rounds, edits and attributed constraints, fresh 24/48/72-hour announcements, admin cancellation, electorate checks, deduped cross-surface voting, results/history, impact assessments.
**Gate:** must pass all voting race, timer reset, outage, role/rules eligibility and privacy tests in [CONTRACTS](CONTRACTS.md). **First intended owner-run manual governance test is THE HUNT proposal; this does not create its gameplay server.**

## P5 — Community work, support and accountability
**Deliver:** tickets, moderation appeals, community project board from successful votes, dependency and impact reporting, public progress statuses, notification preferences and events; independent policy and project lifecycle automation.
**Gate:** community can trace an approved proposal into work or an explicit blocked state, no private leakage, ticket operations function without OpenCode.

## P6 — AI co-administrator and operational memory
**Deliver:** OpenCode gateway with typed tools, bounded memory and durable task loop, review/investigation workflows, Discord read/write/moderation capability through Core, user-facing AI identity, live adjustable autonomy modes/budgets, incident alerts in dedicated Discord channel, suspended/paused AI behavior.
**Gate:** model cannot get bot token, host shell, self-extend privileges or bypass policy; a dashboard autonomy downgrade takes effect for the next action; simulated prompt injections fail; governance and server operations remain healthy without OpenCode.

## P7 — Autonomous development and experimental lab
**Deliver:** versioned custom plugin source registry, CurseForge compatible discovery, update plans, Sentinel micro-server tests, dependency graph, packaged artifact verification, bounded staging/simulation experiments, approval and rollback process for AI-produced extensions.
**Gate:** no unsigned/unreviewed live code, incompatible mods blocked, performance and world-integrity evidence tracked, failed experiment cannot corrupt live servers. THE HUNT is not automatically scheduled or built by this phase.

## P8 — Resilience, product hardening and controlled launch
**Deliver:** end-to-end recovery drills, incident management, telemetry/analytics and privacy controls, reliability and load tests, documented installation wizard, migrations, production security review, domain/ingress setup and owner-approved website/guild rollout plan.
**Gate:** disaster recovery tested from clean host; world restore demonstrated; platform stable across core/Discord/AI restarts; alerts reach authorized operators; owner explicitly authorizes production cutover.

## Cross-phase acceptance matrix
- **Identity/security:** wrong account/scope, rule unaccepted, stale privilege and Discord role race must all fail closed.
- **Settings:** live policy propagation, optimistic conflicts, denied AI authority escalation, protected break-glass.
- **Voting:** time bounds, mandatory Discord announcements, multiple edits, resets, cancellation races, one unique linked voter/round.
- **Server safety:** backed-up state, world-health validation, Sentinel, capacity contention, staged rollback and audit.
- **AI:** offline path, incident escalation and budget exhaustion, revoked authorization, injection resistance.
- **Product:** accessible public proposal UX, deterministic Discord/web synchronization, mobile UI, project provenance and notifications.
- **Recovery:** process restarts, Discord outage, storage-full, dead-letter queues, restore evidence and no silent deletion.

## No silent policy selection
Open parameters are enumerated in [DECISIONS.md](DECISIONS.md). Operators configure valid values via dashboard when supported; undefined values never cause surprise automatic deployment. A temporarily disabled feature is preferable to a guessed sensitive authorization policy.

## Cross-phase integration — organization, Bridge and modpacks

- **P0:** include [organization/rank model](ORGANIZATION_AND_PERMISSIONS.md) and [Bridge protocols](BLACKGRID_BRIDGE.md) in security ADRs, permissions schemas, command collisions/interop studies, mod license review and contract tests.
- **P1:** rank-tab editor, scopes/inheritance, owner/Deadhead/AI/moderator/server-admin/backend role templates; Core-linked Discord/Minecraft identity foundation.
- **P2:** Minecraft Bridge's Paper server-side handshake, health, secure event adapter, and basic command capability detection; server runs when Core/AI unavailable.
- **P3:** scoped bidirectional per-instance Discord chat, staff relay, linked identities, duplicate prevention, announced modpack release channels. Fabric/NeoForge bridge compatibility per adapter readiness.
- **P4:** in-game linked governance commands using same Core ballot, outage pause behavior, quorum and vote privacy as website/Discord.
- **P5:** in-game report/appeal/authorized staff commands and case routing to two network moderators, admins and Deadhead; optional Essentials-like player utilities avoiding collisions.
- **P6:** role-limited `/bg ask`, AI operational investigations and spark diagnostics; AI permissions live in rank dashboard.
- **P7:** validated per-server client modpack publication on website, compatible Minecraft/loader builds and idempotent Discord changelogs; controlled updates through isolated testing and owner-defined release gates.
- **P8:** cross-platform/offline/failed-sync tests, modpack deployment/rollback drills, client download accessibility and license provenance.

**No phase authorizes construction of THE HUNT, Discord guild mutation or website cutover without owner approval.**

## P0 consolidation reference

[DECISIONS.md](DECISIONS.md) is the consolidated approved-policy register; [PERMISSION_REGISTRY.md](PERMISSION_REGISTRY.md) provides proposed granular permission keys (not approved role grants); [STATE_MACHINES.md](STATE_MACHINES.md) defines voting, incident, Bridge and release lifecycles; [P0_REVIEW_CHECKLIST.md](P0_REVIEW_CHECKLIST.md) is the review exit gate. No new implementation authority is granted by these links.
