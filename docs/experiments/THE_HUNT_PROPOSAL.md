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

## Research directions and uncertainties (NOT a build specification)

**Architecture is deliberately undecided.** Do not assume one LLM per chicken, a single shared LLM, a fixed action classifier, or Minecraft UUIDs as the only possible perception mechanism. Candidate approaches to compare *if separately authorized later*:

1. **Structured observations + world-state planning:** deterministic observations (entities, location, line-of-sight, inventory, blocks, events), a stateful planner and persistent memory. Baseline for efficiency and causally testable actions.
2. **Learned policy / reinforcement learning:** train behavior policies in sandboxed Minecraft scenarios using survival, exploration, tool usage, resource acquisition, coordination and death outcomes. Assess generalization and reward hacking.
3. **Small LLM as planner:** map observations and memories to structured intentions/action plans, with a deterministic plugin validating and executing only available Minecraft actions.
4. **Visual or multimodal perception:** if observations are actual pixels or vision embeddings, identity recognition and movement patterns may become meaningful tasks; Minecraft UUID lookup is then only a useful baseline, not a necessity. Requires deliberately provided visual inputs and evaluation.
5. **Hybrid agent:** fast reactive navigation/combat routines plus slower planning/model inference and individual/flock knowledge. Compare latency, GPU/RAM requirements, stability and player experience.

**Capabilities are not intelligence:** Vanilla chickens cannot wield diamond swords, operate chests, trigger TNT, or breathe dragon breath. A future *single* THE HUNT gameplay plugin must deliberately expose any such in-game mechanics as validated, rate-limited actions. Dramatic outcomes should arise through learned strategy where feasible, rather than scripted revenge. Unscripted behavior does not guarantee subjective experience.

**Identity, memory and flock knowledge:** Evaluate individually keyed entity memories, perceived visual/behavioral recognition and different scopes for shared knowledge (none, same flock, proximity, across generations). Global shared memory is an **open design question**, not an approved requirement: an administrator's hypothetical 'no global chicken memory' example does not establish a final prohibition. Keep persistence/transfer policies explicit and resource-bounded.

**Death learning:** Record observation/action/reward trajectories and context preceding death. Compare replay-only memory, supervised retrospective learning, offline preference/ranking, reinforcement learning and periodic checkpoint fine-tuning; do not imply that collecting death logs automatically changes network weights. Measure strategy improvement against fixed scripted baselines and held-out scenarios. Prevent unintended catastrophic forgetting and evaluate each checkpoint in isolated Sentinel before any authorized live deployment.

**Biology/dataset inspiration (review licenses and actual utility before using):**
- Avian visual tectofugal pathway 3D reconstruction — https://onlinelibrary.wiley.com/doi/10.1002/cne.25558 — anatomical reference, not neural weights, connectome, conscious mind or executable model.
- ChickenVerse — https://github.com/amirivojdan/ChickenVerse — chicken detection/segmentation and behavior-recognition datasets. Its published CC BY-NC-SA 4.0 licensing imposes noncommercial and share-alike conditions for adapted content; review exact sources and licensing before training or redistribution.
- Chicks4FreeID — https://huggingface.co/datasets/dariakern/Chicks4FreeID — research data relevant to visually identifying individual birds, not directly required where stable Minecraft IDs are provided. Inspect its dataset card, license, provenance and size before any download.
- These sources are **research leads only**, not authorization to ingest datasets or a claim they will improve Minecraft gameplay.

**Evaluation questions:** Can the system discover unscripted multistep tool use, retain relationships across restarts, learn from failure/death, adapt to unseen player behavior, coordinate without omniscient knowledge, and remain within practical inference cost and server TPS/MSPT limits? Use reproducible matched experiments, held-out test worlds, baseline agents and observed metrics. Do not call observed adaptation proof of sentience.

**Player and host boundaries:** The joke includes armed, destructive or dragon-breath chickens, but only *within an explicitly designated Minecraft experiment*. Never give chickens credentials, unrestricted shell, permission changes or access to host/world backups. Keep world snapshots and owner recovery independent. Do not expose players to undisclosed real-world exploitation or abuse.

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
