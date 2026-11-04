# BlackGrid — Operations, lifecycle and resilience

**Status:** planning baseline.

## 7. Lifecycle and workflows
### Server states
`REQUESTED -> APPROVED -> QUEUED | PROVISIONING -> CONFIGURING -> VALIDATING -> STOPPED | RUNNING`.
Operational transitions: `RUNNING -> STOPPING -> STOPPED -> ARCHIVED`; failures enter `FAILED` with explicit repair/retry. `ARCHIVED` is reversible, not deletion. Define legal transitions in code and test them.

### Governance states
`DRAFT -> DISCUSSION -> ELIGIBILITY_REVIEW -> PENDING_ANNOUNCEMENT -> BALLOT_OPEN -> PASSED | REJECTED | INVALID | CANCELLED_BY_ADMIN -> SCHEDULED -> EXECUTING -> COMPLETED | FAILED | BLOCKED`. `CANCELLED_BY_ADMIN` is terminal for the ballot; queued vote-authorized execution can be separately revoked before it begins. Approval binds a specific proposal revision, scope, parameters and expiration. A passed ballot alone never bypasses current capacity or policy.

### Provisioning saga
Reserve capacity/port -> prepare storage -> create isolated instance -> validate startup/health -> create/reconcile Discord resources -> publish. Each step persisted with idempotency keys. On error release reservations where safe and retain potentially valuable instance/world data. Retries must not create duplicate channels or instances.

### BlackGrid Sentinel — isolated change validation
A **micro-server** means a short-lived, capacity-limited, player-inaccessible Minecraft test instance managed by the BlackGrid Supervisor; it is not the permanent host of BlackGrid Core. The validation instance starts with the same Minecraft version, Java runtime requirements, loader, mods/plugins and relevant configuration as production and a consistent snapshot of the world or appropriately selected representative test dataset. A lightweight sandbox must not be assumed capable of booting a full modpack: each test requires adequate minimum RAM/CPU/disk and a bounded timeout. If resources are insufficient, report `VALIDATION_UNAVAILABLE`, queue the change or require owner review; never auto-pass.

**Process:** Snapshot/hash the production world at a consistent point -> create isolated test instance and apply proposed change **only to the test copy** -> boot -> read startup logs and crashes -> wait for healthy world load -> sample TPS/MSPT, JVM/GC, CPU/RAM/disk and log errors -> check region/NBT structure and per-file world hash manifest changes within approved scope -> produce immutable structured result -> shut down/dispose of ephemeral compute, retaining required test evidence. On failure, mark implementation blocked and notify Discord with a concise reason. On success, prepare a separate production change with its own pre-change verified recovery snapshot and post-start integrity verification (see World-integrity change gate). If production fails despite passing staging, restore safely and report failure.

**Scope/limitations:** Starting a clone without active players cannot demonstrate live concurrency performance or catch all corruption. Treat small/sampled worlds as smoke tests, not proof that a full world or full player load is safe. Never reject solely because TPS fluctuates or expected world files change; compare to appropriate baseline and evaluate actual world validity. Keep resource/performance thresholds configurable per server template. Default to conservative decisions and clearly report 'inconclusive' rather than guessing.

**Native monitoring:** BlackGrid owns its event/log collector, process metrics, health probes, structured crash classification, world manifest/region/NBT checker, validation policies, dashboard history and AI-readable reports. Integrate spark as the preferred deep profiler where compatible (avoid duplicate installation when bundled), and optionally integrate Prometheus-compatible collectors/exporters and existing NBT/MCA validation libraries under explicit license/security review rather than reinventing JVM profiling or binary parsers blindly. OpenCode receives read-only sanitized evidence; it may propose follow-up work but cannot manufacture a passing validation result.

**Validation states:** `PENDING -> SNAPSHOTTING -> PROVISIONING -> BOOTING -> OBSERVING -> VERIFYING -> PASSED | FAILED | INCONCLUSIVE | VALIDATION_UNAVAILABLE`. Each state and test evidence is durable, jobs idempotent, and temporary credentials and instance runtime are disposed after completion. No direct public network access to the test instance, no Discord chat bridge, and no permanent player connections.

**Acceptance:** bad plugin preventing startup fails in staging without touching production; corrupt region fails deterministic validation; good change passes a matching-environment smoke test; undersized sandbox is inconclusive/unavailable rather than false pass; production is gated behind staging and production rollback remains available; telemetry and actionable failure reasons remain available without OpenCode.

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

## 300-member / eight-instance operational model (illustrative capacity scenario)

The eight-server example is a scenario, not a mandated fleet composition or RAM allocation. Capacity decisions depend on concurrency, plugins/mods, JVM overhead, disk I/O, CPU and available host resources—not registered-member counts alone.

**Admission and scheduling:** Track reserved and observed CPU/RAM/disk/ports and minimum host headroom; each server has versioned resource profile, priority class, schedule and status. Approved but unplaceable requests enter a visible queue with reason and options. Do not autonomously stop unrelated live communities to make space. Scheduled/event instances may start/stop through an owner-approved policy while preserving worlds. Exact queue ordering and priority weights remain open and dashboard-configurable.

**Incident manager:** Cross-service incident IDs, affected services, evidence timeline, severity, acknowledgement owner, escalation targets, approved containment playbooks, recovery checkpoints and postmortem. For S2/major issues, publish an evidence-backed incident message to a configurable dedicated Discord channel. S3/critical incidents require preauthorized protective actions and notification to appropriately authorized infrastructure personnel as well as community staff if player experience is affected. Discord unavailability must have an owner-configurable independent alert route; AI unavailability cannot prevent deterministic recovery. S0–S3 labels and triggers are proposed, not final policy.

**Stability:** Repeated restart failures use bounded retries and circuit breakers; disk-full stops risky writes and alerts; backup/restore evidence is independently verifiable. Stop serving potentially unsafe changes rather than fabricate healthy state. Recover job ownership after worker crash, reconcile partial Discord API operations, and retain immutable event histories.

**Staff offboarding:** Revocation of role/session/service grants and rotation of exposed credentials, reassignment of tickets/projects, preservation of work and audit history; returning staff never automatically inherits old permissions.

**Health and operations center:** Dashboard aggregates core, Discord, AI, fleet, backups, Sentinel, tickets, votes, queued actions, incidents, and pending approvals. Explicitly show real monitoring values vs illustrative estimates, with drill-down and safe cancellation at defined checkpoints.

## Owner decisions: capacity denial and Discord incident channel (2026-11-04)

When admission would exceed measured or reserved capacity, return a structured **DENIED_INSUFFICIENT_CAPACITY** result with the specific blockers and suggested options. Surface an AI-generated recommendation for an **appropriately scoped shutdown/archive vote** targeting an underperforming existing server supported by comparative utilization, active-player trends and world importance—not an automated shutdown. Only a separate successful, executable, safety-checked authorization may retire an instance; archive world/backups rather than delete.

Deliver operational incidents to the dedicated owner-configured Discord channel, with message ID, acknowledged state and incident link. Owner enables Discord notifications; the platform should show failed Discord delivery distinctly from a notification actually sent. Severity detection and preauthorized safe response depend on rank/action policies. Discord unavailable: queue durable notifications and flag the need for a separate fallback alert mechanism, still unresolved.
