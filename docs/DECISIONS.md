# BlackGrid — Current decision register

**Status:** consolidated November 4, 2026. **Approved** means a product requirement accepted by owner; does not authorize coding or deployment. Historical discussions remain in Git history and [legacy reference](PRD_LEGACY_REFERENCE.md), but superseded 'proposed' tables are not the live source of truth. Canonical technical interpretation: [STATE_MACHINES](STATE_MACHINES.md), [PERMISSION_REGISTRY](PERMISSION_REGISTRY.md), [CONTRACTS](CONTRACTS.md).

## Approved decisions

| ID | Approved current policy | Configurability |
|---|---|---|
| D-01 | Regular ballot needs **51% YES** of valid votes; major change **60%**; server retirement **2/3** | Dashboard by ballot class/scope |
| D-02 | Quorum **10% of eligible active voters** | Dashboard by ballot class/scope |
| D-03 | Voting requires relevant Discord guild membership, accepted rules and verified linked Minecraft identity for gameplay votes | Eligibility policy editable |
| D-04 | Optional **24-hour** proposal discussion period | Dashboard |
| D-05 | **Three formal ballot-round revisions** before staff review; each authorized substantive edit supersedes round, voids prior round's tally and starts fresh announced 24/48/72h active clock | Dashboard cap |
| D-06 | Insufficient server capacity → AI **denies operational request with factual reason**, suggests a separately authorized vote to archive/shut down an underperforming server; **never auto-evicts or deletes world** | Capacity policy configurable; evidence required |
| D-07 | AI autonomy is governed by **individual dashboard permission toggles**. Each rank has its **own tab** showing all granular permissions, scopes and effective grants. AI modes OFF/SUGGEST/APPROVAL/AUTONOMOUS per action. | Live, audited, bounded and protected |
| D-08 | Operational incidents reported to **dedicated Discord channel**; owner enables notifications | Channel/severity permissions adjustable |
| D-09 | When Discord is unavailable during active voting, **ballot timer stops**. Preserve votes and resume remaining active time on recovery; no new ballot opening without successful Discord announcement | Exact outage detection/clock details open |
| D-10 | **Show turnout and quorum**, hide YES/NO distribution until ballot closes; preserve individual ballot privacy | Owner-authorized future ballot settings |
| D-11 | AI moderation follows D-07's exact granted actions, not assumed universal moderation authority | Dashboard |
| D-12 | **Minecraft world/map backups daily, local, 7-day routine retention**. Retention policy for other records deferred until storage issues warrant review. Protected pre-change recovery points/world archives separate | Dashboard |
| D-13 | Paper-first; compatible Fabric/NeoForge adapters and **spark** profiling support | Server capability settings |
| D-14 | Authorized AI can identify BlackGrid bugs/improvements, develop fixes/features and test in isolated environments. Production code/security release requires independent approval and safety checks; no self-escalation | Separate grants for sandbox work and release |

## Further approved product decisions
- **Community:** approx. 300 members, 8 servers, 2 network moderators, one scoped admin/server, one AI administrator, Deadhead highest ordinary community authority, owner infrastructure authority; these are a **scalable scenario, not fixed limits**. Backend admins/developers are distinct. Full roles in [ORGANIZATION_AND_PERMISSIONS](ORGANIZATION_AND_PERMISSIONS.md).
- **Core:** unified self-hosted management, Discord bot with broad guild-side capability but typed Core authorization, optional OpenCode; no AI dependency for deterministic workflows. Protected audit/world/owner recovery boundaries.
- **Voting:** network vs instance electorate, 24/48/72-hour ballots; announcement required before ballot opens; native Discord Administrator cancellation and attributed immutable revisions; one person/round across website, Discord and Minecraft.
- **Player entry:** join Minecraft from IP found on listing, ad, website or Discord; **no mandatory Discord/login/link/client-side BlackGrid mod to play**. In-game welcome with clickable Discord invite and optional commands/vote link.
- **Website:** Discord OAuth2 only for public community login; any Discord account may authenticate, but guild membership, rules and linking may still be necessary for privileged community actions. Public modpack pages/downloads need no login where distribution allows. One verified Minecraft UUID↔Discord ID association remembered; username coincidence is not verification.
- **Bridge:** a server-side-only Paper/Fabric/NeoForge Minecraft bridge providing bidirectional instance-scoped Discord chat, authorized commands and AI/governance tools. Per-server optional/required gameplay client modpacks distributed/linked via website with versioned notes in that server's matching Discord channel; redistribution must follow third-party rights. [BLACKGRID_BRIDGE](BLACKGRID_BRIDGE.md).
- **Operations:** safe backups, Sentinel and world integrity verification, no world/archive deletion by ordinary AI operations; live dashboard configuration and incident reporting, controlled development/release.

## Remaining open **implementation decisions**
- **VOTING:** Define 'eligible active' window; 51% threshold calculation (fractional/rounding), quorum rounding; outage detection/grace, website casting during pause, resumption notice, maximum wall-clock age beyond 72h; account-age/anti-alt details.
- **AUTHORIZATION:** Complete initial role default permission values; exact staff suspension/appeals delegation; owner-only release approval details; protected role/lockout recovery semantics. [PERMISSION_REGISTRY](PERMISSION_REGISTRY.md) is a proposed key namespace **not approved grants**.
- **INCIDENTS:** Exact severity definitions, containment playbooks, fallback alert when Discord itself is down, independent staff appeal reviewers.
- **CAPACITY:** How to judge an 'underperforming' server fairly; resource admission metrics, infrastructure configuration and optional network proxy topology.
- **BACKUPS:** Actual local backup location, seven elapsed days vs seven successful recovery points, pruning rules respecting protected snapshots; non-world data retention deferred.
- **BRIDGE/MODS:** Which EssentialsX-like features to implement vs integrate; supported Minecraft/game loader version matrix, per-server command compatibility, modpack storage/CDN/provider choices and third-party licenses; full schema/test coverage.

All open policies are surfaced for explicit owner review rather than invented as unapproved defaults. Security-essential unknowns are fail-closed.

## No implementation authorization
No Minecraft server, plugin, THE HUNT experiment, Discord guild modification, website cutover, AI self-deployment or production release is authorized by this documentation pass.
