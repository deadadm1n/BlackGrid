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

## Refactor note
The previous 75 KB monolithic PRD was preserved verbatim in [PRD_LEGACY_REFERENCE](PRD_LEGACY_REFERENCE.md). Section-specific documents were extracted without intentionally dropping the original requirements. The shorter PRD is now the entry point. Future changes should update the *relevant subject file* and this register rather than append another divergent requirement block to the entry-point PRD.
