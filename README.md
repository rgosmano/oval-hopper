# Oval Hopper

A Python entry for Builders Mech Royale (`mechfight/1`). Oval Hopper collects cubes, opens visible game crates and chooses health or mobility upgrades. It explores reachable tiles within a wide circle, steers away from groups of game avatars and prioritizes the zone as it closes. It stops for supply captures and keeps energy in reserve between sprints. The bot reads the organizer's map at startup and uses only the Python standard library.

## Reproduce the checks

Run from this repository in Linux with the [official kit](https://www.joinbuilders.org/buildathon/tracks/builders) extracted to a sibling directory named `mechfight-kit`.

```sh
python3 -B -m unittest discover -v
docker build --platform linux/amd64 -t oval-hopper .
python3 ../mechfight-kit/check/check.py --map-dir /arena -- \
  docker run --rm -i --platform linux/amd64 --network none \
  --cpus 1 --memory 512m --memory-swap 512m --pids-limit 128 \
  --read-only --cap-drop ALL --tmpfs /tmp:rw,size=64m --user 65534:65534 \
  -v "$(cd ../mechfight-kit/arena && pwd):/arena:ro" oval-hopper
```

The tests exercise a blocked corridor, bridge clearance, a disconnected courtyard, supply capture, recovery after a stall, collecting cubes, upgrades and the healing timer. To compare movement with the 1.79 submission, run `python3 -B test_policy.py` from a clone containing commit `d8e123a`. It uses 12 fixed seeds for each of two 40-second flat-arena scenarios and reports cube collection and time near a moving tagger. Only official practice matches measure placement. The organizer's replay checks protocol and timing.

## Submission

Publish the contents of this directory as the root of the public GitHub repository and enter its URL on the [Mech Royale track page](https://www.joinbuilders.org/buildathon/tracks/builders). The scorer supplies the arena. The image uses a digest-pinned Python base.

## Credits

Builders supplied `mechfight.py` and the Python example used in `starter.py`. The example has an import guard so the new controller can reuse its actions and the tests can compare its movement. The navigation, supply-drop controller and tests were developed with OpenAI Codex. Original contributions are licensed under MIT.
