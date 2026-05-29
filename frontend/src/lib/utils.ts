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

export const AGENT_DESCRIPTIONS: Record<string, string> = {
  brandManager:      "Loads your brand profile, decrypts the Instagram token, and builds a rich brand-knowledge context block (positioning, voice, content pillars, audience) that every downstream agent uses.",
  analyst:           "Calls the Meta Graph API for real-time Instagram metrics — followers, engagement rate, top posts — then uses GPT to interpret the numbers into strategic insights and benchmarks.",
  researchAgent:     "Runs 7 targeted web searches (Tavily + NewsAPI) for your niche, surfaces viral trends and audience pain points, then synthesises findings into brand-specific content angles and 25+ hashtags.",
  competitorTracker: "Analyses your known competitors plus top niche accounts, maps their content strategy, and identifies the gaps and differentiation angles your brand can own.",
  growthPlanner:     "Orchestrates Research + Competitor agents in parallel, audits your Instagram post history, builds a month-by-month follower growth roadmap, and generates the strategy PPT + Excel deck.",
  strategist:        "Creates the 15-day content calendar — one post per day — using the brand brief, content pillars, research trends, and competitor gaps. Each post has a topic, content type, visual direction, and posting time.",
  copywriter:        "Writes production-ready captions for every post: 3 hook variations, short + long captions, CTA, 20-30 hashtags, SEO keywords, and type-specific content (Reel script / Carousel slides / Story frames / Graphic layout).",
  designer:          "Generates images via Freepik Mystic AI for Graphic/Reel/Carousel posts, builds the styled 18-column Excel content calendar, and renders the final PowerPoint strategy presentation.",
};

export const AGENT_PRODUCES: Record<string, string> = {
  brandManager:      "Brand knowledge context · Decrypted IG token",
  analyst:           "Follower count · Engagement rate · Top 10 posts · Content opportunities",
  researchAgent:     "Trending content angles · Audience pain insights · Hashtag clusters · Viral formats",
  competitorTracker: "Competitor content breakdown · Gaps to fill · Differentiation strategy",
  growthPlanner:     "Growth roadmap · KPI targets · Content mix % · Strategy PPT · Excel calendar",
  strategist:        "15-day content calendar · Topic per post · Content type · Visual direction · Posting time",
  copywriter:        "Hooks · Captions · CTAs · Hashtags · SEO keywords · Scripts · Slides · Layouts",
  designer:          "AI-generated images · Downloadable Excel calendar · Downloadable PPT deck",
};

// ── Rich agent metadata — powers the "before run" Agent Information Panel ──────
// Each entry explains what the agent is, why it exists, and how to judge success.
export interface AgentMeta {
  purpose: string;
  objective: string;
  inputs: string[];
  outputs: string[];
  tools: string[];
  dataSources: string[];
  dependencies: string[];
  successCriteria: string[];
}

export const AGENT_METADATA: Record<string, AgentMeta> = {
  brandManager: {
    purpose: "Load and structure everything the platform knows about your brand.",
    objective: "Decrypt the Instagram access token server-side and assemble a rich brand-knowledge context block (positioning, voice, pillars, audience) that every downstream agent reuses.",
    inputs: ["Brand profile from database", "Encrypted Instagram token", "Brand guidelines & media URLs"],
    outputs: ["Brand knowledge context block", "Decrypted IG token (server-side only)"],
    tools: ["Prisma / Supabase", "AES-256-GCM token decryption", "GPT-4o-mini (context synthesis)"],
    dataSources: ["Brand Hub profile", "Uploaded brand guidelines"],
    dependencies: ["None — runs first"],
    successCriteria: ["Brand context block built", "IG token decrypted (if connected)", "All downstream agents receive consistent brand data"],
  },
  analyst: {
    purpose: "Measure real Instagram performance and turn the numbers into insight.",
    objective: "Call the Meta Graph API for live followers, engagement, reach and top posts, then interpret the data into strengths, opportunities and benchmarks.",
    inputs: ["Decrypted IG token", "IG account ID", "Brand knowledge context"],
    outputs: ["Follower count", "Avg engagement rate", "Avg reach", "Top 10 posts", "Content opportunities"],
    tools: ["Meta Graph API v21.0", "GPT-4o-mini (insight synthesis)"],
    dataSources: ["Instagram Business account insights", "Recent media (last 20 posts)"],
    dependencies: ["Brand Manager"],
    successCriteria: ["Live metrics fetched (or labelled baseline if no IG)", "Top posts ranked by engagement", "No fabricated metrics when IG is disconnected"],
  },
  researchAgent: {
    purpose: "Discover what is working RIGHT NOW in your niche across the web.",
    objective: "Run 7 targeted searches plus a news query, then synthesise findings into brand-specific content angles, audience pain insights and a hashtag strategy.",
    inputs: ["Niche & industry", "Target audience & pain points", "Content pillars"],
    outputs: ["Trending content angles", "Audience pain insights", "Hook ideas", "25+ hashtags", "Viral formats"],
    tools: ["Tavily Search API", "NewsAPI", "GPT-4o-mini (synthesis)"],
    dataSources: ["Web (Instagram, TikTok, YouTube Shorts trends)", "Recent news articles"],
    dependencies: ["Brand Manager"],
    successCriteria: ["7 searches executed", "Sources captured for audit", "Angles specific to the niche (not generic)"],
  },
  competitorTracker: {
    purpose: "Analyze competitors in the market and find where you can win.",
    objective: "Identify positioning, strengths, weaknesses, content strategy and gaps, then produce concrete differentiation opportunities.",
    inputs: ["Known competitors list", "Niche & positioning", "Brand differentiation"],
    outputs: ["Competitor content breakdown", "Their strengths & weaknesses", "Content gaps to fill", "Differentiation strategy"],
    tools: ["Tavily Search API", "GPT-4o-mini (competitive analysis)"],
    dataSources: ["Competitor websites", "Instagram / LinkedIn / Facebook / YouTube pages", "Reviews & articles"],
    dependencies: ["Brand Manager"],
    successCriteria: ["Real competitors identified", "Sources categorised by platform", "Gaps tied to the brand's positioning"],
  },
  growthPlanner: {
    purpose: "Turn data + research into a measurable follower-growth roadmap.",
    objective: "Audit Instagram history, run the goal-feasibility math, validate every number, and generate a consultant-grade growth strategy deck.",
    inputs: ["Analyst report", "Research data", "Competitor data", "Current followers & goal", "Plan duration"],
    outputs: ["Growth roadmap", "Goal feasibility math", "KPI targets", "Content mix %", "Strategy PPT"],
    tools: ["GPT-4o-mini (strategy)", "python-pptx", "Quality-check validator", "Supabase Storage"],
    dataSources: ["Analyst metrics", "Research Agent output", "Competitor Tracker output"],
    dependencies: ["Brand Manager", "Analyst", "Research Agent", "Competitor Tracker"],
    successCriteria: ["Goal math verified & consistent", "No fabricated statistics", "Plan duration honoured", "Low-confidence figures labelled Estimate/Assumption"],
  },
  strategist: {
    purpose: "Lay out exactly what to post, every day.",
    objective: "Build the day-by-day content calendar using the brand brief, pillars, research trends and competitor gaps.",
    inputs: ["Growth strategy", "Content pillars", "Research trends", "Competitor gaps"],
    outputs: ["Content calendar (1 post/day)", "Topic per post", "Content type", "Visual direction", "Posting time"],
    tools: ["GPT-4o-mini (calendar generation)"],
    dataSources: ["Growth Planner strategy", "Research & competitor insights"],
    dependencies: ["Growth Planner"],
    successCriteria: ["One post per day for the full window", "Each post mapped to a pillar", "Variety across content types"],
  },
  copywriter: {
    purpose: "Write production-ready copy for every planned post.",
    objective: "Produce hooks, captions, CTAs, hashtags and type-specific content (Reel scripts, carousel slides, story frames) in the brand voice.",
    inputs: ["Content calendar", "Brand voice & hook style", "Research hooks & hashtags"],
    outputs: ["3 hook variations", "Short & long captions", "CTA", "20–30 hashtags", "Scripts / slides / frames"],
    tools: ["GPT-4o-mini (copywriting)"],
    dataSources: ["Strategist calendar", "Brand voice profile"],
    dependencies: ["Strategist"],
    successCriteria: ["Every post has complete copy", "Voice matches the brand", "Type-specific content present"],
  },
  designer: {
    purpose: "Create the visuals and the final deliverable files.",
    objective: "Generate images for visual posts, build the styled Excel content calendar, and render the final PowerPoint.",
    inputs: ["Post briefs & copy", "Brand colours & logo", "Visual direction per post"],
    outputs: ["AI-generated images", "Excel content calendar", "PowerPoint deck"],
    tools: ["Freepik Mystic AI", "openpyxl (Excel)", "python-pptx", "Supabase Storage"],
    dataSources: ["Copywriter briefs", "Brand identity assets"],
    dependencies: ["Copywriter"],
    successCriteria: ["Images generated for visual posts", "Excel & PPT uploaded", "Files traceable to source data"],
  },
};
