# BlackGrid — Architecture and data boundaries

**Status:** planning baseline; implementation details subject to design review.

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