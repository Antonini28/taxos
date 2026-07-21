"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bot,
  ChevronRight,
  CircleCheck,
  CircleDashed,
  Play,
  ShieldAlert,
  Stamp,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PageHeader } from "@/components/PageHeader";
import {
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  InfoNote,
  Skeleton,
  StatusBadge,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";

const ENTITY_ID = "00000000-0000-0000-0000-000000000e01";

/**
 * Agent workspace (US-401).
 *
 * Agent output renders as typed cards, not chat bubbles: each step shows which tools it
 * called, what it returned, and on what basis it was confident. And there is deliberately
 * no approve button anywhere on this page — a run hands off to a work item, and approving
 * happens there, by a different human (docs/frontend/03 §3.2).
 */

interface Step {
  sequence: number;
  agent: string;
  goal: string;
  status: string;
  tool_calls: { tool: string; [k: string]: unknown }[];
  output: Record<string, unknown>;
  confidence: string;
  confidence_basis: string;
  model: string;
  duration_ms: number;
}

interface Run {
  id: string;
  goal: string;
  state: string;
  plan: { agent: string; goal: string }[];
  requested_by: string;
  work_item_id: string | null;
  escalation: { reason: string; needed_input: string } | null;
  steps_used: number;
  budget_steps: number;
  cost_gbp: string;
  mode: string;
  steps: Step[];
}

const STATE_TONE: Record<string, "good" | "warning" | "critical" | "neutral"> = {
  HANDOFF: "good",
  WAITING_INPUT: "warning",
  FAILED: "critical",
  EXECUTING: "neutral",
  PLANNING: "neutral",
};

export default function AgentsPage() {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);

  const runs = useQuery({
    queryKey: ["agent-runs"],
    queryFn: () => api.get<Run[]>("/api/v1/agent-runs"),
  });

  const startRun = useMutation({
    mutationFn: () =>
      api.post<Run>("/api/v1/agent-runs", {
        entity_id: ENTITY_ID,
        period_key: "2026-Q2",
      }),
    onSuccess: (run) => {
      queryClient.invalidateQueries();
      setSelected(run.id);
    },
  });

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader
        title="Agent workspace"
        description="Agents prepare the work and stop at a human. Every step records what it called and why."
        asOf="live"
        actions={
          <Button
            variant="primary"
            size="sm"
            loading={startRun.isPending}
            onClick={() => startRun.mutate()}
          >
            <Play size={14} aria-hidden />
            Run VAT cycle for Q2
          </Button>
        }
      />

      <div className="mb-4">
        <InfoNote>
          Running in <strong>deterministic mode</strong>: the orchestration, tool grants,
          budgets, escalation and tracing are real, while narratives come from templates
          rather than a language model. The figures are identical either way — they come
          from the rule engine, which is the point of the separation.
        </InfoNote>
      </div>

      {startRun.isError && (
        <Card className="mb-4">
          <ErrorState
            title={(startRun.error as ApiError).title}
            detail={(startRun.error as ApiError).detail}
            traceId={(startRun.error as ApiError).traceId}
          />
        </Card>
      )}

      <Card>
        <CardHeader title="Runs" description="Most recent first." />
        {runs.isLoading && (
          <div className="space-y-2 p-5">
            <Skeleton className="h-10" />
          </div>
        )}
        {runs.data?.length === 0 && (
          <EmptyState
            icon={Bot}
            title="No agent runs yet"
            body="Start a VAT cycle above. The team will confirm the data, compute the return, scan for anomalies, and hand off for review."
          />
        )}
        {runs.data && runs.data.length > 0 && (
          <ul className="divide-y divide-hairline">
            {runs.data.map((run) => (
              <li key={run.id}>
                <button
                  onClick={() => setSelected(run.id === selected ? null : run.id)}
                  className={`flex w-full items-center gap-3 px-5 py-3 text-left transition-colors hover:bg-surface-2 ${
                    run.id === selected ? "bg-accent-subtle" : ""
                  }`}
                >
                  <Bot size={15} className="shrink-0 text-ink-muted" aria-hidden />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-body font-medium">{run.goal}</div>
                    <div className="mt-0.5 text-micro text-ink-muted">
                      requested by {run.requested_by.replace("user:", "")} ·{" "}
                      {run.steps_used}/{run.budget_steps} steps
                    </div>
                  </div>
                  <StatusBadge tone={STATE_TONE[run.state] ?? "neutral"}>
                    {run.state.replace(/_/g, " ").toLowerCase()}
                  </StatusBadge>
                  <ChevronRight
                    size={15}
                    className={`shrink-0 text-ink-muted transition-transform ${
                      run.id === selected ? "rotate-90" : ""
                    }`}
                    aria-hidden
                  />
                </button>
                {run.id === selected && <RunDetail runId={run.id} />}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function RunDetail({ runId }: { runId: string }) {
  const run = useQuery({
    queryKey: ["agent-run", runId],
    queryFn: () => api.get<Run>(`/api/v1/agent-runs/${runId}`),
  });

  if (run.isLoading) {
    return (
      <div className="border-t border-hairline bg-surface-2 p-5">
        <Skeleton className="h-32" />
      </div>
    );
  }
  if (!run.data) return null;
  const data = run.data;

  return (
    <div className="animate-slide-in border-t border-hairline bg-surface-2 px-5 py-4">
      <div className="mb-3 flex flex-wrap items-center gap-3 text-micro text-ink-muted">
        <span className="font-mono">{data.mode} mode</span>
        <span>·</span>
        <span>
          {data.steps_used} of {data.budget_steps} step budget
        </span>
        <span>·</span>
        <span className="font-mono">£{data.cost_gbp}</span>
      </div>

      {/* The plan is visible before the steps: a reviewable plan is what makes an
          autonomous run auditable rather than merely surprising. */}
      <h3 className="mb-2 text-small font-medium">Plan</h3>
      <ol className="mb-4 space-y-1">
        {data.plan.map((step, index) => {
          const executed = data.steps.find((s) => s.agent === step.agent);
          const done = Boolean(executed) || (step.agent === "reporting" && data.work_item_id);
          return (
            <li key={index} className="flex items-center gap-2 text-small">
              {done ? (
                <CircleCheck size={13} className="shrink-0 text-status-good" aria-hidden />
              ) : (
                <CircleDashed size={13} className="shrink-0 text-ink-muted" aria-hidden />
              )}
              <span className="font-mono text-micro text-ink-muted">{step.agent}</span>
              <span className={done ? "text-ink" : "text-ink-muted"}>{step.goal}</span>
            </li>
          );
        })}
      </ol>

      <h3 className="mb-2 text-small font-medium">Steps</h3>
      <ol className="space-y-2">
        {data.steps.map((step) => (
          <li
            key={step.sequence}
            className="rounded-md border border-hairline bg-surface p-3"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-sm bg-surface-2 px-1.5 py-0.5 font-mono text-micro">
                {step.agent}
              </span>
              <span className="flex-1 text-small font-medium">{step.goal}</span>
              <StatusBadge
                tone={step.status === "COMPLETED" ? "good" : "warning"}
              >
                {step.status.toLowerCase()}
              </StatusBadge>
            </div>

            {typeof step.output.narrative === "string" && (
              <p className="mt-2 text-small text-ink-secondary">
                {step.output.narrative}
              </p>
            )}

            {Array.isArray(step.output.observations) &&
              (step.output.observations as string[]).length > 0 && (
                <ul className="mt-1.5 space-y-1">
                  {(step.output.observations as string[]).map((note, i) => (
                    <li key={i} className="flex gap-1.5 text-small text-ink-secondary">
                      <span className="text-ink-muted">·</span>
                      {note}
                    </li>
                  ))}
                </ul>
              )}

            {Array.isArray(step.output.findings) &&
              (step.output.findings as { type: string; severity: string; detail: string }[]).map(
                (finding, i) => (
                  <div
                    key={i}
                    className="mt-1.5 flex items-start gap-2 rounded border border-hairline bg-surface-2 px-2 py-1.5"
                  >
                    <ShieldAlert
                      size={13}
                      className={`mt-0.5 shrink-0 ${
                        finding.severity === "HIGH"
                          ? "text-status-serious"
                          : "text-ink-muted"
                      }`}
                      aria-hidden
                    />
                    <div>
                      <span className="font-mono text-micro text-ink-muted">
                        {finding.type}
                      </span>
                      <p className="text-small text-ink-secondary">{finding.detail}</p>
                    </div>
                  </div>
                ),
              )}

            <div className="mt-2 flex flex-wrap items-center gap-3 border-t border-hairline pt-2 text-micro text-ink-muted">
              <span className="flex items-center gap-1">
                <Wrench size={10} aria-hidden />
                {step.tool_calls.map((call) => call.tool).join(", ") || "no tools"}
              </span>
              {/* Confidence always with its basis — a bare percentage says nothing
                  about whether a number was computed or guessed. */}
              <span className="font-mono">
                {step.confidence_basis.toLowerCase()} ·{" "}
                {(Number(step.confidence) * 100).toFixed(0)}%
              </span>
              <span className="font-mono">{step.duration_ms}ms</span>
            </div>
          </li>
        ))}
      </ol>

      {data.escalation && (
        <div className="mt-3 rounded-md border border-status-warning/40 bg-status-warning/10 p-3">
          <h4 className="text-small font-medium">Run parked — human input needed</h4>
          <p className="mt-1 text-small text-ink-secondary">{data.escalation.reason}</p>
          <p className="mt-1.5 text-small">
            <strong>To unblock:</strong> {data.escalation.needed_input}
          </p>
          <p className="mt-2 text-micro text-ink-muted">
            The run did not estimate the missing data or compute a partial return. It
            resumes from this point once the gap is filled.
          </p>
        </div>
      )}

      {data.work_item_id && (
        <div className="mt-3 flex items-center gap-3 rounded-md border border-status-good/30 bg-status-good/10 p-3">
          <Stamp size={16} className="shrink-0 text-status-good" aria-hidden />
          <div className="min-w-0 flex-1">
            <h4 className="text-small font-medium">Handed off for human review</h4>
            <p className="mt-0.5 text-small text-ink-secondary">
              The run ends here by design. Approval requires a second person and happens
              in the approvals queue.
            </p>
          </div>
          <Link
            href="/work/approvals"
            className="shrink-0 rounded-md border border-hairline bg-surface px-2.5 py-1 text-small transition-colors hover:border-strong"
          >
            Open approvals
          </Link>
        </div>
      )}
    </div>
  );
}
