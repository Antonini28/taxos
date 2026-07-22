"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileCheck2, Fingerprint, ShieldCheck, Stamp, UserCheck } from "lucide-react";
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
  toneForWorkState,
} from "@/components/ui";
import {
  ApiError,
  api,
  currentUser,
  setCurrentUser,
  type Approval,
  type ApprovalEligibility,
  type Computation,
  type Transition,
  type WorkItem,
} from "@/lib/api";
import { formatMoney, shortHash } from "@/lib/utils";

const ENTITY_ID = "00000000-0000-0000-0000-000000000e01";

/**
 * Approvals (US-402) — the governance screen.
 *
 * Two design decisions carry the platform's ethic here:
 *   1. Approval lives WITH the evidence. There is no approve button on a queue row,
 *      because approving something you have not opened is exactly what the gate exists
 *      to prevent.
 *   2. A refusal explains itself. When the button is unavailable the reason is written
 *      beneath it, never a greyed-out control with no account of why.
 */
export default function ApprovalsPage() {
  const queryClient = useQueryClient();
  const [user, setUser] = useState(currentUser);
  const [selected, setSelected] = useState<string | null>(null);

  const items = useQuery({
    queryKey: ["work-items", user],
    queryFn: () => api.get<WorkItem[]>("/api/v1/work-items"),
  });

  const computation = useQuery({
    queryKey: ["computation-for-work", ENTITY_ID],
    queryFn: () =>
      api.post<Computation>("/api/v1/computations", {
        entity_id: ENTITY_ID,
        period_key: "2026-Q2",
      }),
    retry: false,
  });

  const createItem = useMutation({
    mutationFn: async () => {
      const item = await api.post<WorkItem>("/api/v1/work-items", {
        entity_id: ENTITY_ID,
        period_key: "2026-Q2",
        item_type: "VAT_RETURN",
        title: "Meridian UK Limited · VAT Q2-2026",
        computation_id: computation.data?.id,
      });
      await api.post(`/api/v1/work-items/${item.id}/transitions`, {
        to_state: "AWAITING_REVIEW",
      });
      return item;
    },
    onSuccess: (item) => {
      queryClient.invalidateQueries({ queryKey: ["work-items"] });
      setSelected(item.id);
    },
  });

  function switchUser(next: string) {
    setCurrentUser(next);
    setUser(next);
    queryClient.invalidateQueries();
  }

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader
        title="Approvals"
        description="Nothing becomes a position of record without a named human approving exactly what they read."
        asOf="live"
        actions={
          items.data && items.data.length === 0 ? (
            <Button
              variant="primary"
              size="sm"
              loading={createItem.isPending}
              disabled={!computation.data}
              onClick={() => createItem.mutate()}
            >
              Prepare Q2 return for review
            </Button>
          ) : undefined
        }
      />

      {/* Switching seats demonstrates segregation of duties without needing two browsers.
          In production this is the signed-in identity from the IdP. */}
      <Card className="mb-4">
        <div className="flex flex-wrap items-center gap-3 px-5 py-3">
          <UserCheck size={15} className="text-ink-muted" aria-hidden />
          <span className="text-small text-ink-secondary">Acting as</span>
          {[
            { id: "daniel@dev", label: "Daniel Kaur · Preparer" },
            { id: "priya@dev", label: "Priya Raman · Reviewer" },
          ].map((seat) => (
            <button
              key={seat.id}
              onClick={() => switchUser(seat.id)}
              className={`rounded-md border px-2.5 py-1 text-small transition-colors ${
                user === seat.id
                  ? "border-accent bg-accent-subtle font-medium text-accent"
                  : "border-hairline text-ink-secondary hover:border-strong hover:text-ink"
              }`}
            >
              {seat.label}
            </button>
          ))}
        </div>
      </Card>

      <Card>
        <CardHeader title="Work items" description="Select an item to review its evidence." />
        {items.isLoading && (
          <div className="space-y-2 p-5">
            <Skeleton className="h-9" />
          </div>
        )}
        {items.isError && (
          <ErrorState
            title={(items.error as ApiError).title}
            detail={(items.error as ApiError).detail}
            traceId={(items.error as ApiError).traceId}
            onRetry={() => items.refetch()}
          />
        )}
        {items.data?.length === 0 && (
          <EmptyState
            icon={Stamp}
            title="Nothing awaiting approval"
            body="Prepare the Q2 return above to send it for review, then switch seats to approve it."
          />
        )}
        {items.data && items.data.length > 0 && (
          <ul className="divide-y divide-hairline">
            {items.data.map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => setSelected(item.id === selected ? null : item.id)}
                  className={`flex w-full items-center gap-3 px-5 py-3 text-left transition-colors hover:bg-surface-2 ${
                    item.id === selected ? "bg-accent-subtle" : ""
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-body font-medium">{item.title}</div>
                    <div className="mt-0.5 text-micro text-ink-muted">
                      prepared by {item.prepared_by.replace("user:", "")}
                    </div>
                  </div>
                  <StatusBadge tone={toneForWorkState(item.state)}>
                    {item.state.replace(/_/g, " ").toLowerCase()}
                  </StatusBadge>
                </button>
                {item.id === selected && <ReviewPanel item={item} actingAs={user} />}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function ExportEvidenceButton({ workItemId }: { workItemId: string }) {
  const download = useMutation({
    mutationFn: async () => {
      const blob = await api.download(`/api/v1/work-items/${workItemId}/evidence-pack`);
      const url = URL.createObjectURL(blob);
      // Open in a new tab: the pack is a readable document, and the browser prints it to
      // PDF from there. A blob URL keeps it fully client-side once fetched.
      window.open(url, "_blank", "noopener");
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
    },
  });

  return (
    <Button
      variant="primary"
      className="mt-3 w-full"
      loading={download.isPending}
      onClick={() => download.mutate()}
    >
      <FileCheck2 size={14} aria-hidden />
      Export evidence pack
    </Button>
  );
}

function ReviewPanel({ item, actingAs }: { item: WorkItem; actingAs: string }) {
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");

  const eligibility = useQuery({
    queryKey: ["eligibility", item.id, actingAs],
    queryFn: () =>
      api.get<ApprovalEligibility>(`/api/v1/work-items/${item.id}/approval-eligibility`),
  });
  const history = useQuery({
    queryKey: ["history", item.id],
    queryFn: () => api.get<Transition[]>(`/api/v1/work-items/${item.id}/history`),
  });
  const approvals = useQuery({
    queryKey: ["approvals", item.id],
    queryFn: () => api.get<Approval[]>(`/api/v1/work-items/${item.id}/approvals`),
  });
  const computation = useQuery({
    queryKey: ["computation-detail", item.computation_id],
    queryFn: () => api.get<Computation>(`/api/v1/computations/${item.computation_id}`),
    enabled: Boolean(item.computation_id),
  });

  const approve = useMutation({
    mutationFn: () =>
      api.post(`/api/v1/work-items/${item.id}/approvals`, {
        content_hash: eligibility.data?.content_hash,
        comment: comment || null,
      }),
    onSuccess: () => {
      setComment("");
      queryClient.invalidateQueries();
    },
  });

  const boxes = computation.data?.boxes ?? [];
  const headline = boxes.filter((b) => ["box_1", "box_4", "box_5"].includes(b.box_id));

  return (
    <div className="animate-slide-in border-t border-hairline bg-surface-2 px-5 py-4">
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="min-w-0">
          <h3 className="mb-2 text-small font-medium">What you are approving</h3>
          {computation.isLoading && <Skeleton className="h-24" />}
          {computation.data && (
            <div className="rounded-md border border-hairline bg-surface p-4">
              <div className="grid grid-cols-3 gap-4">
                {headline.map((box) => (
                  <div key={box.box_id}>
                    <div className="text-micro uppercase tracking-wide text-ink-muted">
                      {box.box_id.replace("box_", "Box ")}
                    </div>
                    <div className="tabular mt-0.5 text-heading font-semibold">
                      {formatMoney(box.value)}
                    </div>
                    <div className="text-micro text-ink-muted">{box.label}</div>
                  </div>
                ))}
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-hairline pt-3 text-micro text-ink-muted">
                <span className="font-mono">{computation.data.pack_ref}</span>
                <span className="font-mono">engine {computation.data.engine_version}</span>
                <span className="flex items-center gap-1 font-mono">
                  <Fingerprint size={11} aria-hidden />
                  {shortHash(computation.data.result_hash, 12)}
                </span>
              </div>
            </div>
          )}

          <h3 className="mb-2 mt-4 text-small font-medium">History</h3>
          <ol className="space-y-1.5">
            {history.data?.map((transition, index) => (
              <li key={index} className="flex items-center gap-2 text-small">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-ink-muted" aria-hidden />
                <span className="text-ink-secondary">
                  {transition.from_state.toLowerCase().replace(/_/g, " ")} →{" "}
                  <span className="font-medium text-ink">
                    {transition.to_state.toLowerCase().replace(/_/g, " ")}
                  </span>
                </span>
                <span className="text-ink-muted">
                  by {transition.actor.replace("user:", "")}
                </span>
              </li>
            ))}
          </ol>
        </div>

        <div>
          <h3 className="mb-2 text-small font-medium">Approval</h3>
          <div className="rounded-md border border-hairline bg-surface p-4">
            {approvals.data && approvals.data.length > 0 ? (
              approvals.data.map((approval) => (
                <div key={approval.id}>
                  <div className="flex items-center gap-2">
                    <ShieldCheck
                      size={15}
                      className={approval.voided ? "text-status-critical" : "text-status-good"}
                      aria-hidden
                    />
                    <span className="text-small font-medium">
                      {approval.voided ? "Approval voided" : "Approved"}
                    </span>
                  </div>
                  <p className="mt-1 text-small text-ink-secondary">
                    by {approval.approver.replace("user:", "")}
                  </p>
                  {approval.comment && (
                    <p className="mt-1.5 rounded border border-hairline bg-surface-2 px-2 py-1 text-small text-ink-secondary">
                      “{approval.comment}”
                    </p>
                  )}
                  <p className="mt-2 font-mono text-micro text-ink-muted">
                    bound to {shortHash(approval.content_hash, 16)}
                  </p>
                  {approval.voided && (
                    <p className="mt-1 text-micro text-status-critical">
                      {approval.void_reason}
                    </p>
                  )}
                  {!approval.voided && <ExportEvidenceButton workItemId={item.id} />}
                </div>
              ))
            ) : (
              <>
                <textarea
                  value={comment}
                  onChange={(event) => setComment(event.target.value)}
                  placeholder="Review comment (optional)"
                  rows={3}
                  className="w-full resize-none rounded-md border border-hairline bg-surface-2 px-2.5 py-2 text-small placeholder:text-ink-muted"
                />
                <Button
                  variant="primary"
                  className="mt-2 w-full"
                  loading={approve.isPending}
                  disabled={!eligibility.data?.can_approve}
                  onClick={() => approve.mutate()}
                >
                  <ShieldCheck size={14} aria-hidden />
                  Approve
                </Button>

                {eligibility.data && !eligibility.data.can_approve && (
                  <div className="mt-2">
                    <InfoNote>{eligibility.data.reason}</InfoNote>
                  </div>
                )}

                {approve.isError && (
                  <div className="mt-2 rounded-md border border-status-critical/30 bg-status-critical/10 px-2.5 py-2">
                    <p className="text-small font-medium text-status-critical">
                      {(approve.error as ApiError).title}
                    </p>
                    <p className="mt-0.5 text-small text-ink-secondary">
                      {(approve.error as ApiError).detail}
                    </p>
                  </div>
                )}

                {eligibility.data?.content_hash && (
                  <p className="mt-2 font-mono text-micro text-ink-muted">
                    will bind to {shortHash(eligibility.data.content_hash, 16)}
                  </p>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
