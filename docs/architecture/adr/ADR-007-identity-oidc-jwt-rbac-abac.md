# ADR-007 — OIDC (Entra ID) + BFF sessions; layered RBAC + ABAC in code

**Status:** Accepted · 2026-07-20 · Principles: AP-5; FR-701, NFR-01/02

## Context
Enterprise buyers (and Big Four internal IT) mandate SSO + MFA via their IdP; the app must also run in demo/local without a corporate tenant. Authorisation needs role checks *and* attribute rules (entity scope, SoD, workflow state, tenant match).

## Decision
- **AuthN:** OIDC authorization-code + PKCE against **Microsoft Entra ID**; a pluggable issuer config with a bundled dev issuer for local/demo. **BFF token handling** — tokens are exchanged and held server-side; the browser gets only an httpOnly, SameSite=strict session cookie (no tokens in JS-accessible storage).
- **Sessions:** 15-min access JWT + rotating refresh; revocation denylist in Redis consulted on refresh.
- **AuthZ:** layered model (doc 07 §2): RBAC route guards → ABAC policy functions over a typed `AuthzContext` → RLS backstop. Policies are in-repo pure functions with exhaustive unit tests.
- **Service identity:** client-credentials per service; Azure Managed Identity for Azure resources (no stored cloud credentials anywhere, including CI — GitHub OIDC federation).

## Alternatives considered
1. **Roll-your-own passwords + MFA** — prohibited by enterprise reality and needless liability; the IdP owns credentials, conditional access, and MFA policy.
2. **Auth0/Okta** — fine products, but Entra is the incumbent in every target buyer; choosing it removes a procurement objection and demonstrates Azure-native fluency. The OIDC abstraction keeps others pluggable.
3. **Tokens in browser storage (SPA pattern)** — XSS-exfiltratable; BFF pattern is current OAuth2 browser-app best practice (IETF BCP recommendations).
4. **OPA/Cedar external policy engine** — expressive, auditable policy-as-data, but an extra runtime + policy-language ramp for a policy set (~dozens of rules) that typed, unit-tested functions express more verifiably today. Revisit trigger: policies shared across >1 service or customer-authored policies.
5. **Casbin / DB-driven permission matrices** — runtime-editable permissions sound flexible but make authorisation state un-reviewable (who changed what policy when?); our policies change via PR + audit trail.

## Consequences
- (+) SSO/MFA story is a checkbox in enterprise review; local demo stays friction-free.
- (+) SoD and entity-scoping rules live where they can be exhaustively tested (US-402/501 acceptance).
- (−) BFF adds a session layer to operate (Redis dependency on the auth path — already core infra).
- (−) Policy-in-code means product managers can't edit permissions at runtime → correct trade-off for a compliance platform; role *assignments* (not policies) are runtime-administered (FR-704).
