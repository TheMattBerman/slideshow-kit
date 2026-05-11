# Style System (v0.6.0+)

The style system is how slideshow-kit drives consistent visual identity across
carousels. Each brand has a `styles/` directory of named selectables; the
daily loop generates one carousel per style per trend per day.

## Concepts

**Style:** a directory under `<brand>/styles/<name>/` containing:
- `DESIGN.md`: YAML token block + markdown rationale (Google open-source spec)
- `refs/*.png`: 1-5 visual reference images (loaded into gpt-image-2 image_input)

**Brand layer:** `<brand>/visual-system.md`, also DESIGN.md-shaped. Provides
brand-default tokens (palette, typography, etc.) that styles inherit unless
they override.

**Kit default:** `references/styles/social_native/`. Used when a brand has no
`default_style` set and the run has no `--style` override.

## Token inheritance

At runtime the resolver merges three layers in this order (later wins):

1. Kit defaults (hardcoded in `lib/style_resolver.py`)
2. Brand layer (`<brand>/visual-system.md` YAML)
3. Style layer (`<brand>/styles/<name>/DESIGN.md` YAML)

Each token resolves independently. Missing token at any layer falls through
to the next. The `extends` key in style YAML controls inheritance:

- `extends: brand` (default): inherit unspecified tokens from brand layer
- `extends: kit`: skip brand layer; inherit only from kit defaults

## DESIGN.md schema

YAML keys (kit-recognized):

| Key | Type | Purpose |
|---|---|---|
| `name` | string | The style identifier (snake_case, matches dir name) |
| `extends` | "brand" or "kit" | Inheritance source |
| `palette.background` | hex string | Primary background color |
| `palette.primary_accent` | hex string | Highlight / emphasis color |
| `palette.text` | hex string | Body and headline text color |
| `typography.heading_family` | string | Font family for headlines |
| `typography.heading_weight` | string | Font weight for headlines |
| `typography.heading_size_pt` | number | Headline size in points |
| `typography.body_family` | string | Font family for body |
| `typography.body_weight` | string | Body weight |
| `typography.body_size_pt` | number | Body size in points |
| `typography.emphasis` | string | Emphasis treatment ("underline + accent_color", "bold", etc.) |
| `layout.grid_cols` | number | Layout grid column count |
| `layout.hero_position` | string | "top", "top-left", "center", etc. |
| `layout.density` | string | "low", "medium", "high" |
| `image_treatment` | string | "minimal_flat_icons", "screenshot_native", "photo_grid", etc. |
| `ui_chrome.pill_tags` | bool | Whether to render pill-shaped UI tags |
| `ui_chrome.position` | string | "top_corners", "bottom_corners", etc. |

Forward-compatible: unknown keys pass through to the resolved token bundle and
the prompt. Add new keys as styles need them.

## Authoring a style

For users, style authoring should feel like a short visual interview. Do not
start by telling them to run a command. Ask:

1. "What kind of reusable carousel style do you want: branded, social-native,
   thread/native text, or more than one?"
2. "Describe the style in 1-3 sentences."
3. "Do you have 1-5 visual examples? You can provide screenshots, PNGs, links,
   or say `no examples`."
4. "Should this become the default style, and should it run every day?"

The agent then turns the answers into files under
`<brand>/styles/<style-name>/` and updates `config.json` as needed.

Use `scripts/add_style.sh` internally to scaffold the directory:

```bash
./scripts/add_style.sh --brand matt --style dickie_bush_narrative \
  --description "dark navy + red accents, stat-driven case study" \
  --refs ref1.png,ref2.png
```

Three input modes:

1. **Description only:** the host agent generates DESIGN.md from the prose; synthesizes one visual ref via gpt-image-2 to lock the gestalt.
2. **Refs only:** the host agent uses vision on the supplied refs to extract palette, typography grammar, layout pattern, image treatment.
3. **Both:** description steers, refs anchor. Best results.

The script scaffolds the dir + a stub DESIGN.md. The host agent then runs the
style-extraction prompt (below) to populate tokens and rationale. The user
should experience this as "I made the style and here is the summary," not as a
CLI task.

### Style lanes

Use these lanes to translate user language into starter tokens:

| Lane | Typical `image_treatment` | Ask for |
|---|---|---|
| Branded | `branded_typography`, `minimal_flat_icons`, `photo_grid` | Palette, type, layout, brand examples |
| Social-native | `iphone_candid` | Recurring person, environment, wardrobe, neutral face refs |
| Thread/native text | `screenshot_native` | Platform feel, density, background/text preference |

The style name should be snake_case and specific enough to pick later:
`branded_editorial`, `iphone_candid_founder`, `thread_native`, etc.

### Agent prompt contract for style extraction

When invoked by `add_style.sh`, the host agent should:

1. Read the operator's description (if provided).
2. Analyze any refs in `<style>/refs/*.png` using the host's vision capability.
3. Extract:
   - Palette (3-5 hex values)
   - Typography (heading + body family, weight, size)
   - Layout grammar (grid, hero position, density)
   - Image treatment (one of the recognized strings, or a new descriptor)
   - UI chrome (pill tags, badges, etc.)
4. Write a complete DESIGN.md to `<style>/DESIGN.md`, replacing the stub.
5. Ask which style should be `default_style` and which should be in
   `styles_per_day`; update `<brand>/config.json`.
6. Confirm the result with the operator before declaring done.

## Listing styles

```bash
./scripts/list_styles.sh <brand>
```

Outputs the brand's `default_style` and a list of available styles with ref
counts and the (default) marker.

## Daily loop integration

`config.json` fields:

- `default_style` (string, required after init): the brand's primary style
- `styles_per_day` (array of strings, optional): styles to render per trend per day; defaults to `[default_style]`

The daily loop iterates over `styles_per_day` and produces one carousel per
(style x trend) pair.

## Per-run override

```bash
./scripts/run-daily-loop.sh --brand matt --style social_native
```

The `--style` flag wins over `default_style` for that single run.

## Common errors

- `style 'X' not found in <brand>/styles/X or <kit>/references/styles/X`: the named style does not exist in the brand or in the kit's reference styles. Check spelling; run `list_styles.sh` to see available styles.
- `[WARN] <style>/refs missing; generating without visual refs`: the style has no refs; generation will still work but quality may suffer. Run `add_style.sh --force` with refs to repopulate.
- `malformed YAML in <path>`: front matter is invalid. Check indentation and quoting.

## Migration from v0.5.x

v0.5.x -> v0.6.0 is a breaking change. The recommended path:

1. Pull v0.6.0.
2. For each existing brand workspace: re-run `scripts/init_brand.sh <slug> --force`. This overwrites the brand workspace with the new shape (DESIGN.md-shaped visual-system.md, populated styles/ dir, updated config.json). Your existing brand-voice and brand-perspective markdown files are preserved if they exist (they are not touched by init_brand).
3. Optionally run `scripts/add_style.sh` to author additional styles per brand.

There is no auto-migration script. Pre-live status accepts the manual cost.
