"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
// Auth bypass — signOut replaced with redirect
import { cn } from "@/lib/utils";
import { useAppStore, useActiveBrand } from "@/store/useAppStore";
import { instagramAPI } from "@/lib/api";
import { getInitials } from "@/lib/utils";
import {
  LayoutDashboard,
  Layers,
  Play,
  CalendarDays,
  Paintbrush,
  BarChart2,
  Settings,
  ChevronDown,
  Zap,
  LogOut,
  Instagram,
} from "lucide-react";

export function Sidebar() {
  const pathname    = usePathname();
  const activeBrand = useActiveBrand();
  const { brands, setActiveBrand, activeBrandId } = useAppStore();

  // Live: count posts needing action (draft/approved)
  const { data: postsData } = useQuery({
    queryKey: ["sidebar-posts", activeBrandId],
    queryFn: () => instagramAPI.getPosts(activeBrandId!).then((r) => r.data),
    enabled: !!activeBrandId,
    staleTime: 30_000,
    refetchInterval: 60_000,
    select: (d) => ({
      drafts:    (d.posts as Array<{ status: string }>).filter((p) => p.status === "draft").length,
      approved:  (d.posts as Array<{ status: string }>).filter((p) => p.status === "approved").length,
      scheduled: (d.posts as Array<{ status: string }>).filter((p) => p.status === "scheduled").length,
    }),
  });

  const pendingCount = (postsData?.drafts ?? 0) + (postsData?.approved ?? 0);

  const NAV_ITEMS = [
    { href: "/dashboard",  label: "Dashboard",   icon: LayoutDashboard, badge: null },
    { href: "/brands",     label: "Brand Hub",   icon: Layers,          badge: null },
    { href: "/agents",     label: "Run Agents",  icon: Play,            badge: null },
    { href: "/calendar",   label: "Calendar",    icon: CalendarDays,    badge: pendingCount || null },
    { href: "/designer",   label: "Designer",    icon: Paintbrush,      badge: null },
    { href: "/analytics",  label: "Analytics",   icon: BarChart2,       badge: null },
    { href: "/settings",   label: "Settings",    icon: Settings,        badge: null },
  ];

  const brandColor = (activeBrand?.colors as { primary?: string } | undefined)?.primary ?? "#6C3CE1";

  return (
    <aside className="fixed left-0 top-0 h-screen w-60 flex flex-col z-40 bg-dark-base/90 backdrop-blur-xl border-r border-white/[0.06]">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 h-16 border-b border-white/[0.06]">
        <div className="w-8 h-8 rounded-lg bg-brand flex items-center justify-center shadow-brand">
          <Zap className="w-4 h-4 text-white" />
        </div>
        <div>
          <span className="font-bold text-base tracking-tight text-white">
            Social<span className="text-brand-light">OS</span>
          </span>
          <p className="text-[9px] text-white/60 -mt-0.5 tracking-wider uppercase" aria-hidden="true">PerformEdge</p>
        </div>
      </div>

      {/* Brand Switcher */}
      <div className="px-3 py-3 border-b border-white/[0.06]">
        <p className="text-[10px] uppercase tracking-widest text-white/50 px-1 mb-2">Active Brand</p>
        {brands.length === 0 ? (
          <Link href="/brands" className="flex items-center gap-2 px-3 py-2 rounded-xl border border-dashed border-white/[0.08] hover:border-brand/30 text-xs text-white/55 hover:text-white/80 transition-colors">
            <Zap className="w-3.5 h-3.5" /> Add your first brand
          </Link>
        ) : (
          <div className="relative">
            <select
              value={activeBrandId ?? ""}
              onChange={(e) => setActiveBrand(e.target.value || null)}
              className="w-full bg-dark-mid/60 border border-white/[0.08] rounded-xl pl-9 pr-7 py-2 text-sm text-white appearance-none cursor-pointer focus:outline-none focus:border-brand/50 transition-colors hover:border-white/[0.15]"
            >
              <option value="">Select brand…</option>
              {brands.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
            {/* Color dot */}
            <div
              className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 rounded-full flex items-center justify-center text-[8px] font-bold text-white pointer-events-none"
              style={{ backgroundColor: brandColor }}
            >
              {activeBrand ? getInitials(activeBrand.name) : ""}
            </div>
            <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/40 pointer-events-none" />
          </div>
        )}

        {/* IG connected indicator */}
        {activeBrand && (activeBrand as { igUsername?: string }).igUsername && (
          <div className="flex items-center gap-1.5 mt-1.5 px-1">
            <Instagram className="w-3 h-3 text-pink-400" />
            <span className="text-[10px] text-pink-400/70">@{(activeBrand as { igUsername?: string }).igUsername}</span>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        {NAV_ITEMS.map(({ href, label, icon: Icon, badge }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href + "/"));
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 group relative",
                active
                  ? "bg-brand/15 text-brand-light border border-brand/20"
                  : "text-white/50 hover:text-white/80 hover:bg-white/[0.04]"
              )}
            >
              <Icon className={cn(
                "w-4 h-4 flex-shrink-0 transition-colors",
                active ? "text-brand-light" : "text-white/40 group-hover:text-white/60"
              )} />
              <span className="flex-1">{label}</span>
              {badge !== null && badge !== undefined && badge > 0 && (
                <span className="min-w-[18px] h-[18px] rounded-full bg-brand text-white text-[10px] font-bold flex items-center justify-center px-1">
                  {badge > 99 ? "99+" : badge}
                </span>
              )}
              {active && !badge && (
                <span className="w-1.5 h-1.5 rounded-full bg-brand-light" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer — quick sign out */}
      <div className="px-3 py-3 border-t border-white/[0.06]">
        <button
          onClick={() => { window.location.href = "/auth/login"; }}
          className="flex items-center gap-2.5 w-full px-3 py-2 rounded-xl text-xs text-white/55 hover:text-red-400 hover:bg-red-500/5 transition-colors group"
        >
          <LogOut className="w-3.5 h-3.5 group-hover:text-red-400 transition-colors" />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
