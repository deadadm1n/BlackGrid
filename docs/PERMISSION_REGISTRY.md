# BlackGrid — Permission registry (P0 canonical proposal)

**Status:** proposed permission namespace and role templates for engineering review. Owner approved **rank tabs and granular live toggles**, NOT individual default grants. No implementation authorization.

## Authorization semantics
Each decision evaluates verified principal + scoped role assignments + permission key + resource + action context + current policy version. Scope: network, guild/channel, Minecraft instance, world, project, ticket, incident or release. **Explicit deny and nondelegable protection override any allow**. AI additionally has OFF/SUGGEST_ONLY/APPROVAL_REQUIRED/AUTONOMOUS and hard resource/time/action budgets **per capability and scope**. Ordinary ranks use DENY/ALLOW/INHERIT with explicit effective-view resolution.

The dashboard renders **one tab per rank**, plus custom ranks and assignment UI. Show every registry key, effective state, provenance, description, scope and last change. No privilege self-grant; modify permission settings only under protected `permissions.manage` with secondary safeguards for owner-critical policies. Any permission not explicitly granted is denied.

## Proposed granular keys (namespace version 1)
| Category | Keys | Scope / effect |
|---|---|---|
| Identity | `identity.link`, `identity.unlink.self`, `identity.link.review`, `rules.acknowledge`, `members.view` | Own identity, staff review |
| Player & chat | `chat.send.local`, `chat.send.global`, `chat.send.staff`, `chat.bridge.configure`, `player.home.use`, `player.home.manage`, `player.tpa.use`, `player.warp.use` | Instance / channel |
| Governance | `vote.create`, `vote.cast`, `vote.edit.own`, `vote.edit.title`, `vote.edit.request`, `vote.edit.details`, `vote.edit.constraints`, `vote.cancel`, `vote.manage`, `vote.policy.configure`, `vote.audit.read` | Network / instance |
| Reports & moderation | `report.create`, `report.read`, `ticket.assign`, `ticket.resolve`, `ticket.appeal.review`, `moderation.warn`, `moderation.mute`, `moderation.kick`, `moderation.ban.temporary`, `moderation.ban.permanent`, `moderation.history.read`, `moderation.restore.request` | Instance / network / ticket |
| Discord | `discord.channel.manage`, `discord.role.manage`, `discord.message.publish`, `discord.message.moderate`, `discord.member.moderate`, `discord.guild.configure`, `discord.incident.publish` | Guild / channel |
| Fleet | `instance.status.read`, `instance.console.read`, `instance.console.execute`, `instance.provision.request`, `instance.start`, `instance.stop`, `instance.archive`, `instance.restore`, `instance.capacity.configure`, `instance.config.stage` | Instance / fleet |
| Backup & diagnosis | `backup.status.read`, `backup.create`, `backup.restore`, `backup.policy.configure`, `diagnostics.spark.run`, `diagnostics.logs.read`, `incident.read`, `incident.manage`, `incident.contain` | Instance / incident |
| Mods and release | `modpack.draft`, `modpack.validate`, `modpack.publish`, `plugin.install.request`, `project.plan`, `development.sandbox.run`, `release.review`, `release.approve`, `release.deploy`, `release.rollback` | Server / project / environment |
| AI and settings | `ai.ask`, `ai.task.propose`, `ai.task.run`, `ai.budget.configure`, `ai.autonomy.configure`, `settings.read`, `settings.write`, `permissions.manage`, `audit.read` | Instance / network / rank |

## Suggested rank templates — all **unapproved defaults**
- **Player:** read public server status, local chat, permitted essentials, own linking, report.create, rules acknowledgement and eligible vote.create/cast.
- **Server Admin:** player rights plus assigned-server report review and scoped moderation/change requests. No blanket network moderation or host access.
- **Network Moderator (two in current scenario):** permitted cross-server incident/ticket and moderation actions; no server-host or plugin-release authority.
- **Deadhead:** community final appeals, moderation-staff oversight, governance/community review; no implicit infrastructure root.
- **AI Administrator:** network-scoped visibility and individually configured operational permissions with each mode/budget; **no automatic grants inferred from being AI**.
- **Backend Operator / Developer:** operations and isolated development by assignment; no implied community-ban power.
- **Owner:** protected root authority with separate break-glass/recovery mechanisms and audited sensitive changes.

**Hard prohibited:** model self-permission escalation; deletion of protected world/archive, falsifying audit/votes, access to raw root credentials from AI tools, bypass of code security and independent release gates. These are not normal permission toggles.

## Tests
Evaluate explicit deny vs inheritance, multiple roles, temporary grants and expiration, scoped admins, moderator disputes, role-editor self-escalation, AI downgrade during queued action, guild Admin-specific veto rule, owner break-glass availability, and unchanged deterministic system when AI offline.
