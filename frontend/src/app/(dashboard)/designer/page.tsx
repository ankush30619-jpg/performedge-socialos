"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { agentAPI } from "@/lib/api";
import { useActiveBrand } from "@/store/useAppStore";
import { GlassCard } from "@/components/ui/GlassCard";
import { CONTENT_TYPE_COLORS } from "@/lib/utils";
import {
  Download, Paintbrush, ExternalLink, X, ChevronLeft, ChevronRight,
  ZoomIn, FileText, Presentation, Image as ImageIcon, Layers,
  CheckCircle2, Filter, Copy,
} from "lucide-react";
import Link from "next/link";
import type { DesignAsset } from "@/types";

type FilterType = "All" | string;

export default function DesignerPage() {
  const activeBrand = useActiveBrand();
  const [lightboxIdx, setLightboxIdx] = useState<number | null>(null);
  const [filter, setFilter]           = useState<FilterType>("All");
  const [copied, setCopied]           = useState<string | null>(null);

  const { data: runsData, isLoading } = useQuery({
    queryKey: ["runs", activeBrand?.id],
    queryFn: () =>
      activeBrand
        ? agentAPI.listRuns(activeBrand.id).then((r) => r.data)
        : Promise.resolve({ runs: [] }),
    enabled: !!activeBrand,
    staleTime: 30000,
  });

  const allRuns    = runsData?.runs ?? [];
  const latestRun  = allRuns[0];
  const assets: DesignAsset[] = latestRun?.designAssets ?? [];

  // Unique content types for filter
  const contentTypes = ["All", ...Array.from(new Set(assets.map((a) => a.contentType)))];
  const filtered = filter === "All" ? assets : assets.filter((a) => a.contentType === filter);

  // Lightbox navigation
  const lightboxPrev = () => setLightboxIdx((i) => (i !== null && i > 0 ? i - 1 : filtered.length - 1));
  const lightboxNext = () => setLightboxIdx((i) => (i !== null && i < filtered.length - 1 ? i + 1 : 0));

  function copyPrompt(prompt: string, id: string) {
    navigator.clipboard.writeText(prompt);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  }

  async function downloadAll() {
    for (const asset of filtered) {
      const a = document.createElement("a");
      a.href = asset.imageUrl;
      a.download = `${asset.contentType}-${asset.id}.jpg`;
      a.target = "_blank";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      await new Promise((r) => setTimeout(r, 300));
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Designer Studio</h1>
          <p className="text-sm text-white/60 mt-0.5">
            {activeBrand
              ? `${activeBrand.name} · AI-generated visuals · Freepik Mystic`
              : "Select a brand to view designs"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {assets.length > 0 && (
            <>
              <span className="text-xs text-white/40 bg-white/[0.06] px-3 py-1.5 rounded-full">
                {assets.length} assets
              </span>
              <button onClick={downloadAll}
                className="btn-ghost flex items-center gap-2 text-sm">
                <Download className="w-4 h-4" /> Download All
              </button>
            </>
          )}
          <Link href="/agents" className="btn-primary flex items-center gap-2 text-sm">
            <Paintbrush className="w-4 h-4" /> Generate New
          </Link>
        </div>
      </div>

      {/* Strategy files row */}
      {latestRun && (latestRun.pptUrl || latestRun.excelUrl) && (
        <div className="grid grid-cols-2 gap-4">
          {latestRun.pptUrl && (
            <a href={latestRun.pptUrl} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-4 p-4 rounded-2xl bg-gradient-to-r from-orange-500/10 to-red-500/10 border border-orange-500/20 hover:border-orange-500/40 transition-all group">
              <div className="w-12 h-12 rounded-xl bg-orange-500/20 flex items-center justify-center flex-shrink-0">
                <Presentation className="w-6 h-6 text-orange-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white">Strategy Deck</p>
                <p className="text-xs text-white/40 mt-0.5">PowerPoint · 6 slides · Growth strategy overview</p>
              </div>
              <ExternalLink className="w-4 h-4 text-white/20 group-hover:text-orange-400 transition-colors flex-shrink-0" />
            </a>
          )}
          {latestRun.excelUrl && (
            <a href={latestRun.excelUrl} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-4 p-4 rounded-2xl bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/20 hover:border-green-500/40 transition-all group">
              <div className="w-12 h-12 rounded-xl bg-green-500/20 flex items-center justify-center flex-shrink-0">
                <FileText className="w-6 h-6 text-green-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white">Content Calendar</p>
                <p className="text-xs text-white/40 mt-0.5">Excel · 15-day schedule · All posts with captions</p>
              </div>
              <ExternalLink className="w-4 h-4 text-white/20 group-hover:text-green-400 transition-colors flex-shrink-0" />
            </a>
          )}
        </div>
      )}

      {/* Run history selector */}
      {allRuns.length > 1 && (
        <GlassCard className="p-4">
          <div className="flex items-center gap-3 overflow-x-auto">
            <Layers className="w-4 h-4 text-white/40 flex-shrink-0" />
            <span className="text-xs text-white/40 flex-shrink-0">Run:</span>
            {allRuns.slice(0, 5).map((run: { id: string; createdAt: string; postsGenerated?: number }, i: number) => (
              <button key={run.id}
                onClick={() => {}}
                className={`text-xs px-3 py-1.5 rounded-lg border whitespace-nowrap transition-all flex-shrink-0
                  ${i === 0 ? "bg-brand/20 border-brand/30 text-brand-light" : "border-white/[0.08] text-white/40 hover:text-white/70 hover:bg-white/[0.05]"}`}>
                {i === 0 ? "Latest" : new Date(run.createdAt).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                {run.postsGenerated != null && ` · ${run.postsGenerated} posts`}
              </button>
            ))}
          </div>
        </GlassCard>
      )}

      {/* Filter bar */}
      {assets.length > 0 && contentTypes.length > 2 && (
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="w-3.5 h-3.5 text-white/30" />
          {contentTypes.map((type) => (
            <button key={type}
              onClick={() => setFilter(type)}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-all
                ${filter === type
                  ? "bg-brand/20 border-brand/30 text-brand-light"
                  : "border-white/[0.08] text-white/40 hover:text-white/70 hover:bg-white/[0.05]"}`}
              style={filter === type && type !== "All" ? { borderColor: `${CONTENT_TYPE_COLORS[type] ?? "#6C3CE1"}50`, backgroundColor: `${CONTENT_TYPE_COLORS[type] ?? "#6C3CE1"}15`, color: CONTENT_TYPE_COLORS[type] ?? "#A78BFA" } : {}}>
              {type}
              {type !== "All" && (
                <span className="ml-1 opacity-60">
                  ({assets.filter((a) => a.contentType === type).length})
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Asset grid */}
      {isLoading ? (
        <div className="grid grid-cols-4 gap-4">
          {[1,2,3,4,5,6].map(i => <div key={i} className="skeleton aspect-square rounded-2xl" />)}
        </div>
      ) : filtered.length > 0 ? (
        <div className="grid grid-cols-4 gap-4">
          {filtered.map((asset, idx) => (
            <GlassCard key={asset.id} className="overflow-hidden p-0 group cursor-pointer" animate>
              {/* Image */}
              <div className="relative aspect-square bg-dark-mid/60" onClick={() => setLightboxIdx(idx)}>
                <img
                  src={asset.imageUrl}
                  alt={asset.topic ?? "Design asset"}
                  className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                  loading="lazy"
                />
                {/* Hover overlay */}
                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
                  <button onClick={(e) => { e.stopPropagation(); setLightboxIdx(idx); }}
                    aria-label={`Preview ${asset.contentType}: ${asset.topic ?? "design asset"}`}
                    className="w-9 h-9 rounded-xl bg-black/70 flex items-center justify-center hover:bg-black/90 transition-colors" title="Preview">
                    <ZoomIn className="w-4 h-4 text-white" />
                  </button>
                  <a href={asset.imageUrl} target="_blank" rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    aria-label={`Open original ${asset.contentType} in new tab`}
                    className="w-9 h-9 rounded-xl bg-black/70 flex items-center justify-center hover:bg-black/90 transition-colors" title="Open original">
                    <ExternalLink className="w-4 h-4 text-white" />
                  </a>
                  <a href={asset.imageUrl} download={`${asset.contentType}-${asset.id}.jpg`}
                    onClick={(e) => e.stopPropagation()}
                    aria-label={`Download ${asset.contentType} image`}
                    className="w-9 h-9 rounded-xl bg-black/70 flex items-center justify-center hover:bg-black/90 transition-colors" title="Download">
                    <Download className="w-4 h-4 text-white" />
                  </a>
                </div>

                {/* Content type badge — dark bg ensures WCAG AA contrast for white text */}
                <div className="absolute top-2 left-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full font-semibold"
                    style={{
                      backgroundColor: "rgba(0,0,0,0.72)",
                      color: CONTENT_TYPE_COLORS[asset.contentType] ?? "#A78BFA",
                      border: `1px solid ${CONTENT_TYPE_COLORS[asset.contentType] ?? "#6C3CE1"}60`,
                    }}>
                    {asset.contentType}
                  </span>
                </div>
              </div>

              {/* Meta */}
              <div className="p-3">
                <div className="flex items-center justify-between mb-1">
                  {asset.date && (
                    <span className="text-[10px] text-white/30">
                      {new Date(asset.date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                    </span>
                  )}
                </div>
                {asset.topic && (
                  <p className="text-xs text-white/70 line-clamp-2">{asset.topic}</p>
                )}
                {asset.prompt && (
                  <div className="flex items-start justify-between mt-1 gap-1">
                    <p className="text-[10px] text-white/30 line-clamp-2 italic flex-1">{asset.prompt}</p>
                    <button onClick={() => copyPrompt(asset.prompt!, asset.id)}
                      aria-label="Copy image generation prompt"
                      className="p-0.5 hover:text-brand-light text-white/20 transition-colors flex-shrink-0" title="Copy prompt">
                      {copied === asset.id ? <CheckCircle2 className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                )}
              </div>
            </GlassCard>
          ))}
        </div>
      ) : (
        <GlassCard className="p-20 flex flex-col items-center text-center">
          <div className="w-16 h-16 rounded-2xl bg-brand/10 flex items-center justify-center mb-4">
            <Paintbrush className="w-7 h-7 text-brand-light" />
          </div>
          <h2 className="text-lg font-semibold text-white mb-2">No designs yet</h2>
          <p className="text-sm text-white/60 max-w-xs mb-5">
            Run the full agent pipeline to generate AI visuals with your brand style
          </p>
          <Link href="/agents" className="btn-primary text-sm">Run Agents Now</Link>
        </GlassCard>
      )}

      {/* Lightbox */}
      {lightboxIdx !== null && filtered[lightboxIdx] && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/90 backdrop-blur-md"
          onClick={() => setLightboxIdx(null)}>
          {/* Close */}
          <button onClick={() => setLightboxIdx(null)}
            aria-label="Close image preview"
            className="absolute top-4 right-4 w-10 h-10 rounded-xl bg-black/70 flex items-center justify-center hover:bg-black/90 transition-colors z-10">
            <X className="w-5 h-5 text-white" />
          </button>

          {/* Prev */}
          {filtered.length > 1 && (
            <button onClick={(e) => { e.stopPropagation(); lightboxPrev(); }}
              aria-label="Previous image"
              className="absolute left-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-xl bg-black/70 flex items-center justify-center hover:bg-black/90 transition-colors z-10">
              <ChevronLeft className="w-5 h-5 text-white" />
            </button>
          )}

          {/* Image */}
          <div className="flex flex-col items-center gap-4 max-w-2xl w-full px-20" onClick={(e) => e.stopPropagation()}>
            <div className="relative w-full aspect-square rounded-2xl overflow-hidden">
              <img
                src={filtered[lightboxIdx].imageUrl}
                alt={filtered[lightboxIdx].topic ?? "Asset"}
                className="w-full h-full object-contain bg-dark-base"
              />
            </div>

            {/* Info & actions */}
            <div className="w-full flex items-start justify-between gap-4">
              <div className="min-w-0">
                {filtered[lightboxIdx].topic && (
                  <p className="text-sm font-medium text-white">{filtered[lightboxIdx].topic}</p>
                )}
                {filtered[lightboxIdx].prompt && (
                  <p className="text-xs text-white/40 mt-1 italic line-clamp-2">{filtered[lightboxIdx].prompt}</p>
                )}
                <p className="text-xs text-white/30 mt-1">
                  {lightboxIdx + 1} / {filtered.length}
                </p>
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <a href={filtered[lightboxIdx].imageUrl} download
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-medium transition-colors">
                  <Download className="w-3.5 h-3.5" /> Download
                </a>
                <a href={filtered[lightboxIdx].imageUrl} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-medium transition-colors">
                  <ExternalLink className="w-3.5 h-3.5" /> Open
                </a>
              </div>
            </div>
          </div>

          {/* Next */}
          {filtered.length > 1 && (
            <button onClick={(e) => { e.stopPropagation(); lightboxNext(); }}
              aria-label="Next image"
              className="absolute right-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-xl bg-black/70 flex items-center justify-center hover:bg-black/90 transition-colors z-10">
              <ChevronRight className="w-5 h-5 text-white" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
