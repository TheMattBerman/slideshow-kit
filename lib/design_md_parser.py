"""Parse DESIGN.md files: YAML front matter + markdown body."""

import os
from typing import NamedTuple

import yaml


class DesignMd(NamedTuple):
    tokens: dict
    body: str


def parse(path: str) -> DesignMd:
    """Parse a DESIGN.md file at path. Returns DesignMd(tokens, body).

    YAML front matter is delimited by lines containing only '---'. Front matter
    is optional. Body is everything after the closing '---' (or the entire file
    if there is no front matter).
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    if text == "":
        return DesignMd(tokens={}, body="")

    lines = text.split("\n")

    # Detect front matter: opening '---' must be the first non-empty line.
    first_nonempty = next((i for i, line in enumerate(lines) if line.strip() != ""), None)
    if first_nonempty is None or lines[first_nonempty].strip() != "---":
        return DesignMd(tokens={}, body=text)

    # Find the closing '---' on its own line.
    close_idx = None
    for i in range(first_nonempty + 1, len(lines)):
        if lines[i].strip() == "---":
            close_idx = i
            break

    if close_idx is None:
        return DesignMd(tokens={}, body=text)

    yaml_text = "\n".join(lines[first_nonempty + 1:close_idx])
    body_lines = lines[close_idx + 1:]
    body = "\n".join(body_lines).lstrip("\n")

    try:
        tokens = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"malformed YAML in {path}: {e}") from e

    if not isinstance(tokens, dict):
        raise ValueError(f"YAML front matter in {path} must be a mapping, got {type(tokens).__name__}")

    return DesignMd(tokens=tokens, body=body)
