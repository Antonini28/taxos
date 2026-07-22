"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Inbox } from "lucide-react";

import { ComputationReturn } from "@/components/ComputationReturn";
import { PageHeader } from "@/components/PageHeader";
import { Button, Card, EmptyState, ErrorState, InfoNote, Skeleton } from "@/components/ui";
import { ApiError, api, type Computation } from "@/lib/api";

const ENTITY_ID = "00000000-0000-0000-0000-000000000e01";
const PERIOD = "2026";

// The natural reading order of a tax computation: profit, adjustments, taxable profits,
// then the charge. The API returns boxes sorted by id, so the screen imposes this order.
const BOX_ORDER = ["box_pbt", "box_addbacks", "box_deductions", "box_ttp", "box_ct"];

/**
 * The Corporation Tax computation — the platform's second tax type, and the proof that a tax
 * type is authored, not engineered (AP-3).
 *
 * It shares the deterministic engine, the evidence trail, and this very rendering component
 * with VAT. Nothing here is CT-specific except the framing and which endpoint is called: the
 * adjustment of accounting profit to taxable total profits lives entirely in the rule pack.
 */
export default function CorporationTaxPage() {
  const queryClient = useQueryClient();

  const computation = useQuery({
    queryKey: ["computation", ENTITY_ID, PERIOD, "CT"],
    queryFn: async () =>
      api.post<Computation>("/api/v1/computations/corporation-tax", {
        entity_id: ENTITY_ID,
        period_key: PERIOD,
      }),
    retry: false,
  });

  const recompute = useMutation({
    mutationFn: () =>
      api.post<Computation>("/api/v1/computations/corporation-tax", {
        entity_id: ENTITY_ID,
        period_key: PERIOD,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["computation"] }),
  });

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader
        title="Corporation Tax"
        description={`Meridian UK Limited · FY${PERIOD} · same engine as VAT, a different rule pack`}
        asOf="live"
        actions={
          <Button size="sm" loading={recompute.isPending} onClick={() => recompute.mutate()}>
            Recompute
          </Button>
        }
      />

      <div className="mb-4">
        <InfoNote>
          The same deterministic engine and evidence trail that files VAT compute this return —
          only the <span className="font-mono text-micro">uk-corporation-tax</span> pack differs.
          The adjustment of accounting profit to taxable total profits, and the main-rate charge,
          are content in that pack, not code in the engine.
        </InfoNote>
      </div>

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
              body="No Corporation Tax adjustments for this period. Seed the computation, then it appears here."
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
          boxesTitle="UK Corporation Tax computation"
          boxesDescription="Select any line to see the adjustments behind it, each with its authority."
          unmappedNoun="adjustment codes"
          boxGutter={() => ""}
          order={BOX_ORDER}
        />
      )}
    </div>
  );
}
