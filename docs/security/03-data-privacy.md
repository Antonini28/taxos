# 03 — Data Privacy & GDPR

## 1. Data inventory & classification (the DPIA's backbone)

| Class | Examples | Systems | Personal data? |
|---|---|---|---|
| Transactional finance | AP/AR/GL rows, invoices | Postgres, Blob raw | Incidental (names in memo fields, sole traders) |
| Payroll-derived | Payroll tax extracts | Postgres (pseudonymised) | **Yes — special care** |
| Master data | Vendors, entities | Postgres | Vendor contacts (business context) |
| Documents | Invoices, certificates, correspondence | Blob + OCR | Yes, incidental-to-moderate |
| Knowledge B-class | Emails, internal policies | Corpus | Yes (emails) — pseudonymised pre-index |
| Platform | Users, sessions, audit | Postgres | Yes (staff identities — lawful basis: contract/LI) |
| Telemetry | Logs, traces | Log Analytics | No (PII-scrubbed by design; scrubber tested) |

## 2. PII detection pipeline (the mechanism behind "pseudonymisation at ingest")

```
ingest → field-class rules (schema-known PII columns: names, NI numbers, emails)
       → NER pass (worker, `fast`-route local model — PII detection never calls external LLM)
       → deterministic keyed pseudonyms  PSN(v) = HMAC(k_version, normalise(v))
         (same value ⇒ same pseudonym ⇒ joins/dedupe still work)
       → mapping table (pseudonym ↔ encrypted original, key-versioned, field-level
         encrypted, access = named-role + purpose + audit)
       → downstream stores, features, prompts, logs see pseudonyms only
re-identification: explicit API w/ purpose enum + RBAC (PRIVACY_REIDENTIFY) + audit;
UI shows originals only where role + purpose justify (payroll preparer sees names;
fraud reviewer sees pseudonym w/ [reveal] action that logs)
```

Precision policy: recall-biased on schema-known fields (always pseudonymise), precision-biased on free text (NER threshold + quarantine review queue for uncertain hits) — over-masking memo fields is acceptable; leaking an NI number is not.

## 3. GDPR positions (the questions a DPO asks, answered)

| Topic | Position |
|---|---|
| Roles | Tenant = controller; TaxOS operator = processor (Art. 28 DPA template in enterprise pack); sub-processors: Azure, Azure OpenAI (listed, no-training terms) |
| Lawful basis (tenant's) | Legal obligation (tax compliance) + legitimate interest (fraud prevention) — documented per processing purpose in the ROPA template |
| Purpose limitation | Purposes enumerated in config; re-identification API requires purpose; analytics on pseudonyms |
| Minimisation | Pseudonymise-at-edge; LLM context assembled by allow-listed retrievers; telemetry PII-free |
| Retention | Statutory tax retention (UK 6y+current) per record class; platform data per policy table; enforcement = scheduled job + WORM windows aligned |
| **Right to erasure vs statutory retention** | Erase the mapping, keep the evidence: destroying `k_version`-scoped mapping rows renders pseudonyms permanently unlinkable while tax records stay intact — the standard reconciliation, implemented as the `privacy-erasure` runbook with verification step |
| Access/portability (DSAR) | Mapping-table lookup → export of linked records where the person is data subject (not merely mentioned); template + runbook |
| International transfers | UK/EU residency (uksouth + ukwest; policy-enforced); Azure OpenAI UK/EU deployment; no third-country processing |
| DPIA | Required (large-scale, special-category-adjacent payroll + AI processing): the Phase 9 doc set *is* the DPIA technical annex; residual-risk register in 01 §4 |
| Automated decision-making (Art. 22) | **No solely-automated decisions with legal effect exist** — GP-1/ML-1 human gates are the compliance answer, by design, everywhere |
| Breach notification | 72h clock procedures in IR plan (doc 06); processor→controller notification template |

## 4. Encryption summary (consolidated)

Transit: TLS 1.2+ everywhere incl. intra-VNet. Rest: platform AES-256 (Postgres, Blob, Redis); CMK via Key Vault = enterprise option (module ready). Field-level: pseudonym mapping table (AES-GCM, keys in KV, versioned). Application-layer: audit chain hashes (integrity, not confidentiality); pack signatures (Ed25519). Key rotation: doc-08 cadence; pseudonym keys version-only (never delete — old mappings must stay resolvable until erasure is *requested*).
