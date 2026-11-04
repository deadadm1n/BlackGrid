# BlackGrid — Cross-system contracts (design baseline)

**Status:** proposed technical contracts for owner/implementation review. Documentation only. Exact framework, transport and fields may evolve via versioned ADR; don't infer runtime implementation.

## 1. Non-negotiable boundary

Web, Discord and optional OpenCode are **clients** of BlackGrid Core. Core owns identity, authorization, database transactions, audit, ballots, settings and job admission. Supervisor alone owns host/instance lifecycle, through a narrow authenticated API. Minecraft adapters translate version-scoped game operations. Discord worker exclusively holds Discord credentials; model receives only typed scoped capability responses.

No surface is a second source of truth. A passed vote is evidence of a specific authorization class, **not** unlimited permission to take any action.

## 2. Common request and event envelopes

Each mutating request carries: `request_id`, `idempotency_key`, `actor_principal_id`, `auth_context`, `scope` (network/guild/instance/channel/project), `action_type`, `payload_schema_version`, `expected_resource_revision`, `requested_at`, and typed `payload`. Identity is derived from verified auth, never trusted from client-supplied text. Use UTC timestamps and opaque IDs.

Persist Core decisions with: `operation_id`, `policy_revision`, `principal`, `scope`, `allowed/denied`, `reason_code`, `required_approvals`, `state`, `created_at`, `updated_at`. Worker retries are safe. Reauthorize before an action commits/effects; if permissions or current policy changed, stop or return to approval.

Outbox events include `event_id`, `aggregate_type/id`, `aggregate_revision`, `event_type`, `schema_version`, `occurred_at`, and safe `data`. Consumers deduplicate by event ID and reconcile from Core if events arrive late/out of order. Outbox is transactional with primary database writes. Deliver events at least once, without claiming exactly-once transport.

## 3. Core ↔ Website

- Discord OAuth2 callback establishes a secure Core session tied to verified Discord identity. Website has no local password-based public signup.
- `GET /api/v1/me`: identity, accepted rules revision, eligible scopes, effective grants, not secret policies.
- `GET /api/v1/proposals`, `GET /api/v1/proposals/{id}`: scope-filtered proposals, versions, current ballot and discussion cursor.
- `POST /api/v1/proposals`: title, request, details, requested duration, scope, proposal type; check rules acceptance, create grants and rate limits.
- `PATCH /api/v1/proposals/{id}`: field-scoped authorization plus expected revision; new proposal version/round and mandatory announcement; does not silently overwrite ballot.
- `PUT /api/v1/ballots/{id}/my-vote`: cast/change one vote for one verified eligible voter in active round; transactional unique identity constraint; never trust public username for identity.
- `GET /api/v1/settings` / `PATCH /api/v1/settings/{key}`: authorized effective settings with inherited/override source, revision, apply mode and applied/pending state.
- `GET /api/v1/operations`: scope-filtered jobs, approval status and safe cancellation controls.
- Structured comment operations with moderation state; never surface private Discord material to public routes.

API routes are conceptual names; finalize OpenAPI, pagination, errors, request body schemas and access matrices before P1/P4 code.

## 4. Core ↔ Discord worker

- Discord interaction signatures and member/guild state verified using Discord's supported mechanisms, then mapped to a Core principal and permissions. The bot's guild Administrator permission does not imply blanket authorization.
- Core issues idempotent delivery tasks: `discord.message.publish`, `discord.channel.reconcile`, `discord.role.reconcile`, `discord.moderation.apply`, and `discord.vote.announce`. Each task has precise target guild/channel IDs and authorized operation IDs, not arbitrary bot-token access.
- Worker acknowledges delivery with Discord snowflake IDs and outcome; retries handle rate limits, missing permissions, deleted resources and ambiguous previous success through reconciliation.
- Ballot round cannot enter `OPEN` until its **new** Discord opening announcement is confirmed. A proposal revision supersedes the previous round, invalidates previous current votes, and requests publication of a new ballot round before its clock begins.
- Cross-surface comments have canonical IDs, source refs and visibility labels; editing/deletion/moderation generates a revision/tombstone event, not silent duplication.
- Guild admin vote veto must verify actual Administrator guild permission at action time; moderator or AI cannot imitate that source authority.

## 5. Core ↔ Minecraft supervisor / adapters

- Commands: `instance.reserve`, `instance.provision`, `instance.start`, `instance.stop`, `instance.archive`, `instance.snapshot`, `instance.restore`, `instance.health`, `instance.config.stage` and `instance.change.deploy`.
- Supervisor verifies Core service identity plus an expiring, operation-bound capability for exact instance and action; never accepts free-form host shell from web/Discord/AI.
- Reserve CPU/RAM/disk/ports against max-active and provisioned caps transactionally before scheduling. Conflicting reservations are rejected/queued under configured policy, not handled by LLM guesses.
- For affected world changes: consistent manifest and restorable snapshot; Sentinel compatible dry run; authorized release gate; production mutation; post-start health + structural world checks; controlled rollback and incident if failed.
- Game events (`player.join/leave`, `chat`, `health`, `crash`) carry instance, correlation and source trust metadata. In-game player messages are untrusted text, not executable instructions.

## 6. Core ↔ Optional AI/OpenCode

- AI adapter reads redacted, permission-scoped data and submits `action.propose` with reason, evidence references, requested scope, resource impact and intended result.
- Core returns decision `DENIED`, `SUGGESTION_ONLY`, `WAITING_APPROVAL`, `QUEUED`, or `ALLOWED` under the **current** dashboard-controlled autonomy matrix. The model cannot issue privileged service credentials, direct Docker/Discord API calls, or bypass policy.
- For a permitted sandbox development task, Core creates a bounded job with CPU/RAM/time/cost limits. Built artifacts require independent provenance, tests and release authorization.
- Pausing AI cancels or suspends queued future autonomous actions and revokes AI tool grants; deterministic Discord/voting/server operations remain available.
- Each AI tool invocation has a typed schema, correlation ID, allowed scope and audit. Text from Discord, Minecraft books/chat, websites and logs is untrusted.

## 7. Settings, safety and failure semantics

- Settings write → transaction committed with new revision → subscription notification → workers reconcile effective policy. Changes that need restart show `PENDING_APPLY` until observed.
- All mutating clients must handle `403_FORBIDDEN`, `409_REVISION_CONFLICT`, `409_POLICY_CHANGED`, `429_RATE_LIMITED`, `503_DEPENDENCY_UNAVAILABLE` and safe retry semantics. Response messages never reveal credentials.
- Discord down: website/discussions can persist safe drafts but **new votes cannot start** until announcement confirmation. Already-open votes require a **policy decision** about whether to pause/extend on prolonged outage; do not silently extend beyond approved duration or prematurely finalize.
- Core down: workers must not authorize new actions from cached permissions; Minecraft servers may continue operating independently; queued state recovers on restart.
- AI down: only autonomous reasoning pauses, not governance, deterministic bot behavior, or instance management.

## 8. Contract tests required before release

1. Website + Discord simultaneous ballot updates result in one valid vote.
2. Proposal edit during tally races yields one superseded old round and one newly announced round.
3. Admin constraints show attribution and restart the timer.
4. Discord post succeeds but acknowledgment lost: retry does not duplicate an official announcement.
5. Permission revoked while operation is queued: action blocked on pre-execution recheck.
6. AI requests Discord Administrator action not authorized by Core: reject and audit.
7. Two server starts race against one remaining resource slot: only one admitted.
8. World precheck/Sentinel/postcheck failure blocks or rolls back change; no data loss.
9. All deterministic workflows function when OpenCode is unavailable.
10. Private Discord content never leaks into public proposal views.

## 9. Unresolved contracts

Final decisions: exact ballot outage treatment, quorum/threshold policies, voter eligibility and alt-account checks, queued-resource priority, incident escalation levels, default autonomy allowlists, event retention, approval authority for release/cancellation, and role hierarchy delegation. These are owner/community policy choices tracked in [DECISIONS.md](DECISIONS.md).
