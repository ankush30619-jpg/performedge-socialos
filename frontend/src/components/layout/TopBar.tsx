"use client";
import { useState, useRef, useEffect } from "react";
import { useActiveBrand } from "@/store/useAppStore";
import { useQuery } from "@tanstack/react-query";
import { instagramAPI } from "@/lib/api";
import { Bell, Search, Instagram, Wifi, WifiOff, X } from "lucide-react";
import { getInitials } from "@/lib/utils";

type Notif = { id: string; msg: string; time: string; type: "success" | "error" | "info"; read: boolean };

export function TopBar() {
  const activeBrand = useActiveBrand();
  // Auth bypass — mock session user
  const mockUser = { name: "Dev User", email: "dev@socialos.local" };
  const [showNotifs, setShowNotifs]   = useState(false);
  const [notifs, setNotifs]           = useState<Notif[]>([]);
  const [searchVal, setSearchVal]     = useState("");
  const notifRef                      = useRef<HTMLDivElement>(null);

  const brandColor = (activeBrand?.colors as { primary?: string } | undefined)?.primary ?? "#6C3CE1";

  // Close notif panel on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifs(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Live IG status in topbar
  const { data: insights } = useQuery({
    queryKey: ["topbar-insights", activeBrand?.id],
    queryFn: () => instagramAPI.insights(activeBrand!.id).then((r) => r.data),
    enabled: !!activeBrand?.id,
    staleTime: 60_000,
    refetchInterval: 120_000,
  });

  const igConnected  = insights?.igConnected ?? false;
  const followerCount = insights?.followerCount;

  const unreadCount = notifs.filter(n => !n.read).length;

  function markAllRead() {
    setNotifs(ns => ns.map(n => ({ ...n, read: true })));
  }

  function clearNotif(id: string) {
    setNotifs(ns => ns.filter(n => n.id !== id));
  }

  const userInitial = mockUser.name?.[0]?.toUpperCase() ?? "D";

  return (
    <header className="fixed top-0 left-60 right-0 h-16 z-30 flex items-center justify-between px-6 bg-dark-base/80 backdrop-blur-xl border-b border-white/[0.06]">
      {/* Search */}
      <div className="relative w-72">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/25 pointer-events-none" />
        <input
          type="text"
          value={searchVal}
          onChange={e => setSearchVal(e.target.value)}
          placeholder="Search brands, runs, assets…"
          className="w-full bg-dark-mid/40 border border-white/[0.08] rounded-xl pl-9 pr-4 py-2 text-sm text-white/70 placeholder:text-white/25 focus:outline-none focus:border-brand/40 focus:bg-dark-mid/60 transition-all"
        />
        {searchVal && (
          <button onClick={() => setSearchVal("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60">
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">

        {/* IG status pill */}
        {activeBrand && (
          <div className={`flex items-center gap-2 rounded-full px-3 py-1.5 border text-xs font-medium transition-all
            ${igConnected
              ? "bg-green-500/10 border-green-500/20 text-green-300"
              : "bg-dark-mid/60 border-white/[0.08] text-white/30"}`}>
            {igConnected
              ? <><Wifi className="w-3 h-3" /> {followerCount?.toLocaleString("en-IN") ?? "—"} followers</>
              : <><WifiOff className="w-3 h-3" /> No IG</>}
          </div>
        )}

        {/* Active brand pill */}
        {activeBrand && (
          <div className="flex items-center gap-2 bg-dark-mid/60 border border-white/[0.08] rounded-full px-3 py-1.5">
            {(activeBrand as { igUsername?: string }).igUsername
              ? <Instagram className="w-3.5 h-3.5 text-pink-400 flex-shrink-0" />
              : (
                <div
                  className="w-4 h-4 rounded-full flex items-center justify-center text-[8px] font-bold text-white flex-shrink-0"
                  style={{ backgroundColor: brandColor }}
                >
                  {getInitials(activeBrand.name)}
                </div>
              )}
            <span className="text-xs text-white/70 max-w-[120px] truncate">{activeBrand.name}</span>
          </div>
        )}

        {/* Notifications */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => { setShowNotifs(o => !o); if (!showNotifs) markAllRead(); }}
            className="relative w-9 h-9 rounded-xl bg-dark-mid/60 border border-white/[0.08] flex items-center justify-center text-white/50 hover:text-white/80 hover:border-white/[0.15] transition-all"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-[16px] rounded-full bg-brand text-white text-[9px] font-bold flex items-center justify-center px-0.5">
                {unreadCount}
              </span>
            )}
          </button>

          {showNotifs && (
            <div className="absolute right-0 top-12 w-80 glass rounded-2xl border border-white/[0.08] shadow-2xl py-2 z-50">
              <div className="flex items-center justify-between px-4 py-2 border-b border-white/[0.06]">
                <span className="text-xs font-semibold text-white">Notifications</span>
                {notifs.length > 0 && (
                  <button onClick={() => setNotifs([])} className="text-[10px] text-white/30 hover:text-white/60">Clear all</button>
                )}
              </div>
              {notifs.length === 0 ? (
                <div className="flex flex-col items-center py-8 gap-2">
                  <Bell className="w-8 h-8 text-white/10" />
                  <p className="text-xs text-white/25">No notifications yet</p>
                </div>
              ) : (
                <div className="max-h-80 overflow-y-auto">
                  {notifs.map(n => (
                    <div key={n.id} className={`flex items-start gap-3 px-4 py-3 hover:bg-white/[0.03] transition-colors ${!n.read ? "bg-brand/5" : ""}`}>
                      <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${n.type === "success" ? "bg-green-400" : n.type === "error" ? "bg-red-400" : "bg-brand"}`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-white/70">{n.msg}</p>
                        <p className="text-[10px] text-white/25 mt-0.5">{n.time}</p>
                      </div>
                      <button onClick={() => clearNotif(n.id)} className="text-white/20 hover:text-white/50 flex-shrink-0">
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* User avatar */}
        <div
          className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand to-indigo-500 flex items-center justify-center text-xs font-bold text-white cursor-pointer shadow-brand"
          title={mockUser.email}
        >
          {userInitial}
        </div>
      </div>
    </header>
  );
}
