# AI Studio — End User Compute

Cursor authors the prompts and skills in this repository. AI Studio runs them.

The default model is MiniMax. Record each prompt version in `agents/VERSIONS.md`.

## Layout

| Path | What it holds | Git |
|------|----------------|-----|
| `agents/` | Lean Studio prompts | committed |
| `skills/` | One folder per skill | committed |
| `documentation/` | Published agent-family pages | committed |
| `docs/` | Local notes for Cursor, including the ingested Studio docs | ignored |
| `plans/` | Local design plans | ignored |
| `.workspace/` | Local mirror of the Studio workspace | ignored |
| `dist/` | Optional skill zips | ignored |
| `.cursor/rules/` | Authoring rules | ignored |

Customer data stays under `.workspace/`. Do not commit it.

Test a skill against that mirror with `--workspace` when the script supports it.
