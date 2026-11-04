# BlackGrid — Endgame organization and permission design

**Status:** owner-approved organizational direction with proposed role templates; permission defaults, conflict arbitration details, and any executable privileges require explicit configuration. **Documentation only.**

## Operating scenario
Design for about **300 members, eight active Minecraft server communities, one designated admin per server, two network-wide moderators, one AI administrator, Deadhead as final ordinary community authority, and owner as infrastructure root authority.** Counts are scenario parameters, never hard limits. Backend operators/developers may be assigned independently of community hierarchy. Example server names (Survival, Anarchy, Kingdoms, Modded, Creative, Hardcore, Events, Experimental) are illustrative, not mandatory.

## Accountability and jurisdiction
- **Owner:** protected infrastructure authority, global policy administration, safe recovery, production release authority and appointments as configured. Owner recovery access must not rely exclusively on Discord availability.
- **Deadhead:** highest ordinary community authority; handles unresolved moderation/appeal/staff disputes, community staff oversight, not automatic host/database root.
- **AI Administrator:** persistent, network-wide coordinator for monitoring, investigations, help, maintenance, development and incident triage. Core enforces per-action grants, scope, autonomy mode and budgets. Cross-team visibility is not unrestricted authority.
- **Two network moderators:** equivalent network-scoped role by default; handle cross-server reports, spam, appeals and staff escalation, respecting each server's rules. Cases assigned by availability and workload. No implied server shell or deployment.
- **Eight scoped server administrators:** each holds administration **only** for explicitly assigned server IDs. Local events, moderation, gameplay policy coordination, player support, operational read access and approved change requests. No implied host control, another instance's bans or arbitrary plugin install.
- **Backend operator/developer:** distinct scopes, usually service/instance rather than community moderation. Deploy, diagnose, restore or develop only through authorized gateways, gated validation and audit.
- **Player:** participate, report, vote, propose, choose servers; no governance requirement to enjoy gameplay.

## Authorization model
Use **principal + rank assignments + action permission + scope + context + policy revision**. Multiple role assignments are possible; deny/locked/nondelegable policies override grants. Explicit scope types: network, Discord guild/channel, Minecraft instance, project, incident and operation. A server admin for instance A has no implied authority on B; Minecraft op status or Discord Administrator permission does not automatically confer Core permissions except narrowly defined separate platform-specific checks (e.g., established Discord Administrator ballot cancellation).

**Dashboard: one tab per rank**, with all individual permissions grouped into community, moderation, appeals, governance, tickets, Discord, Minecraft, spark/diagnostics, backup/restore, operations, development, release, security, AI tools and settings. For each permission show OFF / SUGGEST / APPROVAL REQUIRED / AUTONOMOUS where appropriate for AI, and allow/deny/inherit for conventional roles. Show effective scope, provenance, inherited settings, pending application, role assignment, full audit history, conflicts and warnings. Support custom ranks and future scale, not fixed hardcoded personnel counts.

**Protected invariants:** no self-elevation; no model/bot directly controlling host/credentials; no falsification/erasure of audit, vote totals or protected archives; protected owner recovery cannot be delegated or disabled by an ordinary rank toggle. A proposal cannot supersede safety/integrity gates.

## Separation and escalation examples
- Local gameplay dispute → server admin → independent network moderator on appeal → Deadhead for unresolved community disputes.
- Moderator versus moderator or credible staff misconduct → Deadhead, with evidence preserved and independent reviewer where available.
- Backend performance/security incident → authorized backend operator / owner recovery; inform community staff when player-impacting.
- AI versus human: AI may state evidence and risk, then must obey authorized decision unless deterministic safeguards block unsafe action. No AI argument loop.
- Two moderators not online: AI may gather evidence and run only previously authorized protective playbooks; case remains queued for human review.
- Staff offboarding: revoke grants/sessions, rotate affected credentials, reassign tickets and preserve audit; returning user gets no automatic restored authority.

## Moderation and capacity case handling
Server constitutions are contextual: legal TNT raiding on Anarchy cannot be treated as griefing on protected Survival. In-game event/claim logs are evidence only if an approved recorder is present. Support targeted rollback where possible and consent/appeal pathways. No punishment for criticizing AI. Keep staff review queues, severity, availability and ownership, rather than sending every ticket to owner/Deadhead.

When resources are insufficient, **deny admission and explain why**; the AI may present a data-backed proposal to vote to archive an underperforming server, but cannot automatically evict, archive or erase the existing world. Proposed popularity/performance comparisons must be transparent and avoid equating a niche community with wrongdoing.

## Proposed (not yet owner-approved) role defaults
AI: autonomous Q&A, routine evidence gathering, bounded diagnostics and permitted routine maintenance; high-impact discipline or production deployment requires explicit grants/approval. Moderators: report review, scoped timeout/warnings, appeal handling; severe punishments separately gated. Server admins: scoped gameplay/community administration, approved read-only health checks and change requests; no unrestricted host console. Any default not approved stays disabled / setup-required.

## Required tests
Verify cross-server denial, role revocation during queued action, conflicting inherited grants, secure role-editor access, Discord Administrator edge cases, AI permission downgrade, Deadhead community-only boundary, no self-elevation, moderator appeal separation, service-offline functioning, and immutability of audit/protected backups.

## P0 consolidation reference

[DECISIONS.md](DECISIONS.md) is the consolidated approved-policy register; [PERMISSION_REGISTRY.md](PERMISSION_REGISTRY.md) provides proposed granular permission keys (not approved role grants); [STATE_MACHINES.md](STATE_MACHINES.md) defines voting, incident, Bridge and release lifecycles; [P0_REVIEW_CHECKLIST.md](P0_REVIEW_CHECKLIST.md) is the review exit gate. No new implementation authority is granted by these links.
