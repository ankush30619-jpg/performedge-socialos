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
