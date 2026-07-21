import { ArrowRight, CheckCircle2, Clock, Database, Stamp } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/PageHeader";

/**
 * Operations home — the Analyst's landing page (docs/frontend/02 §3).
 * Answers "what do I owe today" before anything else.
 */
export default function OperationsPage() {
  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader
        title="Operations"
        description="Your queue, your deadlines, and the state of the data behind them."
        asOf="just now"
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          icon={Clock}
          label="Awaiting your review"
          value="1"
          hint="VAT Q2-2026 · UK-01"
          href="/work/approvals"
        />
        <StatCard
          icon={Database}
          label="Batches this period"
          value="2"
          hint="1 with exceptions"
          href="/data/batches"
        />
        <StatCard
          icon={CheckCircle2}
          label="Computations"
          value="1"
          hint="uk-vat@1.0.0 · reproducible"
          href="/tax/vat"
        />
      </div>

      <section className="mt-6 rounded-lg border border-hairline bg-surface">
        <div className="border-b border-hairline px-5 py-3">
          <h2 className="text-heading font-semibold">The R1 vertical slice</h2>
          <p className="mt-0.5 text-small text-ink-secondary">
            Every step below is live against the API — ingest, validate, compute, review,
            approve — with audit and lineage throughout.
          </p>
        </div>
        <ol className="divide-y divide-hairline">
          <SliceStep
            n={1}
            title="Ingest & validate"
            body="Upload an ERP extract. Rows that fail validation are quarantined with the exact rule they broke — never silently dropped."
            href="/data/batches"
            cta="Open ingestion"
          />
          <SliceStep
            n={2}
            title="Compute the return"
            body="A deterministic engine produces the 9-box VAT return from validated rows. Identical inputs always yield an identical result hash."
            href="/tax/vat"
            cta="View VAT returns"
          />
          <SliceStep
            n={3}
            title="Drill to evidence"
            body="Every box drills to the invoices that produced it, each carrying the HMRC reference that authorises its treatment."
            href="/tax/vat"
            cta="See lineage"
          />
          <SliceStep
            n={4}
            title="Review & approve"
            body="Approval binds to a hash of exactly what was reviewed. The preparer cannot approve their own work, and later data changes void the approval automatically."
            href="/work/approvals"
            cta="Open approvals"
          />
        </ol>
      </section>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  hint,
  href,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  hint: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="group rounded-lg border border-hairline bg-surface p-4 transition-colors hover:border-strong"
    >
      <div className="flex items-center gap-2 text-ink-secondary">
        <Icon size={15} aria-hidden />
        <span className="text-small">{label}</span>
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="tabular text-hero font-semibold">{value}</span>
      </div>
      <div className="mt-1 flex items-center gap-1 text-small text-ink-muted">
        <span>{hint}</span>
        <ArrowRight
          size={13}
          className="opacity-0 transition-opacity group-hover:opacity-100"
          aria-hidden
        />
      </div>
    </Link>
  );
}

function SliceStep({
  n,
  title,
  body,
  href,
  cta,
}: {
  n: number;
  title: string;
  body: string;
  href: string;
  cta: string;
}) {
  return (
    <li className="flex gap-4 px-5 py-4">
      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-hairline text-micro font-semibold text-ink-secondary">
        {n}
      </div>
      <div className="min-w-0 flex-1">
        <h3 className="text-body font-medium">{title}</h3>
        <p className="mt-0.5 text-small text-ink-secondary">{body}</p>
      </div>
      <Link
        href={href}
        className="flex h-fit shrink-0 items-center gap-1 rounded-md border border-hairline px-2.5 py-1 text-small text-ink-secondary transition-colors hover:border-strong hover:text-ink"
      >
        {cta}
        <ArrowRight size={13} aria-hidden />
      </Link>
    </li>
  );
}
