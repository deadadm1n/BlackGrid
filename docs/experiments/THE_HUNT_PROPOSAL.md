# Experiment 001 — THE HUNT (proposal only)

**Status:** IDEA / PENDING COMMUNITY VOTE — NOT APPROVED FOR IMPLEMENTATION  
**Owner of submission:** Human server owner, manually via Discord  
**System under test:** BlackGrid's Discord proposal → ballot → vote → audit flow  
**IMPORTANT:** Do not build, provision, schedule, deploy, install a plugin, create a live ballot, or automatically post this proposal. This document is a parked idea for a future manual submission. No implementation work is authorized by this note.

## Pitch

**THE HUNT** — *It's just Minecraft.*

A vanilla-looking Minecraft survival server with **one custom gameplay plugin**: an AI-driven chicken intelligence system (working name **ChickenGPT**). At first, chickens look ordinary. As players interact with the world, the chickens learn, remember, cooperate, and may develop unexpected counterstrategies. The concept is a humorous emergent-AI experiment, not a scripted boss encounter.

## Intended concept (subject to later voting and design)

- One gameplay plugin only, handling chicken perception, available in-game actions, individual memory, flock-level shared knowledge, coordination and learned planning.
- Chickens may eventually learn to pick up items, use weapons or mechanisms, infiltrate buildings, and counter players *within Minecraft gameplay*, if permitted by the plugin action interface. These abilities require implementing them; they are not provided by vanilla chicken mobs.
- Log encounters and deaths as training examples; an offline evaluation/fine-tuning pipeline could use outcomes to improve later ChickenGPT model checkpoints. Recording a death alone does not train an LLM.
- Shared model with separate individual and flock memories, rather than a separate heavy language model per chicken. Event-triggered inference and resource ceilings would be necessary.
- In-world consequences may be surprising or destructive, but the chicken system gets **no access** to BlackGrid control plane, host, permissions, credentials, or protected backups. Test checkpoints with Sentinel before any production deployment.
- Genuine subjective sentience is **not** assumed or promised. The avian visual-pathway research (DOI: 10.1002/cne.25558) is anatomical inspiration, not a complete chicken brain or working consciousness model.

## First test: community vote, not construction

1. When BlackGrid's Discord voting system actually exists, the owner will **manually submit** this concept as a proposal from Discord.
2. BlackGrid should handle normal proposal intake, scope validation, announcement, appropriate electorate, ballot duration, tally, administrator veto/cancellation, and audit trail according to the PRD.
3. The first test passes if the proposal is processed correctly and the system records the community's decision. **Do not treat a test vote as permission to autonomously implement THE HUNT.** Any future implementation requires a separately explicit owner authorization and normal project/security gates.
4. No Discord post or vote is to be created until the owner manually submits it.

## Short Discord proposal text (for owner to copy later)

**Proposal: THE HUNT**  
*It's just Minecraft.*

Create an experimental, vanilla-looking survival server with one custom gameplay plugin: chickens controlled by a learning AI. Chickens develop memories, share experiences, learn from deaths, and gradually discover how to use the Minecraft world against players. No scripted chicken uprising—let unexpected behavior emerge. Gameplay stays isolated from BlackGrid's administrative systems and protected backups.

**This is a vote on the concept only, not authorization to begin development or deployment.**
