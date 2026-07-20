# Contributing to TaxOS

Thanks for your interest. This is primarily a portfolio/reference platform, but contributions — issues, discussions, and PRs — are welcome under the rules below. **Read the [developer guide](docs/guides/developer-guide.md) first**; it's the fast path.

## Ground rules

1. **The architecture is governed.** Significant design changes need an ADR (or an update to one) in the same PR — see the [ADR log](docs/architecture/README.md#adr-index). The five rules in the developer guide are CI-enforced; arguing with the linter means arguing with an ADR.
2. **Governance invariants are not negotiable by PR:** human approval gates, deterministic tax computation, audit-on-write, tenant isolation, agent capability confinement. PRs weakening these are closed with a pointer to the relevant ADR — reopen as a discussion if you think the ADR is wrong.
3. **No real data, ever.** Test fixtures come from the generator; tax content must cite its source (HMRC/legislation reference) in the pack.

## Workflow

Fork → short-lived branch → PR to `main` (template will guide you) → green checks + review → squash merge. Conventional Commits required (`feat:`, `fix:`, `docs:`, `infra:`, `sec:`, `eval:` scopes) — the changelog is generated from them. Bugfixes lead with the failing regression test.

## What's most welcome

Golden-set additions (eval fixtures, injection attempts that beat a layer, tricky VAT scenarios with cited treatment) · pack content corrections **with HMRC citations** · accessibility findings · performance findings with reproduction on the `scale` seed · documentation fixes.

## Setup & verification

```bash
just up        # full local stack (< 5 min)
just test      # fast suite — run before every push
just lint      # exactly what CI runs
```

## Conduct

Standard expectations: technical arguments, evidence over assertion, kindness in review. Security findings go through [SECURITY.md](SECURITY.md), never public issues.
