# BlackGrid

**One unified, AI-optional platform for running a community-governed Minecraft network.**

**Website:** [blackgrid.online](https://blackgrid.online) · **Project status:** PRD and architecture planning · **Repository:** `deadadm1n/BlackGrid`

> **Not yet implemented.** The capabilities below describe the intended product, not working functionality. The existing website is planned to be replaced; no production migration or deployment is part of this README.

## What is BlackGrid?

BlackGrid combines a public Minecraft network website, secure owner dashboard, multi-server hosting wrapper, native Discord integration, player governance, support tickets, monitoring, and AI-assisted operations into **one application**.

Players may propose and vote on virtually any Minecraft-related change—including adding a server, selecting its type, installing mods, resetting a world, or shutting down a server—subject to administrator authority, safety policy and available resources. Discord administrators can cancel active ballots. **Stopping or retiring a server must never delete its world.**

[OpenCode](https://opencode.ai/) powers optional AI administration, investigation and feature development. **BlackGrid Core, Minecraft instances, Discord operations, tickets, voting, backups and approved deterministic workflows must keep working when OpenCode is offline.**

## AI co-administrator and continuous improvement

BlackGrid's OpenCode-powered AI is an **active co-administrator**, not a command-only assistant. It can form evidence-based opinions, disagree respectfully, initiate investigations, propose improvements, maintain a persistent task backlog and follow up on incidents. It operates with delegated permissions—not unrestricted host access—and BlackGrid keeps running while OpenCode is offline.

Planned intelligence features include:
- **Shared knowledge across servers:** reuse verified diagnoses, compatibility findings and fixes without blindly applying them.
- **Community-created game modes:** players propose entirely new mechanics; BlackGrid searches first, then can develop and validate custom content.
- **Long-term plugin maintenance:** proactively track bugs, Minecraft version changes and updates to BlackGrid-built plugins.
- **Predictive monitoring:** spot worsening TPS, memory, save times and error patterns using native metrics and spark before failures become severe.

**Per-server voting:** Each Minecraft server gets its own local proposals, ballots, Discord announcements and eligible electorate; shared-resource and cross-server decisions use network-wide votes. Both share one governance engine, 24–72-hour voting windows, and Discord administrator veto. **Separate voting systems do not create separate governments or admin hierarchies.**

## Planned capabilities

| Area | BlackGrid will provide |
| --- | --- |
| **Owner dashboard** | Secure login, direct AI chat, per-server console, real-time logs, player/permission management, files, plugins/mods, backups, configuration, audit history and network administration |
| **Multi-server wrapper** | Create, isolate, start, stop, archive and restore multiple servers; configurable maximum *concurrently active* servers, provisioning limits and CPU/RAM/storage budgets |
| **Minecraft runtimes** | Adapter-based support, beginning with Paper; staged compatibility for Fabric and NeoForge rather than assuming their mod/plugin ecosystems are interchangeable |
| **Discord controller** | Guild/channel/role management, server-specific channels, Minecraft chat bridges, notifications, tickets and scoped votes; new servers get their Discord resources automatically |
| **Community governance** | Proposals, eligibility, network-wide and server-specific ballots, durable tallying, approval policies, execution history and Discord administrator veto |
| **Support tickets** | Private player support, evidence and diagnostics, status/appeals, optional AI triage and human escalation |
| **CurseForge API** | Search mods/modpacks/plugin listings, resolve Minecraft version and mod-loader compatibility, dependencies, file provenance and update discovery via deployment-provided API access |
| **Community custom projects** | Players can request new plugins, mods, datapacks and gameplay features. BlackGrid searches compatible existing solutions first; if none fits, OpenCode can build a tracked project in isolation, with community approval, Sentinel testing and reviewed deployment |
| **Extension lifecycle** | Manage CurseForge-sourced compatible artifacts and BlackGrid-built plugins; version pinning, auto-update policies, staged tests, safe deployments, rollback and archives |
| **OpenCode integration** | Direct dashboard conversations, diagnostics, proposed actions and development of new features in an isolated workspace; no unrestricted production authority |
| **BlackGrid Sentinel** | Temporary, player-inaccessible Minecraft test instances that check startup, logs, world health and performance before changes reach production |
| **Performance** | Native process/protocol health metrics plus **spark** profiling where supported (avoid duplicate installation where bundled) |

## Governance rules

- Every ballot must be open for **at least 24 hours and no longer than 72 hours (three days)**.
- **Every vote must be announced on Discord** before its voting clock begins. Closing and cancellation notices are also published. A notification failure blocks opening rather than silently hiding a vote.
- A verified **Discord guild Administrator** can cancel an active vote. Cancellation is recorded and published, and an associated queued action can be revoked before execution begins. Completed changes require a separate recovery/reversal workflow.
- A ballot may cover any Minecraft-related proposal, but passing it never bypasses a prohibited action, capacity cap, compatibility check or safety gate.
- Voting eligibility, quorum and approval thresholds are owner-configurable and are **not yet finalized**.
- Players can vote to stop or archive a server, **never to delete its world**.
- All votes, approvals, cancellations, results and attempted changes are auditable.

## Changes: test first, preserve worlds

For a server-changing operation, BlackGrid's planned safety pipeline is:

```text
Proposed / approved change
      ↓
Consistent world snapshot + per-file SHA-256 manifest
      ↓
Verified recovery backup
      ↓
Sentinel: isolated copy + proposed changes
      ↓
Boot / world validation / logs / spark metrics when available
      ↓
PASS? ── No → Block change and publish reason
  │
 Yes
  ↓
Apply to production with its own verified pre-change backup
      ↓
Startup, health, world-file manifest and structure checks
      ↓
PASS? ── No → Maintenance + safe rollback + Discord failure notice
  │
 Yes
  ↓
Publish success and retain audit / recovery records
```

**Hashes do not prove world health by themselves.** Minecraft can legitimately change files during startup; BlackGrid must validate region/NBT structures, logs, and expected-change scope rather than fail simply because before/after hashes differ. A vote that passes remains historically passed even when its *implementation* fails and is rolled back.

Sentinel's micro-server is a **temporary isolated test instance**, not a replacement for BlackGrid Core. Large modpacks may need substantial RAM even for a smoke test; resource shortage results in an explicit inconclusive/unavailable result, **never an automatic pass**. Testing without players cannot guarantee live-load performance.

## Automatic updates and custom plugins

Every server maintains a versioned manifest covering Minecraft, Java, mod loader, plugins, mods, modpacks, source IDs, dependencies, hashes and a last-known-good configuration. Updates may be **off**, **notify-only** (initial safe default), or **auto-stage-and-deploy**, configured per instance/package. Compatible updates go through Sentinel, backups, authorized rollout and post-start validation.

Owner/community feature requests can produce **BlackGrid-built plugins** through OpenCode. Code is developed and tested in an isolated workspace and requires an authorized release process before production. Generated code cannot change BlackGrid's core permissions or self-deploy by bypassing the approval gateway. CurseForge access is configured at deployment; BlackGrid will respect actual API access and file distribution restrictions.

### Player-requested custom development

If a player requests a feature BlackGrid cannot find in its compatible CurseForge/installed catalog, BlackGrid will create a **tracked custom project** instead of dropping the request. The intended flow is:

```text
Player feature request → Search compatible existing solutions
                               ↓
                         No suitable match
                               ↓
                  Define scope + requirements
                               ↓
                 Announced community vote
                               ↓
                OpenCode builds in sandbox
                               ↓
             Automated tests + Sentinel trial
                               ↓
               Authorized production release
                               ↓
               Versioned updates + rollback
```

Development and deployment are distinct approvals: **passing a vote may authorize creating the project, not bypassing the security review for newly generated code**. Progress, failures, and reasons are visible to the community. When OpenCode is offline, projects queue without affecting server uptime or governance.

## System architecture

```text
                    blackgrid.online
             Public portal + Secure dashboard
                           |
                     BlackGrid Core
        Auth · Resource Registry · Policy · API · Jobs
               /           |           \
         Governance      Tickets      Discord Controller
               \           |           /
                 Action / Policy Gateway
                           |
                    Host Supervisor
                           |
          +----------------+----------------+
          |                |                |
       Paper           Fabric          NeoForge
      instances       instances        instances
          |                |                |
       Worlds / plugins / mods / backups / logs
                           |
                Sentinel test instances

        OpenCode (optional) ---> authenticated Core API
        CurseForge API ------> Core catalog adapter
        spark ---------------> monitoring / profiling
```

One unified product does **not** require every function to live in one process. The core uses modular boundaries, while the supervisor, Discord worker, Minecraft instances and optional AI runtime remain independently recoverable.

### Security principles

BlackGrid treats Minecraft chat, signs/books, Discord messages, logs, tickets, external package metadata and AI output as untrusted input. An independent policy engine authorizes actions before they reach the supervisor; **OpenCode is never given unrestricted host shell, Docker socket, console, Discord secrets or database administrator access**. Prompt-injection defenses reduce risk but cannot make model manipulation impossible. Critical world data is preserved via verified backups and restorable archives, with an independent owner recovery path.

## Proposed repository structure

```text
apps/
  web/                 # Public website + dashboard
  core/                # Unified control API and domain modules
services/
  supervisor/          # Restricted instance lifecycle and recovery
  discord/             # Discord integration worker
  ai-adapter/          # Optional OpenCode session/tool bridge
  sentinel/            # Isolated validation orchestration
adapters/
  minecraft/           # Paper, Fabric, NeoForge adapters
packages/
  contracts/           # Shared API / event schemas
infra/
  docker/              # Deployment and isolation configs
docs/
  PRD.md               # Authoritative product requirements
  OPEN_CODE_HANDOFF.md # Agent planning / implementation protocol
tests/
```

*This layout is proposed, not scaffolded.*

## Roadmap

| Phase | Deliverable |
| --- | --- |
| **P0** | Architecture, threat model, contracts, technical decisions and planning review |
| **P1** | Authentication, unified app shell, database, policy, durable jobs and audit |
| **P2** | Secure supervisor, instance lifecycle, owner console, backup and resource controls |
| **P3** | Multi-instance support and Discord channel/chat integration |
| **P4** | Discord voting, proposals, notification requirements and administrator cancellation |
| **P5** | Ticket system and moderation workflow |
| **P6** | Optional OpenCode dashboard integration |
| **P7** | Capability registry and controlled AI feature development |
| **P8** | Recovery drills, security testing, monitoring and production deployment |

Sentinel validation, spark, CurseForge integration and managed updates are cross-cutting capabilities with detailed requirements in the PRD; their precise delivery-phase allocation is still to be finalized.

## Development guidance

**Read first:** [Product Requirements Document](docs/PRD.md) and [OpenCode Handoff](docs/OPEN_CODE_HANDOFF.md).

The PRD is the authoritative specification. OpenCode should first identify design gaps, propose contracts and test plans, and implement one approved phase at a time. **Do not wipe or redeploy blackgrid.online, touch existing server worlds or assert that planned features already work.**

## License

Not selected yet. Confirm licensing before accepting external contributions.
