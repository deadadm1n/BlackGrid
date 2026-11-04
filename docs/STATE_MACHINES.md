# BlackGrid — Governance, incident and Bridge state machines (P0 baseline)

**Status:** deterministic proposed engineering contracts; policy details explicitly OPEN where noted. No code/deployment authorization.

## Voting
`DRAFT → DISCUSSION (optional 24h configured) → PENDING_ANNOUNCEMENT → OPEN → CLOSED`.
Additional transitions: `OPEN → PAUSED_DISCORD_UNAVAILABLE → OPEN`; `OPEN/PAUSED → SUPERSEDED` on authorized formal revision; `OPEN/PAUSED/PENDING → CANCELLED` under existing special Discord Administrator veto or other configured authorized cancellation. **A revised ballot is a new round requiring new announcement and a full selected active-duration clock.** Old ballots remain immutable audit, not counted. Only the delivered official Discord announcement permits a new round to open. Pauses stop **remaining active voting time**, retain votes, and are audited; recovery reconciliation resumes from stored remaining seconds, not old wall-clock deadline. Multiple outages are cumulative. No quiet hidden voting.

**Owner-approved rule snapshot for each opened round:** regular 51% YES, major 60%, server retirement two-thirds, quorum 10% of eligible active voters; current rules acceptance, Discord membership, verified Minecraft UUID for gameplay voting, optional 24h discussion, three formal edits/round before staff review, 24/48/72h active voting periods. These values are adjustable for **future rounds** through dashboard and versioned in snapshots. During OPEN/PAUSED only turnout/quorum progress is public; choice breakdown hidden until CLOSE. Only one ballot choice per verified person/round across game, Discord and website.

**Open engineering decisions:** rounding of percentage quorum and thresholds, eligible 'active' definition, whether paused ballots accept new votes, Discord connectivity/grace assessment, re-announcement on recovery, wall-clock upper bound / 72h interpretation, contested Discord Admin cancellation during outage. These must be approved or safely held as CONFIGURATION_REQUIRED before release; do not silently select. The owner has said 'timer stops' during Discord outage, which is binding; implementation details aren't.

## Incident and moderation
`DETECTED/REPORTED → TRIAGED → INVESTIGATING → CONTAINED (if permitted) → REVIEWED → RESOLVED → CLOSED`; with `APPEALED → REOPENED/UPHELD/OVERTURNED`. Every state change records actor, authority, evidence and relevant instance rules. The AI may investigate/report, and executes only separately granted contained actions. A protected claim in Survival and permitted raiding in Anarchy are materially different. Moderators cannot review their own appeals where independent reviewer exists; Deadhead is ordinary community escalation. Backend security incidents route to owner/backend authority. Operational alerts go to dedicated Discord channel, with verified delivery; fallback when Discord unavailable remains open. Severity definitions not yet approved.

## Bridge connection and chat
`DISCONNECTED → AUTHENTICATING → SYNCING_CAPABILITIES → READY`, with `DEGRADED` (Core/Discord unreachable), retry/backoff and no privileged action while Core authorization cannot be reached. Local gameplay continues. Event schemas MUST have `event_id`, `schema_version`, `instance_id`, `actor_minecraft_uuid` (where relevant), `source_channel`, `destination`, `message_id/correlation_id`, `occurred_at`, `trust_class`, and structured payload. Prevent echo loops and duplicate Discord messages by recorded bindings and reconciliation. Bound and expire outgoing chat queue; never replay stale staff commands. Inbound content cannot be executed as Core instructions.

**Example typed commands:** `bridge.chat.publish`, `bridge.chat.deliver`, `bridge.identity.link.begin/confirm`, `bridge.command.request/result`, `bridge.vote.list/cast`, `bridge.report.create`, `bridge.diagnostics.spark.request/result`. No raw Discord token or arbitrary host console.

## Modpack publication
`DRAFT → VALIDATING → READY_FOR_REVIEW → APPROVED → PUBLISHED`, plus `REJECTED/FAILED/RETIRED`. Each publication binds to a specific server ID, game + mod-loader version, compatible server profile, immutable manifest/hashes and distribution provenance. Website presents download/manifest (only directly hosting files that may legally be redistributed). The Discord worker posts release notes **in that server's designated channel** via outbox and records delivery ID; announcement retry never duplicates. Bridge itself requires no client-side mod; gameplay packs may require client-side content.

## Release and resource safeguards
New instance admission checks actual resource constraints and returns denial with evidence if full. AI suggests independent vote to archive underperforming instance; vote cannot instantly destroy the world. Daily local Minecraft world backups with seven-day routine retention; protected world archives/safety snapshots obey separate immutable rules. Code developed by AI stays in sandbox until tests, authorization, and controlled release; model cannot give itself privileged deployment authority.

## Required tests
Concurrent votes, outage/reconnect/pause, privacy redaction, formal edit invalidation, Discord announcement failures, staff scopes and appeals, permission revocation, Core/AI disconnection, chat loop prevention, modpack mismatches, third-party licensing, resource denial and no world deletion.
