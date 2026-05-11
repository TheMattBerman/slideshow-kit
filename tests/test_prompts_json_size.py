"""Tests guarding the concept-generator prompts.json templates.

Each agent_prompt_template must stay <= 2000 chars (so it fits inside
typical Task tool prompt budgets) and the concept_generation template
must mention visual_hook so concepts include a visual through-line.
"""

import json
import os


PROMPTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "skills", "concept-generator", "prompts.json"
)
MAX_CHARS = 2000


def _load_prompts():
    with open(PROMPTS_PATH) as f:
        return json.load(f)


def test_concept_generation_prompt_under_2000_chars():
    prompts = _load_prompts()
    template = prompts["concept_generation"]["agent_prompt_template"]
    assert len(template) <= MAX_CHARS, (
        f"concept_generation template is {len(template)} chars (cap {MAX_CHARS})"
    )


def test_scene_elicitation_prompt_under_2000_chars():
    prompts = _load_prompts()
    template = prompts["scene_elicitation"]["agent_prompt_template"]
    assert len(template) <= MAX_CHARS


def test_script_draft_prompt_under_2000_chars():
    prompts = _load_prompts()
    template = prompts["script_draft"]["agent_prompt_template"]
    assert len(template) <= MAX_CHARS


def test_concept_generation_template_mentions_visual_hook():
    prompts = _load_prompts()
    template = prompts["concept_generation"]["agent_prompt_template"]
    assert "visual_hook" in template.lower() or "Visual hook" in template
