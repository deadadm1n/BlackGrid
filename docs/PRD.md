# BlackGrid — Product Requirements Document
**Version:** 0.1 (planning baseline)  
**Status:** Draft for owner review; not implementation authorization  
**Domain:** blackgrid.online  
**Repository:** deadadm1n/BlackGrid  
**Agent runtime:** OpenCode (optional dependency)

## 1. Executive summary
BlackGrid is a unified, self-hosted Minecraft network management platform. One web application provides a public community portal and a secure owner dashboard; a central control plane manages multiple isolated Minecraft instances and a Discord guild. Players can propose and vote on *any Minecraft-related topic*, including provisioning, retiring, or resetting servers, subject to explicit eligibility, capacity, safety, and authorization policies. A ticket system supports AI-assisted investigations and owner escalation. OpenCode augments administration and develops new features through a reviewable, isolated pipeline; it is never required for core operation.

**Central invariant:** OpenCode is a client of BlackGrid, not the controller of its policy or availability.

## 2. Product principles / non-negotiables
BG-001 Unified UX: one product and one source of truth for public site, dashboard, servers, Discord, governance, and tickets.
BG-002 AI-independent: all deterministic functionality remains usable with OpenCode disabled, crashed, or unreachable. No boot-time dependency on AI.
BG-003 Preserve worlds: stopping/retiring a server never deletes its world. Any reset first creates a verified, restorable archive; destructive world/archive deletion is unavailable to AI and governance.
BG-004 No AI privilege escalation: model output is untrusted; deterministic policy and execution gateway mediate every mutation. No model-facing raw host shell, Docker socket, arbitrary RCON, admin database connection, or Discord token.
BG-005 Prompt-injection-resistant design: all player-generated content, Discord content, logs, plugin metadata, and AI-generated artifacts are untrusted inputs. This is risk reduction, not a guarantee of impossible injection.
BG-006 Durable and auditable: votes, tickets, jobs, action authorizations, effects, backups and rollback evidence are persisted with idempotency.
BG-007 Discord is first-class and network-aware, not a chat relay bolted onto a single server.
BG-008 Capacity is configurable from owner dashboard, especially **maximum concurrently active Minecraft servers**; provisioning and storage caps are separate.
BG-009 No breaking the host: resource reservations, isolated instance runtimes, rollback, and host headroom are mandatory.
BG-010 Emergency access: an independent authenticated break-glass path remains when website, Discord, or OpenCode is unavailable.
BG-011 Source-driven changes: changes to security, permissions, governance rules and AI capabilities follow explicit owner-authorized release workflows; AI cannot alter its own guardrails.
BG-012 Discord administrator vote cancellation: any currently verified Discord guild administrator may unilaterally cancel an open community ballot. Cancellation is immediate, final for that ballot, audited and cannot be overridden by voters or AI.
BG-013 Voting duration: every ballot must remain open for at least 24 hours and no more than 72 hours (three days), calculated from the recorded opening time; no shortened or extended ballot outside these limits.
BG-014 Mandatory vote notification: every ballot must produce a Discord announcement when opened, with proposal, scope, voting controls, and exact closing time; notification failures must be retried and surfaced, never silently ignored.
BG-015 World-integrity change gate: before a server-changing operation, record a deterministic SHA-256 manifest of the relevant world folder, produce and validate a restorable snapshot, then repeat the manifest and integrity checks after the changed server starts and reaches a healthy save point. Unexpected changes or validation failures trigger controlled rollback and a public failure reason; legitimate Minecraft writes must not be mistaken for corruption.

## 3. Users and roles
- **Owner (root of trust):** full policy-setting and emergency recovery rights, subject to authentication and break-glass safeguards.
- **Platform operator (optional future role):** delegated server operational rights, no change to security root of trust.
- **Community player:** linked Discord account and Minecraft UUID, ticket creation, scoped proposals/votes, view authorized data.
- **Moderator:** limited moderation and ticket review capabilities.
- **AI/OpenCode:** nonhuman principal with narrowly scoped read tools and explicitly authorized action proposals; never owner-equivalent.
- **System service:** separate service principals for Discord integration, core, supervisor and instance adapters.

## 4. Scope and user journeys
### 4.1 Owner dashboard
The owner can securely log in (passkeys/WebAuthn preferred; robust recovery), inspect every managed instance, see real-time health/player counts/logs, use per-instance console, manage players, plugin/mod installations and configs, worlds/backups, files within safe server-scoped paths, network ports and templates, Discord guild topology, proposals, tickets, audit logs, permissions and policies.
Provide an **explicitly separated** emergency host terminal for owner only, with stronger re-auth and session recording/audit; it cannot be reached by AI or player-facing endpoints.
The owner can directly chat with OpenCode from the dashboard, see plans/tool calls/approvals, and terminate AI sessions.

### 4.2 Minecraft fleet wrapper
Support multiple Minecraft instance types via adapters (Paper, Fabric, NeoForge staged, not assumed interoperable). Each instance is a separately identified resource with type, version, mod/plugin manifest, resource caps, network address, data volumes, world archives and lifecycle state. Reconciliation discovers drift. Configurable limits include max_active_servers, max_provisioned_servers, per-instance RAM/CPU, fleet resource budget, disk reserve and optional player caps.
A server request can be approved yet **queued** until active-server capacity becomes available. All network ports are allocated uniquely. Instances are never silently removed on failure.

### 4.3 Discord first-class controller
One guild can span the network. BlackGrid tracks Discord IDs for guild, roles, channels, and game-instance mapping. Provision a new instance => prepare its scoped channels, status, chat bridge, scoped votes, and access policy; failures lead to repairable partial state and idempotent retries, not duplicates. Guild-wide votes coexist with per-instance votes. Discord API permissions and rate limits are handled, without requiring OpenCode for normal operations. Prevent feedback loops, impersonation and unwanted disclosure in chat bridging.

### 4.4 Community governance
Players can propose **any Minecraft-related change**; eligibility review and policy decide whether it can be balloted and automatically executed. Examples: server creation/type, server retirement/shutdown (not deletion), world reset with preserved snapshot, difficulty, datapacks, plugin request, event, rules, economics. Votes have scope (network / instance), immutable proposal revision at ballot start, electorate snapshot, unique eligible voter identity, timestamps, quorum, threshold, deterministic counting, and immutable outcome. Identity linking and anti-alt/anti-sybil policy are essential; thresholds/quorums/eligibility are **owner-configurable and unset until policy is chosen**. Owner defines which actions are automatically executable, manual-review, or prohibited. Passed-but-unsupported proposal becomes a tracked feature request, not an improvised privileged AI action.

**Ballot timing and notification:** Vote duration is configurable per ballot only within an inclusive minimum of 24 hours and maximum of 72 hours (three days), measured by UTC timestamps; local Discord displays may show viewer-local time. At ballot activation, BlackGrid must durably create and publish a notification to the designated Discord announcement channel for the network or affected server, including the proposal summary, voting link/buttons, eligibility/scope, opening time, and closing time. The notification is mandatory: use a persisted outbox, idempotent delivery, retry/backoff and operator alerts. A ballot must not become open for voting until initial publication is confirmed; if publication fails, keep it `PENDING_ANNOUNCEMENT` and do not start its voting clock. Record the Discord message ID to avoid duplicates. On cancellation, also post a cancellation notification; on closure, publish results. If Discord is offline, drafts and proposals remain usable but new ballots await announcement. No quiet/hidden ballots.

**Discord administrator veto:** Any member holding Discord's actual guild Administrator permission at the time of the action may use a protected `/vote cancel` command or authenticated dashboard control to cancel a vote. Role names alone do not confer this authority. Core must verify the administrator's current guild identity and permission via trusted Discord state, not message text or AI claims. Cancellable votes transition atomically to `CANCELLED_BY_ADMIN`, with optional reason, administrator ID, time, proposal/ballot ID, and an announcement. Closing or tally workers must recheck cancellation inside the same transactional authorization boundary before scheduling execution. Cancelled ballots never authorize actions; cast ballots remain in history. Cancellation is not reversal of an action that has already executed; execution/rollback is a separate owner-controlled workflow. If the vote passed but the resulting action remains queued, the administrator may cancel the *pending vote-authorized operation* before execution begins. If execution has begun, stop only at a declared safe checkpoint and escalate instead of claiming an impossible instant rollback. A vote is never silently erased.

### 4.5 Tickets
Open/triage/needs-info/escalated/resolved/appealed/reopened. Discord private support flows and web dashboard views. Logs/evidence are access-controlled and retention-governed. AI may summarize, correlate data and propose remedies; auto-execution only for allowlisted low-risk actions. Sensitive punishment/ban appeals and disputed facts route to human review. Ticketing persists and manual workflow operates with OpenCode off.

### 4.6 OpenCode AI integration
OpenCode runs as an isolated optional service. Core owns auth, authorization, resource registry, durable job queue and state. Dashboard AI chat is proxied by core; OpenCode is never exposed publicly. Supply typed read-only tools for current fleet, metrics, logs (redacted), Discord channel metadata, governance state, tickets as authorized, and capability registry. All changes go via `propose_action` with structured parameters, identity and scope; core independently validates against policy and proof of approval before execution. AI can plan unsupported feature development in an isolated checked-out workspace, run tests and produce a change set for human-reviewed deployment. No self-updating policy enforcement, unrestricted runtime exec, direct production credentials or autonomous security-policy changes.

## 5. Architecture and service boundaries
**Unified product, modular monolith control plane; isolated processes only where fault isolation requires it.**
- `apps/web`: public web and authenticated dashboard (e.g. Next.js/TypeScript), accessible routes separate and least-privilege.
- `apps/core`: authenticated API, resource registry, governance, tickets, authz/policy, audit and job state (e.g. Python/FastAPI).
- `services/supervisor`: independently running host operator with a *fixed* allowlisted interface, credentials separate from API; owns instance lifecycle, resource admission, snapshot/restore and health actions.
- `services/discord`: bot worker handling Discord API and interaction verification; uses core APIs and durable events.
- `services/ai-adapter`: optional OpenCode gateway / session manager; no startup dependency for core.
- `adapters/minecraft`: versioned adapters for Paper/Fabric/NeoForge, plus compatible in-game bridge modules; fail closed on unsupported operations.
- `packages/contracts`: versioned schemas for all control-plane operations/events.
- `PostgreSQL`: transactional system of record; durable job/outbox tables. Redis only as optional transient transport, never sole source of truth.
- `runtime`: per-instance isolation, explicit storage volumes, network boundaries, resource limits, locked down credentials.
- `proxy`: Velocity when multi-instance player routing is desirable, optional in first milestone.

### Essential security boundary
`Owner UI / Discord / OpenCode -> Authenticated Core API -> Policy Decision -> Durable Action -> Restricted Supervisor/Adapter -> Minecraft or Discord`.
Never let a bot or agent address Docker/socket, system shell or raw instance internals directly. Console input from owner is a distinct, high-trust route requiring explicit server selection, re-auth and audit. A request from Discord chat is *not* a console command.

## 6. Resource and data model (initial)
- `users`, `identities` (Discord snowflake and Minecraft UUID), `role_assignments`, `sessions`, `service_principals`
- `minecraft_instances`, `instance_templates`, `instance_allocations`, `instance_ports`, `instance_configs`, `instance_modules`
- `worlds`, `snapshots`, `backup_verifications`, `restore_jobs`
- `discord_guilds`, `discord_resources`, `instance_discord_mappings`, `chat_bridge_routes`
- `proposals`, `proposal_revisions`, `ballots`, `electorate_snapshots`, `votes`, `vote_results`, `vote_cancellations`, `governance_policies`
- `tickets`, `ticket_messages`, `ticket_evidence`, `ticket_events`
- `operations`, `operation_approvals`, `action_policies`, `jobs`, `outbox_events`, `audit_events`
- `capabilities`, `ai_sessions`, `feature_requests`, `release_candidates`
All records carry stable IDs, provenance, timestamps and appropriate state/versioning. Never persist secrets in audit or AI transcripts.

## 7. Lifecycle and workflows
### Server states
`REQUESTED -> APPROVED -> QUEUED | PROVISIONING -> CONFIGURING -> VALIDATING -> STOPPED | RUNNING`.
Operational transitions: `RUNNING -> STOPPING -> STOPPED -> ARCHIVED`; failures enter `FAILED` with explicit repair/retry. `ARCHIVED` is reversible, not deletion. Define legal transitions in code and test them.

### Governance states
`DRAFT -> DISCUSSION -> ELIGIBILITY_REVIEW -> PENDING_ANNOUNCEMENT -> BALLOT_OPEN -> PASSED | REJECTED | INVALID | CANCELLED_BY_ADMIN -> SCHEDULED -> EXECUTING -> COMPLETED | FAILED | BLOCKED`. `CANCELLED_BY_ADMIN` is terminal for the ballot; queued vote-authorized execution can be separately revoked before it begins. Approval binds a specific proposal revision, scope, parameters and expiration. A passed ballot alone never bypasses current capacity or policy.

### Provisioning saga
Reserve capacity/port -> prepare storage -> create isolated instance -> validate startup/health -> create/reconcile Discord resources -> publish. Each step persisted with idempotency keys. On error release reservations where safe and retain potentially valuable instance/world data. Retries must not create duplicate channels or instances.

### World-integrity change gate (before/after startup)
Every *server-changing operation* initiated by the owner, governance, or AI uses a protected before/after world-integrity check. The goal is to detect unexpected world modifications or corruption **caused by a change**, not to require a world folder to remain byte-identical while Minecraft runs.

1. **Preflight:** Lock changes on the instance, safely flush/quiesce world writes, then record a deterministic SHA-256 manifest of all relevant world-folder files (normalized relative paths, file sizes and file hashes, sorted) and a root manifest digest. Capture a consistent, restorable backup of worlds and relevant configuration/player/plugin state. Verify archive integrity, independent storage, and at least structural Minecraft world checks before proceeding.
2. **Apply:** Record an explicit expected-change scope (e.g. plugin config vs planned world reset). Perform the approved change. Start the server and require successful process startup, service readiness, world load and stability checks. Prevent normal players joining until the validation gate passes when feasible.
3. **Postflight:** At the first stable save point, flush/quiesce world writes and compute the same deterministic manifest; compare it with the baseline to identify unexpected additions, removals, or changes. Perform Minecraft-specific checks of NBT/region structure, load errors and other indicators. Hash differences *alone* do not prove corruption: Minecraft naturally updates world files on boot, so the validator must distinguish expected writes from anomalous changes and surface uncertainty.
4. **Success:** Only mark the operation complete and expose the changed server normally if health, scope-aware manifest comparison, and world validation pass. Store pre/post manifests, validation results and audit records. Optional post-change recovery snapshot follows successful validation.
5. **Failure:** If preflight backup/validation fails, reject the proposed execution without mutation. If postflight fails, put the instance in maintenance, stop it safely, preserve evidence and the failed state where feasible, and automatically restore the last verified pre-change backup **only if the restore preconditions and procedure are safe and validated**; otherwise alert the owner and keep the instance stopped for manual recovery. Verify restored world health before reopening access. Never overwrite or discard the failed state without preserving recovery evidence.
6. **Governance outcome:** A previously passed community vote remains historically **PASSED**, but its associated implementation is marked `FAILED_INTEGRITY_CHECK` / `ROLLED_BACK` (or `RECOVERY_REQUIRED`), not retroactively changed to rejected. Post a Discord notification explaining which integrity or startup check failed, what rollback occurred, and whether admin action is required. No repeated automatic attempts without reevaluation/approval.
7. **Reliability:** File hashing must operate on a consistent snapshot, not during live writes. Record pre/post root SHA-256 and per-file hashes; do not compare ZIP byte hashes against each other as a corruption test. Run corrupted-region, expected-write, failed-restore, resource-exhaustion and simultaneous-change tests. Backup capacity must be checked before beginning.

**Acceptance:** A harmless server restart doesn't trigger a false corruption alarm solely because map files changed. A corrupted or unreadable world, missing critical files, startup failure or change outside allowed scope is detected. A vote-authorized deployment that fails is safely reverted when possible and a reason is posted publicly. A failed restore never silently reports success.

### World reset
Quiesce instance -> create immutable world snapshot -> verify snapshot readability/restore test as policy dictates -> generate new world -> verify -> restart. Rollback restores previous world while preserving a snapshot of the replacement; no data wipe.

## 8. Security, resilience and privacy requirements
- Web auth: secure cookies, CSRF protections, strict server-side RBAC/ABAC, WebAuthn and recovery controls, request throttling, audit.
- Network: internal-only OpenCode and supervisor; minimal exposed endpoints, TLS, secure Discord interaction verification, short-lived service credentials.
- Sandbox: non-root containers, CPU/RAM/PID/IO caps, per-instance file scopes, no privilege escalation, no general network reachability without need. Untrusted plugins/mods are executable code: compatibility and provenance review, allowlisting and isolation are required.
- Prompt injection: taint external text; strongly delimit tool context, typed tool schemas, independent policy enforcement, permission scoping, adversarial tests. Cannot guarantee no injections; guarantee no privilege follows from the text alone.
- Backups: separate protected backup storage, retention policy for critical world assets, monitored capacity, periodic restore proof, restricted deletion privileges outside AI/governance.
- Disaster: management access through independent local recovery; platform can be restored from backed-up DB/config/volumes without OpenCode.
- Owner-controlled website replacement: existing blackgrid.online deployment can be superseded; take config/credential/data inventory first, no irreversible cutover in PRD phases.
- Privacy: Discord player messages and tickets are sensitive; use minimal collection, access controls, redaction, retention and transparency; avoid collecting unnecessary private DMs.

## 9. Phased delivery plan (each phase: deliver + acceptance)
### P0 — Repository and specification freeze
**Deliver:** documented architecture, threat model, contracts, ADRs, data model, contributor/agent instructions and risk register.
**Acceptance:** no ambiguous security boundary; OpenCode can identify precisely which modules may touch host, Discord and game APIs; reviewable incremental work items.

### P1 — Core foundation
**Deliver:** unified app scaffold, protected dashboard/login, DB+migrations, RBAC, audit, configuration, durable jobs/outbox, minimal read-only health API.
**Acceptance:** unauthorized requests blocked at API; startup without OpenCode; audit and job state survive restarts; automated tests pass.

### P2 — Supervisor and server lifecycle
**Deliver:** container isolation, capacity policy and max_active_servers dashboard control, provision/start/stop/archive/restore one Paper instance, health/logs/owner console, safe backups.
**Acceptance:** cannot exceed cap under concurrent requests; preserve world during stop/archive; restart core/worker does not duplicate instance; restore test passes.

### P3 — Multi-instance and Discord
**Deliver:** second Paper instance, adapter contracts and compatibility tests, Discord bot connection, scoped channel provisioning, chat bridge, reconciliation.
**Acceptance:** both instances independent; creating instance creates expected Discord resources exactly once, retries safe; system runs with Discord offline; shutdown never wipes data.

### P4 — Governance
**Deliver:** identity link, anti-alt policy, proposal/discussion/ballot/tally flow, scope and action gating, post-vote job creation.
**Acceptance:** duplicate and ineligible votes rejected; exact ballot snapshot and quorum rules preserved; passing stop-server vote archives safely; blocked proposals cannot execute. A verified Discord Administrator can cancel an open vote instantly, with public notice and durable audit; a non-admin or AI cannot; closing/cancellation races cannot accidentally authorize execution; a queued action can be revoked before start. All ballots use 24–72 hour durations, reject invalid ranges, announce successfully before opening, do not duplicate notices on retry, and publish cancellation/result notices.

### P5 — Tickets and moderation
**Deliver:** ticket channels/web views, role-scoped visibility, audit, reopen/appeal, manual resolution.
**Acceptance:** no cross-user leakage, operation without AI, evidence provenance and access tests.

### P6 — OpenCode integration
**Deliver:** dashboard chat, isolated OpenCode sessions, typed read tools, action proposal approvals, redaction, health degradation UX.
**Acceptance:** pull OpenCode down during operations; everything in P1-P5 still works. Injection tests cannot trigger unapproved operations. No direct shell/host access by OpenCode.

### P7 — Feature-development automation
**Deliver:** capability registry, isolated development environment, tests, artifact signing or provenance, change-review and release/rollback.
**Acceptance:** AI-generated code cannot self-deploy to production or modify policy root; owner can inspect and approve release; rollback restores prior stable release.

### P8 — Production hardening and launch
**Deliver:** monitoring/alerting, recovery drills, performance/load tests, docs, website replacement plan and cutover.
**Acceptance:** disaster recovery from clean host documented and verified; provisioning, voting, tickets and server uptime remain functional without AI; no destructive data loss in test scenarios.

## 10. Release gates and global acceptance tests
1. AI-off test: disable OpenCode for 24h in staging; all deterministic workflows work.
2. Injection test: malicious Discord/chat/book/ticket/log strings cannot produce unauthorized supervisor, console or Discord admin calls.
3. Capacity race: 20 simultaneous votes/provision attempts cannot exceed configured active cap.
4. No deletion: attempt to retire/stop/reset any instance; preserved snapshots and world state recoverable; AI cannot access deletion mechanisms.
5. Discord retry: partial success followed by retry creates no duplicate channels/roles and preserves binding IDs.
6. Restart chaos: kill/restart core, workers and Discord during a job; jobs resume idempotently.
7. Security review: every mutation requires server-side identity, scope, policy and audit.
8. Restore drill: recover core DB, world data and Discord resource registry into a clean staging environment.
9. Version compatibility: unsupported mod-loader features fail with clear capability errors, never silently run Paper-specific commands.
10. Deployment rollback: broken release recovers without OpenCode.
11. World-integrity gate: every server-changing operation records a consistent pre-change world-folder hash manifest and validated rollback backup, then a post-start manifest and world-health check; unexpected changes fail the operation, trigger safe rollback when possible, and notify Discord with the reason. Normal startup writes do not cause automatic false positives.

## 11. Explicitly deferred / open decisions
- Exact server hardware, per-instance resource presets and owner-set defaults.
- Exact governance voter eligibility, thresholds, quorum, discussion duration, cooldowns and owner veto/emergency procedures.
- Ownership/auth provider, domain DNS and ingress/certificate details.
- Plugin/mod distribution policy and legal terms; player data retention and Discord server requirements.
- Whether to operate Velocity on day one; allowed Minecraft version range and modloader versions.
**Do not invent final values for these.** Implement safe configuration with explicit validation and deployment defaults marked as provisional.

## 12. Definition of first production-credible milestone
From blackgrid.online, owner signs in, creates two isolated Paper instances subject to a dashboard-set concurrent cap, monitors both, manages a console and backups, stops/archives/restores one without deleting its world, and Discord channels/chat bindings are created exactly once. All persists and operates with OpenCode absent. Governance and tickets follow as separate acceptance-gated phases.
