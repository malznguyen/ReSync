"use client";

import {
  BarChart3,
  Camera,
  LayoutDashboard,
  LogOut,
  Map,
  RadioTower
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { logout } from "@/lib/api";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  {
    href: "/dashboard",
    label: "Overview",
    icon: LayoutDashboard
  },
  {
    href: "/cameras",
    label: "Cameras",
    icon: Camera
  },
  {
    href: "/zones",
    label: "Zones",
    icon: Map
  },
  {
    href: "/events",
    label: "Events",
    icon: RadioTower
  },
  {
    href: "/analytics",
    label: "Analytics",
    icon: BarChart3
  }
] as const;

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps): JSX.Element {
  const pathname = usePathname();
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleLogout = async (): Promise<void> => {
    setIsLoggingOut(true);
    try {
      await logout();
      router.push("/login");
      router.refresh();
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <div className="min-h-screen dashboard-grid">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 border-r border-ink-900/10 bg-[#fffdf6]/88 px-5 py-6 shadow-panel backdrop-blur-xl lg:flex lg:flex-col">
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-ink-900 text-white shadow-control">
            <RadioTower className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <p className="font-display text-lg font-black tracking-normal text-ink-900">
              ReSync
            </p>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-ink-500">
              Vision Ops
            </p>
          </div>
        </Link>

        <nav className="mt-10 space-y-2">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active =
              pathname === item.href || pathname.startsWith(`${item.href}/`);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "group flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-bold transition",
                  active
                    ? "bg-ink-900 text-white shadow-control"
                    : "text-ink-500 hover:bg-ink-900/5 hover:text-ink-900"
                )}
              >
                <Icon
                  className={cn(
                    "h-4 w-4 transition",
                    active ? "text-lagoon-100" : "text-ink-500 group-hover:text-ink-900"
                  )}
                  aria-hidden="true"
                />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto rounded-lg border border-ink-900/10 bg-white/70 p-4">
          <p className="text-sm font-black text-ink-900">Low-latency mode</p>
          <p className="mt-1 text-xs leading-5 text-ink-500">
            Camera controls, zone edits, and event telemetry are routed through
            the Control API.
          </p>
          <Button
            className="mt-4 w-full"
            variant="secondary"
            onClick={handleLogout}
            disabled={isLoggingOut}
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            Sign out
          </Button>
        </div>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 border-b border-ink-900/10 bg-[#fffdf6]/80 px-4 py-3 backdrop-blur-xl lg:hidden">
          <div className="flex items-center justify-between">
            <Link href="/dashboard" className="flex items-center gap-2">
              <RadioTower className="h-5 w-5 text-ink-900" aria-hidden="true" />
              <span className="font-display font-black text-ink-900">ReSync</span>
            </Link>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              disabled={isLoggingOut}
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
              Sign out
            </Button>
          </div>
          <nav className="mt-3 flex gap-2 overflow-x-auto pb-1">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const active =
                pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-xs font-bold transition",
                    active
                      ? "bg-ink-900 text-white"
                      : "bg-white/70 text-ink-500"
                  )}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </header>
        <main className="mx-auto w-full max-w-7xl px-4 py-6 md:px-8 md:py-10">
          {children}
        </main>
      </div>
    </div>
  );
}
