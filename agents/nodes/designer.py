"""
Designer Agent Node — IMPLEMENTED
Generates images via Freepik Mystic API for visual posts,
builds XLSX content calendar and PPT strategy deck,
then uploads everything to Supabase Storage.
"""
import asyncio
import io
import json
import os
import time
from datetime import datetime

import httpx
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from supabase import create_client, Client as SupabaseClient
from state import SocialOSState

# ── Config ────────────────────────────────────────────────────────────────────
FREEPIK_API_KEY  = os.getenv("FREEPIK_API_KEY", "")
FREEPIK_ENGINE   = os.getenv("FREEPIK_ENGINE", "mystic")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "")
BUCKET           = os.getenv("SUPABASE_STORAGE_BUCKET", "socialos-storage")

# Only generate images for these types
VISUAL_TYPES = {"Graphic", "AI Reel", "Carousel"}
# Max images per run (cost control)
MAX_IMAGES = 6

# Lazy Supabase singleton — initialized on first use to ensure .env is loaded
_supabase: SupabaseClient | None = None


def _get_supabase() -> SupabaseClient | None:
    """Return (or lazily create) the Supabase client."""
    global _supabase
    if _supabase is not None:
        return _supabase
    url = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        print(f"[Designer] Supabase env vars missing: URL={'set' if url else 'MISSING'}, KEY={'set' if key else 'MISSING'}")
        return None
    try:
        _supabase = create_client(url, key)
        print(f"[Designer] Supabase client initialized OK")
        return _supabase
    except Exception as e:
        print(f"[Designer] Supabase init error: {e}")
        return None


# ── Main Node ─────────────────────────────────────────────────────────────────

async def designer_node(state: SocialOSState, event_queue: asyncio.Queue) -> dict:
    posts    = state.get("posts_with_copy") or state.get("content_calendar") or []
    brand    = state.get("brand") or {}
    strategy = state.get("growth_strategy") or {}
    run_id   = state["run_id"]
    brand_id = state["brand_id"]

    # ── 1. Generate images ────────────────────────────────────────────────────
    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "designer",
        "message": "Generating brand images with Freepik Mystic…",
    })

    visual_posts = [p for p in posts if p.get("contentType") in VISUAL_TYPES][:MAX_IMAGES]
    design_assets = []

    image_tasks = [
        _generate_and_upload(post, brand, run_id, i, event_queue)
        for i, post in enumerate(visual_posts)
    ]
    results = await asyncio.gather(*image_tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, dict) and r.get("imageUrl"):
            design_assets.append(r)

    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "designer",
        "message": f"{len(design_assets)} images generated — building Excel calendar…",
    })

    # ── 2. Excel XLSX ─────────────────────────────────────────────────────────
    excel_url = await _build_excel(posts, brand, strategy, run_id)

    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "designer",
        "message": "Building strategy PowerPoint deck…",
    })

    # ── 3. PPT deck ───────────────────────────────────────────────────────────
    ppt_url = await _build_ppt(posts, brand, strategy, state.get("analyst_report") or {}, run_id)

    return {
        "design_assets": design_assets,
        "ppt_url":       ppt_url,
        "excel_url":     excel_url,
        "_message": (
            f"Designer complete — {len(design_assets)} images, "
            f"{'Excel ready' if excel_url else 'Excel failed'}, "
            f"{'PPT ready' if ppt_url else 'PPT failed'}"
        ),
    }


# ── Image Generation ──────────────────────────────────────────────────────────

async def _generate_and_upload(post: dict, brand: dict, run_id: str, idx: int, event_queue) -> dict:
    topic  = post.get("topic", "brand content")
    ct     = post.get("contentType", "Graphic")
    niche  = brand.get("name", "") + " " + brand.get("niche", "")
    tone   = brand.get("tone", "professional")
    colors = brand.get("colors") or {}
    primary_color = colors.get("primary", "#6C3CE1") if isinstance(colors, dict) else "#6C3CE1"

    # Build Freepik prompt
    style_map = {
        "Graphic":  "clean minimal social media graphic, flat design, bold typography",
        "AI Reel":  "cinematic vertical social media thumbnail, vibrant, eye-catching",
        "Carousel": "instagram carousel slide, professional layout, infographic style",
    }
    style = style_map.get(ct, "social media graphic")
    prompt = (
        f"{topic}. {niche} brand. {tone} tone. "
        f"{style}. Brand color {primary_color}. "
        "High quality, Instagram-ready, 1080x1080px aesthetic."
    )

    await event_queue.put({
        "type": "agent_progress",
        "agentKey": "designer",
        "message": f"Generating image {idx+1}: {topic[:40]}…",
    })

    image_url = await _freepik_generate(prompt)

    if not image_url:
        return {}

    return {
        "imageUrl":    image_url,
        "contentType": ct,
        "topic":       topic,
        "prompt":      prompt,
        "date":        post.get("date"),
    }


async def _freepik_generate(prompt: str) -> str:
    """Call Freepik Mystic API and poll for result."""
    if not FREEPIK_API_KEY:
        return ""

    headers = {
        "x-freepik-api-key": FREEPIK_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Start generation
            start_resp = await client.post(
                "https://api.freepik.com/v1/ai/mystic",
                headers=headers,
                json={
                    "prompt": prompt,
                    "num_images": 1,
                    "resolution": "1_1",
                    "engine": FREEPIK_ENGINE,
                    "creative_detailing": 60,
                    "styling": {"style": "photo"},
                },
            )

            if start_resp.status_code not in (200, 201, 202):
                print(f"[Designer] Freepik start error {start_resp.status_code}: {start_resp.text[:200]}")
                return ""

            data = start_resp.json()
            task_id = (data.get("data") or {}).get("id") or data.get("id")

            if not task_id:
                print(f"[Designer] No task ID from Freepik: {data}")
                return ""

            # Poll for result (max 60s)
            for attempt in range(20):
                await asyncio.sleep(3)
                poll_resp = await client.get(
                    f"https://api.freepik.com/v1/ai/mystic/{task_id}",
                    headers=headers,
                )
                poll_data = poll_resp.json()
                result = poll_data.get("data") or {}
                status = result.get("status") or poll_data.get("status")

                if status == "completed":
                    generated = result.get("generated_images") or result.get("images") or []
                    if generated:
                        return generated[0].get("url") or generated[0].get("base64", "")
                    return ""

                if status in ("failed", "error", "cancelled"):
                    print(f"[Designer] Freepik task {task_id} status: {status}")
                    return ""

            print(f"[Designer] Freepik task {task_id} timed out")
            return ""

    except Exception as e:
        print(f"[Designer] Freepik error: {e}")
        return ""


# ── Excel XLSX ────────────────────────────────────────────────────────────────

async def _build_excel(posts: list, brand: dict, strategy: dict, run_id: str) -> str | None:
    try:
        wb = openpyxl.Workbook()

        # ── Sheet 1: Content Calendar ──
        ws = wb.active
        ws.title = "Content Calendar"
        name = brand.get("name", "Brand")
        niche = brand.get("niche", "")

        # Header row style
        header_fill  = PatternFill("solid", fgColor="6C3CE1")
        white_font   = Font(bold=True, color="FFFFFF", size=11)
        subhdr_fill  = PatternFill("solid", fgColor="2D235A")
        subhdr_font  = Font(bold=True, color="A78BFA", size=10)
        center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border  = Border(
            left=Side(style="thin", color="2D235A"),
            right=Side(style="thin", color="2D235A"),
            top=Side(style="thin", color="2D235A"),
            bottom=Side(style="thin", color="2D235A"),
        )

        # Title
        ws.merge_cells("A1:H1")
        title_cell = ws["A1"]
        title_cell.value = f"{name} — Content Calendar"
        title_cell.font  = Font(bold=True, color="FFFFFF", size=14)
        title_cell.fill  = header_fill
        title_cell.alignment = center_align

        # Subtitle
        ws.merge_cells("A2:H2")
        sub_cell = ws["A2"]
        sub_cell.value = f"Generated by SocialOS | {niche} | {datetime.utcnow().strftime('%d %b %Y')}"
        sub_cell.font  = Font(color="A78BFA", italic=True, size=10)
        sub_cell.fill  = PatternFill("solid", fgColor="1E1640")
        sub_cell.alignment = center_align

        # Column headers
        headers = ["#", "Date", "Day", "Content Type", "Topic", "Caption", "Hashtags", "Status"]
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col, value=h)
            cell.font  = subhdr_font
            cell.fill  = subhdr_fill
            cell.alignment = center_align
            cell.border = thin_border

        # Post rows
        type_colors = {
            "Reel":     "3B82F6", "AI Reel":  "EC4899",
            "Carousel": "10B981", "Graphic":  "A78BFA", "Story": "F59E0B",
        }
        for i, post in enumerate(posts):
            row = i + 4
            post_date = post.get("date", "")
            try:
                dt = datetime.fromisoformat(post_date)
                day_name  = dt.strftime("%A")
                date_str  = dt.strftime("%d %b %Y")
            except Exception:
                day_name, date_str = "", post_date

            ct = post.get("contentType", "")
            ct_color = type_colors.get(ct, "6C3CE1")
            ct_fill  = PatternFill("solid", fgColor=ct_color)
            row_fill = PatternFill("solid", fgColor="0F0A1E" if i % 2 == 0 else "1E1640")

            row_data = [
                i + 1,
                date_str,
                day_name,
                ct,
                post.get("topic", ""),
                post.get("caption", ""),
                " ".join(post.get("hashtags", [])[:10]),
                post.get("status", "draft").upper(),
            ]
            for col, val in enumerate(row_data, 1):
                cell = ws.cell(row=row, column=col, value=val)
                cell.alignment = Alignment(vertical="center", wrap_text=True)
                cell.border    = thin_border
                cell.fill      = ct_fill if col == 4 else row_fill
                if col == 4:
                    cell.font  = Font(bold=True, color="FFFFFF", size=9)
                elif col in (1, 2, 3):
                    cell.font  = Font(color="A78BFA", size=9)
                else:
                    cell.font  = Font(color="D1D5DB", size=9)

        # Column widths
        widths = [5, 14, 12, 14, 40, 60, 50, 10]
        for col, width in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(col)].width = width

        # Freeze top rows
        ws.freeze_panes = "A4"

        # ── Sheet 2: Growth Strategy ──
        ws2 = wb.create_sheet("Growth Strategy")
        ws2.sheet_view.showGridLines = False
        ws2["A1"] = "Growth Strategy Overview"
        ws2["A1"].font = Font(bold=True, color="FFFFFF", size=14)
        ws2["A1"].fill = header_fill

        row2 = 3
        sections = {
            "Content Pillars": strategy.get("pillars", []),
            "Growth Tactics":  strategy.get("growth_tactics", []),
            "CTA Templates":   strategy.get("cta_templates", []),
        }
        for section, items in sections.items():
            ws2.cell(row=row2, column=1, value=section).font = Font(bold=True, color="A78BFA", size=11)
            ws2.cell(row=row2, column=1).fill = subhdr_fill
            row2 += 1
            if isinstance(items, list):
                for item in items:
                    cell = ws2.cell(row=row2, column=1, value=f"  • {item}")
                    cell.font = Font(color="D1D5DB", size=10)
                    row2 += 1
            row2 += 1

        ws2.column_dimensions["A"].width = 80

        # Serialize and upload
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        path = f"runs/{run_id}/content_calendar.xlsx"
        url  = _upload_bytes(buf.read(), path, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        return url

    except Exception as e:
        print(f"[Designer] Excel build error: {e}")
        return None


# ── PowerPoint PPT ────────────────────────────────────────────────────────────

async def _build_ppt(posts: list, brand: dict, strategy: dict, analyst_report: dict, run_id: str) -> str | None:
    try:
        prs = Presentation()
        prs.slide_width  = Inches(10)
        prs.slide_height = Inches(5.625)  # 16:9

        name    = brand.get("name", "Brand")
        niche   = brand.get("niche", "")
        colors  = brand.get("colors") or {}
        primary = colors.get("primary", "#6C3CE1") if isinstance(colors, dict) else "#6C3CE1"

        def hex_to_rgb(h: str):
            h = h.lstrip("#")
            return RGBColor(int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))

        brand_color = hex_to_rgb(primary)
        white       = RGBColor(0xFF, 0xFF, 0xFF)
        dark_bg     = RGBColor(0x0F, 0x0A, 0x1E)
        accent      = RGBColor(0xA7, 0x8B, 0xFA)

        blank_layout = prs.slide_layouts[6]  # blank

        def add_bg(slide, color: RGBColor):
            fill = slide.background.fill
            fill.solid()
            fill.fore_color.rgb = color

        def add_text(slide, text, left, top, width, height, size, bold=False, color=None, align=PP_ALIGN.LEFT):
            txb = slide.shapes.add_textbox(left, top, width, height)
            tf  = txb.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = align
            run = p.add_run()
            run.text = text
            run.font.size   = Pt(size)
            run.font.bold   = bold
            run.font.color.rgb = color or white
            return txb

        # ── Slide 1: Title ──
        slide = prs.slides.add_slide(blank_layout)
        add_bg(slide, dark_bg)
        # Accent bar
        bar = slide.shapes.add_shape(1, 0, 0, Inches(0.05), prs.slide_height)
        bar.fill.solid(); bar.fill.fore_color.rgb = brand_color; bar.line.fill.background()
        add_text(slide, name.upper(),         Inches(0.4), Inches(1.2), Inches(9), Inches(1.2), 40, bold=True, color=white)
        add_text(slide, f"{niche} — Content Strategy", Inches(0.4), Inches(2.4), Inches(9), Inches(0.8), 20, color=accent)
        add_text(slide, f"Generated by SocialOS | {datetime.utcnow().strftime('%d %b %Y')}", Inches(0.4), Inches(4.8), Inches(9), Inches(0.5), 12, color=RGBColor(0x6B,0x72,0x80))

        # ── Slide 2: Content Mix ──
        slide = prs.slides.add_slide(blank_layout)
        add_bg(slide, dark_bg)
        add_text(slide, "Content Mix Strategy", Inches(0.5), Inches(0.3), Inches(9), Inches(0.7), 28, bold=True)
        content_mix = strategy.get("content_mix", {})
        y_pos = 1.3
        for ct, pct in content_mix.items():
            add_text(slide, f"{ct}:  {pct}%", Inches(0.5), Inches(y_pos), Inches(4), Inches(0.4), 16, color=accent)
            y_pos += 0.5

        # ── Slide 3: Content Pillars ──
        slide = prs.slides.add_slide(blank_layout)
        add_bg(slide, dark_bg)
        add_text(slide, "Content Pillars", Inches(0.5), Inches(0.3), Inches(9), Inches(0.7), 28, bold=True)
        pillars = strategy.get("pillars", [])
        for i, pillar in enumerate(pillars[:4]):
            add_text(slide, f"0{i+1}. {pillar}", Inches(0.5), Inches(1.2 + i*0.9), Inches(9), Inches(0.7), 18, color=white if i%2==0 else accent)

        # ── Slide 4: Growth Tactics ──
        slide = prs.slides.add_slide(blank_layout)
        add_bg(slide, dark_bg)
        add_text(slide, "Growth Tactics", Inches(0.5), Inches(0.3), Inches(9), Inches(0.7), 28, bold=True)
        tactics = strategy.get("growth_tactics", [])
        y = 1.2
        for t in tactics[:5]:
            add_text(slide, f"• {t}", Inches(0.5), Inches(y), Inches(9), Inches(0.55), 14, color=accent if y < 2 else white)
            y += 0.6

        # ── Slide 5: 15-Day Calendar Summary ──
        slide = prs.slides.add_slide(blank_layout)
        add_bg(slide, dark_bg)
        add_text(slide, f"{len(posts)}-Day Content Calendar", Inches(0.5), Inches(0.3), Inches(9), Inches(0.7), 28, bold=True)
        y = 1.2
        for i, post in enumerate(posts[:8]):
            try:
                dt = datetime.fromisoformat(post.get("date",""))
                date_str = dt.strftime("%d %b")
            except Exception:
                date_str = post.get("date","")[:10]
            ct    = post.get("contentType","")
            topic = post.get("topic","")[:55]
            line  = f"{date_str}  [{ct}]  {topic}"
            add_text(slide, line, Inches(0.5), Inches(y), Inches(9), Inches(0.42), 11, color=white if i%2==0 else accent)
            y += 0.48

        # Serialize and upload
        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)

        path = f"runs/{run_id}/strategy_deck.pptx"
        url  = _upload_bytes(buf.read(), path, "application/vnd.openxmlformats-officedocument.presentationml.presentation")
        return url

    except Exception as e:
        print(f"[Designer] PPT build error: {e}")
        return None


# ── Supabase Upload ───────────────────────────────────────────────────────────

def _upload_bytes(data: bytes, path: str, content_type: str) -> str | None:
    sb = _get_supabase()
    if not sb:
        print(f"[Designer] Supabase unavailable — skipping upload for {path}")
        return None
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "socialos-storage")
    try:
        sb.storage.from_(bucket).upload(
            path, data,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        result = sb.storage.from_(bucket).get_public_url(path)
        print(f"[Designer] Uploaded {path} -> {str(result)[:80]}")
        return result
    except Exception as e:
        print(f"[Designer] Supabase upload error for {path}: {e}")
        import traceback; traceback.print_exc()
        return None
