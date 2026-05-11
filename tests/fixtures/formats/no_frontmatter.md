# HOOK
a script with no frontmatter at all defaults to narrative.

# REVEAL
when frontmatter is missing the parser falls back to the narrative format and the close action defaults to save by convention.

# SETUP
this is the v0.6.x compatibility path so existing scripts keep rendering without any edits or migration after the v0.7.0 release ships to users.

# EXAMPLES
older brand workspaces store dozens of scripts that never had frontmatter; they each route through this default path and produce the same output as before.

# OUTCOME
backward compatibility is preserved through v0.7.0 and any script written before the format system shipped continues to lint, parse, and render successfully today.

# CTA
save this if you maintain old scripts and want the migration path documented in one place for future reference.
