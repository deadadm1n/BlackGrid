# BlackGrid — Website and dashboard

**Status:** approved design direction; not implementation authorization.

### 4.1 Owner dashboard
The owner can securely log in (passkeys/WebAuthn preferred; robust recovery), inspect every managed instance, see real-time health/player counts/logs, use per-instance console, manage players, plugin/mod installations and configs, worlds/backups, files within safe server-scoped paths, network ports and templates, Discord guild topology, proposals, tickets, audit logs, permissions and policies.
Provide an **explicitly separated** emergency host terminal for owner only, with stronger re-auth and session recording/audit; it cannot be reached by AI or player-facing endpoints.
The owner can directly chat with OpenCode from the dashboard, see plans/tool calls/approvals, and terminate AI sessions.

### 4.1c Public community portal and Discord-only identity (approved product direction; documentation only)

**One website, two experiences:** Host a responsive public/community interface at `blackgrid.online` and a separately authorization-protected administration area at `blackgrid.online/dashboard`, backed by BlackGrid Core and the same authoritative data. Suggested routes: `/` (news/status/events), `/proposals` (browse/create), `/proposals/:id` (stable proposal detail), `/votes` (active ballots), `/results` (historical outcomes), `/projects` (work progress), `/servers` (fleet status), `/profile` (identity/preferences), `/rules` (rules and acceptance). Never expose secrets, internal diagnostics or admin powers from public routes.

**Authentication:** For community members, **Discord OAuth2 is the only interactive login provider**: no separate username/password registration, email-based signup or alternative social logins. Use standard Authorization Code flow with PKCE and validated state, secure server-side session handling, HTTPS and CSRF protections. Link the resulting trusted Discord user ID to the canonical BlackGrid principal and optional verified Minecraft UUID. Validate current guild membership, accepted version of community rules, eligible network/instance electorate and relevant global/scoped permissions before any proposal, comment, edit or ballot operation; being logged in alone is insufficient. Make the status and required next steps visible to users. Admins may use the same identity but high-risk dashboard actions require strong additional verification, with independent owner-only break-glass recovery preserved; that recovery is *not* a second public/community sign-in method.

**Proposal UX:** Every proposal has a permanent canonical URL and displays title, precise vote request, details, author, scope, classification (advisory/development/deployment), admin-authored constraints, impact report, discussion, current ballot, deadline, eligibility, revision history and project links as applicable. Eligible players can create proposals on the website using Vote Title, Vote Request, Request Details and 24/48/72-hour duration, edit only fields their permissions allow, view their submissions and follow/watch discussions. Include a draft flow with optional invited co-editors under explicit permission and attribution; publishing a collaborative draft does not bypass the ordinary voting or announcement workflow.

**Cross-surface consistency:** Discord, site and workers all operate on **one canonical governance service and database**. A proposal submitted from either surface creates one proposal ID, one canonical proposal version and one Discord forum/discussion binding (subject to retries). Comments and edits propagate in both directions with identity attribution and moderation enforcement; website and Discord are views of the same proposal, not separately authoritative stores. Since Discord messages may be edited/deleted, preserve a canonical audited record and explicit sync/tombstone handling without falsely displaying removed content as active. Make synchronization eventually consistent, with visible pending/failure state and idempotent retries; never lose a ballot because Discord is temporarily unavailable. Discord publication is still a mandatory precondition to the start of each new ballot round as defined in governance rules.

**Votes:** A user can cast or change their ballot from either authorized surface during the active round, but the authoritative service enforces **one current vote per verified eligible principal per ballot round**, atomically, even under concurrent Discord/web interaction. A vote change updates that ballot rather than adding another voter. Version edits invalidate the prior round and restart the timer only after its new Discord announcement succeeds. Display countdowns based on server timestamps and final results from canonical tally logic. Confirmation may be private, and disclosure of individual ballots follows the configured privacy policy.

**Discussion and moderation:** Provide website discussions linked to their Discord forum/thread counterparts; support authenticated comments, replies, report/flag, removal/moderation, audit, basic rate limiting, mentions and accessibility. Ordinary comments do not count as proposal edits and never restart the timer. AI comments are clearly marked. Discord synchronization must respect channel visibility: content from private or restricted Discord channels/tickets is never surfaced publicly.

**Community profile:** Show linked Discord and Minecraft identities, rules acknowledgement, server membership/eligible scopes, proposal history, follows, notifications and privacy controls. Support permissioned notification subscriptions and avoid exposing private voting choices to other members.

**Shared API and security:** Public pages may expose intentionally public aggregate information to visitors, but mutations require a valid account, membership and permissions. Enforce role/scope rules and rate limits at Core API, not UI. Ensure the owner dashboard is inaccessible to ordinary members even if they guess its URL; verify Discord role state independently where relevant. API origin checks, structured audit, event/outbox delivery, anti-replay and bot/website error handling are required. Discord outage degrades synchronization with clear indicators but does not take the website or backend down; new ballots still await their mandatory announcement.

**Acceptance:** A valid Discord-only login works without local password creation; a nonmember or rule-unaccepted user cannot cast or create; a member creates a proposal on the site and sees one corresponding Discord forum entry; a Discord comment appears on its authorized website discussion (and vice versa), without duplications; concurrent voting on Discord and web yields one ballot per user; an authorized edit visibly supersedes the old round and triggers fresh publication and timer; Discord downtime produces pending sync rather than data loss; a member cannot access `/dashboard`; an invited coeditor cannot modify fields beyond their explicit grants.

**Scope control:** This section is a requirements addition only. Do not create a website deployment, Discord channels, live ballots, or THE HUNT gameplay from this document.

### 4.1a Live settings and AI autonomy control center (approved design)

**Core UX requirement:** Every ordinary BlackGrid runtime setting must have a discoverable, permission-controlled control in the owner/admin dashboard. Avoid config-file edits, code changes, redeployments or routine service restarts merely to adjust policy. This covers network defaults, per-instance overrides, governance, Discord, moderation, project workflows, tickets, notifications, AI behavior and budgets, plugin/update policy, monitoring, backups, and community experience. When a setting inherently needs restart/reprovisioning, label it prominently, offer a reviewed staged apply/restart workflow, and never misleadingly claim it was applied live.

**Autonomy matrix:** Display AI capabilities, current effective policy and scope (network, Discord guild, server, channel/project), with separately adjustable modes such as OFF / SUGGEST ONLY / APPROVAL REQUIRED / AUTONOMOUS for explicitly allowed operations. Examples: public replies, proposal drafting, spam cleanup, member moderation, channel organization, incident investigation, sandbox prototyping, server operations and release requests. Protect nondelegable invariants: AI cannot self-grant permissions, remove its own safeguards, access owner-only recovery, delete protected backups, or deploy unreviewed executable code. Discord bot Administrator permission does not change these Core limits.

**Live change semantics:** Changes are validated and saved centrally with version/revision, actor, time, reason, scope, before/after diff, and audit entry. Workers and bot receive revisioned updates via subscription/event plus periodic reconciliation; new authorization decisions use the latest committed policy; queued actions are revalidated before execution and newly disallowed actions are cancelled or paused. Show applied/pending/failed state, effective inherited value vs override, and drift/errors. Dangerous settings changes use reauthentication, preview/confirmation and optional staged rollout; support revert to a prior known-good configuration with a complete audit trail. Concurrent edits use optimistic locking to prevent silent lost updates.

**Settings organization:** Dashboard navigation: Overview; Fleet & Servers; Discord & Community; Governance & Proposals; Roles & Permissions; AI & Autonomy; Tasks & Projects; Plugins & Updates; Security & Moderation; Observability & Alerts; Backups & Recovery; Integrations & Secrets; Notifications; Audit & Configuration History. Offer search, contextual descriptions, safe defaults, import/export of non-secret configuration, and sensitive-role restrictions. Never disclose stored tokens/secrets to AI or unauthorized viewers; secret rotation is controlled separately.

**Access model:** Owner can see full settings subject to stronger authorization for sensitive operations. Delegated admins can modify only authorized settings in their assigned scope. Community managers can manage approved community settings without gaining infrastructure rights. AI can read only sanitized settings and request changes but cannot directly alter its own autonomy, permissions, policy root or protected settings. Settings affect all entry points consistently (web, Discord, background jobs, AI, Minecraft adapters).

**Acceptance:** Changing an allowed AI action from AUTONOMOUS to SUGGEST ONLY in the dashboard immediately blocks the next autonomous action across the bot and workers without a restart; an in-flight/queued action rechecks policy before applying; per-server override behaves correctly; a concurrent conflicting edit is rejected; audit and rollback work; a restart-required setting is shown as pending until actually applied; unauthorized users and the AI cannot escalate their own authority.

### 4.1b Additional approved product capabilities (details and thresholds for later design)

- **Onboarding and unified identity:** guided rule acceptance, Discord identity, optional/required Minecraft UUID linking per governance eligibility, current role/permission visibility, membership recovery and scope-aware access without unnecessary personal data.
- **Permission-management UX:** global/scoped role and permission matrix with previews, protected roles, effective-grants debugger, change audit, and owner-controlled delegation.
- **AI operational memory:** durable investigations, evidence provenance, decisions and confirmed outcomes with confidence, expiration/correction, access controls and data-retention policy; not a claim of subjective consciousness.
- **AI budgets:** dashboard controls for tokens/cost, concurrent tasks, inference cadence, server CPU/RAM load and project budgets; clear suspend/stop controls and alarms.
- **Governance safeguards:** voter eligibility, anti-alt review, proposal revision limits, spam controls, configurable thresholds/quorums, and moderation appeals with owner-chosen policy values rather than invented defaults.
- **Notification subscriptions:** member-selectable events, per-server/project follows, digest and urgent-only options, mention/rate limits and reliable delivery status.
- **Disaster recovery:** backup schedules and retention, configuration snapshots, restore drills, external/offline recovery and clear recovery procedures with verifiable evidence.
- **AI community presence:** an identifiable AI co-admin with configurable voice/interaction style and community context, without preferential enforcement or special voting power for favored users.
- **Investigations:** evidence-based cross-system diagnosis using logs, world state, plugin inventory, incidents, player reports and historical fixes, with privacy protections and citations to observed evidence.
- **Dependency mapping:** versioned mod/plugin/config dependencies and impact previews for removal, upgrades and compatibility changes.
- **Simulation lab:** isolated Sentinel-connected experiments for gameplay mechanics, behavior prototypes and load tests, separate from production and subject to resource limits and explicit deployment gates.
- **Community analytics:** aggregate retention/engagement/activity metrics, scoped dashboards, performance correlation, clear privacy/retention settings and no default intrusive surveillance.
- **Community events:** proposals, scheduling, reminders, reservations/capacity, event life cycle, AI-generated ideas and approved execution.
- **Self-improvement proposals:** AI may identify inefficiencies, design solutions, test changes in isolation and submit human-reviewable proposals for BlackGrid itself; no self-modification of policy enforcement or unapproved core deployment.

**Open design decisions:** Exact thresholds, defaults, identity requirements, quotas, review authority, incident retention and autonomy allowlists require a dedicated owner-approved design pass. This section records accepted feature direction, not permission for arbitrary autonomous execution or production changes.

## Role-specific endgame operating experience (proposed)

**Player:** responsive Discord-only sign-in, rules acceptance, optional verified Minecraft linking as required, server browser, proposal/discussion/voting, relevant notifications, report/appeal workflows and game access without compulsory political participation.

**Community staff:** scoped case inbox with report priority, evidence, authorized moderation actions, appeal separation, member assistance, governance constraints and staff availability. Clearly show current instance rules and what counts as a violation.

**Backend staff:** operational fleet view, telemetry, logs, dependency inventory, safe instance console, backups, rollout queue, staged modifications, resource scheduler, Sentinel results and incident handling—only within granted scopes.

**Owner:** an actionable overview showing network health, community queues, current AI operation/budgets, pending approvals, failures, settings and audit. Effective-permission inspector: who may do what, on which guild/server/project, through which role and policy revision. Explicit policy editing and emergency pause for AI; backend-only controls independent of community Discord OAuth.

**Every consequential action must explain:** initiator/trigger, rationale/evidence, granting authority, actual change and whether/how it is reversible. Avoid exposing private evidence on public pages. Player notifications are scoped and opt-in where appropriate, not indiscriminate broadcast.

## Owner-approved rank-tab permission editor (2026-11-04)

The live dashboard has **one clearly labeled tab per rank** (including community ranks, backend ranks, and AI). Within each tab show **all applicable individual permissions** organized by category (governance, moderation, Discord administration, tickets, Minecraft instance operations, backups, diagnostics/spark, AI tasks, development, deployment, settings, security, audit). Each permission has a toggle or explicit allow/deny/inherit state as appropriate, the permitted scope and a concise description of what it allows. Avoid hiding dangerous permissions in generic "admin" switches.

Display the *effective* permissions resulting from assignment, inheritance, instance/guild scope and any hard nondelegable restrictions. Changing a toggle writes a versioned audited policy revision to Core; Core rechecks permission before each consequential action and cancels or suspends revoked queued authority. Protect the role/permission editor itself from self-escalation, lockout and cross-scope leaks. Permission tabs also apply to AI moderation and AI autonomous development. All rank settings remain live-adjustable when technically possible; restart-required changes show pending status.

Voting defaults (51%, 60%, 2/3, 10% active-player quorum, optional 24h discussion, three revisions) are configurable from the governance settings view. Show each ballot's snapped rules and pause/resume state when Discord is offline.

## Approved ballot privacy and world-backup controls (2026-11-04)

Governance settings expose **live turnout visible / live YES-NO hidden until close** as the approved default, with appropriate role authorization, snapshots and audit. Public ballot components show participation and remaining voting time, never an early choice breakdown.

Server backup settings expose daily local Minecraft world/map backups and seven-day routine retention (with backups' latest verified state, disk usage, restore points, failed runs and protected snapshot exemptions). Editing backup settings requires scoped permission and a change record.
