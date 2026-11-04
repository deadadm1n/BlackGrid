# P0 engineering review checklist — NO CODING

**Authority:** Planning review only. Owner approval is required before P1 implementation, external Discord guild changes, publishing website changes, or THE HUNT.

## Specification integrity
- [ ] Verify [PRD](PRD.md) and all subject specs; no contradictory old decision supersedes [DECISIONS](DECISIONS.md).
- [ ] Every active requirement has one canonical subject home; archived PRD is reference, not second source of truth.
- [ ] Confirm permission registry with owner rank-by-rank; no default grant guessed.
- [ ] Define precise voting threshold/quorum rounding, electorate definition, outage/pause/resume policy and anti-alt rules.
- [ ] Define incident severity and fallback alerts, protected world archive and 7-day daily backup pruning.
- [ ] Define developer/operator and release-approval roles, scope boundary tests and break-glass plan.

## Architecture/contracts
- [ ] ADRs for chosen languages, deployment, persistent data, auth sessions, message transport, Minecraft protocol adapters, supported versions and proxy strategy.
- [ ] Complete OpenAPI/JSON schemas for Core↔Web↔Discord↔Bridge↔Supervisor↔AI; versioned error codes, idempotency, clocks and replay prevention.
- [ ] Final state machine transitions and race invariants in [STATE_MACHINES](STATE_MACHINES.md).
- [ ] Web Discord login without requiring guild membership; gameplay join without website account or Bridge client; linking code only for verified features.
- [ ] Permission coverage for all Bridge commands, spark diagnostics, modpack publishing, backups, Discord guild actions and AI release activity.
- [ ] Explicit modpack release manifest/download compatibility, license provenance, per-instance Discord notes, idempotent publication.
- [ ] Threat model Discord chat/books/signs, logs, proposals, untrusted plugins, API and supply-chain, moderation privacy and bot permissions.
- [ ] Failure behavior AI offline, Discord offline, Core offline, network partition, storage full, rolled-back modpack, crashed instance.
- [ ] Migration and recovery strategy for worlds, DB, permissions and Discord bindings; no destructive world cleanup.

## Required review deliverables
- [ ] Architecture diagram and selected stack ADRs.
- [ ] Schemas and API/event contract examples.
- [ ] Permission registry finalized (rank/group/instance action matrix and testable policy fixtures).
- [ ] Voting/incident/Bridge/modpack finite state machine tests.
- [ ] Ranked issue backlog: minimum implementation slices P1–P8, each with acceptance/negative tests and rollback.
- [ ] Risk register and named owner decisions required before implementation.
- [ ] Evidence matrix: required test, environment, observed outcome, failure classification (not simulated success).
- [ ] Human review packet; explicit decision to approve/deny P1.

**Exit criterion:** No unowned critical P0 ambiguity, policy boundary explicit, all open choices isolated, and the owner explicitly authorizes next phase. No code implied or authorized by checklist completion.
