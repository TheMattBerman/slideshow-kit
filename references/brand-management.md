# Brand Management

How slideshow-kit thinks about brands, where it stores them, and how to work with one or many.

## Mental model

A **brand** is a coherent voice + perspective + visual system. The kit treats brands as first-class concepts — never hardcoded.

Brand workspaces have this structure:

```
<brands_root>/<slug>/
├── brand-voice.md           how the brand talks
├── brand-perspective.md     what it believes (pillars, hot takes, ICP)
├── visual-system.md         palette, typography, layout, output sizes
├── config.json              postiz integrations, telegram chat_id, mode, lookback
└── runs/<YYYY-MM-DD>/       per-day run logs
```

Brand state is **user data**, not kit data. The kit never commits or distributes any brand workspace.

## Where brands live (`brands_root`)

The kit resolves the brands root in this order:

1. `$SLIDESHOW_BRANDS_ROOT` env var (absolute path or starting with `~`)
2. `brands_root` field in `~/.clawd/slideshow-kit/config.json`
3. **Default: `./brands/`** (resolved against the directory you invoke scripts from)

The default puts brand workspaces inside your cloned slideshow-kit repo at `slideshow-kit/brands/<slug>/`. That folder is gitignored, so brand state never lands in commits — but it's discoverable: `open ~/Documents/GitHub/slideshow-kit/brands/<slug>/runs/...` shows you exactly where outputs land.

Power users running multiple tools, or storing brands outside any repo, can pin `brands_root` to an absolute path:

```bash
# Option 1: shell rc
export SLIDESHOW_BRANDS_ROOT="$HOME/work/brands"

# Option 2: edit ~/.clawd/slideshow-kit/config.json
{
  "brands_root": "~/work/brands",
  "default_brand": "matt",
  "kit_version": "0.1.0"
}
```

## Single brand

```bash
cd ~/Documents/GitHub/slideshow-kit
./scripts/init_brand.sh me              # scaffolds at ./brands/me/
$EDITOR ./brands/me/brand-voice.md
$EDITOR ./brands/me/brand-perspective.md
$EDITOR ./brands/me/visual-system.md
./doctor.sh                             # verify all three are valid
./scripts/switch_brand.sh me            # set as default

# Now any workflow defaults to brand=me
python skills/branded-carousel/scripts/generate_branded_carousel.py \
  --script examples/test-script.md
```

## Multiple brands (agency pattern)

```bash
./scripts/init_brand.sh client-acme
./scripts/init_brand.sh client-beta
./scripts/init_brand.sh me
./scripts/list_brands.sh                # see all + default

# Run a workflow against a specific brand
python skills/branded-carousel/scripts/generate_branded_carousel.py \
  --brand client-acme --script /path/to/script.md
```

Each brand has its own:
- Postiz integration ids (so you publish to the right LinkedIn page)
- Telegram chat_id (so check-ins go to the right team)
- Mode (`draft` or `autopilot`)
- Lookback period for trends
- runs/ history

## Brand resolution order (which brand a workflow uses)

When a workflow needs to know which brand to use:

1. `--brand <slug>` flag
2. `$SLIDESHOW_BRAND` env var
3. `default_brand` in `~/.clawd/slideshow-kit/config.json`
4. Error: "no brand resolved — pass --brand or set a default"

## Backing up brand state

Brand workspaces are user data. Treat them accordingly:

```bash
# Backup (default brands_root)
tar czf brand-backup-$(date +%Y%m%d).tar.gz ~/Documents/GitHub/slideshow-kit/brands

# Or wherever your brands_root points
tar czf brand-backup.tar.gz "$(./scripts/_show_brands_root.sh 2>/dev/null || echo ./brands)"
```

## Removing a brand

```bash
rm -rf <brands_root>/<slug>/
./scripts/switch_brand.sh <other-slug>   # update default if needed
```

`uninstall.sh` does NOT remove brand workspaces by default. Pass `--purge-brands` only if you really want them gone.
