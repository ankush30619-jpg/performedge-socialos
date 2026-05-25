"""
Expert Social Media Planner — premium desktop app (v4).

Sidebar-driven layout with seven specialised agents:
  • Home              — brand dashboard, connection status, quick actions
  • GROOK             — Growth Planner (master strategist)
  • Analyst Baba      — continuous social intelligence (NEW)
  • Competitors       — competitor playbook
  • Strategist        — plan-aware calendar
  • Copy Writer       — story-driven copy
  • Designer          — visual generation
"""
import json
import os
import re
import sys
import threading
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import (
    Tk, Toplevel, StringVar, IntVar, BooleanVar, END, DISABLED, NORMAL,
    filedialog, messagebox, Text, Canvas, Listbox, Scrollbar, SINGLE,
    Frame, Label, Button as TkButton
)
from tkinter import ttk

import sv_ttk

import core
import brand_extractor
import competitor_analyzer
import trend_scout
import strategist
import designer_agent
import compositor
import growth_planner
import meta_client
import analyst_agent


APP_NAME = "Expert Social Media Planner"
APP_TAGLINE = "AI-Powered Social Strategy Operating System"
APP_VERSION = "v4.0"
ROOT_DIR = Path(__file__).parent
DEFAULT_OUTPUT_DIR = ROOT_DIR / "output"


# ═══════════════════════════════════════════════════════════════════════
#                            DESIGN TOKENS
# ═══════════════════════════════════════════════════════════════════════
# Premium light palette — Linear / Notion / Stripe-inspired
PALETTE = {
    "bg":          "#F7F8FA",   # base canvas
    "bg_alt":      "#FFFFFF",   # topbar / surfaces on bg
    "surface":     "#FFFFFF",   # cards
    "surface_2":   "#F9FAFB",   # raised cards / input bg
    "border":      "#E5E7EB",
    "border_soft": "#F1F2F4",

    "txt":         "#1F2937",
    "txt_dim":     "#4B5563",
    "txt_mute":    "#9CA3AF",
    "txt_high":    "#0B0F1A",

    "accent":      "#FF6B4A",   # warm coral — primary CTA
    "accent_dk":   "#E5563B",
    "accent_soft": "#FFF1EC",
    "accent_glow": "#FFA68F",

    "brand":       "#5B7CFF",   # cool indigo
    "brand_soft":  "#EEF0FF",
    "success":     "#10B981",
    "success_soft": "#ECFDF5",
    "warning":     "#F59E0B",
    "warning_soft": "#FFFBEB",
    "danger":      "#EF4444",
    "danger_soft": "#FEF2F2",

    "sidebar":     "#FFFFFF",
    "sidebar_hi":  "#F3F4F6",
    "sidebar_sel_bg": "#FFF1EC",
    "sidebar_sel": "#FF6B4A",
}

# Premium typography — Inter if installed, fallback to Segoe UI Variable
_FONT_FAMILY = "Inter"
def _pick_font():
    """Pick best available premium font."""
    import tkinter.font as tkfont
    try:
        fams = tkfont.families()
        for cand in ("Inter Display", "Inter", "SF Pro Display", "Segoe UI Variable Display",
                     "Segoe UI Variable", "Segoe UI"):
            if cand in fams:
                return cand
    except Exception:
        pass
    return "Segoe UI"

# Will be resolved on first init_styles call
_FONT = None

def _F(size, weight="normal"):
    global _FONT
    if _FONT is None:
        _FONT = _pick_font()
    return (_FONT, size, weight) if weight != "normal" else (_FONT, size)

# Lazy font dict — built after _FONT is set
def _build_fonts():
    return {
        "title":   _F(26, "bold"),
        "h1":      _F(20, "bold"),
        "h2":      _F(15, "bold"),
        "h3":      _F(12, "bold"),
        "body":    _F(11),
        "bold":    _F(11, "bold"),
        "small":   _F(10),
        "tiny":    _F(9),
        "mono":    ("Consolas", 10),
        "nav":     _F(11, "bold"),
        "metric":  _F(28, "bold"),
    }

FONTS = {}  # populated by init_styles


def init_styles(root):
    """Apply sv_ttk light theme + custom overrides for premium feel."""
    global FONTS, _FONT
    _FONT = _pick_font()
    FONTS.update(_build_fonts())

    sv_ttk.set_theme("light")
    s = ttk.Style(root)

    # Frame backgrounds
    s.configure("Bg.TFrame",      background=PALETTE["bg"])
    s.configure("Sidebar.TFrame", background=PALETTE["sidebar"])
    s.configure("Surface.TFrame", background=PALETTE["surface"])
    s.configure("Card.TFrame",    background=PALETTE["surface"], relief="flat", borderwidth=1)
    s.configure("CardRaised.TFrame", background=PALETTE["surface_2"])
    s.configure("Topbar.TFrame",  background=PALETTE["bg_alt"])
    s.configure("Statusbar.TFrame", background=PALETTE["surface_2"])

    # Labels
    s.configure("Bg.TLabel",      background=PALETTE["bg"],     foreground=PALETTE["txt"])
    s.configure("Card.TLabel",    background=PALETTE["surface"], foreground=PALETTE["txt"])
    s.configure("Surface.TLabel", background=PALETTE["surface"], foreground=PALETTE["txt"])
    s.configure("Sidebar.TLabel", background=PALETTE["sidebar"], foreground=PALETTE["txt"])
    s.configure("Topbar.TLabel",  background=PALETTE["bg_alt"], foreground=PALETTE["txt"])

    s.configure("Title.TLabel",   background=PALETTE["bg_alt"],
                foreground=PALETTE["txt_high"], font=FONTS["title"])
    s.configure("H1.TLabel",      background=PALETTE["bg"],
                foreground=PALETTE["txt_high"], font=FONTS["h1"])
    s.configure("H2.TLabel",      background=PALETTE["surface"],
                foreground=PALETTE["txt_high"], font=FONTS["h2"])
    s.configure("H3.TLabel",      background=PALETTE["surface"],
                foreground=PALETTE["txt"], font=FONTS["h3"])
    s.configure("Body.TLabel",    background=PALETTE["surface"],
                foreground=PALETTE["txt"], font=FONTS["body"])
    s.configure("Hint.TLabel",    background=PALETTE["surface"],
                foreground=PALETTE["txt_mute"], font=FONTS["small"])
    s.configure("HintBg.TLabel",  background=PALETTE["bg"],
                foreground=PALETTE["txt_mute"], font=FONTS["small"])
    s.configure("Accent.TLabel",  background=PALETTE["surface"],
                foreground=PALETTE["accent"], font=FONTS["bold"])
    s.configure("Metric.TLabel",  background=PALETTE["surface"],
                foreground=PALETTE["txt_high"], font=FONTS["metric"])
    s.configure("Caption.TLabel", background=PALETTE["surface"],
                foreground=PALETTE["txt_mute"], font=FONTS["tiny"])
    s.configure("Status.TLabel",  background=PALETTE["surface_2"],
                foreground=PALETTE["txt_dim"], font=FONTS["small"])

    # Subtitle labels in topbar
    s.configure("Subtitle.TLabel", background=PALETTE["bg_alt"],
                foreground=PALETTE["txt_mute"], font=FONTS["small"])

    # Buttons
    s.configure("Accent.TButton",  font=FONTS["bold"], padding=(20, 11))
    s.configure("Ghost.TButton",   font=FONTS["body"], padding=(14, 8))
    s.configure("Pill.TButton",    font=FONTS["small"], padding=(12, 5))

    # Entries
    s.configure("Modern.TEntry", padding=(12, 9), font=FONTS["body"])
    s.configure("TEntry", padding=(12, 9))

    # Combobox tweaks
    s.configure("TCombobox", padding=(10, 8))

    # Progressbar
    s.configure("Horizontal.TProgressbar",
                background=PALETTE["accent"],
                troughcolor=PALETTE["border_soft"],
                borderwidth=0,
                thickness=8)


# ═══════════════════════════════════════════════════════════════════════
#                       REUSABLE PRIMITIVES
# ═══════════════════════════════════════════════════════════════════════
def card(parent, padding=(20, 18)) -> ttk.Frame:
    """Surface-style card with internal padding and subtle border."""
    # Outer = light bg with 1px border simulated via background
    outer = Frame(parent, bg=PALETTE["border"], bd=0, highlightthickness=0)
    # Inner card sits 1px inside outer to create the border line
    f = ttk.Frame(outer, style="Card.TFrame")
    f.pack(fill="both", expand=True, padx=1, pady=1)
    inner = ttk.Frame(f, style="Card.TFrame", padding=padding)
    inner.pack(fill="both", expand=True)
    outer.inner = inner
    return outer


def make_scrollable_view(parent):
    """
    Build a vertically-scrollable canvas+inner frame inside parent.
    Returns (container, inner) — pack content into 'inner'.
    Inner is a ttk.Frame styled as Bg.TFrame.
    """
    container = ttk.Frame(parent, style="Bg.TFrame")
    canvas = Canvas(container, bg=PALETTE["bg"], highlightthickness=0)
    vsb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    inner = ttk.Frame(canvas, style="Bg.TFrame")
    window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_inner_configure(_e=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
    inner.bind("<Configure>", _on_inner_configure)

    def _on_canvas_resize(e):
        canvas.itemconfigure(window_id, width=e.width)
    canvas.bind("<Configure>", _on_canvas_resize)

    # Mouse-wheel scrolling — only when pointer is over this canvas
    def _on_mousewheel(e):
        canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
    def _bind_wheel(_e):
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    def _unbind_wheel(_e):
        canvas.unbind_all("<MouseWheel>")
    container.bind("<Enter>", _bind_wheel)
    container.bind("<Leave>", _unbind_wheel)

    return container, inner


def section_heading(parent, title, subtitle=None):
    c = ttk.Frame(parent, style="Bg.TFrame")
    ttk.Label(c, text=title, style="H1.TLabel").pack(anchor="w")
    if subtitle:
        ttk.Label(c, text=subtitle, style="HintBg.TLabel").pack(anchor="w", pady=(2, 0))
    return c


def metric_card(parent, label, value, sublabel=None, accent=False):
    """Big-number metric card."""
    c = card(parent, padding=(18, 14))
    color_label = PALETTE["accent"] if accent else PALETTE["txt_mute"]
    val_color = PALETTE["accent"] if accent else PALETTE["txt_high"]
    ttk.Label(c.inner, text=label.upper(),
              foreground=color_label,
              background=PALETTE["surface"],
              font=FONTS["tiny"]).pack(anchor="w")
    ttk.Label(c.inner, text=str(value),
              foreground=val_color,
              background=PALETTE["surface"],
              font=FONTS["metric"]).pack(anchor="w", pady=(4, 0))
    if sublabel:
        ttk.Label(c.inner, text=sublabel, style="Caption.TLabel").pack(anchor="w", pady=(2, 0))
    return c


# ═══════════════════════════════════════════════════════════════════════
#                       SETTINGS DIALOG
# ═══════════════════════════════════════════════════════════════════════
class SettingsDialog(Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Settings — Expert Social Media Planner")
        self.configure(bg=PALETTE["bg"])
        self.geometry("680x720"); self.minsize(640, 660)
        self.transient(master); self.grab_set()
        s = core.load_settings()

        # Build a scrollable form
        canvas = Canvas(self, bg=PALETTE["bg"], highlightthickness=0)
        canvas.pack(side="left", fill="both", expand=True)
        sb = Scrollbar(self, orient="vertical", command=canvas.yview)
        sb.pack(side="right", fill="y")
        canvas.config(yscrollcommand=sb.set)
        wrap = ttk.Frame(canvas, style="Bg.TFrame", padding=24)
        canvas.create_window((0, 0), window=wrap, anchor="nw", width=660)
        wrap.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind_all("<MouseWheel>",
                          lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        ttk.Label(wrap, text="Settings", style="H1.TLabel",
                  background=PALETTE["bg"]).pack(anchor="w", pady=(0, 18))

        # Helper for field rows
        def field_row(parent, label, var, *, secret=False):
            row = ttk.Frame(parent, style="Bg.TFrame")
            row.pack(fill="x", pady=(8, 4))
            ttk.Label(row, text=label, style="HintBg.TLabel",
                      font=FONTS["small"]).pack(anchor="w")
            e = ttk.Entry(row, textvariable=var, show="•" if secret else "")
            e.pack(fill="x", pady=(4, 0))
            return e

        def section(title):
            ttk.Label(wrap, text=title.upper(),
                      foreground=PALETTE["accent"],
                      background=PALETTE["bg"],
                      font=FONTS["tiny"]).pack(anchor="w", pady=(18, 4))

        # LLM Provider
        section("LLM Provider")
        self.provider_var = StringVar(value=s.get("llm_provider", "groq"))
        prov_frame = ttk.Frame(wrap, style="Bg.TFrame"); prov_frame.pack(fill="x", pady=(0, 4))
        ttk.Radiobutton(prov_frame, text="Groq · Llama 3.3 70B (fast, free, recommended)",
                        value="groq", variable=self.provider_var
                        ).pack(anchor="w", pady=2)
        ttk.Radiobutton(prov_frame, text="Gemini 2.5 Flash (free, multimodal — needed for brand extraction)",
                        value="gemini", variable=self.provider_var
                        ).pack(anchor="w", pady=2)

        section("Gemini")
        self.gem_var = StringVar(value=s.get("gemini_api_key", ""))
        field_row(wrap, "API Key", self.gem_var, secret=True)
        row = ttk.Frame(wrap, style="Bg.TFrame"); row.pack(fill="x", pady=(8, 4))
        ttk.Label(row, text="Model", style="HintBg.TLabel", font=FONTS["small"]
                  ).pack(anchor="w")
        self.gem_model_var = StringVar(value=s.get("model", "gemini-2.5-flash"))
        ttk.Combobox(row, textvariable=self.gem_model_var, state="readonly",
                     values=["gemini-2.5-flash", "gemini-2.5-pro",
                              "gemini-2.5-flash-lite", "gemini-2.0-flash"]
                     ).pack(fill="x", pady=(4, 0))

        section("Groq")
        self.grq_var = StringVar(value=s.get("groq_api_key", ""))
        field_row(wrap, "API Key", self.grq_var, secret=True)
        row = ttk.Frame(wrap, style="Bg.TFrame"); row.pack(fill="x", pady=(8, 4))
        ttk.Label(row, text="Model", style="HintBg.TLabel", font=FONTS["small"]
                  ).pack(anchor="w")
        self.grq_model_var = StringVar(value=s.get("groq_model", "llama-3.3-70b-versatile"))
        try:
            import llm_provider as _lp
            groq_models = _lp.GROQ_MODELS
        except Exception:
            groq_models = ["llama-3.3-70b-versatile"]
        ttk.Combobox(row, textvariable=self.grq_model_var, state="readonly",
                     values=groq_models).pack(fill="x", pady=(4, 0))

        section("Intelligence Sources")
        self.apify_var = StringVar(value=s.get("apify_token", ""))
        field_row(wrap, "Apify Token (competitor scraping)", self.apify_var, secret=True)
        self.news_var = StringVar(value=s.get("news_api_key", ""))
        field_row(wrap, "NewsAPI Key (free)", self.news_var, secret=True)
        self.tavily_var = StringVar(value=s.get("tavily_api_key", ""))
        field_row(wrap, "Tavily API Key (web research)", self.tavily_var, secret=True)

        section("Designer · Freepik")
        self.freepik_var = StringVar(value=s.get("freepik_api_key", ""))
        field_row(wrap, "Freepik API Key", self.freepik_var, secret=True)
        row = ttk.Frame(wrap, style="Bg.TFrame"); row.pack(fill="x", pady=(8, 4))
        ttk.Label(row, text="Engine", style="HintBg.TLabel", font=FONTS["small"]
                  ).pack(anchor="w")
        self.freepik_engine_var = StringVar(value=s.get("freepik_engine", "mystic"))
        ttk.Combobox(row, textvariable=self.freepik_engine_var, state="readonly",
                     values=["mystic", "imagen3"]).pack(fill="x", pady=(4, 0))

        section("Agency")
        self.agency_name_var = StringVar(value=s.get("agency_name", "PerformEdge"))
        field_row(wrap, "Agency name (appears on PPT footers)", self.agency_name_var)

        # Actions
        actions = ttk.Frame(wrap, style="Bg.TFrame")
        actions.pack(fill="x", pady=(28, 0))
        actions.columnconfigure(0, weight=1)
        ttk.Button(actions, text="Cancel", style="Ghost.TButton",
                   command=self.destroy).grid(row=0, column=0, sticky="w")
        ttk.Button(actions, text="Save", style="Accent.TButton",
                   command=self.save).grid(row=0, column=1, sticky="e")

    def save(self):
        existing = core.load_settings()
        existing.update({
            "llm_provider": self.provider_var.get().strip(),
            "gemini_api_key": self.gem_var.get().strip(),
            "model": self.gem_model_var.get().strip(),
            "groq_api_key": self.grq_var.get().strip(),
            "groq_model": self.grq_model_var.get().strip(),
            "apify_token": self.apify_var.get().strip(),
            "news_api_key": self.news_var.get().strip(),
            "freepik_api_key": self.freepik_var.get().strip(),
            "freepik_engine": self.freepik_engine_var.get().strip(),
            "tavily_api_key": self.tavily_var.get().strip(),
            "agency_name": self.agency_name_var.get().strip() or "PerformEdge",
        })
        core.save_settings(existing)
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════
#                     CONNECT INSTAGRAM DIALOG
# ═══════════════════════════════════════════════════════════════════════
class ConnectInstagramDialog(Toplevel):
    GUIDE_TEXT = (
        "Step-by-step to get the three values:\n\n"
        "1. Make sure the IG account is Business / Creator + linked to a Facebook Page.\n"
        "2. https://developers.facebook.com → 'My Apps' → use existing or create Business app.\n"
        "3. Add use case: 'Manage messaging & content on Instagram'\n"
        "    + tick permissions: instagram_basic, instagram_manage_insights\n"
        "4. https://developers.facebook.com/tools/explorer/\n"
        "    • Pick your app top-right\n"
        "    • Permissions: instagram_basic, instagram_manage_insights,\n"
        "      pages_show_list, pages_read_engagement, business_management\n"
        "    • Click Generate Access Token → choose the FB Page → Continue\n"
        "5. Extend to long-lived (~60d):\n"
        "    https://developers.facebook.com/tools/debug/accesstoken/\n"
        "6. In Explorer:\n"
        "     GET /me/accounts\n"
        "       → 'id' inside the Page block = FB Page ID\n"
        "       → 'access_token' inside the same block = Page Access Token\n"
        "     GET /<PAGE-ID>?fields=instagram_business_account\n"
        "       → instagram_business_account.id = IG Account ID\n"
        "7. Paste all three → Test → Save.")

    def __init__(self, master, brand_key: str):
        super().__init__(master)
        self.brand_key = brand_key
        self.brand = core.load_brand(brand_key)
        self.title(f"Connect Instagram — {self.brand['name']}")
        self.geometry("800x720"); self.minsize(700, 640)
        self.configure(bg=PALETTE["bg"])
        self.transient(master); self.grab_set()

        existing = self.brand.get("meta_credentials") or {}

        hdr = ttk.Frame(self, style="Topbar.TFrame", padding=(24, 18))
        hdr.pack(fill="x")
        ttk.Label(hdr, text="📊  Connect Instagram", style="Title.TLabel"
                  ).pack(anchor="w")
        ttk.Label(hdr,
                  text=f"Wire {self.brand['name']}'s IG Business Account for Analyst Baba.",
                  background=PALETTE["bg_alt"], foreground=PALETTE["txt_dim"],
                  font=FONTS["body"]
                  ).pack(anchor="w", pady=(4, 0))

        body = ttk.Frame(self, style="Bg.TFrame", padding=24); body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)

        self.status_var = StringVar(value=self._status_text(existing))
        ttk.Label(body, textvariable=self.status_var, style="HintBg.TLabel",
                  font=FONTS["bold"]).grid(row=0, column=0, sticky="w", pady=(0, 14))

        # Help row
        help_row = ttk.Frame(body, style="Bg.TFrame"); help_row.grid(row=1, column=0, sticky="we", pady=(0, 10))
        help_row.columnconfigure(0, weight=1)
        ttk.Button(help_row, text="📖 Show step-by-step guide", style="Ghost.TButton",
                   command=self._show_guide).grid(row=0, column=0, sticky="w")
        ttk.Button(help_row, text="↗ Open Meta Developer console", style="Ghost.TButton",
                   command=lambda: webbrowser.open("https://developers.facebook.com/tools/explorer/")
                   ).grid(row=0, column=1, sticky="e")

        # Form card
        form_card = card(body, padding=(18, 18)); form_card.grid(row=2, column=0, sticky="we", pady=(8, 8))
        form = form_card.inner
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Facebook Page ID", style="H3.TLabel"
                  ).grid(row=0, column=0, sticky="w", padx=(0, 14), pady=8)
        self.page_id_var = StringVar(value=existing.get("page_id", ""))
        ttk.Entry(form, textvariable=self.page_id_var
                  ).grid(row=0, column=1, sticky="we", pady=8)

        ttk.Label(form, text="Instagram Account ID", style="H3.TLabel"
                  ).grid(row=1, column=0, sticky="w", padx=(0, 14), pady=8)
        self.ig_id_var = StringVar(value=existing.get("ig_account_id", ""))
        ttk.Entry(form, textvariable=self.ig_id_var
                  ).grid(row=1, column=1, sticky="we", pady=8)

        ttk.Label(form, text="Page Access Token", style="H3.TLabel"
                  ).grid(row=2, column=0, sticky="w", padx=(0, 14), pady=8)
        self.token_var = StringVar(value=existing.get("access_token", ""))
        tok = ttk.Entry(form, textvariable=self.token_var, show="•")
        tok.grid(row=2, column=1, sticky="we", pady=8)
        self.show_token_var = BooleanVar(value=False)
        def toggle():
            tok.config(show="" if self.show_token_var.get() else "•")
        ttk.Checkbutton(form, text="Show", variable=self.show_token_var,
                        command=toggle).grid(row=3, column=1, sticky="w")

        ttk.Label(body, text="TEST RESULT", style="HintBg.TLabel",
                  font=FONTS["tiny"]).grid(row=3, column=0, sticky="w", pady=(18, 6))
        self.result_text = Text(body, height=10, wrap="word",
                                  bg=PALETTE["surface"], fg=PALETTE["txt"],
                                  insertbackground=PALETTE["txt"],
                                  font=FONTS["mono"], relief="flat", borderwidth=0,
                                  padx=14, pady=12)
        self.result_text.grid(row=4, column=0, sticky="nsew")
        body.rowconfigure(4, weight=1)
        self.result_text.config(state=DISABLED)
        if existing:
            self._set_result(self._format_existing(existing))

        actions = ttk.Frame(body, style="Bg.TFrame")
        actions.grid(row=5, column=0, sticky="we", pady=(18, 0))
        actions.columnconfigure(0, weight=1)
        ttk.Button(actions, text="Disconnect", style="Ghost.TButton",
                   command=self.disconnect).grid(row=0, column=0, sticky="w")
        ttk.Button(actions, text="🧪 Test Connection", style="Ghost.TButton",
                   command=self.test).grid(row=0, column=1, sticky="e", padx=(0, 8))
        ttk.Button(actions, text="Save", style="Accent.TButton",
                   command=self.save).grid(row=0, column=2, sticky="e")

    def _status_text(self, e):
        if not e:
            return "Status: ⚪ Not connected"
        u = e.get("ig_username") or "—"
        exp = e.get("token_expires_str") or "—"
        return f"Status: ✅ Connected to @{u}  ·  Token expires: {exp}"

    def _set_result(self, t):
        self.result_text.config(state=NORMAL)
        self.result_text.delete("1.0", END); self.result_text.insert(END, t)
        self.result_text.config(state=DISABLED)

    def _show_guide(self):
        top = Toplevel(self); top.title("Meta Graph API — Setup Guide")
        top.geometry("780x600"); top.configure(bg=PALETTE["bg"])
        top.transient(self); top.grab_set()
        f = ttk.Frame(top, style="Bg.TFrame", padding=20); f.pack(fill="both", expand=True)
        f.rowconfigure(0, weight=1); f.columnconfigure(0, weight=1)
        t = Text(f, wrap="word", bg=PALETTE["surface"], fg=PALETTE["txt"],
                  font=FONTS["mono"], relief="flat", borderwidth=0, padx=16, pady=14)
        t.grid(row=0, column=0, sticky="nsew"); t.insert(END, self.GUIDE_TEXT)
        t.config(state=DISABLED)
        ttk.Button(f, text="Close", style="Accent.TButton",
                   command=top.destroy).grid(row=1, column=0, sticky="e", pady=(12, 0))

    def _format_existing(self, e):
        return ("Previously connected\n─────────────────────\n"
                f"  IG username:     @{e.get('ig_username', '—')}\n"
                f"  IG account ID:    {e.get('ig_account_id', '—')}\n"
                f"  Page name:        {e.get('page_name', '—')}\n"
                f"  Page ID:          {e.get('page_id', '—')}\n"
                f"  Connected at:     {e.get('connected_at', '—')}\n"
                f"  Token expires:    {e.get('token_expires_str', '—')}\n\n"
                "Click 🧪 Test Connection to verify the token is still valid.")

    def test(self):
        p = self.page_id_var.get().strip(); i = self.ig_id_var.get().strip(); t = self.token_var.get().strip()
        if not (p and i and t):
            messagebox.showerror("Missing", "Fill all three fields before testing."); return
        self._set_result("⏳ Testing connection… (calling Meta Graph API)")
        threading.Thread(target=self._test_worker, args=(p, i, t), daemon=True).start()

    def _test_worker(self, p, i, t):
        try:
            r = meta_client.MetaClient(p, i, t).test_connection()
            self.after(0, lambda: self._on_test_done(r))
        except Exception as e:
            err = str(e); self.after(0, lambda: self._set_result(f"✗ Unexpected error:\n{err}"))

    def _on_test_done(self, r):
        if not r.get("ok"):
            self._set_result(
                "✗ Connection failed\n─────────────────────\n"
                f"Error: {r.get('error', 'unknown')}\n\n"
                "Common causes:\n"
                "  • Token expired or invalid → regenerate from Graph API Explorer\n"
                "  • Permissions missing → ensure instagram_manage_insights is granted\n"
                "  • IG not linked to FB Page → fix on facebook.com → Page Settings\n"
                "  • Wrong IDs → use 'Show step-by-step guide'")
            self.status_var.set("Status: ❌ Test failed"); return
        f = r.get("ig_followers"); m = r.get("ig_media_count")
        out = ["✅ Connection works", "─────────────────────",
               f"  IG username:   @{r.get('ig_username')}",
               f"  IG name:        {r.get('ig_name', '')}",
               f"  Page:           {r.get('page_name')}",
               f"  Followers:      {f:,}" if f is not None else "  Followers:      n/a",
               f"  Total posts:    {m}" if m is not None else "  Total posts:    n/a",
               "",
               f"  Token valid:    {'✅ yes' if r.get('token_valid') else '⚠ unverified'}",
               f"  Token expires:  {r.get('token_expires_str') or 'unknown'}",
               "", "Click Save to persist these credentials."]
        self._set_result("\n".join(out))
        self.status_var.set(f"Status: ✅ Connection works — @{r.get('ig_username')}")
        self._last_test = r

    def save(self):
        p = self.page_id_var.get().strip(); i = self.ig_id_var.get().strip(); t = self.token_var.get().strip()
        if not (p and i and t):
            messagebox.showerror("Missing", "Fill all three fields first."); return
        try:
            meta_client.save_meta_credentials(
                brand_key=self.brand_key, brands_dir=core.BRANDS_DIR,
                page_id=p, ig_account_id=i, access_token=t,
                test_result=getattr(self, "_last_test", None))
            messagebox.showinfo("Saved", "Credentials stored. Analyst Baba can now pull insights.")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def disconnect(self):
        if not messagebox.askyesno("Disconnect?",
                                     "Remove Meta credentials from this brand?"): return
        try:
            meta_client.clear_meta_credentials(self.brand_key, core.BRANDS_DIR)
            self.page_id_var.set(""); self.ig_id_var.set(""); self.token_var.set("")
            self._set_result("Disconnected.")
            self.status_var.set("Status: ⚪ Not connected")
        except Exception as e:
            messagebox.showerror("Failed", str(e))


# ═══════════════════════════════════════════════════════════════════════
#                       NEW BRAND DIALOG
# ═══════════════════════════════════════════════════════════════════════
class NewBrandDialog(Toplevel):
    def __init__(self, master, on_saved=None):
        super().__init__(master)
        self.title("Add New Brand"); self.geometry("860x720"); self.minsize(760, 640)
        self.configure(bg=PALETTE["bg"])
        self.transient(master); self.grab_set()
        self.on_saved = on_saved
        self.file_paths = []
        self.profile = None

        hdr = ttk.Frame(self, style="Topbar.TFrame", padding=(24, 18)); hdr.pack(fill="x")
        ttk.Label(hdr, text="✨  Add New Brand", style="Title.TLabel").pack(anchor="w")
        ttk.Label(hdr, text="Drop guidelines (PDF / PPTX / DOCX / images) — Gemini extracts everything.",
                  background=PALETTE["bg_alt"], foreground=PALETTE["txt_dim"],
                  font=FONTS["body"]).pack(anchor="w", pady=(4, 0))

        self.container = ttk.Frame(self, style="Bg.TFrame", padding=24)
        self.container.pack(fill="both", expand=True)
        self._build_step1()

    def _build_step1(self):
        for c in self.container.winfo_children(): c.destroy()
        f = self.container; f.columnconfigure(0, weight=1)

        ttk.Label(f, text="STEP 1 — Upload Brand Guidelines", style="H1.TLabel",
                  background=PALETTE["bg"]).grid(row=0, column=0, sticky="w")
        ttk.Label(f, text="PDF · PPTX · DOCX · PNG / JPG · TXT — any mix.",
                  style="HintBg.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 14))

        lc = card(f, padding=(2, 2)); lc.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        f.rowconfigure(2, weight=1)
        inner = lc.inner; inner.columnconfigure(0, weight=1); inner.rowconfigure(0, weight=1)
        self.file_listbox = Listbox(inner, selectmode=SINGLE, height=10,
                                     bg=PALETTE["surface"], fg=PALETTE["txt"],
                                     font=FONTS["body"], relief="flat", borderwidth=0,
                                     activestyle="none", selectbackground=PALETTE["accent"])
        self.file_listbox.grid(row=0, column=0, sticky="nsew")
        sb = Scrollbar(inner, orient="vertical", command=self.file_listbox.yview)
        sb.grid(row=0, column=1, sticky="ns"); self.file_listbox.config(yscrollcommand=sb.set)
        self._refresh_file_list()

        btns = ttk.Frame(f, style="Bg.TFrame"); btns.grid(row=3, column=0, sticky="we", pady=(0, 14))
        ttk.Button(btns, text="+ Add Files", style="Ghost.TButton",
                   command=self.add_files).pack(side="left")
        ttk.Button(btns, text="− Remove Selected", style="Ghost.TButton",
                   command=self.remove_selected).pack(side="left", padx=(8, 0))

        self.s1_progress = ttk.Progressbar(f, mode="indeterminate")
        self.s1_progress.grid(row=4, column=0, sticky="we", pady=(4, 4))
        self.s1_log = ttk.Label(f, text="", style="HintBg.TLabel", wraplength=780, justify="left")
        self.s1_log.grid(row=5, column=0, sticky="w", pady=(2, 14))

        act = ttk.Frame(f, style="Bg.TFrame"); act.grid(row=6, column=0, sticky="we", pady=(8, 0))
        act.columnconfigure(0, weight=1)
        ttk.Button(act, text="Cancel", style="Ghost.TButton",
                   command=self.destroy).grid(row=0, column=0, sticky="w")
        self.extract_btn = ttk.Button(act, text="🔍 Extract Brand Profile",
                                        style="Accent.TButton",
                                        command=self.start_extraction)
        self.extract_btn.grid(row=0, column=1, sticky="e")

    def _refresh_file_list(self):
        self.file_listbox.delete(0, END)
        for fp in self.file_paths:
            kb = Path(fp).stat().st_size // 1024 if Path(fp).exists() else 0
            self.file_listbox.insert(END, f"    {Path(fp).name}    ({kb:,} KB)")
        if not self.file_paths:
            self.file_listbox.insert(END, "    (no files added yet)")

    def add_files(self):
        ps = filedialog.askopenfilenames(title="Brand Guideline Files",
            filetypes=[("All supported", "*.pdf *.png *.jpg *.jpeg *.webp *.pptx *.docx *.txt *.md"),
                       ("PDF", "*.pdf"), ("Images", "*.png *.jpg *.jpeg *.webp"),
                       ("PowerPoint", "*.pptx"), ("Word", "*.docx"), ("All", "*.*")])
        for p in ps:
            if p not in self.file_paths: self.file_paths.append(p)
        self._refresh_file_list()

    def remove_selected(self):
        s = self.file_listbox.curselection()
        if s and self.file_paths and s[0] < len(self.file_paths):
            self.file_paths.pop(s[0]); self._refresh_file_list()

    def _log_s1(self, m):
        c = self.s1_log.cget("text"); self.s1_log.config(text=(c + "\n" + m).strip()[-1500:])
        self.update_idletasks()

    def start_extraction(self):
        if not self.file_paths:
            messagebox.showwarning("No files", "Add at least one file."); return
        self.extract_btn.config(state=DISABLED); self.s1_progress.start(12); self._log_s1("Starting…")
        threading.Thread(target=self._extract_worker, daemon=True).start()

    def _extract_worker(self):
        try:
            s = core.load_settings()
            self.profile = brand_extractor.extract_brand_from_files(
                file_paths=self.file_paths, api_key=s["gemini_api_key"],
                model_name=s.get("model", "gemini-2.5-flash"), log_callback=self._log_s1)
            self.after(0, self._build_step2)
        except Exception as e:
            self.after(0, lambda: self._on_err(e))

    def _on_err(self, e):
        self.s1_progress.stop(); self.extract_btn.config(state=NORMAL)
        messagebox.showerror("Extraction failed", str(e))

    def _build_step2(self):
        self.s1_progress.stop()
        for c in self.container.winfo_children(): c.destroy()
        p = self.profile; f = self.container
        f.columnconfigure(0, weight=1); f.rowconfigure(2, weight=1)
        ttk.Label(f, text="STEP 2 — Review & Edit", style="H1.TLabel",
                  background=PALETTE["bg"]).grid(row=0, column=0, sticky="w")
        ttk.Label(f, text="Auto-extracted. Edit anything before saving.",
                  style="HintBg.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 14))

        cv = Canvas(f, bg=PALETTE["bg"], highlightthickness=0)
        cv.grid(row=2, column=0, sticky="nsew")
        sb = Scrollbar(f, orient="vertical", command=cv.yview)
        sb.grid(row=2, column=1, sticky="ns"); cv.config(yscrollcommand=sb.set)
        form = ttk.Frame(cv, style="Bg.TFrame", padding=4)
        cv.create_window((0, 0), window=form, anchor="nw")
        form.columnconfigure(1, weight=1)
        cv.bind_all("<MouseWheel>", lambda e: cv.yview_scroll(int(-1*(e.delta/120)), "units"))

        self.fields = {}
        def text_field(row, label, key, default=""):
            ttk.Label(form, text=label, style="HintBg.TLabel"
                      ).grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=4)
            v = StringVar(value=str(default))
            ttk.Entry(form, textvariable=v).grid(row=row, column=1, sticky="we", pady=4)
            self.fields[key] = ("entry", v)
        def multi(row, label, key, default="", h=4):
            ttk.Label(form, text=label, style="HintBg.TLabel"
                      ).grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=4)
            t = Text(form, height=h, wrap="word", font=FONTS["small"],
                     bg=PALETTE["surface"], fg=PALETTE["txt"],
                     insertbackground=PALETTE["txt"], relief="flat",
                     borderwidth=0, padx=10, pady=8)
            t.grid(row=row, column=1, sticky="we", pady=4); t.insert("1.0", default)
            self.fields[key] = ("text", t)
        def L(x): return "\n".join(str(i) for i in x) if isinstance(x, list) else str(x or "")

        sections = [
            ("IDENTITY", [
                (text_field, "Brand Name", "name", p.get("name", "")),
                (text_field, "Tagline", "tagline", p.get("tagline", "")),
                (multi, "Alt Taglines (one per line)", "alt_taglines", L(p.get("alt_taglines", []))),
                (text_field, "Category", "category", p.get("category", "")),
                (text_field, "Location", "location", p.get("location", "")),
                (multi, "Products / Services (one per line)", "products",
                 L(p.get("products_or_services") or p.get("products_current") or p.get("services") or [])),
            ]),
            ("VISUAL", [
                (text_field, "Primary Color", "cp", p.get("colors", {}).get("primary", "")),
                (text_field, "Secondary Color", "cs", p.get("colors", {}).get("secondary", "")),
                (text_field, "Accent Color", "ca", p.get("colors", {}).get("accent", "")),
                (text_field, "Headline Font", "fh", p.get("fonts", {}).get("headline", "")),
                (text_field, "Body Font", "fb", p.get("fonts", {}).get("body", "")),
            ]),
            ("AUDIENCE", [
                (multi, "Primary Audience", "ap", p.get("audience", {}).get("primary", "")),
                (multi, "Pain Points (one per line)", "apa", L(p.get("audience", {}).get("pain_points", []))),
                (multi, "Desires (one per line)", "ad", L(p.get("audience", {}).get("desires", []))),
            ]),
            ("TONE & VOICE", [
                (text_field, "Personality", "tp", p.get("tone", {}).get("personality", "")),
                (multi, "Voice", "tv", p.get("tone", {}).get("voice", ""), 3),
                (multi, "Writing Rules (one per line)", "tr", L(p.get("tone", {}).get("rules", [])), 7),
            ]),
            ("LANGUAGE", [
                (multi, "Signature Phrases", "sp", L(p.get("signature_phrases", [])), 6),
                (multi, "Do NOT Use", "dn", L(p.get("do_not_use", [])), 6),
                (text_field, "Story Formula", "sf", p.get("story_formula", "")),
                (multi, "CTA Styles", "cta", L(p.get("cta_styles", [])), 5),
                (multi, "Compliance Notes", "cn", L(p.get("compliance_notes", [])), 3),
            ]),
        ]
        r = 0
        for stitle, fields in sections:
            ttk.Label(form, text=stitle, foreground=PALETTE["accent"],
                      background=PALETTE["bg"],
                      font=FONTS["bold"]).grid(row=r, column=0, columnspan=2,
                                                  sticky="w", pady=(14, 6))
            r += 1
            for spec in fields:
                fn, *args = spec; fn(r, *args); r += 1

        form.update_idletasks(); cv.configure(scrollregion=cv.bbox("all"))
        a = ttk.Frame(f, style="Bg.TFrame"); a.grid(row=3, column=0, columnspan=2, sticky="we", pady=(14, 0))
        a.columnconfigure(0, weight=1)
        ttk.Button(a, text="← Back", style="Ghost.TButton",
                   command=self._build_step1).grid(row=0, column=0, sticky="w")
        ttk.Button(a, text="Save Brand", style="Accent.TButton",
                   command=self.save_brand).grid(row=0, column=1, sticky="e")

    def _g(self, k):
        kind, w = self.fields[k]
        return w.get().strip() if kind == "entry" else w.get("1.0", END).strip()
    def _gl(self, k): return [l.strip() for l in self._g(k).splitlines() if l.strip()]

    def save_brand(self):
        try:
            profile = {
                "name": self._g("name"), "tagline": self._g("tagline"),
                "alt_taglines": self._gl("alt_taglines"),
                "category": self._g("category"), "location": self._g("location"),
                "products_or_services": self._gl("products"),
                "colors": {"primary": self._g("cp"), "secondary": self._g("cs"), "accent": self._g("ca")},
                "fonts": {"headline": self._g("fh"), "body": self._g("fb")},
                "audience": {"primary": self._g("ap"),
                              "pain_points": self._gl("apa"),
                              "desires": self._gl("ad")},
                "tone": {"personality": self._g("tp"), "voice": self._g("tv"),
                          "rules": self._gl("tr")},
                "signature_phrases": self._gl("sp"),
                "do_not_use": self._gl("dn"),
                "story_formula": self._g("sf"),
                "cta_styles": self._gl("cta"),
                "compliance_notes": self._gl("cn"),
                "platforms_active": ["Instagram", "Facebook"],
            }
            if not profile["name"]:
                messagebox.showerror("Missing", "Brand name is required."); return
            profile = brand_extractor._normalize_profile(profile)
            k = brand_extractor.save_brand_profile(profile, core.BRANDS_DIR)
            messagebox.showinfo("Saved", f"Brand '{profile['name']}' saved.")
            if self.on_saved: self.on_saved(new_brand_key=k)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Save error", str(e))


# ═══════════════════════════════════════════════════════════════════════
#                  BRAND ASSETS DIALOG (full-featured)
# ═══════════════════════════════════════════════════════════════════════
class BrandAssetsDialog(Toplevel):
    def __init__(self, master, brand_key: str):
        super().__init__(master)
        self.brand_key = brand_key
        self.brand = core.load_brand(brand_key)
        self.title(f"Brand Assets — {self.brand['name']}")
        self.geometry("900x760"); self.minsize(820, 700)
        self.configure(bg=PALETTE["bg"])
        self.transient(master); self.grab_set()

        self._logo_files = {"primary": None, "white": None, "black": None}
        self._product_rows = []
        self._guideline_files = []
        self._reference_files = []

        e = compositor.get_brand_assets(self.brand, core.BRANDS_DIR)
        for v, p in e["logos"].items():
            if p: self._logo_files[v] = p
        prefilled_products = list(e["products"].items())

        assets_dir = core.BRANDS_DIR / f"{brand_key}_assets"
        g_dir = assets_dir / "guidelines"; r_dir = assets_dir / "references"
        if g_dir.exists():
            self._guideline_files = [str(p) for p in g_dir.iterdir() if p.is_file()]
        if r_dir.exists():
            self._reference_files = [str(p) for p in r_dir.iterdir() if p.is_file()]

        hdr = ttk.Frame(self, style="Topbar.TFrame", padding=(24, 18)); hdr.pack(fill="x")
        ttk.Label(hdr, text="🖼  Brand Assets", style="Title.TLabel").pack(anchor="w")
        ttk.Label(hdr, text=f"Everything for {self.brand['name']} — logos, products, guidelines, references.",
                  background=PALETTE["bg_alt"], foreground=PALETTE["txt_dim"],
                  font=FONTS["body"]).pack(anchor="w", pady=(4, 0))

        tb = ttk.Frame(self, style="Bg.TFrame", padding=(24, 12)); tb.pack(fill="x")
        tb.columnconfigure(0, weight=1)
        self._count_var = StringVar()
        ttk.Label(tb, textvariable=self._count_var, style="HintBg.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(tb, text="📁 Open Assets Folder", style="Ghost.TButton",
                   command=self._open_folder).grid(row=0, column=1, padx=(8, 0))

        wrap = ttk.Frame(self, style="Bg.TFrame", padding=(24, 6, 24, 6))
        wrap.pack(fill="both", expand=True); wrap.columnconfigure(0, weight=1); wrap.rowconfigure(0, weight=1)
        cv = Canvas(wrap, bg=PALETTE["bg"], highlightthickness=0)
        cv.grid(row=0, column=0, sticky="nsew")
        sb = Scrollbar(wrap, orient="vertical", command=cv.yview)
        sb.grid(row=0, column=1, sticky="ns"); cv.config(yscrollcommand=sb.set)
        form = ttk.Frame(cv, style="Bg.TFrame", padding=4)
        fid = cv.create_window((0, 0), window=form, anchor="nw")
        form.columnconfigure(1, weight=1)
        cv.bind_all("<MouseWheel>", lambda e: cv.yview_scroll(int(-1*(e.delta/120)), "units"))
        cv.bind("<Configure>", lambda e: cv.itemconfigure(fid, width=e.width))

        def sec(parent, row, title, hint):
            ttk.Label(parent, text=title.upper(), foreground=PALETTE["accent"],
                      background=PALETTE["bg"], font=FONTS["h3"]
                      ).grid(row=row, column=0, columnspan=4, sticky="w", pady=(18, 2))
            ttk.Label(parent, text=hint, style="HintBg.TLabel"
                      ).grid(row=row+1, column=0, columnspan=4, sticky="w", pady=(0, 10))

        # LOGOS
        sec(form, 0, "Logos",
              "Transparent PNGs preferred. White variant auto-selected on dark scenes.")
        self._logo_labels = {}
        for r, v in enumerate(["primary", "white", "black"], start=2):
            t = {"primary": "Primary (color)", "white": "White", "black": "Black"}[v]
            ttk.Label(form, text=t, style="HintBg.TLabel"
                      ).grid(row=r, column=0, sticky="w", pady=5, padx=(0, 12))
            disp = StringVar(value=self._fname(self._logo_files[v]))
            self._logo_labels[v] = disp
            ttk.Label(form, textvariable=disp, background=PALETTE["bg"],
                      foreground=PALETTE["txt_dim"], font=FONTS["small"]
                      ).grid(row=r, column=1, sticky="w", pady=5)
            ttk.Button(form, text="Browse…", style="Ghost.TButton",
                       command=lambda x=v: self._pick_logo(x)
                       ).grid(row=r, column=2, sticky="e", pady=5, padx=(8, 0))
            ttk.Button(form, text="✕", style="Ghost.TButton", width=3,
                       command=lambda x=v: self._clear_logo(x)
                       ).grid(row=r, column=3, sticky="e", pady=5, padx=(4, 0))

        # PRODUCTS
        sec(form, 6, "Product Images",
              "One transparent PNG per product. Designer composites these onto scenes when the name appears in posts.")
        self.products_frame = ttk.Frame(form, style="Bg.TFrame")
        self.products_frame.grid(row=8, column=0, columnspan=4, sticky="we", pady=(0, 6))
        self.products_frame.columnconfigure(1, weight=1)

        seed = prefilled_products
        if not seed:
            raw = (self.brand.get("products_current") or
                   self.brand.get("products_or_services") or [])
            cleaned = []
            for p in raw[:8]:
                m = re.search(r"\(([^)]+)\)", p)
                if m:
                    cleaned.extend([x.strip() for x in m.group(1).split(",") if x.strip()])
                else:
                    cleaned.append(p.strip())
            seed = [(n, None) for n in cleaned[:8]]

        for n, p in seed: self._add_product_row(n, p)
        ttk.Button(form, text="+ Add Product Variant", style="Ghost.TButton",
                   command=lambda: self._add_product_row("", None)
                   ).grid(row=9, column=0, sticky="w", pady=(6, 0))

        # GUIDELINES
        sec(form, 10, "Brand Guidelines",
              "PDFs / PPT / DOCX. Used by GROOK during deep brand understanding.")
        self.guidelines_frame = ttk.Frame(form, style="Bg.TFrame")
        self.guidelines_frame.grid(row=12, column=0, columnspan=4, sticky="we", pady=(0, 6))
        self.guidelines_frame.columnconfigure(0, weight=1)
        self._refresh_docs(self.guidelines_frame, self._guideline_files, "guideline")
        ttk.Button(form, text="+ Add Guideline Documents", style="Ghost.TButton",
                   command=lambda: self._add_docs("guideline")
                   ).grid(row=13, column=0, sticky="w", pady=(6, 0))

        # REFERENCES
        sec(form, 14, "Other References",
              "Case studies, campaign decks, anything contextual. GROOK reads these too.")
        self.references_frame = ttk.Frame(form, style="Bg.TFrame")
        self.references_frame.grid(row=16, column=0, columnspan=4, sticky="we", pady=(0, 6))
        self.references_frame.columnconfigure(0, weight=1)
        self._refresh_docs(self.references_frame, self._reference_files, "reference")
        ttk.Button(form, text="+ Add Reference Documents", style="Ghost.TButton",
                   command=lambda: self._add_docs("reference")
                   ).grid(row=17, column=0, sticky="w", pady=(6, 0))

        form.update_idletasks(); cv.configure(scrollregion=cv.bbox("all"))

        act = ttk.Frame(self, style="Bg.TFrame", padding=(24, 10, 24, 18))
        act.pack(fill="x"); act.columnconfigure(0, weight=1)
        ttk.Button(act, text="Cancel", style="Ghost.TButton",
                   command=self.destroy).grid(row=0, column=0, sticky="w")
        ttk.Button(act, text="Save All Assets", style="Accent.TButton",
                   command=self.save).grid(row=0, column=1, sticky="e")
        self._refresh_count()

    def _fname(self, p): return Path(p).name if p else "(none)"
    def _open_folder(self):
        d = core.BRANDS_DIR / f"{self.brand_key}_assets"; d.mkdir(exist_ok=True)
        try: os.startfile(str(d))
        except Exception: webbrowser.open(f"file://{d}")
    def _pick_logo(self, v):
        p = filedialog.askopenfilename(title=f"Pick {v} logo",
            filetypes=[("PNG", "*.png"), ("Images", "*.png *.jpg *.jpeg *.webp"), ("All", "*.*")])
        if p: self._logo_files[v] = p; self._logo_labels[v].set(self._fname(p))
    def _clear_logo(self, v):
        self._logo_files[v] = None; self._logo_labels[v].set("(none)")
    def _add_product_row(self, name="", current_file=None):
        f = self.products_frame; r = len(self._product_rows)
        nv = StringVar(value=name); fs = {"path": current_file}; fv = StringVar(value=self._fname(current_file))
        ttk.Entry(f, textvariable=nv, width=22).grid(row=r, column=0, sticky="w", pady=3, padx=(0, 8))
        ttk.Label(f, textvariable=fv, background=PALETTE["bg"],
                  foreground=PALETTE["txt_dim"]
                  ).grid(row=r, column=1, sticky="w", pady=3)
        def pick():
            p = filedialog.askopenfilename(title=f"Pick image for {nv.get() or 'product'}",
                filetypes=[("PNG", "*.png"), ("Images", "*.png *.jpg *.jpeg *.webp"), ("All", "*.*")])
            if p: fs["path"] = p; fv.set(self._fname(p))
        ttk.Button(f, text="Browse…", style="Ghost.TButton", command=pick
                   ).grid(row=r, column=2, sticky="e", pady=3, padx=(8, 4))
        def rm():
            for w in f.grid_slaves(row=r): w.grid_forget()
            nv.set(""); fs["path"] = None
        ttk.Button(f, text="✕", style="Ghost.TButton", width=3, command=rm
                   ).grid(row=r, column=3, sticky="e", pady=3, padx=(4, 0))
        self._product_rows.append((nv, fs))
    def _add_docs(self, kind):
        ps = filedialog.askopenfilenames(title=f"Add {kind} documents",
            filetypes=[("All supported", "*.pdf *.docx *.doc *.pptx *.ppt *.txt *.md"),
                       ("PDF", "*.pdf"), ("All", "*.*")])
        store = self._guideline_files if kind == "guideline" else self._reference_files
        frame = self.guidelines_frame if kind == "guideline" else self.references_frame
        for p in ps:
            if p not in store: store.append(p)
        self._refresh_docs(frame, store, kind)
    def _refresh_docs(self, frame, files, kind):
        for w in frame.winfo_children(): w.destroy()
        if not files:
            ttk.Label(frame, text="(no documents yet)", background=PALETTE["bg"],
                      foreground=PALETTE["txt_mute"], font=FONTS["small"]
                      ).grid(row=0, column=0, sticky="w", pady=3); return
        for r, p in enumerate(files):
            ttk.Label(frame, text=f"📄  {self._fname(p)}", background=PALETTE["bg"],
                      foreground=PALETTE["txt"], font=FONTS["small"]
                      ).grid(row=r, column=0, sticky="w", pady=3)
            def mk(path=p, k=kind):
                def _r():
                    store = self._guideline_files if k == "guideline" else self._reference_files
                    if path in store: store.remove(path)
                    self._refresh_docs(frame, store, k)
                return _r
            ttk.Button(frame, text="✕", style="Ghost.TButton", width=3, command=mk()
                       ).grid(row=r, column=1, sticky="e", pady=3)
    def _refresh_count(self):
        n_l = sum(1 for v in self._logo_files.values() if v)
        n_p = sum(1 for n, fs in self._product_rows if n.get().strip() and fs.get("path"))
        self._count_var.set(f"{n_l} logo(s) · {n_p} product(s) · "
                              f"{len(self._guideline_files)} guideline(s) · "
                              f"{len(self._reference_files)} reference(s)")
    def save(self):
        try:
            import shutil
            bd = core.BRANDS_DIR
            ad = bd / f"{self.brand_key}_assets"; ad.mkdir(exist_ok=True)
            gd = ad / "guidelines"; rd = ad / "references"; pd = ad / "products"
            for d in (gd, rd, pd): d.mkdir(exist_ok=True)
            pf = {}
            for nv, fs in self._product_rows:
                n = nv.get().strip()
                if not n: continue
                if fs.get("path"): pf[n] = fs["path"]
            logos = {v: p for v, p in self._logo_files.items() if p}
            compositor.save_assets_to_brand(brand=self.brand, brands_dir=bd,
                                              brand_key=self.brand_key,
                                              logo_files=logos, product_files=pf)
            def _copy(files, target):
                existing = {p.name for p in target.iterdir() if p.is_file()}
                wanted = set()
                for src in files:
                    name = Path(src).name; wanted.add(name)
                    dst = target / name
                    try:
                        if Path(src).resolve() != dst.resolve():
                            shutil.copy(src, dst)
                    except Exception as e:
                        print(f"copy fail: {e}")
                for nm in existing - wanted:
                    try: (target / nm).unlink()
                    except Exception: pass
            _copy(self._guideline_files, gd); _copy(self._reference_files, rd)
            brand = core.load_brand(self.brand_key)
            assets = brand.get("assets", {}) or {}
            assets["guidelines"] = [f"{self.brand_key}_assets/guidelines/{Path(p).name}"
                                       for p in self._guideline_files]
            assets["references"] = [f"{self.brand_key}_assets/references/{Path(p).name}"
                                       for p in self._reference_files]
            brand["assets"] = assets
            (bd / f"{self.brand_key}.json").write_text(
                json.dumps(brand, indent=2, ensure_ascii=False), encoding="utf-8")
            messagebox.showinfo("Saved",
                                  f"Saved for {self.brand['name']}:\n"
                                  f"  Logos: {len(logos)}\n"
                                  f"  Products: {len(pf)}\n"
                                  f"  Guidelines: {len(self._guideline_files)}\n"
                                  f"  References: {len(self._reference_files)}")
            self.destroy()
        except Exception as e:
            import traceback; traceback.print_exc()
            messagebox.showerror("Save failed", str(e))


# ═══════════════════════════════════════════════════════════════════════
#                            MAIN APP
# ═══════════════════════════════════════════════════════════════════════
NAV_ITEMS = [
    ("home",       "🏠",  "Home"),
    ("grook",      "⭐",  "GROOK · Growth Planner"),
    ("analyst",    "🔮",  "Analyst Baba"),
    ("competitors","🔍",  "Competitors"),
    ("strategist", "🧠",  "Strategist"),
    ("copy",       "✦",   "Copy Writer"),
    ("designer",   "🎨",  "Designer"),
]


class App:
    def __init__(self, root):
        self.root = root
        root.title(APP_NAME)
        root.geometry("1320x860"); root.minsize(1120, 720)
        root.configure(bg=PALETTE["bg"])
        init_styles(root)

        # State
        self._current_nav = "home"
        self._views = {}    # nav_id → frame
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()
        self.des_pause_event = threading.Event()
        self.des_stop_event = threading.Event()

        # Log throttling — only call update_idletasks 5x/sec max
        import time as _time
        self._time = _time
        self._last_ui_update = 0.0

        # Layout: topbar / [sidebar | content] / statusbar
        self._build_topbar()
        body = ttk.Frame(root, style="Bg.TFrame"); body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1); body.rowconfigure(0, weight=1)
        self._build_sidebar(body)
        self._build_content_area(body)
        self._build_statusbar()

        # Global Enter key binding → trigger primary action on current view
        root.bind("<Return>", self._on_enter_pressed)
        root.bind("<KP_Enter>", self._on_enter_pressed)

        self._select_nav("home")

    def _on_enter_pressed(self, event):
        """Enter triggers the primary action for the current view (unless typing in a Text widget)."""
        try:
            w = event.widget
            # Skip if inside multi-line Text widget
            if isinstance(w, Text):
                return
            # Skip when widget is the brand combobox or settings entries
            cls = w.winfo_class() if hasattr(w, "winfo_class") else ""
            if cls == "TCombobox":
                return
        except Exception:
            pass

        primary = {
            "grook":      lambda: self.start_planner(),
            "analyst":    lambda: self.start_analyst(),
            "strategist": lambda: self.start_strategist(),
            "copy":       lambda: self.start_generation(),
            "designer":   lambda: self.start_designer(),
            "competitors": lambda: self.add_competitor() if self.comp_handle_var.get().strip()
                              else self.start_comp_refresh(),
        }.get(self._current_nav)
        if primary:
            try: primary()
            except Exception: pass

    def _ui_tick(self):
        """Throttled update_idletasks — call at most 5x/sec to avoid lag."""
        now = self._time.time()
        if now - self._last_ui_update > 0.2:
            self.root.update_idletasks()
            self._last_ui_update = now

    # ─────────────── TOPBAR ───────────────
    def _build_topbar(self):
        tb = ttk.Frame(self.root, style="Topbar.TFrame")
        tb.pack(fill="x")
        inner = ttk.Frame(tb, style="Topbar.TFrame", padding=(18, 14))
        inner.pack(fill="x"); inner.columnconfigure(1, weight=1)

        # Brand wordmark
        wm = ttk.Frame(inner, style="Topbar.TFrame"); wm.grid(row=0, column=0, sticky="w")
        ttk.Label(wm, text="◆", background=PALETTE["bg_alt"],
                  foreground=PALETTE["accent"], font=("Segoe UI Variable", 22, "bold")
                  ).pack(side="left")
        wm_text = ttk.Frame(wm, style="Topbar.TFrame")
        wm_text.pack(side="left", padx=(10, 0))
        ttk.Label(wm_text, text=APP_NAME, background=PALETTE["bg_alt"],
                  foreground=PALETTE["txt_high"], font=FONTS["h2"]
                  ).pack(anchor="w")
        ttk.Label(wm_text, text=APP_TAGLINE, background=PALETTE["bg_alt"],
                  foreground=PALETTE["txt_mute"], font=FONTS["tiny"]
                  ).pack(anchor="w")

        # Brand selector
        center = ttk.Frame(inner, style="Topbar.TFrame")
        center.grid(row=0, column=1, sticky="e", padx=(0, 12))
        ttk.Label(center, text="ACTIVE BRAND  ", background=PALETTE["bg_alt"],
                  foreground=PALETTE["txt_mute"], font=FONTS["tiny"]
                  ).pack(side="left")
        self.brand_var = StringVar()
        self.brand_combo = ttk.Combobox(center, textvariable=self.brand_var,
                                          values=self._brand_options(),
                                          state="readonly", width=36)
        self.brand_combo.pack(side="left")
        if self.brand_combo["values"]:
            self.brand_combo.current(0)
        self.brand_combo.bind("<<ComboboxSelected>>",
                                lambda e: (self._on_brand_changed(), None))

        # Right action buttons
        actions = ttk.Frame(inner, style="Topbar.TFrame")
        actions.grid(row=0, column=2, sticky="e")
        ttk.Button(actions, text="+ Brand", style="Ghost.TButton",
                   command=self.open_new_brand).pack(side="left", padx=2)
        ttk.Button(actions, text="🖼 Assets", style="Ghost.TButton",
                   command=self.open_brand_assets).pack(side="left", padx=2)
        ttk.Button(actions, text="📊 Connect IG", style="Ghost.TButton",
                   command=self.open_connect_instagram).pack(side="left", padx=2)
        ttk.Button(actions, text="⚙ Settings", style="Ghost.TButton",
                   command=self.open_settings).pack(side="left", padx=2)

        # Separator
        sep = ttk.Frame(self.root, height=1); sep.pack(fill="x")
        sep.configure(style="Bg.TFrame")
        Canvas(self.root, height=1, bg=PALETTE["border_soft"], highlightthickness=0
                ).pack(fill="x")

    # ─────────────── SIDEBAR ───────────────
    def _build_sidebar(self, parent):
        side = ttk.Frame(parent, style="Sidebar.TFrame", width=240)
        side.grid(row=0, column=0, sticky="ns")
        side.grid_propagate(False)

        # Top label
        ttk.Label(side, text="WORKSPACE", background=PALETTE["sidebar"],
                  foreground=PALETTE["txt_mute"], font=FONTS["tiny"]
                  ).pack(anchor="w", padx=20, pady=(22, 10))

        self._nav_buttons = {}
        for nav_id, icon, label in NAV_ITEMS:
            btn = self._make_nav_button(side, nav_id, icon, label)
            btn.pack(fill="x", padx=10, pady=2)
            self._nav_buttons[nav_id] = btn

        # Spacer
        sp = ttk.Frame(side, style="Sidebar.TFrame"); sp.pack(fill="both", expand=True)

        # Bottom footer with version
        foot = ttk.Frame(side, style="Sidebar.TFrame")
        foot.pack(fill="x", side="bottom", padx=20, pady=14)
        ttk.Label(foot, text=f"{APP_NAME}", background=PALETTE["sidebar"],
                  foreground=PALETTE["txt_dim"], font=FONTS["small"]
                  ).pack(anchor="w")
        ttk.Label(foot, text=f"{APP_VERSION}", background=PALETTE["sidebar"],
                  foreground=PALETTE["txt_mute"], font=FONTS["tiny"]
                  ).pack(anchor="w")

    def _make_nav_button(self, parent, nav_id, icon, label):
        """Custom nav button — Frame so we can style hover/select."""
        f = Frame(parent, bg=PALETTE["sidebar"],
                   highlightthickness=0, bd=0, cursor="hand2")
        f.configure(height=42)

        # Selection indicator (left stripe)
        stripe = Frame(f, bg=PALETTE["sidebar"], width=3)
        stripe.pack(side="left", fill="y")

        # Icon + label
        inner = Frame(f, bg=PALETTE["sidebar"])
        inner.pack(side="left", fill="both", expand=True, padx=(12, 12), pady=10)

        icon_lbl = Label(inner, text=icon, bg=PALETTE["sidebar"],
                          fg=PALETTE["txt_dim"], font=("Segoe UI Variable", 14))
        icon_lbl.pack(side="left")
        text_lbl = Label(inner, text=label, bg=PALETTE["sidebar"],
                          fg=PALETTE["txt_dim"], font=FONTS["nav"])
        text_lbl.pack(side="left", padx=(10, 0))

        widgets = [f, inner, icon_lbl, text_lbl, stripe]

        def on_enter(e):
            if self._current_nav != nav_id:
                for w in widgets: w.configure(bg=PALETTE["sidebar_hi"])
                icon_lbl.configure(bg=PALETTE["sidebar_hi"])
                text_lbl.configure(bg=PALETTE["sidebar_hi"], fg=PALETTE["txt"])
                icon_lbl.configure(fg=PALETTE["txt"])

        def on_leave(e):
            if self._current_nav != nav_id:
                for w in widgets: w.configure(bg=PALETTE["sidebar"])
                icon_lbl.configure(bg=PALETTE["sidebar"], fg=PALETTE["txt_dim"])
                text_lbl.configure(bg=PALETTE["sidebar"], fg=PALETTE["txt_dim"])

        def on_click(e):
            self._select_nav(nav_id)

        for w in widgets:
            w.bind("<Enter>", on_enter); w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)
        f._stripe = stripe; f._icon = icon_lbl; f._text = text_lbl
        return f

    def _select_nav(self, nav_id):
        # Update visuals
        for nid, btn in self._nav_buttons.items():
            stripe, icon, text = btn._stripe, btn._icon, btn._text
            if nid == nav_id:
                btn.configure(bg=PALETTE["sidebar_hi"])
                stripe.configure(bg=PALETTE["sidebar_sel"])
                icon.configure(bg=PALETTE["sidebar_hi"], fg=PALETTE["accent"])
                text.configure(bg=PALETTE["sidebar_hi"], fg=PALETTE["txt_high"])
                for child in btn.winfo_children():
                    try: child.configure(bg=PALETTE["sidebar_hi"])
                    except Exception: pass
            else:
                btn.configure(bg=PALETTE["sidebar"])
                stripe.configure(bg=PALETTE["sidebar"])
                icon.configure(bg=PALETTE["sidebar"], fg=PALETTE["txt_dim"])
                text.configure(bg=PALETTE["sidebar"], fg=PALETTE["txt_dim"])
                for child in btn.winfo_children():
                    try: child.configure(bg=PALETTE["sidebar"])
                    except Exception: pass
        self._current_nav = nav_id
        # Show the view
        for nid, v in self._views.items():
            v.grid_forget()
        if nav_id not in self._views:
            self._views[nav_id] = self._build_view(nav_id)
        self._views[nav_id].grid(row=0, column=0, sticky="nsew")
        self._refresh_statusbar()

    # ─────────────── CONTENT AREA + STATUSBAR ───────────────
    def _build_content_area(self, parent):
        self.content = ttk.Frame(parent, style="Bg.TFrame")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.columnconfigure(0, weight=1); self.content.rowconfigure(0, weight=1)

    def _build_statusbar(self):
        Canvas(self.root, height=1, bg=PALETTE["border_soft"], highlightthickness=0
                ).pack(fill="x")
        sb = ttk.Frame(self.root, style="Statusbar.TFrame")
        sb.pack(fill="x")
        inner = ttk.Frame(sb, style="Statusbar.TFrame", padding=(18, 8))
        inner.pack(fill="x")
        inner.columnconfigure(1, weight=1)
        self._status_left_var = StringVar()
        self._status_right_var = StringVar()
        ttk.Label(inner, textvariable=self._status_left_var, style="Status.TLabel"
                  ).grid(row=0, column=0, sticky="w")
        ttk.Label(inner, textvariable=self._status_right_var, style="Status.TLabel"
                  ).grid(row=0, column=1, sticky="e")

    def _refresh_statusbar(self):
        key = self._selected_brand_key()
        try:
            b = core.load_brand(key) if key else None
        except Exception:
            b = None
        if b:
            ig = b.get("meta_credentials", {}).get("ig_username")
            mc = b.get("meta_credentials")
            conn = f"  ·  @{ig}  ✅ connected" if ig else "  ·  ⚪ Meta not connected"
            self._status_left_var.set(f"Brand: {b.get('name')}{conn}")
        else:
            self._status_left_var.set("No brand selected")

        s = core.load_settings()
        prov = s.get("llm_provider", "groq").upper()
        active_view = next((n for k, _, n in NAV_ITEMS
                              if k == self._current_nav), self._current_nav)
        self._status_right_var.set(f"View: {active_view}  ·  LLM: {prov}  ·  {APP_VERSION}")

    # ─────────────── VIEW BUILDER ───────────────
    def _build_view(self, nav_id):
        # Outer container fills the content area
        outer = ttk.Frame(self.content, style="Bg.TFrame")

        # Inner scrollable region (vertical scroll for all views)
        scroll_container, inner = make_scrollable_view(outer)
        scroll_container.pack(fill="both", expand=True)

        # Padded content frame inside scroll inner
        f = ttk.Frame(inner, style="Bg.TFrame", padding=(32, 26, 32, 26))
        f.pack(fill="both", expand=True)

        if nav_id == "home":        self._build_home(f)
        elif nav_id == "grook":     self._build_grook(f)
        elif nav_id == "analyst":   self._build_analyst(f)
        elif nav_id == "competitors": self._build_competitors_view(f)
        elif nav_id == "strategist": self._build_strategist(f)
        elif nav_id == "copy":      self._build_copywriter(f)
        elif nav_id == "designer":  self._build_designer(f)
        else:
            ttk.Label(f, text="Coming soon", style="H1.TLabel",
                      background=PALETTE["bg"]).pack()
        return outer

    # ─────────────── HOME ───────────────
    def _build_home(self, f):
        f.columnconfigure(0, weight=1)
        section_heading(f, "Welcome back",
                          "Choose an agent from the sidebar or pick up where you left off.").pack(anchor="w", fill="x")

        # Metric strip
        metrics = ttk.Frame(f, style="Bg.TFrame"); metrics.pack(fill="x", pady=(20, 16))
        for i in range(4): metrics.columnconfigure(i, weight=1)
        self._home_metric_cards = []
        for i, (label, value, sub) in enumerate([
            ("BRANDS",            str(len(core.list_brands())), "loaded"),
            ("ACTIVE",            "—", "selected brand"),
            ("META CONNECTION",   "—", "Instagram"),
            ("LATEST PLAN",       "—", "from GROOK"),
        ]):
            mc = metric_card(metrics, label, value, sub)
            mc.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            self._home_metric_cards.append(mc)

        # Quick actions
        ttk.Label(f, text="QUICK ACTIONS", style="HintBg.TLabel",
                  font=FONTS["tiny"]).pack(anchor="w", pady=(8, 8))
        qa = ttk.Frame(f, style="Bg.TFrame"); qa.pack(fill="x", pady=(0, 16))
        qa.columnconfigure((0, 1, 2), weight=1)

        for i, (icon, title, desc, action) in enumerate([
            ("⭐", "Build a 30-day Plan", "GROOK audits + designs the strategy", lambda: self._select_nav("grook")),
            ("🔮", "Run Analyst Audit", "Pull live Meta data + benchmarks", lambda: self._select_nav("analyst")),
            ("🧠", "Generate Calendar", "Plan-aware monthly content topics", lambda: self._select_nav("strategist")),
        ]):
            qc = card(qa, padding=(20, 18))
            qc.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            ttk.Label(qc.inner, text=icon, foreground=PALETTE["accent"],
                      background=PALETTE["surface"], font=("Segoe UI Variable", 20)
                      ).pack(anchor="w")
            ttk.Label(qc.inner, text=title, style="H2.TLabel"
                      ).pack(anchor="w", pady=(6, 2))
            ttk.Label(qc.inner, text=desc, style="Hint.TLabel"
                      ).pack(anchor="w")
            ttk.Button(qc.inner, text="Open  →", style="Accent.TButton",
                       command=action).pack(anchor="w", pady=(14, 0))

        # Brand summary card
        ttk.Label(f, text="ACTIVE BRAND", style="HintBg.TLabel",
                  font=FONTS["tiny"]).pack(anchor="w", pady=(8, 8))
        self._home_brand_card = card(f, padding=(22, 20))
        self._home_brand_card.pack(fill="x", pady=(0, 10))
        self._refresh_home_brand_card()

    def _refresh_home_brand_card(self):
        if not hasattr(self, "_home_brand_card"): return
        c = self._home_brand_card.inner
        for w in c.winfo_children(): w.destroy()

        key = self._selected_brand_key()
        if not key:
            ttk.Label(c, text="No brand selected. Pick one in the topbar.",
                      style="Body.TLabel").pack(anchor="w"); return
        try:
            b = core.load_brand(key)
        except Exception as e:
            ttk.Label(c, text=f"Failed to load brand: {e}", style="Body.TLabel").pack(anchor="w")
            return

        # Name + category
        head = ttk.Frame(c, style="Card.TFrame")
        head.pack(fill="x")
        ttk.Label(head, text=b.get("name", "—"), style="H2.TLabel"
                  ).pack(side="left")
        ttk.Label(head, text=f"   {b.get('category', '')}", style="Hint.TLabel"
                  ).pack(side="left")

        mc = b.get("meta_credentials") or {}
        info_rows = [
            ("Tagline",       b.get("tagline", "—")),
            ("Location",      b.get("location", "—")),
            ("Instagram",     f"@{mc.get('ig_username')}" if mc.get("ig_username") else "Not connected"),
            ("Token expiry",  mc.get("token_expires_str") or "—"),
        ]
        for label, val in info_rows:
            row = ttk.Frame(c, style="Card.TFrame")
            row.pack(fill="x", pady=(6, 0))
            ttk.Label(row, text=f"{label}", style="Hint.TLabel", width=14
                      ).pack(side="left")
            ttk.Label(row, text=str(val), style="Body.TLabel"
                      ).pack(side="left", padx=(6, 0))

        # Update home metrics
        if hasattr(self, "_home_metric_cards"):
            # ACTIVE card
            for inner in self._home_metric_cards[1].inner.winfo_children():
                inner.destroy()
            mc1 = self._home_metric_cards[1].inner
            ttk.Label(mc1, text="ACTIVE", foreground=PALETTE["txt_mute"],
                      background=PALETTE["surface"], font=FONTS["tiny"]
                      ).pack(anchor="w")
            ttk.Label(mc1, text=b.get("name", "—"), foreground=PALETTE["txt_high"],
                      background=PALETTE["surface"], font=FONTS["h2"]
                      ).pack(anchor="w", pady=(6, 0))

            # META card
            mc2 = self._home_metric_cards[2].inner
            for w in mc2.winfo_children(): w.destroy()
            ttk.Label(mc2, text="META CONNECTION", foreground=PALETTE["txt_mute"],
                      background=PALETTE["surface"], font=FONTS["tiny"]
                      ).pack(anchor="w")
            conn = "Connected" if mc.get("ig_username") else "Not connected"
            color = PALETTE["success"] if mc.get("ig_username") else PALETTE["warning"]
            ttk.Label(mc2, text=conn, foreground=color,
                      background=PALETTE["surface"], font=FONTS["h2"]
                      ).pack(anchor="w", pady=(6, 0))
            sub = f"@{mc.get('ig_username')}" if mc.get("ig_username") else "Click 📊 Connect IG"
            ttk.Label(mc2, text=sub, style="Caption.TLabel"
                      ).pack(anchor="w", pady=(2, 0))

            # PLAN card
            mc3 = self._home_metric_cards[3].inner
            for w in mc3.winfo_children(): w.destroy()
            ttk.Label(mc3, text="LATEST PLAN", foreground=PALETTE["txt_mute"],
                      background=PALETTE["surface"], font=FONTS["tiny"]
                      ).pack(anchor="w")
            try:
                s = growth_planner.load_strategy(core.BRANDS_DIR, key)
            except Exception:
                s = None
            if s:
                gen = (s.get("_meta", {}) or {}).get("generated_at", "")[:10]
                ttk.Label(mc3, text="Generated", foreground=PALETTE["success"],
                          background=PALETTE["surface"], font=FONTS["h2"]
                          ).pack(anchor="w", pady=(6, 0))
                ttk.Label(mc3, text=gen or "—", style="Caption.TLabel"
                          ).pack(anchor="w", pady=(2, 0))
            else:
                ttk.Label(mc3, text="None yet", foreground=PALETTE["warning"],
                          background=PALETTE["surface"], font=FONTS["h2"]
                          ).pack(anchor="w", pady=(6, 0))
                ttk.Label(mc3, text="Run GROOK", style="Caption.TLabel"
                          ).pack(anchor="w", pady=(2, 0))

    # ─────────────── GROOK ───────────────
    def _build_grook(self, f):
        f.columnconfigure(0, weight=1)
        section_heading(f, "GROOK · Growth Planner",
                          "Audits the brand · runs Tavily research · harvests trends · "
                          "produces a 30-day plan. Auto-reads Analyst Baba for existing brands."
                          ).pack(anchor="w", fill="x", pady=(0, 14))

        # Mode + Version status strip
        status_strip = ttk.Frame(f, style="Bg.TFrame")
        status_strip.pack(fill="x", pady=(0, 14))
        status_strip.columnconfigure(0, weight=1); status_strip.columnconfigure(1, weight=1); status_strip.columnconfigure(2, weight=1)

        # Build 3 status cards
        self._grook_mode_card = card(status_strip, padding=(16, 12))
        self._grook_mode_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self._grook_version_card = card(status_strip, padding=(16, 12))
        self._grook_version_card.grid(row=0, column=1, sticky="nsew", padx=6)

        self._grook_analyst_card = card(status_strip, padding=(16, 12))
        self._grook_analyst_card.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

        self._refresh_grook_status_strip()

        c1 = card(f, padding=(22, 20)); c1.pack(fill="x", pady=(0, 12))
        ic = c1.inner; ic.columnconfigure(0, weight=1); ic.columnconfigure(1, weight=1)

        # Website
        ttk.Label(ic, text="BRAND WEBSITE URL", style="Hint.TLabel"
                  ).grid(row=0, column=0, columnspan=2, sticky="w")
        self.planner_url_var = StringVar()
        ttk.Entry(ic, textvariable=self.planner_url_var
                  ).grid(row=1, column=0, columnspan=2, sticky="we", pady=(4, 12))

        # Social handles row
        ttk.Label(ic, text="INSTAGRAM HANDLE", style="Hint.TLabel"
                  ).grid(row=2, column=0, sticky="w", padx=(0, 8))
        ttk.Label(ic, text="FACEBOOK PAGE / URL", style="Hint.TLabel"
                  ).grid(row=2, column=1, sticky="w", padx=(8, 0))
        self.planner_ig_var = StringVar()
        self.planner_fb_var = StringVar()
        ttk.Entry(ic, textvariable=self.planner_ig_var
                  ).grid(row=3, column=0, sticky="we", pady=(4, 12), padx=(0, 8))
        ttk.Entry(ic, textvariable=self.planner_fb_var
                  ).grid(row=3, column=1, sticky="we", pady=(4, 12), padx=(8, 0))

        # Analytics
        ttk.Label(ic, text="ANALYTICS NOTES  (optional)", style="Hint.TLabel"
                  ).grid(row=4, column=0, columnspan=2, sticky="w")
        self.planner_analytics_text = Text(ic, height=3, wrap="word",
                                              bg=PALETTE["bg_alt"], fg=PALETTE["txt"],
                                              insertbackground=PALETTE["txt"],
                                              font=FONTS["body"], relief="flat",
                                              borderwidth=0, padx=10, pady=8)
        self.planner_analytics_text.grid(row=5, column=0, columnspan=2, sticky="we", pady=(4, 6))

        # File pickers
        files_row = ttk.Frame(ic, style="Card.TFrame")
        files_row.grid(row=6, column=0, columnspan=2, sticky="we", pady=(0, 12))
        files_row.columnconfigure(0, weight=1)
        self.planner_analytics_files = []
        self.planner_analytics_files_var = StringVar(value="(no analytics files added)")
        ttk.Label(files_row, textvariable=self.planner_analytics_files_var,
                  style="Hint.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(files_row, text="📎 Analytics Files", style="Ghost.TButton",
                   command=self._planner_add_analytics_files
                   ).grid(row=0, column=1, padx=(8, 4))
        ttk.Button(files_row, text="Clear", style="Ghost.TButton",
                   command=self._planner_clear_analytics_files
                   ).grid(row=0, column=2)

        # Campaigns
        ttk.Label(ic, text="ONGOING CAMPAIGNS  (free text)", style="Hint.TLabel"
                  ).grid(row=7, column=0, columnspan=2, sticky="w")
        self.planner_campaigns_text = Text(ic, height=3, wrap="word",
                                              bg=PALETTE["bg_alt"], fg=PALETTE["txt"],
                                              insertbackground=PALETTE["txt"],
                                              font=FONTS["body"], relief="flat",
                                              borderwidth=0, padx=10, pady=8)
        self.planner_campaigns_text.grid(row=8, column=0, columnspan=2, sticky="we", pady=(4, 12))

        # Extra refs
        ttk.Label(ic, text="EXTRA REFERENCE FILES", style="Hint.TLabel"
                  ).grid(row=9, column=0, columnspan=2, sticky="w")
        refs_row = ttk.Frame(ic, style="Card.TFrame")
        refs_row.grid(row=10, column=0, columnspan=2, sticky="we", pady=(4, 0))
        refs_row.columnconfigure(0, weight=1)
        self.planner_refs = []
        self.planner_refs_var = StringVar(value="(no files added)")
        ttk.Label(refs_row, textvariable=self.planner_refs_var, style="Hint.TLabel"
                  ).grid(row=0, column=0, sticky="w")
        ttk.Button(refs_row, text="+ Add", style="Ghost.TButton",
                   command=self._planner_add_refs).grid(row=0, column=1, padx=(8, 4))
        ttk.Button(refs_row, text="Clear", style="Ghost.TButton",
                   command=self._planner_clear_refs).grid(row=0, column=2)

        # Actions
        act = ttk.Frame(f, style="Bg.TFrame"); act.pack(fill="x", pady=(8, 12))
        act.columnconfigure(0, weight=1)
        self.planner_status = ttk.Label(act, text="Ready", style="HintBg.TLabel")
        self.planner_status.grid(row=0, column=0, sticky="w")
        ttk.Button(act, text="📂 Open Last Strategy", style="Ghost.TButton",
                   command=self._planner_open_last).grid(row=0, column=1, padx=4)
        self.planner_btn = ttk.Button(act, text="⭐  Generate Growth Plan",
                                         style="Accent.TButton",
                                         command=self.start_planner)
        self.planner_btn.grid(row=0, column=2, padx=(8, 0))

        self.planner_progress = ttk.Progressbar(f, mode="determinate", maximum=100)
        self.planner_progress.pack(fill="x", pady=(0, 10))

        # Log card
        log_card = card(f, padding=(2, 2)); log_card.pack(fill="both", expand=True)
        log_inner = log_card.inner
        log_inner.columnconfigure(0, weight=1); log_inner.rowconfigure(0, weight=1)
        self.planner_log = Text(log_inner, wrap="word",
                                  bg=PALETTE["surface"], fg=PALETTE["txt"],
                                  insertbackground=PALETTE["txt"],
                                  font=FONTS["mono"], relief="flat", borderwidth=0,
                                  padx=14, pady=12)
        self.planner_log.grid(row=0, column=0, sticky="nsew")
        sb = Scrollbar(log_inner, orient="vertical", command=self.planner_log.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.planner_log.config(yscrollcommand=sb.set, state=DISABLED)
        self._log_planner("GROOK ready. Provide brand website + Instagram handle + campaigns.")
        self._planner_load_handles()

    def _planner_load_handles(self):
        key = self._selected_brand_key()
        if not key or not hasattr(self, "planner_ig_var"): return
        try:
            b = core.load_brand(key); sh = b.get("social_handles", {}) or {}
            self.planner_ig_var.set(sh.get("instagram", ""))
            self.planner_fb_var.set(sh.get("facebook", ""))
        except Exception: pass
        self._refresh_grook_status_strip()

    def _refresh_grook_status_strip(self):
        """Update the 3 status cards in the GROOK view (mode / version / analyst)."""
        if not hasattr(self, "_grook_mode_card"): return
        key = self._selected_brand_key()
        if not key: return

        try:
            brand = core.load_brand(key)
            mode = growth_planner.detect_brand_mode(brand, core.BRANDS_DIR, key)
            next_v = growth_planner.next_plan_version(core.BRANDS_DIR, key)
            history = growth_planner.list_plan_versions(core.BRANDS_DIR, key)
        except Exception:
            return

        # Mode card
        for w in self._grook_mode_card.inner.winfo_children(): w.destroy()
        mode_color = PALETTE["success"] if mode == "existing" else PALETTE["brand"]
        mode_label = "EXISTING BRAND" if mode == "existing" else "NEW BRAND"
        mode_sub = ("Has Meta + Analyst report — plan will be data-driven."
                    if mode == "existing"
                    else "No Meta connection yet — plan will be industry-driven.")
        ttk.Label(self._grook_mode_card.inner, text="BRAND MODE",
                  foreground=PALETTE["txt_mute"], background=PALETTE["surface"],
                  font=FONTS["tiny"]).pack(anchor="w")
        ttk.Label(self._grook_mode_card.inner, text=mode_label,
                  foreground=mode_color, background=PALETTE["surface"],
                  font=FONTS["h2"]).pack(anchor="w", pady=(4, 2))
        ttk.Label(self._grook_mode_card.inner, text=mode_sub,
                  style="Caption.TLabel", wraplength=300).pack(anchor="w")

        # Version card
        for w in self._grook_version_card.inner.winfo_children(): w.destroy()
        ttk.Label(self._grook_version_card.inner, text="PLAN VERSION",
                  foreground=PALETTE["txt_mute"], background=PALETTE["surface"],
                  font=FONTS["tiny"]).pack(anchor="w")
        ttk.Label(self._grook_version_card.inner, text=f"v{next_v}",
                  foreground=PALETTE["accent"], background=PALETTE["surface"],
                  font=FONTS["metric"]).pack(anchor="w", pady=(2, 2))
        if history:
            ttk.Label(self._grook_version_card.inner,
                      text=f"Previous: " + ", ".join(f"v{v}" for v in history[-3:]),
                      style="Caption.TLabel").pack(anchor="w")
        else:
            ttk.Label(self._grook_version_card.inner,
                      text="First plan for this brand",
                      style="Caption.TLabel").pack(anchor="w")

        # Analyst card
        for w in self._grook_analyst_card.inner.winfo_children(): w.destroy()
        ttk.Label(self._grook_analyst_card.inner, text="ANALYST BABA",
                  foreground=PALETTE["txt_mute"], background=PALETTE["surface"],
                  font=FONTS["tiny"]).pack(anchor="w")
        try:
            r = analyst_agent.latest_report(core.BRANDS_DIR, key)
        except Exception:
            r = None
        if r:
            stamp = (r.get("_meta", {}).get("generated_at") or "")[:10]
            acc = r.get("account_metrics", {}) or {}
            ttk.Label(self._grook_analyst_card.inner, text="✅ Report ready",
                      foreground=PALETTE["success"], background=PALETTE["surface"],
                      font=FONTS["h2"]).pack(anchor="w", pady=(4, 2))
            ttk.Label(self._grook_analyst_card.inner,
                      text=f"From {stamp} · ER {acc.get('avg_engagement_rate_pct', '?')}% · {acc.get('followers_now', '?')} followers",
                      style="Caption.TLabel").pack(anchor="w")
        else:
            ttk.Label(self._grook_analyst_card.inner, text="⚪ No report yet",
                      foreground=PALETTE["warning"], background=PALETTE["surface"],
                      font=FONTS["h2"]).pack(anchor="w", pady=(4, 2))
            ttk.Label(self._grook_analyst_card.inner,
                      text="Run Analyst Baba first for sharper plan",
                      style="Caption.TLabel").pack(anchor="w")

    def _planner_add_refs(self):
        ps = filedialog.askopenfilenames(title="Add references",
            filetypes=[("All supported", "*.pdf *.docx *.doc *.pptx *.txt *.md"),
                       ("All", "*.*")])
        for p in ps:
            if p not in self.planner_refs: self.planner_refs.append(p)
        self._planner_refs_update()
    def _planner_clear_refs(self): self.planner_refs = []; self._planner_refs_update()
    def _planner_refs_update(self):
        if not self.planner_refs: self.planner_refs_var.set("(no files added)")
        else:
            self.planner_refs_var.set(f"{len(self.planner_refs)} file(s) attached")
    def _planner_add_analytics_files(self):
        ps = filedialog.askopenfilenames(title="Add analytics reports",
            filetypes=[("All supported", "*.xlsx *.xlsm *.pdf *.png *.jpg *.jpeg *.webp"),
                       ("Excel", "*.xlsx *.xlsm"), ("PDF", "*.pdf"),
                       ("Images", "*.png *.jpg *.jpeg *.webp"), ("All", "*.*")])
        for p in ps:
            if p not in self.planner_analytics_files: self.planner_analytics_files.append(p)
        self._planner_analytics_update()
    def _planner_clear_analytics_files(self):
        self.planner_analytics_files = []; self._planner_analytics_update()
    def _planner_analytics_update(self):
        if not self.planner_analytics_files:
            self.planner_analytics_files_var.set("(no analytics files added)")
        else:
            self.planner_analytics_files_var.set(
                f"{len(self.planner_analytics_files)} file(s) attached")
    def _planner_open_last(self):
        out_dir = Path(DEFAULT_OUTPUT_DIR)
        candidates = sorted(out_dir.glob("*_Strategy_*.pptx"),
                              key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            messagebox.showinfo("None yet", "No strategy PPT yet. Generate one first."); return
        try: os.startfile(str(candidates[0]))
        except Exception: pass
    def _log_planner(self, m):
        self.planner_log.config(state=NORMAL); self.planner_log.insert(END, m + "\n")
        self.planner_log.see(END); self.planner_log.config(state=DISABLED)
        self._ui_tick()
    def _planner_progress_cb(self, c, t, label):
        pct = 0 if t == 0 else int(c / t * 100)
        self.planner_progress["value"] = pct
        self.planner_status.config(text=f"Step {c}/{t} · {label}")
        self._ui_tick()

    def start_planner(self):
        key = self._selected_brand_key()
        if not key: messagebox.showerror("Pick brand", "Select a brand first."); return
        url = self.planner_url_var.get().strip()
        s = core.load_settings()
        prov = s.get("llm_provider", "groq")
        if (prov == "groq" and not s.get("groq_api_key")) or (prov == "gemini" and not s.get("gemini_api_key")):
            messagebox.showerror("Missing API key", "Add your LLM API key in Settings."); return

        # Token health check — warn if expired or expiring soon
        try:
            brand = core.load_brand(key)
            mc = brand.get("meta_credentials") or {}
            exp_ts = mc.get("token_expires_at")
            if exp_ts:
                import datetime as _dt
                exp_dt = _dt.datetime.fromtimestamp(int(exp_ts))
                hours_left = (exp_dt - _dt.datetime.now()).total_seconds() / 3600
                if hours_left < 0:
                    if not messagebox.askyesno(
                        "Meta token expired",
                        f"Your Meta token for this brand expired "
                        f"{exp_dt.strftime('%d %b %Y, %H:%M')}.\n\n"
                        "Analyst/Meta-related steps in GROOK will fail. "
                        "Reconnect Instagram now (📊 Connect Instagram in topbar) "
                        "and try again.\n\nProceed anyway in NEW BRAND mode? "
                        "(no Meta data will be used)"):
                        return
                elif hours_left < 24:
                    self._log_planner(f"⚠ Meta token expires in {hours_left:.1f}h — "
                                      f"consider re-extending via Token Debugger.")
        except Exception:
            pass

        ig = self.planner_ig_var.get().strip(); fb = self.planner_fb_var.get().strip()
        camps = self.planner_campaigns_text.get("1.0", END).strip()
        analytics = self.planner_analytics_text.get("1.0", END).strip()
        afiles = list(self.planner_analytics_files); refs = list(self.planner_refs)

        self.planner_btn.config(state=DISABLED)
        self.planner_progress["value"] = 0
        self._log_planner("─" * 60)
        self._log_planner(f"▸ Brand: {key}  ·  Website: {url or '(none)'}")
        threading.Thread(target=self._planner_worker,
                          args=(key, url, camps, refs, ig, fb, analytics, afiles),
                          daemon=True).start()

    def _planner_worker(self, key, url, camps, refs, ig, fb, an, afiles):
        try:
            client = core.make_llm_client()
            self._log_planner(f"Using LLM: {client.name.upper()} · {client.model_name}")
            result = growth_planner.run_growth_planner(
                brand_key=key, website_url=url, ongoing_campaigns=camps,
                reference_paths=refs, output_dir=str(DEFAULT_OUTPUT_DIR),
                llm_client=client, settings=core.load_settings(),
                instagram_handle=ig, facebook_handle=fb,
                manual_analytics=an, analytics_paths=afiles,
                progress_callback=self._planner_progress_cb,
                log_callback=self._log_planner)
            self.root.after(0, lambda: self._on_planner_done(result))
        except Exception as e:
            err = traceback.format_exc()
            self.root.after(0, lambda: self._on_planner_error(e, err))
    def _on_planner_done(self, r):
        self.planner_btn.config(state=NORMAL); self.planner_progress["value"] = 100
        self.planner_status.config(text="Strategy generated ✓")
        if messagebox.askyesno("Done", f"PPT saved.\nOpen now?"):
            try: os.startfile(r["pptx_path"])
            except Exception: pass
    def _on_planner_error(self, e, tb):
        self.planner_btn.config(state=NORMAL)
        self.planner_status.config(text="Failed")
        self._log_planner(f"\n✗ ERROR: {e}")
        messagebox.showerror("GROOK failed", str(e))

    # ─────────────── ANALYST ───────────────
    def _build_analyst(self, f):
        f.columnconfigure(0, weight=1)
        section_heading(f, "Analyst Baba · Continuous Intelligence",
                          "Pulls live Meta data, attributes performance to plan pillars, "
                          "compares against industry benchmarks, prescribes specific changes."
                          ).pack(anchor="w", fill="x", pady=(0, 18))

        # Setup card
        c1 = card(f, padding=(22, 20)); c1.pack(fill="x", pady=(0, 12))
        ic = c1.inner; ic.columnconfigure(1, weight=1)
        self._analyst_status_var = StringVar(value="No Meta connection on this brand.")
        ttk.Label(ic, text="META CONNECTION", style="Hint.TLabel"
                  ).grid(row=0, column=0, sticky="w", padx=(0, 16))
        ttk.Label(ic, textvariable=self._analyst_status_var, style="Body.TLabel"
                  ).grid(row=0, column=1, sticky="w")

        ttk.Label(ic, text="PERIOD", style="Hint.TLabel"
                  ).grid(row=1, column=0, sticky="w", padx=(0, 16), pady=(14, 0))
        self.analyst_period_var = IntVar(value=60)
        period_row = ttk.Frame(ic, style="Card.TFrame")
        period_row.grid(row=1, column=1, sticky="w", pady=(14, 0))
        for v in (30, 60, 90):
            ttk.Radiobutton(period_row, text=f"Last {v} days",
                            value=v, variable=self.analyst_period_var
                            ).pack(side="left", padx=(0, 14))

        # Action row
        act = ttk.Frame(f, style="Bg.TFrame"); act.pack(fill="x", pady=(0, 10))
        act.columnconfigure(0, weight=1)
        self._analyst_status_label = ttk.Label(act, text="Ready", style="HintBg.TLabel")
        self._analyst_status_label.grid(row=0, column=0, sticky="w")
        self.analyst_btn = ttk.Button(act, text="🔮  Run Audit Now",
                                         style="Accent.TButton",
                                         command=self.start_analyst)
        self.analyst_btn.grid(row=0, column=1, padx=(8, 0))

        self.analyst_progress = ttk.Progressbar(f, mode="determinate", maximum=100)
        self.analyst_progress.pack(fill="x", pady=(0, 10))

        # Output area split: log on left, latest report summary on right
        out = ttk.Frame(f, style="Bg.TFrame"); out.pack(fill="both", expand=True)
        out.columnconfigure(0, weight=2); out.columnconfigure(1, weight=3); out.rowconfigure(0, weight=1)

        # Log
        lc = card(out, padding=(2, 2)); lc.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        lci = lc.inner; lci.columnconfigure(0, weight=1); lci.rowconfigure(0, weight=1)
        self.analyst_log = Text(lci, wrap="word", bg=PALETTE["surface"], fg=PALETTE["txt"],
                                  insertbackground=PALETTE["txt"], font=FONTS["mono"],
                                  relief="flat", borderwidth=0, padx=12, pady=10)
        self.analyst_log.grid(row=0, column=0, sticky="nsew")
        sb = Scrollbar(lci, orient="vertical", command=self.analyst_log.yview)
        sb.grid(row=0, column=1, sticky="ns"); self.analyst_log.config(yscrollcommand=sb.set, state=DISABLED)

        # Report panel
        rc = card(out, padding=(2, 2)); rc.grid(row=0, column=1, sticky="nsew")
        rci = rc.inner; rci.columnconfigure(0, weight=1); rci.rowconfigure(0, weight=1)
        self.analyst_report_text = Text(rci, wrap="word",
                                          bg=PALETTE["surface"], fg=PALETTE["txt"],
                                          insertbackground=PALETTE["txt"],
                                          font=FONTS["mono"], relief="flat",
                                          borderwidth=0, padx=14, pady=12)
        self.analyst_report_text.grid(row=0, column=0, sticky="nsew")
        sb2 = Scrollbar(rci, orient="vertical", command=self.analyst_report_text.yview)
        sb2.grid(row=0, column=1, sticky="ns"); self.analyst_report_text.config(yscrollcommand=sb2.set, state=DISABLED)

        self._refresh_analyst_state()

    def _refresh_analyst_state(self):
        key = self._selected_brand_key()
        if not hasattr(self, "_analyst_status_var"): return
        try:
            b = core.load_brand(key) if key else None
        except Exception:
            b = None
        mc = (b.get("meta_credentials") if b else {}) or {}
        if mc.get("ig_username"):
            self._analyst_status_var.set(
                f"✅ Connected to @{mc['ig_username']}   ·   Token expires {mc.get('token_expires_str', '—')}")
        else:
            self._analyst_status_var.set("⚠ No Meta connection. Click 📊 Connect IG in topbar.")

        # Latest report
        if hasattr(self, "analyst_report_text"):
            self.analyst_report_text.config(state=NORMAL)
            self.analyst_report_text.delete("1.0", END)
            r = None
            try: r = analyst_agent.latest_report(core.BRANDS_DIR, key) if key else None
            except Exception: pass
            if r:
                meta = r.get("_meta", {}) or {}
                acc = r.get("account_metrics", {}) or {}
                an = r.get("analysis", {}) or {}
                lines = [
                    f"LATEST REPORT — {meta.get('generated_at', '')[:16]}",
                    f"Period: {meta.get('period_days')} days · Benchmark: {meta.get('benchmark_used')}",
                    "",
                    "── ACCOUNT METRICS ──",
                    f"  Followers: {acc.get('followers_now')}  "
                    f"(Δ {acc.get('follower_delta_period', 'n/a')})",
                    f"  Avg ER:    {acc.get('avg_engagement_rate_pct')}%  "
                    f"[{(r.get('format_grades') or {}).get('engagement_rate')}]",
                    f"  Reach %:   {acc.get('avg_reach_pct_followers')}%  "
                    f"[{(r.get('format_grades') or {}).get('reach')}]",
                    f"  Save rate: {acc.get('avg_save_rate_pct_reach')}%  "
                    f"[{(r.get('format_grades') or {}).get('save_rate')}]",
                    f"  Posts/wk:  {acc.get('posting_frequency_per_week')}",
                    "",
                    "── EXECUTIVE READ ──",
                    f"  {an.get('executive_summary', '(no summary)')}",
                ]
                if an.get("wins"):
                    lines += ["", "── WHAT'S WORKING ──"] + [f"  ✓ {w}" for w in an["wins"][:5]]
                if an.get("losses"):
                    lines += ["", "── WHAT'S NOT ──"] + [f"  ✗ {w}" for w in an["losses"][:5]]
                if an.get("actionable_recommendations"):
                    lines += ["", "── RECOMMENDED CHANGES (priority order) ──"]
                    for rec in an["actionable_recommendations"][:8]:
                        pri = rec.get("priority", "med").upper()
                        lines.append(f"  [{pri}] {rec.get('change', '')}")
                        lines.append(f"        → {rec.get('expected_impact', '')}")
                if an.get("next_15_days_focus"):
                    lines += ["", f"NEXT 15 DAYS FOCUS:", f"  {an['next_15_days_focus']}"]
                self.analyst_report_text.insert(END, "\n".join(lines))
            else:
                self.analyst_report_text.insert(END,
                    "No audit yet for this brand.\n\n"
                    "Make sure Meta is connected (📊 Connect IG in topbar),\n"
                    "then click '🔮 Run Audit Now'.\n\n"
                    "The audit pulls last 30-90 days of posts + insights,\n"
                    "attributes performance to your Growth Plan pillars,\n"
                    "and produces a structured intelligence report that\n"
                    "GROOK uses to revise the plan.")
            self.analyst_report_text.config(state=DISABLED)

    def _log_analyst(self, m):
        if not hasattr(self, "analyst_log"): return
        self.analyst_log.config(state=NORMAL); self.analyst_log.insert(END, m + "\n")
        self.analyst_log.see(END); self.analyst_log.config(state=DISABLED)
        self._ui_tick()
    def _analyst_progress_cb(self, c, t, label):
        pct = 0 if t == 0 else int(c / t * 100)
        self.analyst_progress["value"] = pct
        self._analyst_status_label.config(text=f"Step {c}/{t} · {label}")
        self._ui_tick()

    def start_analyst(self):
        key = self._selected_brand_key()
        if not key: messagebox.showerror("Pick brand", "Select a brand first."); return
        try:
            b = core.load_brand(key)
        except Exception as e:
            messagebox.showerror("Brand", str(e)); return
        if not meta_client.has_meta_credentials(b):
            messagebox.showerror("Meta not connected",
                                  "Click '📊 Connect IG' in the topbar first."); return

        # Token health check
        try:
            mc = b.get("meta_credentials") or {}
            exp_ts = mc.get("token_expires_at")
            if exp_ts:
                import datetime as _dt
                exp_dt = _dt.datetime.fromtimestamp(int(exp_ts))
                if (exp_dt - _dt.datetime.now()).total_seconds() < 0:
                    messagebox.showerror(
                        "Meta token expired",
                        f"Your Meta token expired {exp_dt.strftime('%d %b %Y, %H:%M')}.\n\n"
                        "Reconnect Instagram via 📊 Connect IG in the topbar.\n\n"
                        "Quick fix:\n"
                        "1. https://developers.facebook.com/tools/debug/accesstoken/\n"
                        "2. Paste current token → Debug → Extend Access Token\n"
                        "3. Update token in 📊 Connect IG dialog.")
                    return
        except Exception:
            pass

        period = int(self.analyst_period_var.get())
        self.analyst_btn.config(state=DISABLED)
        self.analyst_progress["value"] = 0
        self._log_analyst("─" * 60)
        self._log_analyst(f"▸ Analyst Baba: {b['name']} · last {period} days")
        threading.Thread(target=self._analyst_worker, args=(key, period), daemon=True).start()

    def _analyst_worker(self, key, period):
        try:
            report = analyst_agent.run_audit(
                brand_key=key, period_days=period,
                progress_callback=self._analyst_progress_cb,
                log_callback=self._log_analyst)
            self.root.after(0, lambda: self._on_analyst_done(report))
        except Exception as e:
            err = traceback.format_exc()
            self.root.after(0, lambda: self._on_analyst_error(e, err))
    def _on_analyst_done(self, r):
        self.analyst_btn.config(state=NORMAL); self.analyst_progress["value"] = 100
        self._analyst_status_label.config(text="Report ready ✓")
        self._refresh_analyst_state()
        messagebox.showinfo("Audit done",
                              "Report saved. GROOK will read this automatically on next plan revision.")
    def _on_analyst_error(self, e, tb):
        self.analyst_btn.config(state=NORMAL)
        self._analyst_status_label.config(text="Failed")
        self._log_analyst(f"\n✗ ERROR: {e}")
        messagebox.showerror("Analyst failed", str(e))

    # ─────────────── COMPETITORS ───────────────
    def _build_competitors_view(self, f):
        f.columnconfigure(0, weight=1)
        section_heading(f, "Competitors",
                          "Add competitor IG handles per brand. Refresh pulls posts via Apify "
                          "and analyses with Gemini Vision."
                          ).pack(anchor="w", fill="x", pady=(0, 18))

        c1 = card(f, padding=(22, 18)); c1.pack(fill="x", pady=(0, 12))
        ic = c1.inner; ic.columnconfigure(0, weight=1)
        self.comp_handle_var = StringVar()
        ttk.Label(ic, text="ADD A COMPETITOR INSTAGRAM HANDLE", style="Hint.TLabel"
                  ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Entry(ic, textvariable=self.comp_handle_var
                  ).grid(row=1, column=0, sticky="we", pady=(4, 0))
        ttk.Button(ic, text="+ Add", style="Accent.TButton",
                   command=self.add_competitor).grid(row=1, column=1, padx=(8, 0))

        list_card = card(f, padding=(18, 16)); list_card.pack(fill="x", pady=(0, 12))
        lci = list_card.inner; lci.columnconfigure(0, weight=1)
        ttk.Label(lci, text="ADDED COMPETITORS", style="Hint.TLabel"
                  ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.comp_listbox = Listbox(lci, height=6, selectmode=SINGLE,
                                       bg=PALETTE["bg_alt"], fg=PALETTE["txt"],
                                       font=FONTS["body"], relief="flat", borderwidth=0,
                                       activestyle="none", selectbackground=PALETTE["accent"])
        self.comp_listbox.grid(row=1, column=0, sticky="we")
        cact = ttk.Frame(lci, style="Card.TFrame")
        cact.grid(row=2, column=0, sticky="we", pady=(8, 0))
        cact.columnconfigure(0, weight=1)
        ttk.Button(cact, text="− Remove Selected", style="Ghost.TButton",
                   command=self.remove_competitor).grid(row=0, column=0, sticky="w")
        self.comp_refresh_btn = ttk.Button(cact, text="🔄 Refresh All Insights",
                                              style="Accent.TButton",
                                              command=self.start_comp_refresh)
        self.comp_refresh_btn.grid(row=0, column=1, sticky="e")

        self.comp_progress = ttk.Progressbar(f, mode="indeterminate")
        self.comp_progress.pack(fill="x", pady=(0, 10))

        ins_card = card(f, padding=(2, 2)); ins_card.pack(fill="both", expand=True)
        ici = ins_card.inner; ici.columnconfigure(0, weight=1); ici.rowconfigure(0, weight=1)
        self.comp_text = Text(ici, wrap="word", bg=PALETTE["surface"], fg=PALETTE["txt"],
                                insertbackground=PALETTE["txt"], font=FONTS["mono"],
                                relief="flat", borderwidth=0, padx=14, pady=12)
        self.comp_text.grid(row=0, column=0, sticky="nsew")
        sb = Scrollbar(ici, orient="vertical", command=self.comp_text.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.comp_text.config(yscrollcommand=sb.set, state=DISABLED)
        self._refresh_comp_view()

    def _comp_data(self):
        key = self._selected_brand_key()
        if not key: return None, None
        return key, competitor_analyzer.load_competitors(core.BRANDS_DIR, key)
    def _refresh_comp_view(self):
        if not hasattr(self, "comp_listbox"): return
        self.comp_listbox.delete(0, END); self._set_comp_text("")
        key, data = self._comp_data()
        if not data: self.comp_listbox.insert(END, "  (pick a brand at top)"); return
        for h in data.get("competitor_handles", []):
            per = data.get("per_competitor", {}).get(h, {})
            st = ""
            if per.get("error"): st = f"   ⚠ {per['error'][:50]}"
            elif per.get("_meta", {}).get("analyzed_at"): st = f"   ✓ {per['_meta']['analyzed_at'][:10]}"
            self.comp_listbox.insert(END, f"  @{h}{st}")
        if not data.get("competitor_handles"): self.comp_listbox.insert(END, "  (no competitors yet)")
        out = []
        if data.get("last_refreshed"): out.append(f"Last refreshed: {data['last_refreshed']}\n")
        if data.get("combined_playbook"):
            out += ["━━ CATEGORY PLAYBOOK ━━", data["combined_playbook"], ""]
        if data.get("differentiation_recommendations"):
            out += ["━━ DIFFERENTIATION ANGLES ━━"] + [f"  • {x}" for x in data["differentiation_recommendations"]] + [""]
        if data.get("saturated_themes"):
            out += ["━━ SATURATED THEMES (avoid) ━━"] + [f"  • {x}" for x in data["saturated_themes"]] + [""]
        if data.get("underused_angles"):
            out += ["━━ UNDERUSED ANGLES (exploit) ━━"] + [f"  • {x}" for x in data["underused_angles"]] + [""]
        if data.get("engagement_drivers"):
            out += ["━━ ENGAGEMENT DRIVERS ━━"] + [f"  • {x}" for x in data["engagement_drivers"]]
        if not out:
            out = ["No insights yet. Add handles, then click 'Refresh All Insights'."]
        self._set_comp_text("\n".join(out))
    def _set_comp_text(self, t):
        self.comp_text.config(state=NORMAL); self.comp_text.delete("1.0", END)
        self.comp_text.insert(END, t); self.comp_text.config(state=DISABLED)
    def _log_comp(self, m):
        self.comp_text.config(state=NORMAL); self.comp_text.insert(END, m + "\n")
        self.comp_text.see(END); self.comp_text.config(state=DISABLED)
        self._ui_tick()
    def add_competitor(self):
        raw = self.comp_handle_var.get().strip()
        if not raw: return
        key, data = self._comp_data()
        if not key: return
        c = competitor_analyzer._normalise_handle(raw)
        if not c: messagebox.showerror("Invalid", "Couldn't parse handle."); return
        h = data.setdefault("competitor_handles", [])
        if c in h: messagebox.showinfo("Exists", f"@{c} already added."); return
        h.append(c); competitor_analyzer.save_competitors(core.BRANDS_DIR, key, data)
        self.comp_handle_var.set(""); self._refresh_comp_view()
    def remove_competitor(self):
        s = self.comp_listbox.curselection()
        if not s: return
        key, data = self._comp_data()
        if not key: return
        h = data.get("competitor_handles", [])
        if s[0] >= len(h): return
        x = h.pop(s[0]); data.get("per_competitor", {}).pop(x, None)
        competitor_analyzer.save_competitors(core.BRANDS_DIR, key, data); self._refresh_comp_view()
    def start_comp_refresh(self):
        key, data = self._comp_data()
        if not key: return
        h = data.get("competitor_handles", [])
        if not h: messagebox.showwarning("No competitors", "Add handles first."); return
        s = core.load_settings()
        if not s.get("apify_token"): messagebox.showerror("Need Apify", "Add Apify token in Settings."); return
        if not s.get("gemini_api_key"): messagebox.showerror("Need Gemini", "Add Gemini key in Settings."); return
        if not messagebox.askyesno("Refresh?", f"Refresh {len(h)} competitor(s)? ~3-5 minutes."): return
        self.comp_refresh_btn.config(state=DISABLED); self.comp_progress.start(12)
        self._set_comp_text(""); self._log_comp(f"Refreshing {len(h)} competitor(s)…")
        threading.Thread(target=self._comp_worker, args=(key,), daemon=True).start()
    def _comp_worker(self, key):
        try:
            data = competitor_analyzer.load_competitors(core.BRANDS_DIR, key)
            b = core.load_brand(key); s = core.load_settings()
            competitor_analyzer.refresh_all_competitors(
                brands_dir=core.BRANDS_DIR, brand_key=key,
                brand_name=b.get("name", key), brand_category=b.get("category", ""),
                handles=data.get("competitor_handles", []),
                apify_token=s.get("apify_token", ""),
                gemini_api_key=s.get("gemini_api_key", ""),
                model_name=s.get("model", "gemini-2.5-flash"),
                posts_per_competitor=10, log=self._log_comp)
            self.root.after(0, self._on_comp_done)
        except Exception as e:
            err = traceback.format_exc()
            self.root.after(0, lambda: self._on_comp_error(e, err))
    def _on_comp_done(self):
        self.comp_progress.stop(); self.comp_refresh_btn.config(state=NORMAL)
        self._refresh_comp_view()
        messagebox.showinfo("Done", "Competitor insights refreshed.")
    def _on_comp_error(self, e, tb):
        self.comp_progress.stop(); self.comp_refresh_btn.config(state=NORMAL)
        self._log_comp(f"\n✗ ERROR: {e}")
        messagebox.showerror("Refresh failed", str(e))

    # ─────────────── STRATEGIST ───────────────
    def _build_strategist(self, f):
        f.columnconfigure(0, weight=1)
        section_heading(f, "Strategist · Plan-Aware Calendar",
                          "Reads the active Growth Plan + competitor playbook + trends + "
                          "Analyst report. Outputs 30-day topic calendar."
                          ).pack(anchor="w", fill="x", pady=(0, 18))

        c1 = card(f, padding=(22, 20)); c1.pack(fill="x", pady=(0, 12))
        ic = c1.inner; ic.columnconfigure(1, weight=1)
        ttk.Label(ic, text="MONTH", style="Hint.TLabel"
                  ).grid(row=0, column=0, sticky="w", padx=(0, 12), pady=6)
        now = datetime.now()
        self.strat_month_var = StringVar(value=now.strftime("%B %Y"))
        ttk.Entry(ic, textvariable=self.strat_month_var, width=24
                  ).grid(row=0, column=1, sticky="w", pady=6)
        ttk.Label(ic, text="NUMBER OF POSTS", style="Hint.TLabel"
                  ).grid(row=1, column=0, sticky="w", padx=(0, 12), pady=6)
        self.strat_count_var = IntVar(value=28)
        ttk.Spinbox(ic, from_=8, to=50, textvariable=self.strat_count_var, width=10
                    ).grid(row=1, column=1, sticky="w", pady=6)
        ttk.Label(ic, text="THEME  (optional)", style="Hint.TLabel"
                  ).grid(row=2, column=0, sticky="w", padx=(0, 12), pady=6)
        self.strat_theme_var = StringVar(value="")
        ttk.Entry(ic, textvariable=self.strat_theme_var
                  ).grid(row=2, column=1, sticky="we", pady=6)

        act = ttk.Frame(f, style="Bg.TFrame"); act.pack(fill="x", pady=(0, 8))
        act.columnconfigure(0, weight=1)
        self.strat_status = ttk.Label(act, text="Ready", style="HintBg.TLabel")
        self.strat_status.grid(row=0, column=0, sticky="w")
        ttk.Button(act, text="🧠  Generate Topics", style="Accent.TButton",
                   command=self.start_strategist).grid(row=0, column=1)

        self.strat_progress = ttk.Progressbar(f, mode="indeterminate")
        self.strat_progress.pack(fill="x", pady=(0, 10))

        lc = card(f, padding=(2, 2)); lc.pack(fill="both", expand=True)
        lci = lc.inner; lci.columnconfigure(0, weight=1); lci.rowconfigure(0, weight=1)
        self.strat_log = Text(lci, wrap="word", bg=PALETTE["surface"], fg=PALETTE["txt"],
                                insertbackground=PALETTE["txt"], font=FONTS["mono"],
                                relief="flat", borderwidth=0, padx=12, pady=10)
        self.strat_log.grid(row=0, column=0, sticky="nsew")
        sb = Scrollbar(lci, orient="vertical", command=self.strat_log.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.strat_log.config(yscrollcommand=sb.set, state=DISABLED)
        self._log_strat("Strategist ready. Pick month & count, click Generate.")

    def _log_strat(self, m):
        self.strat_log.config(state=NORMAL); self.strat_log.insert(END, m + "\n")
        self.strat_log.see(END); self.strat_log.config(state=DISABLED)
        self._ui_tick()
    def start_strategist(self):
        key = self._selected_brand_key()
        if not key: messagebox.showerror("Pick brand", "Select a brand first."); return
        month = self.strat_month_var.get().strip()
        count = int(self.strat_count_var.get())
        theme = self.strat_theme_var.get().strip()
        self.strat_progress.start(12); self.strat_status.config(text="Strategist thinking…")
        threading.Thread(target=self._strat_worker,
                          args=(key, month, count, theme), daemon=True).start()
    def _strat_worker(self, key, month, count, theme):
        try:
            brand = core.load_brand(key)
            playbook = competitor_analyzer.get_playbook_text(core.BRANDS_DIR, key)
            trends = trend_scout.get_trend_brief(core.BRANDS_DIR, key)
            client = core.make_llm_client()
            self._log_strat(f"Using LLM: {client.name.upper()} · {client.model_name}")
            if playbook: self._log_strat("✓ Competitor playbook loaded.")
            if trends: self._log_strat("✓ Trend snapshot loaded.")
            sb = growth_planner.get_strategy_brief(core.BRANDS_DIR, key)
            if sb: self._log_strat("✓ Growth Plan loaded.")
            cal = strategist.generate_topic_calendar(
                brand=brand, month=month, post_count=count, theme=theme,
                llm_client=client, competitor_playbook=playbook,
                trends_brief=trends, strategy_brief=sb, log=self._log_strat)
            out_dir = str(DEFAULT_OUTPUT_DIR); os.makedirs(out_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe = "".join(c for c in brand["name"] if c.isalnum() or c in "_-").strip("_")
            out_path = str(Path(out_dir) / f"{safe}_Topics_{ts}.xlsx")
            strategist.write_topic_calendar_xlsx(brand["name"], month, cal, out_path)
            self._log_strat(f"\n✓ Saved: {out_path}")
            self.root.after(0, lambda: self._on_strat_done(out_path))
        except Exception as e:
            err = traceback.format_exc()
            self.root.after(0, lambda: self._on_strat_error(e, err))
    def _on_strat_done(self, p):
        self.strat_progress.stop()
        self.strat_status.config(text="Topics generated ✓")
        if messagebox.askyesno("Done", "Open Excel now?"):
            try: os.startfile(p)
            except Exception: pass
            try: self.input_var.set(p)
            except Exception: pass
    def _on_strat_error(self, e, tb):
        self.strat_progress.stop()
        self.strat_status.config(text="Failed")
        self._log_strat(f"\n✗ ERROR: {e}")
        messagebox.showerror("Strategist failed", str(e))

    # ─────────────── COPY WRITER ───────────────
    def _build_copywriter(self, f):
        f.columnconfigure(0, weight=1)
        section_heading(f, "Copy Writer",
                          "Takes a topic calendar Excel and writes scroll-stopping copy "
                          "per row — informed by plan + competitors + trends + keyword research."
                          ).pack(anchor="w", fill="x", pady=(0, 18))

        c1 = card(f, padding=(22, 20)); c1.pack(fill="x", pady=(0, 12))
        ic = c1.inner; ic.columnconfigure(0, weight=1)
        ttk.Label(ic, text="INPUT CALENDAR (Excel)", style="Hint.TLabel"
                  ).grid(row=0, column=0, columnspan=2, sticky="w")
        self.input_var = StringVar()
        ttk.Entry(ic, textvariable=self.input_var
                  ).grid(row=1, column=0, sticky="we", pady=(4, 4))
        ttk.Button(ic, text="Browse…", style="Ghost.TButton",
                   command=self._browse_input).grid(row=1, column=1, padx=(8, 0))

        ttk.Label(ic, text="OUTPUT FOLDER", style="Hint.TLabel"
                  ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(12, 0))
        self.output_var = StringVar(value=str(DEFAULT_OUTPUT_DIR))
        ttk.Entry(ic, textvariable=self.output_var
                  ).grid(row=3, column=0, sticky="we", pady=(4, 4))
        ttk.Button(ic, text="Browse…", style="Ghost.TButton",
                   command=self._browse_output).grid(row=3, column=1, padx=(8, 0))

        act = ttk.Frame(f, style="Bg.TFrame"); act.pack(fill="x", pady=(8, 8))
        act.columnconfigure(0, weight=1)
        self.resume_btn = ttk.Button(act, text="🔁 Resume", style="Ghost.TButton",
                                        command=self.start_resume)
        self.resume_btn.grid(row=0, column=1, padx=4)
        self.pause_btn = ttk.Button(act, text="⏸ Pause", style="Ghost.TButton",
                                       command=self.toggle_pause, state=DISABLED)
        self.pause_btn.grid(row=0, column=2, padx=4)
        self.stop_btn = ttk.Button(act, text="⏹ Stop", style="Ghost.TButton",
                                      command=self.stop_generation, state=DISABLED)
        self.stop_btn.grid(row=0, column=3, padx=4)
        self.generate_btn = ttk.Button(act, text="✦  Generate Copy",
                                          style="Accent.TButton",
                                          command=self.start_generation)
        self.generate_btn.grid(row=0, column=4, padx=(8, 4))
        ttk.Button(act, text="📁 Folder", style="Ghost.TButton",
                   command=self._open_output_folder).grid(row=0, column=5)

        self.progress = ttk.Progressbar(f, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(0, 4))
        self.progress_label = ttk.Label(f, text="Ready", style="HintBg.TLabel")
        self.progress_label.pack(anchor="w", pady=(0, 10))

        lc = card(f, padding=(2, 2)); lc.pack(fill="both", expand=True)
        lci = lc.inner; lci.columnconfigure(0, weight=1); lci.rowconfigure(0, weight=1)
        self.log_text = Text(lci, wrap="word", bg=PALETTE["surface"], fg=PALETTE["txt"],
                               insertbackground=PALETTE["txt"], font=FONTS["mono"],
                               relief="flat", borderwidth=0, padx=12, pady=10)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        sb = Scrollbar(lci, orient="vertical", command=self.log_text.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=sb.set, state=DISABLED)
        self._log("Welcome. Pick a topics Excel (from Strategist tab) and click Generate.")

    def _browse_input(self):
        p = filedialog.askopenfilename(title="Select Content Calendar",
            filetypes=[("Excel", "*.xlsx *.xlsm"), ("All", "*.*")])
        if p: self.input_var.set(p)
    def _browse_output(self):
        p = filedialog.askdirectory(title="Output folder")
        if p: self.output_var.set(p)
    def _open_output_folder(self):
        p = self.output_var.get().strip() or str(DEFAULT_OUTPUT_DIR)
        os.makedirs(p, exist_ok=True)
        try: os.startfile(p)
        except Exception: webbrowser.open(f"file://{p}")
    def _log(self, m):
        self.log_text.config(state=NORMAL); self.log_text.insert(END, m + "\n")
        self.log_text.see(END); self.log_text.config(state=DISABLED)
        self._ui_tick()
    def _set_progress(self, c, t, lbl):
        pct = 0 if t == 0 else int(c / t * 100)
        self.progress["value"] = pct
        self.progress_label.config(text=f"{c}/{t} · {lbl}")
        self._ui_tick()

    def start_generation(self):
        key = self._selected_brand_key()
        ip = self.input_var.get().strip()
        od = self.output_var.get().strip() or str(DEFAULT_OUTPUT_DIR)
        if not key: messagebox.showerror("Pick brand", "Select a brand."); return
        if not ip or not Path(ip).exists(): messagebox.showerror("Missing", "Pick a valid input Excel."); return
        s = core.load_settings(); prov = s.get("llm_provider", "groq")
        if (prov == "groq" and not s.get("groq_api_key")) or (prov == "gemini" and not s.get("gemini_api_key")):
            messagebox.showerror("Missing API key", "Set API key in Settings."); return
        self.pause_event.clear(); self.stop_event.clear()
        self.generate_btn.config(state=DISABLED); self.resume_btn.config(state=DISABLED)
        self.pause_btn.config(state=NORMAL, text="⏸ Pause")
        self.stop_btn.config(state=NORMAL)
        self.progress["value"] = 0
        self._log("─" * 60); self._log(f"▸ Brand: {key}  ·  Input: {Path(ip).name}")
        threading.Thread(target=self._gen_worker, args=(key, ip, od), daemon=True).start()

    def _gen_worker(self, key, ip, od):
        try:
            out = core.generate_calendar(
                brand_key=key, input_path=ip, output_dir=od,
                progress_callback=self._set_progress, log_callback=self._log,
                pause_event=self.pause_event, stop_event=self.stop_event)
            self.root.after(0, lambda: self._on_gen_done(out))
        except Exception as e:
            err = traceback.format_exc()
            self.root.after(0, lambda: self._on_gen_error(e, err))
    def toggle_pause(self):
        if self.pause_event.is_set():
            self.pause_event.clear(); self.pause_btn.config(text="⏸ Pause")
            self._log("▶ Resume requested.")
        else:
            self.pause_event.set(); self.pause_btn.config(text="▶ Resume")
            self._log("⏸ Pause requested.")
    def stop_generation(self):
        if not messagebox.askyesno("Stop?", "Stop after current post finishes?"): return
        self.stop_event.set(); self.pause_event.clear(); self._log("⏹ Stop requested.")
    def _reset_run_buttons(self):
        self.generate_btn.config(state=NORMAL); self.resume_btn.config(state=NORMAL)
        self.pause_btn.config(state=DISABLED, text="⏸ Pause"); self.stop_btn.config(state=DISABLED)
        self.pause_event.clear(); self.stop_event.clear()
    def _on_gen_done(self, p):
        self._reset_run_buttons(); self.progress["value"] = 100; self.progress_label.config(text="Complete")
        if messagebox.askyesno("Done", f"Saved.\nOpen now?"):
            try: os.startfile(p)
            except Exception: pass
    def _on_gen_error(self, e, tb):
        self._reset_run_buttons(); self.progress_label.config(text="Failed")
        self._log(f"✗ ERROR: {e}"); messagebox.showerror("Generation failed", str(e))
    def start_resume(self):
        p = filedialog.askopenfilename(title="Pick file with failed rows",
            initialdir=str(DEFAULT_OUTPUT_DIR), filetypes=[("Excel", "*.xlsx"), ("All", "*.*")])
        if not p: return
        s = core.load_settings(); prov = s.get("llm_provider", "groq")
        if (prov == "groq" and not s.get("groq_api_key")) or (prov == "gemini" and not s.get("gemini_api_key")):
            messagebox.showerror("Missing API key", "Set key first."); return
        self.pause_event.clear(); self.stop_event.clear()
        self.generate_btn.config(state=DISABLED); self.resume_btn.config(state=DISABLED)
        self.pause_btn.config(state=NORMAL, text="⏸ Pause")
        self.stop_btn.config(state=NORMAL); self.progress["value"] = 0
        self._log("─" * 60); self._log(f"▸ Resuming: {Path(p).name}")
        threading.Thread(target=self._resume_worker, args=(p,), daemon=True).start()
    def _resume_worker(self, p):
        try:
            ok, fail = core.resume_failed_generations(
                output_xlsx_path=p, progress_callback=self._set_progress,
                log_callback=self._log,
                pause_event=self.pause_event, stop_event=self.stop_event)
            self.root.after(0, lambda: self._on_resume_done(p, ok, fail))
        except Exception as e:
            err = traceback.format_exc()
            self.root.after(0, lambda: self._on_gen_error(e, err))
    def _on_resume_done(self, p, ok, fail):
        self._reset_run_buttons(); self.progress_label.config(text=f"Resume · {ok} fixed, {fail} failing")
        if messagebox.askyesno("Done", f"Fixed: {ok}\nStill failing: {fail}\n\nOpen file?"):
            try: os.startfile(p)
            except Exception: pass

    # ─────────────── DESIGNER ───────────────
    def _build_designer(self, f):
        f.columnconfigure(0, weight=1)
        section_heading(f, "Designer",
                          "Premium static + carousel visuals via Freepik. "
                          "Skips Reels / AI Reels / Videos. Composites real logo + product PNGs."
                          ).pack(anchor="w", fill="x", pady=(0, 18))

        c1 = card(f, padding=(22, 20)); c1.pack(fill="x", pady=(0, 12))
        ic = c1.inner; ic.columnconfigure(0, weight=1)
        ttk.Label(ic, text="GENERATED COPY EXCEL", style="Hint.TLabel"
                  ).grid(row=0, column=0, columnspan=2, sticky="w")
        self.des_input_var = StringVar()
        ttk.Entry(ic, textvariable=self.des_input_var
                  ).grid(row=1, column=0, sticky="we", pady=(4, 4))
        ttk.Button(ic, text="Browse…", style="Ghost.TButton",
                   command=self._des_browse).grid(row=1, column=1, padx=(8, 0))

        ttk.Label(ic, text="OUTPUT FOLDER", style="Hint.TLabel"
                  ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(12, 0))
        self.des_output_var = StringVar(value=str(DEFAULT_OUTPUT_DIR))
        ttk.Entry(ic, textvariable=self.des_output_var
                  ).grid(row=3, column=0, sticky="we", pady=(4, 4))
        ttk.Button(ic, text="Browse…", style="Ghost.TButton",
                   command=self._des_browse_out).grid(row=3, column=1, padx=(8, 0))

        act = ttk.Frame(f, style="Bg.TFrame"); act.pack(fill="x", pady=(8, 8))
        act.columnconfigure(0, weight=1)
        ttk.Label(act, text="Engine:", style="HintBg.TLabel"
                  ).grid(row=0, column=0, sticky="w")
        s = core.load_settings()
        self.des_engine_var = StringVar(value=s.get("freepik_engine", "mystic"))
        ttk.Combobox(act, textvariable=self.des_engine_var, state="readonly",
                     values=["mystic", "imagen3"], width=12
                     ).grid(row=0, column=1, padx=(8, 16))
        self.des_pause_btn = ttk.Button(act, text="⏸ Pause", style="Ghost.TButton",
                                          command=self._des_toggle_pause, state=DISABLED)
        self.des_pause_btn.grid(row=0, column=2, padx=2)
        self.des_stop_btn = ttk.Button(act, text="⏹ Stop", style="Ghost.TButton",
                                         command=self._des_stop, state=DISABLED)
        self.des_stop_btn.grid(row=0, column=3, padx=2)
        self.des_generate_btn = ttk.Button(act, text="🎨  Design Visuals",
                                              style="Accent.TButton",
                                              command=self.start_designer)
        self.des_generate_btn.grid(row=0, column=4, padx=(8, 4))
        ttk.Button(act, text="📁 Folder", style="Ghost.TButton",
                   command=self._des_open_folder).grid(row=0, column=5)

        self.des_progress = ttk.Progressbar(f, mode="determinate", maximum=100)
        self.des_progress.pack(fill="x", pady=(0, 4))
        self.des_progress_label = ttk.Label(f, text="Ready", style="HintBg.TLabel")
        self.des_progress_label.pack(anchor="w", pady=(0, 10))

        lc = card(f, padding=(2, 2)); lc.pack(fill="both", expand=True)
        lci = lc.inner; lci.columnconfigure(0, weight=1); lci.rowconfigure(0, weight=1)
        self.des_log = Text(lci, wrap="word", bg=PALETTE["surface"], fg=PALETTE["txt"],
                              insertbackground=PALETTE["txt"], font=FONTS["mono"],
                              relief="flat", borderwidth=0, padx=12, pady=10)
        self.des_log.grid(row=0, column=0, sticky="nsew")
        sb = Scrollbar(lci, orient="vertical", command=self.des_log.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.des_log.config(yscrollcommand=sb.set, state=DISABLED)
        self._log_des("Designer ready. Pick a Copy Writer output Excel.")

    def _log_des(self, m):
        self.des_log.config(state=NORMAL); self.des_log.insert(END, m + "\n")
        self.des_log.see(END); self.des_log.config(state=DISABLED)
        self._ui_tick()
    def _des_progress(self, c, t, lbl):
        pct = 0 if t == 0 else int(c / t * 100); self.des_progress["value"] = pct
        self.des_progress_label.config(text=f"{c}/{t} · {lbl}")
        self._ui_tick()
    def _des_browse(self):
        p = filedialog.askopenfilename(title="Generated copy Excel",
            initialdir=str(DEFAULT_OUTPUT_DIR), filetypes=[("Excel", "*.xlsx"), ("All", "*.*")])
        if p: self.des_input_var.set(p)
    def _des_browse_out(self):
        p = filedialog.askdirectory(title="Output folder")
        if p: self.des_output_var.set(p)
    def _des_open_folder(self):
        p = self.des_output_var.get().strip() or str(DEFAULT_OUTPUT_DIR)
        v = Path(p) / "visuals"; target = str(v) if v.exists() else p
        try: os.startfile(target)
        except Exception: webbrowser.open(f"file://{target}")
    def _des_toggle_pause(self):
        if self.des_pause_event.is_set():
            self.des_pause_event.clear(); self.des_pause_btn.config(text="⏸ Pause")
            self._log_des("▶ Resume.")
        else:
            self.des_pause_event.set(); self.des_pause_btn.config(text="▶ Resume")
            self._log_des("⏸ Pause requested.")
    def _des_stop(self):
        if not messagebox.askyesno("Stop?", "Stop after current image finishes?"): return
        self.des_stop_event.set(); self.des_pause_event.clear(); self._log_des("⏹ Stop requested.")
    def start_designer(self):
        key = self._selected_brand_key()
        ip = self.des_input_var.get().strip()
        od = self.des_output_var.get().strip() or str(DEFAULT_OUTPUT_DIR)
        if not key: messagebox.showerror("Pick brand", "Select a brand."); return
        if not ip or not Path(ip).exists(): messagebox.showerror("Missing", "Pick a generated-copy Excel."); return
        s = core.load_settings()
        if not s.get("freepik_api_key"): messagebox.showerror("Need Freepik", "Add Freepik key in Settings."); return
        if not messagebox.askyesno("Confirm",
                                     "Render images for every static + carousel + story?\n\n"
                                     "Skipped: Reels / AI Reels. Uses Freepik credits."): return
        self.des_pause_event.clear(); self.des_stop_event.clear()
        self.des_generate_btn.config(state=DISABLED)
        self.des_pause_btn.config(state=NORMAL, text="⏸ Pause")
        self.des_stop_btn.config(state=NORMAL); self.des_progress["value"] = 0
        self._log_des("─" * 60); self._log_des(f"▸ Engine: {self.des_engine_var.get()}")
        threading.Thread(target=self._des_worker,
                          args=(key, ip, od, self.des_engine_var.get()), daemon=True).start()
    def _des_worker(self, key, ip, od, engine):
        try:
            v = designer_agent.design_calendar_visuals(
                output_xlsx_path=ip, brand_key=key, output_dir=od,
                settings=core.load_settings(), engine=engine,
                progress_callback=self._des_progress, log_callback=self._log_des,
                pause_event=self.des_pause_event, stop_event=self.des_stop_event)
            self.root.after(0, lambda: self._on_des_done(v))
        except Exception as e:
            err = traceback.format_exc()
            self.root.after(0, lambda: self._on_des_error(e, err))
    def _on_des_done(self, v):
        self.des_generate_btn.config(state=NORMAL)
        self.des_pause_btn.config(state=DISABLED, text="⏸ Pause")
        self.des_stop_btn.config(state=DISABLED)
        self.des_pause_event.clear(); self.des_stop_event.clear()
        self.des_progress["value"] = 100; self.des_progress_label.config(text="Complete")
        if messagebox.askyesno("Done", f"Visuals saved.\nOpen folder?"):
            try: os.startfile(v)
            except Exception: pass
    def _on_des_error(self, e, tb):
        self.des_generate_btn.config(state=NORMAL)
        self.des_pause_btn.config(state=DISABLED, text="⏸ Pause")
        self.des_stop_btn.config(state=DISABLED)
        self.des_pause_event.clear(); self.des_stop_event.clear()
        self.des_progress_label.config(text="Failed")
        self._log_des(f"✗ ERROR: {e}"); messagebox.showerror("Designer failed", str(e))

    # ─────────────── Helpers ───────────────
    def _brand_options(self):
        opts = []
        for k in core.list_brands():
            try:
                b = core.load_brand(k); opts.append(f"{b['name']}  ({k})")
            except Exception:
                opts.append(k)
        return opts
    def _selected_brand_key(self):
        sel = self.brand_var.get()
        if "(" in sel and sel.endswith(")"):
            return sel.split("(")[-1].rstrip(")").strip()
        return sel
    def refresh_brands(self, new_brand_key=None):
        self.brand_combo["values"] = self._brand_options()
        if new_brand_key:
            for i, o in enumerate(self.brand_combo["values"]):
                if o.endswith(f"({new_brand_key})"):
                    self.brand_combo.current(i); break
        self._on_brand_changed()
    def _on_brand_changed(self):
        # Rebuild views that depend on selected brand
        for nav_id in ("home", "analyst", "competitors", "grook"):
            if nav_id in self._views:
                self._views[nav_id].destroy(); self._views.pop(nav_id)
        if self._current_nav in ("home", "analyst", "competitors", "grook"):
            self._views[self._current_nav] = self._build_view(self._current_nav)
            self._views[self._current_nav].grid(row=0, column=0, sticky="nsew")
        # Update planner handles if currently on grook
        if self._current_nav == "grook":
            self._planner_load_handles()
        self._refresh_statusbar()
    def open_settings(self): SettingsDialog(self.root)
    def open_new_brand(self):
        s = core.load_settings()
        if not s.get("gemini_api_key"):
            messagebox.showerror("Need Gemini key",
                                  "Brand extraction needs Gemini API. Add it in Settings."); return
        NewBrandDialog(self.root, on_saved=self.refresh_brands)
    def open_brand_assets(self):
        k = self._selected_brand_key()
        if not k: messagebox.showerror("Pick brand", "Select a brand."); return
        BrandAssetsDialog(self.root, k)
    def open_connect_instagram(self):
        k = self._selected_brand_key()
        if not k: messagebox.showerror("Pick brand", "Select a brand."); return
        ConnectInstagramDialog(self.root, k)


def main():
    root = Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()