"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowUpRight,
  Building2,
  CheckCircle2,
  Clock,
  Database,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import {
  Bar,
  BarChart,
  CartesianGrid,

  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { PageHeader } from "@/components/PageHeader";
import {
  Card,
  CardHeader,
  ErrorState,
  Skeleton,
  StatusBadge,
  toneForWorkState,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { formatMoney } from "@/lib/utils";

/**
 * Executive dashboard (FR-601) — the five-second read for a Head of Tax or CFO.
 *
 * Every tile links onward: the point of an executive view is not to summarise but to
 * route attention, so no figure here is a dead end (docs/frontend/03 §3.1).
 */

interface DashboardData {
  as_of: string;
  entities: number;
  net_vat_due: string;
  open_items: number;
  approved_items: number;
  data_quality: {
    total_rows: number;
    accepted_rows: number;
    quarantined_rows: number;
    quarantine_rate: number;
    batches: number;
  };
  liability_trend: {
    period_key: string;
    output_vat: string;
    input_vat: string;
    net_due: string;
  }[];
  code_breakdown: { vat_code: string; net_amount: string; transaction_count: number }[];
  compliance: {
    entity_code: string;
    entity_name: string;
    period_key: string;
    state: string;
    net_due: string | null;
  }[];
}

export default function ExecutiveDashboard() {
  const dashboard = useQuery({
    queryKey: ["executive-dashboard"],
    queryFn: () => api.get<DashboardData>("/api/v1/dashboards/executive"),
  });

  if (dashboard.isLoading) {
    return (
      <div className="mx-auto max-w-[1100px] space-y-4">
        <Skeleton className="h-16" />
        <div className="grid gap-4 md:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (dashboard.isError) {
    return (
      <div className="mx-auto max-w-[1100px]">
        <Card>
          <ErrorState
            title={(dashboard.error as ApiError).title}
            detail={(dashboard.error as ApiError).detail}
            traceId={(dashboard.error as ApiError).traceId}
            onRetry={() => dashboard.refetch()}
          />
        </Card>
      </div>
    );
  }

  const data = dashboard.data!;
  const asOf = new Date(data.as_of).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
  });

  const codeChart = data.code_breakdown.map((entry) => ({
    code: entry.vat_code,
    amount: Number(entry.net_amount),
    count: entry.transaction_count,
  }));

  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader
        title="Group tax overview"
        description="Meridian Group · compliance position, exposure, and the state of the evidence behind it."
        asOf={asOf}
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Kpi
          icon={Building2}
          label="Entities in scope"
          value={String(data.entities)}
          hint="UK VAT registered"
          href="/tax/vat"
        />
        <Kpi
          icon={ShieldCheck}
          label="Net VAT position"
          value={formatMoney(data.net_vat_due)}
          hint="current period, all entities"
          href="/tax/vat"
        />
        <Kpi
          icon={Clock}
          label="Awaiting review"
          value={String(data.open_items)}
          hint={`${data.approved_items} approved`}
          href="/work/approvals"
          tone={data.open_items > 0 ? "warning" : undefined}
        />
        <Kpi
          icon={Database}
          label="Data quality"
          value={`${(100 - data.data_quality.quarantine_rate).toFixed(1)}%`}
          hint={`${data.data_quality.quarantined_rows} of ${data.data_quality.total_rows} rows quarantined`}
          href="/data/batches"
          tone={data.data_quality.quarantine_rate > 5 ? "warning" : undefined}
        />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader
            title="Net position by VAT code"
            description="Where the value sits across the transaction population."
          />
          <div className="px-3 py-4">
            {codeChart.length === 0 ? (
              <p className="px-2 text-small text-ink-secondary">No transactions yet.</p>
            ) : (
              <>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={codeChart} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
                    <CartesianGrid
                      strokeDasharray="0"
                      vertical={false}
                      stroke="var(--border-hairline)"
                    />
                    <XAxis
                      dataKey="code"
                      tick={{ fontSize: 11, fill: "var(--ink-muted)" }}
                      axisLine={{ stroke: "var(--border-strong)" }}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: "var(--ink-muted)" }}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(value: number) => `£${(value / 1000).toFixed(0)}k`}
                      width={48}
                    />
                    <Tooltip
                      cursor={{ fill: "var(--accent-subtle)" }}
                      contentStyle={{
                        background: "var(--bg-overlay)",
                        border: "1px solid var(--border-hairline)",
                        borderRadius: 6,
                        fontSize: 12,
                        color: "var(--ink-primary)",
                      }}
                      formatter={(value: number, _name, item) => [
                        `${formatMoney(String(value))} · ${item.payload.count} transactions`,
                        "Net amount",
                      ]}
                    />
                    {/* One series, one hue: a second colour would imply a categorical
                        split with no legend to explain it. The reverse-charge distinction
                        is carried by the caption and the table, not by colour alone. */}
                    <Bar
                      dataKey="amount"
                      radius={[4, 4, 0, 0]}
                      maxBarSize={48}
                      fill="var(--series-1)"
                    />
                  </BarChart>
                </ResponsiveContainer>
                <p className="mt-2 px-2 text-micro text-ink-muted">
                  RC20 is the domestic reverse charge: the buyer self-accounts, so those
                  amounts appear in both Box 1 and Box 4 and net to nil in cash terms.
                </p>
                {/* Table view parity: charts are never the only way to read the data. */}
                <details className="mt-2 px-2">
                  <summary className="cursor-pointer text-micro text-ink-muted hover:text-ink-secondary">
                    View as table
                  </summary>
                  <table className="mt-2 w-full text-small">
                    <thead>
                      <tr className="text-left text-micro uppercase text-ink-muted">
                        <th className="py-1 font-medium">Code</th>
                        <th className="py-1 text-right font-medium">Net</th>
                        <th className="py-1 text-right font-medium">Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {codeChart.map((entry) => (
                        <tr key={entry.code} className="border-t border-hairline">
                          <td className="py-1 font-mono text-micro">{entry.code}</td>
                          <td className="tabular py-1 text-right">
                            {formatMoney(String(entry.amount))}
                          </td>
                          <td className="tabular py-1 text-right">{entry.count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </details>
              </>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Compliance position"
            description="Entity × period, with the current workflow state."
          />
          <ul className="divide-y divide-hairline">
            {data.compliance.length === 0 && (
              <li className="px-5 py-6 text-small text-ink-secondary">
                No computed periods yet.
              </li>
            )}
            {data.compliance.map((cell) => (
              <li
                key={`${cell.entity_code}-${cell.period_key}`}
                className="flex items-center gap-3 px-5 py-3"
              >
                <div className="min-w-0 flex-1">
                  <div className="truncate text-body font-medium">{cell.entity_name}</div>
                  <div className="text-micro text-ink-muted">
                    {cell.entity_code} · {cell.period_key}
                  </div>
                </div>
                <div className="text-right">
                  {cell.net_due && (
                    <div className="tabular text-body font-semibold">
                      {formatMoney(cell.net_due)}
                    </div>
                  )}
                  <StatusBadge tone={toneForWorkState(cell.state)}>
                    {cell.state.replace(/_/g, " ").toLowerCase()}
                  </StatusBadge>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader
          title="Evidence posture"
          description="What makes the figures above defensible."
        />
        <div className="grid gap-4 px-5 py-4 md:grid-cols-3">
          <Posture
            icon={CheckCircle2}
            title="Deterministic computation"
            body="Figures come from a versioned rule engine, not a model. Identical inputs always produce an identical result hash."
          />
          <Posture
            icon={ShieldCheck}
            title="Human-gated approval"
            body="No position of record exists without a named approver, bound to a hash of exactly what they reviewed."
          />
          <Posture
            icon={Database}
            title="Traceable to source"
            body="Every box drills to the invoices behind it, each carrying the HMRC reference authorising its treatment."
          />
        </div>
      </Card>
    </div>
  );
}

function Kpi({
  icon: Icon,
  label,
  value,
  hint,
  href,
  tone,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  hint: string;
  href: string;
  tone?: "warning";
}) {
  return (
    <Link
      href={href}
      className="group rounded-lg border border-hairline bg-surface p-4 transition-colors hover:border-strong"
    >
      <div className="flex items-center gap-2 text-ink-secondary">
        <Icon size={14} aria-hidden />
        <span className="text-small">{label}</span>
        <ArrowUpRight
          size={13}
          className="ml-auto text-ink-muted opacity-0 transition-opacity group-hover:opacity-100"
          aria-hidden
        />
      </div>
      <div
        className={`tabular mt-2 text-hero font-semibold ${
          tone === "warning" ? "text-status-warning" : ""
        }`}
      >
        {value}
      </div>
      <div className="mt-0.5 text-micro text-ink-muted">{hint}</div>
    </Link>
  );
}

function Posture({
  icon: Icon,
  title,
  body,
}: {
  icon: React.ElementType;
  title: string;
  body: string;
}) {
  return (
    <div className="flex gap-3">
      <Icon size={16} className="mt-0.5 shrink-0 text-status-good" aria-hidden />
      <div>
        <h3 className="text-small font-medium">{title}</h3>
        <p className="mt-0.5 text-small text-ink-secondary">{body}</p>
      </div>
    </div>
  );
}
