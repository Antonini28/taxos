# LinkedIn Article (publish-ready)

**Title:** I built the tax platform I wished existed when I worked in Big Four tax technology
**Hook image:** VAT return with lineage open (light) or executive dashboard (dark) · **Length:** ~750 words · **Tone:** practitioner, zero hype
**Status:** refreshed 2026-07-23 to cover the full build — two tax types, the complete ML ladder, 169 tests. Post as-is when LinkedIn access returns.

---

When I worked as a Tax Technology Engineer at PwC, I watched brilliant tax professionals spend most of their week doing something no one hired them for: moving data between systems, reconciling spreadsheets, and rebuilding the same computations every quarter.

Meanwhile, every vendor deck promised "AI transformation." What actually shipped was either form-filling automation or a chatbot that answered questions. Nobody shipped the layer in between — AI that *does the work*, under the governance that tax actually requires.

So I built it. It's called **TaxOS** — an enterprise agentic tax operating system — designed the way a Big Four firm would build an internal platform asset (thirteen phases, 18 Architecture Decision Records) and then actually built: **169 tests against real PostgreSQL, CI green, running locally in five minutes with no API keys.**

**What it does:** AI agents carry UK VAT *and* UK Corporation Tax from raw ERP extracts to a review-ready state — validation, deterministic computation, anomaly investigation, evidence assembly — and then stop, by design, at a human approval gate.

**The four rules that make it enterprise-grade rather than a demo:**

🔒 **Agents cannot file.** The endpoints for approval and filing don't exist on the agents' API surface. This isn't a policy — it's architecture. A prompt-injected agent can't call what isn't there. There's a test named `test_run_completes_in_handoff_never_approved`; breaking it is definitionally an architecture change.

🔢 **The AI never does the maths.** Every figure comes from a deterministic rule engine — versioned content packs citing the HMRC authority behind every rule, decimal arithmetic, reproducible bit-for-bit. LLMs reason, explain, and orchestrate around it.

📎 **Cited or refused.** Ask the research layer a question and the answer *is* the cited evidence, ranked legislation-above-guidance. If the corpus can't support an answer, it returns "insufficient sources" with what was searched — it never improvises.

⛓️ **Everything is evidence.** Every action commits atomically with a hash-chained audit record. One click on an approved return exports the evidence pack: figures, lineage, approvals bound to content hashes, agent traces, a fresh chain verification. The enquiry response that takes weeks becomes a download.

**Two things I only learned by building it:**

1. *Your architecture's claims are worthless until something tests them.* I'd claimed for months that tax types were "content, not code." Adding Corporation Tax was the test — and it exposed the one place my engine still hardcoded arithmetic. I generalised it into a formula evaluator, proved VAT output byte-identical through the reproducibility hashes, and then Corporation Tax dropped in as a rule pack: same engine, same approval gate, same evidence pack, **zero tax-specific code in the pipeline**. The claim survived, but only because I made it falsifiable.

2. *The most valuable thing an AI system can do is refuse.* The whole platform is built around honest refusal. Unknown tax codes are reported, never guessed. Research questions outside the corpus get "insufficient sources," not an improvised answer. And the fraud model's supervised layer — which learns from reviewers' dispositions — *declines to train* until it has enough real labels, and excludes "dismissed — no time to review" as censored rather than counting it as benign, because a model trained on skipped reviews learns that unreviewed means safe. Exactly backwards. Every refusal is evidenced: what was searched, what was counted, why it wasn't enough.

The ML estate runs the full cold-start ladder: explainable rules first, then an unsupervised outlier model where every score carries an **exact Shapley explanation** (the contributions sum to the score — auditable, not a black box), then the supervised layer above. It advises; a named human decides; the disposition becomes the next training label.

The full build is public: architecture, agent specifications, threat model, the deterministic engine, both tax verticals, and a demo that runs locally with no cloud account.

If you work in tax technology or AI engineering — or you've ever had to defend a platform to an audit committee — I'd genuinely value critique. Repo and a 3-minute demo in the comments.

#TaxTechnology #AgenticAI #AIEngineering #EnterpriseAI #ExplainableAI #MachineLearning #BigFour

---

**First comment (self):** 🔗 Repo: github.com/Antonini28/taxos · 🎥 3-min demo: [link] · 📐 Architecture walkthrough: docs/architecture in the repo. Built with FastAPI, PostgreSQL, Next.js, scikit-learn — 169 tests, 18 ADRs explaining why, and no API keys needed to run it.
