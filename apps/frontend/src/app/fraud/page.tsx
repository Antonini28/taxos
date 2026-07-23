"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CircleCheck,
  CircleX,
  Flag,
  GraduationCap,
  RadarIcon,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
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
 * Fraud & Risk Centre (US-801).
 *
 * The explanation is the hero: a reviewer decides on "why flagged" before "which rows",
 * so it renders first and in plain language. Disposition reasons come from the API's own
 * taxonomy — a structured label, never a free-text box — and the UI is honest that a
 * dismissal for "no time" is a different signal from a genuine acceptance.
 */

interface Anomaly {
  id: string;
  document_ref: string;
  detector: string;
  anomaly_type: string;
  severity: string;
  explanation: string;
  evidence: Record<string, string>;
  status: string;
  disposition_reason: string | null;
  dispositioned_by: string | null;
}

interface Summary {
  open: number;
  confirmed: number;
  dismissed: number;
  high_open: number;
}

interface Reasons {
  confirm: Record<string, string>;
  dismiss: Record<string, string>;
}

interface Attribution {
  feature: string;
  value: number;
  contribution: number;
}

interface RiskScore {
  document_ref: string;
  counterparty: string;
  score: number;
  rank: number;
  percentile: number;
  reason: string;
  model_version: string;
  attributions: Attribution[];
}

const FEATURE_LABEL: Record<string, string> = {
  log_net: "amount (size)",
  vat_ratio: "VAT-to-net ratio",
  is_round: "round amount",
  counterparty_zscore: "vs. counterparty's usual",
};

interface FeatureImportance {
  feature: string;
  contribution: number;
}

interface ModelStatus {
  sufficient: boolean;
  model_version: string;
  note: string;
  n_confirmed: number;
  n_true_negative: number;
  n_censored_excluded: number;
  min_per_class: number;
  model_auc: number | null;
  baseline_auc: number | null;
  beats_baseline: boolean | null;
  feature_importance: FeatureImportance[];
}

const SEVERITY_TONE: Record<string, "critical" | "serious" | "neutral"> = {
  HIGH: "critical",
  MEDIUM: "serious",
  LOW: "neutral",
};

export default function FraudPage() {
  const queryClient = useQueryClient();

  const summary = useQuery({
    queryKey: ["anomaly-summary"],
    queryFn: () => api.get<Summary>("/api/v1/anomalies/summary"),
  });
  const anomalies = useQuery({
    queryKey: ["anomalies"],
    queryFn: () => api.get<Anomaly[]>("/api/v1/anomalies"),
  });
  const reasons = useQuery({
    queryKey: ["disposition-reasons"],
    queryFn: () => api.get<Reasons>("/api/v1/anomalies/reasons"),
  });
  const riskScores = useQuery({
    queryKey: ["risk-scores"],
    queryFn: () =>
      api.get<RiskScore[]>(
        `/api/v1/anomalies/risk-scores?entity_id=${ENTITY_ID}&period_key=2026-Q2`,
      ),
  });
  const modelStatus = useQuery({
    queryKey: ["model-status"],
    queryFn: () => api.get<ModelStatus>("/api/v1/anomalies/model-status"),
  });

  const runScan = useMutation({
    mutationFn: () =>
      api.post("/api/v1/anomalies/scan", { entity_id: ENTITY_ID, period_key: "2026-Q2" }),
    onSuccess: () => queryClient.invalidateQueries(),
  });

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader
        title="Fraud & risk centre"
        description="Explainable rules over the validated population. The detector advises; you decide."
        asOf="live"
        actions={
          <Button size="sm" loading={runScan.isPending} onClick={() => runScan.mutate()}>
            <RadarIcon size={14} aria-hidden />
            Scan Q2
          </Button>
        }
      />

      {summary.data && (
        <div className="mb-4 grid grid-cols-2 gap-4 md:grid-cols-4">
          <Stat label="Open" value={summary.data.open} />
          <Stat
            label="High severity open"
            value={summary.data.high_open}
            tone={summary.data.high_open > 0 ? "critical" : undefined}
          />
          <Stat label="Confirmed" value={summary.data.confirmed} />
          <Stat label="Dismissed" value={summary.data.dismissed} />
        </div>
      )}

      <Card>
        <CardHeader
          title="Anomaly queue"
          description="Highest severity first — ordered by what to look at, not by insertion."
        />

        {anomalies.isLoading && (
          <div className="space-y-2 p-5">
            <Skeleton className="h-24" />
          </div>
        )}
        {anomalies.isError && (
          <ErrorState
            title={(anomalies.error as ApiError).title}
            detail={(anomalies.error as ApiError).detail}
            traceId={(anomalies.error as ApiError).traceId}
            onRetry={() => anomalies.refetch()}
          />
        )}
        {anomalies.data?.length === 0 && (
          <EmptyState
            icon={ShieldAlert}
            title="No anomalies"
            body="Run a scan above. A clean result is a scan that found nothing — recorded distinctly from a scan that never ran."
          />
        )}
        {anomalies.data && anomalies.data.length > 0 && (
          <ul className="divide-y divide-hairline">
            {anomalies.data.map((anomaly) => (
              <AnomalyRow key={anomaly.id} anomaly={anomaly} reasons={reasons.data} />
            ))}
          </ul>
        )}
      </Card>

      {riskScores.data && riskScores.data.length > 0 && (
        <Card className="mt-6">
          <CardHeader
            title="Model risk score — advisory"
            description="Rung 2: an unsupervised model surfaces statistical outliers the rules do not encode. It advises, never decides — a reviewer weighs the score and its reason."
          />
          <div className="px-5 pb-2">
            <InfoNote>
              Each score is explained by <strong>exact Shapley values</strong> — the features
              below sum to the anomaly score, so the reason a line was flagged is auditable,
              not a black box. Model{" "}
              <span className="font-mono text-micro">{riskScores.data[0].model_version}</span>.
            </InfoNote>
          </div>
          <ul className="divide-y divide-hairline">
            {riskScores.data.map((s) => (
              <RiskScoreRow key={s.document_ref} score={s} />
            ))}
          </ul>
        </Card>
      )}

      {modelStatus.data && <SupervisedStatusCard status={modelStatus.data} />}
    </div>
  );
}

function SupervisedStatusCard({ status }: { status: ModelStatus }) {
  return (
    <Card className="mt-6">
      <CardHeader
        title="Supervised model — Rung 3"
        description="Learns from your dispositions: a confirm is a positive, a reason-coded dismissal a true negative. Censored dismissals (no time to review) are excluded, never counted as benign."
      />
      <div className="px-5 py-4">
        {!status.sufficient ? (
          <div className="flex items-start gap-3">
            <GraduationCap size={20} className="mt-0.5 shrink-0 text-status-warning" aria-hidden />
            <div className="min-w-0">
              <h3 className="text-body font-medium">Not yet trained</h3>
              <p className="mt-1 text-small text-ink-secondary">{status.note}</p>
              <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-micro text-ink-muted">
                <span>
                  confirmed{" "}
                  <span className="font-mono text-ink">
                    {status.n_confirmed}/{status.min_per_class}
                  </span>
                </span>
                <span>
                  true-negative{" "}
                  <span className="font-mono text-ink">
                    {status.n_true_negative}/{status.min_per_class}
                  </span>
                </span>
                <span>
                  censored excluded{" "}
                  <span className="font-mono text-ink">{status.n_censored_excluded}</span>
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-start gap-3">
            <GraduationCap size={20} className="mt-0.5 shrink-0 text-status-good" aria-hidden />
            <div className="min-w-0 flex-1">
              <h3 className="text-body font-medium">
                Trained · {status.model_version}
                {status.beats_baseline && (
                  <span className="ml-2 rounded-sm bg-accent-subtle px-1.5 py-0.5 text-micro font-medium text-accent">
                    beats baseline
                  </span>
                )}
              </h3>
              <p className="mt-1 text-small text-ink-secondary">
                Cross-validated ROC-AUC{" "}
                <span className="tabular font-medium text-ink">
                  {status.model_auc?.toFixed(3)}
                </span>{" "}
                vs a logistic-regression baseline at{" "}
                <span className="tabular font-medium text-ink">
                  {status.baseline_auc?.toFixed(3)}
                </span>
                . Trained on {status.n_confirmed + status.n_true_negative} labelled dispositions.
              </p>
              <div className="mt-3 space-y-1">
                {status.feature_importance.map((f) => (
                  <div key={f.feature} className="flex items-center gap-2">
                    <span className="w-40 shrink-0 text-micro text-ink-muted">
                      {FEATURE_LABEL[f.feature] ?? f.feature}
                    </span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2">
                      <div
                        className="h-full rounded-full bg-accent"
                        style={{
                          width: `${
                            (f.contribution /
                              Math.max(
                                ...status.feature_importance.map((a) => a.contribution),
                                0.0001,
                              )) *
                            100
                          }%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

function RiskScoreRow({ score }: { score: RiskScore }) {
  const top = score.attributions.filter((a) => a.contribution > 0).slice(0, 4);
  const max = Math.max(...top.map((a) => a.contribution), 0.0001);
  return (
    <li className="px-5 py-4">
      <div className="flex flex-wrap items-center gap-2">
        <Sparkles size={14} className="text-accent" aria-hidden />
        <span className="font-mono text-micro text-ink-muted">{score.document_ref}</span>
        <span className="text-small text-ink-secondary">{score.counterparty}</span>
        <div className="flex-1" />
        <span className="text-micro text-ink-muted">
          rank #{score.rank} · {Math.round(score.percentile * 100)}th percentile
        </span>
        <span className="tabular rounded-sm bg-accent-subtle px-1.5 py-0.5 text-micro font-medium text-accent">
          {score.score.toFixed(3)}
        </span>
      </div>
      <p className="mt-1 text-small text-ink">
        Flagged because {score.reason}.
      </p>
      <div className="mt-2 space-y-1">
        {top.map((a) => (
          <div key={a.feature} className="flex items-center gap-2">
            <span className="w-40 shrink-0 text-micro text-ink-muted">
              {FEATURE_LABEL[a.feature] ?? a.feature}
            </span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2">
              <div
                className="h-full rounded-full bg-accent"
                style={{ width: `${(a.contribution / max) * 100}%` }}
              />
            </div>
            <span className="tabular w-14 shrink-0 text-right font-mono text-micro text-ink-muted">
              +{a.contribution.toFixed(3)}
            </span>
          </div>
        ))}
      </div>
    </li>
  );
}

function AnomalyRow({ anomaly, reasons }: { anomaly: Anomaly; reasons: Reasons | undefined }) {
  const queryClient = useQueryClient();
  const [choosing, setChoosing] = useState<"confirm" | "dismiss" | null>(null);

  const disposition = useMutation({
    mutationFn: (args: { confirm: boolean; reason: string }) =>
      api.post(`/api/v1/anomalies/${anomaly.id}/disposition`, args),
    onSuccess: () => {
      setChoosing(null);
      queryClient.invalidateQueries();
    },
  });

  const dispositioned = anomaly.status !== "OPEN";

  return (
    <li className="px-5 py-4">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge tone={SEVERITY_TONE[anomaly.severity] ?? "neutral"}>
          {anomaly.severity.toLowerCase()}
        </StatusBadge>
        <span className="rounded-sm bg-surface-2 px-1.5 py-0.5 font-mono text-micro">
          {anomaly.detector}
        </span>
        <span className="font-mono text-micro text-ink-muted">{anomaly.document_ref}</span>
        <div className="flex-1" />
        {dispositioned && (
          <StatusBadge tone={anomaly.status === "CONFIRMED" ? "critical" : "good"}>
            {anomaly.status.toLowerCase()}
          </StatusBadge>
        )}
      </div>

      {/* Explanation first — the reviewer decides on "why" before "which". */}
      <p className="mt-2 text-body text-ink-secondary">{anomaly.explanation}</p>

      {anomaly.evidence.match_document && (
        <p className="mt-1 text-small text-ink-muted">
          Compare with{" "}
          <span className="font-mono text-ink-secondary">
            {anomaly.evidence.match_document}
          </span>
        </p>
      )}

      {dispositioned ? (
        <p className="mt-2 text-small text-ink-muted">
          {anomaly.status === "CONFIRMED" ? "Confirmed" : "Dismissed"} by{" "}
          {anomaly.dispositioned_by?.replace("user:", "")} · reason{" "}
          <span className="font-mono">{anomaly.disposition_reason}</span>
        </p>
      ) : (
        <div className="mt-3">
          {choosing === null && (
            <div className="flex gap-2">
              <Button size="sm" onClick={() => setChoosing("confirm")}>
                <CircleCheck size={13} aria-hidden />
                Confirm
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setChoosing("dismiss")}>
                <CircleX size={13} aria-hidden />
                Dismiss
              </Button>
            </div>
          )}

          {choosing && reasons && (
            <div className="rounded-md border border-hairline bg-surface-2 p-3">
              <div className="mb-2 text-small font-medium">
                {choosing === "confirm" ? "Confirm — reason" : "Dismiss — reason"}
              </div>
              <div className="space-y-1.5">
                {Object.entries(
                  choosing === "confirm" ? reasons.confirm : reasons.dismiss,
                ).map(([code, label]) => (
                  <button
                    key={code}
                    disabled={disposition.isPending}
                    onClick={() =>
                      disposition.mutate({ confirm: choosing === "confirm", reason: code })
                    }
                    className="flex w-full items-start gap-2 rounded border border-hairline bg-surface px-2.5 py-1.5 text-left text-small transition-colors hover:border-strong disabled:opacity-50"
                  >
                    <span className="font-mono text-micro text-ink-muted">{code}</span>
                    <span className="text-ink-secondary">{label}</span>
                  </button>
                ))}
              </div>
              <button
                onClick={() => setChoosing(null)}
                className="mt-2 text-micro text-ink-muted hover:text-ink-secondary"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      )}
    </li>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "critical";
}) {
  return (
    <Card className="p-4">
      <div className="text-micro uppercase tracking-wide text-ink-muted">{label}</div>
      <div
        className={`tabular mt-1 text-hero font-semibold ${
          tone === "critical" && value > 0 ? "text-status-critical" : ""
        }`}
      >
        {value}
      </div>
    </Card>
  );
}
