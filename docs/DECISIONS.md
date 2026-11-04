# BlackGrid — Decision register

**Purpose:** Record agreed design, unresolved settings, and forbidden assumptions. This register is a navigation aid; canonical details live in the linked specifications. No design approval here authorizes deployment.

## Approved design direction
- Community-first Minecraft network, unified web/Discord/Core, AI optional: [PRD](PRD.md).
- Discord-only OAuth community login and synchronized website governance: [WEBSITE](WEBSITE.md).
- Rules acknowledgement before proposals/votes; network- and server-scoped voting; 24–72 hour ballots announced before the timer runs: [GOVERNANCE](GOVERNANCE.md).
- Proposal fields: Title, Request, Details, Time Limit. Authorized edit creates new immutable round, discards previous votes for tally, restarts full timer and announces changes: [GOVERNANCE](GOVERNANCE.md).
- Granular global/scoped permissions, administrator constraints with attribution, Discord administrator ballot cancellation: [GOVERNANCE](GOVERNANCE.md).
- First-party Discord bot with full-guild administration capability for AI via gated Core tools, Discord role hierarchy respected: [DISCORD](DISCORD.md).
- Live permissioned dashboard controls for settings, AI autonomy, budgets and operations; staged apply for settings requiring restart: [WEBSITE](WEBSITE.md).
- Players are the purpose of the network. Community disputes escalate to the designated Deadhead authority; infrastructure and owner-only break-glass are distinct. Do not infer unlimited host rights from community authority.
- Serious incidents should be reported to an owner-configurable dedicated Discord incident channel, with preauthorized mitigation only: [OPERATIONS](OPERATIONS.md).
- Approved additional capabilities (identity, memory, incident investigation, dependencies, gameplay sandbox, analytics, events, recovery, self-improvement proposals) require detailed implementation specification: [WEBSITE](WEBSITE.md), [AI_SYSTEM](AI_SYSTEM.md).
- **THE HUNT** is a manually submitted *future* Discord governance test, **not** authorization to implement the chicken AI or server: [Proposal](experiments/THE_HUNT_PROPOSAL.md).

## Decisions and safe proposed defaults — owner review required

| ID | Policy question | Proposed starting point (NOT approved) | What the dashboard should expose |
|---|---|---|---|
| D-01 | Vote passing threshold | Configurable simple majority of valid votes, subject to quorum | threshold by vote type/scope |
| D-02 | Minimum participation | Require an explicit configured quorum before binding votes can open | min voters or eligible-electorate percentage |
| D-03 | Identity and new-member eligibility | Linked Discord principal plus rules acknowledgement; optional Minecraft-link requirement according to electorate | membership age, account link, voter-eligibility rules |
| D-04 | Proposal discussion period | Optional per scope, with no automatic start until an authorized announcement | minimum discussion duration, bypass authority |
| D-05 | Repeated proposal edits | Configurable limit/cooldown; every actual edit restarts timer and voids prior round | edit quota, interval and escalation |
| D-06 | Concurrent capacity requests | FIFO by approval time unless an explicit owner-set priority class exists | resource admission policy, class weights, quotas |
| D-07 | AI autonomy | Low-risk answers/investigations suggest-only initially; no privileged writes without authorization until owner configures it | capability × scope × autonomy mode |
| D-08 | Incident response | Report serious incidents to designated Discord channel; preauthorized stabilizing actions only; escalate if communication fails | severity, channel, notification target, safe playbook |
| D-09 | Discord outage during active ballot | **Unresolved policy conflict**: published ballot duration cannot be exceeded beyond 72h and announcement is required; consider 'continue clock with website available' vs 'cancel and reissue new round on recovery'. Do **not** silently extend | outage policy and operator review |
| D-10 | Vote visibility/privacy | Aggregate totals may be displayed by configuration; individual votes private by default | tally visibility, anonymity, audit scope |
| D-11 | Moderation and appeals | Routine predefined spam cleanup may auto-execute; contested severe punishments require human review | moderation action risk tiers, appeals |
| D-12 | Data retention and backup windows | Explicit owner-set retention, immutable audit and protected world archives | policies by data class |
| D-13 | Minecraft platform versions and proxy | Paper-first, Fabric/NeoForge via adapters; Velocity deferred until need confirmed | supported adapters, version matrix, routing |
| D-14 | Deployment and self-improvement authority | AI can create proposals and sandbox plans; production core changes require independent approval | release approval policies and audit |

**Do not implement these candidate defaults as owner decisions.** Configure as explicit setup-required values or safe unavailable states where a product action depends on an unresolved value. Provide a clear owner review flow.

## Open decisions (do not choose silently)
- Quorum, passing threshold, anti-alt criteria, eligibility, proposal discussion/cooldowns and edit limits.
- Autonomy allowlists, default budgets, moderation escalation and notification levels.
- Resource scheduling when several approved instances compete for host capacity; oldest-first is a candidate, not an approved rule.
- Exact installed hardware, runtime, DNS, credentials, Minecraft versions, proxy topology and mod distribution policy.
- Public vs private vote visibility and detailed data retention periods.
- Precise incident severity definitions and automated emergency responses.

## Rejected / prohibited interpretations
- No automatic construction, publication or vote creation for THE HUNT.
- No assumption that passing a concept vote authorizes development or deployment.
- No AI self-grant of rights, unreviewed production code, world/archive deletion, or access to owner break-glass.
- No inference that biological research/datasets provide a working chicken consciousness or ready-to-run trained Minecraft agent.

## Service interface reference

The service boundary contracts and cross-system failure/race tests are specified in [CONTRACTS.md](CONTRACTS.md); the updated sequencing is in [ROADMAP.md](ROADMAP.md). These are architecture proposals subject to owner review, not implementation authority.

## Refactor note
The previous 75 KB monolithic PRD was preserved verbatim in [PRD_LEGACY_REFERENCE](PRD_LEGACY_REFERENCE.md). Section-specific documents were extracted without intentionally dropping the original requirements. The shorter PRD is now the entry point. Future changes should update the *relevant subject file* and this register rather than append another divergent requirement block to the entry-point PRD.

## 300-member scenario follow-up — needs approval before encoding final policy

- **Confirmed product direction:** distinct community/backend roles and scoped grants; explicit appeal handling; evidence-grounded grief investigation; targeted restoration when feasible; role-specific dashboard; transparent AI action records; useful staff handoff; per-server rule context; careful moderation rather than personality policing.
- **Examples not final values:** eight example server types, sample RAM assignments, illustrative moderation levels, proposed 50%/60%/two-thirds vote thresholds, and S0–S3 incident definitions. Do not implement these numbers as canonical defaults without owner approval.
- **Policy still unresolved:** moderation auto-action tiers, appeal reviewers when few staff are available, active ballot outage behavior, server resource queue priority, quorum, account eligibility, exact emergency notification routes, retention and voluntary-staff availability policy.
- **No new authority granted:** AI cannot bypass Core, invent evidence, ban dissenters for disagreeing, access protected host recovery or escalate its own permissions.

## Owner-approved decisions — November 4, 2026 (supersedes candidate defaults)

- **D-01 APPROVED:** Regular ballots require **51% yes** of valid votes; major changes **60% yes**; server retirement **two-thirds yes**. Vote-type classification and all thresholds are editable in owner-authorized dashboard settings with versioned audit. Exact fraction/rounding semantics must be defined in the contract before implementation.
- **D-02 APPROVED:** A binding vote requires participation by **10% of eligible active players**, with denominator and integer rounding semantics to be defined and displayed before ballot starts. Adjustable by scope/type in dashboard.
- **D-03 APPROVED:** Discord membership, acceptance of current rules and verified Minecraft account for gameplay votes. Eligibility settings are adjustable in dashboard; cross-platform identity deduplication applies.
- **D-04 APPROVED:** Optional **24-hour proposal discussion period** before voting; configurable per scope/type from dashboard.
- **D-05 APPROVED:** At most **three formal revisions per voting round before staff review**; every authorized content/constraint revision invalidates the current round's votes and restarts its timer after fresh Discord announcement. Dashboard-configurable revision cap.
- **D-06 APPROVED:** On insufficient resource capacity, **AI denies the requested server activation/provisioning and explains specific capacity constraints**, then recommends an appropriately scoped vote to shut down/archive an **underperforming** server. AI does not unilaterally remove existing capacity, select a target without transparent evidence, or initiate the vote without normal proposal authorization. Existing worlds/backups must be preserved. An already-approved concept may remain as a non-executing recorded outcome; no resource promise.
- **D-07 APPROVED:** AI autonomy is permission-based in the dashboard. Provide **one tab per rank**, with complete granular permission list and explicit toggles per rank, scope, and action; effective permissions must reflect inheritance/overrides and Core-enforced checks. AI is a separately scoped principal/rank whose abilities can be changed live; protected root/break-glass restrictions remain non-delegable.
- **D-08 APPROVED:** Post incident reports to a **dedicated Discord channel**; owner will enable notifications for that channel. Incident notification should work without requiring AI inference; fallback when Discord is down is an open operational decision.
- **D-09 APPROVED POLICY:** If Discord becomes unavailable during an active ballot, **pause the ballot's remaining time** and resume when Discord is reliably back. Preserve all votes and record pause/resume audit events. Pause new ballot openings as already specified. **OPEN implementation reconciliation:** interaction with the nominal 24–72 hour voting window (72h is active elapsed duration vs wall-clock limit), outage-detection grace/health definition, and whether ballots must be re-announced on resume.
- **D-11 APPROVED:** AI moderation abilities are governed by the exact same dashboard rank-based granular permission toggles and Core policy gate; no broad implicit moderation privilege. Review and appeals remain auditable.
- **D-13 APPROVED:** Paper first with compatible Fabric/NeoForge adapters and **spark profiling support**. Include profiler capability detection, authorized install/use per loader/version, safety/resource limits, profile artifact retention and dashboard integration. Proxy deployment remains subject to actual network need.
- **D-14 APPROVED DIRECTION:** AI may autonomously identify BlackGrid bugs, propose improvements and develop features/fixes in isolated controlled workspaces **when granted permissions through the dashboard**. Owner expects a self-improving platform. Production changes still require independent security/test/release authorization; no self-modification of the Core permission root or bypass of safeguards.

**Still open:** D-10 ballot privacy/results visibility; D-12 retention; precise authority for AI deployment release; D-09 72-hour/pause implementation; quorum denominator/rounding; definitions of 'underperforming'; emergency fallback and severity mapping; precise initial rank defaults. All settings must have effective current values, scopes and revisions visible in the dashboard.

## Additional owner decisions — November 4, 2026

- **D-10 APPROVED:** During an active ballot, display participation/turnout but **hide YES/NO counts, percentages and choice breakdown** until the ballot closes. Once a ballot closes, publish outcome and tally under the existing privacy rules; individual voter choices remain private by default. Apply consistently to Discord, website, APIs and AI summaries to avoid side-channel leaks. These are current defaults, adjustable through authorized dashboard governance settings.
- **D-12 PARTIALLY APPROVED:** For Minecraft **world/map backups**, run **one local backup per day** and retain the last **seven days** of daily recovery points, subject to preservation and integrity gates. The detailed retention policies for other records/artifacts are **deferred until storage becomes an issue**. Expose backup frequency and local retention in dashboard controls. Protected snapshots, pre-change backups, world archive preservation and audit requirements must not be silently destroyed by this routine retention policy. Alert if storage would prevent a new backup; never report an unverified backup as successful.

**Remaining design detail:** define local backup placement independent of the live world, retention counting when scheduled runs fail, and how routine daily backup pruning interacts with immutable world archives and protected pre-change snapshots. No offsite-backup promise is implied by local-only backups.
