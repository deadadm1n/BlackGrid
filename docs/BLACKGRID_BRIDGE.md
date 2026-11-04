# BlackGrid Bridge — Minecraft, Discord and website integration

**Status:** owner-approved direction and proposed command/design inventory; no implementation or server deployment authorized.

## 1. Role in BlackGrid
**BlackGrid Bridge is server-side. No BlackGrid client-side mod is required.** Use server plugin/mod adapters for Paper, Fabric and NeoForge where each platform supports them. Players may install optional client-side mods, and particular gameplay modpacks may separately require client mods; neither changes the Bridge's server-side-only requirement.

Bridge connects through authenticated Core APIs/events; it does **not** connect to Discord using a bot token or accept privileged raw remote shell/RCON. Discord worker handles Discord API. Core owns identity/ranks/governance/audit. Minecraft continues operating if Core, Discord or AI is offline; unavailable cross-service features degrade clearly.

## 2. Shared chat and social integration
- Bidirectional Minecraft ↔ per-instance Discord chat, routed through Core and Discord worker. Optional global/network chat, scoped staff channels and announcements; each route configured in dashboard.
- Message envelope: message ID, source/instance/channel, actor linked identity, trust/visibility label, timestamp, content, destination routes and correlation ID. Deduplicate to prevent Discord→Minecraft→Discord feedback loops.
- Preserve source labels and handle mentions, formatting, emoji, moderation decisions, privacy, rate limits, chat length, deleted/edited messages and offline behavior. Private/staff channels must never leak to public/world chat.
- Use verified Minecraft UUID↔Discord ID linkage for staff, voting and moderation; names are presentation only. Apply scoped sanctions and identity sync only as policy permits.

## 3. Essential player commands — proposed module set
Reference feature categories from **EssentialsX**, not a commitment to reimplement/copy it. Optional and individually enabled by instance/rank:
`/spawn`, `/sethome`, `/home`, `/delhome`, `/tpa`, `/tpaccept`, `/tpdeny`, `/back`, `/warp`, `/msg`, `/reply`, `/rules`, `/discord`, `/link`, `/report`, `/help`.
Cooldowns, costs, permissions and restrictions differ across Survival/Hardcore/Anarchy/etc. Detect command collisions with EssentialsX and other providers; **allow modules to be disabled** and prefer interoperability over duplicating a mature plugin. Define local-state availability (homes/warps/teleport) separately from Core-dependent cross-service commands.

## 4. BlackGrid network commands — proposed namespace
`/bg votes`, `/bg vote <id>`, `/bg propose`, `/bg projects`, `/bg status`, `/bg events`, `/bg ticket`, `/bg ask <question>`, `/bg staff`, `/bg reports`, `/bg inspect`, `/bg warn`, `/bg mute`, `/bg kick`, `/bg ban`, `/bg history`, `/bg rollback`, `/bg server`, `/bg spark`.
This is an initial command catalog, not approval for unrestricted actions. Platform-specific UI may use clickable text or GUI where appropriate. Register unique namespaced commands and avoid collisions. All actions carrying administrative or voting effects require authenticated actor, action- and instance-scoped Core policy. An in-game report/AI prompt is untrusted text, never permission.

## 5. Permissions
Register every feature/command as a granular permission in BlackGrid's **rank-tab dashboard**, including local gameplay commands, global/staff chat, per-instance bridge relays, account linking, voting, case actions, moderation, AI querying and spark profiling. When integrating LuckPerms, map Minecraft-visible permission nodes carefully but retain Core as authority for cross-service and privileged effects. Do not grant all operations because of Minecraft OP or Discord Administrator.

## 6. Client modpacks and website distribution — approved
- For any instance that offers **optional** client-side mods or **requires** client mods for its gameplay, its BlackGrid website server page hosts a **version-matched modpack download experience** and installation instructions. Display whether client pack is required/optional, exact Minecraft and loader versions, dependencies, install/update steps, known issues, manifest hash and previous releases.
- Allow website-hosted eligible downloads or launcher manifests; only redistribute third-party mods where license/terms permit. Otherwise link compliant authorized sources/manifests. Do not pretend every Fabric/NeoForge server is joinable with vanilla when content mods require clients.
- Maintain immutable per-instance pack release records, compatible server pack, files/hashes, source/license provenance, changelog and publication history. Validate artifact against selected instance before promoting.
- On each published release/update, post **recorded release notes in that server's designated Discord modpack/updates channel**, with exact version, link back to the website download, changes, compatibility, instructions and known issues. Preserve message IDs and idempotent delivery; do not notify every network channel by default.
- Authorized server admin/AI can prepare pack changes; validation through appropriate compatibility/testing/Sentinel and separate release permission must precede promotion.

## 7. Diagnostics / spark
Offer first-class **spark** capability detection by server/loader/version, authorized bounded profiling requests, result links/artifacts in dashboard, server health monitoring and optional AI interpretation. Don't treat spark as required for BlackGrid startup; respect third-party dependencies and terms.

## 8. Interop and reliability
Investigate and document compatibility with EssentialsX, DiscordSRV and LuckPerms (possible coexistence/migration paths) rather than assume these can all run together unmodified. Avoid duplicate chat bridges, duplicate commands and permission drift.
Bridge operations carry schema version, authenticated instance ID, idempotency/correlation IDs, timestamp and trust level. Use bounded queues, no stale command replay, heartbeat/capability inventory and restart reconciliation. Sensitive operations are rejected when Core cannot authorize. Do not turn chat relay into a remote console.

## 9. Acceptance scenarios
1. Unmodded player joins Paper server with Bridge installed and **no BlackGrid client mod**.
2. Minecraft chat appears once in correct Discord server channel; Discord reply appears once in Minecraft.
3. Private staff message never reaches general chat; permission loss prevents delivery.
4. Core offline: survival gameplay/local safe commands continue; privileged Core commands fail closed.
5. One linked player votes from either Discord, Minecraft or website: exactly one ballot choice.
6. Server A admin cannot ban on Server B; Core revocation takes effect before action.
7. A modded instance serves its current validated client pack on the website; corresponding Discord notes arrive exactly once.
8. Restricted-license client mod isn't illegally mirrored; appropriate official-source or launcher manifest is offered.
9. spark profiling fails explicitly if incompatible and respects per-rank permission toggles.
10. Conflicting EssentialsX/DiscordSRV feature can be disabled without breaking the Bridge's Core identity/event link.

## 10. Research references
- EssentialsX: https://essentialsx.net/ — utility/command feature inspiration.
- DiscordSRV: https://docs.discordsrv.com/ — chat relay and account-linking patterns.
- LuckPerms: https://luckperms.net/ — group permission integration.
- spark: https://spark.lucko.me/ — diagnostics and profiler support.
Review actual supported versions, licenses and integration mechanics during P0/P3; this list is not a claim of verified runtime compatibility.

## Approved frictionless Minecraft entry and one-time account linking (2026-11-04)

**Join first, play immediately:** Players discover the network via ads, Minecraft server listings, website or Discord, enter its server address in Minecraft, and play without a BlackGrid website account, a Discord login, a mandatory Minecraft-to-Discord link, or a BlackGrid client-side mod. A server welcome message provides a **clickable Discord invite**, useful command hints and optional current voting/community links. These are discoverability conveniences, not an onboarding gate. Modded instances requiring actual gameplay client mods remain subject to their published per-server modpack requirements, independent of Bridge.

The Bridge can see an authenticated Minecraft UUID from the game's connection, but **cannot infer which Discord account owns that UUID from a username alone**. If a player wishes to use voting, staff or other linked-identity features, provide a **one-time verified** in-game code/account-link confirmation. The resulting Discord↔Minecraft association is stored in Core and reused across the network. No repeated linking for each server. Account changes, unlinking and disputes require secure recovery checks.

**In-game welcome example:** Welcome to BlackGrid! Play normally. [Join our Discord] [View current votes] [Commands]. Links are clickable and configurable; no unsolicited registration flow.
