"use client";

import { useQuery } from "@tanstack/react-query";
import { Bot, Link2, OctagonX, ScrollText, ShieldCheck, User } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/PageHeader";
import {
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  Skeleton,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { shortHash } from "@/lib/utils";

interface AuditEvent {
  seq: number;
  action: string;
  subject_type: string;
  subject_id: string;
  actor: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  event_hash: string;
  prev_hash: string;
  recorded_at: string;
}

interface ChainStatus {
  verified: boolean;
  events_checked: number;
  head_hash: string | null;
  broken_at_seq: number | null;
  reason: string | null;
}

/**
 * Audit trail (FR-702) — the trust surface.
 *
 * Two things this screen must convey that a plain log listing cannot: that every action
 * has a named actor (human *or* agent, never anonymous), and that the record is
 * verifiable rather than merely present. The chain status card is the second point.
 */
export default function AuditPage() {
  const [actorFilter, setActorFilter] = useState("");

  const chain = useQuery({
    queryKey: ["chain-status"],
    queryFn: () => api.get<ChainStatus>("/api/v1/audit/chain-status"),
  });

  const events = useQuery({
    queryKey: ["audit-events", actorFilter],
    queryFn: () =>
      api.get<AuditEvent[]>(
        `/api/v1/audit/events${actorFilter ? `?actor=${encodeURIComponent(actorFilter)}` : ""}`,
      ),
  });

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader
        title="Audit trail"
        description="Every action, human and agent, in one tamper-evident record."
        asOf="live"
      />

      {/* Verification status leads the page. A log you cannot verify is a narrative. */}
      <Card className="mb-4">
        {chain.isLoading && (
          <div className="p-5">
            <Skeleton className="h-12" />
          </div>
        )}
        {chain.data && (
          <div className="flex flex-wrap items-center gap-4 px-5 py-4">
            {chain.data.verified ? (
              <>
                <ShieldCheck size={22} className="shrink-0 text-status-good" aria-hidden />
                <div className="min-w-0 flex-1">
                  <h2 className="text-body font-medium">Chain verified</h2>
                  <p className="mt-0.5 text-small text-ink-secondary">
                    All {chain.data.events_checked} events rehashed from their stored
                    payloads and matched. Altering any one of them would break this check
                    at its sequence number.
                  </p>
                </div>
                {chain.data.head_hash && (
                  <div className="text-right">
                    <div className="text-micro uppercase tracking-wide text-ink-muted">
                      Chain head
                    </div>
                    <div
                      className="font-mono text-small"
                      title={chain.data.head_hash}
                    >
                      {shortHash(chain.data.head_hash, 16)}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <>
                <OctagonX size={22} className="shrink-0 text-status-critical" aria-hidden />
                <div className="min-w-0 flex-1">
                  <h2 className="text-body font-medium text-status-critical">
                    Chain verification failed
                  </h2>
                  <p className="mt-0.5 text-small text-ink-secondary">
                    {chain.data.reason} Break located at sequence{" "}
                    <strong>{chain.data.broken_at_seq}</strong>. This is a security
                    incident: preserve the evidence before remediating.
                  </p>
                </div>
              </>
            )}
            <Button size="sm" onClick={() => chain.refetch()} loading={chain.isFetching}>
              Re-verify
            </Button>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader
          title="Events"
          description="Most recent first. Each row links to the one before it by hash."
          actions={
            <div className="flex gap-1">
              {[
                { label: "All", value: "" },
                { label: "Humans", value: "user:" },
                { label: "Agents", value: "agent:" },
              ].map((filter) => (
                <button
                  key={filter.label}
                  onClick={() => setActorFilter(filter.value)}
                  className={`rounded-md border px-2 py-0.5 text-small transition-colors ${
                    actorFilter === filter.value
                      ? "border-accent bg-accent-subtle text-accent"
                      : "border-hairline text-ink-secondary hover:border-strong"
                  }`}
                >
                  {filter.label}
                </button>
              ))}
            </div>
          }
        />

        {events.isLoading && (
          <div className="space-y-2 p-5">
            <Skeleton className="h-8" />
            <Skeleton className="h-8" />
          </div>
        )}
        {events.isError && (
          <ErrorState
            title={(events.error as ApiError).title}
            detail={(events.error as ApiError).detail}
            traceId={(events.error as ApiError).traceId}
            onRetry={() => events.refetch()}
          />
        )}
        {events.data?.length === 0 && (
          <EmptyState
            icon={ScrollText}
            title="No events for this filter"
            body="Actions appear here the moment they happen — the log is written inside the same transaction as the change it records."
          />
        )}

        {events.data && events.data.length > 0 && (
          <ul className="divide-y divide-hairline">
            {events.data.map((event) => {
              const isAgent = event.actor.startsWith("agent:");
              return (
                <li key={event.seq} className="px-5 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="tabular w-10 shrink-0 font-mono text-micro text-ink-muted">
                      #{event.seq}
                    </span>
                    <span className="rounded-sm bg-surface-2 px-1.5 py-0.5 font-mono text-micro">
                      {event.action}
                    </span>
                    <span className="flex items-center gap-1 text-small text-ink-secondary">
                      {isAgent ? (
                        <Bot size={12} className="text-ink-muted" aria-hidden />
                      ) : (
                        <User size={12} className="text-ink-muted" aria-hidden />
                      )}
                      {event.actor.replace(/^(user|agent):/, "")}
                    </span>
                    <div className="flex-1" />
                    <span className="text-micro text-ink-muted">
                      {new Date(event.recorded_at).toLocaleTimeString("en-GB")}
                    </span>
                  </div>

                  {event.after && (
                    <div className="ml-12 mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
                      {Object.entries(event.after)
                        .filter(([, value]) => typeof value !== "object")
                        .slice(0, 4)
                        .map(([key, value]) => (
                          <span key={key} className="text-micro text-ink-muted">
                            <span className="text-ink-secondary">{key}</span>{" "}
                            {String(value)}
                          </span>
                        ))}
                    </div>
                  )}

                  {/* The hash link is the mechanism, shown rather than described. */}
                  <div className="ml-12 mt-1 flex items-center gap-1.5 font-mono text-micro text-ink-muted">
                    <Link2 size={10} aria-hidden />
                    <span title={event.prev_hash}>{shortHash(event.prev_hash, 8)}</span>
                    <span aria-hidden>→</span>
                    <span title={event.event_hash}>{shortHash(event.event_hash, 8)}</span>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </div>
  );
}
