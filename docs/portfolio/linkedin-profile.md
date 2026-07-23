# LinkedIn Profile (paste-ready)

Everything below is ready to paste the day access returns. Order of operations: About first,
then Skills reorder, then Featured (add the article and video to Featured after they exist).

---

## 🚀 About (the "About Me" section — ~1,700 chars, fits the 2,600 limit)

> LinkedIn shows only the first ~3 lines before "…see more" — the opening two sentences are
> written to earn that click.

🚀 I build AI systems that do real work under real governance — agents that prepare, humans who decide, and evidence for everything. The most valuable thing an AI system can do is refuse: to guess, to improvise, to pretend it knows.

I started in Big Four tax technology at PwC, watching brilliant professionals lose most of their week to data wrangling while vendor decks promised an "AI transformation" that never shipped. The gap — between form-filling automation and chatbots, where AI actually *does* the work under the controls regulated industries require — is where I build.

Currently: AI Engineer at Blockchain Advisors, owning the AI capabilities of a live AI-enabled CRM platform — a RAG chatbot with confidence-thresholded human hand-off and a vision-based image-analysis pipeline behind an admin review queue — from solution design and evaluation through deployment.

Flagship project: TaxOS, an open-source enterprise agentic tax operating system. A multi-agent runtime carries UK VAT and Corporation Tax from ERP extract to a review-ready, evidence-attached state — and architecturally cannot approve its own work, because the approval endpoints don't exist on its API surface. Deterministic rule engine with HMRC-cited per-figure lineage (tax types are data-driven content packs — Corporation Tax was added with zero engine changes), hash-chained audit trail with one-click evidence packs, research that cites or refuses, and an explainable ML ladder whose supervised layer declines to train until it has enough real labels. 169 tests on real PostgreSQL, 18 ADRs, runs locally in five minutes with no API keys.

MSc Artificial Intelligence (completing Sep 2026) · Ex-PwC Tax Technology · Open to AI Engineering and Tax Technology roles.

📌 TaxOS is in Featured below — the repo, the architecture, and a 3-minute demo.

---

## 🛠️ Tech Stack (append to About, or use as its own block)

🛠️ Tech Stack
• Languages & APIs — Python, SQL, TypeScript, FastAPI, REST API design
• GenAI & LLMs — RAG pipelines with citations, prompt engineering, fine-tuning (LoRA/QLoRA/PEFT), quantisation · Claude, OpenAI (incl. vision), Gemini · Hugging Face Transformers
• Agentic AI — LangChain, LangGraph, CrewAI · multi-agent orchestration, tool grants, budgets, confidence-thresholded human hand-off
• ML & Explainability — PyTorch, TensorFlow, scikit-learn · Shapley/SHAP explanations, evaluation & calibration (ROC/AUC, precision/recall, threshold tuning), bias auditing
• Data & Infra — PostgreSQL (incl. RLS multi-tenancy & full-text search), Docker, GitHub Actions CI/CD · deployed on Render, Vercel, Hugging Face Hub · building depth in Azure AI, Kubernetes, IaC
• Frontend — Next.js / React (working knowledge)
• Responsible AI — human-in-the-loop gates, audit logging, GDPR-safe data handling, output guardrails, evidenced refusals

**Skills section — pin these top 5** (LinkedIn shows pinned skills first):
1. Artificial Intelligence (AI)
2. Large Language Models (LLM)
3. Python
4. Retrieval-Augmented Generation (RAG)
5. Machine Learning

Also add if missing: Agentic AI / AI Agents, FastAPI, PostgreSQL, Prompt Engineering, MLOps,
Tax Technology, Explainable AI (XAI), Docker, CI/CD.

---

## 📌 Featured (in this order)

**1. TaxOS — Enterprise Agentic Tax Operating System** (Link → github.com/Antonini28/taxos)
> Description: Open-source governed multi-agent tax platform: UK VAT + Corporation Tax on one
> deterministic engine, HMRC-cited lineage, an approval gate agents architecturally cannot
> reach, hash-chained audit, evidence packs, and explainable ML that refuses to pretend.
> 169 tests · 18 ADRs · runs locally, no API keys.

**2. (once posted) The article** — "I built the tax platform I wished existed when I worked in
Big Four tax technology" → feature the LinkedIn post itself.

**3. (once recorded) The 3-minute demo video** — upload natively to LinkedIn (autoplays muted;
captions are burned in per the demo script), then feature the post.

**4. Atlas AI — Private-Markets Portfolio Analytics** (Link → live Vercel URL)
> Description: Production full-stack analytics platform — ILPA-standard metrics (XIRR, TVPI/DPI/
> RVPI, PME), 23k+ price bars ingested idempotently, document RAG with citations. FastAPI ·
> PostgreSQL · React.

**5. SkinSense — AI Skin-Lesion Triage** (Link → live Vercel URL)
> Description: Clinical triage across 8 lesion classes (0.944 AUC) with a calibrated,
> sensitivity-first threshold and a RAG clinical assistant over an 8,700+ document corpus.
> Deployed end-to-end; models on Hugging Face Hub.

> Keep Featured to 4–5 items — the first two cards are what most visitors see without scrolling.
> Once the article and video exist, they take slots 2 and 3 and Atlas/SkinSense share the tail.

---

## Headline (bonus — the line under your name, 220 chars)

AI Engineer | Agentic Systems, LLM Workflows & Governed AI | Ex-PwC Tax Technology | Author of TaxOS (open-source enterprise agentic tax platform) | MSc AI

---

## Ten-minute checklist for restoration day

1. Paste the About block (incl. Tech Stack) → save.
2. Update the Headline.
3. Reorder/pin the top-5 skills.
4. Add TaxOS + Atlas + SkinSense to Featured with the descriptions above.
5. Post the article (docs/portfolio/linkedin-article.md) with the VAT-lineage screenshot; first
   comment = repo + demo links.
6. Feature the article post.
