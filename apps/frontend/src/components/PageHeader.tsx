import { Clock3 } from "lucide-react";

/**
 * Every page leads with the same header (docs/frontend/01 §6): title, purpose, and —
 * where data is involved — an as-of chip. Freshness is always visible; a dashboard
 * that hides its staleness is lying quietly.
 */
export function PageHeader({
  title,
  description,
  asOf,
  actions,
}: {
  title: string;
  description?: string;
  asOf?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-5 flex items-start gap-4">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2.5">
          <h1 className="text-title font-semibold">{title}</h1>
          {asOf && (
            <span className="flex items-center gap-1 rounded-full border border-hairline px-2 py-0.5 text-micro text-ink-muted">
              <Clock3 size={11} aria-hidden />
              as of {asOf}
            </span>
          )}
        </div>
        {description && <p className="mt-1 text-small text-ink-secondary">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}
