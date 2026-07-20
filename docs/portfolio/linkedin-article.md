# LinkedIn Article (publish-ready)

**Title:** I designed the tax platform I wished existed when I worked in Big Four tax technology
**Hook image:** executive dashboard (dark) · **Length:** ~700 words · **Tone:** practitioner, zero hype

---

When I worked as a Tax Technology Engineer at PwC, I watched brilliant tax professionals spend most of their week doing something no one hired them for: moving data between systems, reconciling spreadsheets, and rebuilding the same computations every quarter.

Meanwhile, every vendor deck promised "AI transformation." What actually shipped was either form-filling automation or a chatbot that answered questions. Nobody shipped the layer in between — AI that *does the work*, under the governance that tax actually requires.

So I designed and built it. It's called **TaxOS** — an enterprise agentic tax operating system — and I built it the way a Big Four firm would build an internal platform asset: thirteen phases from product discovery to deployment, 18 Architecture Decision Records, and documentation an auditor could walk through.

**What it does:** autonomous AI agents carry UK VAT compliance from raw ERP extracts to a review-ready state — data validation, deterministic computation, anomaly investigation, drafting with citations — and then stop, by design, at a human approval gate.

**The four rules that make it enterprise-grade rather than a demo:**

🔒 **Agents cannot file.** The endpoints for approval and filing don't exist on the agents' API surface. This isn't a policy — it's architecture. A prompt-injected agent can't call what isn't there.

🔢 **The AI never does the maths.** Tax figures come from a deterministic rule engine — versioned, signed content packs citing the HMRC guidance behind every rule, reproducible bit-for-bit. LLMs reason, explain, and orchestrate around it.

📎 **Cited or refused.** Every tax-technical claim resolves to a source passage, or the platform says "insufficient sources" and escalates. Refusing to improvise is a feature.

⛓️ **Everything is evidence.** Every action — human or agent — commits atomically with a hash-chained audit record. One click exports the evidence pack: figures, lineage, approvals, agent traces, citations. The enquiry response that takes weeks becomes a download.

**What I learned building it:**

1. *Governance is the product.* The hard part of enterprise AI isn't the agents — it's making their work reviewable, attributable, and reversible. Trust is an architecture problem, not a prompt problem.

2. *Determinism and intelligence belong in different components.* The moment I separated "computes the number" from "explains the number," everything downstream — testing, audit, reproducibility — got dramatically simpler.

3. *Boring choices need receipts.* I rejected Kafka, GraphQL, Neo4j-on-day-one, and fine-grained microservices — each with a written ADR recording the trigger that would change the answer. Restraint documented is judgement; restraint undocumented looks like ignorance.

4. *Evaluation is the release gate.* Prompt changes that regress the golden-answer sets don't merge. AI quality became a CI concern, like test coverage — which is exactly where it belongs.

The full build is public: architecture, agent specifications, threat model, the design system, and a demo that runs locally in five minutes with no API keys.

If you work in tax technology, AI engineering, or you're just curious what "enterprise-grade agentic AI" looks like beyond the buzzword — the repo and a 3-minute demo are in the comments. I'd genuinely value critique, especially from people who've had to defend a platform to an audit committee.

#TaxTechnology #AgenticAI #AIEngineering #EnterpriseAI #LLM #MachineLearning #BigFour

---

**First comment (self):** 🔗 Repo: github.com/Antonini28/taxos · 🎥 3-min demo: [link] · 📐 Architecture walkthrough: [link]. Built with FastAPI, LangGraph, PostgreSQL, Next.js, Azure — and 18 ADRs explaining why.
