# Oval Hopper

Entry for Builders Mech Royale (`mechfight/1`).

## Credit: code we brought

**Current runtime (from commit 'waiprotein fork'):** waiprotein's public MIT fork of giddygiddyboy's bot, https://github.com/waiprotein/mech-royale-bot at commit `fea5742c`, copyright (c) 2026 giddygiddyboy and (c) 2026 waihu (modifications); license in `LICENSE-waiprotein`. Our changes: ready name, flat layout, `Salt` value. Earlier commits used the giddy copy described below.

The current runtime (`main.go`, `brain.go`, `types.go`, `world.go`, `export.go`, `go.mod`) is **giddygiddyboy's public Mech Royale bot**. We use it under its MIT license, and the full license text is kept in [`LICENSE-giddygiddyboy`](LICENSE-giddygiddyboy).

- Upstream: https://github.com/justnau/giddygiddyboy-mech-royale (no longer public). We took the copy vendored under `drivers/giddy/` in https://github.com/charliescull/mech-royale-bot (MIT, copyright (c) 2026 giddygiddyboy).
- That copy contains charliescull's small hooks in `brain.go`: environment overrides `GIDDY_ENDGHOST`, `GIDDY_FFA` and `GIDDY_PRAC`, which are unset in our image. It also contains the practice late-hide rule `EndGhost`, taken from https://github.com/SandeepMadhavarapu/BattleRoyale (MIT, commit `b532564`).
- Our changes to it:
  - the bot's ready name;
  - a flat file layout, which the `Dockerfile` reassembles into the Go module;
  - any later parameter or seed ("salt") changes, which are listed in the git history after the commit that introduced the Go runtime.

Builders supplied the protocol (`mechfight-kit`, `protocol.md`).

## Earlier Python bot (our own work, no longer built)

`bot.py`, `navigation.py`, `starter.py`, `mechfight.py` and their tests are our original Python entry. It collects cubes, opens crates, picks upgrades, roams the zone ring, leads its gun shots and lobs mortars. It scored up to 4.04 in practice under an earlier scorer version. Builders supplied `mechfight.py` and the example used in `starter.py`. The navigation, supply-drop controller and tests were developed with OpenAI Codex and Claude Code. Original contributions are licensed under MIT (see `LICENSE`).

## Build and check

```sh
docker build --platform linux/amd64 -t oval-hopper .
python3 ../mechfight-kit/check/check.py --map-dir /arena -- \
  docker run --rm -i --platform linux/amd64 --network none \
  --cpus 1 --memory 512m --read-only --tmpfs /tmp:rw,size=64m --user 65534:65534 \
  -v "$(cd ../mechfight-kit/arena && pwd):/arena:ro" oval-hopper
```

Without Docker: rebuild the module layout (`mech/` for brain/types/world/export, `cmd/bot/` for main), run `go build -o mechbot ./cmd/bot`, then run `check.py -- ./mechbot`.
