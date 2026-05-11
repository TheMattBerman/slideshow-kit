"""Build gpt-image-2 prompts from script + visual system."""
import re
from typing import Dict, Any


def parse_visual_system(path: str) -> Dict[str, Any]:
    text = open(path).read()
    out: Dict[str, Any] = {"palette": {}, "typography": {}, "layout": {}, "vibe": {"avoid": []}, "output_sizes": []}

    palette_block = _section(text, "# Palette")
    for ln in palette_block.splitlines():
        m = re.match(r"-\s*([\w\s]+):\s*`?(#[0-9A-Fa-f]{3,8})`?", ln)
        if m:
            key = m.group(1).strip().lower().replace(" ", "_")
            out["palette"][key] = m.group(2)

    typ_block = _section(text, "# Typography")
    for ln in typ_block.splitlines():
        m = re.match(r"-\s*([\w\s/-]+):\s*<?([^<>]+)>?", ln)
        if m:
            key = m.group(1).strip().lower().replace(" ", "_")
            out["typography"][key] = m.group(2).strip()

    layout_block = _section(text, "# Layout")
    for ln in layout_block.splitlines():
        m = re.match(r"-\s*([\w\s]+):\s*(.+)", ln)
        if m:
            key = m.group(1).strip().lower().replace(" ", "_")
            out["layout"][key] = m.group(2).strip()

    vibe_block = _section(text, "# Vibe Rules")
    for ln in vibe_block.splitlines():
        m = re.match(r"-\s*Tone:\s*(.+)", ln)
        if m:
            out["vibe"]["tone"] = m.group(1).strip()
        m = re.match(r"-\s*Avoid:\s*(.+)", ln)
        if m:
            out["vibe"]["avoid"] = [x.strip() for x in m.group(1).split(",")]

    return out


def _section(text: str, header: str) -> str:
    m = re.search(rf"^{re.escape(header)}\s*$", text, re.MULTILINE)
    if not m:
        return ""
    start = m.end()
    next_h = re.search(r"^# ", text[start:], re.MULTILINE)
    end = start + next_h.start() if next_h else len(text)
    return text[start:end].strip()


def _common_anti_meta() -> str:
    return "NO 'Slide X of Y'. NO watermark. NO frame border. NO URLs. NO meta text."


def _vibe_clause(visual: Dict[str, Any]) -> str:
    tone = visual.get("vibe", {}).get("tone", "minimal")
    avoid = visual.get("vibe", {}).get("avoid", [])
    avoid_str = f" Avoid: {', '.join(avoid)}." if avoid else ""
    return f"Tone: {tone}.{avoid_str}"


def build_hook(text: str, visual: Dict[str, Any], size: str) -> str:
    pal = visual["palette"]
    typ = visual["typography"]
    return (
        f"HOOK slide. Canvas {size}. "
        f"Solid background, hex {pal['background']}. "
        f"ONLY the headline \"{text}\": {typ.get('headline_weight','extra-bold')}, "
        f"{typ.get('headline_case','UPPERCASE')}, massive white typography filling 70% of width, centered. "
        f"NO subtitle. NO icons. {_common_anti_meta()} {_vibe_clause(visual)}"
    )


def build_reveal(text: str, visual: Dict[str, Any], size: str) -> str:
    pal = visual["palette"]
    typ = visual["typography"]
    return (
        f"REVEAL slide. Canvas {size}. "
        f"Solid background, hex {pal['background']}. "
        f"Headline \"{text}\": {typ.get('headline_weight','extra-bold')}, {typ.get('headline_case','UPPERCASE')}, "
        f"primary line in white, secondary line in {pal['primary_accent']}. "
        f"{_common_anti_meta()} {_vibe_clause(visual)}"
    )


def build_setup(text: str, visual: Dict[str, Any], size: str) -> str:
    pal = visual["palette"]
    return (
        f"SETUP slide. Canvas {size}. Background {pal['background']}. "
        f"Headline \"{text}\" in white, {visual['typography'].get('headline_case','UPPERCASE')}. "
        f"{_common_anti_meta()} {_vibe_clause(visual)}"
    )


def build_example(number: int, headline: str, bullets: list, visual: Dict[str, Any], size: str) -> str:
    pal = visual["palette"]
    bullets_str = "\n".join(f"- {b}" for b in bullets)
    return (
        f"EXAMPLE slide. Canvas {size}. Background {pal['background']}. "
        f"Large number badge \"{number}\" in {pal['primary_accent']}. "
        f"Headline \"{headline}\" in white {visual['typography'].get('headline_case','UPPERCASE')}. "
        f"Body bullets in {pal.get('neutral', '#94A3B8')}, regular weight, sentence case:\n{bullets_str}\n"
        f"{_common_anti_meta()} {_vibe_clause(visual)}"
    )


def build_outcome(text: str, key_word: str, visual: Dict[str, Any], size: str) -> str:
    pal = visual["palette"]
    typ = visual["typography"]
    return (
        f"OUTCOME slide. Canvas {size}. Background {pal['background']}. "
        f"Headline \"{text}\": {typ.get('headline_weight','extra-bold')}, white. "
        f"KEY WORD \"{key_word}\" highlighted in {pal['secondary_accent']}. "
        f"{_common_anti_meta()} {_vibe_clause(visual)}"
    )


def build_cta(text: str, visual: Dict[str, Any], size: str) -> str:
    pal = visual["palette"]
    return (
        f"CTA slide. Canvas {size}. Background {pal['background']}. "
        f"Headline \"{text}\" in white, prominent SAVE button shape in {pal['primary_accent']}. "
        f"{_common_anti_meta()} {_vibe_clause(visual)}"
    )
