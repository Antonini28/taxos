# 01 — Business Problem & Market Opportunity

## 1. Executive summary

Enterprise tax functions are drowning in manual, fragmented, deadline-driven work at exactly the moment regulators are digitising faster than corporates can respond. Tax teams at multinational enterprises (MNEs) spend the majority of their capacity on data collection, reconciliation, and return preparation — low-judgement work — while the high-judgement work (risk, planning, audit defence) is squeezed into whatever time remains. **TaxOS** is an autonomous, multi-agent AI platform that industrialises the low-judgement work end-to-end (data ingestion → computation → anomaly detection → filing readiness → executive reporting) under human-in-the-loop governance, so that qualified tax professionals supervise outcomes instead of producing spreadsheets.

## 2. The business problem

### 2.1 Problem statement

> Enterprise tax compliance is a high-volume, high-stakes data engineering problem being solved with spreadsheets, email, and heroics.

Concretely, a typical in-house tax function at a mid-to-large MNE faces:

| # | Pain | Evidence / mechanism | Consequence |
|---|------|----------------------|-------------|
| P-01 | **Fragmented source data** | Tax data lives in ERP (SAP/Oracle/Dynamics), payroll systems, AP/AR sub-ledgers, spreadsheets, and email attachments. Every filing cycle begins with weeks of extraction and cleansing. | 50–70% of tax team time consumed by data wrangling, not tax judgement. |
| P-02 | **Manual, error-prone computation** | VAT returns, CT computations, and WHT calculations are assembled in Excel with per-entity variations and no version control. | Restatements, interest and penalties, audit exposure. |
| P-03 | **Regulatory velocity** | Making Tax Digital (HMRC), OECD Pillar Two / GloBE, e-invoicing mandates (EU ViDA, KSA ZATCA, and similar regimes), real-time reporting. Rules change faster than manual processes adapt. | Compliance gaps discovered *after* deadlines; reactive firefighting. |
| P-04 | **No continuous risk visibility** | Fraud indicators, duplicate invoices, misclassified transactions, and anomalous vendor behaviour are found (if at all) during year-end or by the auditor. | Value leakage, fraud losses, qualified audit findings. |
| P-05 | **Audit readiness is a project, not a state** | Evidence packs are reconstructed retrospectively per enquiry (HMRC/tax-authority audits, SAO certification, CCO compliance). | Weeks of disruption per enquiry; key-person risk. |
| P-06 | **Executive blindness** | The CFO sees tax as an annual number, not a live risk surface. Effective tax rate (ETR), cash tax forecasting, and exposure quantification are quarterly, backward-looking exercises. | Poor capital allocation decisions; surprises at board level. |
| P-07 | **Talent leverage** | Skilled tax professionals are scarce and expensive; their capacity is consumed by work that does not require their judgement. | Burnout, attrition, and advisory spend leakage to external firms. |

### 2.2 Cost of inaction (illustrative model, 1,000-entity MNE group)

| Cost driver | Conservative annual estimate |
|-------------|------------------------------|
| Tax team time on manual data prep (15 FTE × 55% × £85k loaded) | ~£700k |
| External advisor spend substituting for internal capacity | £500k–£2m |
| Penalties, interest, and error remediation | £100k–£1m+ |
| Undetected AP fraud / duplicate payments (industry norm ~0.5–1% of AP spend) | Material, often unmeasured |
| Opportunity cost: reliefs/credits unclaimed, ETR unoptimised | Frequently exceeds all of the above |

The point of the model is not the exact figures — it is that **the payback argument for automation is structural, not marginal**, which is why every Big Four firm is investing heavily in exactly this category.

### 2.3 Why now (market drivers)

1. **Regulatory digitisation is mandatory, not optional.** MTD, e-invoicing mandates, SAF-T, and Pillar Two data requirements force structured, machine-readable tax data. Once the data is structured, agentic automation becomes feasible — and expected.
2. **LLM + agent maturity.** Reliable tool-calling, structured output, RAG grounding, and multi-agent orchestration frameworks (LangGraph et al.) crossed the production-readiness threshold in 2024–2025. Tax is a near-ideal domain: rule-based, document-heavy, auditable.
3. **Tax authorities are using AI first.** HMRC Connect and analogous programmes at other authorities cross-match taxpayer data at scale. Enterprises analysing their own data manually are asymmetrically exposed.
4. **Big Four productisation race.** The firms are converting advisory hours into subscription software (managed services + platforms). Demonstrating the ability to build such a platform is directly aligned with their hiring needs.
5. **Cost pressure on tax functions.** CFOs demand "more compliance with less headcount" — the classic automation adoption trigger.

## 3. Market opportunity

### 3.1 Market sizing (top-down, defensible ranges)

| Layer | Definition | Sizing rationale | Estimate |
|-------|-----------|------------------|----------|
| **TAM** | Global tax technology and tax managed-services software spend | Analyst consensus places tax tech at ~$18–20bn (2025) growing ~10–12% CAGR, driven by e-invoicing mandates and Pillar Two | ~$19bn |
| **SAM** | Tax compliance automation + tax analytics platforms for mid/large enterprises (the segment an agentic platform serves) | ~30–35% of TAM (excludes consumer, SMB point tools, pure hardware/services) | ~$6bn |
| **SOM** | Realistic obtainable share for a new enterprise platform via Big Four channel or direct, 3–5 yr horizon | 0.5–1% of SAM | $30–60m ARR potential |

*Positioning note:* as a portfolio project, the relevant "market" is also the **internal build-vs-buy conversation inside a Big Four firm** — TaxOS is deliberately shaped like an internal asset (cf. PwC Sightline, Deloitte Omnia, KPMG Digital Gateway, EY Global Tax Platform) rather than a startup SaaS, because that is the artefact a Tax Technology Director evaluates candidates against.

### 3.2 Target segments (in priority order)

1. **UK-headquartered MNE groups (500–5,000 legal entities' worth of complexity)** — subject to SAO, CCO, MTD, Pillar Two; strong HMRC-centric knowledge base fit.
2. **Big Four tax managed-services delivery centres** — the platform as an internal delivery accelerator (one platform, many clients — multi-tenancy is a first-class requirement).
3. **Large domestic corporates** with high indirect-tax volume (retail, logistics, manufacturing) where VAT/AP anomaly detection alone pays for the platform.

### 3.3 Value proposition (one sentence per stakeholder)

- **Head of Tax:** continuous compliance and a live risk surface instead of deadline-driven crises.
- **CFO:** cash tax forecasting, ETR visibility, and quantified exposure on one dashboard.
- **Tax Operations:** 60–80% of data preparation and computation automated with full audit trail.
- **Internal Audit / SAO signatory:** evidence-by-default — every figure traceable to source transaction, rule version, and approving human.
- **Big Four Partner (channel):** a deployable platform that converts one-off engagements into recurring managed-service revenue.

## 4. Guiding product principles (constraints on everything downstream)

| # | Principle | Implication |
|---|-----------|-------------|
| GP-1 | **Human-in-the-loop by design** | No filing, adjustment, or external communication is executed without explicit human approval. Agents prepare; humans approve. |
| GP-2 | **Evidence-by-default** | Every agent action, model output, and data transformation is logged immutably and traceable to source. |
| GP-3 | **Grounded, cited AI** | All tax-technical assertions must cite retrievable sources (legislation, HMRC manuals, internal policy). No uncited tax advice. |
| GP-4 | **Deterministic core, probabilistic edge** | Tax computations are deterministic, versioned rule engines. AI handles interpretation, extraction, anomaly detection, and drafting — never the arithmetic of record. |
| GP-5 | **Multi-tenant, multi-jurisdiction from day one** | Architecture must not assume one company or one tax regime, even if MVP ships UK-only. |
| GP-6 | **Assume audit** | Design every feature as if HMRC will inspect it. |

These principles are the acceptance filter for all Phase 2+ design decisions.
