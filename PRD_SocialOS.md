# Product Requirements Document (PRD)
## SocialOS — AI-Powered Social Media Operating System

**Version:** 1.0  
**Date:** May 2026  
**Author:** Product Team  
**Status:** Draft for Review

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Product Vision & Goals](#product-vision--goals)
4. [User Personas](#user-personas)
5. [Product Scope](#product-scope)
6. [Feature Requirements](#feature-requirements)
   - 6.1 Brand Hub
   - 6.2 Agent 1 — Brand Manager
   - 6.3 Agent 2 — Analyst
   - 6.4 Agent 3 — Growth Planner (+ Sub-Agents)
   - 6.5 Agent 4 — Strategist
   - 6.6 Agent 5 — Copywriter
   - 6.7 Self-Learning Loop
   - 6.8 Premium Glass Dashboard
7. [Non-Functional Requirements](#non-functional-requirements)
8. [Out of Scope (v1)](#out-of-scope-v1)
9. [Success Metrics (KPIs)](#success-metrics-kpis)
10. [Roadmap](#roadmap)
11. [Open Questions](#open-questions)

---

## 1. Executive Summary

SocialOS is a multi-agent AI platform built for social media marketers, brand managers, and agencies. It ingests deep brand knowledge and uses a chain of specialized AI agents — Analyst, Growth Planner, Strategist, and Copywriter — to produce research-backed, brand-specific content calendars and scripts that self-improve every 15 days based on real performance data from the Meta API.

Unlike generic AI content tools, SocialOS learns the brand first, then acts. Every output is grounded in real Instagram analytics, live niche research, and competitor intelligence — never generic, always on-brand.

---

## 2. Problem Statement

### Current Pain Points

**For Marketing Agencies & Brand Managers:**
- Content creation is time-consuming and repetitive
- Strategy and execution are siloed — research rarely informs copy
- AI tools produce generic content that doesn't match brand voice or niche context
- Post-performance data is rarely fed back into the planning cycle
- Managing multiple brands across tools is fragmented and manual

**Specific Gaps in the Market:**
- No single tool combines brand intelligence + Instagram analytics + content strategy + copywriting in one pipeline
- Existing scheduling tools (Buffer, Hootsuite) don't generate content — they just post it
- AI writers (ChatGPT, Jasper) don't connect to real analytics or do competitor research automatically
- The feedback loop between "what we posted" and "what we should post next" is entirely manual today

### The Opportunity
A tool that **learns a brand deeply**, pulls **real performance data**, researches **live trends**, and delivers a **complete, ready-to-execute content system** — and then **gets smarter every 15 days on its own** — does not exist yet.

---

## 3. Product Vision & Goals

### Vision Statement
> "SocialOS is the AI brain behind every great social media brand — it learns your brand, reads the market, and builds the strategy, calendar, and scripts so your team only has to create and post."

### Core Goals

| Goal | Description |
|------|-------------|
| Brand-first AI | Every agent action is grounded in the specific brand's details, not generic templates |
| Real data, not assumptions | Instagram analytics via Meta API feed every strategy decision |
| Full pipeline automation | From research → strategy → calendar → script, the entire pipeline runs in one flow |
| Self-improving system | Every 15-day cycle makes the system smarter — it learns what works for that specific brand |
| Multi-brand support | Agencies can manage unlimited brands from one workspace |

---

## 4. User Personas

### Persona 1: Riya — Social Media Manager at a D2C Brand
- **Age:** 26  
- **Team Size:** Solo + 1 designer
- **Problem:** Spends 3 days per month just planning content. Strategy is based on gut feeling, not data.
- **Need:** A tool that tells her exactly what to post, when, and gives her the script — based on what's actually working for her brand.
- **Usage:** Runs the full agent pipeline once a month, reviews the PPT strategy deck, exports the content calendar, and hands scripts to the designer.

### Persona 2: Arjun — Founder of a 10-Brand Marketing Agency
- **Age:** 32  
- **Team Size:** 8 people managing 10 brands
- **Problem:** Every brand needs a unique strategy. His team wastes 40% of their time on research and planning, not execution.
- **Need:** Manage all brands from one place. Let AI do the research and planning. His team just executes.
- **Usage:** Adds all 10 brands into SocialOS. Each brand runs its own agent pipeline. He reviews the growth planner PPTs in weekly client meetings.

### Persona 3: Neha — Freelance Content Strategist
- **Age:** 29  
- **Clients:** 4–6 brands simultaneously
- **Problem:** Juggling research, strategy, and content for multiple clients is overwhelming. Clients want data-backed pitches.
- **Need:** A system that generates professional strategy decks and detailed content plans she can present to clients.
- **Usage:** Uses the Growth Planner PPT as client pitch material. Uses the Copywriter's detailed Excel to brief her video editor and designer.

---

## 5. Product Scope

### In Scope for v1.0

- Multi-brand workspace with full brand profile management
- Campaign tracking with file upload proof
- **6 AI Agents** running in sequence: Brand Manager → Analyst → Growth Planner → Strategist → Copywriter → **Designer**
- Sub-agents inside Growth Planner: Research Agent + Competitor Tracking Agent
- 15-day and 30-day content calendar modes
- PPT output from Growth Planner (brand-colored, with logo)
- Excel content calendar output from Strategist
- Full detailed script Excel output from Copywriter
- **AI-generated carousel slides and static graphic PNGs from Designer Agent (DALL-E 3 + brand overlay)**
- 15-day automated refresh and self-learning loop
- Premium glass morphism dashboard with 5-hour analytics refresh
- Meta API (Instagram Graph API) integration

### Out of Scope for v1.0
- Direct post scheduling/publishing
- TikTok, YouTube, LinkedIn integration (v2)
- Real-time collaboration (v2)
- White-label / client portal (v2)

---

## 6. Feature Requirements

---

### 6.1 Brand Hub

The central repository where all brand intelligence lives. This is the single source of truth that all agents read from.

**FR-001: Multi-Brand Workspace**
- Users can create unlimited brand profiles within one account
- Each brand is a self-contained workspace (separate agents, analytics, content calendars)
- Brand switcher available from the top navigation bar
- Brands are listed with logo, name, and last-activity timestamp on the main dashboard

**FR-002: Brand Profile Fields**

Each brand profile must capture the following information:

| Field | Type | Description |
|-------|------|-------------|
| Brand Name | Text | Primary brand identifier |
| Brand Website | URL | Main website for context crawling |
| Instagram Handle | Text | For Meta API connection |
| Brand Logo | File Upload | Used in PPT generation |
| Brand Colors | Color Picker (HEX) | Primary, Secondary, Accent colors — used in PPT |
| Brand Voice | Multi-select + Custom | E.g., Witty, Professional, Inspirational, Raw |
| Brand Guidelines | File Upload (PDF/Doc) | Agent reads this before generating content |
| Industry / Niche | Dropdown + Custom | E.g., D2C Skincare, SaaS, Fashion, Food & Beverage |
| Target Audience | Long Text | Demographics, psychographics, pain points |
| Audience Persona | File Upload or Text | Detailed persona description |
| Competitors | Repeatable Field | Instagram handles of 3–5 competitors |
| Products / Services | Repeatable Field | Name, description, USP for each |
| Business Type | Radio | B2C / B2B / D2C / Creator / Agency |
| Market | Text | E.g., "India — Tier 1 cities, 22–35 age group" |
| Current Followers | Number | Used as baseline for goal setting |
| Follower Goal | Number | Target followers for the planning period |

**FR-003: Campaign Manager within Brand Profile**
- Users can add active campaigns to a brand profile
- Each campaign entry has:
  - Campaign Name / Theme (text)
  - Active Pillars (multi-select tags, e.g., "Product Showcase", "Influencer", "Education")
  - Campaign Start / End Date
  - Proof Uploads: drag-and-drop upload of reels, graphics, carousels (MP4, JPG, PNG, GIF)
  - Status: Active / Paused / Completed
- Agents read active campaigns to understand current brand focus

---

### 6.2 Agent 1 — Brand Manager

**Purpose:** Ingest, parse, and deeply understand all brand details before any other agent runs. Acts as the persistent brand memory layer.

**FR-010: Brand Knowledge Ingestion**
- On first setup (or whenever brand details are updated), Brand Manager runs a full read and parse of all Brand Hub data
- Crawls the brand website to extract: About page, product descriptions, tone of writing, any published content
- Reads uploaded brand guidelines PDF
- Summarizes brand DNA into a structured internal schema used by all downstream agents
- User sees a "Brand Knowledge Score" (0–100%) indicating how completely the brand profile is filled

**FR-011: Brand Knowledge Refresh**
- Any time brand details are updated, user can trigger "Re-learn Brand"
- Automatically triggered when a new campaign is added

**FR-012: Brand Summary View**
- After ingestion, user can view a "Brand Summary Card" showing what the AI understands about the brand
- Editable correction layer — user can override any AI interpretation

---

### 6.3 Agent 2 — Analyst

**Purpose:** Connect to Instagram via Meta API and produce a deep performance analysis of the brand's Instagram account. This data powers all downstream strategy.

**FR-020: Meta API Integration**
- OAuth 2.0 connection to Instagram Business Account via Meta Graph API
- Required permissions: `instagram_basic`, `instagram_manage_insights`, `pages_read_engagement`
- Connection status shown in dashboard (Connected / Disconnected / Token Expired)
- Token refresh handled automatically

**FR-021: Data Collection Scope**
The Analyst pulls and stores the following data points:

| Metric | Granularity |
|--------|-------------|
| Total Followers | Current + growth trend |
| Post Count | Reels / Carousels / Graphics / Stories — broken down |
| Reach per post | Per post + rolling average |
| Impressions per post | Per post + rolling average |
| Engagement Rate | Per post + rolling average |
| Likes, Comments, Shares, Saves | Per post |
| Comments Content | Fetched and sentiment-analysed |
| Top performing posts | Ranked by reach and engagement |
| Worst performing posts | Ranked by lowest reach and engagement |
| Topic / Theme tagging | AI-tagged based on caption + visual brief |
| Content type performance | Reel vs Carousel vs Graphic vs Story comparison |
| Posting frequency | Posts per week actual vs optimal |
| Best posting times | Heatmap of engagement by hour/day |
| Hashtag performance | Which hashtags drove the most reach |
| Profile visits & link clicks | If available via API |

**FR-022: Analysis Output**
- Analyst produces a structured JSON report + human-readable summary
- Summary includes:
  - "What's Working": Top 3 content themes with data
  - "What's Not Working": Bottom 3 themes with data
  - "Hidden Gems": Posts with low reach but high saves/comments (underrated content types)
  - "Audience Signal": What the comments reveal about audience needs
- This report is passed directly to Growth Planner

**FR-023: Analyst Trigger Schedule**
- Analyst runs automatically every 15 days (configurable, min: 7 days)
- Can also be triggered manually by user at any time
- Each run stores a timestamped snapshot (history preserved for trend tracking over time)

---

### 6.4 Agent 3 — Growth Planner (+ Sub-Agents)

**Purpose:** Using brand knowledge + analyst data + live market research, define the content strategy for the next 15 or 30 days and deliver it as a professional PowerPoint presentation.

**FR-030: Planning Period Selection**
- User selects planning period before Growth Planner runs:
  - Dropdown options: **15 Days** / **30 Days**
- User can set the follower goal for the period (e.g., "Gain 200 followers organically")

**FR-031: Sub-Agent — Research Agent**
- The Research Agent runs before Growth Planner creates the strategy
- Searches for trending topics and content ideas in the brand's niche
- **Platforms searched (user-selectable, minimum 1, maximum 6):**
  - Google Trends
  - Reddit (subreddits relevant to niche)
  - Quora
  - Instagram (via scraping — trending reels in niche hashtags)
  - News API (industry news sources)
  - LinkedIn (for B2B brands)
- For each platform, the agent extracts:
  - Top trending topics in the niche (last 30 days)
  - Trending content formats (what style of posts are getting traction)
  - Common audience questions and pain points
  - Seasonal or current-event hooks relevant to the brand
- Output: Research Brief — ranked list of 20–30 content opportunities with source citations

**FR-032: Sub-Agent — Competitor Tracking**
- Reads competitor Instagram handles from Brand Hub
- For each competitor (up to 5):
  - Fetches recent posts (last 30 days) via public scraping
  - Identifies their top performing content themes
  - Tracks posting frequency
  - Identifies content gaps (what they're NOT covering that the brand could own)
- Output: Competitor Intelligence Brief — summary of competitive landscape with gaps and opportunities

**FR-033: Growth Planner Core — Pillar & Topic Definition**
- Using Analyst data + Research Brief + Competitor Intelligence Brief, Growth Planner defines:
  - **Content Pillars** for the planning period (3–6 pillars)
    - e.g., "Product Showcase", "Behind the Scenes", "Educational", "Influencer Collab", "Trend Hijack"
  - **Target breakdown** per pillar (what % of content should be each pillar)
  - **Topic ideas** under each pillar (5–10 specific topic ideas per pillar)
  - **Rationale** for why each pillar is recommended (data-backed)
- Growth Planner explicitly drops pillars that the Analyst identified as underperforming

**FR-034: Growth Planner PPT Output**

The Growth Planner generates a fully designed PowerPoint (`.pptx`) using the brand's colors and logo.

**Slide Structure:**

| Slide | Content |
|-------|---------|
| 1 | Cover — Brand Name, Logo, Planning Period, Date |
| 2 | About the Brand — What the brand is, industry, positioning |
| 3–4 | Instagram Current State — Followers, reach, engagement rate, post breakdown (visual charts) |
| 5 | What's Working — Top performing themes with data (charts + examples) |
| 6 | What's Not Working — Underperforming themes with data |
| 7 | Market Research Summary — Top trends from Research Agent, with sources |
| 8 | Competitor Landscape — What competitors are doing, key gaps identified |
| 9 | Growth Target — Current state vs target, organic growth plan |
| 10–11 | Content Pillars — Defined pillars for this period with rationale |
| 12–13 | Content Ideas — Topic breakdown per pillar |
| 14 | Recommended Posting Schedule — Frequency, best times |
| 15 | Next Steps & Handoff |

- PPT uses brand's primary and secondary colors for slide backgrounds and accents
- Brand logo appears on every slide (header or footer)
- Charts are data-driven (actual numbers from Analyst)
- PPT is downloadable as `.pptx` and viewable in-app

---

### 6.5 Agent 4 — Strategist

**Purpose:** Convert the Growth Planner's pillars and topics into a detailed, day-by-day content calendar in Excel format.

**FR-040: Calendar Mode**
- Matches the Growth Planner's selected period (15 or 30 days)
- Each day that has content assigned gets a row (not every day needs a post)
- Strategist decides posting frequency based on Analyst's recommended frequency + platform best practices

**FR-041: Content Type Decision**
- Strategist independently determines the best content format for each topic:
  - **Reel** — for trend-based, high-reach potential topics
  - **Carousel** — for educational, detailed, or list-based topics
  - **Graphic / Static Post** — for quotes, announcements, product shots
  - **Story** — for polls, Q&A, behind-the-scenes, time-sensitive content
- Decision is AI-driven based on: topic type, what has worked historically (Analyst data), and platform algorithm best practices
- NOT a fixed ratio — the AI decides based on what's right for each topic

**FR-042: Strategist Excel Output**

Excel file with the following columns:

| Column | Description |
|--------|-------------|
| Day # | 1–15 or 1–30 |
| Date | Specific calendar date |
| Pillar | Which content pillar this belongs to |
| Topic | The specific topic/idea |
| Content Type | Reel / Carousel / Graphic / Story |
| Platform | Instagram (+ others if added later) |
| Why This Topic | One-line rationale (data or trend-backed) |
| Visual Direction | High-level visual concept |
| Priority | High / Medium / Low |

- Excel is styled with brand colors (header row, alternating row colors)
- Downloadable as `.xlsx`

---

### 6.6 Agent 5 — Copywriter

**Purpose:** Take the Strategist's content calendar and expand every single post into a fully detailed, ready-to-execute content brief.

**FR-050: Full Content Brief Per Post**

For every post in the Strategist's calendar, the Copywriter produces:

| Field | Description |
|-------|-------------|
| Date | Posting date |
| Time | Recommended posting time (based on Analyst's best-time data) |
| Platform | Instagram |
| Content Type | Reel / Carousel / Graphic / Story |
| Topic | From Strategist |
| Hook | Opening line/frame — must stop the scroll (3 variations provided) |
| Script | Full script for Reel (with scene directions) OR slide-by-slide content for Carousel |
| Caption | Full caption (short + long versions) |
| CTA | Call to action (comment, share, follow, click link) |
| Hashtags | 20–30 relevant hashtags (mix of niche, medium, and broad) |
| SEO Keywords | 3–5 keywords for caption SEO |
| Visual Brief | Detailed description of what the visual should look like |
| Audio / Music | Trending audio suggestion (for Reels) |
| Story Sequence | If Story: slide-by-slide breakdown (poll text, question text, etc.) |
| Carousel Slide Breakdown | Slide 1: Hook, Slide 2–N: Content, Last Slide: CTA |

**FR-051: Brand Voice Compliance**
- Every piece of copy is written in the brand's defined voice and tone (pulled from Brand Hub)
- Copywriter references the brand guidelines before generating any copy
- Copy is NOT generic — it references the brand's specific products, audience, and niche context

**FR-052: Copywriter Excel Output**
- Same structure as Strategist Excel, with all the above fields added as additional columns
- Color-coded by content type (Reel = blue, Carousel = green, Graphic = purple, Story = orange)
- Each row is self-contained — team member can execute any post independently from the Excel

---

### 6.6b Agent 6 — Designer

**Purpose:** Extract all posts that require visual design (Carousels and Static Graphics) from the Copywriter's output, then automatically generate ready-to-use visual assets using AI image generation — all styled with the brand's colors, logo, and visual identity.

**FR-055: Post Extraction**
- Designer Agent reads Copywriter's full output Excel
- Filters all posts where Content Type = Carousel OR Graphic
- Skips Reels (script-only output) and Stories (platform-native design)

**FR-056: Carousel Generation**
- For each carousel post:
  - Reads the full slide-by-slide breakdown from Copywriter output
  - Generates each slide individually as a 1080×1080px image
  - **Slide 1 (Hook):** Bold headline + high-contrast background using brand primary color
  - **Slides 2–N (Content):** Visual supporting the slide's key point + text overlay from Copywriter brief
  - **Last Slide (CTA):** Clean brand slide with CTA text + brand logo + Instagram handle
  - All slides maintain visual consistency (same color palette, font style, corner radius)
- Output: Individual PNG files per slide + combined ZIP download

**FR-057: Static Graphic Generation**
- For each graphic post:
  - Reads the visual brief from Copywriter output
  - Identifies graphic type: product showcase / quote / announcement / educational / promotional
  - Generates base visual via DALL-E 3 or Ideogram API (Ideogram preferred for text-heavy graphics)
  - Post-processing via Pillow: applies brand color overlay, adds logo watermark (8% image width, corner placement), adds text layers
  - Output: 1080×1080px PNG (feed format)

**FR-058: Brand Identity Application**
- All generated assets automatically use:
  - Brand primary, secondary, and accent colors (from Brand Hub)
  - Brand logo (uploaded in Brand Hub) — applied as watermark on each asset
  - Visual style descriptor from brand voice (e.g., "clean minimal" / "bold vibrant" / "editorial dark") — injected into image generation prompt
- Ensures no off-brand visuals are generated

**FR-059: Designer Agent Review Screen**
- After generation, all designs appear in a review grid (3 columns)
- For each design card: thumbnail preview, post date, topic title, content type badge
- Carousel cards: swipeable slide preview within the card
- Per-design actions: Approve, Download PNG/ZIP, Regenerate (with ability to edit the prompt before regeneration)
- Bulk action: "Approve All" marks all designs as ready
- Approved designs show a "Design Ready" green badge in the content calendar

**FR-060: Output Files**
- Individual PNG files: `{brand}_{date}_{topic}_{slide_n}.png`
- Carousel ZIP: `{brand}_{date}_{topic}_carousel.zip` (all slides in one file)
- All files stored in S3, accessible via signed download URLs (valid 7 days)
- Design status logged in DB per post — content calendar shows design readiness

**Image Generation API Selection:**

| Graphic Type | Preferred API | Reason |
|---|---|---|
| Lifestyle / product photography | DALL-E 3 | Best photorealistic quality |
| Quote / text-first graphics | Ideogram | Best text rendering in images |
| Abstract / artistic backgrounds | Stability AI SDXL | Most stylistic control |
| Template-based brand graphics | Canva API (v2 option) | Guaranteed on-brand consistency |

---

### 6.7 Self-Learning Loop

This is the core intelligence engine of SocialOS — what makes it get smarter over time.

**FR-060: 15-Day Refresh Trigger**
- Every 15 days (from the moment the first content calendar was generated), the system automatically:
  1. **Triggers Analyst** — pulls fresh Instagram data for the past 15 days
  2. **Generates Performance Report** — compares planned content vs actual posts and their performance
  3. **Sends to Growth Planner** — Analyst data flows automatically to Growth Planner
  4. **Growth Planner Recalibrates** — redefines pillars, drops what isn't working, doubles down on what is
  5. **Generates new Strategy + Copywriter outputs** — fresh 15-day plan ready for review

**FR-061: Performance Report (at each 15-day refresh)**
- Which topics performed best vs expectations
- Which content types drove most engagement
- Which hashtags drove most reach
- Follower growth during the period (vs goal)
- Content type breakdown (% posted vs % planned)
- Engagement rate trend (improving / declining / stable)

**FR-062: Learning Memory**
- The system maintains a "Brand Learning Log" — a persistent record of:
  - Every 15-day cycle's top performers and bottom performers
  - Pillar performance over time
  - Audience growth trajectory
- Growth Planner reads the full learning log before generating new strategy (not just the latest 15 days — it learns cumulatively)

**FR-063: User Notification**
- When the 15-day refresh completes, user receives in-app notification + email
- Summary card shows: "Here's what changed since last cycle" with key metrics
- User can approve the new plan or request a regeneration with different parameters

---

### 6.8 Premium Glass Dashboard

**Purpose:** The central control center — one screen that shows everything happening across all brands and agents.

**FR-070: Dashboard Panels**

| Panel | Content |
|-------|---------|
| Brand Switcher | Dropdown to switch between all brand workspaces |
| Analytics Overview | Followers, Reach, Engagement Rate — current period vs previous period |
| Agent Status | Which agents have run, when, and their status (Ready / Running / Needs Review) |
| Content Calendar Preview | Mini calendar view of upcoming scheduled posts |
| Top Performing Post | Thumbnail + metrics from best post in current period |
| Research Trends | Top 3 trending topics from Research Agent (live) |
| Next Actions | Cards showing what needs the user's attention (e.g., "Review new content calendar") |
| Refresh Countdown | Time until next 15-day auto-refresh |

**FR-071: Analytics Refresh Rate**
- Dashboard analytics refresh every 5 hours automatically
- User can manually trigger a refresh at any time
- Refresh status shown with timestamp ("Last updated: 2 hours ago")

**FR-072: Design**
- Glass morphism aesthetic — frosted glass panels, subtle blur backgrounds
- Brand color theming — dashboard accent colors match the active brand's colors
- Dark mode and light mode support
- Fully responsive (desktop-first, tablet-compatible)

---

## 7. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| Performance | Agent pipeline (full run, all 5 agents) completes in under 8 minutes |
| Reliability | 99.5% uptime SLA; 15-day refresh never misses its trigger |
| Security | All brand data encrypted at rest (AES-256) and in transit (TLS 1.3) |
| Meta API Compliance | Full compliance with Meta's Platform Terms; no data stored beyond permitted scope |
| Scalability | System must support 100+ brands per account without degradation |
| Data Retention | Instagram analytics snapshots retained for 12 months |
| File Storage | Uploaded files (brand guidelines, campaign proofs) stored securely; max 500MB per brand |
| Export | All exports (PPT, Excel) generated within 60 seconds of request |
| Audit Log | All agent runs logged with timestamps, inputs, and outputs for user review |

---

## 8. Out of Scope (v1)

The following features are explicitly excluded from v1.0 to maintain focus:

- **Direct publishing / scheduling** — SocialOS generates content, not posts it. User exports and posts manually (or via existing tools).
- **TikTok, YouTube, LinkedIn, Twitter** — v1 is Instagram-only via Meta API
- **Real-time team collaboration** — v1 is single-user per brand; multi-user workspace is v2
- **White-label / client portal** — agency clients get PPT and Excel exports; no client login in v1
- **Video / Reel generation** — SocialOS writes the script; it does not generate the video
- **Graphic generation** — SocialOS provides the visual brief; it does not generate the graphic (though this is planned for v2 via image generation APIs)
- **Paid ads management** — organic content only in v1

---

## 9. Success Metrics (KPIs)

### Product Health Metrics
| Metric | Target at 3 Months |
|--------|-------------------|
| Monthly Active Brands (per user) | > 3 brands actively using the tool |
| Agent Pipeline Completion Rate | > 85% of started pipelines complete fully |
| 15-Day Refresh Retention | > 70% of brands still active after 3 refresh cycles |
| Content Calendar Download Rate | > 90% of completed strategist runs result in Excel download |
| PPT Download Rate | > 85% of completed growth planner runs result in PPT download |

### User Outcome Metrics (tracked via survey / optional API connection)
| Metric | Target |
|--------|--------|
| Avg Engagement Rate Improvement | +15% after 3 cycles |
| Avg Follower Growth vs Goal Achievement | 60%+ users hit their follower goal in each cycle |
| Time Saved per Brand per Month | >5 hours reported saved on research + strategy + copywriting |

---

## 10. Roadmap

### v1.0 — Foundation (Months 1–3)
- Brand Hub (multi-brand, unlimited brands)
- All 5 agents running in sequence
- Meta API integration (Analyst)
- Research Agent (Google, Reddit, Quora, News API)
- Competitor Tracking Agent
- Growth Planner PPT output
- Strategist + Copywriter Excel output
- 15-day self-learning loop
- Glass dashboard

### v1.5 — Enhancement (Months 4–6)
- AI Graphic Brief Generator (generates Canva-ready design briefs)
- More research platforms (LinkedIn, YouTube trending)
- Bulk export (all brands' calendars in one download)
- Posting time optimizer (A/B test recommendations)
- Webhook for direct Notion/Trello/Asana calendar sync

### v2.0 — Scale (Months 7–12)
- Multi-user workspaces with role-based access
- Client portal (read-only brand report view for agency clients)
- TikTok and YouTube integration
- AI-generated script narrations (text-to-voice for Reel scripts)
- Canva/Figma integration for visual brief to design handoff
- White-label option for agencies

---

## 11. Open Questions

| # | Question | Owner | Due |
|---|----------|-------|-----|
| 1 | What is the Meta API rate limit impact on multi-brand accounts? Need to assess if batch processing is needed. | Engineering | Before TRD finalization |
| 2 | Which LLM provider(s) for agent reasoning? GPT-4o, Claude, or hybrid? | Architecture | Sprint 1 |
| 3 | PPT generation: python-pptx (more control) or use Canva API? | Engineering | Sprint 1 |
| 4 | Research Agent scraping: what is the legal/ToS compliance for Instagram public content scraping? | Legal | Before launch |
| 5 | Pricing model: per brand, per user, or flat monthly? | Product / Business | Month 1 |
| 6 | Should the 15-day refresh be opt-in (user approves before new plan is generated) or fully automatic? | Product | Sprint 2 |

---

*Document prepared by: Product Team, SocialOS*  
*Next review: After TRD and Design Doc are complete*  
*Changelog: v1.0 — Initial draft*
