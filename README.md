# BlackGrid

**A community-governed Minecraft server operated by AI, with Discord as its control center.**

> Status: planning / foundation. No deployed Minecraft server, Discord bot, or AI administrator exists yet.

## Vision

BlackGrid aims to automate routine Minecraft server operations, support and event management while giving community members transparent control over changes through Discord proposals and votes.

The AI is an **operator**, not an unrestricted owner. Governance rules, permissions, and auditable policies constrain every write action.

## Primary capabilities

- **Discord-first governance:** submit proposals, discuss them, validate voter eligibility, vote once per eligible person, enforce quorum/thresholds, publish results, and retain an audit trail.
- **AI-managed tickets:** open private tickets, classify and summarize evidence, suggest/perform permitted remedies, escalate sensitive disputes, allow appeals, and track resolution.
- **Minecraft bridge:** a Paper plugin sends server events and exposes a strictly allowlisted command/configuration interface to BlackGrid Core.
- **Operations:** health, TPS, player counts, crashes, log alerts, backups, safe restarts, and configuration change verification.
- **Community events:** AI-generated event suggestions and scheduling, with policy-gated execution.
- **Model flexibility:** local-first inference with a pluggable provider interface.

## Architecture

```text
Discord <--> Bot (Python/discord.py) <---> BlackGrid Core (Python/FastAPI)
                                                   |
                       +---------------------------+------------------------+
                       |                           |                        |
                 Governance                  Ticket manager           AI planner
                       |                           |                        |
                       +---------------------------+------------------------+
                                                   |
                                               PostgreSQL
                                                   |
                                        Policy + Action Gateway
                                                   |
                                      Paper plugin (Java) <--> Minecraft
                                                   |
                                     Backups, monitoring, logs
```

**Critical boundary:** The AI emits *structured action requests*. A deterministic policy engine validates identity, authorization, action parameters, approval/vote requirements, cooldowns, and impact before an executor touches the server. Raw shell, arbitrary console command, and unrestricted filesystem access are not AI tools.

## Governance defaults (initial proposal; configurable)

1. Eligible voters must link their Discord account to a Minecraft UUID. Eligibility and anti-sybil rules are enforced before voting.
2. Proposals have statuses: draft → discussion → ballot → passed/rejected → scheduled → executed/failed/rolled_back.
3. Only one active vote per eligible voter per proposal; changing a vote replaces the old one before ballot close.
4. Public votes use a recorded opening, closing, tally, quorum, and threshold. Set precise values via a governance configuration before public launch.
5. Low-risk approved changes can be executed automatically after validation and backup. High-impact changes (world reset, economy wipe, role/permission changes, sensitive sanctions) need an additional owner approval or are explicitly prohibited.
6. The AI never counts its own vote, silently changes voting rules, or executes failed proposals.
7. Results and each attempted action are logged with actor, rationale, authorization, outcome, and rollback information.

## Ticket workflow

Open → triage → gather context → AI recommendation → automatic safe action **or** human escalation → resolution → appeal/reopen. Ticket contents and evidence are access controlled. AI recommendations are distinguishable from verified facts. Bans and sensitive accusations require suitable review.

Example Discord commands to implement: `/ticket open`, `/ticket status`, `/propose`, `/vote`, `/proposal status`, `/server status`, `/link`.

## Security and reliability

- Discord and Minecraft are untrusted input surfaces. Messages, books, signs, chat, and uploaded evidence cannot override system policies.
- Never expose Discord tokens, model keys, RCON passwords, or database credentials in source or AI prompts. Prefer the authenticated Paper plugin to unrestricted RCON.
- Role-based permissions, service authentication, rate limits, idempotent jobs, and transaction-safe ballot counting.
- Data retention limits and privacy rules for player logs and tickets.
- Backups must be tested for restore. Config changes include dry-run validation, canary when possible, restart coordination, and rollback.
- AI inference can fail: Minecraft stays playable, Discord votes remain durable, and no action runs without authorization.

## Suggested repository layout

```text
apps/
  discord-bot/
  core-api/
plugins/
  blackgrid-paper/
packages/
  contracts/
infra/
  docker/
docs/
  architecture/
  governance/
  security/
tests/
```

## Development roadmap

**Phase 1 — Foundation:** repo scaffolding, Compose stack, database migrations, Discord bot, Paper plugin handshake, health endpoints, secrets/config.

**Phase 2 — Tickets:** private threads/channels, ticket states, AI triage, review and appeal flow, audit logs.

**Phase 3 — Governance:** Minecraft–Discord account linking, proposals, eligibility, votes, tallies, policy-authorized execution and reversals.

**Phase 4 — AI operations:** structured tool interface, monitor-only mode, automated low-risk remediation, backups and failure recovery.

**Phase 5 — Events and economy:** event director, NPC/community interactions, governed economy and game-rule changes.

## Definition of first playable milestone

A player can join Minecraft, link their Discord ID, open a private support ticket, propose a harmless server-setting change, vote, view a transparent result, and see a *policy-approved* change applied with an audit log. This milestone does not require granting AI blanket administrator privileges.

## Licensing

To be decided before accepting external contributions.
