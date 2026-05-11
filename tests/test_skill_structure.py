import os
import re
import yaml
import pytest

KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_frontmatter(path: str) -> dict:
    text = open(path).read()
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}


def body(path: str) -> str:
    text = open(path).read()
    m = re.match(r"^---\n.*?\n---\n", text, re.DOTALL)
    return text[m.end():] if m else text


def all_skill_files():
    out = []
    skills_dir = os.path.join(KIT_ROOT, "skills")
    candidate_dirs = [KIT_ROOT]
    if os.path.isdir(skills_dir):
        for entry in os.listdir(skills_dir):
            sub = os.path.join(skills_dir, entry)
            if os.path.isdir(sub):
                candidate_dirs.append(sub)
    for d in candidate_dirs:
        p = os.path.join(d, "SKILL.md")
        if os.path.isfile(p):
            out.append(p)
    return out


@pytest.mark.parametrize("path", all_skill_files())
def test_skill_has_required_frontmatter(path):
    fm = parse_frontmatter(path)
    assert "name" in fm, f"{path}: missing name"
    assert "description" in fm, f"{path}: missing description"
    assert isinstance(fm["description"], str), f"{path}: description must be string"
    assert len(fm["description"]) <= 1024, f"{path}: description over 1024 chars"


@pytest.mark.parametrize("path", all_skill_files())
def test_skill_description_has_dont_use_for(path):
    fm = parse_frontmatter(path)
    desc = fm.get("description", "")
    assert "do NOT use for" in desc.lower() or "do not use for" in desc.lower(), \
        f"{path}: description should include 'do NOT use for' clause"


@pytest.mark.parametrize("path", all_skill_files())
def test_skill_body_under_500_lines(path):
    lines = body(path).splitlines()
    assert len(lines) < 500, f"{path}: body has {len(lines)} lines (limit 500)"


@pytest.mark.parametrize("path", all_skill_files())
def test_skill_body_no_xml_tags(path):
    forbidden = re.search(r"<(essential_principles|intake|routing|workflow|examples)\b", body(path))
    assert not forbidden, f"{path}: contains XML tag {forbidden.group(0) if forbidden else ''} (use markdown headings)"
