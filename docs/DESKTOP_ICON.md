# Desktop icon

ATM uses the selected **terminal toolbox** design: a white toolbox with a coral
handle and cursor, and a dark `>` prompt, on a petroleum-blue rounded tile.
The toolbox represents local management of coding tools, configuration and
skills; the terminal prompt connects it to developer tooling. It remains distinct
from NMD's network symbol and blue-purple/green palette.

The geometry preserves the displayed ImageGen B concept's handle, lid, body and
terminal symbol. The seam and stroke weights are set to remain distinguishable at
16px. The generated concept's bitmap texture is replaced by a restrained gradient
and clean geometry so every platform can reproduce the same mark. Concept images
and earlier working designs are preserved in the task evidence directory outside
the audited repository. Updating the installed application is a separate action.

## Source and exports

`apps/desktop/src/assets/app-icon.json` is the single design source: a 64-unit
canvas, rounded shapes, a round-joined terminal stroke and RGB colors. Edit this
file to change the mark. Upper and lower corner radii preserve the lid shape and
flat seam; no system font or image-processing dependency is required.
`src/icon.ts` renders it as an SVG data URL for the header and favicon.
`src-tauri/icon.rs` renders the same geometry directly at each native size,
with 4×4 supersampling and coverage-correct alpha. A larger icon is never
produced by enlarging a small raster.

The native desktop build generates ignored files in `src-tauri/icons/`:

- PNG: 16, 20, 24, 32, 48, 64, 128, 256, 512 and 1024 pixels.
- `icon.png`: the 256px default window icon.
- `icon.ico`: eight PNG-compressed frames, 16–256px, for Windows.
- `icon.icns`: standard and Retina entries, 16–1024px, for macOS.

These are build outputs, not authoring inputs. Do not hand-edit them or add
binary images to the audited source manifest. The build no longer contains
an independent key drawing or platform-specific palette. Existing output
bytes are left untouched when the generated contents match.

To export on any platform without starting the desktop or requiring native GUI
libraries (the ordinary Cargo dependency cache is still needed):

```sh
cargo run --locked --offline -p atm --no-default-features --example export_icons
# Optional destination follows --:
cargo run --locked --offline -p atm --no-default-features --example export_icons -- /tmp/atm-icons
```

Normal desktop builds regenerate these resources automatically. Tauri's base
configuration selects the PNG, ICO and ICNS; the macOS bundle configuration
continues to select ICNS. Complete portable desktop packages include these resources in `icons/`, so a
launcher can reference its installed release without depending on a source
checkout. CLI-only packages omit them. The Linux window embeds the PNG. Updating an
already-installed launcher or its icon cache is a separate deployment action.

## Verification

```sh
cargo test --locked --offline -p atm --no-default-features --test icons
npm run check
npm test
npm run build
```

The icon test decodes the exported PNGs, verifies ICO/ICNS entries and dimensions,
checks transparent antialiased corners and the 16px handle opening, lid seam,
terminal chevron and coral cursor, and verifies
that a repeated export preserves both bytes and modification times. The native
GUI smoke also checks that the header image loads and agrees with the favicon.
Inspect actual-size exports on light and dark backgrounds after design changes.
Container checks on Linux do not constitute native Windows Explorer or macOS
Finder/Dock acceptance; check those on their respective platforms before release.
