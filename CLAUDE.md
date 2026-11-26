## Agent skills

### Issue tracker

Issues live in GitHub Issues on `zhipengzhu1-dotcom/11-26-2026-3D-Modeling` (via the `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Models

- Main session (planning, orchestration): Fable 5.2 (`claude-fable-5-2`), medium effort.
- Workers (subagents doing implementation): Opus 5.5 (`claude-opus-5-5`), medium effort. When spawning a worker, pass `model: opus` and `effort: medium`.
