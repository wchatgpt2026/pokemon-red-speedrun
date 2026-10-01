# Development workflow

## Repository and branches

Work in `wchatgpt2026/pokemon-red-speedrun`. Follow [DESIGN_CHARTER.md](DESIGN_CHARTER.md)
and the current work package's scope. Start each package from the accepted state
on `master`, not from the pristine upstream baseline. WP002 uses
`wp002-development-foundation`, based on accepted WP001 commit
`42e8d83645ffe2f19e69fea3f83a0e5e86c90183`.

Before starting, run `git fetch origin`, `git status --short --branch`, and
`git log -1 --oneline`; confirm the accepted base and a clean working tree.
Create a package branch with `git switch -c <package-branch> origin/master`,
or switch to its existing branch after checking its ancestry. Never overwrite
unrelated local work.

## Build environment and commands

The supported/default project development toolchain is **RGBDS 1.0.4**, matching
upstream, `.rgbds-version`, CI, and the aligned local environment.
Check `rgbasm --version`, `rgblink --version`, `rgbfix --version`, and
`rgbgfx --version` before building.
Use a Unix-like shell with GNU Make, GCC, and the utilities used by the Makefile
(including `find` and `sha1sum` or `shasum`); WSL works on Windows. Run commands
from the repository root.

`INSTALL.md` provides environment setup instructions. Although `rgbdscheck.asm`
accepts 1.0.0 or newer, use 1.0.4 for project development. For a separate
installation, the Makefile supports `make RGBDS=/path/to/rgbds-1.0.4/`
(keep the trailing slash).

```sh
make              # Red, Blue, and Blue debug ROMs
make red          # pokered.gbc only
make blue         # pokeblue.gbc only
make clean
make              # full rebuild, including generated graphics
```

`make tidy` removes ROMs, objects, symbols/maps, patches, and compiled helper
tools while retaining generated graphics. `make clean` also removes generated
graphics. The build compiles its helper tools, assembles objects, links each
ROM with `layout.link`, and runs `rgbfix`; `.sym` and `.map` files are emitted
alongside each ROM. `make red_vc` and `make blue_vc` produce the existing VC
patches; they are not required for a normal local Red test.

## Pristine verification versus hack validation

The pristine baseline is `d2704a63c26f9ba046ade877445216b3de0519a4`
(`baseline-pokered`). Only in a separate, clean checkout of that baseline is
`make compare` expected to match `roms.sha1`. It builds the normal ROMs and VC
patches and checks their vanilla SHA-1 values.

Historically, this pristine baseline was successfully reproduced locally with
RGBDS 1.0.3 before the project aligned its development environment to upstream
1.0.4. That records a past verification, not the current toolchain recommendation.

**An intentionally modified hack ROM is not expected to pass `make compare`.**
WP002 changes shared text, so Red, Blue, and Blue debug intentionally differ
from vanilla. Do not update `roms.sha1` to hide this distinction. Validate hack
builds by successful assembly, linking, ROM generation, focused diff review,
and local play testing. There is no dedicated non-byte-identity Make check
target. CI's existing `sh .github/checkdiff.sh` checks tracked Git cleanliness,
not gameplay or ROM correctness; run it after committing, when the tree is clean.

## Git hygiene

Never commit generated `.gb`/`.gbc` ROMs, `.o` objects, `.sym`/`.map` files,
`.patch` outputs, generated `.1bpp`/`.2bpp`/`.pic` graphics, compiled tool binaries
(`tools/gfx`, `tools/make_patch`, `tools/pkmncompress`, `tools/scan_includes`,
or `.exe` files), or emulator saves/states. Existing ignore rules cover these;
do not force-add them. Keep build logs and toolchain installations outside the
tracked source tree.

Before committing, review `git diff`, run `git diff --check`, and stage only
the package's explicit files. Inspect `git diff --cached --stat` and
`git diff --cached` to confirm scope and absence of generated artifacts. Commit
with a clear package message, then run `sh .github/checkdiff.sh` and
`git status --short --branch`. Push with `git push -u origin <package-branch>`
and confirm the remote branch matches the commit. Record the toolchain, commands,
results, manual test status, and any limitations in the package report.

## Local ROM test and WP002 marker

Open the freshly built `pokered.gbc` in a local Game Boy emulator. Start a new
game to avoid resuming an old save state or cached ROM. Complete the opening,
leave the player's house, and read the Pallet Town town sign at map coordinates
`(7, 9)` by facing it and pressing A. It displays:

```text
PALLET TOWN
WP002 hack build
journey await!
```

The sole source edit is the middle line of `_PalletTownSignText` in
`text/PalletTown.asm`. It fits the text box and preserves the original text
commands, other lines, and terminator. It also appears in Blue builds because
the text is shared. Confirm the marker renders and closes normally, then check
that normal movement and Oak's opening sequence still work. Keep saves/states
local and report whether this manual test was actually performed.
