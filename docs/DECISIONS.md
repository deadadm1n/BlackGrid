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
