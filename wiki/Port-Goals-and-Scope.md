# Port Goals and Scope

## Approved primary product

**Option B, selected on 2026-09-16:** a fully playable Nexuiz Classic game with
offline matches/bots, the campaign/progression supplied by the pinned game,
audio, persistent settings, controller-operated menus and LAN hosting/joining.
Automatic demo playback and the continuous mixed-world benchmark remain included.

The [playable-game and LAN design](Playable-Game-and-LAN) defines the release
contract. A map viewer, partial menu or demo-only executable is an intermediate
development gate, not the final product.

## Baseline

Stock 64 MiB memory, homebrew-capable Original Xbox launch environment, pinned
nxdk, intended Nexuiz Classic 2.5.2 baseline with actual content hashes verified,
xemu development and real-hardware acceptance. Video modes must be enumerated
and tested against the connected output; do not require unverified 480p support
to reach the menu. Keep 128 MiB testing diagnostic-only.

## Benchmark requirements retained

One continuous route passes normal geometry, visibility pressure, resident and
changing textures, alpha vegetation/fur, particles/decals, procedural math,
animation, lighting/reflections and combined-load/recovery regions. Automatic
quality defaults OFF; controller edits and explicit saved choices remain usable.
Real-time 60 FPS intent and uncapped fixed-work throughput are distinct modes,
not a reason to hide overload by changing quality or skipping scene work.

## Excluded from Option B

Internet master servers/advertising, accounts, NAT traversal and automatic external
downloads; split-screen; arbitrary modern DarkPlaces games/mods; mandatory 720p/1080i
or 128 MiB hardware; proprietary SDK material. LAN and audio are **not** excluded.
Cosmetic renderer approximations are documented per feature and may not remove
necessary actors, collision cues, gameplay or HUD information.

## Completion

A controller can leave autoplay, start and finish real offline games, host/join LAN,
change maps, use audio and saved preferences, recover from failures, and deliberately
return to demo loops. Track the full pinned map/mode/campaign corpus and measured
bot/player limits. Validate games, LAN and benchmark soaks on xemu and real 64 MiB
hardware. Do not silently omit failing content and claim a complete port.
