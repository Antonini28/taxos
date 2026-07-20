## What & why

<!-- One paragraph. Link the issue. If this changes architecture, link the ADR (new or updated). -->

Closes #

## Type

- [ ] Feature  - [ ] Fix  - [ ] Refactor  - [ ] Docs  - [ ] Infra  - [ ] Security  - [ ] Prompt/eval  - [ ] Pack content

## Checklist (delete rows that don't apply — reviewers verify the rest)

- [ ] Tests added/updated; **bugfix PRs: the regression test was reviewed failing first**
- [ ] All state changes go through `AuditedUnitOfWork`; new tables have `tenant_id` + RLS policy
- [ ] New/changed endpoints: authz guard, problem+json, idempotency key (POST), OpenAPI complete, route tests
- [ ] New events added to the catalogue; consumers idempotent
- [ ] Migration follows expand→migrate→contract; `downgrade()` tested
- [ ] Prompt/rubric/registry changes: `just evals a=<agent>` green; eval thresholds hold
- [ ] Pack changes: citations present; golden scenario added; signed on publish path
- [ ] UI: all four states (loading/empty/error/success) implemented; axe clean; dark mode checked
- [ ] Docs/guides updated in this PR (not "later")
- [ ] No new dependency without licence check + justification below

## Screenshots / evidence

<!-- UI: light+dark screenshots. Perf-relevant: before/after run output. Evals: score table. -->

## Reviewer notes

<!-- Where to start reading; anything you want challenged. -->
