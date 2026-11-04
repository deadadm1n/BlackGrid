# BlackGrid — Security and privacy

**Status:** required safety invariants; no implicit authorization from a vote or AI output.

## 8. Security, resilience and privacy requirements
- Web auth: secure cookies, CSRF protections, strict server-side RBAC/ABAC, WebAuthn and recovery controls, request throttling, audit.
- Network: internal-only OpenCode and supervisor; minimal exposed endpoints, TLS, secure Discord interaction verification, short-lived service credentials.
- Sandbox: non-root containers, CPU/RAM/PID/IO caps, per-instance file scopes, no privilege escalation, no general network reachability without need. Untrusted plugins/mods are executable code: compatibility and provenance review, allowlisting and isolation are required.
- Prompt injection: taint external text; strongly delimit tool context, typed tool schemas, independent policy enforcement, permission scoping, adversarial tests. Cannot guarantee no injections; guarantee no privilege follows from the text alone.
- Backups: separate protected backup storage, retention policy for critical world assets, monitored capacity, periodic restore proof, restricted deletion privileges outside AI/governance.
- Disaster: management access through independent local recovery; platform can be restored from backed-up DB/config/volumes without OpenCode.
- Owner-controlled website replacement: existing blackgrid.online deployment can be superseded; take config/credential/data inventory first, no irreversible cutover in PRD phases.
- Privacy: Discord player messages and tickets are sensitive; use minimal collection, access controls, redaction, retention and transparency; avoid collecting unnecessary private DMs.