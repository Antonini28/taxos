"use client";

import { AlertTriangle, CheckCircle2, Info, Loader2, OctagonX } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Shared primitives (docs/frontend/01 §6). Every state a screen can be in — loading,
 * empty, error — is a designed component, not an afterthought rendered as raw text.
 */

export function Card({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("rounded-lg border border-hairline bg-surface", className)}>{children}</div>
  );
}

export function CardHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3 border-b border-hairline px-5 py-3">
      <div className="min-w-0 flex-1">
        <h2 className="text-heading font-semibold">{title}</h2>
        {description && <p className="mt-0.5 text-small text-ink-secondary">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

export type StatusTone = "good" | "warning" | "serious" | "critical" | "neutral";

const TONE_STYLES: Record<StatusTone, string> = {
  good: "border-status-good/30 bg-status-good/10 text-status-good",
  warning: "border-status-warning/40 bg-status-warning/10 text-[#8a6100] dark:text-status-warning",
  serious: "border-status-serious/40 bg-status-serious/10 text-[#a3441c] dark:text-status-serious",
  critical: "border-status-critical/30 bg-status-critical/10 text-status-critical",
  neutral: "border-hairline bg-surface-2 text-ink-secondary",
};

const TONE_ICONS: Record<StatusTone, React.ElementType | null> = {
  good: CheckCircle2,
  warning: AlertTriangle,
  serious: AlertTriangle,
  critical: OctagonX,
  neutral: null,
};

/**
 * Status never travels by colour alone — icon plus label, always (WCAG 1.4.1).
 */
export function StatusBadge({
  tone,
  children,
}: {
  tone: StatusTone;
  children: React.ReactNode;
}) {
  const Icon = TONE_ICONS[tone];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-micro font-medium",
        TONE_STYLES[tone],
      )}
    >
      {Icon && <Icon size={11} aria-hidden />}
      {children}
    </span>
  );
}

export function toneForBatchStatus(status: string): StatusTone {
  if (status === "VALIDATED") return "good";
  if (status === "VALIDATED_WITH_EXCEPTIONS") return "warning";
  if (status === "REJECTED") return "critical";
  return "neutral";
}

export function toneForWorkState(state: string): StatusTone {
  if (state === "APPROVED") return "good";
  if (state === "AWAITING_REVIEW") return "warning";
  if (state === "CHANGES_REQUESTED") return "serious";
  if (state === "CANCELLED") return "critical";
  return "neutral";
}

export function Button({
  children,
  variant = "secondary",
  size = "md",
  loading,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md";
  loading?: boolean;
}) {
  return (
    <button
      {...props}
      disabled={props.disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-md font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" ? "px-2.5 py-1 text-small" : "px-3 py-1.5 text-body",
        variant === "primary" && "bg-accent text-white hover:bg-accent-hover",
        variant === "secondary" &&
          "border border-hairline bg-surface text-ink hover:border-strong hover:bg-surface-2",
        variant === "ghost" && "text-ink-secondary hover:bg-surface-2 hover:text-ink",
        className,
      )}
    >
      {loading && <Loader2 size={14} className="animate-spin" aria-hidden />}
      {children}
    </button>
  );
}

/** Skeletons reserve the exact final space, so nothing shifts when data lands (CLS 0). */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded bg-surface-2", className)} />;
}

export function EmptyState({
  icon: Icon,
  title,
  body,
  action,
}: {
  icon: React.ElementType;
  title: string;
  body: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center">
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-surface-2 text-ink-muted">
        <Icon size={18} aria-hidden />
      </div>
      <h3 className="text-body font-medium">{title}</h3>
      <p className="mt-1 max-w-sm text-small text-ink-secondary">{body}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

/**
 * Errors show what failed, and the trace id — so a screenshot is enough for support
 * to find the exact request (docs/frontend/05 §5).
 */
export function ErrorState({
  title,
  detail,
  traceId,
  onRetry,
}: {
  title: string;
  detail?: string | null;
  traceId?: string | null;
  onRetry?: () => void;
}) {
  return (
    <div className="flex items-start gap-3 px-5 py-6">
      <OctagonX size={18} className="mt-0.5 shrink-0 text-status-critical" aria-hidden />
      <div className="min-w-0 flex-1">
        <h3 className="text-body font-medium">{title}</h3>
        {detail && <p className="mt-0.5 text-small text-ink-secondary">{detail}</p>}
        {traceId && (
          <p className="mt-2 font-mono text-micro text-ink-muted">trace {traceId}</p>
        )}
        {onRetry && (
          <Button size="sm" className="mt-3" onClick={onRetry}>
            Try again
          </Button>
        )}
      </div>
    </div>
  );
}

export function InfoNote({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-hairline bg-surface-2 px-3 py-2 text-small text-ink-secondary">
      <Info size={14} className="mt-0.5 shrink-0 text-ink-muted" aria-hidden />
      <div>{children}</div>
    </div>
  );
}
