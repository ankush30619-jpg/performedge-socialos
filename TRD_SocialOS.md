# Technical Requirements Document (TRD)
## SocialOS — AI-Powered Social Media Operating System

**Version:** 1.0  
**Date:** May 2026  
**Author:** Engineering Team  
**Status:** Draft

---

## Table of Contents

1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Tech Stack](#tech-stack)
4. [Agent Architecture & Orchestration](#agent-architecture--orchestration)
5. [Data Models](#data-models)
6. [API Integrations](#api-integrations)
7. [Database Design](#database-design)
8. [File Storage & Processing](#file-storage--processing)
9. [Background Jobs & Scheduling](#background-jobs--scheduling)
10. [Security & Compliance](#security--compliance)
11. [Infrastructure & Deployment](#infrastructure--deployment)
12. [Observability & Monitoring](#observability--monitoring)
13. [Performance Requirements](#performance-requirements)
14. [Testing Strategy](#testing-strategy)

---

## 1. System Overview

SocialOS is a multi-agent AI orchestration platform that runs 5 specialized agents in sequence. It integrates with the Meta Graph API for Instagram analytics, multiple web data sources for niche research, and generates structured output files (PPTX, XLSX). A 15-day cron-based self-learning loop automatically re-triggers the agent pipeline.

### Core Technical Challenges
1. **LLM Orchestration** — 5 agents must share context, pass structured data between them, and each must have access to the brand knowledge base
2. **Meta API Rate Limits** — Instagram Graph API has strict rate limits; multi-brand setups need careful request queuing
3. **Research Scraping Compliance** — Web scraping for research must be throttled, use rotating proxies where needed, and respect ToS
4. **File Generation at Scale** — PPTX and XLSX generation must be reliable, templated, and produce brand-consistent output
5. **15-Day Scheduled Refresh** — Must be reliable, retryable, and produce output even if some agents partially fail

---

## 2. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                        │
│  Dashboard │ Brand Hub │ Agent Status │ Preview │ Export         │
└───────────────────────────────┬──────────────────────────────────┘
                                │ REST / WebSocket
┌───────────────────────────────▼──────────────────────────────────┐
│                     API GATEWAY (Node.js / Fastify)              │
│  Auth │ Rate Limiting │ Request Validation │ Response Caching    │
└───┬───────────────┬──────────────────────────────────────────────┘
    │               │
    ▼               ▼
┌──────────┐  ┌────────────────────────────────────────────────────┐
│ Auth     │  │             AGENT ORCHESTRATOR SERVICE              │
│ Service  │  │  (LangGraph / Custom DAG runner on Node.js/Python) │
│(Auth.js) │  │                                                    │
└──────────┘  │  Agent 1: Brand Manager                           │
              │  Agent 2: Analyst                                  │
              │  Agent 3: Growth Planner                           │
              │    ├─ Sub-Agent: Research Agent                    │
              │    └─ Sub-Agent: Competitor Tracker               │
              │  Agent 4: Strategist                               │
              │  Agent 5: Copywriter                               │
              └────────────────────┬───────────────────────────────┘
                                   │
         ┌─────────────────────────┼──────────────────────────┐
         ▼                         ▼                          ▼
┌─────────────────┐   ┌────────────────────────┐  ┌──────────────────┐
│   LLM Gateway   │   │   External APIs        │  │  File Generation │
│ (GPT-4o /       │   │ - Meta Graph API       │  │ - PPTX (python-  │
│  Claude 3.5)    │   │ - News API             │  │   pptx)          │
│                 │   │ - Reddit API           │  │ - XLSX (openpyxl)│
│ Context Window  │   │ - Google Trends        │  │                  │
│ Management      │   │ - Quora Scraper        │  └──────────────────┘
└─────────────────┘   │ - Instagram Scraper    │
                      └────────────────────────┘
         ┌─────────────────────────┬──────────────────────────┐
         ▼                         ▼                          ▼
┌─────────────────┐   ┌────────────────────────┐  ┌──────────────────┐
│  PostgreSQL DB  │   │     Redis Cache        │  │  File Storage    │
│  (Primary DB)   │   │  (Session / Rate       │  │  (S3-compatible) │
│                 │   │   Limit / Job Queue)   │  │                  │
└─────────────────┘   └────────────────────────┘  └──────────────────┘
         ▼
┌─────────────────────────────────────────────┐
│              BullMQ Job Queue               │
│  - Analyst Refresh Jobs (15-day cron)       │
│  - Research Agent Jobs                      │
│  - File Generation Jobs                     │
└─────────────────────────────────────────────┘
```

---

## 3. Tech Stack

### Frontend
| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Framework | Next.js 15 (App Router) | SSR for dashboard performance, built-in API routes |
| UI Library | Tailwind CSS + shadcn/ui | Rapid component development, consistent design system |
| State Management | Zustand + React Query | Lightweight state + server state synchronization |
| Charts | Recharts | Instagram metrics visualization |
| Animations | Framer Motion | Glass morphism UI transitions |
| File Export Trigger | Client-side download via signed S3 URL | PPT and Excel download |
| Real-time Updates | Server-Sent Events (SSE) | Agent progress streaming to UI |

### Backend
| Layer | Technology | Rationale |
|-------|-----------|-----------|
| API Server | Node.js + Fastify | High throughput, low latency REST API |
| Agent Orchestration | Python + LangGraph | LangGraph is purpose-built for multi-agent pipelines with state graphs |
| LLM Provider | OpenAI GPT-4o (primary) + Anthropic Claude 3.5 Sonnet (fallback) | GPT-4o for reasoning; Claude for long-context brand document analysis |
| Async Jobs | BullMQ + Redis | Reliable job queues for agent runs, scheduled refreshes |
| Auth | Auth.js (NextAuth) v5 + JWT | Session management, OAuth (Meta) |

### Data
| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Primary Database | PostgreSQL 16 (via Supabase) | ACID compliance, relational brand data, JSON columns for flexible schema |
| Cache | Redis 7 | Rate limit counters, session store, intermediate agent data |
| Vector Store | Pgvector (PostgreSQL extension) | Brand knowledge embeddings for semantic retrieval by agents |
| File Storage | AWS S3 (or Cloudflare R2) | Brand uploads, generated PPT/Excel, campaign proof files |
| ORM | Prisma | Type-safe DB queries |

### File Generation
| Format | Library | Notes |
|--------|---------|-------|
| PPTX | python-pptx | Full control over slide layouts, brand colors, chart embedding |
| XLSX | openpyxl | Color-coded rows, brand header styling, formula support |
| PDF (optional) | WeasyPrint | If user wants PDF export of PPT summary |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Hosting | Vercel (Frontend) + Railway / Render (Backend + Python workers) |
| CDN | Cloudflare |
| Monitoring | Datadog or Sentry (errors) + PostHog (product analytics) |
| CI/CD | GitHub Actions |
| Secrets Management | Doppler or AWS Secrets Manager |

---

## 4. Agent Architecture & Orchestration

### 4.1 Orchestration Pattern

SocialOS uses a **DAG (Directed Acyclic Graph)** orchestration pattern implemented in LangGraph. Each agent is a node in the graph. Edges define data flow. The graph state object is passed from node to node, accumulating data.

```python
# Simplified LangGraph state definition
class SocialOSState(TypedDict):
    brand_id: str
    brand_profile: BrandProfile          # Set by Brand Manager
    analyst_report: AnalystReport        # Set by Analyst
    research_brief: ResearchBrief        # Set by Research Sub-Agent
    competitor_brief: CompetitorBrief    # Set by Competitor Sub-Agent
    growth_plan: GrowthPlan             # Set by Growth Planner
    ppt_path: str                       # Set by Growth Planner (file path)
    content_calendar: ContentCalendar   # Set by Strategist
    strategy_xlsx_path: str            # Set by Strategist (file path)
    full_content_brief: FullBrief      # Set by Copywriter
    copywriter_xlsx_path: str          # Set by Copywriter (file path)
    planning_period: Literal["15", "30"]
    errors: List[str]
    status: str
```

### 4.2 Agent Node Definitions

#### Agent 1 — Brand Manager Node

```
Input:  brand_id
Output: brand_profile (structured BrandProfile object)

Steps:
1. Fetch brand profile from PostgreSQL
2. Retrieve brand knowledge embeddings from pgvector
3. If brand_knowledge_score < 80%:
   a. Crawl brand website (Playwright headless browser)
   b. Parse brand guidelines PDF (PyPDF2 + LLM extraction)
   c. Generate embeddings (OpenAI text-embedding-3-large)
   d. Store embeddings in pgvector
4. Generate BrandProfile structured object via LLM
5. Return BrandProfile
```

**Context window strategy:** Brand guidelines PDF is chunked into 2000-token segments with 200-token overlap. Relevant chunks are retrieved semantically at each downstream agent step rather than injecting the entire document each time.

#### Agent 2 — Analyst Node

```
Input:  brand_profile (Meta account ID from brand_profile.instagram_handle)
Output: analyst_report

Steps:
1. Authenticate with Meta Graph API (retrieve stored access token from DB)
2. Check token validity; refresh if expired
3. Fetch data (see API Integrations section for full endpoint list)
4. Run sentiment analysis on comments (LLM batch call with structured output)
5. Tag each post by content theme (LLM classification call)
6. Compute aggregated metrics
7. Generate AnalystReport via LLM (structured JSON + human summary)
8. Store report snapshot in DB with timestamp
9. Return analyst_report
```

**Rate limit handling:**  
Meta Graph API allows ~200 calls per hour per token. With multiple brands, requests are batched and queued via BullMQ with a rate-limiting middleware. Each brand's analyst job has a dedicated queue slot.

#### Agent 3 — Growth Planner Node (with Sub-Agent Fan-out)

```
Input:  brand_profile, analyst_report, planning_period, follower_goal
Output: growth_plan, ppt_path

Sub-Agent Fan-out (parallel execution):
  ├── Research Agent → research_brief
  └── Competitor Tracker → competitor_brief

Both sub-agents run in parallel using LangGraph's parallel branch feature.

Main node resumes after both complete:
1. Synthesize: analyst_report + research_brief + competitor_brief
2. Define pillars (LLM reasoning call with chain-of-thought prompt)
3. Validate pillars against historical learning log
4. Generate GrowthPlan structured object
5. Send to PPTX generation service
6. Return growth_plan + ppt_path
```

**Research Sub-Agent Detail:**
```
For each selected platform (parallel requests, max concurrency 3):
  - Google Trends: pytrends library API
  - Reddit: PRAW (Reddit API) — search relevant subreddits
  - Quora: Playwright scraper — search relevant topics
  - Instagram: Apify actor or Playwright — public hashtag search
  - News API: newsapi.org REST API
  - Google News: gnews library

Rate limits respected per platform.
All raw data stored in Redis (TTL: 24 hours) to avoid re-scraping.
LLM synthesizes raw data into research_brief structured object.
```

**Competitor Sub-Agent Detail:**
```
For each competitor handle (max 5):
  - Fetch recent posts via Instagram public data (Apify / Playwright)
  - Extract: post count, top performing posts (estimated), content themes, posting frequency
  - LLM analyzes competitor patterns
  - Identify content gaps (topics covered by competitor but not by brand, or vice versa)
Output: competitor_brief JSON
```

#### Agent 4 — Strategist Node

```
Input:  brand_profile, analyst_report, growth_plan
Output: content_calendar, strategy_xlsx_path

Steps:
1. Read growth_plan pillars and topic ideas
2. For each topic, determine optimal content type (LLM decision with reasoning)
   - Context given to LLM: topic type, analyst's content type performance data, algorithm notes
3. Generate posting schedule (distribute posts across planning period)
   - Use analyst's best-time-to-post data
   - Respect posting frequency recommendation from growth_plan
4. Generate ContentCalendar structured object
5. Send to XLSX generation service (openpyxl)
6. Return content_calendar + strategy_xlsx_path
```

#### Agent 5 — Copywriter Node

```
Input:  brand_profile, analyst_report, content_calendar
Output: full_content_brief, copywriter_xlsx_path

Steps:
1. For each post in content_calendar (sequential, with shared brand context):
   a. Generate hook variations (3 options) — LLM
   b. Generate full script OR carousel breakdown OR graphic brief — LLM
   c. Generate caption (short + long) — LLM
   d. Generate hashtag set (20–30 tags) — LLM + hashtag database lookup
   e. Generate SEO keywords — LLM
   f. Generate visual brief — LLM
2. Compile into FullBrief object
3. Send to XLSX generation service
4. Return full_content_brief + copywriter_xlsx_path

Optimization: Batch all posts for one agent call using structured output with
repeated JSON schema. Avoid N sequential LLM calls (use max_tokens carefully
to fit all posts in one or two large calls).
```

#### Agent 6 — Designer Node

```
Input:  copywriter_output (all posts with content_type = Carousel or Graphic)
        brand_profile (colors, logo_url, brand_voice)
Output: designer_output (PNG URLs per post/slide), design_review_url

Steps:
1. Filter copywriter_output → extract carousel_posts[] and graphic_posts[]
2. For each post, build image_generation_prompt:
   a. Load visual_brief from copywriter output
   b. Inject brand context: colors (HEX), visual style (from brand_voice), industry
   c. Select API: Ideogram for text-heavy, DALL-E 3 for photorealistic, SDXL for artistic
3. Call image generation API (parallel, max 5 concurrent)
4. Post-process each image (Python Pillow):
   a. Download generated image
   b. Apply brand color overlay (blend mode: multiply, 25–35% opacity)
   c. Load brand logo from S3
   d. Resize logo to 8% of image width
   e. Paste logo at bottom-right corner (with 24px padding)
   f. For carousels: add slide number indicator (bottom center)
   g. For text-overlay slides: render Copywriter's text using PIL.ImageFont (Inter Bold)
5. Upload processed PNGs to S3: outputs/{run_id}/designs/
6. For carousels: bundle all slides in ZIP using Python zipfile
7. Store design records in DB (post_id, slide_index, s3_url, status=pending_review)
8. Return designer_output with all URLs
```

**Image Generation Prompt Template:**
```python
# Example prompt construction
def build_design_prompt(visual_brief, brand_profile, slide_context):
    return f"""
    {visual_brief}
    
    Style requirements:
    - Brand aesthetic: {brand_profile['brand_voice_descriptors']}
    - Color palette: primarily {brand_profile['colors']['primary']} and {brand_profile['colors']['secondary']}
    - Industry: {brand_profile['industry']}
    - Format: square 1:1 ratio, social media optimized
    - Quality: professional, high-contrast, Instagram-worthy
    - Do NOT include any text in the image (text will be overlaid separately)
    - Background should complement brand colors
    """
```

**Rate limiting for image generation:**
- DALL-E 3: 5 images/minute (Tier 1), 50 images/minute (Tier 2)
- BullMQ handles queue with rate limiter: max 4 concurrent image gen requests per brand run
- Each full 15-day calendar: typically 5–8 carousel posts × 4–7 slides = 20–56 image calls + 4–6 graphic calls

**Cost estimate per pipeline run (Designer Agent only):**
| Content | Count (avg) | Cost per Image | Total |
|---------|-------------|---------------|-------|
| Carousel slides | 40 slides | $0.06 (DALL-E 3) | $2.40 |
| Static graphics | 5 graphics | $0.06 (DALL-E 3) | $0.30 |
| **Total image gen** | | | **~$2.70 per run** |

---

### 4.3 LLM Prompt Architecture

Each agent uses a layered prompt structure:

```
SYSTEM PROMPT (fixed per agent)
  └── Agent role + capabilities + output format schema

BRAND CONTEXT INJECTION (dynamic, per brand)
  └── BrandProfile summary (compressed, ~500 tokens)
  └── Relevant brand guideline chunks (semantic retrieval, ~800 tokens)
  └── Brand voice examples (sampled from past outputs if available)

TASK PROMPT (dynamic, per run)
  └── Analyst report summary (compressed)
  └── Growth plan context (for agents 4 and 5)
  └── Specific task instruction

OUTPUT SCHEMA (JSON Schema)
  └── Enforced via OpenAI structured outputs (response_format: json_schema)
```

**Context Budget (GPT-4o, 128k context window):**
| Component | Max Tokens |
|-----------|-----------|
| System prompt | 1,000 |
| Brand context | 2,000 |
| Task data | 10,000 |
| Output | 8,000–20,000 |
| Buffer | Remaining |

---

## 5. Data Models

### Brand
```typescript
interface Brand {
  id: string                    // UUID
  workspaceId: string           // Foreign key → Workspace
  name: string
  websiteUrl: string
  instagramHandle: string
  logo: string                  // S3 URL
  brandColors: {
    primary: string             // HEX
    secondary: string           // HEX
    accent: string              // HEX
  }
  brandVoice: string[]          // e.g., ["Witty", "Inspirational"]
  guidelinesFileUrl: string     // S3 URL
  industry: string
  targetAudience: string        // Long text
  businessType: "B2C" | "B2B" | "D2C" | "Creator" | "Agency"
  market: string
  currentFollowers: number
  followerGoal: number
  competitors: string[]         // Instagram handles
  products: ProductEntry[]
  campaigns: Campaign[]
  knowledgeScore: number        // 0–100
  metaAccessToken: string       // Encrypted
  metaAccessTokenExpiry: Date
  createdAt: Date
  updatedAt: Date
}
```

### Campaign
```typescript
interface Campaign {
  id: string
  brandId: string
  name: string
  pillars: string[]             // e.g., ["Product Showcase", "Influencer"]
  startDate: Date
  endDate: Date
  proofFiles: string[]          // S3 URLs
  status: "Active" | "Paused" | "Completed"
  createdAt: Date
}
```

### AgentRun
```typescript
interface AgentRun {
  id: string
  brandId: string
  runType: "Manual" | "Scheduled_15Day"
  planningPeriod: "15" | "30"
  followerGoal: number
  selectedResearchPlatforms: string[]
  status: "Queued" | "Running" | "Completed" | "Failed" | "PartialSuccess"
  startedAt: Date
  completedAt: Date
  outputs: {
    analystReportId: string
    pptUrl: string              // S3 URL
    strategyXlsxUrl: string    // S3 URL
    copywriterXlsxUrl: string  // S3 URL
  }
  errors: string[]
  agentStatuses: {
    brandManager: "Pending" | "Running" | "Done" | "Failed"
    analyst: "Pending" | "Running" | "Done" | "Failed"
    researchAgent: "Pending" | "Running" | "Done" | "Failed"
    competitorTracker: "Pending" | "Running" | "Done" | "Failed"
    growthPlanner: "Pending" | "Running" | "Done" | "Failed"
    strategist: "Pending" | "Running" | "Done" | "Failed"
    copywriter: "Pending" | "Running" | "Done" | "Failed"
  }
}
```

### AnalystReport
```typescript
interface AnalystReport {
  id: string
  brandId: string
  agentRunId: string
  snapshotDate: Date
  metrics: {
    totalFollowers: number
    followerGrowth: number           // Since last snapshot
    totalPostsInPeriod: number
    postBreakdown: {
      reels: number
      carousels: number
      graphics: number
      stories: number
    }
    avgReach: number
    avgImpressions: number
    avgEngagementRate: number        // Percentage
    topPerformingPosts: PostMetric[]
    bottomPerformingPosts: PostMetric[]
    contentTypePerformance: {        // Avg engagement rate per content type
      reels: number
      carousels: number
      graphics: number
      stories: number
    }
    bestPostingTimes: HeatmapData[]  // Hour x Day engagement matrix
    topHashtags: HashtagPerformance[]
  }
  summary: {
    whatsWorking: string[]           // Text descriptions
    whatsNotWorking: string[]
    hiddenGems: string[]
    audienceSignal: string
  }
  rawDataJson: object               // Full API response stored for audit
}
```

### BrandLearningLog
```typescript
interface BrandLearningLog {
  id: string
  brandId: string
  cycleNumber: number              // Increments with each 15-day refresh
  periodStart: Date
  periodEnd: Date
  pillarsUsed: string[]
  topPerformingPillar: string
  bottomPerformingPillar: string
  contentTypeWinner: string
  followerGrowthActual: number
  followerGrowthGoal: number
  goalAchieved: boolean
  keyLearnings: string             // LLM-generated summary of this cycle's learnings
  droppedTopics: string[]          // Topics dropped for next cycle
  carriedForwardTopics: string[]   // Topics to continue in next cycle
  createdAt: Date
}
```

---

## 6. API Integrations

### 6.1 Meta Graph API (Instagram)

**Base URL:** `https://graph.facebook.com/v19.0`  
**Auth:** OAuth 2.0 — User token with `instagram_basic`, `instagram_manage_insights`, `pages_read_engagement`

**Endpoints Used:**

| Endpoint | Purpose | Rate Limit Notes |
|----------|---------|-----------------|
| `GET /{ig-user-id}?fields=followers_count,media_count,name` | Account overview | 200/hr |
| `GET /{ig-user-id}/media?fields=id,media_type,timestamp,like_count,comments_count,reach,impressions,saved,caption` | All posts with metrics | 200/hr |
| `GET /{ig-media-id}/comments?fields=text,timestamp,like_count` | Post comments | 200/hr |
| `GET /{ig-user-id}/insights?metric=reach,impressions,follower_count&period=day` | Account-level insights | 200/hr |
| `GET /{ig-media-id}/insights?metric=reach,impressions,engagement,saved,shares` | Post-level insights | 200/hr |

**Rate Limit Strategy:**
- Each brand's Meta API calls are queued in BullMQ with a `limiter` setting of max 180 requests/hour (leaving 10% buffer)
- For multi-brand accounts, tokens are per-brand (each brand connects their own Instagram account)
- Exponential backoff on 429 responses
- Token expiry monitored; user notified 48 hours before expiry

### 6.2 News API

**Provider:** newsapi.org  
**Endpoint:** `GET https://newsapi.org/v2/everything?q={niche_keywords}&sortBy=relevancy&language=en`  
**Rate Limit:** 1,000 requests/day (paid plan)  
**Caching:** Results cached in Redis for 24 hours per query

### 6.3 Reddit API (PRAW)

**Auth:** OAuth 2.0 app credentials  
**Usage:** Search relevant subreddits for top posts in the past 30 days  
**Subreddit selection:** LLM identifies relevant subreddits based on brand niche  
**Rate Limit:** 60 requests/minute  
**Data extracted:** Post title, upvotes, comments count, flair (topic), top comment

### 6.4 Google Trends

**Library:** `pytrends` (unofficial Python API)  
**Usage:** Get trending search interest for niche keywords  
**Throttling:** Max 1 request every 5 seconds; results cached for 12 hours  
**Data extracted:** Interest over time, related queries, related topics

### 6.5 Quora Scraper

**Method:** Playwright headless browser (since Quora has no public API)  
**Usage:** Search for questions related to brand's niche  
**Data extracted:** Question text, number of answers, follower count, top answers (truncated)  
**Rate limiting:** Max 10 pages per search, 2-second delay between page loads  
**Proxy rotation:** Required to avoid IP bans — use Bright Data or Oxylabs

### 6.6 Instagram Public Content Scraper

**Method:** Apify Instagram Hashtag Scraper actor (ToS-compliant approach)  
**Alternative:** Playwright scraper as backup  
**Usage:** Fetch trending posts under niche-relevant hashtags  
**Data extracted:** Post type, caption snippet, estimated engagement, hashtags used  
**Note:** No private data is accessed; only public post metadata

### 6.7 OpenAI API

**Models Used:**
| Agent | Model | Reason |
|-------|-------|--------|
| Brand Manager | `text-embedding-3-large` | Embedding brand docs for pgvector |
| Brand Manager | `gpt-4o` | Brand DNA extraction from crawled content |
| Analyst | `gpt-4o` | Sentiment analysis, theme tagging, report generation |
| Growth Planner | `gpt-4o` | Pillar definition, strategy synthesis |
| Strategist | `gpt-4o` | Content type decisions, calendar generation |
| Copywriter | `gpt-4o` | Script, caption, hashtag generation |
| Designer | `gpt-4o` (prompt builder) + DALL-E 3 / Ideogram / SDXL | Build image prompts from visual briefs; generate carousel slides and graphic images |

**Structured Output:** All agent outputs use `response_format: { type: "json_schema" }` with strict schemas to ensure parseable, validated JSON.

**Token cost estimate per full pipeline run (one brand):**
| Agent | Estimated Input Tokens | Estimated Output Tokens |
|-------|----------------------|------------------------|
| Brand Manager | 8,000 | 2,000 |
| Analyst | 12,000 | 4,000 |
| Growth Planner | 20,000 | 6,000 |
| Strategist | 15,000 | 5,000 |
| Copywriter | 25,000 | 20,000 |
| Designer (prompt builder LLM only) | 10,000 | 3,000 |
| **Total LLM tokens** | **~90,000** | **~40,000** |

At GPT-4o pricing (~$5/1M input, ~$15/1M output): **~$1.05 LLM cost per full pipeline run**  
Plus image generation: **~$2.70** (Designer Agent, ~45 images at DALL-E 3 pricing)  
**Total per full pipeline run: ~$3.75 per brand**

---

## 7. Database Design

### Schema (PostgreSQL via Prisma)

```sql
-- Core tables (abbreviated for clarity)

CREATE TABLE workspaces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id UUID NOT NULL,
  name TEXT NOT NULL,
  plan TEXT DEFAULT 'free', -- free / pro / agency
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE brands (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  website_url TEXT,
  instagram_handle TEXT,
  logo_url TEXT,
  brand_colors JSONB,            -- { primary, secondary, accent }
  brand_voice TEXT[],
  guidelines_file_url TEXT,
  industry TEXT,
  target_audience TEXT,
  business_type TEXT,
  market TEXT,
  current_followers INTEGER,
  follower_goal INTEGER,
  competitors TEXT[],
  products JSONB,                -- Array of { name, description, usp }
  meta_access_token TEXT,        -- Encrypted at application layer
  meta_token_expiry TIMESTAMPTZ,
  knowledge_score INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  pillars TEXT[],
  start_date DATE,
  end_date DATE,
  proof_file_urls TEXT[],
  status TEXT DEFAULT 'Active',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agent_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
  run_type TEXT NOT NULL,        -- 'Manual' | 'Scheduled_15Day'
  planning_period TEXT NOT NULL, -- '15' | '30'
  follower_goal INTEGER,
  research_platforms TEXT[],
  status TEXT DEFAULT 'Queued',
  agent_statuses JSONB,
  outputs JSONB,                 -- { analystReportId, pptUrl, strategyXlsxUrl, copywriterXlsxUrl }
  errors TEXT[],
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE analyst_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID REFERENCES brands(id),
  agent_run_id UUID REFERENCES agent_runs(id),
  snapshot_date TIMESTAMPTZ DEFAULT NOW(),
  metrics JSONB NOT NULL,
  summary JSONB NOT NULL,
  raw_data_json JSONB
);

CREATE TABLE brand_learning_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID REFERENCES brands(id),
  cycle_number INTEGER NOT NULL,
  period_start DATE,
  period_end DATE,
  pillars_used TEXT[],
  top_performing_pillar TEXT,
  bottom_performing_pillar TEXT,
  content_type_winner TEXT,
  follower_growth_actual INTEGER,
  follower_growth_goal INTEGER,
  goal_achieved BOOLEAN,
  key_learnings TEXT,
  dropped_topics TEXT[],
  carried_forward_topics TEXT[],
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- pgvector for brand knowledge embeddings
CREATE TABLE brand_knowledge_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
  source TEXT,                   -- 'guidelines_pdf' | 'website_crawl' | 'manual'
  chunk_text TEXT NOT NULL,
  embedding vector(3072),        -- text-embedding-3-large dimensions
  token_count INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX brand_knowledge_embedding_idx
  ON brand_knowledge_chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

---

## 8. File Storage & Processing

### S3 Bucket Structure

```
s3://socialos-storage/
  ├── brands/
  │   └── {brand_id}/
  │       ├── logos/
  │       ├── guidelines/
  │       └── campaigns/
  │           └── {campaign_id}/
  │               └── proofs/
  └── outputs/
      └── {agent_run_id}/
          ├── growth_plan.pptx
          ├── strategy_calendar.xlsx
          └── content_brief.xlsx
```

### PPTX Generation Service

**Library:** python-pptx  
**Runs as:** Separate Python microservice called by the Growth Planner agent after the growth_plan object is generated

**Template Engine:**
1. Load base template (blank slide master)
2. Apply brand colors to all slide layouts programmatically
3. Add brand logo to slide master (auto-inherits to all slides)
4. Generate slides from growth_plan structured data
5. Embed chart images (generated with matplotlib using brand colors)
6. Save to temp file → upload to S3 → return signed URL

**Chart Generation for PPTX:**
- Follower growth trend → Line chart (matplotlib)
- Content type performance → Bar chart
- Engagement rate comparison → Bar chart
- Pillar breakdown → Pie chart
- All charts use brand primary color as the main color

### XLSX Generation Service

**Library:** openpyxl  
**Runs as:** Part of Strategist and Copywriter agent code

**Styling:**
- Header row: Brand primary color background, white bold text
- Content rows: Alternating white / very light tint of brand secondary color
- Color-coded "Content Type" column: Reel (blue), Carousel (green), Graphic (purple), Story (orange)
- Auto-sized columns
- Freeze top row for easy scrolling

---

## 9. Background Jobs & Scheduling

### Job Queue Architecture (BullMQ + Redis)

```
Queues:
├── agent-pipeline          # Full pipeline runs (manual + scheduled)
│   └── Priority: High for manual, Normal for scheduled
├── analyst-only            # Analyst-only refresh (15-day trigger)
├── research-sub-agent      # Research Agent jobs (spawned by Growth Planner)
├── competitor-tracker      # Competitor tracking jobs
├── file-generation         # PPTX + XLSX generation jobs
└── meta-api                # Meta API calls (rate-limited queue, 180 req/hr)
```

### 15-Day Scheduled Refresh

```typescript
// BullMQ Cron Job — created per brand when first pipeline completes
const refreshJob = await analytistQueue.add(
  `brand-refresh-${brand.id}`,
  { brandId: brand.id, runType: "Scheduled_15Day" },
  {
    repeat: {
      every: 15 * 24 * 60 * 60 * 1000  // 15 days in ms
    },
    jobId: `scheduled-refresh-${brand.id}`, // Idempotent job ID
    attempts: 3,
    backoff: { type: "exponential", delay: 30000 }
  }
);
```

**Failure handling:**
- If Analyst fails → retry 3 times with exponential backoff → alert user via email + in-app notification
- If Growth Planner fails but Analyst succeeded → partial success stored; user can manually trigger Growth Planner + Strategist + Copywriter
- All agent runs are idempotent — re-running is safe

### Agent Progress Streaming (SSE)

```
Client                          Server
  |                               |
  |-- GET /api/runs/{id}/stream -->|
  |                               |
  |<-- event: agent_started -------|  { agent: "analyst", timestamp }
  |<-- event: agent_progress ------|  { agent: "analyst", step: "fetching_posts", progress: 30 }
  |<-- event: agent_completed -----|  { agent: "analyst", timestamp }
  |<-- event: agent_started -------|  { agent: "growth_planner" }
  |<-- ...                         |
  |<-- event: pipeline_complete ---|  { outputs: { pptUrl, xlsxUrl } }
```

---

## 10. Security & Compliance

### Authentication & Authorization
- All API routes require valid JWT (issued by Auth.js)
- Workspace-level isolation: all DB queries filtered by `workspace_id`
- Brand-level access control: users can only access brands in their workspace
- Meta access tokens stored encrypted (AES-256-GCM) in DB; never exposed to frontend

### Data Encryption
| Data Type | Encryption Method |
|-----------|-----------------|
| Meta access tokens | AES-256-GCM at application layer |
| Data at rest (DB) | PostgreSQL with disk-level encryption (Supabase manages) |
| Data in transit | TLS 1.3 enforced on all connections |
| File uploads (S3) | Server-side encryption (SSE-S3) |

### Meta API Compliance
- Store only permitted data (no private message content, no data not authorized by token scope)
- User can disconnect their Instagram account and delete all stored analytics data at any time
- Data retention: Instagram analytics raw data deleted after 12 months
- No data sold or shared with third parties

### Rate Limiting (API Layer)
- 100 requests/minute per authenticated user
- 10 agent pipeline runs/hour per workspace (to prevent abuse)
- Research Agent: per-platform rate limits enforced in job queue

### OWASP Top 10 Mitigations
- SQL injection: Prisma ORM with parameterized queries
- XSS: Content Security Policy headers, React's default escaping
- CSRF: SameSite cookie + CSRF token on state-changing requests
- File upload security: MIME type validation, file size limits (50MB max per file), virus scanning (ClamAV)
- Secrets: Never in code; all via environment variables / Doppler

---

## 11. Infrastructure & Deployment

### Services Architecture

```
Production:
├── Vercel                        # Next.js frontend + API routes
├── Railway                       # Fastify API server (Node.js)
├── Railway                       # Agent Orchestrator (Python / LangGraph)
├── Railway                       # PPTX Generation Service (Python)
├── Supabase                      # PostgreSQL + pgvector + Auth
├── Upstash Redis                 # BullMQ job queues + caching
└── AWS S3 (or Cloudflare R2)     # File storage
```

### Environment Variables

```bash
# LLM
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Meta API
META_APP_ID=
META_APP_SECRET=

# External APIs
NEWS_API_KEY=
APIFY_API_KEY=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=

# Database
DATABASE_URL=
REDIS_URL=

# Storage
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET=

# Auth
NEXTAUTH_SECRET=
NEXTAUTH_URL=

# Encryption
ENCRYPTION_KEY=                   # AES-256 key for token encryption
```

### CI/CD Pipeline (GitHub Actions)

```yaml
On push to main:
  1. Run linting (ESLint, Ruff for Python)
  2. Run unit tests
  3. Run integration tests (mocked Meta API)
  4. Build Docker images (Python services)
  5. Deploy frontend to Vercel
  6. Deploy backend services to Railway
  7. Run smoke tests on production
  8. Send deployment notification to Slack
```

---

## 12. Observability & Monitoring

### Metrics Tracked
| Metric | Tool | Alert Threshold |
|--------|------|----------------|
| API response time (p95) | Datadog | > 2,000ms |
| Agent pipeline completion rate | Custom (PostHog) | < 80% |
| 15-day refresh job failure | Datadog | Any failure |
| Meta API token expiry | Custom | 48 hours before expiry |
| LLM API errors | Sentry | Any 5xx from OpenAI |
| Queue depth (BullMQ) | Datadog | > 50 pending jobs |
| DB query time (p95) | Datadog / Prisma Pulse | > 500ms |

### Error Tracking
- Sentry integration on both frontend and backend
- Every agent step wrapped in try/catch; errors logged with brand_id, run_id, and step context
- LLM output validation errors logged separately for prompt debugging

### Agent Run Audit Log
- Every agent run stored in DB with full input/output JSON (compressed)
- Retained for 6 months
- User can view run history and download past outputs

---

## 13. Performance Requirements

| Scenario | Target |
|----------|--------|
| Dashboard initial load | < 2 seconds (FCP) |
| Analytics refresh (cached) | < 500ms |
| Full agent pipeline (all 5 agents, 15-day plan) | < 8 minutes |
| PPTX generation | < 60 seconds |
| XLSX generation | < 30 seconds |
| Research Agent (5 platforms) | < 3 minutes |
| Competitor Tracker (5 handles) | < 2 minutes |
| 15-day refresh (Analyst only) | < 5 minutes |
| Signed S3 URL generation | < 200ms |

---

## 14. Testing Strategy

### Unit Tests
- Agent prompt templates (snapshot tests)
- Data model validation (Zod schemas)
- File generation functions (PPTX/XLSX output structure)
- Rate limit middleware logic

### Integration Tests
- Full agent pipeline with mocked LLM responses and mocked Meta API
- BullMQ job scheduling and retry behavior
- S3 upload and signed URL generation

### End-to-End Tests (Playwright)
- Brand profile creation flow
- Agent pipeline trigger and progress monitoring
- PPT and Excel download
- 15-day refresh notification

### Load Testing
- Simulate 50 concurrent brand pipeline runs
- Verify queue depth stays manageable
- Verify Meta API rate limit middleware prevents 429 errors

### LLM Output Quality Testing
- Periodic eval runs using a set of 10 test brands
- Human review of generated PPT and content calendar quality
- Regression checks when prompts are updated

---

*Document prepared by: Engineering Team, SocialOS*  
*Next review: Sprint planning before engineering kickoff*  
*Related docs: PRD_SocialOS.md, DesignDoc_SocialOS.docx, AgentFlow_SocialOS.html*
