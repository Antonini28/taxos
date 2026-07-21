import type { Metadata } from "next";

import { AppShell } from "@/components/AppShell";
import { QueryProvider } from "@/components/QueryProvider";

import "./globals.css";

export const metadata: Metadata = {
  title: "TaxOS — Enterprise Agentic Tax Operating System",
  description:
    "Agents prepare. Humans decide. Everything is evidence. Governed multi-agent AI for enterprise tax compliance.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-GB" suppressHydrationWarning>
      <body>
        <QueryProvider>
          <AppShell>{children}</AppShell>
        </QueryProvider>
      </body>
    </html>
  );
}
