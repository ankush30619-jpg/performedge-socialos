"""
Marketing Skills Registry — Framework constants for agent prompts.
Distilled from marketing psychology, copywriting, social, content-strategy,
customer-research, and competitor-profiling methodologies.

LAST_RESEARCHED: 2026-06-02 — see research_2026.md for the audit trail
behind every "_2026" suffixed constant in this file.
"""

# ── Critical instruction prefix — injected at the top of every brain-agent ────
# prompt. Single source of truth for the platform's anti-generic stance.

CRITICAL_INSTRUCTION_PREFIX = """
CRITICAL — read before generating anything:

1. If your output could apply to ANY brand, reject it and rewrite. Every
   piece must contain at least one detail that ONLY this brand, in THIS
   niche, to THIS audience, could say. Use the brand name, the niche
   keyword, or an audience-specific descriptor in every caption / pillar /
   tactic line.

2. Banned phrases (any presence triggers automatic rejection by the
   quality gate): unlock, unleash, elevate, dive into, delve, leverage,
   harness, supercharge, game-changer, revolutionize, seamless, robust,
   embark, navigate the landscape, in today's fast-paced world, look no
   further, in conclusion, when it comes to, the world of, that being
   said, it's important to note, tapestry, testament, realm, foster,
   cutting-edge, ever-evolving, paradigm, take it to the next level,
   the secret sauce, at the end of the day, needle-moving, let's dive in,
   buckle up, multifaceted, comprehensive, holistic, bespoke, journey,
   moreover, furthermore, crucial, transformative, groundbreaking,
   synergy, empower, beacon, innovative, seamlessly.

3. Replace every vague claim ("amazing", "great", "best") with a specific
   number, name, or comparison. No tricolons. No hedge stacks. No
   restating the prompt back as the opening line.
"""

# ── Learned-patterns slot — filled by the manager from brands/<brand>/_lessons.md
# Brain-agent prompts include this constant as a placeholder; the manager
# substitutes in the real lessons content per-run.

LEARNED_PATTERNS_SLOT = """
LEARNED_PATTERNS — patterns the manager extracted from this brand's prior
runs. Treat as hard constraints; they were learned from concrete failures
or successes on previous executions.
{learned_patterns_body}
"""

# ── Marketing Psychology Triggers ────────────────────────────────────────────

PSYCHOLOGY_TRIGGERS = """
PSYCHOLOGY TRIGGERS — apply to every piece of copy:
| Trigger        | When to use                          | Mechanism                              |
|----------------|--------------------------------------|----------------------------------------|
| Curiosity Gap  | Hook line, carousel slide 1          | Open a loop the reader must close     |
| Loss Aversion  | CTA, transformation posts            | "Stop losing X" outperforms "Gain X"  |
| Social Proof   | Results posts, testimonials          | Numbers + names + before/after        |
| Scarcity/FOMO  | Offers, trending topic posts         | Limited window / others already doing  |
| Status         | Aspirational / transformation        | "People who do X are seen as..."      |
| Relatability   | Behind-scenes, story posts           | "You've felt this too" empathy        |
| Authority      | Educational, tips posts              | Data, credentials, specific expertise  |
| Anchoring      | Before/after, comparison posts       | Set high reference before the reveal  |

Hook → Emotional trigger mapping (pick one per post):
- "Most people don't know..." → Curiosity
- "Stop losing..." / "This is costing you..." → Loss Aversion
- "X% of [audience] are doing this wrong..." → Social Proof + Fear
- "Only [specific people] know this..." → Scarcity + Status
- "I used to [pain state]. Now [desired state]." → Relatability + Aspiration
- "If you're serious about [goal], stop [common mistake]." → Loss Aversion + Authority
"""

# ── AIDA Framework for Caption Structure ─────────────────────────────────────

AIDA_STRUCTURE = """
AIDA CAPTION STRUCTURE — required for every caption:
A (Attention)  — First 1-2 lines: pattern interrupt, scroll-stopper, bold claim or question.
I (Interest)   — Lines 3-5: "here's why this matters to you" — specific, relevant insight.
D (Desire)     — Middle section: paint the outcome they want. Use specific numbers, not vague claims.
A (Action)     — Last line: ONE clear CTA with a specific verb. Never two competing asks.

Content-type caption length guide:
- Reel/AI Reel: 80-150 chars (viewer came for video, caption is secondary)
- Carousel: 150-280 chars (support the slide story, don't repeat it)
- Graphic/Static: 100-200 chars (complement the visual hook)
- Story: minimal text only (the frame IS the content)
"""

# ── Hook Formula Library ──────────────────────────────────────────────────────

HOOK_FORMULAS = """
HIGH-CONVERTING HOOK FORMULAS — rotate these across posts, never repeat consecutively:
1. Contrarian    : "Everyone says [X]. They're wrong. Here's why:"
2. Number list   : "[N] things about [niche] nobody talks about:"
3. Curiosity gap : "The [niche] secret that took me [X years] to learn:"
4. Loss frame    : "Stop doing [X] if you care about [outcome]."
5. Social proof  : "[X]% of [audience type] are making this exact mistake:"
6. Before/after  : "I went from [pain state] to [desired state]. Here's how:"
7. Question      : "What would [goal] look like if you fixed [specific problem]?"
8. Bold statement: "[Common belief] is the #1 reason [niche] brands fail."
9. Prediction    : "By [timeframe], [brands/people] that ignore [X] will [consequence]."
10. Direct address: "If you're a [specific audience descriptor], read this first."

3-Second Reel Hook Rules (Reels only):
- First frame MUST show the payoff visually — never start with a talking head greeting
- On-screen text in frame 1 IS the hook — write it before scripting the rest
- Pattern interrupt in seconds 3-5: unexpected visual cut, stat reveal, or POV shift
- Retention loop: give a reason to rewatch (reveal at end that recontextualises the start)
"""

# ── Seven Sweeps Copy Quality Check ──────────────────────────────────────────

SEVEN_SWEEPS = """
COPY QUALITY STANDARDS — every caption must pass all 7:
1. Clarity     : Would a 14-year-old understand this immediately? If not, simplify.
2. Specificity : Replace any vague word (amazing, great, best) with a specific claim or number.
3. Voice       : Does it sound like a real human from this brand, or generic AI? Remove preamble.
4. Hook        : Does the first line make you NEED to read the second? If not, rewrite it.
5. CTA         : Is there exactly ONE clear action ask? Remove all competing asks.
6. Emotion     : Name the feeling the last line creates. Is it the intended trigger?
7. Forbidden   : Check for and remove all AI clichés (unlock, elevate, dive into, leverage, etc.)
"""

# ── JTBD Customer Research Framework ─────────────────────────────────────────

JTBD_FRAMEWORK = """
JOBS TO BE DONE RESEARCH FRAMEWORK — three job layers:

Functional Jobs (literal task):
  Format: "I need to [verb] [object] so that [outcome]"
  Measure: time saved / money earned / problem eliminated / risk avoided

Emotional Jobs (how they want to feel after):
  Current feeling  → Desired feeling
  overwhelmed      → in control
  behind           → ahead of the curve
  embarrassed      → confident
  stuck            → moving forward

Social Jobs (how they want to be perceived):
  "Their peers should see them as: [smart / successful / ahead of the curve]"
  "They fear being seen as: [behind / incompetent / naive / wasteful]"

Trigger Events (what forces the decision to seek a solution):
  The specific moment the status quo became unacceptable.
  Examples: lost a client, saw competitor succeeding, hit a revenue ceiling,
  received negative feedback, failed publicly, reached a deadline.

Pain Point Scoring (for content prioritisation):
  Frequency × Intensity = Priority
  - Frequency : daily (3) > weekly (2) > monthly (1)
  - Intensity : catastrophic (3) > serious (2) > annoying (1)
  - Score 9 = create content immediately; Score 1-2 = low priority

Exact Vocabulary Rule:
  Use the words your audience uses to describe their own problems — not industry jargon.
  If they say "my posts get no likes", write "posts that get no likes" not "low engagement rate".
"""

# ── Content Strategy — Buyer Stage Framework ─────────────────────────────────

BUYER_STAGES = """
CONTENT STRATEGY — BUYER STAGE MAPPING:
Every post must serve one buyer stage. Distribute content across all four:

AWARENESS (≈50% of content):
  Audience: doesn't know they have the problem yet, or just discovered it
  Content: trend reveals, myth-busting, industry insights, "did you know" hooks, POV posts
  Goal: earn the follow — not the sale
  CTA style: "Follow for more", "Save this", "Share with someone who needs it"

CONSIDERATION (≈30% of content):
  Audience: knows the problem, comparing solutions
  Content: how-to tutorials, comparisons, behind-scenes process, case studies, Q&A
  Goal: position brand as the best solution
  CTA style: "DM us X", "Comment your question", "Link in bio for more"

DECISION (≈15% of content):
  Audience: ready to buy / hire / commit
  Content: testimonials, client results, offers, objection handling, direct conversion
  Goal: convert the warm audience
  CTA style: "Book a call", "Apply now", "DM 'START'", "Limited spots"

IMPLEMENTATION (≈5% of content):
  Audience: existing customers — keep engaged, generate referrals
  Content: advanced tips, community spotlights, success amplification, behind-scenes
  Goal: retention + word-of-mouth
  CTA style: "Tag someone you've helped", "Share your result"

ICE Scoring for content ideas (1-10 each):
  Impact    : how much will this move the growth needle?
  Confidence: how sure are we it'll resonate?
  Ease      : how quick to produce?
  Priority  = (Impact × Confidence) / Ease — higher = do first
"""

# ── Competitor Profiling Methodology ─────────────────────────────────────────

COMPETITOR_PROFILING = """
COMPETITOR PROFILING METHODOLOGY — three analysis dimensions:

1. POSITIONING MATRIX (per competitor):
   - Core promise  : what they claim to deliver
   - Proof method  : how they prove it (data / testimonials / authority / results)
   - Target segment: who they're actually talking to
   - Positioning gap: what they're avoiding or missing

2. CONTENT PILLAR ANALYSIS (per competitor):
   - Content type split: educational / promotional / social proof / entertainment %
   - Format lean    : Reels / Carousels / static — which dominates?
   - Overused hooks : signals what's working AND what's now oversaturated
   - Ignored topics : high-value topics they haven't addressed

3. GAP OPPORTUNITY SCORING:
   - Topic gap    : important topic in the niche with low competitive coverage
   - Format gap   : high-performing format competitors aren't using
   - Audience gap : sub-segment of the audience no competitor is serving
   - Tone gap     : emotional register no one occupies
     (e.g., all competitors are corporate → own the "human & honest" lane)

Use these gaps to build differentiation recommendations — not generic advice.
"""

# ── Anti-AI Language — kill the robotic tells ────────────────────────────────

ANTI_AI_LANGUAGE = """
ANTI-AI LANGUAGE RULES — copy that reads as AI-written is an automatic fail.

BANNED words / phrases (never output these or their close cousins):
unlock, unleash, elevate, dive into, delve, leverage, harness, supercharge,
game-changer, game-changing, revolutionize, seamless, robust, embark, navigate
the landscape, in today's fast-paced world, look no further, in conclusion,
when it comes to, the world of, that being said, it's important to note,
tapestry, testament, realm, foster, cutting-edge, ever-evolving, paradigm,
take it to the next level, the secret sauce, at the end of the day, needle-moving,
"✨ unlock the secret ✨", "let's dive in", "buckle up", "spoiler alert".

BANNED structural tells:
- Opening with a definition ("X is the process of...").
- Tricolon padding ("fast, easy, and effective").
- Hedge stacks ("can help to potentially improve").
- Symmetrical "It's not just X, it's Y" unless it earns its place.
- Emoji bullet lists where every line starts with the same emoji.
- Restating the prompt back as the first line.

WRITE LIKE A HUMAN:
- Start in the middle of a thought, the way a person texts.
- Use concrete nouns and real numbers, not adjectives.
- Vary sentence length hard — a 3-word line next to a 20-word line.
- One idea per line. Cut every word that isn't load-bearing.
- If a sentence could appear in ANY brand's post, delete it and write the
  version only THIS brand, in THIS niche, to THIS audience could write.
"""

# ── Direct-Response Ad Script Framework ──────────────────────────────────────

AD_SCRIPT_FRAMEWORK = """
AD-CREATIVE SCRIPT STANDARD — every Reel/video script is a performance ad, not
a narration. It MUST contain all 7 beats, in this order, each doing real work:

1. PATTERN INTERRUPT HOOK (0-2s): a visual or line that breaks the scroll.
   Show the payoff, the conflict, or the result FIRST. Never a greeting, never
   a logo, never "Hi guys". The on-screen text in frame 1 IS the hook.
2. CURIOSITY GAP (2-5s): open a loop the viewer must stay to close
   ("...but here's what nobody tells you").
3. EMOTIONAL TRIGGER (5-10s): name the exact feeling — the frustration, the
   fear of missing out, the relief — in the audience's own words.
4. PRODUCT / PROOF DEMONSTRATION: show the thing working, the process, the
   before→after. Demonstrate, don't claim.
5. SOCIAL PROOF ANGLE: a number, a result, a name, a "12,000 people / 3 years
   / 47 clients" — concrete evidence, never "lots of people love it".
6. CLEAR VALUE PROPOSITION: the single transformation the viewer gets, stated
   in one line. What changes for THEM.
7. STRONG CTA: one action, one verb, friction-free. Match the awareness stage
   (follow/save for cold, DM/link for warm).

SHOT DISCIPLINE:
- Each shot = a distinct visual. If two shots look identical, merge them.
- Write on_screen_text as if the sound is OFF (80% watch muted).
- Pattern interrupt again at the midpoint to re-hook drop-offs.
- End on a loop or a question that recontextualises the opening.

Generate MULTIPLE creative directions (distinct concepts, not reworded copies):
e.g. (a) talking-head POV, (b) faceless screen-record / b-roll, (c) skit /
problem-reenactment. Each direction implies a different shot list.
"""

# ── Conversion Copywriting Frameworks (PAS + Direct Response) ────────────────

CONVERSION_FRAMEWORKS = """
CONVERSION COPY FRAMEWORKS — pick the one that fits the post's job:

PAS (Problem · Agitate · Solve) — best for pain-driven / decision content:
  Problem  — name the specific problem in the reader's exact words.
  Agitate  — make the cost of inaction felt (time lost, money burned, status risk).
  Solve    — present the brand's approach as the relief. One CTA.

AIDA — best for awareness / discovery content (see AIDA_STRUCTURE).

BAB (Before · After · Bridge) — best for transformation / results content:
  Before — the stuck state. After — the desired state. Bridge — how to cross.

DIRECT-RESPONSE PRINCIPLES (apply to all):
  - Specificity beats superlatives: "+312 followers in 14 days" > "huge growth".
  - One reader, one problem, one promise, one CTA per asset.
  - Sell the outcome and the feeling, not the feature.
  - Credibility: every claim needs a proof element or it gets cut.
  - Reduce friction at the CTA: tell them exactly what happens next.
"""

# ── Growth Roadmap + Strategic Thinking (consultant-grade) ───────────────────

GROWTH_ROADMAP_FRAMEWORK = """
GROWTH ROADMAP STANDARD — recommendations are worthless without sequencing,
ownership, and measurement. Structure execution across four horizons:

  QUICK WINS  (1-7 days)   — low effort, fast signal, builds momentum.
  SHORT TERM  (30 days)    — the core engine: cadence, formats, systems.
  MID TERM    (90 days)    — compounding plays: collabs, series, repurposing.
  LONG TERM   (6-12 months)— moats: authority, owned audience, product pull.

Every roadmap item MUST specify:
  action · owner · resources_required · expected_result · kpi · priority(P0/P1/P2)

Every individual recommendation MUST carry:
  why_it_matters · expected_impact · difficulty(low/med/high) ·
  priority_score(1-10) · timeline · implementation_steps · success_metrics

Never give an instruction without the reason, the expected result, and how
success is measured. "Post more" is banned. "Ship 1 founder-POV Reel/day for 14
days using PAS hooks on [specific pain]; success = 3 Reels >5k reach by day 10"
is the standard.
"""

# ── Hook Rotation Engine (anti-repetition, scroll-stop) ──────────────────────

HOOK_ROTATION_ENGINE = """
HOOK ROTATION ENGINE — the hook is the most important part. Each post gets an
ASSIGNED hook category (given per post below). Write the primary hook in that
category. The 3 hook_variations must be 3 DIFFERENT categories — never 3 of the
same shape.

The 20 categories (write a genuinely different opening for each):
Curiosity · Contrarian · Shock · Mistake · Story · Relatable · Problem · FOMO ·
Confession · Comparison · Myth-busting · Secret-revealing · Before/After ·
Question · Challenge · Observation · Customer-review · Social-proof · Emotional ·
Unexpected-fact.

HARD RULES:
- Never reuse an opening sentence structure across posts.
- Never slightly reword a previous hook — write from scratch.
- No two posts may open with the same category (rotation is enforced for you).
- A hook that could be pasted onto any other brand's post is REJECTED.

QUALITY FILTER — discard a hook if ANY is true: sounds AI-written, predictable,
boring, corporate, or a structure already used. Keep only hooks that create
curiosity, trigger emotion, and would actually stop a thumb mid-scroll.

CTA ROTATION — rotate CTA mechanism across posts; never repeat the same CTA type
back-to-back: Curiosity · Urgency · Direct · Community · Soft · Comment · Save ·
Share · DM.

BANNED generic openers (English AND Hinglish) — never output these or close cousins:
"Aaj main aapko batane wala hu", "Kya aap jante hain", "Yeh product bahut accha hai",
"Agar aap bhi…", "Let me tell you", "Did you know", "In this post", "Here's why you
should", and any line that reads like a corporate announcement.
"""

# ── Hinglish Voice (Roman-script Hindi + English) ────────────────────────────

HINGLISH_VOICE = """
HINGLISH MODE — write hooks, captions, voiceovers and CTAs in natural Hinglish
(Hindi + English in Roman script), the way a real creator talks to camera. NOT
pure Hindi, NOT pure English, NOT Devanagari.

Sound like a person, not a brand:
GOOD: "Bhai sach bataun, agar tum abhi bhi ye galti kar rahe ho toh paise waste kar rahe ho."
GOOD: "Ye dekh ke mujhe bhi yakeen nahi hua tha."
BAD : "This product is designed with advanced features." (too corporate / pure English)
BAD : full Devanagari or formal Hindi.

Category openers (Hinglish flavour — reinvent each time, don't copy verbatim):
- Curiosity:   "Bhai ye dekh ke pehle mujhe laga fake hai…"
- Contrarian:  "Sab log ye kar rahe hain… aur isi wajah se fail ho rahe hain."
- Story:       "Kal mere saath kuch aisa hua jo socha bhi nahi tha…"
- Mistake:     "Agar tum ye ek galti kar rahe ho, result kabhi nahi aayega."
- Observation: "Maine ek cheez notice ki hai jo koi nahi bolta…"
- Relatable:   "Kabhi aisa hua hai ki…"
- Shock:       "Ye result sirf 7 din mein aaya."

Tone: natural, conversational, modern, Reels-native. Short punchy lines.
Hashtags and proper nouns stay as-is; the spoken copy is Hinglish.
"""

STRATEGIC_THINKING = """
STRATEGIC PRESSURE-TEST — before finalising any plan, challenge it:
  - What could make this fail? (assumptions, market, algorithm, capacity)
  - What customer behaviour are we assuming, and is it realistic?
  - What is the tradeoff of this path vs the alternative?
  - What are the hard constraints (time, budget, team, content supply)?
  - If the main plan stalls by day 7, what is the backup?

Surface this honestly as: risks · tradeoffs · constraints ·
alternative_approaches · backup_plans. A plan with no stated risk is not a
strategy — it's a wish. Consultant-grade output names what could go wrong and
what to do about it.
"""

# ── Reel Script Framework (50-second emotional arc) ──────────────────────────

REEL_SCRIPT_FRAMEWORK = """
REEL SCRIPT — 50-SECOND EMOTIONAL ARC (mandatory structure for every Reel script):

[0-5s]   HOOK / PATTERN INTERRUPT:
  Show the PAYOFF or CONFLICT first — never a greeting, never a logo.
  The first visual + first words ARE the hook. Make it impossible to scroll past.
  Ask: "Would I stop scrolling for this?"

[5-15s]  CURIOSITY LOOP:
  Open a question the viewer must stay to have answered.
  "Here's the part nobody talks about…" / "And what I found shocked me…"
  Do NOT answer it yet. Let the tension build.

[15-25s] EMOTIONAL CONNECTION:
  Name the exact feeling — frustration, fear of missing out, the relief they want.
  Use 5th-grade vocabulary. Simple sentences. Short bursts.
  If a 12-year-old would not understand it, rewrite it.
  "You know that feeling when…" / "The worst part is…"

[25-35s] REAL-WORLD EXAMPLE / DEMONSTRATION:
  Show the concept working — not describe it, SHOW it.
  Concrete. Specific. One real example beats three vague claims.
  Include a number, a name, a result. "47 people tried this and…"

[35-45s] RE-HOOK / PATTERN INTERRUPT #2:
  Mid-video reset. A surprising fact, a POV shift, or an unexpected reveal
  that re-engages viewers who are drifting. This is the secret to high
  completion rates.

[45-50s] MEMORABLE CLOSE + CTA:
  One line that resonates emotionally AND gives a clear next action.
  "That's why [result]. If you want [outcome], [action]."
  CTA must be friction-free — one verb, obvious next step.

VOICE TEST: Read every line aloud. If any line sounds like it was written
(not spoken), rewrite it. Scripts are SPOKEN, not read.
"""

# ── Script Quality Checklist ──────────────────────────────────────────────────

SCRIPT_QUALITY_CHECKLIST = """
SCRIPT QUALITY GATE — run every script through this before finalizing:

1. LENGTH: Can this be cut by 30% without losing the core value? If yes, cut it.
   Target: under 150 words for 50-second Reel. Under 80 words for 30-second.

2. VOCABULARY: 5th-grade language. Replace every technical/jargon word with the
   simplest equivalent. "Engagement rate" → "likes and comments".
   "Content strategy" → "what to post and when".

3. EVERY SENTENCE EARNS ITS PLACE: Read each sentence and ask "what happens
   if I delete this?" If the script still works, delete it.

4. ROBOTIC TEST: Mark any sentence that sounds like it was typed, not spoken.
   - AI tell: "In today's fast-paced world…" → DELETE
   - AI tell: "This is why it's important to…" → DELETE
   - AI tell: starting with "So," or "Well," or "Now, let's" → DELETE

5. BRAND SPECIFICITY: Replace at least 1 generic reference with the brand's
   exact niche, audience, product name, or unique differentiator. If you can
   swap this brand's name for any other brand and the script still works,
   it's not specific enough — rewrite.

6. HOOK TEST (apply BEFORE writing the rest): Show only the first 2 lines to
   someone. Would they want to know what comes next? If "maybe" — rewrite.
   Must be a "yes" or it fails.
"""

# ── Viral Content Architecture (research-first framework) ────────────────────

VIRAL_CONTENT_ARCHITECTURE = """
VIRAL CONTENT ARCHITECTURE — 5-step research-first process:

STEP 1 — RESEARCH THE TOPIC (use data, not guesses):
  - What's currently trending in this niche? (check Tavily/research agent output)
  - What are the audience's KEY pain points right now? (use competitor_tracker gaps)
  - What format is getting shares/saves this week? (use research_data)
  - What are competitors NOT covering that the audience wants?

STEP 2 — DEFINE PRIMARY MESSAGE (one message per piece):
  Pick ONE: Educate / Entertain / Inspire / Convert / Build authority.
  NEVER try to do two at once. Single-message content outperforms multi-message
  content by 2-3x on completion rate.

STEP 3 — DRAFT THE SCRIPT:
  A: Hook that references the specific audience pain/desire
  B: Content that delivers on the hook's promise — no padding
  C: Conclusion that reinforces the hook + ONE clear action

STEP 4 — PLATFORM OPTIMIZATION:
  - Instagram Reels: fast cuts, on-screen text for muted viewing, vertical 9:16
  - Carousel: each slide must be a complete thought, Slide 1 IS the hook
  - Story: interactive (poll/question), 15s max per frame, no dense text
  - Caption: first line mirrors the hook, do NOT repeat the script

STEP 5 — VISUAL SUGGESTIONS PER SECTION:
  For every script section, specify: what the camera shows, what on-screen text
  appears, and what the pacing/cut style is. Sound-off test: does the visual
  alone communicate the message? If not, add stronger on-screen text.
"""

# ── Performance Scoring Framework (5-dimension quality rubric) ───────────────

PERFORMANCE_SCORING_FRAMEWORK = """
OUTPUT QUALITY SELF-CHECK — score your own output before submitting.
Apply this to EVERY piece of content, strategy, or recommendation:

DIMENSION 1 — SPECIFICITY (1-10):
  Is this specific to THIS brand, niche, audience, and competitive landscape?
  Score 1-4: Could apply to any business in any industry.
  Score 5-7: References the niche but not the specific brand.
  Score 8-10: Names the brand, references their specific audience, competitors,
              or content performance — cannot be copy-pasted to another account.

DIMENSION 2 — EVIDENCE (1-10):
  Does every recommendation cite actual data, research, or competitor findings?
  Score 1-4: Pure assertion. No data cited.
  Score 5-7: References research vaguely ("studies show", "experts say").
  Score 8-10: Cites specific metrics, competitor names, platform data, or
              research findings from the research/competitor agent output.

DIMENSION 3 — BRAND ALIGNMENT (1-10):
  Does the output match the brand's voice, tone, positioning, and audience?
  Score 1-4: Generic corporate tone that contradicts the brand brief.
  Score 8-10: A reader who knows the brand would say "yes, this sounds like them."

DIMENSION 4 — COMPLETENESS (1-10):
  Are all required fields populated with substantive (not placeholder) content?
  Score 1-4: Multiple empty fields or placeholder text ("TBD", "see above").
  Score 8-10: Every field has real, actionable, non-repetitive content.

DIMENSION 5 — ANTI-GENERIC TEST (1-10):
  Would this output still make sense if the brand name was swapped for a
  completely different brand in a different niche?
  Score 1-4: Yes — dangerously generic.
  Score 8-10: No — this is irreplaceable, brand-specific content.

COMPOSITE THRESHOLD: If any single dimension scores < 5, regenerate before
submitting. Target composite ≥ 7.0 for all content-producing agents.
"""

# ══════════════════════════════════════════════════════════════════════════════
# 2026 RESEARCH-DRIVEN UPGRADES — see research_2026.md for the audit trail
# ══════════════════════════════════════════════════════════════════════════════

HOOK_FORMULAS_2026 = """
HOOK FORMULAS — 2026 upgrade (use these in addition to the 10 classic
formulas above). Brain agents should reach for these first; the classic
list is the fallback.

1. Specific-Outcome (highest converter across IG/TikTok/Shorts in 2026):
   "I went from [bad number] to [good number] in [timeframe] using [thing]."

2. POV-Native Reels (strongest Reels-native opener):
   "POV: you just found the [niche] hack that saves you [specific time/money]."

3. Unpopular-Opinion:
   "Unpopular opinion: [contrarian statement most of niche disagrees with]."

4. Compound Hook (stack 2+ triggers — curiosity + social proof, status +
   loss aversion, controversy + authority):
   "[Curiosity opener] + [number-based social proof] + [time-bound stake]."

5. Pattern Interrupt:
   First visual frame violates the niche's normal aesthetic. Unexpected
   movement, contrasting color, or contextual mismatch in the first 0.5s.

Hook hit rates that matter: ≥ 30 % three-second hold = good, ≥ 45 % = top
percentile. If a hook can't credibly hit ≥ 30 % on its niche, replace it.
"""

REEL_HOOK_TIMING_RULES_2026 = """
REEL HOOK TIMING — 2026 algorithm contract for Instagram Reels:

  0.0s    — First visual frame IS the hook. Write the on-screen text BEFORE
            scripting voiceover.
  ≤ 1.0s  — Verbal/conceptual hook lands. No greetings, no "hey guys".
  ≤ 3.0s  — Payoff promise visible (what they're going to learn / get /
            see). Reels' algorithm penalizes slow-burn intros harder than
            TikTok's.
  ≤ 5.0s  — Pattern interrupt (unexpected cut, stat reveal, POV shift) to
            re-secure attention from autopilot scrollers.
  Last 2s — Retention loop. Recontextualize the opening so viewers
            re-watch. End-card must give a reason to swipe or comment.
"""

CAROUSEL_FRAMEWORKS_2026 = """
CAROUSEL FRAMEWORKS — 2026 (Welsh / Acosta / Bloom playbook):

Format spec:
  • Aspect ratio: 1080×1350 (4:5 portrait) — 71% of LinkedIn traffic is
    mobile and 4:5 maximizes screen area.
  • Optimal length: 8 slides (outperforms 5 on dwell-time signals).
  • Posting mix for serious creators: 60% text posts, 40% carousels —
    text posts maintain daily presence, carousels do the algorithmic
    heavy lifting.

8-slide canonical structure:
  1. Pattern-interrupt hook  + "swipe to see…" pull (one big phrase).
  2. Pain framing — name the specific pain, not the abstract category.
  3. Why it matters — stakes / loss frame.
  4. The reveal — the framework, list, or step number teaser.
  5. Step / item 1 — concrete, named, with a number.
  6. Step / item 2 — same depth.
  7. Step / item 3 (or punchline / contrarian close).
  8. ONE CTA — save, comment a keyword, follow. Never two competing asks.

Choose ONE of these four sub-frameworks per carousel:
  • OPEN-LOOP   : promise → tension → resolution withheld until slide 7
  • STEP-BY-STEP: numbered tactical breakdown of a result
  • CONTRARIAN  : challenge a niche orthodoxy with evidence
  • CASE-STUDY  : "I tried [thing] for [time]. Here's what happened."
"""

HASHTAG_STRATEGY_2026 = """
HASHTAG STRATEGY — 2026 (the 10–15-per-post, 5-rotated-sets approach):

Per post: use 10–15 hashtags, never 30. Rotate across 5 sets to give the
algorithm fresh signals.

Each set composed as:
  • 5 broad tags     — 500K–2M posts each. Baseline reach, low conversion.
                       Examples: #marketing, #instagramgrowth.
                       Cap at 2–3 per post — over-use dilutes signal.
  • 10 mid-tier tags — 100K–500K posts. The sweet spot. Use 5–7 per post.
                       Specific enough to find interested audiences.
  • 10 niche tags    — 10K–100K posts. High relevance, low competition.
                       Use 3–5 per post — strongest follower-conversion.
  • 5 branded tags   — campaign or community hashtags this brand owns.

KPI: A/B-testing hashtags lifts reach 40% in 3 months (HubSpot 2026 study).
Cycle a new set into rotation every 2 weeks.
"""

GROWTH_KPI_THRESHOLDS_2026 = """
GROWTH KPI THRESHOLDS — 2026 (concrete numbers, not vibes):

Reach-decline triggers (any one of these = act):
  • Engagement rate (likes+comments+saves ÷ reach) declines MoM for 2+ months.
  • Story completion rate drops below 40%.
  • DM rate falls below 2 DMs per 1,000 impressions.

Audience-growth signals:
  • Micro-niche accounts gain followers ~5× faster than generalists in
    year 1 — focus beats breadth.
  • Follower:engagement ratio of < 3% on accounts under 10k = thin
    audience; pause acquisition, fix content.

When growthPlanner outputs a tactic, every line MUST include:
  • A concrete number (frequency, time slot, KPI threshold, count).
  • A platform name (Instagram, LinkedIn, Reels, Stories — not "social").
  • A measurable trigger that says when to escalate or pivot.
"""

AUDIENCE_PAIN_MINING_2026 = """
AUDIENCE PAIN-POINT MINING — 2026 methodology for the Research agent:

Reddit and Quora are the only places users say what they actually think
without brand filter. Use them in parallel — Reddit is raw and fast,
Quora is contextual and problem-framed.

Methodology:
  1. Identify 3–5 subreddits + 3–5 Quora topic pages in the brand's niche.
  2. Pull threads with these filters:
     • Reddit: sort = `top`, period = `month`.
     • Quora: sort by answer upvote count.
  3. Target volume: 50–100 threads per niche. Quality > quantity — skip
     low-upvote noise.
  4. Synthesis: extract pain themes + 2–3 verbatim quotes per theme.
     Verbatim quotes are gold for hook generation — they reveal the exact
     phrasing the audience uses for their own problem.
  5. The questions themselves become content-pillar candidates. High-
     upvote answers tell you the depth required to compete.

NEVER summarize pain into a generic adjective ("frustrated", "confused").
Always cite the specific situation that caused the pain ("got the wrong
ring size after the 14-day return window closed").
"""

ANTI_AI_LANGUAGE_2026_ADDITIONS = """
ANTI-AI LANGUAGE — 2026 additions (these are the words/phrases now flagged
in addition to the original ANTI_AI_LANGUAGE list above):

Additional banned words: multifaceted, comprehensive, holistic, bespoke,
journey, moreover, furthermore, crucial, transformative, groundbreaking,
synergy, empower, beacon, innovative, seamlessly, utilize.

Additional banned phrases:
  • "In today's digital age..."
  • "In today's fast-paced world..." (already in v1 — restated for emphasis)
  • "It's worth noting..."
  • "Designed to enhance..."
  • "Embark on a journey..."

Detectors (Turnitin, GPTZero, Originality AI) are now more sensitive to
these clusters than they were in 2024. By 2026, a reader's "AI fingerprint
sensitivity" detects the pattern within ~2 sentences.
"""

# ── Backward-compat: keep the 7-sweeps name but advise upgrading to 8 ─────────
EIGHT_SWEEPS = SEVEN_SWEEPS + """
8. Brand-specific detail : Does the output contain at least ONE detail
   that ONLY this brand, in this niche, to this audience could write?
   If not, identify the line that fails and rewrite it with a brand-
   specific number, name, place, or product.
"""

