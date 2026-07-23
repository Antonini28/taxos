"use client";

import { useQuery } from "@tanstack/react-query";
import { CalendarClock, ChevronRight, Quote } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/PageHeader";
import {
  Card,
  CardHeader,
  ErrorState,
  InfoNote,
  Skeleton,
  StatusBadge,
  type StatusTone,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";

const ENTITY_ID = "00000000-0000-0000-0000-000000000e01";
const YEAR = 2026;

interface Obligation {
  tax_type: string;
  period_key: string;
  period_label: string;
  period_end: string;
  due_date: string;
  basis: string;
  status: string;
  overdue: boolean;
  work_item_id: string | null;
}

const STATUS_LABEL: Record<string, string> = {
  NOT_STARTED: "not started",
  IN_PREPARATION: "in preparation",
  AWAITING_REVIEW: "awaiting review",
  APPROVED: "approved",
};

const STATUS_TONE: Record<string, StatusTone> = {
  NOT_STARTED: "neutral",
  IN_PREPARATION: "neutral",
  AWAITING_REVIEW: "warning",
  APPROVED: "good",
};

function daysUntil(iso: string): number {
  const due = new Date(`${iso}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((due.getTime() - today.getTime()) / 86_400_000);
}

/**
 * The filing calendar (US-501). Obligations are derived, never stored: the entity's
 * registrations imply what must be filed, the period implies the statutory deadline, and the
 * status IS the live workflow state — so this screen cannot disagree with the approvals queue.
 */
export default function CalendarPage() {
  const obligations = useQuery({
    queryKey: ["obligations", ENTITY_ID, YEAR],
    queryFn: () =>
      api.get<Obligation[]>(
        `/api/v1/calendar/obligations?entity_id=${ENTITY_ID}&year=${YEAR}`,
      ),
  });

  return (
    <div className="mx-auto max-w-[900px]">
      <PageHeader
        title="Filing calendar"
        description={`Meridian UK Limited · ${YEAR} · every deadline carries its statutory basis`}
        asOf="live"
      />

      <div className="mb-4">
        <InfoNote>
          Obligations are derived from the entity&apos;s registrations and joined to live
          workflow state — the calendar and the approvals queue cannot disagree, because they
          are the same facts. Overdue means past the statutory deadline without an approval.
        </InfoNote>
      </div>

      {obligations.isLoading && (
        <Card className="space-y-2 p-5">
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
        </Card>
      )}

      {obligations.isError && (
        <Card className="p-5">
          <ErrorState
            title={(obligations.error as ApiError).title}
            detail={(obligations.error as ApiError).detail}
            traceId={(obligations.error as ApiError).traceId}
            onRetry={() => obligations.refetch()}
          />
        </Card>
      )}

      {obligations.data && (
        <Card>
          <CardHeader
            title={`Obligations · ${YEAR}`}
            description="Ordered by statutory due date, soonest first."
          />
          <ul className="divide-y divide-hairline">
            {obligations.data.map((o) => {
              const days = daysUntil(o.due_date);
              const href = o.tax_type === "VAT" ? "/tax/vat" : "/tax/corporation-tax";
              return (
                <li key={`${o.tax_type}-${o.period_key}`}>
                  <Link
                    href={o.status === "AWAITING_REVIEW" ? "/work/approvals" : href}
                    className="flex items-center gap-4 px-5 py-3.5 transition-colors hover:bg-surface-2"
                  >
                    <CalendarClock
                      size={18}
                      className={`shrink-0 ${o.overdue ? "text-status-critical" : "text-ink-muted"}`}
                      aria-hidden
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-body font-medium">{o.period_label}</span>
                        <StatusBadge tone={STATUS_TONE[o.status] ?? "neutral"}>
                          {STATUS_LABEL[o.status] ?? o.status.toLowerCase()}
                        </StatusBadge>
                        {o.overdue && <StatusBadge tone="critical">overdue</StatusBadge>}
                      </div>
                      <div className="mt-0.5 flex items-center gap-1.5 text-micro text-ink-muted">
                        <Quote size={9} aria-hidden />
                        <span>{o.basis}</span>
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="tabular text-small font-medium">
                        {new Date(`${o.due_date}T00:00:00`).toLocaleDateString("en-GB", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </div>
                      <div
                        className={`text-micro ${
                          o.overdue ? "font-medium text-status-critical" : "text-ink-muted"
                        }`}
                      >
                        {o.status === "APPROVED"
                          ? "approved"
                          : days >= 0
                            ? `due in ${days} day${days === 1 ? "" : "s"}`
                            : `${-days} day${days === -1 ? "" : "s"} overdue`}
                      </div>
                    </div>
                    <ChevronRight size={15} className="shrink-0 text-ink-muted" aria-hidden />
                  </Link>
                </li>
              );
            })}
          </ul>
        </Card>
      )}
    </div>
  );
}
