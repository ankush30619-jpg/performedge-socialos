"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { instagramAPI, agentAPI } from "@/lib/api";
import { useActiveBrand } from "@/store/useAppStore";
import { GlassCard } from "@/components/ui/GlassCard";
import { CONTENT_TYPE_COLORS } from "@/lib/utils";
import {
  CalendarDays, Download, ChevronLeft, ChevronRight,
  CheckCircle2, XCircle, Send, Instagram, Image as ImageIcon,
  Hash, Clock, Eye, X, Loader2, Copy, AlertCircle, Sparkles,
  CalendarClock, Trash2,
} from "lucide-react";
import type { Post, DesignAsset } from "@/types";

const DAYS   = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = [
  "January","February","March","April","May","June",
  "July","August","September","October","November","December",
];

const STATUS_CONFIG = {
  draft:     { label: "Draft",     color: "text-white/40",    bg: "bg-white/[0.06]" },
  approved:  { label: "Approved",  color: "text-green-400",   bg: "bg-green-500/10" },
  rejected:  { label: "Rejected",  color: "text-red-400",     bg: "bg-red-500/10"   },
  scheduled: { label: "Scheduled", color: "text-yellow-400",  bg: "bg-yellow-500/10"},
  published: { label: "Published", color: "text-brand-light", bg: "bg-brand/10"     },
};

function buildCalendarGrid(year: number, month: number) {
  const first = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (number | null)[] = Array(first).fill(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

export default function CalendarPage() {
  const activeBrand = useActiveBrand();
  const queryClient = useQueryClient();
  const today = new Date();

  const [viewYear, setViewYear]   = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth());
  const [selectedPost, setSelectedPost]   = useState<Post | null>(null);
  const [publishingId, setPublishingId]   = useState<string | null>(null);
  const [schedulingPost, setSchedulingPost] = useState<Post | null>(null);
  const [publishMsg, setPublishMsg]       = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Fetch posts & assets
  const { data, isLoading } = useQuery({
    queryKey: ["ig-posts", activeBrand?.id],
    queryFn: () =>
      activeBrand
        ? instagramAPI.getPosts(activeBrand.id).then((r) => r.data)
        : Promise.resolve({ posts: [], designAssets: [], igConnected: false }),
    enabled: !!activeBrand,
    refetchInterval: 30_000, // 30s — calendar data doesn't change that fast; was 5s (wasteful)
  });

  const posts: Post[]          = data?.posts ?? [];
  const assets: DesignAsset[]  = data?.designAssets ?? [];
  const igConnected: boolean   = data?.igConnected ?? false;
  const igUsername: string     = data?.igUsername ?? "";

  // Also get latest run for download links
  const { data: runsData } = useQuery({
    queryKey: ["runs", activeBrand?.id],
    queryFn: () =>
      activeBrand
        ? agentAPI.listRuns(activeBrand.id).then((r) => r.data)
        : Promise.resolve({ runs: [] }),
    enabled: !!activeBrand,
  });
  const latestRun = runsData?.runs?.[0];

  // Approve / reject mutation
  const statusMutation = useMutation({
    mutationFn: ({ postId, status }: { postId: string; status: string }) =>
      instagramAPI.updateStatus(postId, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ig-posts", activeBrand?.id] }),
  });

  // Publish mutation
  async function handlePublish(post: Post) {
    if (!activeBrand) return;
    setPublishingId(post.id);
    setPublishMsg(null);

    try {
      // Find matching design asset for this post
      const asset = assets.find(
        (a) => a.contentType === post.contentType || a.topic === post.topic
      );
      const imageUrl = asset?.imageUrl;
      const caption = buildCaption(post);

      if (!imageUrl) {
        // Publish caption-only with placeholder image
        await instagramAPI.publishCaption({
          postId: post.id,
          brandId: activeBrand.id,
          caption,
          imageUrl: `https://placehold.co/1080x1080/6C3CE1/FFFFFF?text=${encodeURIComponent(post.contentType)}`,
        });
      } else {
        await instagramAPI.publish({
          postId: post.id,
          brandId: activeBrand.id,
          imageUrl,
          caption,
        });
      }

      setPublishMsg({ type: "success", text: "Published to Instagram! 🎉" });
      queryClient.invalidateQueries({ queryKey: ["ig-posts", activeBrand.id] });
      if (selectedPost?.id === post.id) {
        setSelectedPost({ ...post, status: "published" });
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message ?? "Publish failed";
      setPublishMsg({ type: "error", text: msg });
    } finally {
      setPublishingId(null);
    }
  }

  function buildCaption(post: Post): string {
    const hashtags = post.hashtags?.length ? "\n\n" + post.hashtags.map((h) => `#${h}`).join(" ") : "";
    return (post.caption ?? post.topic) + hashtags;
  }

  // Group posts by day in current view month
  const postsByDay: Record<number, Post[]> = {};
  posts.forEach((p) => {
    const d = new Date(p.date);
    if (d.getFullYear() === viewYear && d.getMonth() === viewMonth) {
      const day = d.getDate();
      if (!postsByDay[day]) postsByDay[day] = [];
      postsByDay[day].push(p);
    }
  });

  const cells = buildCalendarGrid(viewYear, viewMonth);

  function prevMonth() {
    if (viewMonth === 0) { setViewMonth(11); setViewYear((y) => y - 1); }
    else setViewMonth((m) => m - 1);
  }
  function nextMonth() {
    if (viewMonth === 11) { setViewMonth(0); setViewYear((y) => y + 1); }
    else setViewMonth((m) => m + 1);
  }

  // Stats
  const totalPosts    = posts.length;
  const approved      = posts.filter((p) => p.status === "approved").length;
  const published     = posts.filter((p) => p.status === "published").length;
  const scheduled     = posts.filter((p) => p.status === "scheduled").length;
  const drafts        = posts.filter((p) => p.status === "draft").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Content Calendar</h1>
          <p className="text-sm text-white/40 mt-0.5">
            {activeBrand
              ? `${activeBrand.name} — Approve, schedule & publish posts`
              : "Select a brand to view calendar"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {igConnected && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-500/10 border border-green-500/20">
              <Instagram className="w-3.5 h-3.5 text-green-400" />
              <span className="text-xs text-green-400 font-medium">@{igUsername}</span>
            </div>
          )}
          {latestRun?.excelUrl && (
            <a href={latestRun.excelUrl} target="_blank" rel="noopener noreferrer"
              className="btn-ghost flex items-center gap-2 text-sm">
              <Download className="w-4 h-4" /> Export Excel
            </a>
          )}
        </div>
      </div>

      {/* Publish toast */}
      {publishMsg && (
        <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border text-sm
          ${publishMsg.type === "success"
            ? "bg-green-500/15 border-green-500/30 text-green-300"
            : "bg-red-500/15 border-red-500/30 text-red-300"}`}>
          {publishMsg.type === "success"
            ? <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            : <AlertCircle className="w-4 h-4 flex-shrink-0" />}
          {publishMsg.text}
          <button onClick={() => setPublishMsg(null)} className="ml-auto hover:opacity-70">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Stats row */}
      {totalPosts > 0 && (
        <div className="grid grid-cols-5 gap-3">
          {[
            { label: "Total",     value: totalPosts, color: "text-white" },
            { label: "Drafts",    value: drafts,     color: "text-white/50" },
            { label: "Approved",  value: approved,   color: "text-green-400" },
            { label: "Scheduled", value: scheduled,  color: "text-yellow-400" },
            { label: "Published", value: published,  color: "text-brand-light" },
          ].map(({ label, value, color }) => (
            <GlassCard key={label} className="p-4 text-center">
              <p className={`text-2xl font-bold ${color}`}>{value}</p>
              <p className="text-xs text-white/40 mt-1">{label}</p>
            </GlassCard>
          ))}
        </div>
      )}

      {/* Content type legend */}
      <div className="flex items-center gap-4 flex-wrap">
        {Object.entries(CONTENT_TYPE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-xs text-white/50">{type}</span>
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <GlassCard className="p-5">
        {/* Month nav */}
        <div className="flex items-center justify-between mb-4">
          <button onClick={prevMonth} className="p-1.5 rounded-lg hover:bg-white/[0.08] text-white/40 hover:text-white transition-all">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <h2 className="font-semibold text-white text-sm">
            {MONTHS[viewMonth]} {viewYear}
          </h2>
          <button onClick={nextMonth} className="p-1.5 rounded-lg hover:bg-white/[0.08] text-white/40 hover:text-white transition-all">
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Day headers */}
        <div className="grid grid-cols-7 mb-2">
          {DAYS.map((d) => (
            <div key={d} className="text-center text-xs text-white/30 font-medium py-2">{d}</div>
          ))}
        </div>

        {/* Cells */}
        <div className="grid grid-cols-7 gap-1">
          {cells.map((day, i) => {
            if (!day) return <div key={`e-${i}`} className="h-24 rounded-xl" />;
            const dayPosts = postsByDay[day] ?? [];
            const isToday = day === today.getDate() && viewMonth === today.getMonth() && viewYear === today.getFullYear();

            return (
              <div
                key={day}
                className={`h-24 rounded-xl p-1.5 border transition-colors cursor-default ${
                  isToday ? "border-brand/40 bg-brand/5" : "border-white/[0.04] hover:border-white/[0.10]"
                }`}
              >
                <span className={`text-xs font-medium block mb-1 ${isToday ? "text-brand-light" : "text-white/40"}`}>
                  {day}
                </span>
                <div className="space-y-0.5 overflow-hidden">
                  {dayPosts.slice(0, 2).map((p, pi) => (
                    <button
                      key={pi}
                      onClick={() => setSelectedPost(p)}
                      className="w-full text-left text-[10px] truncate px-1 py-0.5 rounded hover:opacity-80 transition-opacity"
                      style={{
                        backgroundColor: `${CONTENT_TYPE_COLORS[p.contentType] ?? "#6C3CE1"}22`,
                        color: CONTENT_TYPE_COLORS[p.contentType] ?? "#A78BFA",
                      }}
                    >
                      {p.contentType}
                      {p.status === "published" && " ✓"}
                      {p.status === "approved" && " ●"}
                    </button>
                  ))}
                  {dayPosts.length > 2 && (
                    <p className="text-[10px] text-white/30 px-1">+{dayPosts.length - 2}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </GlassCard>

      {/* Post list with approve/publish actions */}
      {posts.length > 0 && (
        <GlassCard className="p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white text-sm">All Posts ({posts.length})</h2>
            <div className="flex gap-2 text-xs text-white/40">
              {!igConnected && (
                <span className="flex items-center gap-1 text-yellow-400/70">
                  <AlertCircle className="w-3.5 h-3.5" />
                  Connect Instagram to publish
                </span>
              )}
            </div>
          </div>
          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
            {posts.map((p) => {
              const st = STATUS_CONFIG[p.status as keyof typeof STATUS_CONFIG] ?? STATUS_CONFIG.draft;
              const asset = assets.find((a) => a.contentType === p.contentType || a.topic === p.topic);
              const isPublishing = publishingId === p.id;

              return (
                <div key={p.id}
                  className="flex items-start gap-3 px-4 py-3 rounded-xl bg-dark-mid/40 border border-white/[0.05] hover:border-white/[0.10] transition-colors group">
                  {/* Color dot */}
                  <div className="w-2 h-2 rounded-full mt-2 flex-shrink-0"
                    style={{ backgroundColor: CONTENT_TYPE_COLORS[p.contentType] ?? "#6C3CE1" }} />

                  {/* Thumbnail */}
                  {asset?.imageUrl ? (
                    <img src={asset.imageUrl} alt="" className="w-10 h-10 rounded-lg object-cover flex-shrink-0 border border-white/[0.08]" />
                  ) : (
                    <div className="w-10 h-10 rounded-lg bg-white/[0.04] flex items-center justify-center flex-shrink-0">
                      <ImageIcon className="w-4 h-4 text-white/20" />
                    </div>
                  )}

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                      <span className="text-xs text-white/40">
                        {new Date(p.date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                        style={{
                          backgroundColor: `${CONTENT_TYPE_COLORS[p.contentType] ?? "#6C3CE1"}22`,
                          color: CONTENT_TYPE_COLORS[p.contentType] ?? "#A78BFA",
                        }}>
                        {p.contentType}
                      </span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${st.bg} ${st.color}`}>
                        {st.label}
                      </span>
                    </div>
                    <p className="text-sm text-white/80 truncate">{p.topic}</p>
                    {p.caption && (
                      <p className="text-xs text-white/40 truncate mt-0.5">{p.caption}</p>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1.5 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                    {/* View details */}
                    <button onClick={() => setSelectedPost(p)}
                      className="p-1.5 rounded-lg hover:bg-white/[0.08] text-white/30 hover:text-white transition-all" title="View details">
                      <Eye className="w-3.5 h-3.5" />
                    </button>

                    {/* Approve */}
                    {p.status === "draft" && (
                      <button
                        onClick={() => statusMutation.mutate({ postId: p.id, status: "approved" })}
                        disabled={statusMutation.isPending}
                        className="p-1.5 rounded-lg hover:bg-green-500/20 text-white/30 hover:text-green-400 transition-all" title="Approve">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                      </button>
                    )}

                    {/* Reject */}
                    {(p.status === "draft" || p.status === "approved") && (
                      <button
                        onClick={() => statusMutation.mutate({ postId: p.id, status: "rejected" })}
                        disabled={statusMutation.isPending}
                        className="p-1.5 rounded-lg hover:bg-red-500/20 text-white/30 hover:text-red-400 transition-all" title="Reject">
                        <XCircle className="w-3.5 h-3.5" />
                      </button>
                    )}

                    {/* Schedule */}
                    {p.status === "approved" && igConnected && (
                      <button
                        onClick={() => setSchedulingPost(p)}
                        className="p-1.5 rounded-lg hover:bg-yellow-500/20 text-white/30 hover:text-yellow-400 transition-all" title="Schedule">
                        <CalendarClock className="w-3.5 h-3.5" />
                      </button>
                    )}

                    {/* Publish to Instagram */}
                    {p.status === "approved" && igConnected && (
                      <button
                        onClick={() => handlePublish(p)}
                        disabled={isPublishing}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-gradient-to-r from-purple-600/30 to-pink-600/30 border border-purple-500/30 hover:border-purple-400/60 text-pink-300 text-xs font-medium transition-all disabled:opacity-50"
                        title="Publish to Instagram">
                        {isPublishing
                          ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          : <Send className="w-3.5 h-3.5" />}
                        Publish
                      </button>
                    )}

                    {/* Cancel schedule */}
                    {p.status === "scheduled" && (
                      <button
                        onClick={async () => {
                          await instagramAPI.cancelSchedule(p.id);
                          queryClient.invalidateQueries({ queryKey: ["ig-posts", activeBrand?.id] });
                        }}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 text-xs font-medium hover:bg-yellow-500/20 transition-all"
                        title="Cancel schedule">
                        <Trash2 className="w-3.5 h-3.5" /> Cancel
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </GlassCard>
      )}

      {/* Empty state */}
      {posts.length === 0 && activeBrand && !isLoading && (
        <GlassCard className="p-16 flex flex-col items-center text-center">
          <CalendarDays className="w-10 h-10 text-brand-light/40 mb-3" />
          <p className="text-white/50 text-sm">No content calendar yet</p>
          <p className="text-white/30 text-xs mt-1">Run the agent pipeline to generate your content calendar</p>
        </GlassCard>
      )}

      {!activeBrand && (
        <GlassCard className="p-16 flex flex-col items-center text-center">
          <Sparkles className="w-10 h-10 text-brand-light/40 mb-3" />
          <p className="text-white/50 text-sm">Select a brand to get started</p>
        </GlassCard>
      )}

      {/* Schedule Modal */}
      {schedulingPost && (
        <ScheduleModal
          post={schedulingPost}
          assets={assets}
          brandId={activeBrand!.id}
          onClose={() => setSchedulingPost(null)}
          onScheduled={(msg) => {
            setSchedulingPost(null);
            setPublishMsg({ type: "success", text: msg });
            queryClient.invalidateQueries({ queryKey: ["ig-posts", activeBrand?.id] });
          }}
        />
      )}

      {/* Post Detail Modal */}
      {selectedPost && (
        <PostDetailModal
          post={selectedPost}
          assets={assets}
          igConnected={igConnected}
          publishingId={publishingId}
          onClose={() => setSelectedPost(null)}
          onStatusChange={(status) => {
            statusMutation.mutate({ postId: selectedPost.id, status });
            setSelectedPost({ ...selectedPost, status: status as Post["status"] });
          }}
          onPublish={() => handlePublish(selectedPost)}
        />
      )}
    </div>
  );
}

// ── Schedule Modal ────────────────────────────────────────────────────────────
function ScheduleModal({
  post, assets, brandId, onClose, onScheduled,
}: {
  post: Post;
  assets: DesignAsset[];
  brandId: string;
  onClose: () => void;
  onScheduled: (msg: string) => void;
}) {
  const asset = assets.find((a) => a.contentType === post.contentType || a.topic === post.topic);
  const caption = (post.caption ?? post.topic) +
    (post.hashtags?.length ? "\n\n" + post.hashtags.map((h) => `#${h}`).join(" ") : "");

  // Default to post.date at 9am
  const defaultDate = new Date(post.date);
  defaultDate.setHours(9, 0, 0, 0);
  const toLocalInput = (d: Date) => {
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  const [scheduledAt, setScheduledAt] = useState(toLocalInput(defaultDate));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSchedule() {
    setError("");
    const date = new Date(scheduledAt);
    if (date <= new Date()) { setError("Please pick a future date and time"); return; }
    setLoading(true);
    try {
      const imageUrl = asset?.imageUrl ??
        `https://placehold.co/1080x1080/6C3CE1/FFFFFF?text=${encodeURIComponent(post.contentType)}`;
      const res = await instagramAPI.schedule({ postId: post.id, brandId, imageUrl, caption, scheduledAt: date.toISOString() });
      onScheduled(res.data.message ?? `Post scheduled for ${date.toLocaleString()}`);
    } catch (e: unknown) {
      setError((e as { response?: { data?: { message?: string } } })?.response?.data?.message ?? "Scheduling failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <GlassCard variant="raised" className="w-full max-w-md" animate>
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <CalendarClock className="w-4 h-4 text-yellow-400" />
            <h2 className="font-semibold text-white text-sm">Schedule Post</h2>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/[0.08] text-white/40 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div className="flex items-start gap-3 p-3 rounded-xl bg-dark-base/40 border border-white/[0.06]">
            {asset?.imageUrl
              ? <img src={asset.imageUrl} className="w-12 h-12 rounded-lg object-cover flex-shrink-0" alt="" />
              : <div className="w-12 h-12 rounded-lg bg-brand/10 flex items-center justify-center flex-shrink-0"><ImageIcon className="w-5 h-5 text-brand-light/40" /></div>
            }
            <div className="min-w-0">
              <p className="text-sm font-medium text-white truncate">{post.topic}</p>
              <p className="text-xs text-white/40 truncate mt-0.5">{post.contentType}</p>
            </div>
          </div>

          <div>
            <label className="text-xs text-white/50 font-medium mb-1.5 block">Schedule Date & Time</label>
            <input
              type="datetime-local"
              className="input-glass w-full"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              min={toLocalInput(new Date(Date.now() + 60000))}
            />
            <p className="text-xs text-white/30 mt-1">
              Post will auto-publish via BullMQ at this time
            </p>
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <div className="flex gap-3">
            <button onClick={onClose} className="btn-ghost flex-1">Cancel</button>
            <button onClick={handleSchedule} disabled={loading}
              className="btn-primary flex-1 flex items-center justify-center gap-2 disabled:opacity-50">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CalendarClock className="w-4 h-4" />}
              Schedule
            </button>
          </div>
        </div>
      </GlassCard>
    </div>
  );
}

// ── Post Detail Modal ──────────────────────────────────────────────────────────
function PostDetailModal({
  post, assets, igConnected, publishingId,
  onClose, onStatusChange, onPublish,
}: {
  post: Post;
  assets: DesignAsset[];
  igConnected: boolean;
  publishingId: string | null;
  onClose: () => void;
  onStatusChange: (status: string) => void;
  onPublish: () => void;
}) {
  const asset = assets.find((a) => a.contentType === post.contentType || a.topic === post.topic);
  const st = STATUS_CONFIG[post.status as keyof typeof STATUS_CONFIG] ?? STATUS_CONFIG.draft;
  const brief = post.briefJson ?? {};
  const captionShort = brief.caption_short ?? post.caption ?? post.topic;
  const captionLong  = brief.caption_long  ?? post.caption ?? post.topic;
  const hooks        = (brief.hook_variations && brief.hook_variations.length > 0)
                        ? brief.hook_variations
                        : (brief.hook ? [brief.hook] : []);
  const cta          = brief.cta ?? "";
  const seoKeywords  = brief.seo_keywords ?? [];
  const audio        = brief.audio_suggestion ?? null;
  const carouselSlides = brief.carousel_slides ?? null;
  const storySequence  = brief.story_sequence ?? null;
  const graphicLayout  = brief.graphic_layout ?? null;
  const reelScript     = brief.reel_script ?? null;
  const postingTime    = brief.posting_time ?? "";
  const visualBrief    = brief.visual_brief ?? "";
  const emotionalTrigger = brief.emotional_trigger ?? "";

  const fullCaption = captionLong + (post.hashtags?.length ? "\n\n" + post.hashtags.map((h) => `#${h}`).join(" ") : "");
  const isPublishing = publishingId === post.id;

  const [activeCaptionTab, setActiveCaptionTab] = useState<"short" | "long">("long");
  const [copied, setCopied] = useState(false);
  function copyCaption() {
    navigator.clipboard.writeText(fullCaption);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <GlassCard variant="raised" className="w-full max-w-2xl max-h-[90vh] overflow-y-auto" animate>
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-white/[0.06]">
          <div>
            <h2 className="font-semibold text-white">{post.topic}</h2>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-white/40">
                {new Date(post.date).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                style={{
                  backgroundColor: `${CONTENT_TYPE_COLORS[post.contentType] ?? "#6C3CE1"}22`,
                  color: CONTENT_TYPE_COLORS[post.contentType] ?? "#A78BFA",
                }}>
                {post.contentType}
              </span>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${st.bg} ${st.color}`}>
                {st.label}
              </span>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/[0.08] text-white/40 hover:text-white transition-all">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {/* Image */}
          {asset?.imageUrl && (
            <div className="aspect-square w-full max-w-sm mx-auto rounded-2xl overflow-hidden border border-white/[0.08]">
              <img src={asset.imageUrl} alt={post.topic} className="w-full h-full object-cover" />
            </div>
          )}
          {!asset?.imageUrl && (
            <div className="aspect-square w-full max-w-sm mx-auto rounded-2xl bg-gradient-to-br from-brand/20 to-purple-800/20 border border-brand/20 flex items-center justify-center">
              <div className="text-center">
                <ImageIcon className="w-12 h-12 text-brand-light/30 mx-auto mb-2" />
                <p className="text-xs text-white/30">No image generated</p>
              </div>
            </div>
          )}

          {/* Posting Time + Emotional Trigger meta row */}
          {(postingTime || emotionalTrigger) && (
            <div className="flex items-center gap-2 flex-wrap">
              {postingTime && (
                <span className="flex items-center gap-1 text-[11px] px-2 py-1 rounded-full bg-yellow-500/10 text-yellow-300 border border-yellow-500/20">
                  <Clock className="w-3 h-3" /> Best time: {postingTime}
                </span>
              )}
              {emotionalTrigger && (
                <span className="text-[11px] px-2 py-1 rounded-full bg-pink-500/10 text-pink-300 border border-pink-500/20">
                  ⚡ {emotionalTrigger}
                </span>
              )}
            </div>
          )}

          {/* 3 Hook Variations */}
          {hooks.length > 0 && (
            <div>
              <label className="text-xs text-white/50 font-medium mb-2 block">
                Hook Variations ({hooks.length})
              </label>
              <div className="space-y-2">
                {hooks.map((h, idx) => (
                  <div key={idx}
                    className="p-3 rounded-xl bg-gradient-to-br from-brand/10 to-purple-800/5 border border-brand/20 text-sm text-white/85 leading-relaxed">
                    <span className="text-[10px] uppercase tracking-wide text-brand-light/70 font-semibold mr-2">Hook {idx + 1}</span>
                    {h}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Caption — Short / Long tabs */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <label className="text-xs text-white/50 font-medium">Caption</label>
                <div className="flex gap-1 ml-2">
                  <button
                    onClick={() => setActiveCaptionTab("short")}
                    className={`text-[10px] px-2 py-0.5 rounded-full font-medium transition-all ${
                      activeCaptionTab === "short"
                        ? "bg-brand/25 text-brand-light border border-brand/40"
                        : "bg-white/[0.04] text-white/40 border border-white/[0.08] hover:text-white/70"
                    }`}>
                    Short
                  </button>
                  <button
                    onClick={() => setActiveCaptionTab("long")}
                    className={`text-[10px] px-2 py-0.5 rounded-full font-medium transition-all ${
                      activeCaptionTab === "long"
                        ? "bg-brand/25 text-brand-light border border-brand/40"
                        : "bg-white/[0.04] text-white/40 border border-white/[0.08] hover:text-white/70"
                    }`}>
                    Long
                  </button>
                </div>
              </div>
              <button onClick={copyCaption}
                className="flex items-center gap-1 text-xs text-white/40 hover:text-brand-light transition-colors">
                <Copy className="w-3 h-3" />
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
            <div className="p-3 rounded-xl bg-dark-base/60 border border-white/[0.06] text-sm text-white/80 whitespace-pre-wrap leading-relaxed">
              {activeCaptionTab === "short" ? captionShort : captionLong}
            </div>
          </div>

          {/* CTA */}
          {cta && (
            <div>
              <label className="text-xs text-white/50 font-medium mb-2 block">Call to Action</label>
              <div className="p-3 rounded-xl bg-gradient-to-r from-pink-500/15 to-purple-600/15 border border-pink-500/25 text-sm text-pink-100 font-medium">
                {cta}
              </div>
            </div>
          )}

          {/* Carousel Slide Breakdown */}
          {carouselSlides && carouselSlides.length > 0 && (
            <div>
              <label className="text-xs text-white/50 font-medium mb-2 block">
                Carousel Breakdown ({carouselSlides.length} slides)
              </label>
              <div className="space-y-2">
                {carouselSlides.map((s) => (
                  <div key={s.slide_number}
                    className="p-3 rounded-xl bg-emerald-500/[0.06] border border-emerald-500/20">
                    <div className="flex items-start gap-2">
                      <span className="flex-shrink-0 inline-flex items-center justify-center w-6 h-6 rounded-full bg-emerald-500/25 text-emerald-300 text-[11px] font-bold">
                        {s.slide_number}
                      </span>
                      <div className="flex-1 min-w-0 space-y-1">
                        {s.headline && <p className="text-sm font-semibold text-white/90">{s.headline}</p>}
                        {s.body && <p className="text-xs text-white/70 leading-relaxed">{s.body}</p>}
                        {s.on_slide_text && <p className="text-[11px] text-emerald-300/80 italic">On-slide text: "{s.on_slide_text}"</p>}
                        {s.visual_note && <p className="text-[11px] text-white/40">Visual: {s.visual_note}</p>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Graphic / Static Layout */}
          {graphicLayout && (graphicLayout.headline || graphicLayout.body_text) && (
            <div>
              <label className="text-xs text-white/50 font-medium mb-2 block">
                Static Graphic Layout
              </label>
              <div className="p-4 rounded-xl bg-gradient-to-br from-purple-500/10 to-violet-700/5 border border-purple-500/25 space-y-3">
                {graphicLayout.headline && (
                  <div>
                    <p className="text-[10px] uppercase tracking-wide text-purple-300/70 font-semibold mb-1">Headline</p>
                    <p className="text-base font-bold text-white leading-tight">{graphicLayout.headline}</p>
                  </div>
                )}
                {graphicLayout.subheadline && (
                  <div>
                    <p className="text-[10px] uppercase tracking-wide text-purple-300/70 font-semibold mb-1">Subheadline</p>
                    <p className="text-sm text-white/85">{graphicLayout.subheadline}</p>
                  </div>
                )}
                {graphicLayout.body_text && (
                  <div>
                    <p className="text-[10px] uppercase tracking-wide text-purple-300/70 font-semibold mb-1">Body</p>
                    <p className="text-xs text-white/70 leading-relaxed">{graphicLayout.body_text}</p>
                  </div>
                )}
                {graphicLayout.supporting_elements && graphicLayout.supporting_elements.length > 0 && (
                  <div>
                    <p className="text-[10px] uppercase tracking-wide text-purple-300/70 font-semibold mb-1">Supporting Elements</p>
                    <ul className="text-xs text-white/70 space-y-1">
                      {graphicLayout.supporting_elements.map((el, idx) => (
                        <li key={idx} className="flex gap-2"><span className="text-purple-300/60">•</span>{el}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {graphicLayout.footer_text && (
                  <div className="pt-2 border-t border-purple-500/20">
                    <p className="text-[10px] uppercase tracking-wide text-purple-300/70 font-semibold mb-1">Footer / CTA</p>
                    <p className="text-xs text-purple-200 italic">{graphicLayout.footer_text}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Story Sequence */}
          {storySequence && storySequence.length > 0 && (
            <div>
              <label className="text-xs text-white/50 font-medium mb-2 block">
                Story Sequence ({storySequence.length} frames)
              </label>
              <div className="space-y-2">
                {storySequence.map((f) => (
                  <div key={f.frame_number}
                    className="p-3 rounded-xl bg-orange-500/[0.06] border border-orange-500/20">
                    <div className="flex items-start gap-2">
                      <span className="flex-shrink-0 inline-flex items-center justify-center w-6 h-6 rounded-full bg-orange-500/25 text-orange-300 text-[11px] font-bold">
                        {f.frame_number}
                      </span>
                      <div className="flex-1 min-w-0 space-y-1">
                        {f.type && (
                          <span className="text-[10px] uppercase tracking-wide font-semibold text-orange-300/80">
                            {f.type}
                          </span>
                        )}
                        {f.text && <p className="text-sm text-white/85 leading-relaxed">{f.text}</p>}
                        {f.sticker && <p className="text-[11px] text-white/40">Sticker: {f.sticker}</p>}
                        {f.cta && <p className="text-[11px] text-orange-200 italic">CTA: {f.cta}</p>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Audio Suggestion (Reel only) */}
          {audio && (audio.track_name || audio.vibe) && (
            <div>
              <label className="text-xs text-white/50 font-medium mb-2 block">Audio / Music</label>
              <div className="p-3 rounded-xl bg-blue-500/[0.06] border border-blue-500/20 space-y-1">
                {audio.track_name && <p className="text-sm font-semibold text-blue-200">🎵 {audio.track_name}</p>}
                {audio.vibe && <p className="text-xs text-white/70">Vibe: {audio.vibe}</p>}
                {audio.why_it_works && <p className="text-[11px] text-white/50 italic">{audio.why_it_works}</p>}
              </div>
            </div>
          )}

          {/* Reel Script */}
          {reelScript && reelScript.shots && reelScript.shots.length > 0 && (
            <div>
              <label className="text-xs text-white/50 font-medium mb-2 block">
                Reel Script {reelScript.duration_seconds ? `(${reelScript.duration_seconds}s)` : ""}
              </label>
              <div className="space-y-2">
                {reelScript.shots.map((shot, idx) => (
                  <div key={idx} className="p-3 rounded-xl bg-blue-500/[0.05] border border-blue-500/15">
                    <div className="flex items-start gap-2">
                      <span className="text-[10px] font-mono font-bold text-blue-300 bg-blue-500/20 px-1.5 py-0.5 rounded">
                        {shot.time_range ?? `Shot ${idx + 1}`}
                      </span>
                      <div className="flex-1 space-y-1">
                        {shot.visual && <p className="text-xs text-white/80">📹 {shot.visual}</p>}
                        {shot.on_screen_text && <p className="text-[11px] text-blue-200 italic">OST: {shot.on_screen_text}</p>}
                        {shot.voiceover && <p className="text-[11px] text-white/50">🎙 {shot.voiceover}</p>}
                      </div>
                    </div>
                  </div>
                ))}
                {reelScript.cta_overlay && (
                  <p className="text-[11px] text-pink-300/80 italic px-1">Final CTA overlay: {reelScript.cta_overlay}</p>
                )}
              </div>
            </div>
          )}

          {/* SEO Keywords */}
          {seoKeywords.length > 0 && (
            <div>
              <label className="text-xs text-white/50 font-medium mb-2 block">SEO Keywords</label>
              <div className="flex flex-wrap gap-1.5">
                {seoKeywords.map((kw, idx) => (
                  <span key={idx}
                    className="text-[11px] px-2 py-0.5 rounded-md bg-white/[0.05] text-white/60 border border-white/[0.08]">
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Visual Brief */}
          {visualBrief && (
            <div>
              <label className="text-xs text-white/50 font-medium mb-1 block">Visual Brief</label>
              <p className="text-xs text-white/55 italic leading-relaxed">{visualBrief}</p>
            </div>
          )}

          {/* Hashtags */}
          {post.hashtags && post.hashtags.length > 0 && (
            <div>
              <label className="text-xs text-white/50 font-medium flex items-center gap-1 mb-2">
                <Hash className="w-3 h-3" /> Hashtags ({post.hashtags.length})
              </label>
              <div className="flex flex-wrap gap-1.5">
                {post.hashtags.map((tag) => (
                  <span key={tag}
                    className="text-xs px-2 py-0.5 rounded-full bg-brand/10 text-brand-light border border-brand/20">
                    #{tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="pt-2 flex items-center gap-3 flex-wrap">
            {post.status === "draft" && (
              <button
                onClick={() => onStatusChange("approved")}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-green-500/15 border border-green-500/25 text-green-400 text-sm font-medium hover:bg-green-500/25 transition-all">
                <CheckCircle2 className="w-4 h-4" /> Approve
              </button>
            )}
            {post.status === "approved" && igConnected && (
              <button
                onClick={onPublish}
                disabled={isPublishing}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-purple-600/30 to-pink-600/30 border border-purple-500/30 text-pink-300 text-sm font-medium hover:border-purple-400/60 transition-all disabled:opacity-50">
                {isPublishing
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <><Instagram className="w-4 h-4" /> Publish to Instagram</>}
              </button>
            )}
            {post.status === "approved" && !igConnected && (
              <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 text-sm">
                <AlertCircle className="w-4 h-4" /> Connect Instagram to publish
              </div>
            )}
            {(post.status === "draft" || post.status === "approved") && (
              <button
                onClick={() => onStatusChange("rejected")}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-medium hover:bg-red-500/20 transition-all">
                <XCircle className="w-4 h-4" /> Reject
              </button>
            )}
            {post.status === "rejected" && (
              <button
                onClick={() => onStatusChange("draft")}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/[0.06] border border-white/[0.10] text-white/70 text-sm font-medium hover:bg-white/[0.10] transition-all">
                Restore to Draft
              </button>
            )}
            {post.status === "published" && (
              <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-brand/10 border border-brand/20 text-brand-light text-sm">
                <CheckCircle2 className="w-4 h-4" /> Published on Instagram
              </div>
            )}
          </div>
        </div>
      </GlassCard>
    </div>
  );
}
