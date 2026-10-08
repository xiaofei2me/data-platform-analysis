## Agent skills

### Data safety

`source/` contains collected DataWorks and MaxCompute Snapshot data and must be treated as immutable input.

See `docs/agents/data-safety.md`.

Agents must not modify, delete, overwrite, rename, move, or clean files under `source/` during development, testing, refactoring, or analysis work.

### Issue tracker

Issues live as markdown files under `.scratch/<feature>/` in this repo. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout (root `CONTEXT.md` + `docs/adr/`). See `docs/agents/domain.md`.
