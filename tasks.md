# Tasks

## In Progress
- [ ] Connect frontmatter audit actions (`audit`/`dry-run`/`autofix`) to an explicit confirmation modal before `autofix`.
- [ ] Add an optional commit message input in `Grow -> Strategy` for grouped autofix commits.

## Done
- [x] Define repository content containers per project using registered `Content Sources`.
- [x] Scope Strategy analytics by `projectId` to avoid cross-project cluster/funnel contamination.
- [x] Add frontmatter governance flow in `Grow -> Strategy`:
  - `Audit frontmatter`
  - `Dry-run`
  - `Autofix` with grouped commits per `repo@branch`
  - JSON/CSV report export

## Next
- [ ] Add scheduled frontmatter audit job (nightly) per project.
- [ ] Add policy presets for required canonical fields by project type (blog, docs, mixed).
