"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleCheck, CircleX, Flag, RadarIcon, ShieldAlert } from "lucide-react";
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
    </div>
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
