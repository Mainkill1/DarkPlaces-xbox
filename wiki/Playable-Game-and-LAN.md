# Playable Nexuiz and LAN — Option B

## Approved product

On 2026-09-16 the owner selected **Option B: a fully playable Nexuiz Classic game
with offline play and LAN hosting/joining**, while retaining automatic demo loops
and the continuous mixed-world benchmark. This supersedes the original
benchmark-only product definition; a map viewer or demo-only program is not the
finished game. Use Nexuiz Classic 2.5.2 as the intended content baseline, pin the
actual source/gamecode/content hashes in issue #26, and preserve the desktop
reference build.

This page defines requirements and architecture, **not implemented capability**.
The smoke built from source `d9ede38a` reached a visible ready screen in the user's
xemu screenshot (uptime 18111 ms). That establishes a user-observed diagnostic
boot, not a DarkPlaces host/game boot, a hardware run, or a soak test. PRs #31–#34
are merged at `3e273cb6a0fd96914c809c3b505de70d309600db`; their native targets remain
diagnostics. The production Xbox engine, native renderer, audio and LAN still
require implementation and end-to-end tests.

## What counts as playable

| Requirement | Completion evidence |
|---|---|
| New Game, local bots, game mode/map/difficulty/player setup | A complete controller-only offline match |
| Real rules and simulation | Movement, collision, all required weapons, alternate fire, pickups, damage, death/respawn, scoring and match end |
| Campaign/local progression supplied by the pinned game | Progress saved and restored after a clean restart |
| Maps and modes | Full pinned-content inventory with per-item runtime status; omissions are blockers or explicit owner-approved exceptions |
| Rendering | World, actors, weapons, HUD/menu and effects required for gameplay; no invisible hazards or placeholder actors presented as completion |
| Audio | Working effects, positional cues, volume and required music, not a permanently null backend |
| LAN host and join | Hosting Xbox plays while another peer joins; roles reversed; match end and map change work |
| Recovery and persistence | Controller reconnect, failed load, cable loss, disconnect and read-only storage leave a usable UI and honest results |
| Benchmark mode | Automatic looping world, controller exit/resume, quality OFF by default and explicit settings/timing identity |

Target stock **64 MiB memory** on a homebrew-capable Original Xbox; 128 MiB is a
diagnostic profile, not a way to pass acceptance. One player per console is the
initial input model; split-screen is not included in Option B. Renderer
approximations may reduce cosmetic fidelity but must preserve gameplay, visibility,
collision and content identity. Do not silently reduce the promised content to
one map because it is the only one that fits.

## Shared engine, separate execution modes

Keep the actual DarkPlaces client, local/listen server and required QuakeC VMs.
Do not construct a second stripped-down viewer as a substitute for Nexuiz.

```text
Boot -> normal engine/configuration -> saved preferences -> automatic demo loop
Demo loop -> fresh controller press -> controller menu
Menu -> New Game -> offline match -> match end / next map / menu
Menu -> Host LAN -> listen server + local player + remote peers
Menu -> Join LAN -> discovery or entered address -> remote match
Menu -> Restart demo loop -> fixed route begins again
```

Entering New Game, Host or Join cancels attract playback. A gameplay death,
ordinary map transition, connection failure or controller disconnect must not
reactivate demos. Start in gameplay opens its menu; Start while editing stays a
navigation action. Restart Demo is deliberate outside a live match. Opening a
host's menu must not freeze connected peers. Keep existing input gating across
context transitions so the takeover button cannot also fire, select or confirm.

The menu must expose all needed fields without a keyboard, including names and
IPv4/port entry. Use bounded on-screen editing and clear network/error status.
Retain the existing graphics controls and actual cvars. Automatic quality remains
OFF by default; explicit saved ON preferences are honored. Settings survive demo
restarts, and texture resource reloads remain explicit.

## LAN architecture and boundary

Reuse `lhnet.c/.h` for addresses/connectionless sockets and `netconn.c/.h` for
connections, discovery and the existing wire protocol. Add a narrow
`DP_PLATFORM_XBOX` transport/lifecycle adapter over the pinned nxdk network stack;
do not disguise the console as desktop WinSock or replace the game protocol.
Preserve loopback for offline games, whether or not a network cable is attached.

Required LAN paths are discovery on the local subnet, manual IPv4/port join,
listen-server hosting, match/map transitions and repeated disconnect/rejoin.
Address acquisition and socket operations must be bounded/nonblocking from the
engine's perspective, with cancellation and useful errors. Support the SDK's
network configuration, including DHCP/manual addressing, without an Internet
service or account dependency. Separate would-block from actual transport errors.

The host must simulate and render locally while serving peers. Test compatible
desktop Nexuiz peers as a reference in both directions, recording the exact
protocol, engine and content identities; universal DarkPlaces/mod compatibility
is not promised. Reject mismatches explicitly. Derive published player/bot limits
from worst-case measured host load, not an invented desktop-sized constant.

Internet server browsing/advertising, matchmaking, accounts, NAT traversal/UPnP,
and automatic external downloads are outside this release. Disable their
reachable entry points rather than assuming `sv_public 0` alone disables every
client lookup or download. This is a product scope, not a claim to block every
possible routed packet. Offline mode and autoplay must work without network
initialization succeeding.

## Build, resources and renderer

Keep `xbox/Makefile` (foundation) and `xbox/inputcheck` as explicit diagnostics.
The production engine needs a distinct target/output set that actually links
`Sys_Main`/`Host_Init`, the client/server/VM/VFS and the native platform/renderer.
An early core diagnostic may omit services; those omissions must not become the
playable release profile. Do not set capability bits to enabled merely because a
backend is planned or a menu setting exists.

Preserve shared engine responsibilities and introduce native system, filesystem,
video, renderer, audio and network boundaries. Reuse `cl_attract.c`,
`cl_graphics_menu.c` and `xbox/controller_sdl.c`, not a second configuration/input
framework. Port `RENDERPATH_XBOX` with real mesh, texture, 2D, BSP/lightmap,
animation and material/effect behavior. Coverage is driven by the complete pinned
game corpus, not only the flythrough. Any current renderer prototype remains an
internal development gate rather than a smaller release promise.

The memory envelope includes **local client plus server, required VMs, bot/entity
state, collision, network buffers, SDK threads/stacks, audio, renderer resources
and loading peaks at the same time**. The single-thread engine backend does not
remove SDK background threads. Rework the old budget before committing player,
bot, texture or map limits; measure actual usable memory and fragmentation.

## Performance and benchmark behavior

Retain one continuous mixed-load world with texture, fuzz/alpha, animation/math,
geometry, effects and combined regions. Gameplay targets nominal 60 FPS where the
selected video mode permits it; this is not a universal measured guarantee or a
reason to reduce quality silently. Fixed-quality testing must expose regressions.

The planned throughput mode has no intentional cap and processes equivalent
scene work; real-time mode uses display pacing. Record effective cap, VSync,
auto-quality, manual effects, audio and workload settings separately. Adaptive
and fixed-quality results are not interchangeable, nor are demo replays and live
LAN matches. Existing menu controls/provenance are implemented components;
deterministic uncapped throughput, native GPU completion timing and scoring still
need their own implementation and evidence.

## Work ownership and final gate

The existing epic remains the roadmap; this is not a competing backlog.

| Work | Owner |
|---|---|
| Platform/core link, filesystem, normal engine boot | Issues #7–#12 |
| Measured memory, capacities, jobs and dependencies | Issues #13–#15 |
| Native graphics and whole-game material coverage | Issues #3, #16–#22 |
| Controller UI, audio, timing and content pipeline | Issues #23–#26 |
| Complete offline gameplay/campaign/content tests | [#35](https://github.com/Mainkill1/DarkPlaces-xbox/issues/35) |
| Native LAN transport, discovery and playable sessions | [#36](https://github.com/Mainkill1/DarkPlaces-xbox/issues/36) |
| Continuous stress world and unattended results | Issues #27–#28 |
| xemu/hardware end-to-end validation and release | Issues #29–#30 |

Do not close the full-game target after a textured-map demonstration. Acceptance
requires an installed package booting into autoplay without input, controller
navigation into a complete offline match, a complete LAN match with host/client
roles reversed, audio, persistence, map changes and recovery, then a return to
repeatable benchmark operation. Test the inventoried maps/modes and supported
limits on xemu and real 64 MiB hardware. Record the stage actually reached;
compile/link/boot/match/soak are different claims.
