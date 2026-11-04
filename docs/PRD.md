# BlackGrid — Product Requirements Document

**Status:** Planning / owner review — **NOT implementation authorization**  
**Repository:** `deadadm1n/BlackGrid`  
**Domain:** `blackgrid.online`  
**AI runtime:** OpenCode, optional for deterministic core operations

> This is the master entry point. Detailed requirements now live in subject-specific files. The full pre-refactor PRD is preserved [verbatim](PRD_LEGACY_REFERENCE.md) for verification. Do not use that archived copy as a competing active specification.

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
BG-017 CurseForge API: BlackGrid Core provides a first-party CurseForge catalog client for modpacks, mods, files, compatibility, dependencies and update discovery. Provider access configuration is supplied at deployment; account registration/onboarding is outside this PRD, and API responses do not bypass installation security checks.
BG-018 spark profiling: spark is the primary supported deep-performance profiler wherever a compatible build or bundled distribution exists; the runtime detects compatibility and reports unsupported cases rather than assuming all versions work.
BG-019 Automated updates and custom extensions: BlackGrid manages compatible automatic updates and first-party AI-assisted plugins, with provenance, dependency resolution, isolated Sentinel validation, scheduled production rollout, verified backups and rollback; update policy is configured per instance and no update bypasses the action gateway.
BG-020 Community feature development: BlackGrid must search existing compatible solutions before creating a custom OpenCode development project for a player-requested plugin, mod, datapack, or server feature. Approved projects remain tracked, sandboxed, tested, and subject to independent deployment authorization.
BG-016 BlackGrid Sentinel: any proposed instance software/configuration change must be tested first against a disposable, isolated, player-inaccessible validation instance using a consistent copy of relevant world and server configuration. Sentinel measures startup, world validity, logs, compatibility, resource use and performance using deterministic checks; OpenCode is optional for interpretation. Test worlds never replace production directly and failed tests do not mutate production.

## 3. Users and roles
- **Owner (root of trust):** full policy-setting and emergency recovery rights, subject to authentication and break-glass safeguards.
- **Platform operator (optional future role):** delegated server operational rights, no change to security root of trust.
- **Community player:** linked Discord account and Minecraft UUID, ticket creation, scoped proposals/votes, view authorized data.
- **Moderator:** limited moderation and ticket review capabilities.
- **AI/OpenCode:** nonhuman principal with narrowly scoped read tools and explicitly authorized action proposals; never owner-equivalent.
- **System service:** separate service principals for Discord integration, core, supervisor and instance adapters.

## 4. Authoritative subject specifications

- [WEBSITE.md](WEBSITE.md): Discord-only community login, proposal portal, full owner dashboard, live settings/autonomy controls, identity and additional capabilities.
- [DISCORD.md](DISCORD.md): Guild organization, Discord first-class integration, bot Administrator capability and AI operations through Core policy.
- [GOVERNANCE.md](GOVERNANCE.md): Rules acceptance, proposal editing and ballot resets, scoped permissions, AI-originated proposals, discussions, voting and tickets.
- [MINECRAFT.md](MINECRAFT.md): Instance fleet, CurseForge/mod/plugin lifecycle, custom development, capacity controls.
- [AI_SYSTEM.md](AI_SYSTEM.md): Optional co-administrator, durable work cycles, memory, evidence and bounded autonomous initiatives.
- [ARCHITECTURE.md](ARCHITECTURE.md): Service boundaries, resource and data model, deterministic control plane.
- [OPERATIONS.md](OPERATIONS.md): Instance lifecycle, Sentinel, world integrity, recovery and operational workflows.
- [SECURITY.md](SECURITY.md): Authentication, authorization, sandboxing, privacy, backups and protected boundaries.
- [ROADMAP.md](ROADMAP.md): Delivery phases, release gates, open implementation dependencies and milestones.
- [DECISIONS.md](DECISIONS.md): Approved, open and prohibited decisions; **do not invent values for open choices**.
- [THE HUNT — Experiment 001](experiments/THE_HUNT_PROPOSAL.md): Research and **future owner-submitted manual Discord voting test only**; no build or automatic post.

## 5. Cross-cutting decisions to honor

BlackGrid exists for its players. Community gameplay changes generally pass through scope-appropriate votes; Deadhead is the designated community dispute authority, distinct from owner-only infrastructure/emergency authority. AI may present technical disagreement and evidence but cannot unilaterally bypass authenticated authorization or disable the community's chosen governance rules. Serious incidents are reported in a dedicated dashboard-configurable Discord channel; predetermined response policy applies during emergencies.

Every ordinary BlackGrid setting should be adjustable in the live dashboard where technically feasible, including granular AI autonomy; settings requiring staged deployment/restart must show pending status. Discord and website use one canonical proposal, identity and ballot service. Every authorized formal proposal edit supersedes the round, invalidates earlier votes for the current tally and restarts the full timer **after** Discord publication.

The Discord bot may have guild Administrator capability for AI-driven operations, but core action authorization, role hierarchy, audit and protected resource controls remain mandatory. Neither a passed concept vote nor AI autonomy waives Sentinel, world preservation, security and owner release gates.

## 6. Remaining design and refactor work

The documents above preserve the previous requirements but are not yet an executable implementation specification. Before OpenCode implementation, reconcile the roadmap against all newly accepted features, define versioned API/events/schemas, threat model and deployment topology, resolve or explicitly parameterize open choices, and add cross-spec integration tests. Keep one canonical subject home for each requirement; update [DECISIONS.md](DECISIONS.md) when decisions change. Never silently reinterpret open questions as approval.

**No deployment, Discord modification, chicken server creation or autonomous development is authorized by this documentation change.**
