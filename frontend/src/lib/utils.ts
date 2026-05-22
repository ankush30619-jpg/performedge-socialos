import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

export function formatPct(n: number, decimals = 1): string {
  return `${n.toFixed(decimals)}%`;
}

export function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

export function getDaysUntil(dateStr: string): number {
  const future = new Date(dateStr);
  const now = new Date();
  return Math.max(0, Math.ceil((future.getTime() - now.getTime()) / 86400000));
}

export function slugify(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

export function getInitials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

export function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export const CONTENT_TYPE_COLORS: Record<string, string> = {
  Reel: "#3B82F6",
  "AI Reel": "#EC4899",
  Carousel: "#10B981",
  Graphic: "#A78BFA",
  Story: "#F59E0B",
};

export const AGENT_LABELS: Record<string, string> = {
  brandManager: "Brand Manager",
  analyst: "Analyst",
  researchAgent: "Research Agent",
  competitorTracker: "Competitor Tracker",
  growthPlanner: "Growth Planner",
  strategist: "Strategist",
  copywriter: "Copywriter",
  designer: "Designer",
};

export const AGENT_ICONS: Record<string, string> = {
  brandManager: "🧠",
  analyst: "📊",
  researchAgent: "🔍",
  competitorTracker: "🕵️",
  growthPlanner: "📈",
  strategist: "📅",
  copywriter: "✍️",
  designer: "🎨",
};
