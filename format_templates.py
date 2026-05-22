"""
Viral Format Templates — opinionated structural templates for each native social format.

When the Strategist outputs a topic with a Content Type, the Copy Writer pulls the
matching template here and writes the post inside that structure. This is what
separates "AI default generic" output from "actually performs on Reels".

Each template is structural advice the LLM follows — NOT a fill-in-the-blank script.
The LLM still writes original copy; the template guarantees the right SHAPE.
"""

VIRAL_FORMAT_TEMPLATES = {
    "POV Reel": """STRUCTURAL TEMPLATE — POV REEL (15-25 sec)

OPENING (0-2s): on-screen text "POV: ..." that puts viewer inside a specific moment
  Example "POV: Papa finally agreed to buy a cooler in 47°C heat"
TENSION (2-8s): the moment plays out visually — small, specific, recognisable detail
  No narration in first 4s — let visual + on-screen text carry it
RESOLUTION (8-18s): the product enters the moment and changes it
  Show the relief / shift — facial reaction is everything
PAYOFF (18-25s): on-screen brand mark + one-line landing

VOICE: First-person or third-person "watching them" — never sales-y. The viewer should
feel like they're seeing a friend's story, not an ad.

HOOK MUST: open with "POV:" or equivalent immediate-immersion construction.
AVOID: explanation, voice-over telling viewer what they're seeing, product-first framing.""",

    "Meme Post": """STRUCTURAL TEMPLATE — MEME / STATIC GRAPHIC

VISUAL: 1 frame, instantly readable. Either:
  - Two-panel before/after (left: pain, right: product relief)
  - Caption-over-image relatable moment
  - Tweet-style text on solid colour

TEXT: ONE punchline. Maximum 12 words on the image.
  Example "Bijli gayi. AC band. Pati shayar ban gaya."

CAPTION (below image): 1-2 lines that EXTEND the joke, not explain it.
  + One line of brand mention max.
  + 2-4 hashtags including #MishikasElectronics

HOOK MUST: be immediately readable in <2 seconds of scroll.
AVOID: long captions, multiple jokes, branded watermarks larger than the joke.""",

    "Vox Pop Reel": """STRUCTURAL TEMPLATE — STREET VOX POP REEL (30-45 sec)

OPENING (0-3s): on-screen text + cut-to-camera question
  Example "Hisar mein public se poocha — aaj kitni garmi laga?"
CONTENT (3-30s): 4-6 quick public reactions, each 3-5 sec
  Real people, real reactions, mix of humour + frustration
TRANSITION (30-35s): "Aur is garmi ka solution?" / interviewer reveal
PRODUCT MOMENT (35-45s): brand person hands them the answer / one reacts to demo
PAYOFF (45s): CTA + brand mark

VOICE: Natural conversational, local accent welcome, unscripted feel.
HOOK MUST: open with a question that makes viewer want to answer in their head.
AVOID: actor-feel, polished reactions, scripted sounding people.""",

    "Myth-Bust Reel": """STRUCTURAL TEMPLATE — MYTH-BUST REEL (20-30 sec)

OPENING (0-3s): "MYTH:" big on-screen text + the common wrong belief
  Example "MYTH: Coolers se sirf paani ka mausam banta hai."
SETUP (3-8s): "Sach baat ye hai..." with proof setup
REVEAL (8-22s): demonstrate the truth — quick demo, comparison, real data
RESOLUTION (22-30s): product as the solution + 1-line takeaway

VOICE: Direct, slightly confrontational, "I'll save you from this mistake" energy.
HOOK MUST: open with "MYTH:" / "Sach ye nahi hai..." / "Ruko, pehle ye sun..."
AVOID: hedging, "depends" answers, multi-myth episodes (one myth per reel).""",

    "Comparison Reel": """STRUCTURAL TEMPLATE — COMPARISON REEL (15-25 sec)

OPENING (0-2s): split-screen visual + text "X vs Y"
  Example "Old cooler vs Mishikas Raftaar"
ROUND 1 (2-8s): airflow / noise / look — visual + numbers if available
ROUND 2 (8-15s): power bill / water use / convenience
ROUND 3 (15-22s): the lifestyle moment (kids sleeping / family chilling)
VERDICT (22-25s): clear winner + CTA

VOICE: Sportscaster energy, light competitive. Numbers help.
HOOK MUST: name both contestants in first 2 seconds.
AVOID: trashing the competitor by name (it's "old cooler" not "Symphony"). Keep it sporting.""",

    "Before/After Transformation Reel": """STRUCTURAL TEMPLATE — TRANSFORMATION REEL (15-20 sec)

OPENING (0-2s): "BEFORE" overlay on the hot/uncomfortable scene
  Real-feeling, slightly grim: kids sweating, fan struggling, dad fanning himself
TENSION (2-7s): the discomfort plays out — visual cues (sweat, slow fan, irritation)
TRANSITION (7-9s): product arrives (unboxing flash / install moment)
AFTER (9-18s): same room, same family, completely different mood
  Cool air visible (curtains moving), faces relaxed, kid sleeping
PAYOFF (18-20s): "Same room. Same family. Diff cooler." + CTA

VOICE: Visual storytelling, minimal copy on screen. Music does the work.
HOOK MUST: open with the BEFORE state immediately — no setup.
AVOID: cutaways to product specs mid-story, voice-over explanation.""",

    "Educational Carousel": """STRUCTURAL TEMPLATE — EDUCATIONAL CAROUSEL (5-7 slides)

SLIDE 1 (Hook): One specific question or unexpected stat
  "Cooler kharidne se pehle ye 3 cheezein check karo (slide karo)"
SLIDES 2-5 (Body): One specific tip / point per slide
  Visual icon + 1-line headline + 2-line explainer
SLIDE 6 (Brand integration): How Mishikas solves these naturally
SLIDE 7 (CTA): "DM RAFTAAR for dealer locator" / "Save this for summer"

VOICE: Helpful expert friend, not lecturer.
HOOK MUST: promise specific value in slide 1.
AVOID: vague tips, brand mentions before slide 6, more than 7 slides.""",

    "Customer Story Reel": """STRUCTURAL TEMPLATE — UGC / CUSTOMER STORY REEL (20-30 sec)

OPENING (0-3s): the customer's face + on-screen text with their name + city
  Example "Suresh ji, Hisar — pehli baar Mishikas khareedi"
STORY (3-20s): in their own voice, mobile-shot, NOT scripted
  Their pain → their search → why they picked Mishikas
PROOF (20-25s): show them using it in their actual home
PAYOFF (25-30s): one-line takeaway + "tag a friend who needs this"

VOICE: 100% customer voice, no over-production, mobile-shot feel.
HOOK MUST: open with the customer's actual face, not B-roll.
AVOID: voice-over the customer, script reading, studio polish.""",

    "Trend-Jack Reel": """STRUCTURAL TEMPLATE — TREND-JACK REEL (15-25 sec)

PRE-WORK: identify a fresh trending audio / format on Reels this week
OPENING (0-3s): use the trending audio's recognised cue
ADAPTATION (3-15s): apply the trend's beat structure to a cooler/heat scenario
  Reference both the original meme AND your brand naturally
PAYOFF (15-25s): brand-specific resolution

VOICE: Native to the trend — if the trend is comedic, be funny; emotional, be emotional.
HOOK MUST: viewer should recognise the trend within 2 seconds.
AVOID: forcing a trend that doesn't fit, using trends that have peaked >1 week ago.""",
}


# Map common Strategist content_type values → format template keys
FORMAT_TYPE_ALIASES = {
    "reel": "POV Reel",  # default reel = POV unless more specific
    "pov reel": "POV Reel",
    "meme": "Meme Post",
    "meme post": "Meme Post",
    "static graphic": "Meme Post",
    "vox pop": "Vox Pop Reel",
    "street interview": "Vox Pop Reel",
    "myth-bust": "Myth-Bust Reel",
    "myth bust": "Myth-Bust Reel",
    "myth buster": "Myth-Bust Reel",
    "comparison": "Comparison Reel",
    "comparison reel": "Comparison Reel",
    "vs reel": "Comparison Reel",
    "before/after": "Before/After Transformation Reel",
    "transformation": "Before/After Transformation Reel",
    "before after reel": "Before/After Transformation Reel",
    "carousel": "Educational Carousel",
    "educational carousel": "Educational Carousel",
    "listicle": "Educational Carousel",
    "customer story": "Customer Story Reel",
    "ugc": "Customer Story Reel",
    "testimonial": "Customer Story Reel",
    "trend-jack": "Trend-Jack Reel",
    "trendjack": "Trend-Jack Reel",
    "trend jack": "Trend-Jack Reel",
}


def get_format_template(content_type: str, post_notes: str = "") -> tuple[str, str]:
    """
    Resolve the right viral format template for a given post.
    Returns (format_name, template_text). Empty strings if no clear match.

    Order: explicit content_type → notes keywords → default by category.
    """
    ct = (content_type or "").lower().strip()
    notes = (post_notes or "").lower()

    # Direct alias match
    if ct in FORMAT_TYPE_ALIASES:
        name = FORMAT_TYPE_ALIASES[ct]
        return name, VIRAL_FORMAT_TEMPLATES.get(name, "")

    # Substring match on alias keys
    for alias, name in FORMAT_TYPE_ALIASES.items():
        if alias in ct or alias in notes:
            return name, VIRAL_FORMAT_TEMPLATES.get(name, "")

    # Default category falls
    if "reel" in ct or "video" in ct:
        return "POV Reel", VIRAL_FORMAT_TEMPLATES["POV Reel"]
    if "carousel" in ct:
        return "Educational Carousel", VIRAL_FORMAT_TEMPLATES["Educational Carousel"]
    if "static" in ct or "graphic" in ct or "post" in ct:
        return "Meme Post", VIRAL_FORMAT_TEMPLATES["Meme Post"]

    return "", ""


# ─────────────── Hook Pattern Library ───────────────
# 6 universal hook patterns that stop the scroll. Used by Copy Writer to ensure
# every reel/post opens with one of these — never with brochure language.
HOOK_PATTERNS = {
    "Pain Interrupt": {
        "structure": "State a sharp pain the audience feels RIGHT NOW (specific, visceral)",
        "examples": [
            "45°C? Ab asli test shuru.",
            "Bijli gayi, kamre mein aag lag rahi hai.",
            "Maa chai bana rahi hai 47° mein…",
        ],
    },
    "Question Hook": {
        "structure": "Ask a question that the viewer will answer in their head",
        "examples": [
            "Sach bolo — aaj kitni garmi laga?",
            "Cooler ya AC — kis pe paisa lagega?",
            "Yaad hai dadi ke ghar wala cooler?",
        ],
    },
    "Curiosity Gap": {
        "structure": "Tease specific information without revealing — viewer must watch to know",
        "examples": [
            "Cooler kharidne se pehle ye 3 cheezein check karo — pata bhi nahi hota.",
            "Yeh cooler chala ke dekho — 30 second mein samajh aa jayega.",
            "Bijli bill 40% kam kaise hua — aage dekho.",
        ],
    },
    "POV Immersion": {
        "structure": "'POV:' followed by a specific identifiable moment",
        "examples": [
            "POV: Papa ne finally cooler khareed liya.",
            "POV: Aapka pankha hawa kam, awaaz zyada de raha hai.",
            "POV: Maa ne kaha 'ab toh kuch kar bhai'.",
        ],
    },
    "Unpopular Opinion": {
        "structure": "State a contrarian view that the audience secretly agrees with",
        "examples": [
            "Sach baat ye hai — most coolers actually room garam karte hain.",
            "Honest opinion: ₹15,000 ka AC mostly waste hai 2-room ghar mein.",
            "Pata hai? Bigger cooler nahi, better airflow chahiye.",
        ],
    },
    "FOMO / Urgency": {
        "structure": "Time pressure + social proof of others acting",
        "examples": [
            "Heat badh rahi hai, price kab badhe pata nahi 👀",
            "Mohalle mein 3 ghar le aaye — aapka kab?",
            "Aaj nahi liya toh June ki garmi mein regret hoga.",
        ],
    },
}


def hook_patterns_brief() -> str:
    """One-paragraph brief for prompt injection."""
    out = ["6 HOOK PATTERNS — every Reel/Static MUST open with one of these:"]
    for name, info in HOOK_PATTERNS.items():
        out.append(f"  ▸ {name}: {info['structure']}")
        out.append(f"      e.g., \"{info['examples'][0]}\"")
    out.append("")
    out.append("BANNED OPENERS (brochure language — automatic regenerate trigger):")
    out.append('  ✗ "Elevate your space" / "Transform your home" / "Premium living"')
    out.append('  ✗ "Introducing..." / "We are proud to..." / "Innovation in..."')
    out.append('  ✗ "Looking for...? Look no further!" / generic listicle openers')
    out.append('  ✗ "Did you know that..." (unless followed by specific surprising number)')
    return "\n".join(out)
