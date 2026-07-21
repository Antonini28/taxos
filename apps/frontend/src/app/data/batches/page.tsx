"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, FileUp, ShieldAlert } from "lucide-react";
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
  toneForBatchStatus,
} from "@/components/ui";
import { ApiError, api, type Batch, type QuarantinedRow, type ValidationReport } from "@/lib/api";
import { formatMoney } from "@/lib/utils";

/**
 * Ingestion (US-201). The screen's job is to make validation *legible*: a preparer must
 * see not just that rows failed, but which rule each one broke and what the row said —
 * enough to fix it at source.
 */
export default function BatchesPage() {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);

  const batches = useQuery({
    queryKey: ["batches"],
    queryFn: () => api.get<Batch[]>("/api/v1/batches"),
  });

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("entity_id", ENTITY_ID);
      form.append("period_key", "2026-Q2");
      form.append("source_type", file.name.toLowerCase().includes("sale") ? "AR" : "AP");
      form.append("file", file);
      return api.upload<{ batch_id: string }>("/api/v1/batches", form);
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["batches"] });
      setSelected(result.batch_id);
    },
  });

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader
        title="Ingestion"
        description="ERP extracts land here. Nothing reaches a computation until it has been validated."
        asOf="live"
      />

      <Card className="mb-4">
        <CardHeader
          title="Upload an extract"
          description="CSV with document_ref, document_date, counterparty, net_amount, vat_amount, vat_code, currency."
        />
        <div className="p-5">
          <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-strong bg-surface-2 px-4 py-8 text-body text-ink-secondary transition-colors hover:border-accent hover:text-ink">
            <FileUp size={17} aria-hidden />
            <span>{upload.isPending ? "Uploading…" : "Choose a CSV file to ingest"}</span>
            <input
              type="file"
              accept=".csv,text/csv"
              className="sr-only"
              disabled={upload.isPending}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) upload.mutate(file);
                event.target.value = "";
              }}
            />
          </label>

          {upload.isError && (
            <div className="mt-3">
              <ErrorState
                title={(upload.error as ApiError).title}
                detail={(upload.error as ApiError).detail}
                traceId={(upload.error as ApiError).traceId}
              />
            </div>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader title="Batches" description="Most recent first." />
        {batches.isLoading && (
          <div className="space-y-2 p-5">
            <Skeleton className="h-9" />
            <Skeleton className="h-9" />
          </div>
        )}
        {batches.isError && (
          <ErrorState
            title="Could not load batches"
            detail={(batches.error as ApiError).detail}
            traceId={(batches.error as ApiError).traceId}
            onRetry={() => batches.refetch()}
          />
        )}
        {batches.data?.length === 0 && (
          <EmptyState
            icon={Database}
            title="No batches yet"
            body="Upload your first ERP extract above. Validation runs immediately and reports rule-level results."
          />
        )}
        {batches.data && batches.data.length > 0 && (
          /* Wide tables scroll inside their own container — the page body never
             scrolls sideways (docs/frontend/04, responsive behaviour). */
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-body">
              <thead>
                <tr className="border-b border-hairline text-left text-micro uppercase tracking-wide text-ink-muted">
                  <th className="px-5 py-2 font-medium">File</th>
                  <th className="px-3 py-2 font-medium">Period</th>
                  <th className="px-3 py-2 font-medium">Source</th>
                  <th className="px-3 py-2 text-right font-medium">Rows</th>
                  <th className="px-3 py-2 text-right font-medium">Accepted</th>
                  <th className="px-3 py-2 text-right font-medium">Quarantined</th>
                  <th className="px-5 py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {batches.data.map((batch) => (
                  <tr
                    key={batch.id}
                    onClick={() => setSelected(batch.id === selected ? null : batch.id)}
                    className={`cursor-pointer transition-colors hover:bg-surface-2 ${
                      batch.id === selected ? "bg-accent-subtle" : ""
                    }`}
                  >
                    <td className="whitespace-nowrap px-5 py-2.5 font-medium">{batch.filename}</td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-ink-secondary">
                      {batch.period_key}
                    </td>
                    <td className="px-3 py-2.5 text-ink-secondary">{batch.source_type}</td>
                    <td className="tabular px-3 py-2.5 text-right">{batch.row_count}</td>
                    <td className="tabular px-3 py-2.5 text-right">{batch.accepted_count}</td>
                    <td className="tabular px-3 py-2.5 text-right">
                      {batch.quarantined_count > 0 ? (
                        <span className="font-medium text-status-serious">
                          {batch.quarantined_count}
                        </span>
                      ) : (
                        <span className="text-ink-muted">0</span>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-5 py-2.5">
                      <StatusBadge tone={toneForBatchStatus(batch.status)}>
                        {batch.status.replace(/_/g, " ").toLowerCase()}
                      </StatusBadge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {selected && <ValidationDetail batchId={selected} />}
    </div>
  );
}

function ValidationDetail({ batchId }: { batchId: string }) {
  const report = useQuery({
    queryKey: ["validation-report", batchId],
    queryFn: () => api.get<ValidationReport>(`/api/v1/batches/${batchId}/validation-report`),
  });
  const quarantine = useQuery({
    queryKey: ["quarantine", batchId],
    queryFn: () => api.get<QuarantinedRow[]>(`/api/v1/batches/${batchId}/quarantine`),
  });

  if (report.isLoading) {
    return (
      <Card className="mt-4 p-5">
        <Skeleton className="h-24" />
      </Card>
    );
  }
  if (!report.data) return null;

  return (
    <Card className="mt-4 animate-slide-in">
      <CardHeader
        title="Validation report"
        description="Rule-level results for the selected batch."
      />
      <div className="grid grid-cols-2 gap-4 px-5 py-4 md:grid-cols-4">
        <Metric label="Rows" value={String(report.data.row_count)} />
        <Metric label="Accepted" value={String(report.data.accepted_count)} />
        <Metric
          label="Quarantined"
          value={String(report.data.quarantined_count)}
          tone={report.data.quarantined_count > 0 ? "serious" : undefined}
        />
        <Metric label="Control total" value={formatMoney(report.data.control_total)} />
      </div>

      {quarantine.data && quarantine.data.length > 0 && (
        <div className="border-t border-hairline px-5 py-4">
          <div className="mb-3 flex items-center gap-2">
            <ShieldAlert size={15} className="text-status-serious" aria-hidden />
            <h3 className="text-body font-medium">Quarantined rows</h3>
          </div>
          <InfoNote>
            These rows are held, not discarded, and contribute to no computed figure. Each
            failure names the rule it broke so it can be corrected at source.
          </InfoNote>
          <ul className="mt-3 space-y-2">
            {quarantine.data.map((row) => (
              <li
                key={row.row_number}
                className="rounded-md border border-hairline bg-surface-2 px-3 py-2.5"
              >
                <div className="flex items-center gap-2">
                  <span className="tabular text-micro text-ink-muted">row {row.row_number}</span>
                  <span className="font-mono text-micro text-ink-secondary">
                    {row.source_payload.document_ref || "(no reference)"}
                  </span>
                  <span className="text-micro text-ink-muted">
                    {row.source_payload.counterparty}
                  </span>
                </div>
                {row.failures.map((failure, index) => (
                  <div key={index} className="mt-1.5 flex items-start gap-2">
                    <span className="shrink-0 rounded-sm border border-status-serious/40 bg-status-serious/10 px-1.5 py-0.5 font-mono text-micro text-[#a3441c] dark:text-status-serious">
                      {failure.rule}
                    </span>
                    <span className="text-small text-ink-secondary">{failure.message}</span>
                  </div>
                ))}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "serious";
}) {
  return (
    <div>
      <div className="text-micro uppercase tracking-wide text-ink-muted">{label}</div>
      <div
        className={`tabular mt-0.5 text-title font-semibold ${
          tone === "serious" ? "text-status-serious" : ""
        }`}
      >
        {value}
      </div>
    </div>
  );
}

// The demo entity, seeded by the backend. Entity selection arrives with master data UI.
const ENTITY_ID = "00000000-0000-0000-0000-000000000e01";
