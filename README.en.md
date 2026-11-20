# NIMBY Rails Speed Limit Patch

[简体中文](README.md)

Experimental Windows patch raising the **track mod loader cap** from 600 to 1200 km/h for one exact executable build. Python standard library only; no third-party dependencies.

## Status

Static analysis, actual executable patching and verification, in-memory reversal and incompatible-file rejection have passed. **In-game operation above 600 km/h has not been verified.** This does not change every track to 1200: each layer's `[TrackLayer] max_speed` still applies. Train capability, power, curves and manual limits still apply. Set a manual track limit to 0 to disable that additional limit. No DRM or Steam authentication code is changed.

## Compatibility

Original executable SHA-256 (official version label has not been verified):

```text
2668b2580d890c0c2b6d0b7befb8069891c15f39ea12917ac8fa26bd06a14eb9
```

Patched SHA-256:

```text
4f20a8b769e6b313bceeaf11e3b6b79debaa7efcea6d3e942106f60e57bc1722
```

Other builds or unrelated modifications are rejected. Never reuse these offsets blindly after an update.

## Usage

Requires Windows and Python 3.9+. Close the game, download the source, and replace the example directory below with your installation:

```powershell
py -3 patch.py status --game-dir "D:\Games\NIMBY Rails"
py -3 patch.py selftest --game-dir "D:\Games\NIMBY Rails"
py -3 patch.py apply --game-dir "D:\Games\NIMBY Rails"
py -3 patch.py restore --game-dir "D:\Games\NIMBY Rails"
```

Alternatively, put this project folder directly inside the game directory and use the `.cmd` launchers. These use system Python and do not require Nimby3D.

Applying creates `NimbyRails.exe.speed-limit-original.bak` beside the game executable. Keep this backup and do not upload it. The tool also recognizes the identical previously patched executable and can create a hash-verified original backup from it.

Restart the game and test on a disposable map with a long straight track, a sufficiently fast train and a suitable track mod. Manual limits can still cap speed. Steam updates or file verification may overwrite the patch. Do not restore an old backup over a newer executable.

## Implementation

The track loader clamps `max_speed` to 10–600 km/h, then converts to m/s. Loader instruction RVA: `0x4034DB`; independent double constant RVA: `0xAAD1A8`. Full static disassembly showed one reference to that double constant, in the track loader.

Only this double changes from 600.0 to 1200.0; shared float constants are untouched. The tool maps RVAs through PE sections, checks the loader signature and whole original-file hash, validates the backup, replaces via a same-directory temporary file and verifies the written result.

`selftest` requires your own compatible game installation; it checks conversion, reversal and incompatible-file rejection in memory, without writing files or launching the game.

## Contributing and license

Report game version, executable SHA-256, command and error. New builds require fresh analysis and reversible/in-game validation. Do not submit executables, game assets, backups, saves or credentials.

MIT applies to this project's original code and documentation only, not to game binaries or assets. Unofficial; not affiliated with Weird and Wry. No game executable or assets are distributed.
