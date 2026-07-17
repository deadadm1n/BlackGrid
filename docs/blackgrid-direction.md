# BlackGrid direction

BlackGrid is not just one Minecraft server.

The cleaner direction is:

```text
BlackGrid = gaming community and server-hosting lab
WatchDog = server wrapper/control plane
AetherReach = first Minecraft server under BlackGrid
WatchDog Helper = Minecraft-side helper mod
```

## What BlackGrid should feel like

BlackGrid should feel like a gaming community first, with enough infrastructure behind it to grow into a learning-friendly server host.

The community-facing version can stay simple:

> BlackGrid is a gaming community that plans to grow into multiple servers over time.

The behind-the-scenes version is bigger:

> BlackGrid is a place where people can try different game servers, learn how hosting works, experiment, and build communities without needing to already know every cursed server-hosting detail.

## What should change in the repo

The repo should slowly stop presenting itself as only an ATM11/Minecraft project.

That does not mean ripping out Minecraft. Minecraft/AetherReach is the first real server, so it stays important.

It means the naming and docs should make the layers obvious:

- BlackGrid owns the brand/community/platform direction.
- WatchDog owns server process control and automation.
- AetherReach owns the Minecraft server identity.
- WatchDog Helper owns Minecraft-only bridge features.

## What should not happen yet

Do not turn this into fake enterprise hosting software before the basics work.

Do not promise public server rentals before there is real capacity, billing policy, abuse policy, isolation, backup strategy, and support expectations.

Do not make WatchDog depend on Minecraft-only assumptions unless it is inside a Minecraft plugin/helper path.

## Good next steps

1. Add a server profile concept to docs before building the full system.
2. Keep `config/wrapper.yaml` working for AetherReach/ATM11.
3. Add example profiles later, such as:
   - `aetherreach-atm11.yaml`
   - `minecraft-vanilla-example.yaml`
   - `source-server-example.yaml`
4. Move Minecraft-specific parsing/update behavior toward Minecraft-specific plugins.
5. Keep the web panel generic enough that it says “server” more often than “Minecraft,” except where Minecraft auth/features are actually required.

## Public wording

Use this style when talking to the community:

> BlackGrid has been quiet for a bit, but it is not dead. The goal is still to be a gaming community, but I want it to grow into something bigger than one server. Long term, I want BlackGrid to become a place where people can try different game servers, learn how hosting works, experiment, and build communities. AetherReach is where it started. WatchDog is the wrapper/control layer being built behind it.

No giant corporate speech. No fake launch hype. Just tell people where it is going.
