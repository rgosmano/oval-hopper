# Oval Hopper

A Python entry for Builders Mech Royale (`mechfight/1`). The mech follows reachable waypoints toward the next game circle, stops inside eligible supply rings, and uses the game's jump and jet controls when movement stalls. It reads the arena from the organizer's read-only mount during initialization. It uses only the Python standard library.

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

The tests exercise a blocked corridor, bridge clearance, a disconnected courtyard, supply capture and recovery after a stall. The official checker measures protocol and timing on a recorded stream. Placement is measured in the organizer's interactive practice matches.

## Submission

Publish the contents of this directory as the root of the public GitHub repository and enter its URL on the [Mech Royale track page](https://www.joinbuilders.org/buildathon/tracks/builders). The scorer supplies the arena. The image uses a digest-pinned Python base.

## Credits

Builders supplied `mechfight.py` and the Python example used in `starter.py`. The example has an import guard so the new controller can reuse its actions and the tests can compare its movement. The navigation, supply-drop controller and tests were developed with OpenAI Codex. Original contributions are licensed under MIT.
