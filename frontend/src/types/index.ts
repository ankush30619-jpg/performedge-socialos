// ═══════════════════════════════════════════════
//  SocialOS — Core TypeScript Types
// ═══════════════════════════════════════════════

export type AgentStatusValue = "pending" | "running" | "completed" | "failed" | "skipped";
export type RunStatus = "pending" | "running" | "completed" | "failed" | "stopped";
export type ContentType = "Reel" | "Carousel" | "Graphic" | "Story" | "AI Reel";

// ── Brand ────────────────────────────────────────
export interface BrandColors {
  primary: string;
  secondary?: string;
  accent?: string;
  palette?: string[];
}

export interface BrandMediaItem {
  name: string;
  url: string;
  type?: string;
}

export interface BrandCompetitor {
  name: string;
  handle?: string;
  notes?: string;
}

export interface AudiencePersona {
  name: string;
  age?: string;
  job?: string;
  goals?: string;
  frustrations?: string;
}

export interface Brand {
  id: string;

  // ── Core Identity ─────────────────────────────
  name: string;
  niche?: string;
  industry?: string;
  website?: string;
  instagramUrl?: string;
  language?: string;
  positioning?: string;
  differentiation?: string;
  brandStory?: string;
  credentials?: string;

  // ── Brand Identity ────────────────────────────
  logoUrl?: string;
  guidelinesUrl?: string;
  colors?: BrandColors;
  campaignUrls?: BrandMediaItem[];
  brandMediaUrls?: BrandMediaItem[];

  // ── Target Audience ───────────────────────────
  targetAudience?: string;
  audienceAge?: string;
  audienceProfession?: string;
  audiencePainPoints?: string;
  audienceLevel?: string;
  audienceLanguage?: string;
  audienceAspirations?: string;
  audiencePersona?: AudiencePersona[];

  // ── Voice & Style ─────────────────────────────
  tone?: string;
  voiceStyle?: string;
  catchphrases?: string;
  forbiddenWords?: string;
  usesSlang?: boolean;
  hookStyle?: string;
  ctaStyle?: string;

  // ── Content Strategy ──────────────────────────
  contentPillars?: string[];
  idealVideoLength?: string;
  hookFormulas?: string;
  bestHooks?: string;
  worstContent?: string;
  competitors?: BrandCompetitor[];

  // ── Instagram ─────────────────────────────────
  igAccountId?: string;
  igUsername?: string;
  igFollowers?: number;
  igTokenExpiresAt?: string;
  igAccessToken?: string;      // never returned to frontend — exists only server-side

  // ── AI Knowledge ──────────────────────────────
  knowledgeJson?: Record<string, unknown>;

  userId?: string;
  createdAt?: string;
  updatedAt?: string;
}

// ── Agent Run ────────────────────────────────────
export interface AgentRun {
  id: string;
  brandId: string;
  userId?: string;
  status: RunStatus;
  mode: string;
  daysAhead: number;
  agentStatuses: Record<string, { status: AgentStatusValue; message?: string }>;
  pptUrl?: string;
  excelUrl?: string;
  postsGenerated: number;
  posts?: Post[];
  designAssets?: DesignAsset[];
  strategyJson?: Record<string, unknown>;
  analystReport?: AnalystReport;
  startedAt?: string;
  completedAt?: string;
  errorMessage?: string;
  createdAt: string;
  updatedAt?: string;
}

// ── Post (Calendar Item) ──────────────────────────
export interface Post {
  id: string;
  agentRunId: string;
  date: string;
  contentType: ContentType;
  topic: string;
  caption?: string;
  hashtags?: string[];
  status: "draft" | "approved" | "rejected" | "scheduled" | "published";
  scheduledAt?: string;
  publishedAt?: string;
  igMediaId?: string;
  createdAt?: string;
}

// ── Design Asset ─────────────────────────────────
export interface DesignAsset {
  id: string;
  agentRunId: string;
  imageUrl: string;
  contentType: ContentType | string;
  topic?: string;
  prompt?: string;
  date?: string;
  createdAt?: string;
}

// ── Analyst Report ────────────────────────────────
export interface PostMetric {
  id: string;
  caption?: string;
  likes?: number;
  comments?: number;
  shares?: number;
  reach?: number;
  impressions?: number;
  engagementRate?: number;
}

export interface AnalystReport {
  followerCount?: number;
  avgReach?: number;
  avgEngagementRate?: number;
  postsAnalyzed?: number;
  followerGrowthPct?: number;
  reachGrowthPct?: number;
  engagementGrowthPct?: number;
  topPosts?: PostMetric[];
  note?: string;
  [key: string]: unknown;
}

// ── Brand Learning Log ────────────────────────────
export interface BrandLearningLog {
  id: string;
  brandId: string;
  trigger: string;
  summary?: string;
  createdAt: string;
}

// ── SSE Event ────────────────────────────────────
export interface SSEEvent {
  type:
    | "agent_started"
    | "agent_progress"
    | "agent_completed"
    | "agent_failed"
    | "pipeline_complete"
    | "pipeline_failed"
    | "log"
    | "error";
  agentKey?: string;
  message?: string;
  timestamp?: string;
  data?: Record<string, unknown>;
}

// ── App Store State ────────────────────────────────
export interface AppStore {
  activeBrandId: string | null;
  brands: Brand[];
  activeRun: AgentRun | null;
  sseEvents: SSEEvent[];
  setActiveBrand: (id: string | null) => void;
  setBrands: (brands: Brand[]) => void;
  setActiveRun: (run: AgentRun | null) => void;
  addSSEEvent: (event: SSEEvent) => void;
  clearSSEEvents: () => void;
}
