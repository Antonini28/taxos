"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronRight, Quote, X } from "lucide-react";
import { useState } from "react";

import { Card, CardHeader, InfoNote, Skeleton } from "@/components/ui";
import { type Computation, type Lineage, api } from "@/lib/api";
import { formatMoney, shortHash } from "@/lib/utils";

/**
 * A computed return with drill-down to evidence — shared by every tax type (US-301/US-202).
 *
 * The screen exists to demonstrate one principle: no figure is a dead end. Click any box and
 * the contributing rows appear, each carrying the reference that authorises its treatment,
 * reconciling to the box exactly. VAT and Corporation Tax render through this same component
 * because the platform computes them through the same engine — the differences are content.
 */
export function ComputationReturn({
  data,
  boxesTitle,
  boxesDescription,
  unmappedNoun,
  boxGutter = (boxId) => boxId.replace("box_", "Box "),
  order,
}: {
  data: Computation;
  boxesTitle: string;
  boxesDescription: string;
  unmappedNoun: string;
  boxGutter?: (boxId: string) => string;
  order?: string[];
}) {
  const [openBox, setOpenBox] = useState<string | null>(null);

  const boxes = order
    ? [...data.boxes].sort((a, b) => order.indexOf(a.box_id) - order.indexOf(b.box_id))
    : data.boxes;

  return (
    <>
      <Card className="mb-4">
        <CardHeader
          title="Provenance"
          description="What produced these figures, and how to prove it again."
        />
        <div className="grid grid-cols-2 gap-4 px-5 py-4 md:grid-cols-4">
          <Provenance label="Rule pack" value={data.pack_ref} mono />
          <Provenance label="Engine" value={data.engine_version} mono />
          <Provenance label="Inputs hash" value={shortHash(data.inputs_hash)} mono title={data.inputs_hash} />
          <Provenance label="Result hash" value={shortHash(data.result_hash)} mono title={data.result_hash} />
        </div>
        {data.unmapped_codes.length > 0 && (
          <div className="px-5 pb-4">
            <InfoNote>
              <strong>Unrecognised {unmappedNoun}:</strong> {data.unmapped_codes.join(", ")}. These
              rows contributed to no box. The engine reports unknown codes rather than guessing a
              treatment — a human decides whether the data or the rule pack is wrong.
            </InfoNote>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title={boxesTitle} description={boxesDescription} />
        <ul className="divide-y divide-hairline">
          {boxes.map((box) => {
            const isOpen = openBox === box.box_id;
            const isZero = Number(box.value) === 0;
            return (
              <li key={box.box_id}>
                <button
                  onClick={() => setOpenBox(isOpen ? null : box.box_id)}
                  className="flex w-full items-center gap-3 px-5 py-3 text-left transition-colors hover:bg-surface-2"
                  aria-expanded={isOpen}
                >
                  <span className="w-16 shrink-0 font-mono text-micro text-ink-muted">
                    {boxGutter(box.box_id)}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-body">
                    {box.label}
                    {box.derived && (
                      <span className="ml-2 rounded-sm bg-surface-2 px-1.5 py-0.5 text-micro text-ink-muted">
                        derived
                      </span>
                    )}
                  </span>
                  <span
                    className={`tabular shrink-0 text-body font-semibold ${isZero ? "text-ink-muted" : ""}`}
                  >
                    {formatMoney(box.value)}
                  </span>
                  <ChevronRight
                    size={15}
                    className={`shrink-0 text-ink-muted transition-transform ${isOpen ? "rotate-90" : ""}`}
                    aria-hidden
                  />
                </button>
                {isOpen && (
                  <LineagePanel
                    computationId={data.id}
                    boxId={box.box_id}
                    onClose={() => setOpenBox(null)}
                  />
                )}
              </li>
            );
          })}
        </ul>
      </Card>
    </>
  );
}

function Provenance({
  label,
  value,
  mono,
  title,
}: {
  label: string;
  value: string;
  mono?: boolean;
  title?: string;
}) {
  return (
    <div>
      <div className="text-micro uppercase tracking-wide text-ink-muted">{label}</div>
      <div className={`mt-0.5 text-small ${mono ? "font-mono" : ""}`} title={title}>
        {value}
      </div>
    </div>
  );
}

function LineagePanel({
  computationId,
  boxId,
  onClose,
}: {
  computationId: string;
  boxId: string;
  onClose: () => void;
}) {
  const lineage = useQuery({
    queryKey: ["lineage", computationId, boxId],
    queryFn: () => api.get<Lineage>(`/api/v1/computations/${computationId}/boxes/${boxId}/lineage`),
  });

  return (
    <div className="animate-slide-in border-t border-hairline bg-surface-2 px-5 py-4">
      <div className="mb-3 flex items-center gap-2">
        <h3 className="text-small font-medium">Contributing rows</h3>
        <div className="flex-1" />
        <button
          onClick={onClose}
          className="rounded p-1 text-ink-muted hover:bg-surface hover:text-ink"
          aria-label="Close lineage"
        >
          <X size={14} aria-hidden />
        </button>
      </div>

      {lineage.isLoading && <Skeleton className="h-20" />}

      {lineage.data && lineage.data.entries.length === 0 && (
        <p className="text-small text-ink-secondary">
          No rows contribute to this box for the period.
        </p>
      )}

      {lineage.data && lineage.data.entries.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-md border border-hairline bg-surface">
            <table className="w-full min-w-[620px] text-small">
              <thead>
                <tr className="border-b border-hairline text-left text-micro uppercase tracking-wide text-ink-muted">
                  <th className="px-3 py-2 font-medium">Document</th>
                  <th className="px-3 py-2 font-medium">Counterparty</th>
                  <th className="px-3 py-2 font-medium">Treatment</th>
                  <th className="px-3 py-2 text-right font-medium">Amount</th>
                  <th className="px-3 py-2 font-medium">Authority</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {lineage.data.entries.map((entry, index) => (
                  <tr key={`${entry.row_id}-${index}`}>
                    <td className="whitespace-nowrap px-3 py-2 font-mono text-micro">
                      {entry.document_ref}
                    </td>
                    <td className="px-3 py-2">{entry.counterparty}</td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <span className="rounded-sm border border-hairline bg-surface-2 px-1.5 py-0.5 font-mono text-micro">
                        {entry.vat_code}
                      </span>
                      <span className="ml-2 text-ink-muted">{entry.kind.replace(/_/g, " ")}</span>
                    </td>
                    <td className="tabular whitespace-nowrap px-3 py-2 text-right font-medium">
                      {formatMoney(entry.amount)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <span className="inline-flex items-center gap-1 text-accent">
                        <Quote size={10} aria-hidden />
                        <span className="font-mono text-micro">{entry.citation_ref}</span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* The reconciliation is the point of the whole screen: the contributions sum to the
              box value exactly, and the UI shows that rather than asserting it. */}
          <div className="mt-2 flex items-center justify-end gap-6 px-1 text-small">
            <span className="text-ink-secondary">
              Contributions total{" "}
              <span className="tabular font-medium text-ink">
                {formatMoney(lineage.data.contribution_total)}
              </span>
            </span>
            <span className="text-ink-secondary">
              Box value{" "}
              <span className="tabular font-medium text-ink">
                {formatMoney(lineage.data.box_value)}
              </span>
            </span>
            <span
              className={
                Number(lineage.data.contribution_total) === Number(lineage.data.box_value)
                  ? "font-medium text-status-good"
                  : "font-medium text-status-critical"
              }
            >
              {Number(lineage.data.contribution_total) === Number(lineage.data.box_value)
                ? "reconciles"
                : "does not reconcile"}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
