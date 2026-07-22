"use client";

import {
  Bot,
  Building2,
  Calculator,
  Database,
  FileCheck2,
  Flag,
  LayoutDashboard,
  Library,
  Moon,
  ScrollText,
  Settings,
  Shield,
  Stamp,
  Sun,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * The app shell (docs/frontend/02 §2): persistent left nav grouped exactly as the
 * sitemap, a top bar carrying the tenant/entity scope, and the page body.
 *
 * Nav groups match the information architecture rather than the codebase — users
 * navigate by their work, not by our module boundaries.
 */

const NAV_GROUPS = [
  {
    label: "Dashboards",
    items: [
      { href: "/", label: "Operations", icon: LayoutDashboard },
      { href: "/dashboard", label: "Executive", icon: Building2 },
    ],
  },
  {
    label: "Tax",
    items: [
      { href: "/tax/vat", label: "VAT", icon: Calculator },
      { href: "/tax/calendar", label: "Calendar", icon: FileCheck2, soon: true },
    ],
  },
  {
    label: "Data",
    items: [{ href: "/data/batches", label: "Ingestion", icon: Database }],
  },
  {
    label: "Work",
    items: [
      { href: "/work/approvals", label: "Approvals", icon: Stamp },
      { href: "/audit", label: "Audit trail", icon: ScrollText },
    ],
  },
  {
    label: "AI & Risk",
    items: [
      { href: "/agents", label: "Agents", icon: Bot },
      { href: "/fraud", label: "Fraud centre", icon: Flag },
      { href: "/knowledge", label: "Knowledge", icon: Library, soon: true },
    ],
  },
];

function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("taxos-theme");
    const prefers = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const isDark = stored ? stored === "dark" : prefers;
    setDark(isDark);
    document.documentElement.classList.toggle("dark", isDark);
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("taxos-theme", next ? "dark" : "light");
  }

  return (
    <button
      onClick={toggle}
      className="rounded-md p-2 text-ink-secondary transition-colors hover:bg-surface-2 hover:text-ink"
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
    >
      {dark ? <Sun size={16} aria-hidden /> : <Moon size={16} aria-hidden />}
    </button>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen">
      <nav
        className="flex w-[232px] shrink-0 flex-col border-r border-hairline bg-surface"
        aria-label="Main navigation"
      >
        <div className="flex h-14 items-center gap-2 border-b border-hairline px-4">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-accent text-white">
            <Shield size={16} aria-hidden />
          </div>
          <div className="leading-tight">
            <div className="text-[13px] font-semibold">TaxOS</div>
            <div className="text-micro text-ink-muted">Agentic Tax OS</div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-3">
          {NAV_GROUPS.map((group) => (
            <div key={group.label} className="mb-4">
              <div className="px-3 pb-1 text-micro font-medium uppercase tracking-wide text-ink-muted">
                {group.label}
              </div>
              {group.items.map((item) => {
                const active =
                  item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "group flex items-center gap-2.5 rounded-md px-3 py-1.5 text-body transition-colors",
                      active
                        ? "bg-accent-subtle font-medium text-accent"
                        : "text-ink-secondary hover:bg-surface-2 hover:text-ink",
                    )}
                    aria-current={active ? "page" : undefined}
                  >
                    <Icon size={16} aria-hidden />
                    <span className="flex-1">{item.label}</span>
                    {item.soon && (
                      <span className="rounded-sm bg-surface-2 px-1 text-micro text-ink-muted">
                        soon
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </div>

        <div className="border-t border-hairline p-3">
          <div className="flex items-center gap-2.5 px-1">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-surface-2 text-micro font-semibold">
              DK
            </div>
            <div className="flex-1 leading-tight">
              <div className="text-small font-medium">Daniel Kaur</div>
              <div className="text-micro text-ink-muted">Preparer</div>
            </div>
            <Settings size={15} className="text-ink-muted" aria-hidden />
          </div>
        </div>
      </nav>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-hairline bg-surface px-5">
          {/* The tenant/entity scope chip is the "whose data am I looking at" anchor
              that a multi-tenant platform must never let you lose (doc 02 §2). */}
          <div className="flex items-center gap-2 rounded-md border border-hairline bg-surface-2 px-2.5 py-1">
            <Building2 size={14} className="text-ink-muted" aria-hidden />
            <span className="text-small font-medium">Meridian Group</span>
            <span className="text-ink-muted">/</span>
            <span className="text-small">UK-01</span>
          </div>
          <div className="flex-1" />
          <ThemeToggle />
        </header>

        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
