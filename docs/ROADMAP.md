# BlackGrid — Delivery roadmap and release gates

**Status:** draft implementation sequence; requires reconciliation with later approved capabilities before OpenCode implementation.

## 9. Phased delivery plan (each phase: deliver + acceptance)
### P0 — Repository and specification freeze
**Deliver:** documented architecture, threat model, contracts, ADRs, data model, contributor/agent instructions and risk register.
**Acceptance:** no ambiguous security boundary; OpenCode can identify precisely which modules may touch host, Discord and game APIs; reviewable incremental work items.

### P1 — Core foundation
**Deliver:** unified app scaffold, protected dashboard/login, DB+migrations, RBAC, audit, revisioned live settings registry and initial permission-gated settings UI, durable jobs/outbox, minimal read-only health API.
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
**Deliver:** dashboard chat, isolated OpenCode sessions, typed read tools, action proposal approvals, redaction, health degradation UX, live AI autonomy/budget matrix with immediate policy enforcement and audit.
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
13. CurseForge/spark integration: valid game-version and loader matching, dependency handling, source provenance, and profiler compatibility detection; neither integration is a hard dependency for BlackGrid startup.
12. Sentinel gate: a change fails safely when an isolated test instance crashes or detects bad world data, and production is not mutated; a missing resource budget yields an inconclusive/unavailable result rather than a fabricated pass.
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