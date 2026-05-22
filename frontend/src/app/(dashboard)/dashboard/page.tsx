"use client";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { brandAPI, agentAPI, instagramAPI } from "@/lib/api";
import { useAppStore, useActiveBrand } from "@/store/useAppStore";
import { GlassCard } from "@/components/ui/GlassCard";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { AgentNode } from "@/components/ui/AgentNode";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { formatRelativeTime } from "@/lib/utils";
import {
  Layers, Play, TrendingUp, FileText, ArrowRight, Sparkles,
  Instagram, Users, Heart, MessageCircle, BarChart2, Calendar,
  CheckCircle2, Clock, AlertCircle, Zap, CalendarClock,
  Brain, Paintbrush,
} from "lucide-react";
import Link from "next/link";
import type { Brand } from "@/types";

const AGENT_ORDER = [
  "brandManager","analyst","researchAgent","competitorTracker",
  "growthPlanner","strategist","copywriter","designer",
];

export default function DashboardPage() {
  const { setBrands, activeBrandId } = useAppStore();
  const activeBrand = useActiveBrand();

  // Load brands
  const { data: brandsData } = useQuery({
    queryKey: ["brands"],
    queryFn: () => brandAPI.list().then((r) => r.data),
    staleTime: 30000,
  });

  useEffect(() => {
    if (brandsData?.brands) setBrands(brandsData.brands);
  }, [brandsData, setBrands]);

  // Load recent runs
  const { data: runsData } = useQuery({
    queryKey: ["runs", activeBrandId],
    queryFn: () =>
      activeBrandId
        ? agentAPI.listRuns(activeBrandId).then((r) => r.data)
        : Promise.resolve({ runs: [] }),
    enabled: !!activeBrandId,
    refetchInterval: 10000,
  });

  // Live Instagram insights
  const { data: igInsights } = useQuery({
    queryKey: ["ig-insights", activeBrandId],
    queryFn: () =>
      activeBrandId
        ? instagramAPI.insights(activeBrandId).then((r) => r.data)
        : Promise.resolve({ connected: false }),
    enabled: !!activeBrandId,
    staleTime: 60000,
  });

  // Calendar posts for approval stats
  const { data: calendarData } = useQuery({
    queryKey: ["ig-posts", activeBrandId],
    queryFn: () =>
      activeBrandId
        ? instagramAPI.getPosts(activeBrandId).then((r) => r.data)
        : Promise.resolve({ posts: [] }),
    enabled: !!activeBrandId,
    staleTime: 15000,
  });

  const brands = brandsData?.brands ?? [];
  const runs   = runsData?.runs ?? [];
  const latestRun = runs[0] ?? null;
  const posts  = calendarData?.posts ?? [];
  const igData = igInsights ?? { connected: false };

  // Agent progress
  const agentStatuses  = latestRun?.agentStatuses ?? {};
  const completedCount = Object.values(agentStatuses).filter(
    (s: unknown) => (s as { status?: string })?.status === "completed"
  ).length;
  const progressPct = AGENT_ORDER.length > 0 ? (completedCount / AGENT_ORDER.length) * 100 : 0;

  // Post stats
  const approvedPosts   = posts.filter((p: { status: string }) => p.status === "approved").length;
  const publishedPosts  = posts.filter((p: { status: string }) => p.status === "published").length;
  const draftPosts      = posts.filter((p: { status: string }) => p.status === "draft").length;
  const scheduledPosts  = posts.filter((p: { status: string; scheduledAt?: string }) => p.status === "scheduled")
    .sort((a: { scheduledAt?: string }, b: { scheduledAt?: string }) =>
      new Date(a.scheduledAt ?? 0).getTime() - new Date(b.scheduledAt ?? 0).getTime()
    ).slice(0, 3) as Array<{ id: string; topic: string; contentType: string; scheduledAt?: string; status: string }>;

  // No brand → onboarding
  if (!activeBrand) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Welcome to SocialOS</h1>
          <p className="text-sm text-white/40 mt-0.5">Your AI-powered social media automation platform</p>
        </div>
        <GlassCard className="p-8">
          <div className="flex items-start gap-6">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-brand to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-brand">
              <Zap className="w-7 h-7 text-white" />
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-bold text-white mb-1">Get started in 4 steps</h2>
              <p className="text-sm text-white/40 mb-6">Set up your brand once, let AI do the rest</p>
              <div className="space-y-3">
                {[
                  { step: 1, label: "Create a Brand",           sub: "Add your brand info, logo & colors",   href: "/brands",   icon: Layers,      done: brands.length > 0 },
                  { step: 2, label: "Connect Instagram",        sub: "OAuth via Meta to unlock publishing",  href: "/brands",   icon: Instagram,   done: brands.some((b: Brand) => !!(b as Brand & { igAccountId?: string }).igAccountId) },
                  { step: 3, label: "Run Agent Pipeline",       sub: "AI generates content calendar + posts",href: "/agents",   icon: Brain,       done: runs.length > 0 },
                  { step: 4, label: "Approve & Publish",        sub: "Review, schedule, publish to Instagram",href: "/calendar", icon: Paintbrush,  done: publishedPosts > 0 },
                ].map(({ step, label, sub, href, icon: Icon, done }) => (
                  <Link key={step} href={href}
                    className={`flex items-center gap-4 p-4 rounded-xl border transition-all group
                      ${done
                        ? "border-green-500/20 bg-green-500/5 cursor-default"
                        : "border-white/[0.08] hover:border-brand/40 hover:bg-brand/5"}`}>
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 transition-colors
                      ${done ? "bg-green-500/20 text-green-400" : "bg-brand/15 text-brand-light group-hover:bg-brand/25"}`}>
                      {done ? <CheckCircle2 className="w-4 h-4" /> : step}
                    </div>
                    <Icon className={`w-4 h-4 flex-shrink-0 ${done ? "text-green-400" : "text-brand-light"}`} />
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-medium ${done ? "text-white/50 line-through" : "text-white"}`}>{label}</p>
                      <p className="text-xs text-white/30">{sub}</p>
                    </div>
                    {!done && <ArrowRight className="w-4 h-4 text-white/20 group-hover:text-brand-light transition-colors flex-shrink-0" />}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            {activeBrand.name} Overview
          </h1>
          <p className="text-sm text-white/40 mt-0.5">
            {activeBrand.niche ?? "Brand"} · AI-powered social intelligence
          </p>
        </div>
        <Link href="/agents" className="btn-primary flex items-center gap-2 text-sm">
          <Play className="w-4 h-4" /> Run Agents
        </Link>
      </div>

      {/* Top KPI row */}
      <div className="grid grid-cols-4 gap-4">
        {/* Instagram Followers — live if connected */}
        {igData.connected ? (
          <GlassCard className="p-4 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-purple-500/10 to-transparent" />
            <div className="flex items-center gap-2 mb-2">
              <Instagram className="w-4 h-4 text-pink-400" />
              <span className="text-xs text-white/40">Followers</span>
              <span className="ml-auto w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" title="Live" />
            </div>
            <p className="text-2xl font-bold text-white">
              {igData.followers?.toLocaleString("en-IN") ?? "—"}
            </p>
            <p className="text-xs text-white/30 mt-0.5">@{igData.username}</p>
          </GlassCard>
        ) : (
          <MetricCard
            label="Total Brands"
            value={brands.length}
            icon={<Layers className="w-4 h-4 text-brand-light" />}
          />
        )}

        {/* Engagement Rate */}
        {igData.connected ? (
          <GlassCard className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Heart className="w-4 h-4 text-pink-400" />
              <span className="text-xs text-white/40">Engagement Rate</span>
            </div>
            <p className="text-2xl font-bold text-white">{igData.avgEngagementRate ?? "—"}%</p>
            <p className="text-xs text-white/30 mt-0.5">{igData.postsAnalyzed} posts analysed</p>
          </GlassCard>
        ) : (
          <MetricCard
            label="Agent Runs"
            value={runs.length}
            icon={<Play className="w-4 h-4 text-brand-light" />}
          />
        )}

        {/* Posts Generated */}
        <MetricCard
          label="Posts Generated"
          value={runs.reduce((acc: number, r: { postsGenerated?: number }) => acc + (r.postsGenerated ?? 0), 0)}
          icon={<FileText className="w-4 h-4 text-brand-light" />}
        />

        {/* Published */}
        <GlassCard className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="w-4 h-4 text-brand-light" />
            <span className="text-xs text-white/40">Published</span>
          </div>
          <p className="text-2xl font-bold text-white">{publishedPosts}</p>
          <p className="text-xs text-white/30 mt-0.5">{approvedPosts} approved · {draftPosts} pending</p>
        </GlassCard>
      </div>

      {/* Middle row */}
      <div className="grid grid-cols-3 gap-6">
        {/* Latest Run — col-span-2 */}
        <div className="col-span-2 space-y-4">
          <GlassCard className="p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-brand-light" />
                <h2 className="font-semibold text-white text-sm">Latest Agent Run</h2>
              </div>
              {latestRun && (
                <StatusBadge status={latestRun.status as "idle" | "running" | "completed" | "failed" | "pending"} />
              )}
            </div>

            {latestRun ? (
              <>
                <div className="mb-4">
                  <ProgressBar value={progressPct} label={`${completedCount}/${AGENT_ORDER.length} agents completed`} />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {AGENT_ORDER.map((key) => {
                    const agentData = agentStatuses[key] as { status?: string; message?: string } | undefined;
                    return (
                      <AgentNode
                        key={key}
                        agentKey={key}
                        status={(agentData?.status as "pending" | "running" | "completed" | "failed" | "skipped") ?? "pending"}
                        message={agentData?.message}
                      />
                    );
                  })}
                </div>
                <div className="mt-4 pt-4 border-t border-white/[0.06] flex items-center justify-between text-xs text-white/40">
                  <span>Started {formatRelativeTime(latestRun.createdAt)}</span>
                  <Link href="/agents" className="flex items-center gap-1 text-brand-light hover:text-brand-light/80">
                    View details <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              </>
            ) : (
              <div className="py-12 flex flex-col items-center text-center">
                <div className="w-12 h-12 rounded-full bg-brand/10 flex items-center justify-center mb-3">
                  <Play className="w-5 h-5 text-brand-light" />
                </div>
                <p className="text-sm text-white/50">No runs yet</p>
                <p className="text-xs text-white/30 mt-1">
                  {activeBrand ? "Start your first agent run" : "Select a brand first"}
                </p>
                <Link href="/agents" className="btn-primary mt-4 text-xs">Run Agents Now</Link>
              </div>
            )}
          </GlassCard>

          {/* Instagram Live Stats (when connected) */}
          {igData.connected && (
            <GlassCard className="p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Instagram className="w-4 h-4 text-pink-400" />
                  <h2 className="font-semibold text-white text-sm">Live Instagram Stats</h2>
                  <span className="text-[10px] px-2 py-0.5 bg-green-500/10 text-green-400 border border-green-500/20 rounded-full">Live</span>
                </div>
                <span className="text-xs text-white/30">@{igData.username}</span>
              </div>
              <div className="grid grid-cols-4 gap-3">
                {[
                  { icon: Users, label: "Followers",   value: igData.followers?.toLocaleString("en-IN") ?? "—",      color: "text-white" },
                  { icon: Heart, label: "Likes (30d)",  value: igData.totalLikes30d?.toLocaleString("en-IN") ?? "—",  color: "text-pink-400" },
                  { icon: MessageCircle, label: "Comments", value: igData.totalComments30d?.toLocaleString("en-IN") ?? "—", color: "text-blue-400" },
                  { icon: BarChart2, label: "Engagement", value: `${igData.avgEngagementRate ?? 0}%`, color: "text-brand-light" },
                ].map(({ icon: Icon, label, value, color }) => (
                  <div key={label} className="p-3 rounded-xl bg-dark-base/40 border border-white/[0.06] text-center">
                    <Icon className={`w-4 h-4 ${color} mx-auto mb-1.5`} />
                    <p className={`text-lg font-bold ${color}`}>{value}</p>
                    <p className="text-[11px] text-white/30 mt-0.5">{label}</p>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}
        </div>

        {/* Right column */}
        <div className="space-y-4">
          {/* Brand list */}
          <GlassCard className="p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-white text-sm flex items-center gap-2">
                <Layers className="w-4 h-4 text-brand-light" /> Brands
              </h2>
              <Link href="/brands" className="text-xs text-brand-light hover:text-brand-light/80">Manage</Link>
            </div>
            {brands.length === 0 ? (
              <div className="py-8 flex flex-col items-center text-center">
                <p className="text-sm text-white/40">No brands yet</p>
                <Link href="/brands" className="btn-primary mt-3 text-xs">Add Brand</Link>
              </div>
            ) : (
              <div className="space-y-2">
                {brands.slice(0, 6).map((brand: Brand) => (
                  <div
                    key={brand.id}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-dark-mid/40 border border-white/[0.05] hover:border-brand/20 transition-colors cursor-pointer"
                    onClick={() => useAppStore.getState().setActiveBrand(brand.id)}
                  >
                    <div
                      className="w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0"
                      style={{ backgroundColor: brand.colors?.primary || "#6C3CE1" }}
                    >
                      {brand.name.slice(0, 2).toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-white/80 truncate">{brand.name}</p>
                      {brand.niche && <p className="text-[11px] text-white/30 truncate">{brand.niche}</p>}
                    </div>
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      {brand.igUsername && <span title={`@${brand.igUsername}`}><Instagram className="w-3 h-3 text-green-400" /></span>}
                      {brand.id === activeBrandId && <span className="w-1.5 h-1.5 rounded-full bg-brand" />}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </GlassCard>

          {/* Quick actions */}
          <GlassCard className="p-5">
            <h2 className="font-semibold text-white text-sm flex items-center gap-2 mb-4">
              <Zap className="w-4 h-4 text-brand-light" /> Quick Actions
            </h2>
            <div className="space-y-2">
              {[
                { href: "/calendar", icon: Calendar,    label: "Review Calendar",     sub: `${draftPosts} drafts pending` },
                { href: "/agents",   icon: Play,         label: "Run Agent Pipeline",  sub: "Generate new content" },
                { href: "/analytics",icon: BarChart2,   label: "View Analytics",      sub: "Brand performance report" },
                { href: "/brands",   icon: Layers,       label: "Manage Brands",       sub: `${brands.length} brand${brands.length !== 1 ? "s" : ""} connected` },
              ].map(({ href, icon: Icon, label, sub }) => (
                <Link key={href} href={href}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/[0.05] border border-transparent hover:border-white/[0.06] transition-all group">
                  <div className="w-7 h-7 rounded-lg bg-brand/10 flex items-center justify-center flex-shrink-0">
                    <Icon className="w-3.5 h-3.5 text-brand-light" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm text-white/70 group-hover:text-white transition-colors">{label}</p>
                    <p className="text-[11px] text-white/30">{sub}</p>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-white/20 group-hover:text-brand-light ml-auto transition-colors" />
                </Link>
              ))}
            </div>
          </GlassCard>

          {/* Upcoming scheduled posts */}
          {scheduledPosts.length > 0 && (
            <GlassCard className="p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold text-white text-sm flex items-center gap-2">
                  <CalendarClock className="w-4 h-4 text-yellow-400" /> Scheduled
                </h2>
                <Link href="/calendar" className="text-xs text-brand-light hover:text-brand-light/80">View all</Link>
              </div>
              <div className="space-y-2">
                {scheduledPosts.map((p) => (
                  <div key={p.id} className="flex items-center gap-2 px-3 py-2 rounded-xl bg-yellow-500/5 border border-yellow-500/15">
                    <CalendarClock className="w-3.5 h-3.5 text-yellow-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-white/70 truncate">{p.topic}</p>
                      {p.scheduledAt && (
                        <p className="text-[10px] text-white/30 mt-0.5">
                          {new Date(p.scheduledAt).toLocaleString("en-IN", {
                            day: "numeric", month: "short", hour: "2-digit", minute: "2-digit"
                          })}
                        </p>
                      )}
                    </div>
                    <span className="text-[10px] text-yellow-400/70 flex-shrink-0">{p.contentType}</span>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}

          {/* Connect Instagram prompt (if not connected) */}
          {activeBrand && !igData.connected && (
            <GlassCard className="p-4 bg-gradient-to-br from-purple-500/5 to-pink-500/5 border border-purple-500/15">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center flex-shrink-0">
                  <Instagram className="w-4 h-4 text-pink-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white">Connect Instagram</p>
                  <p className="text-xs text-white/40 mt-0.5">Get live analytics and publish posts directly</p>
                  <Link href="/brands" className="inline-flex items-center gap-1 mt-2 text-xs text-pink-400 hover:text-pink-300">
                    Go to Brand Hub <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            </GlassCard>
          )}
        </div>
      </div>
    </div>
  );
}
