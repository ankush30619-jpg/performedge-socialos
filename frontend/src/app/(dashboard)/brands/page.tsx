"use client";
import { useState, useRef, useEffect, Suspense } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { brandAPI, api } from "@/lib/api";
import { uploadFile } from "@/lib/supabase";
import { useAppStore } from "@/store/useAppStore";
import { GlassCard } from "@/components/ui/GlassCard";
import { getInitials } from "@/lib/utils";
import {
  Plus, RefreshCw, Trash2, Edit2, MoreVertical, ChevronRight,
  Globe, Users, Mic2, Palette, Instagram, Brain,
  FileText, CheckCircle2, ArrowLeft, ArrowRight, X, Loader2,
  Image as ImageIcon, Link2, Link2Off, AlertCircle, Clock,
  Zap, BookOpen, TrendingUp, Hash, Target, Sparkles, BarChart2,
  Trophy, Swords, Upload, Video, MessageSquare, Eye, Shield, ExternalLink,
} from "lucide-react";
import type { Brand, BrandMediaItem, BrandCompetitor, AudiencePersona } from "@/types";

const BUCKET = "socialos-storage";

const TONES = ["Professional", "Casual", "Inspirational", "Witty", "Bold", "Friendly", "Authoritative", "Playful", "Educational", "Motivational"];
const VOICE_STYLES = ["tum (informal Hindi)", "aap (formal Hindi)", "you (English)", "yaar (casual)", "sir/ma'am (formal)"];
const AUDIENCE_LEVELS = ["Beginners", "Intermediate", "Advanced", "All levels"];
const VIDEO_LENGTHS = ["15s", "30s", "45s", "60s", "90s", "2-3 min", "5+ min"];
const CONTENT_PILLAR_SUGGESTIONS = [
  "Educational", "Motivational", "Behind the Scenes", "Product Showcase",
  "Client Results", "Industry News", "Tips & Tricks", "Q&A", "Trends",
  "Personal Story", "Case Study", "Tutorial",
];

const STEPS = [
  { id: 1, label: "Core Identity",    icon: Globe },
  { id: 2, label: "Brand Story",      icon: BookOpen },
  { id: 3, label: "Brand Identity",   icon: Palette },
  { id: 4, label: "Target Audience",  icon: Target },
  { id: 5, label: "Voice & Style",    icon: Mic2 },
  { id: 6, label: "Content Strategy", icon: BarChart2 },
  { id: 7, label: "Competitors",      icon: Swords },
  { id: 8, label: "Instagram & AI",   icon: Brain },
];

// ─── Form State ───────────────────────────────────────────────────────────────
type FormState = {
  // Step 1
  name: string;
  niche: string;
  industry: string;
  language: string;
  website: string;
  instagramUrl: string;
  positioning: string;
  // Step 2
  differentiation: string;
  brandStory: string;
  credentials: string;
  // Step 3
  logoUrl: string;
  guidelinesUrl: string;
  primaryColor: string;
  secondaryColor: string;
  accentColor: string;
  palette: string[];
  // Step 4
  targetAudience: string;
  audienceAge: string;
  audienceProfession: string;
  audiencePainPoints: string;
  audienceLevel: string;
  audienceLanguage: string;
  audienceAspirations: string;
  audiencePersona: AudiencePersona[];
  // Step 5
  tone: string;
  voiceStyle: string;
  catchphrases: string;
  forbiddenWords: string;
  usesSlang: boolean;
  hookStyle: string;
  ctaStyle: string;
  // Step 6
  contentPillars: string[];
  idealVideoLength: string;
  hookFormulas: string;
  bestHooks: string;
  worstContent: string;
  // Step 7
  competitors: BrandCompetitor[];
  campaignUrls: BrandMediaItem[];
  brandMediaUrls: BrandMediaItem[];
  // Step 8
  igAccountId: string;
  igAccessToken: string;
  knowledgeText: string;
};

const emptyForm = (): FormState => ({
  name: "", niche: "", industry: "", language: "", website: "",
  instagramUrl: "", positioning: "",
  differentiation: "", brandStory: "", credentials: "",
  logoUrl: "", guidelinesUrl: "",
  primaryColor: "#6C3CE1", secondaryColor: "#A78BFA", accentColor: "#EC4899", palette: [],
  targetAudience: "", audienceAge: "", audienceProfession: "", audiencePainPoints: "",
  audienceLevel: "", audienceLanguage: "", audienceAspirations: "", audiencePersona: [],
  tone: "", voiceStyle: "", catchphrases: "", forbiddenWords: "", usesSlang: false,
  hookStyle: "", ctaStyle: "",
  contentPillars: [], idealVideoLength: "", hookFormulas: "", bestHooks: "", worstContent: "",
  competitors: [], campaignUrls: [], brandMediaUrls: [],
  igAccountId: "", igAccessToken: "", knowledgeText: "",
});

function brandToForm(brand: Brand): FormState {
  const kj = brand.knowledgeJson as Record<string, unknown> | null | undefined;
  const colors = brand.colors as { primary?: string; secondary?: string; accent?: string; palette?: string[] } | undefined;
  return {
    name: brand.name ?? "",
    niche: brand.niche ?? "",
    industry: brand.industry ?? "",
    language: brand.language ?? "",
    website: brand.website ?? "",
    instagramUrl: brand.instagramUrl ?? "",
    positioning: brand.positioning ?? "",
    differentiation: brand.differentiation ?? "",
    brandStory: brand.brandStory ?? "",
    credentials: brand.credentials ?? "",
    logoUrl: brand.logoUrl ?? "",
    guidelinesUrl: brand.guidelinesUrl ?? "",
    primaryColor: colors?.primary ?? "#6C3CE1",
    secondaryColor: colors?.secondary ?? "#A78BFA",
    accentColor: colors?.accent ?? "#EC4899",
    palette: colors?.palette ?? [],
    targetAudience: brand.targetAudience ?? "",
    audienceAge: brand.audienceAge ?? "",
    audienceProfession: brand.audienceProfession ?? "",
    audiencePainPoints: brand.audiencePainPoints ?? "",
    audienceLevel: brand.audienceLevel ?? "",
    audienceLanguage: brand.audienceLanguage ?? "",
    audienceAspirations: brand.audienceAspirations ?? "",
    audiencePersona: (brand.audiencePersona as AudiencePersona[] | null) ?? [],
    tone: brand.tone ?? "",
    voiceStyle: brand.voiceStyle ?? "",
    catchphrases: brand.catchphrases ?? "",
    forbiddenWords: brand.forbiddenWords ?? "",
    usesSlang: brand.usesSlang ?? false,
    hookStyle: brand.hookStyle ?? "",
    ctaStyle: brand.ctaStyle ?? "",
    contentPillars: brand.contentPillars ?? [],
    idealVideoLength: brand.idealVideoLength ?? "",
    hookFormulas: brand.hookFormulas ?? "",
    bestHooks: brand.bestHooks ?? "",
    worstContent: brand.worstContent ?? "",
    competitors: (brand.competitors as BrandCompetitor[] | null) ?? [],
    campaignUrls: (brand.campaignUrls as BrandMediaItem[] | null) ?? [],
    brandMediaUrls: (brand.brandMediaUrls as BrandMediaItem[] | null) ?? [],
    igAccountId: brand.igAccountId ?? "",
    igAccessToken: brand.igAccessToken ?? "",
    knowledgeText: typeof kj?.description === "string" ? kj.description : "",
  };
}

function formToPayload(form: FormState) {
  return {
    name: form.name,
    niche: form.niche || undefined,
    industry: form.industry || undefined,
    language: form.language || undefined,
    website: form.website || undefined,
    instagramUrl: form.instagramUrl || undefined,
    positioning: form.positioning || undefined,
    differentiation: form.differentiation || undefined,
    brandStory: form.brandStory || undefined,
    credentials: form.credentials || undefined,
    logoUrl: form.logoUrl || undefined,
    guidelinesUrl: form.guidelinesUrl || undefined,
    colors: {
      primary: form.primaryColor,
      secondary: form.secondaryColor || undefined,
      accent: form.accentColor || undefined,
      palette: form.palette.length > 0 ? form.palette : undefined,
    },
    targetAudience: form.targetAudience || undefined,
    audienceAge: form.audienceAge || undefined,
    audienceProfession: form.audienceProfession || undefined,
    audiencePainPoints: form.audiencePainPoints || undefined,
    audienceLevel: form.audienceLevel || undefined,
    audienceLanguage: form.audienceLanguage || undefined,
    audienceAspirations: form.audienceAspirations || undefined,
    audiencePersona: form.audiencePersona.length > 0 ? form.audiencePersona : undefined,
    tone: form.tone || undefined,
    voiceStyle: form.voiceStyle || undefined,
    catchphrases: form.catchphrases || undefined,
    forbiddenWords: form.forbiddenWords || undefined,
    usesSlang: form.usesSlang,
    hookStyle: form.hookStyle || undefined,
    ctaStyle: form.ctaStyle || undefined,
    contentPillars: form.contentPillars.length > 0 ? form.contentPillars : undefined,
    idealVideoLength: form.idealVideoLength || undefined,
    hookFormulas: form.hookFormulas || undefined,
    bestHooks: form.bestHooks || undefined,
    worstContent: form.worstContent || undefined,
    competitors: form.competitors.length > 0 ? form.competitors : undefined,
    campaignUrls: form.campaignUrls.length > 0 ? form.campaignUrls : undefined,
    brandMediaUrls: form.brandMediaUrls.length > 0 ? form.brandMediaUrls : undefined,
    igAccountId: form.igAccountId || undefined,
    igAccessToken: form.igAccessToken || undefined,
    knowledgeJson: form.knowledgeText ? { description: form.knowledgeText } : undefined,
  };
}

// ─── OAuth callback reader (needs Suspense) ───────────────────────────────────
function OAuthCallbackHandler({
  onToast,
}: { onToast: (t: { type: "success" | "error"; msg: string }) => void }) {
  const queryClient  = useQueryClient();
  const searchParams = useSearchParams();

  const success = searchParams.get("meta_success");
  const igUser  = searchParams.get("ig_user");
  const error   = searchParams.get("meta_error");

  if (success) {
    onToast({ type: "success", msg: `Instagram @${igUser ?? "account"} connected successfully!` });
    queryClient.invalidateQueries({ queryKey: ["brands"] });
    window.history.replaceState({}, "", "/brands");
  } else if (error) {
    onToast({ type: "error", msg: decodeURIComponent(error) });
    window.history.replaceState({}, "", "/brands");
  }

  return null;
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function BrandsPage() {
  const queryClient = useQueryClient();
  const { setActiveBrand, activeBrandId, setBrands } = useAppStore();
  const [showCreate, setShowCreate] = useState(false);
  const [metaToast, setMetaToast] = useState<{ type: "success" | "error"; msg: string } | null>(null);
  const [editBrand, setEditBrand] = useState<Brand | null>(null);
  const [menuBrandId, setMenuBrandId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["brands"],
    queryFn: () => brandAPI.list().then((r) => r.data),
  });
  const brands: Brand[] = data?.brands ?? [];

  // Sync brands to global store — must be in useEffect, NOT in select (causes infinite loop)
  useEffect(() => {
    if (data?.brands) setBrands(data.brands);
  }, [data?.brands, setBrands]);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => brandAPI.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["brands"] }),
  });

  const relearnMutation = useMutation({
    mutationFn: (id: string) => brandAPI.relearn(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ["learning-logs", id] });
    },
  });

  const activeBrand = brands.find((b) => b.id === activeBrandId) ?? null;
  const { data: logsData, isLoading: logsLoading } = useQuery({
    queryKey: ["learning-logs", activeBrandId],
    queryFn: () => brandAPI.learningLogs(activeBrandId!).then((r) => r.data),
    enabled: !!activeBrandId,
    staleTime: 60_000,
  });
  const learningLogs: Array<{ id: string; trigger: string; summary: string | null; createdAt: string }> =
    logsData?.logs ?? [];
  const lastLog = learningLogs[0] ?? null;

  return (
    <div className="space-y-6">
      <Suspense fallback={null}>
        <OAuthCallbackHandler onToast={setMetaToast} />
      </Suspense>

      {/* Meta OAuth Toast */}
      {metaToast && (
        <div className={`fixed top-5 right-5 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-xl border backdrop-blur-md text-sm font-medium animate-in slide-in-from-right
          ${metaToast.type === "success"
            ? "bg-green-500/20 border-green-500/30 text-green-300"
            : "bg-red-500/20 border-red-500/30 text-red-300"}`}>
          {metaToast.type === "success"
            ? <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            : <AlertCircle className="w-4 h-4 flex-shrink-0" />}
          {metaToast.msg}
          <button onClick={() => setMetaToast(null)} className="ml-2 hover:opacity-70"><X className="w-3.5 h-3.5" /></button>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Brand Hub</h1>
          <p className="text-sm text-white/40 mt-0.5">
            Manage your brands, upload guidelines, connect Instagram
          </p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2 text-sm">
          <Plus className="w-4 h-4" /> New Brand
        </button>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => <div key={i} className="skeleton h-52 rounded-2xl" />)}
        </div>
      ) : brands.length === 0 ? (
        <GlassCard className="p-16 flex flex-col items-center text-center">
          <div className="w-16 h-16 rounded-2xl bg-brand/10 flex items-center justify-center mb-4">
            <Plus className="w-7 h-7 text-brand-light" />
          </div>
          <h2 className="text-lg font-semibold text-white mb-2">No brands yet</h2>
          <p className="text-sm text-white/40 max-w-xs">
            Create your first brand to start running AI agents and generating content
          </p>
          <button onClick={() => setShowCreate(true)} className="btn-primary mt-6">
            Create Brand
          </button>
        </GlassCard>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {brands.map((brand) => (
            <GlassCard
              key={brand.id}
              variant={brand.id === activeBrandId ? "brand" : "default"}
              className="p-5 cursor-pointer group relative"
              onClick={() => { setActiveBrand(brand.id); setMenuBrandId(null); }}
            >
              {/* Brand header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div
                    className="w-11 h-11 rounded-xl flex items-center justify-center text-sm font-bold text-white shadow-brand overflow-hidden flex-shrink-0"
                    style={{ backgroundColor: (brand.colors as { primary?: string })?.primary || "#6C3CE1" }}
                  >
                    {brand.logoUrl ? (
                      <img src={brand.logoUrl} alt={brand.name} className="w-full h-full object-cover" />
                    ) : (
                      getInitials(brand.name)
                    )}
                  </div>
                  <div className="min-w-0">
                    <p className="font-semibold text-white text-sm truncate">{brand.name}</p>
                    <p className="text-xs text-white/40 truncate">{brand.niche ?? brand.industry ?? "Brand"}</p>
                  </div>
                </div>

                {/* More menu */}
                <div className="relative">
                  <button
                    onClick={(e) => { e.stopPropagation(); setMenuBrandId(menuBrandId === brand.id ? null : brand.id); }}
                    className="p-1.5 rounded-lg hover:bg-white/[0.08] transition-all text-white/40 hover:text-white"
                  >
                    <MoreVertical className="w-4 h-4" />
                  </button>
                  {menuBrandId === brand.id && (
                    <div
                      className="absolute right-0 top-8 z-20 w-40 glass rounded-xl border border-white/[0.08] shadow-xl py-1"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        className="w-full flex items-center gap-2 px-3 py-2 text-xs text-white/70 hover:text-white hover:bg-white/[0.06] transition-colors"
                        onClick={() => { setEditBrand(brand); setMenuBrandId(null); }}
                      >
                        <Edit2 className="w-3.5 h-3.5" /> Edit Brand
                      </button>
                      <button
                        className="w-full flex items-center gap-2 px-3 py-2 text-xs text-white/70 hover:text-brand-light hover:bg-white/[0.06] transition-colors"
                        onClick={() => { relearnMutation.mutate(brand.id); setMenuBrandId(null); }}
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${relearnMutation.isPending ? "animate-spin" : ""}`} />
                        Re-learn AI
                      </button>
                      <div className="my-1 border-t border-white/[0.06]" />
                      <button
                        className="w-full flex items-center gap-2 px-3 py-2 text-xs text-red-400 hover:bg-red-500/10 transition-colors"
                        onClick={() => { if (confirm(`Delete "${brand.name}"?`)) { deleteMutation.mutate(brand.id); setMenuBrandId(null); } }}
                      >
                        <Trash2 className="w-3.5 h-3.5" /> Delete
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Details */}
              <div className="space-y-1.5 mb-4">
                {brand.positioning && (
                  <p className="text-xs text-white/50 italic line-clamp-2">&ldquo;{brand.positioning}&rdquo;</p>
                )}
                {brand.website && (
                  <p className="text-xs text-white/40 flex items-center gap-1.5 truncate">
                    <Globe className="w-3 h-3 flex-shrink-0" /> {brand.website}
                  </p>
                )}
                {brand.targetAudience && (
                  <p className="text-xs text-white/40 flex items-center gap-1.5 truncate">
                    <Users className="w-3 h-3 flex-shrink-0" /> {brand.targetAudience}
                  </p>
                )}
                {brand.tone && (
                  <p className="text-xs text-white/40 flex items-center gap-1.5">
                    <Mic2 className="w-3 h-3 flex-shrink-0" /> {brand.tone}
                  </p>
                )}
                {brand.igUsername ? (
                  <p className="text-xs text-green-400/70 flex items-center gap-1.5">
                    <Instagram className="w-3 h-3 flex-shrink-0" /> @{brand.igUsername}
                  </p>
                ) : brand.igAccountId ? (
                  <p className="text-xs text-green-400/70 flex items-center gap-1.5">
                    <Instagram className="w-3 h-3 flex-shrink-0" /> Instagram Connected
                  </p>
                ) : null}
                {brand.guidelinesUrl && (
                  <p className="text-xs text-blue-400/70 flex items-center gap-1.5">
                    <FileText className="w-3 h-3 flex-shrink-0" /> Guidelines Uploaded
                  </p>
                )}
                {/* Content pillars */}
                {brand.contentPillars && Array.isArray(brand.contentPillars) && brand.contentPillars.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-0.5">
                    {(brand.contentPillars as string[]).slice(0, 3).map((p: string) => (
                      <span key={p} className="text-[10px] px-1.5 py-0.5 rounded-full bg-brand/10 text-brand-light border border-brand/20">{p}</span>
                    ))}
                    {brand.contentPillars.length > 3 && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/[0.06] text-white/30">+{brand.contentPillars.length - 3}</span>
                    )}
                  </div>
                )}
              </div>

              {/* Color swatches */}
              <div className="flex items-center gap-2 pt-3 border-t border-white/[0.06]">
                <div className="flex gap-1">
                  <div className="w-4 h-4 rounded-full border border-white/20" style={{ backgroundColor: (brand.colors as { primary?: string })?.primary || "#6C3CE1" }} title="Primary" />
                  {(brand.colors as { secondary?: string })?.secondary && (
                    <div className="w-4 h-4 rounded-full border border-white/20" style={{ backgroundColor: (brand.colors as { secondary?: string }).secondary }} title="Secondary" />
                  )}
                  {(brand.colors as { accent?: string })?.accent && (
                    <div className="w-4 h-4 rounded-full border border-white/20" style={{ backgroundColor: (brand.colors as { accent?: string }).accent }} title="Accent" />
                  )}
                  {((brand.colors as { palette?: string[] })?.palette ?? []).slice(0, 3).map((c: string, i: number) => (
                    <div key={i} className="w-4 h-4 rounded-full border border-white/20" style={{ backgroundColor: c }} />
                  ))}
                </div>
                {brand.competitors && Array.isArray(brand.competitors) && brand.competitors.length > 0 && (
                  <span className="text-[10px] text-white/25 flex items-center gap-1 ml-1">
                    <Swords className="w-2.5 h-2.5" /> {brand.competitors.length} competitors
                  </span>
                )}
                <ChevronRight className="w-3.5 h-3.5 text-white/20 group-hover:text-brand-light transition-colors ml-auto" />
              </div>

              {brand.id === activeBrandId && (
                <div className="absolute top-3 left-3">
                  <span className="text-[10px] bg-brand/20 text-brand-light border border-brand/30 rounded-full px-2 py-0.5 font-medium">
                    Active
                  </span>
                </div>
              )}
            </GlassCard>
          ))}

          {/* Add card */}
          <button
            onClick={() => setShowCreate(true)}
            className="glass rounded-2xl p-5 flex flex-col items-center justify-center gap-3 border-2 border-dashed border-white/[0.08] hover:border-brand/40 hover:bg-brand/5 transition-all min-h-[200px]"
          >
            <div className="w-10 h-10 rounded-xl bg-brand/10 flex items-center justify-center">
              <Plus className="w-5 h-5 text-brand-light" />
            </div>
            <p className="text-sm text-white/40">Add New Brand</p>
          </button>
        </div>
      )}

      {/* ── AI Self-Learning Panel ── */}
      {activeBrand && (
        <GlassCard className="p-6">
          <div className="flex items-start justify-between mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-brand/10 flex items-center justify-center flex-shrink-0">
                <Brain className="w-5 h-5 text-brand-light" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-white">AI Self-Learning — {activeBrand.name}</h2>
                <p className="text-xs text-white/40 mt-0.5">
                  {lastLog
                    ? `Last re-learned ${new Date(lastLog.createdAt).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}`
                    : "Never re-learned — run to build brand intelligence"}
                </p>
              </div>
            </div>
            <button
              onClick={() => relearnMutation.mutate(activeBrand.id)}
              disabled={relearnMutation.isPending}
              className="btn-primary flex items-center gap-2 text-sm disabled:opacity-50"
            >
              {relearnMutation.isPending
                ? <><Loader2 className="w-4 h-4 animate-spin" /> Running…</>
                : <><RefreshCw className="w-4 h-4" /> Re-learn AI</>}
            </button>
          </div>

          <div className="grid grid-cols-3 gap-3 mb-5">
            {[
              { icon: TrendingUp, label: "Live Analytics",  desc: "Fetches real IG followers, reach & engagement" },
              { icon: BookOpen,   label: "Niche Research",  desc: "Finds latest trends & industry news via Tavily" },
              { icon: Hash,       label: "Hashtag Intel",   desc: "Refreshes high-impact hashtag recommendations" },
            ].map(({ icon: Icon, label, desc }) => (
              <div key={label} className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-1">
                <div className="flex items-center gap-1.5">
                  <Icon className="w-3.5 h-3.5 text-brand-light" />
                  <span className="text-xs font-medium text-white/70">{label}</span>
                </div>
                <p className="text-[11px] text-white/30 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>

          <div>
            <p className="text-xs font-medium text-white/40 mb-2.5">Learning History</p>
            {logsLoading ? (
              <div className="space-y-2">{[1, 2].map(i => <div key={i} className="skeleton h-10 rounded-xl" />)}</div>
            ) : learningLogs.length === 0 ? (
              <div className="flex items-center gap-3 p-4 rounded-xl border border-dashed border-white/[0.06]">
                <Zap className="w-4 h-4 text-white/20" />
                <p className="text-xs text-white/30">No learning sessions yet. Click "Re-learn AI" to start.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {learningLogs.slice(0, 8).map((log) => (
                  <div key={log.id} className="flex items-start gap-3 p-3 rounded-xl bg-white/[0.03] border border-white/[0.04] hover:border-white/[0.08] transition-colors">
                    <div className={`mt-0.5 w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${log.summary?.startsWith("Failed") ? "bg-red-500/10" : "bg-green-500/10"}`}>
                      {log.summary?.startsWith("Failed")
                        ? <AlertCircle className="w-3 h-3 text-red-400" />
                        : <CheckCircle2 className="w-3 h-3 text-green-400" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-white/60 line-clamp-1">{log.summary ?? "Completed"}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${log.trigger === "manual" ? "bg-brand/10 text-brand-light" : "bg-white/[0.06] text-white/30"}`}>
                          {log.trigger === "cron_15d" ? "Auto (15d)" : "Manual"}
                        </span>
                        <span className="text-[10px] text-white/20 flex items-center gap-1">
                          <Clock className="w-2.5 h-2.5" />
                          {new Date(log.createdAt).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="mt-4 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center gap-2">
            <Clock className="w-3.5 h-3.5 text-white/20 flex-shrink-0" />
            <p className="text-[11px] text-white/25">
              Re-learning also runs automatically every 15 days at 3 AM to keep AI agents up to date.
            </p>
          </div>
        </GlassCard>
      )}

      {/* Modals */}
      {showCreate && (
        <BrandFormModal
          mode="create"
          onClose={() => setShowCreate(false)}
          onSaved={() => { setShowCreate(false); queryClient.invalidateQueries({ queryKey: ["brands"] }); }}
        />
      )}
      {editBrand && (
        <BrandFormModal
          mode="edit"
          brand={editBrand}
          onClose={() => setEditBrand(null)}
          onSaved={() => { setEditBrand(null); queryClient.invalidateQueries({ queryKey: ["brands"] }); }}
        />
      )}
    </div>
  );
}

// ─── Multi-Step Brand Form Modal (8 Steps) ────────────────────────────────────
function BrandFormModal({
  mode, brand, onClose, onSaved,
}: { mode: "create" | "edit"; brand?: Brand; onClose: () => void; onSaved: () => void }) {
  const [step, setStep] = useState(1);
  const [error, setError] = useState("");
  const [logoUploading, setLogoUploading] = useState(false);
  const [guideUploading, setGuideUploading] = useState(false);
  const [mediaUploading, setMediaUploading] = useState(false);
  const [campaignUploading, setCampaignUploading] = useState(false);
  const [newPillar, setNewPillar] = useState("");
  const [newPaletteColor, setNewPaletteColor] = useState("#FFFFFF");
  const logoRef     = useRef<HTMLInputElement>(null);
  const guideRef    = useRef<HTMLInputElement>(null);
  const campaignRef = useRef<HTMLInputElement>(null);
  const mediaRef    = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState<FormState>(() =>
    brand ? brandToForm(brand) : emptyForm()
  );

  const set = (key: keyof FormState) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }));

  const setVal = <K extends keyof FormState>(key: K, val: FormState[K]) =>
    setForm((f) => ({ ...f, [key]: val }));

  // ── File Uploads ──────────────────────────────────────────────────────────
  async function handleLogoUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]; if (!file) return;
    setLogoUploading(true);
    try {
      const url = await uploadFile(BUCKET, `logos/${Date.now()}_${file.name}`, file, file.type);
      setForm(f => ({ ...f, logoUrl: url }));
    } catch { setError("Logo upload failed."); }
    finally { setLogoUploading(false); }
  }

  async function handleGuidelinesUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]; if (!file) return;
    setGuideUploading(true);
    try {
      const url = await uploadFile(BUCKET, `guidelines/${Date.now()}_${file.name}`, file, file.type);
      setForm(f => ({ ...f, guidelinesUrl: url }));
    } catch { setError("Guidelines upload failed."); }
    finally { setGuideUploading(false); }
  }

  async function handleCampaignUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []); if (!files.length) return;
    setCampaignUploading(true);
    try {
      const uploaded: BrandMediaItem[] = await Promise.all(files.map(async (file) => {
        const url = await uploadFile(BUCKET, `campaigns/${Date.now()}_${file.name}`, file, file.type);
        return { name: file.name, url, type: file.type };
      }));
      setForm(f => ({ ...f, campaignUrls: [...f.campaignUrls, ...uploaded] }));
    } catch { setError("Campaign upload failed."); }
    finally { setCampaignUploading(false); }
  }

  async function handleMediaUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []); if (!files.length) return;
    setMediaUploading(true);
    try {
      const uploaded: BrandMediaItem[] = await Promise.all(files.map(async (file) => {
        const url = await uploadFile(BUCKET, `brand-media/${Date.now()}_${file.name}`, file, file.type);
        return { name: file.name, url, type: file.type };
      }));
      setForm(f => ({ ...f, brandMediaUrls: [...f.brandMediaUrls, ...uploaded] }));
    } catch { setError("Media upload failed."); }
    finally { setMediaUploading(false); }
  }

  const mutation = useMutation({
    mutationFn: () => {
      const payload = formToPayload(form);
      return mode === "create" ? brandAPI.create(payload) : brandAPI.update(brand!.id, payload);
    },
    onSuccess: onSaved,
    onError: (e: { response?: { data?: { message?: string } } }) =>
      setError(e.response?.data?.message ?? "Something went wrong"),
  });

  const canNext = step === 1 ? !!form.name.trim() : true;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <GlassCard variant="raised" className="w-full max-w-2xl flex flex-col max-h-[90vh]" animate>

        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-white/[0.06] flex-shrink-0">
          <div>
            <h2 className="text-lg font-semibold text-white">
              {mode === "create" ? "Create Brand" : `Edit — ${brand?.name}`}
            </h2>
            <p className="text-xs text-white/40 mt-0.5">
              Step {step} of {STEPS.length} — {STEPS[step - 1].label}
            </p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/[0.08] text-white/40 hover:text-white transition-all">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Step indicators — scrollable row */}
        <div className="flex items-center gap-1 px-6 py-3 border-b border-white/[0.06] overflow-x-auto flex-shrink-0">
          {STEPS.map((s) => {
            const Icon = s.icon;
            const done   = step > s.id;
            const active = step === s.id;
            return (
              <button
                key={s.id}
                onClick={() => (done || s.id < step) ? setStep(s.id) : undefined}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-all whitespace-nowrap flex-shrink-0
                  ${active ? "bg-brand/20 text-brand-light border border-brand/30"
                    : done   ? "text-green-400/70 hover:bg-white/[0.05] cursor-pointer"
                    : "text-white/25 cursor-default"}`}
              >
                {done ? <CheckCircle2 className="w-3 h-3" /> : <Icon className="w-3 h-3" />}
                {s.label}
              </button>
            );
          })}
        </div>

        {/* Form body — scrollable */}
        <div className="px-6 py-5 space-y-4 overflow-y-auto flex-1">

          {/* ── Step 1: Core Identity ── */}
          {step === 1 && (
            <>
              <SectionHint icon={Globe} title="Core Identity" desc="The essentials — what your brand is and where it plays." />
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="field-label">Brand Name <span className="text-red-400">*</span></label>
                  <input className="input-glass w-full" placeholder="e.g. PerformEdge" value={form.name} onChange={set("name")} autoFocus />
                </div>
                <div>
                  <label className="field-label">Niche</label>
                  <input className="input-glass w-full" placeholder="e.g. AI tools for creators" value={form.niche} onChange={set("niche")} />
                </div>
                <div>
                  <label className="field-label">Industry</label>
                  <input className="input-glass w-full" placeholder="e.g. D2C Fashion, SaaS, Edtech" value={form.industry} onChange={set("industry")} />
                </div>
                <div>
                  <label className="field-label">Primary Language</label>
                  <input className="input-glass w-full" placeholder="e.g. Hinglish, English, Hindi" value={form.language} onChange={set("language")} />
                </div>
                <div>
                  <label className="field-label">Website URL</label>
                  <input className="input-glass w-full" placeholder="https://yourbrand.com" value={form.website} onChange={set("website")} type="url" />
                </div>
                <div>
                  <label className="field-label">Instagram Profile URL</label>
                  <input className="input-glass w-full" placeholder="https://instagram.com/yourbrand" value={form.instagramUrl} onChange={set("instagramUrl")} />
                </div>
                <div className="col-span-2">
                  <label className="field-label">One-line Brand Positioning</label>
                  <input className="input-glass w-full" placeholder="e.g. We help D2C founders scale revenue with AI-powered content" value={form.positioning} onChange={set("positioning")} />
                </div>
              </div>
            </>
          )}

          {/* ── Step 2: Brand Story ── */}
          {step === 2 && (
            <>
              <SectionHint icon={BookOpen} title="Brand Story & Credentials" desc="What makes your brand real, relatable, and credible." />
              <div>
                <label className="field-label">What Makes You Unique (Differentiation)</label>
                <textarea className="input-glass w-full min-h-[80px] resize-none" placeholder="e.g. We are the only agency that combines AI content + performance ads in a single monthly plan. Our proprietary tool reduces content costs by 70%." value={form.differentiation} onChange={set("differentiation")} />
              </div>
              <div>
                <label className="field-label">Brand Story / Origin</label>
                <textarea className="input-glass w-full min-h-[100px] resize-none" placeholder="Share the journey — why you started, struggles, wins, pivots. This makes content authentic and relatable." value={form.brandStory} onChange={set("brandStory")} />
              </div>
              <div>
                <label className="field-label">Credentials & Social Proof</label>
                <textarea className="input-glass w-full min-h-[80px] resize-none" placeholder="e.g. 50K+ followers, ₹5Cr revenue generated for clients, Featured in YourStory, 200+ brands served, 4.9⭐ on G2" value={form.credentials} onChange={set("credentials")} />
              </div>
            </>
          )}

          {/* ── Step 3: Brand Identity ── */}
          {step === 3 && (
            <>
              <SectionHint icon={Palette} title="Brand Identity" desc="Visual assets — logo, guidelines, and your full color palette." />

              {/* Logo */}
              <div>
                <label className="field-label">Brand Logo</label>
                <input ref={logoRef} type="file" accept="image/*" className="hidden" onChange={handleLogoUpload} />
                <div onClick={() => logoRef.current?.click()} className="relative flex items-center gap-4 p-4 rounded-xl border border-dashed border-white/[0.12] hover:border-brand/40 hover:bg-brand/5 cursor-pointer transition-all">
                  {logoUploading ? <Loader2 className="w-8 h-8 text-brand animate-spin" />
                    : form.logoUrl ? <img src={form.logoUrl} alt="Logo" className="w-12 h-12 rounded-xl object-cover border border-white/[0.12]" />
                    : <div className="w-12 h-12 rounded-xl bg-brand/10 flex items-center justify-center"><ImageIcon className="w-5 h-5 text-brand-light" /></div>}
                  <div>
                    <p className="text-sm text-white/70 font-medium">{form.logoUrl ? "Change Logo" : "Upload Logo"}</p>
                    <p className="text-xs text-white/30">PNG, JPG, SVG — max 5MB</p>
                  </div>
                  {form.logoUrl && (
                    <button onClick={(e) => { e.stopPropagation(); setVal("logoUrl", ""); }} className="absolute top-2 right-2 p-1 rounded-full hover:bg-red-500/20 text-white/30 hover:text-red-400">
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>

              {/* Guidelines */}
              <div>
                <label className="field-label">Brand Guidelines</label>
                <input ref={guideRef} type="file" accept=".pdf,.doc,.docx,.ppt,.pptx" className="hidden" onChange={handleGuidelinesUpload} />
                <div onClick={() => guideRef.current?.click()} className="relative flex items-center gap-4 p-4 rounded-xl border border-dashed border-white/[0.12] hover:border-brand/40 hover:bg-brand/5 cursor-pointer transition-all">
                  {guideUploading ? <Loader2 className="w-8 h-8 text-brand animate-spin" />
                    : form.guidelinesUrl ? <div className="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center"><CheckCircle2 className="w-5 h-5 text-blue-400" /></div>
                    : <div className="w-12 h-12 rounded-xl bg-brand/10 flex items-center justify-center"><FileText className="w-5 h-5 text-brand-light" /></div>}
                  <div>
                    <p className="text-sm text-white/70 font-medium">{form.guidelinesUrl ? "Guidelines Uploaded ✓" : "Upload Brand Guidelines"}</p>
                    <p className="text-xs text-white/30">PDF, DOCX, PPT — max 20MB</p>
                  </div>
                  {form.guidelinesUrl && (
                    <button onClick={(e) => { e.stopPropagation(); setVal("guidelinesUrl", ""); }} className="absolute top-2 right-2 p-1 rounded-full hover:bg-red-500/20 text-white/30 hover:text-red-400">
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>

              {/* Colors */}
              <div>
                <label className="field-label">Brand Colors</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { key: "primaryColor" as const,   label: "Primary" },
                    { key: "secondaryColor" as const, label: "Secondary" },
                    { key: "accentColor" as const,    label: "Accent" },
                  ].map(({ key, label }) => (
                    <div key={key} className="p-3 rounded-xl border border-white/[0.08] bg-white/[0.03] flex items-center gap-2">
                      <input type="color" className="w-8 h-8 rounded-lg cursor-pointer bg-transparent border-0 p-0 flex-shrink-0" value={form[key] as string} onChange={set(key)} />
                      <div>
                        <p className="text-xs font-medium text-white/70">{label}</p>
                        <p className="text-[10px] text-white/30 font-mono">{form[key] as string}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Palette */}
              <div>
                <label className="field-label">Extended Palette <span className="text-white/30 font-normal">(optional)</span></label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {form.palette.map((c, i) => (
                    <div key={i} className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-white/[0.05] border border-white/[0.08]">
                      <div className="w-4 h-4 rounded-full border border-white/20" style={{ backgroundColor: c }} />
                      <span className="text-[10px] font-mono text-white/50">{c}</span>
                      <button onClick={() => setVal("palette", form.palette.filter((_, j) => j !== i))} className="text-white/20 hover:text-red-400 ml-0.5"><X className="w-2.5 h-2.5" /></button>
                    </div>
                  ))}
                </div>
                {form.palette.length < 8 && (
                  <div className="flex items-center gap-2">
                    <input type="color" className="w-9 h-9 rounded-lg cursor-pointer bg-transparent border-0 p-0" value={newPaletteColor} onChange={(e) => setNewPaletteColor(e.target.value)} />
                    <span className="text-xs font-mono text-white/40">{newPaletteColor}</span>
                    <button onClick={() => { setVal("palette", [...form.palette, newPaletteColor]); }} className="px-3 py-1.5 rounded-lg bg-brand/20 text-brand-light text-xs border border-brand/30 hover:bg-brand/30 transition-colors">
                      + Add
                    </button>
                  </div>
                )}
              </div>
            </>
          )}

          {/* ── Step 4: Target Audience ── */}
          {step === 4 && (
            <>
              <SectionHint icon={Target} title="Target Audience" desc="Who exactly watches your content and what they care about." />
              <div>
                <label className="field-label">Audience Overview</label>
                <textarea className="input-glass w-full min-h-[60px] resize-none" placeholder="e.g. D2C & SaaS founders, 25-40 years, Tier 1 Indian cities, looking to scale using social media" value={form.targetAudience} onChange={set("targetAudience")} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="field-label">Age Range</label>
                  <input className="input-glass w-full" placeholder="e.g. 22-40 years" value={form.audienceAge} onChange={set("audienceAge")} />
                </div>
                <div>
                  <label className="field-label">Profession / Role</label>
                  <input className="input-glass w-full" placeholder="e.g. D2C founders, SaaS marketers" value={form.audienceProfession} onChange={set("audienceProfession")} />
                </div>
                <div>
                  <label className="field-label">Knowledge Level</label>
                  <select className="input-glass w-full" value={form.audienceLevel} onChange={set("audienceLevel")}>
                    <option value="">Select level…</option>
                    {AUDIENCE_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                  </select>
                </div>
                <div>
                  <label className="field-label">Language Mix</label>
                  <input className="input-glass w-full" placeholder="e.g. 60% English, 40% Hindi" value={form.audienceLanguage} onChange={set("audienceLanguage")} />
                </div>
                <div className="col-span-2">
                  <label className="field-label">Pain Points</label>
                  <textarea className="input-glass w-full min-h-[70px] resize-none" placeholder="e.g. Can't afford agencies, don't know what content works, posting randomly without strategy, low engagement" value={form.audiencePainPoints} onChange={set("audiencePainPoints")} />
                </div>
                <div className="col-span-2">
                  <label className="field-label">Aspirations (What they want to become)</label>
                  <textarea className="input-glass w-full min-h-[70px] resize-none" placeholder="e.g. Build a personal brand with 100K followers, get clients from Instagram, become industry thought leaders" value={form.audienceAspirations} onChange={set("audienceAspirations")} />
                </div>
              </div>

              {/* Audience Persona Cards */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="field-label mb-0">Audience Personas</label>
                  <button
                    onClick={() => setVal("audiencePersona", [...form.audiencePersona, { name: "", age: "", job: "", goals: "", frustrations: "" }])}
                    className="text-xs text-brand-light hover:text-white flex items-center gap-1 transition-colors"
                  >
                    <Plus className="w-3 h-3" /> Add Persona
                  </button>
                </div>
                {form.audiencePersona.length === 0 ? (
                  <p className="text-xs text-white/25 italic">No personas added. Personas help AI agents create hyper-targeted content.</p>
                ) : (
                  <div className="space-y-3">
                    {form.audiencePersona.map((p, i) => (
                      <div key={i} className="p-3 rounded-xl border border-white/[0.08] bg-white/[0.02] space-y-2">
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-medium text-white/60">Persona {i + 1}</p>
                          <button onClick={() => setVal("audiencePersona", form.audiencePersona.filter((_, j) => j !== i))} className="text-white/20 hover:text-red-400"><X className="w-3 h-3" /></button>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <input className="input-glass w-full text-xs py-2" placeholder="Name (e.g. Rahul)" value={p.name} onChange={(e) => { const arr = [...form.audiencePersona]; arr[i] = { ...arr[i], name: e.target.value }; setVal("audiencePersona", arr); }} />
                          <input className="input-glass w-full text-xs py-2" placeholder="Age (e.g. 28)" value={p.age ?? ""} onChange={(e) => { const arr = [...form.audiencePersona]; arr[i] = { ...arr[i], age: e.target.value }; setVal("audiencePersona", arr); }} />
                          <input className="input-glass w-full text-xs py-2" placeholder="Job (e.g. D2C Founder)" value={p.job ?? ""} onChange={(e) => { const arr = [...form.audiencePersona]; arr[i] = { ...arr[i], job: e.target.value }; setVal("audiencePersona", arr); }} />
                          <input className="input-glass w-full text-xs py-2" placeholder="Goals" value={p.goals ?? ""} onChange={(e) => { const arr = [...form.audiencePersona]; arr[i] = { ...arr[i], goals: e.target.value }; setVal("audiencePersona", arr); }} />
                          <input className="input-glass w-full text-xs py-2 col-span-2" placeholder="Frustrations" value={p.frustrations ?? ""} onChange={(e) => { const arr = [...form.audiencePersona]; arr[i] = { ...arr[i], frustrations: e.target.value }; setVal("audiencePersona", arr); }} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

          {/* ── Step 5: Voice & Style ── */}
          {step === 5 && (
            <>
              <SectionHint icon={Mic2} title="Voice & Style" desc="How your brand sounds, speaks, and connects with the audience." />
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="field-label">Brand Tone</label>
                  <select className="input-glass w-full" value={form.tone} onChange={set("tone")}>
                    <option value="">Select tone…</option>
                    {TONES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="field-label">Voice Style (Address)</label>
                  <select className="input-glass w-full" value={form.voiceStyle} onChange={set("voiceStyle")}>
                    <option value="">Select style…</option>
                    {VOICE_STYLES.map(v => <option key={v} value={v}>{v}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="field-label">Signature Catchphrases</label>
                <textarea className="input-glass w-full min-h-[70px] resize-none" placeholder="e.g. 'Content jo convert kare', 'Scale smart, not hard', 'Grow karo, ruko mat'" value={form.catchphrases} onChange={set("catchphrases")} />
              </div>
              <div>
                <label className="field-label">Forbidden Words / Phrases (Never Use)</label>
                <textarea className="input-glass w-full min-h-[60px] resize-none" placeholder="e.g. 'cheap', 'discount', 'basic', competitor names, certain jargon…" value={form.forbiddenWords} onChange={set("forbiddenWords")} />
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl border border-white/[0.08] bg-white/[0.02]">
                <div>
                  <p className="text-sm text-white/70 font-medium">Uses Slang / Memes / Casual Language</p>
                  <p className="text-xs text-white/30">AI will include slang, memes, and informal references in captions</p>
                </div>
                <button
                  onClick={() => setVal("usesSlang", !form.usesSlang)}
                  className={`relative w-11 h-6 rounded-full transition-colors flex-shrink-0 ${form.usesSlang ? "bg-brand" : "bg-white/[0.12]"}`}
                >
                  <span className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-all ${form.usesSlang ? "left-6" : "left-1"}`} />
                </button>
              </div>
              <div>
                <label className="field-label">Hook Style (How content starts)</label>
                <textarea className="input-glass w-full min-h-[70px] resize-none" placeholder="e.g. Start with a bold controversial statement, ask a question that triggers curiosity, share a shocking stat, use pattern interrupt…" value={form.hookStyle} onChange={set("hookStyle")} />
              </div>
              <div>
                <label className="field-label">CTA Style (How content ends)</label>
                <textarea className="input-glass w-full min-h-[60px] resize-none" placeholder="e.g. Always end with a question, direct CTA to DM 'SCALE', save this for later, comment your biggest challenge…" value={form.ctaStyle} onChange={set("ctaStyle")} />
              </div>
            </>
          )}

          {/* ── Step 6: Content Strategy ── */}
          {step === 6 && (
            <>
              <SectionHint icon={BarChart2} title="Content Strategy" desc="What topics, formats, and formulas drive results for your brand." />

              {/* Content Pillars */}
              <div>
                <label className="field-label">Content Pillars</label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {form.contentPillars.map((p, i) => (
                    <span key={i} className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-brand/15 text-brand-light text-xs border border-brand/25">
                      {p}
                      <button onClick={() => setVal("contentPillars", form.contentPillars.filter((_, j) => j !== i))}><X className="w-2.5 h-2.5 ml-0.5" /></button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2 mb-2">
                  <input
                    className="input-glass flex-1 text-sm"
                    placeholder="Add custom pillar…"
                    value={newPillar}
                    onChange={e => setNewPillar(e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter" && newPillar.trim()) { setVal("contentPillars", [...form.contentPillars, newPillar.trim()]); setNewPillar(""); } }}
                  />
                  <button
                    onClick={() => { if (newPillar.trim()) { setVal("contentPillars", [...form.contentPillars, newPillar.trim()]); setNewPillar(""); } }}
                    className="px-3 py-1.5 rounded-lg bg-brand/20 text-brand-light text-xs border border-brand/30 hover:bg-brand/30 transition-colors"
                  >Add</button>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {CONTENT_PILLAR_SUGGESTIONS.filter(s => !form.contentPillars.includes(s)).map(s => (
                    <button key={s} onClick={() => setVal("contentPillars", [...form.contentPillars, s])}
                      className="px-2 py-0.5 rounded-full text-[10px] text-white/40 border border-white/[0.08] hover:border-brand/30 hover:text-brand-light hover:bg-brand/5 transition-all">
                      + {s}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="field-label">Ideal Video/Reel Length</label>
                <div className="flex flex-wrap gap-2">
                  {VIDEO_LENGTHS.map(l => (
                    <button key={l} onClick={() => setVal("idealVideoLength", l)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${form.idealVideoLength === l ? "bg-brand/20 text-brand-light border-brand/40" : "text-white/40 border-white/[0.08] hover:border-brand/20 hover:text-white/60"}`}>
                      {l}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="field-label">Proven Hook Formulas</label>
                <textarea className="input-glass w-full min-h-[80px] resize-none" placeholder={`e.g.\n• "X cheezon ne meri life change kar di in Y days"\n• "Most [profession] make this mistake..."\n• "[Shocking stat] — here's why..."`} value={form.hookFormulas} onChange={set("hookFormulas")} />
              </div>
              <div>
                <label className="field-label">Top 3 Best-Performing Hooks (past content)</label>
                <textarea className="input-glass w-full min-h-[80px] resize-none" placeholder="Paste your 3 hooks that got the most reach/saves/shares. AI will replicate the pattern." value={form.bestHooks} onChange={set("bestHooks")} />
              </div>
              <div>
                <label className="field-label">What Has NOT Worked (Worst Content)</label>
                <textarea className="input-glass w-full min-h-[70px] resize-none" placeholder="e.g. Long educational posts without hooks flopped. Promotional content kills reach. Generic tips get no saves." value={form.worstContent} onChange={set("worstContent")} />
              </div>
            </>
          )}

          {/* ── Step 7: Competitors & Uploads ── */}
          {step === 7 && (
            <>
              <SectionHint icon={Swords} title="Competitors & Media" desc="Who you're up against, and your best campaign assets." />

              {/* Competitors */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="field-label mb-0">Competitors</label>
                  <button
                    onClick={() => setVal("competitors", [...form.competitors, { name: "", handle: "", notes: "" }])}
                    className="text-xs text-brand-light hover:text-white flex items-center gap-1 transition-colors"
                  >
                    <Plus className="w-3 h-3" /> Add Competitor
                  </button>
                </div>
                {form.competitors.length === 0 ? (
                  <p className="text-xs text-white/25 italic">No competitors added yet. AI uses this for gap analysis.</p>
                ) : (
                  <div className="space-y-2">
                    {form.competitors.map((c, i) => (
                      <div key={i} className="grid grid-cols-3 gap-2 items-start">
                        <input className="input-glass text-xs py-2" placeholder="Brand name" value={c.name} onChange={(e) => { const arr = [...form.competitors]; arr[i] = { ...arr[i], name: e.target.value }; setVal("competitors", arr); }} />
                        <input className="input-glass text-xs py-2" placeholder="@handle" value={c.handle ?? ""} onChange={(e) => { const arr = [...form.competitors]; arr[i] = { ...arr[i], handle: e.target.value }; setVal("competitors", arr); }} />
                        <div className="flex gap-1">
                          <input className="input-glass text-xs py-2 flex-1" placeholder="Notes" value={c.notes ?? ""} onChange={(e) => { const arr = [...form.competitors]; arr[i] = { ...arr[i], notes: e.target.value }; setVal("competitors", arr); }} />
                          <button onClick={() => setVal("competitors", form.competitors.filter((_, j) => j !== i))} className="p-2 rounded-lg hover:bg-red-500/10 text-white/20 hover:text-red-400"><X className="w-3 h-3" /></button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Campaign Uploads */}
              <div>
                <label className="field-label">Best Campaigns / Past Ad Creatives</label>
                <input ref={campaignRef} type="file" accept="image/*,video/*,.pdf" multiple className="hidden" onChange={handleCampaignUpload} />
                <div onClick={() => campaignRef.current?.click()} className="flex items-center gap-4 p-4 rounded-xl border border-dashed border-white/[0.12] hover:border-brand/40 hover:bg-brand/5 cursor-pointer transition-all">
                  {campaignUploading ? <Loader2 className="w-6 h-6 text-brand animate-spin" />
                    : <div className="w-10 h-10 rounded-xl bg-brand/10 flex items-center justify-center"><Video className="w-5 h-5 text-brand-light" /></div>}
                  <div>
                    <p className="text-sm text-white/70 font-medium">Upload Campaign Assets</p>
                    <p className="text-xs text-white/30">Images, videos, PDFs — multiple files OK</p>
                  </div>
                </div>
                {form.campaignUrls.length > 0 && (
                  <div className="mt-2 space-y-1.5">
                    {form.campaignUrls.map((f, i) => (
                      <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                        <Upload className="w-3 h-3 text-brand-light flex-shrink-0" />
                        <span className="text-xs text-white/60 flex-1 truncate">{f.name}</span>
                        <button onClick={() => setVal("campaignUrls", form.campaignUrls.filter((_, j) => j !== i))} className="text-white/20 hover:text-red-400"><X className="w-3 h-3" /></button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Brand Media Uploads */}
              <div>
                <label className="field-label">Brand Media Assets (Logos, Visuals, Templates)</label>
                <input ref={mediaRef} type="file" accept="image/*,video/*,.pdf,.ai,.psd" multiple className="hidden" onChange={handleMediaUpload} />
                <div onClick={() => mediaRef.current?.click()} className="flex items-center gap-4 p-4 rounded-xl border border-dashed border-white/[0.12] hover:border-brand/40 hover:bg-brand/5 cursor-pointer transition-all">
                  {mediaUploading ? <Loader2 className="w-6 h-6 text-brand animate-spin" />
                    : <div className="w-10 h-10 rounded-xl bg-brand/10 flex items-center justify-center"><ImageIcon className="w-5 h-5 text-brand-light" /></div>}
                  <div>
                    <p className="text-sm text-white/70 font-medium">Upload Brand Media</p>
                    <p className="text-xs text-white/30">Logos, visuals, design files — multiple files OK</p>
                  </div>
                </div>
                {form.brandMediaUrls.length > 0 && (
                  <div className="mt-2 space-y-1.5">
                    {form.brandMediaUrls.map((f, i) => (
                      <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                        <ImageIcon className="w-3 h-3 text-brand-light flex-shrink-0" />
                        <span className="text-xs text-white/60 flex-1 truncate">{f.name}</span>
                        <button onClick={() => setVal("brandMediaUrls", form.brandMediaUrls.filter((_, j) => j !== i))} className="text-white/20 hover:text-red-400"><X className="w-3 h-3" /></button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

          {/* ── Step 8: Instagram & AI Knowledge ── */}
          {step === 8 && (
            <>
              <InstagramConnectStep
                brandId={brand?.id}
                igUsername={brand?.igUsername}
                igAccountId={brand?.igAccountId}
                igTokenExpiresAt={brand?.igTokenExpiresAt}
                brandName={brand?.name}
                onConnected={(username) => setForm(f => ({ ...f, igAccountId: username }))}
              />

              <div className="mt-4">
                <div className="p-4 rounded-xl bg-gradient-to-r from-brand/10 to-indigo-500/10 border border-brand/20 mb-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Brain className="w-4 h-4 text-brand-light" />
                    <p className="text-sm font-medium text-white">Brand AI Knowledge Base</p>
                  </div>
                  <p className="text-xs text-white/40">
                    Extra context for AI agents — USPs, products, past wins, hashtags to always use, etc. The more detail, the better the output.
                  </p>
                </div>
                <label className="field-label">Additional Brand Context</label>
                <textarea
                  className="input-glass w-full min-h-[160px] resize-none leading-relaxed"
                  placeholder={`Add anything extra the AI should know:\n\n• Key products / services and their prices\n• USPs that must always be highlighted\n• Signature hashtags to always include\n• Topics to focus on / avoid\n• Past viral content details\n• Client success stories\n• Brand dos and don'ts`}
                  value={form.knowledgeText}
                  onChange={set("knowledgeText")}
                />
                <p className="text-xs text-white/30 mt-1">{form.knowledgeText.length} characters · More detail = better AI output</p>
              </div>
            </>
          )}

          {error && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 pb-6 pt-4 border-t border-white/[0.06] flex-shrink-0">
          <button onClick={() => step > 1 ? setStep(s => s - 1) : onClose()} className="btn-ghost flex items-center gap-2">
            <ArrowLeft className="w-4 h-4" />
            {step > 1 ? "Back" : "Cancel"}
          </button>

          <div className="flex items-center gap-3">
            {/* Save & Continue on any step */}
            {mode === "edit" && step < STEPS.length && (
              <button
                onClick={() => mutation.mutate()}
                disabled={!form.name || mutation.isPending}
                className="btn-ghost flex items-center gap-2 text-sm disabled:opacity-40"
              >
                {mutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                Save Draft
              </button>
            )}

            {step < STEPS.length ? (
              <button onClick={() => setStep(s => s + 1)} disabled={!canNext} className="btn-primary flex items-center gap-2 disabled:opacity-40">
                Next <ArrowRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={() => mutation.mutate()}
                disabled={!form.name || mutation.isPending}
                className="btn-primary flex items-center gap-2 disabled:opacity-40"
              >
                {mutation.isPending
                  ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</>
                  : <><CheckCircle2 className="w-4 h-4" /> {mode === "create" ? "Create Brand" : "Save Changes"}</>}
              </button>
            )}
          </div>
        </div>
      </GlassCard>
    </div>
  );
}

// ─── Section Hint ─────────────────────────────────────────────────────────────
function SectionHint({ icon: Icon, title, desc }: { icon: React.ComponentType<{ className?: string }>; title: string; desc: string }) {
  return (
    <div className="flex items-start gap-3 p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.05] mb-1">
      <div className="w-8 h-8 rounded-lg bg-brand/10 flex items-center justify-center flex-shrink-0 mt-0.5">
        <Icon className="w-4 h-4 text-brand-light" />
      </div>
      <div>
        <p className="text-sm font-medium text-white/80">{title}</p>
        <p className="text-xs text-white/35 mt-0.5">{desc}</p>
      </div>
    </div>
  );
}

// ─── Instagram Manual Connect (3-field form) ──────────────────────────────────
function InstagramConnectStep({
  brandId, igUsername, igAccountId, igTokenExpiresAt, brandName, onConnected,
}: {
  brandId?: string; igUsername?: string; igAccountId?: string;
  igTokenExpiresAt?: string; brandName?: string;
  onConnected?: (u: string) => void;
}) {
  const [loading, setLoading]           = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [pageIdInput, setPageIdInput]   = useState("");
  const [accountIdInput, setAccountIdInput] = useState(igAccountId ?? "");
  const [tokenInput, setTokenInput]     = useState("");
  const [showToken, setShowToken]       = useState(false);
  const [showGuide, setShowGuide]       = useState(false);
  const [connectError, setConnectError] = useState("");
  const [testResult, setTestResult]     = useState<{
    igUsername: string; igAccountId: string; igFollowers: number;
    pageName?: string; pageId?: string;
  } | null>(null);
  const queryClient = useQueryClient();

  const isConnected    = !!(igUsername || (igAccountId && igAccountId !== ""));
  const expiryDate     = igTokenExpiresAt ? new Date(igTokenExpiresAt) : null;
  const expiryStr      = expiryDate
    ? expiryDate.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })
    : null;

  async function handleTestConnection() {
    if (!tokenInput.trim()) { setConnectError("Page Access Token is required."); return; }
    setLoading(true); setConnectError(""); setTestResult(null);
    try {
      const res = await api.post("/api/meta/manual-connect", {
        brandId: brandId ?? "test",
        accessToken: tokenInput.trim(),
        igAccountId: accountIdInput.trim() || undefined,
        pageId: pageIdInput.trim() || undefined,
        testOnly: true,
      });
      setTestResult(res.data);
    } catch (err: any) {
      setConnectError(err?.response?.data?.message ?? "Test failed. Check your token and try again.");
    } finally { setLoading(false); }
  }

  async function handleSave() {
    if (!brandId) { setConnectError("Save the brand first, then connect Instagram."); return; }
    if (!tokenInput.trim()) { setConnectError("Paste your Page Access Token first."); return; }
    setLoading(true); setConnectError("");
    try {
      const res = await api.post("/api/meta/manual-connect", {
        brandId,
        accessToken: tokenInput.trim(),
        igAccountId: (testResult?.igAccountId || accountIdInput.trim()) || undefined,
        pageId: (testResult?.pageId || pageIdInput.trim()) || undefined,
        testOnly: false,
      });
      setTestResult(res.data);
      setTokenInput("");
      queryClient.invalidateQueries({ queryKey: ["brands"] });
      onConnected?.(res.data.igUsername ?? res.data.igAccountId);
    } catch (err: any) {
      setConnectError(err?.response?.data?.message ?? "Save failed.");
    } finally { setLoading(false); }
  }

  async function handleDisconnect() {
    if (!brandId) return;
    setDisconnecting(true); setTestResult(null);
    try {
      await api.post("/api/meta/disconnect", { brandId });
      queryClient.invalidateQueries({ queryKey: ["brands"] });
    } finally { setDisconnecting(false); }
  }

  return (
    <div className="space-y-4">

      {/* ── Title ── */}
      <div>
        <div className="flex items-center gap-2 mb-0.5">
          <Instagram className="w-4 h-4 text-pink-400" />
          <p className="text-sm font-semibold text-white">Connect Instagram</p>
        </div>
        {brandName && (
          <p className="text-xs text-white/40 ml-6">
            Connect <span className="text-white/60 font-medium">{brandName}</span>'s IG Business Account
          </p>
        )}
      </div>

      {/* ── Status bar ── */}
      <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs ${
        isConnected
          ? "bg-green-500/10 border border-green-500/20 text-green-400"
          : "bg-white/[0.04] border border-white/[0.08] text-white/40"
      }`}>
        {isConnected
          ? <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
          : <Link2 className="w-3.5 h-3.5 flex-shrink-0 text-white/30" />
        }
        <span className="font-medium">Status:</span>
        {isConnected ? (
          <span>
            Connected to <span className="font-semibold">@{igUsername}</span>
            {expiryStr && <span className="text-green-400/60"> — Token expires: {expiryStr}</span>}
          </span>
        ) : (
          <span>Not connected</span>
        )}
      </div>

      {/* ── Guide toggle + Meta Dev console link ── */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setShowGuide(g => !g)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-white/[0.06] hover:bg-white/[0.10] border border-white/[0.08] text-white/60 transition-colors"
        >
          <BookOpen className="w-3.5 h-3.5" />
          {showGuide ? "Hide guide" : "Show step-by-step guide"}
        </button>
        <a
          href="https://developers.facebook.com/tools/explorer/"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 text-blue-400 transition-colors"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          Open Meta Developer console
        </a>
      </div>

      {/* ── Step-by-step guide ── */}
      {showGuide && (
        <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] text-xs space-y-2">
          <p className="font-semibold text-white/70 mb-3">Meta Graph API — Setup Guide</p>
          <ol className="space-y-2 list-decimal list-inside text-white/40">
            <li>Make sure the IG account is Business / Creator + linked to a Facebook Page.</li>
            <li>Go to <span className="text-white/60 font-mono">developers.facebook.com</span> → "My Apps" → use existing or create Business app.</li>
            <li>Add use case: "Manage messaging on Instagram" + tick permissions: <span className="font-mono text-white/50">instagram_basic, instagram_manage_insights</span></li>
            <li>
              Go to <span className="text-white/60 font-mono">developers.facebook.com/tools/explorer/</span>
              <ul className="ml-4 mt-1 list-disc list-inside space-y-0.5">
                <li>Pick your app top-right</li>
                <li>Permissions: <span className="font-mono text-white/50">instagram_basic, instagram_manage_insights, pages_show_list, pages_read_engagement, business_management</span></li>
                <li>Click Generate Access Token → choose the FB Page → Continue</li>
              </ul>
            </li>
            <li>Extend to long-lived (+60d): <span className="font-mono text-white/50">developers.facebook.com/tools/debug/accesstoken/</span></li>
            <li>
              In Explorer:
              <ul className="ml-4 mt-1 list-disc list-inside space-y-0.5">
                <li>GET /me/accounts → <span className="font-mono">"id"</span> inside the Page block = <span className="text-white/60 font-semibold">FB Page ID</span></li>
                <li><span className="font-mono">"access_token"</span> inside the same block = <span className="text-white/60 font-semibold">Page Access Token</span></li>
                <li>GET /&lt;PAGE-ID&gt;?fields=instagram_business_account → <span className="font-mono">instagram_business_account.id</span> = <span className="text-white/60 font-semibold">IG Account ID</span></li>
              </ul>
            </li>
            <li>Paste all three → Test Connection → Save.</li>
          </ol>
        </div>
      )}

      {/* ── 3 input fields ── */}
      <div className="space-y-3">

        {/* Facebook Page ID */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-white/60">Facebook Page ID</label>
          <input
            type="text"
            value={pageIdInput}
            onChange={e => setPageIdInput(e.target.value)}
            placeholder="e.g. 8609934044585"
            className="w-full px-3 py-2.5 rounded-lg bg-white/[0.06] border border-white/[0.10] text-white text-sm placeholder-white/20 focus:outline-none focus:border-purple-500/50 transition-colors font-mono"
          />
        </div>

        {/* Instagram Account ID */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-white/60">Instagram Account ID</label>
          <input
            type="text"
            value={accountIdInput}
            onChange={e => setAccountIdInput(e.target.value)}
            placeholder="e.g. 17841478318822819"
            className="w-full px-3 py-2.5 rounded-lg bg-white/[0.06] border border-white/[0.10] text-white text-sm placeholder-white/20 focus:outline-none focus:border-purple-500/50 transition-colors font-mono"
          />
        </div>

        {/* Page Access Token */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-white/60">
            Page Access Token <span className="text-pink-400">*</span>
          </label>
          <div className="relative">
            <input
              type={showToken ? "text" : "password"}
              value={tokenInput}
              onChange={e => { setTokenInput(e.target.value); setConnectError(""); setTestResult(null); }}
              placeholder="Paste your long-lived Page Access Token here"
              className="w-full px-3 py-2.5 pr-20 rounded-lg bg-white/[0.06] border border-white/[0.10] text-white text-sm placeholder-white/20 focus:outline-none focus:border-purple-500/50 transition-colors"
            />
            <label className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5 text-xs text-white/40 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={showToken}
                onChange={e => setShowToken(e.target.checked)}
                className="w-3 h-3 accent-purple-500"
              />
              Show
            </label>
          </div>
        </div>
      </div>

      {/* ── Error ── */}
      {connectError && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
          <p className="text-xs text-red-400">{connectError}</p>
        </div>
      )}

      {/* ── Test Result ── */}
      {testResult && (
        <div className="p-3 rounded-xl bg-white/[0.04] border border-white/[0.08]">
          <p className="text-xs font-semibold text-white/60 mb-2 uppercase tracking-wide">Test Result</p>
          <p className="text-xs mb-2">
            {isConnected
              ? <span className="text-green-400 font-medium">✓ Previously connected</span>
              : <span className="text-blue-400 font-medium">✓ Ready to connect</span>
            }
          </p>
          <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
            <span className="text-white/30">IG username:</span>
            <span className="text-white/70 font-mono">@{testResult.igUsername}</span>
            <span className="text-white/30">IG account ID:</span>
            <span className="text-white/70 font-mono">{testResult.igAccountId}</span>
            <span className="text-white/30">Followers:</span>
            <span className="text-white/70">{testResult.igFollowers?.toLocaleString()}</span>
            {testResult.pageName && (
              <>
                <span className="text-white/30">Page name:</span>
                <span className="text-white/70">{testResult.pageName}</span>
              </>
            )}
            {testResult.pageId && (
              <>
                <span className="text-white/30">Page ID:</span>
                <span className="text-white/70 font-mono">{testResult.pageId}</span>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── Action buttons ── */}
      <div className="flex gap-2">
        {isConnected && (
          <button
            onClick={handleDisconnect}
            disabled={disconnecting}
            className="flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg text-xs font-medium bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 transition-all"
          >
            {disconnecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Link2Off className="w-3.5 h-3.5" />}
            Disconnect
          </button>
        )}
        <button
          onClick={handleTestConnection}
          disabled={loading || !tokenInput.trim()}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-xs font-medium bg-white/[0.06] hover:bg-white/[0.10] border border-white/[0.08] text-white/70 disabled:opacity-40 transition-all"
        >
          {loading && !testResult ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
          Test Connection
        </button>
        <button
          onClick={handleSave}
          disabled={loading || !tokenInput.trim() || !brandId}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-xs font-bold bg-gradient-to-r from-purple-600 to-pink-600 hover:opacity-90 text-white disabled:opacity-40 transition-all shadow-lg shadow-purple-900/30"
        >
          {loading && !!testResult ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
          Save
        </button>
      </div>

      {!brandId && (
        <p className="text-xs text-yellow-400/70 text-center">
          ⚠ Save the brand first — then come back to connect Instagram from Edit Brand.
        </p>
      )}
    </div>
  );
}

// ─── Tailwind helper classes used above ──────────────────────────────────────
// field-label is defined in globals.css as: .field-label { @apply text-xs text-white/50 mb-1.5 block font-medium; }
