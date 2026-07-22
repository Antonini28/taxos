"use client";

import { useMutation } from "@tanstack/react-query";
import { ExternalLink, Library, Quote, Search, ShieldQuestion } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/PageHeader";
import { Button, Card, ErrorState, InfoNote } from "@/components/ui";
import { ApiError, api } from "@/lib/api";

interface Passage {
  citation_ref: string;
  title: string;
  authority_rank: string;
  heading: string;
  body: string;
  url: string | null;
  score: number;
}

interface Answer {
  question: string;
  sufficient: boolean;
  passages: Passage[];
  searched_chunks: number;
  best_score: number;
  note: string;
}

const EXAMPLES = [
  "How does the domestic reverse charge for construction work?",
  "Can I recover input tax on exempt supplies?",
  "What is the difference between zero-rated and exempt?",
  "What is the corporation tax rate in Germany?",
];

/**
 * Knowledge search (FR-402/403).
 *
 * Every claim is a cited passage — the answer IS the grounded evidence, ranked by relevance
 * then authority (legislation above guidance). When the corpus cannot support the question,
 * the result is a first-class "insufficient sources" verdict showing what was searched, not
 * a thin improvised reply. Refusing to improvise is the feature.
 */
export default function KnowledgePage() {
  const [query, setQuery] = useState("");

  const ask = useMutation({
    mutationFn: (q: string) => api.get<Answer>(`/api/v1/knowledge/answer?q=${encodeURIComponent(q)}`),
  });

  function submit(q: string) {
    const trimmed = q.trim();
    if (trimmed.length < 3) return;
    setQuery(trimmed);
    ask.mutate(trimmed);
  }

  return (
    <div className="mx-auto max-w-[820px]">
      <PageHeader
        title="Knowledge"
        description="Grounded UK VAT research. Every answer cites its sources — or says it cannot answer."
      />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(query);
        }}
        className="mb-4 flex gap-2"
      >
        <div className="relative flex-1">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted"
            aria-hidden
          />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a UK VAT question…"
            className="w-full rounded-md border border-hairline bg-surface py-2 pl-9 pr-3 text-body placeholder:text-ink-muted"
          />
        </div>
        <Button variant="primary" type="submit" loading={ask.isPending}>
          Ask
        </Button>
      </form>

      {!ask.data && !ask.isPending && (
        <div className="mb-4 flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => submit(ex)}
              className="rounded-full border border-hairline px-3 py-1 text-small text-ink-secondary transition-colors hover:border-strong hover:text-ink"
            >
              {ex}
            </button>
          ))}
        </div>
      )}

      {ask.isError && (
        <Card>
          <ErrorState
            title={(ask.error as ApiError).title}
            detail={(ask.error as ApiError).detail}
            traceId={(ask.error as ApiError).traceId}
          />
        </Card>
      )}

      {ask.data && !ask.data.sufficient && (
        <Card className="p-5">
          <div className="flex items-start gap-3">
            <ShieldQuestion size={20} className="mt-0.5 shrink-0 text-status-warning" aria-hidden />
            <div>
              <h2 className="text-body font-medium">Insufficient sources</h2>
              <p className="mt-1 text-small text-ink-secondary">{ask.data.note}</p>
              <p className="mt-2 text-micro text-ink-muted">
                Searched all {ask.data.searched_chunks} passages · best match scored{" "}
                {ask.data.best_score.toFixed(3)} (below the support threshold)
              </p>
            </div>
          </div>
        </Card>
      )}

      {ask.data && ask.data.sufficient && (
        <>
          <InfoNote>
            Answer composed from {ask.data.passages.length} corpus passage
            {ask.data.passages.length === 1 ? "" : "s"}, ranked by relevance then authority.
            Every statement below carries its source — nothing is generated beyond the cited
            text.
          </InfoNote>

          <div className="mt-3 space-y-3">
            {ask.data.passages.map((p, i) => (
              <Card key={i} className="p-4">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded-sm px-1.5 py-0.5 text-micro font-medium ${
                      p.authority_rank.startsWith("A1")
                        ? "bg-accent-subtle text-accent"
                        : "bg-surface-2 text-ink-secondary"
                    }`}
                  >
                    {p.authority_rank.startsWith("A1") ? "Legislation" : "HMRC guidance"}
                  </span>
                  <span className="text-small font-medium">{p.heading}</span>
                  <div className="flex-1" />
                  <span className="text-micro text-ink-muted">
                    relevance {p.score.toFixed(2)}
                  </span>
                </div>

                <p className="text-body text-ink-secondary">{p.body}</p>

                <div className="mt-3 flex items-center gap-2 border-t border-hairline pt-2">
                  <Quote size={12} className="text-accent" aria-hidden />
                  <span className="font-mono text-micro text-accent">{p.citation_ref}</span>
                  <span className="text-micro text-ink-muted">· {p.title}</span>
                  {p.url && (
                    <a
                      href={p.url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-0.5 text-micro text-ink-muted hover:text-accent"
                    >
                      <ExternalLink size={10} aria-hidden />
                      source
                    </a>
                  )}
                </div>
              </Card>
            ))}
          </div>

          <p className="mt-4 flex items-center gap-1.5 text-micro text-ink-muted">
            <Library size={11} aria-hidden />
            Illustrative UK VAT corpus. Conflicts between sources are shown by authority rank
            and never resolved automatically.
          </p>
        </>
      )}
    </div>
  );
}
