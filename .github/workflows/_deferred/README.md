# Deferred workflows

These are the full CI/CD pipelines specified in the Phase 8 documentation
(`docs/cloud/03-environments-and-promotion.md`): the PR gate, the main → staging → prod
promotion, and the nightly suite. They reference targets — image build and signing, helm
validation, the eval harness, Azure OIDC deploys — that belong to build phases not yet
written.

They live here as `.txt` (so GitHub Actions does not try to run them) rather than being
deleted, because the intent is real and documented. The active pipeline in
`../ci.yml` runs exactly what exists and passes today; jobs graduate from here to there
as the build catches up with the design.
