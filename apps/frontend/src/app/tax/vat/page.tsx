"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Inbox } from "lucide-react";
import { useState } from "react";

import { ComputationReturn } from "@/components/ComputationReturn";
import { PageHeader } from "@/components/PageHeader";
import { Button, Card, EmptyState, ErrorState, Skeleton } from "@/components/ui";
import { ApiError, api, type Computation } from "@/lib/api";

const ENTITY_ID = "00000000-0000-0000-0000-000000000e01";
const PERIOD = "2026-Q2";

/**
 * The VAT return (US-301) with drill-down to evidence (US-202).
 *
 * The rendering lives in the shared <ComputationReturn> — the same component that renders the
 * Corporation Tax computation, because both are produced by the same deterministic engine.
 * This screen just supplies the VAT-specific framing and computes the return on load.
 */
export default function VatPage() {
  const queryClient = useQueryClient();
  // Kept so a future filter can move without touching the fetch; also documents intent.
  const [period] = useState(PERIOD);

  const computation = useQuery({
    queryKey: ["computation", ENTITY_ID, period],
    queryFn: async () =>
      // Computing is idempotent: identical inputs return the existing snapshot rather than
      // creating a second one, so this is safe to call on load.
      api.post<Computation>("/api/v1/computations", { entity_id: ENTITY_ID, period_key: period }),
    retry: false,
  });

  const recompute = useMutation({
    mutationFn: () =>
      api.post<Computation>("/api/v1/computations", { entity_id: ENTITY_ID, period_key: period }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["computation"] }),
  });

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader
        title="VAT return"
        description={`Meridian UK Limited · ${period} · computed by a deterministic engine`}
        asOf="live"
        actions={
          <Button size="sm" loading={recompute.isPending} onClick={() => recompute.mutate()}>
            Recompute
          </Button>
        }
      />

      {computation.isLoading && (
        <Card className="space-y-2 p-5">
          <Skeleton className="h-8" />
          <Skeleton className="h-40" />
        </Card>
      )}

      {computation.isError &&
        ((computation.error as ApiError).status === 422 ? (
          <Card className="p-5">
            <EmptyState
              icon={Inbox}
              title="Nothing to compute yet"
              body="No validated data for this period. Ingest a batch, then the return computes automatically."
            />
          </Card>
        ) : (
          <Card className="p-5">
            <ErrorState
              title={(computation.error as ApiError).title}
              detail={(computation.error as ApiError).detail}
              traceId={(computation.error as ApiError).traceId}
              onRetry={() => computation.refetch()}
            />
          </Card>
        ))}

      {computation.data && (
        <ComputationReturn
          data={computation.data}
          boxesTitle="UK VAT return · 9 boxes"
          boxesDescription="Select any box to see the transactions behind it."
          unmappedNoun="VAT codes"
        />
      )}
    </div>
  );
}
