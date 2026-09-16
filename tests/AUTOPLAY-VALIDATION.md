# Autoplay and controller validation

The local implementation passed 45 discovered host tests, including the actual
portable policy, engine adapter compiled with test doubles for engine services,
SDL virtual-controller hotplug/mapping tests, and package generation. No test
claims execution of an original Xbox console or a real Nexuiz world.

Run the suite with a host C compiler, Python 3.10+, and SDL2 development headers:

```sh
DP_REQUIRE_SDL_TESTS=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
```

`tests/test_xbox_autoplay.py` compiles real implementation sources. The engine
harness exercises startup, demo completion, looping, malformed-header failure,
signon timeout, button takeover/consumption, menu resume, disconnect and context
changes. The virtual controller uses the Original Xbox driver's raw layout and
SDL's semantic mapping, including White/Black and independently mapped triggers.

`tests/test_xbox_autoplay_package.py` verifies automatic `xbox-benchmark.cfg`
generation from explicitly selected demos, explicit order, missing-selection
failure, path/count/command-length limits, source-config collision detection,
byte limits, and reproducible output.

The CI workflow also links the real SDL adapter and policy into the independent
`xbox/inputcheck` XBE/XISO. This is a controller diagnostic, not the DarkPlaces
engine. The foundation smoke source and its branch are unchanged.

The normal desktop `sdl-release` build is a separate regression gate. Actual
Nexuiz content, whole-engine nxdk link, native video integration, rendered demo
playback, and physical-controller testing remain unverified until those gates
are executed. See `wiki/Autoplay-and-Controller.md` for the full behavior and
remaining integration boundary.

The checksum-verified source-transfer helper has been removed. Retained CI
workflows have read-only repository permissions and do not modify the branch.
