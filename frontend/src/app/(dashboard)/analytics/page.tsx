"use client";
import { useQuery } from "@tanstack/react-query";
import { analyticsAPI, agentAPI, instagramAPI } from "@/lib/api";
import { useActiveBrand } from "@/store/useAppStore";
import { GlassCard } from "@/components/ui/GlassCard";
import { formatNumber } from "@/lib/utils";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import {
  BarChart2, Lightbulb, TrendingUp, Users, Target, CheckCircle2,
  Star, ArrowRight, Instagram, Heart, MessageCircle, Eye, Repeat2,
  ExternalLink, RefreshCw, Wifi, WifiOff, Zap,
} from "lucide-react";
import Link from "next/link";

const CONTENT_TYPE_COLORS: Record<string, string> = {
  Reel: "#E040FB", Carousel: "#448AFF", Graphic: "#69F0AE",
  Story: "#FF6E40", "AI Reel": "#FFD740",
};

function KPICard({ label, value, sub, icon: Icon, color = "text-brand-light", live = false }: {
  label: string; value: string | number; sub?: string;
  icon: React.ElementType; color?: string; live?: boolean;
}) {
  return (
    <GlassCard className="p-4 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-bl from-brand/5 to-transparent" />
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 ${color}`} />
        <span className="text-xs text-white/40">{label}</span>
        {live && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" title="Live" />}
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      {sub && <p className="text-xs text-white/30 mt-0.5">{sub}</p>}
    </GlassCard>
  );
}

export default function AnalyticsPage() {
  const activeBrand = useActiveBrand();

  // DB analytics (from agent runs)
  const { data: latestData, isLoading } = useQuery({
    queryKey: ["analytics-latest", activeBrand?.id],
    queryFn: () => activeBrand ? analyticsAPI.latest(activeBrand.id).then(r => r.data) : Promise.resolve(null),
    enabled: !!activeBrand,
    staleTime: 60000,
  });

  const { data: historyData } = useQuery({
    queryKey: ["analytics-history", activeBrand?.id],
    queryFn: () => activeBrand ? analyticsAPI.history(activeBrand.id).then(r => r.data) : Promise.resolve(null),
    enabled: !!activeBrand,
    staleTime: 60000,
  });

  // Latest run analyst report
  const { data: runsData } = useQuery({
    queryKey: ["runs", activeBrand?.id],
    queryFn: () => activeBrand ? agentAPI.listRuns(activeBrand.id).then(r => r.data) : Promise.resolve({ runs: [] }),
    enabled: !!activeBrand,
    staleTime: 30000,
  });

  // Live Instagram insights
  const { data: igData, isLoading: igLoading, refetch: refetchIG } = useQuery({
    queryKey: ["ig-insights-analytics", activeBrand?.id],
    queryFn: () => activeBrand ? instagramAPI.insights(activeBrand.id).then(r => r.data) : Promise.resolve({ connected: false }),
    enabled: !!activeBrand,
    staleTime: 120000,
  });

  // Posts for content type stats
  const { data: postsData } = useQuery({
    queryKey: ["ig-posts", activeBrand?.id],
    queryFn: () => activeBrand ? instagramAPI.getPosts(activeBrand.id).then(r => r.data) : Promise.resolve({ posts: [] }),
    enabled: !!activeBrand,
    staleTime: 30000,
  });

  const report       = latestData?.report ?? null;
  const history      = (historyData?.history ?? []) as Array<{ date: string; avgEngagementRate?: number; followerCount?: number }>;
  const latestRun    = runsData?.runs?.[0];
  // Type the analyst report fields so they can be used safely in JSX
  type AnalystRptType = {
    ig_connected?: boolean;
    username?: string;
    followerCount?: number;
    avgEngagementRate?: number;
    avgReach?: number;
    postsAnalyzed?: number;
    brand_strengths?: string[];
    content_opportunities?: string[];
    audience_insights?: Record<string, string[]>;
    benchmark_metrics?: Record<string, string>;
    content_recommendations?: string[];
    topPosts?: Array<Record<string, unknown>>;
    note?: string;
    [k: string]: unknown;
  };
  const analystRpt = (latestRun?.analystReport ?? report?.rawReport) as AnalystRptType | null;
  const ig           = igData ?? { connected: false };
  const allPosts     = postsData?.posts ?? [];

  // Content type breakdown from generated posts
  const contentTypeCount: Record<string, number> = {};
  allPosts.forEach((p: { contentType: string }) => {
    contentTypeCount[p.contentType] = (contentTypeCount[p.contentType] ?? 0) + 1;
  });
  const contentTypeData = Object.entries(contentTypeCount).map(([name, count]) => ({ name, count }));

  // Live top posts from analyst report
  const liveTopPosts = (ig.connected && analystRpt?.topPosts)
    ? (analystRpt.topPosts as Array<{
        id: string; caption?: string; engagementRate?: number;
        reach?: number; likes?: number; comments?: number;
        thumbnailUrl?: string; permalink?: string; mediaType?: string;
      }>)
    : (report?.topPosts ?? []) as Array<{ id: string; caption?: string; engagementRate?: number; reach?: number; likes?: number }>;

  if (!activeBrand) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] text-center">
        <BarChart2 className="w-12 h-12 text-brand-light/30 mb-4" />
        <p className="text-white/50">Select a brand to view analytics</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Analytics</h1>
          <p className="text-sm text-white/40 mt-0.5">
            {activeBrand.name} · {ig.connected ? "Live Instagram data" : "AI brand intelligence"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {ig.connected ? (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-500/10 border border-green-500/20">
              <Wifi className="w-3.5 h-3.5 text-green-400" />
              <span className="text-xs text-green-400">@{ig.username} · Live</span>
              <button onClick={() => refetchIG()} className="ml-1 hover:text-green-300 text-green-400/60 transition-colors">
                <RefreshCw className="w-3 h-3" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.05] border border-white/[0.08]">
              <WifiOff className="w-3.5 h-3.5 text-white/30" />
              <span className="text-xs text-white/30">IG Not connected</span>
            </div>
          )}
          <Link href="/agents" className="btn-primary flex items-center gap-2 text-sm">
            <TrendingUp className="w-4 h-4" /> Run Analysis
          </Link>
        </div>
      </div>

      {/* ── Live KPI cards ── */}
      {isLoading ? (
        <div className="grid grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <div key={i} className="skeleton h-28 rounded-2xl" />)}
        </div>
      ) : ig.connected ? (
        <div className="grid grid-cols-4 gap-4">
          <KPICard label="Followers"        value={formatNumber(ig.followers ?? 0)}         sub={`@${ig.username}`}               icon={Users}          color="text-white"       live />
          <KPICard label="Engagement Rate"  value={`${ig.avgEngagementRate ?? 0}%`}          sub={`${ig.postsAnalyzed ?? 0} posts analysed`} icon={TrendingUp}  color="text-brand-light" live />
          <KPICard label="Total Likes (30d)" value={formatNumber(ig.totalLikes30d ?? 0)}     sub="from recent posts"               icon={Heart}          color="text-pink-400"    live />
          <KPICard label="Comments (30d)"   value={formatNumber(ig.totalComments30d ?? 0)}   sub="from recent posts"               icon={MessageCircle}  color="text-blue-400"    live />
        </div>
      ) : report ? (
        <div className="grid grid-cols-4 gap-4">
          <KPICard label="Followers"        value={formatNumber(report.followerCount ?? 0)}  sub=""                                icon={Users}          />
          <KPICard label="Avg Reach"        value={formatNumber(report.avgReach ?? 0)}       sub=""                                icon={Eye}            />
          <KPICard label="Avg Engagement"   value={`${(report.avgEngagementRate ?? 0).toFixed(2)}%`} sub=""                       icon={TrendingUp}     />
          <KPICard label="Posts Analyzed"   value={report.postsAnalyzed ?? 0}                sub=""                                icon={BarChart2}      />
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "Followers", icon: Users }, { label: "Engagement", icon: TrendingUp },
            { label: "Reach", icon: Eye }, { label: "Posts", icon: BarChart2 },
          ].map(({ label, icon }) => (
            <KPICard key={label} label={label} value="—" sub="Run agents to populate" icon={icon} />
          ))}
        </div>
      )}

      {/* ── Charts row ── */}
      <div className="grid grid-cols-3 gap-6">
        {/* Engagement trend chart */}
        <GlassCard className="col-span-2 p-5">
          <h2 className="font-semibold text-white text-sm mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-brand-light" />
            Engagement Rate Trend
          </h2>
          {history.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={history} margin={{ top: 4, right: 4, bottom: 0, left: -10 }}>
                <defs>
                  <linearGradient id="engGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6C3CE1" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#6C3CE1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="date" tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 11 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={v => `${v}%`} />
                <Tooltip
                  contentStyle={{ background: "#1E1640", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, fontSize: 12 }}
                  formatter={(v: number) => [`${v.toFixed(2)}%`, "Engagement"]}
                />
                <Area type="monotone" dataKey="avgEngagementRate" stroke="#6C3CE1" strokeWidth={2} fill="url(#engGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[200px] flex flex-col items-center justify-center text-center">
              <BarChart2 className="w-8 h-8 text-brand-light/20 mb-2" />
              <p className="text-xs text-white/30">Trend data builds after multiple runs</p>
            </div>
          )}
        </GlassCard>

        {/* Content type breakdown */}
        <GlassCard className="p-5">
          <h2 className="font-semibold text-white text-sm mb-4 flex items-center gap-2">
            <Zap className="w-4 h-4 text-brand-light" />
            Content Mix
          </h2>
          {contentTypeData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={150}>
                <BarChart data={contentTypeData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="name" tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ background: "#1E1640", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, fontSize: 12 }}
                    formatter={(v: number) => [v, "Posts"]}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {contentTypeData.map((entry) => (
                      <Cell key={entry.name} fill={CONTENT_TYPE_COLORS[entry.name] ?? "#6C3CE1"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="mt-3 space-y-1.5">
                {contentTypeData.map(({ name, count }) => (
                  <div key={name} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: CONTENT_TYPE_COLORS[name] ?? "#6C3CE1" }} />
                      <span className="text-white/50">{name}</span>
                    </div>
                    <span className="text-white/70 font-medium">{count} posts</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="h-[150px] flex items-center justify-center">
              <p className="text-xs text-white/30">Run agents to see content mix</p>
            </div>
          )}
        </GlassCard>
      </div>

      {/* ── Top Posts ── */}
      {(liveTopPosts as unknown[]).length > 0 && (
        <GlassCard className="p-5">
          <h2 className="font-semibold text-white text-sm mb-4 flex items-center gap-2">
            <Star className="w-4 h-4 text-yellow-400" />
            Top Performing Posts
            {ig.connected && <span className="text-[10px] px-2 py-0.5 bg-green-500/10 text-green-400 border border-green-500/20 rounded-full ml-1">Live from Instagram</span>}
          </h2>
          <div className="grid grid-cols-2 gap-3">
            {(liveTopPosts as Array<{
              id: string; caption?: string; engagementRate?: number;
              reach?: number; likes?: number; comments?: number;
              thumbnailUrl?: string; permalink?: string; mediaType?: string;
            }>).slice(0, 6).map((post) => (
              <div key={post.id} className="flex items-start gap-3 p-3 rounded-xl bg-dark-mid/40 border border-white/[0.05] hover:border-white/[0.10] transition-colors">
                {/* Thumbnail */}
                {post.thumbnailUrl ? (
                  <img src={post.thumbnailUrl} alt="" className="w-14 h-14 rounded-xl object-cover flex-shrink-0 border border-white/[0.08]" />
                ) : (
                  <div className="w-14 h-14 rounded-xl bg-brand/10 flex items-center justify-center flex-shrink-0">
                    <Instagram className="w-5 h-5 text-brand-light/40" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-white/60 line-clamp-2 mb-2">{post.caption ?? "No caption"}</p>
                  <div className="flex items-center gap-3 text-[11px] text-white/40">
                    <span className="flex items-center gap-1"><Heart className="w-3 h-3 text-pink-400" />{formatNumber(post.likes ?? 0)}</span>
                    <span className="flex items-center gap-1"><MessageCircle className="w-3 h-3 text-blue-400" />{formatNumber(post.comments ?? 0)}</span>
                    {post.reach != null && post.reach > 0 && <span className="flex items-center gap-1"><Eye className="w-3 h-3" />{formatNumber(post.reach)}</span>}
                  </div>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-[11px] font-semibold text-brand-light">{(post.engagementRate ?? 0).toFixed(2)}% ER</span>
                    {post.permalink && (
                      <a href={post.permalink} target="_blank" rel="noopener noreferrer"
                        className="text-white/20 hover:text-white/60 transition-colors">
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {/* ── AI Brand Intelligence ── */}
      {analystRpt && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 px-1">
            <div className="w-2 h-2 rounded-full bg-brand animate-pulse" />
            <p className="text-sm text-white/50 font-medium">AI Brand Intelligence</p>
            {!!analystRpt.ig_connected && <span className="text-[10px] px-2 py-0.5 bg-brand/10 text-brand-light border border-brand/20 rounded-full">Based on live IG data</span>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Brand Strengths */}
            {Array.isArray(analystRpt.brand_strengths) && analystRpt.brand_strengths.length > 0 && (
              <GlassCard className="p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Star className="w-4 h-4 text-yellow-400" />
                  <h2 className="font-semibold text-white text-sm">Brand Strengths</h2>
                </div>
                <ul className="space-y-2">
                  {(analystRpt.brand_strengths as string[]).map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-white/70">
                      <CheckCircle2 className="w-3.5 h-3.5 text-green-400 flex-shrink-0 mt-0.5" />{s}
                    </li>
                  ))}
                </ul>
              </GlassCard>
            )}

            {/* Content Opportunities */}
            {Array.isArray(analystRpt.content_opportunities) && analystRpt.content_opportunities.length > 0 && (
              <GlassCard className="p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Lightbulb className="w-4 h-4 text-yellow-400" />
                  <h2 className="font-semibold text-white text-sm">Content Opportunities</h2>
                </div>
                <ul className="space-y-2">
                  {(analystRpt.content_opportunities as string[]).map((o, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-white/70">
                      <ArrowRight className="w-3.5 h-3.5 text-brand-light flex-shrink-0 mt-0.5" />{o}
                    </li>
                  ))}
                </ul>
              </GlassCard>
            )}
          </div>

          {/* Audience Insights */}
          {!!analystRpt.audience_insights && typeof analystRpt.audience_insights === "object" && (
            <GlassCard className="p-5">
              <div className="flex items-center gap-2 mb-4">
                <Users className="w-4 h-4 text-brand-light" />
                <h2 className="font-semibold text-white text-sm">Audience Intelligence</h2>
              </div>
              <div className="grid grid-cols-3 gap-4">
                {Object.entries(analystRpt.audience_insights as Record<string, string[]>).map(([key, values]) => (
                  <div key={key}>
                    <p className="text-xs text-white/40 font-medium mb-2 uppercase tracking-wider">{key.replace(/_/g, " ")}</p>
                    <ul className="space-y-1">
                      {(Array.isArray(values) ? values : []).map((v: string, i: number) => (
                        <li key={i} className="text-xs text-white/60 flex items-start gap-1.5">
                          <span className="text-brand-light mt-0.5">•</span> {String(v)}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}

          {/* AI Content Recommendations */}
          {(Array.isArray(analystRpt.content_recommendations) && (analystRpt.content_recommendations as string[]).length > 0) ? (
            <GlassCard className="p-5">
              <div className="flex items-center gap-2 mb-4">
                <Target className="w-4 h-4 text-brand-light" />
                <h2 className="font-semibold text-white text-sm">AI Content Recommendations</h2>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {(analystRpt.content_recommendations as string[]).map((r, i) => (
                  <div key={i} className="flex items-start gap-2 px-3 py-2.5 rounded-xl bg-brand/5 border border-brand/10">
                    <span className="text-brand-light font-bold text-sm flex-shrink-0">{i + 1}.</span>
                    <p className="text-sm text-white/70">{r}</p>
                  </div>
                ))}
              </div>
            </GlassCard>
          ) : null}

          {/* Benchmark metrics */}
          {analystRpt.benchmark_metrics && typeof analystRpt.benchmark_metrics === "object" && (
            <GlassCard variant="dark" className="p-5">
              <div className="flex items-center gap-2 mb-3">
                <BarChart2 className="w-4 h-4 text-brand-light" />
                <h2 className="font-semibold text-white text-sm">Industry Benchmarks</h2>
              </div>
              <div className="flex flex-wrap gap-8">
                {Object.entries(analystRpt.benchmark_metrics as Record<string, string>).map(([k, v]) => (
                  <div key={k}>
                    <p className="text-xs text-white/40 mb-0.5">{k.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}</p>
                    <p className="text-sm font-semibold text-brand-light">{v}</p>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}

          {analystRpt.note && (
            <p className="text-xs text-white/30 px-1">{String(analystRpt.note)}</p>
          )}
        </div>
      )}

      {/* Empty state */}
      {!report && !analystRpt && !ig.connected && (
        <GlassCard className="p-16 flex flex-col items-center text-center">
          <BarChart2 className="w-10 h-10 text-brand-light/40 mb-3" />
          <p className="text-white/50 text-sm">No analytics data yet</p>
          <p className="text-white/30 text-xs mt-1 mb-5">Run the agent pipeline to generate brand intelligence</p>
          <div className="flex gap-3">
            <Link href="/agents" className="btn-primary text-sm">Run Agents Now</Link>
            <Link href="/brands" className="btn-ghost text-sm">Connect Instagram</Link>
          </div>
        </GlassCard>
      )}
    </div>
  );
}
