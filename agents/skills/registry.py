"""
Marketing Skills Registry — Framework constants for agent prompts.
Distilled from marketing psychology, copywriting, social, content-strategy,
customer-research, and competitor-profiling methodologies.
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
