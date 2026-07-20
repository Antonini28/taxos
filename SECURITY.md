# Security Policy

## Reporting a vulnerability

**Please do not open public issues for security problems.**

Report privately via [GitHub Security Advisories](https://github.com/Antonini28/taxos/security/advisories/new) (preferred) or email **olisaanthony25@gmail.com** with subject `[TAXOS SECURITY]`.

Include: affected component, reproduction steps (seeded-data reproductions ideal), impact assessment, and any suggested fix. Please do not include real personal or client data in reports.

**Response targets:** acknowledgement ≤ 48h · triage verdict ≤ 7 days · fix SLA by severity (critical 24h from confirmation, high 7d, medium 30d — per the [vulnerability management policy](docs/security/04-security-testing.md#5-vulnerability-management)).

## Scope

In scope: the TaxOS application (API, frontend, agents, workers), its infrastructure-as-code, CI/CD workflows, and the demo deployment. Especially valued: tenant-isolation bypasses, agent capability escapes / prompt-injection chains that reach a tool call, authorisation matrix gaps, and audit-chain integrity issues — these map to the platform's core guarantees ([threat model](docs/security/01-threat-model.md)).

Out of scope: volumetric DoS against the demo environment, findings requiring compromised local machines, and third-party services (Azure, Azure OpenAI) — report those upstream.

## Safe harbour

Good-faith research against your own local deployment (`just up`) is always welcome. Against the hosted demo: no data exfiltration beyond proof-of-concept, no persistence, no disruption of other users; respecting that, no legal action will be pursued.

## Supported versions

The `main` branch and the latest release tag receive fixes. This is a portfolio/reference platform — there is no LTS commitment.
