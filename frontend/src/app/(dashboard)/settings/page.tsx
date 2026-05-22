"use client";
import { useState } from "react";
// Auth bypass — useSession replaced with mock
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import {
  Settings, Key, Bell, Shield, Database,
  User, Mail, Lock, CheckCircle2, Loader2,
  Zap, Globe, Brain, Image as ImageIcon,
  AlertTriangle, RefreshCw, ExternalLink, Copy,
  ChevronDown, ChevronUp, Server, Info,
  LogOut, Trash2, ToggleLeft, ToggleRight,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────
type NotifPrefs = {
  runComplete: boolean;
  runFailed:   boolean;
  relearn:     boolean;
  published:   boolean;
};

export default function SettingsPage() {
  // Auth bypass — mock user
  const user = { name: "Dev User", email: "dev@socialos.local" };

  // ── Password change ────────────────────────────────────────────────────────
  const [pwForm, setPwForm] = useState({ current: "", newPw: "", confirm: "" });
  const [pwError, setPwError]     = useState("");
  const [pwSuccess, setPwSuccess] = useState(false);

  const changePwMutation = useMutation({
    mutationFn: (data: { currentPassword: string; newPassword: string }) =>
      api.post("/api/auth/change-password", data),
    onSuccess: () => {
      setPwSuccess(true);
      setPwForm({ current: "", newPw: "", confirm: "" });
      setTimeout(() => setPwSuccess(false), 4000);
    },
    onError: (e: { response?: { data?: { message?: string } } }) =>
      setPwError(e.response?.data?.message ?? "Failed to change password"),
  });

  function handleChangePw() {
    setPwError(""); setPwSuccess(false);
    if (!pwForm.current || !pwForm.newPw) { setPwError("All fields required"); return; }
    if (pwForm.newPw !== pwForm.confirm)   { setPwError("Passwords don't match"); return; }
    if (pwForm.newPw.length < 8)           { setPwError("Minimum 8 characters"); return; }
    changePwMutation.mutate({ currentPassword: pwForm.current, newPassword: pwForm.newPw });
  }

  // ── Backend health / API key status ───────────────────────────────────────
  const { data: healthData, isLoading: healthLoading, refetch: refetchHealth } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.get("/health").then((r) => r.data),
    staleTime: 30_000,
  });

  // ── Notification preferences (localStorage) ───────────────────────────────
  const [notifPrefs, setNotifPrefs] = useState<NotifPrefs>(() => {
    if (typeof window === "undefined") return { runComplete: true, runFailed: true, relearn: false, published: true };
    try { return JSON.parse(localStorage.getItem("notif_prefs") ?? "{}") as NotifPrefs; }
    catch { return { runComplete: true, runFailed: true, relearn: false, published: true }; }
  });

  function toggleNotif(key: keyof NotifPrefs) {
    const updated = { ...notifPrefs, [key]: !notifPrefs[key] };
    setNotifPrefs(updated);
    localStorage.setItem("notif_prefs", JSON.stringify(updated));
  }

  // ── Danger zone ────────────────────────────────────────────────────────────
  const [dangerOpen, setDangerOpen] = useState(false);

  // ── Integration status list ────────────────────────────────────────────────
  const INTEGRATIONS = [
    { icon: Zap,       name: "OpenAI GPT-4o",     env: "OPENAI_API_KEY",           desc: "Strategist · Copywriter · Analyst",  docsUrl: "https://platform.openai.com/api-keys" },
    { icon: Globe,     name: "Tavily Search",      env: "TAVILY_API_KEY",           desc: "Research Agent trend discovery",     docsUrl: "https://tavily.com" },
    { icon: Globe,     name: "NewsAPI",             env: "NEWS_API_KEY",             desc: "Industry news for research agent",   docsUrl: "https://newsapi.org/account" },
    { icon: ImageIcon, name: "Freepik Mystic",      env: "FREEPIK_API_KEY",          desc: "AI image generation for designs",    docsUrl: "https://www.freepik.com/api" },
    { icon: Database,  name: "Supabase Storage",    env: "SUPABASE_SERVICE_ROLE_KEY",desc: "File uploads, logos, guidelines",    docsUrl: "https://supabase.com/dashboard/project/_/settings/api" },
    { icon: Zap,       name: "Upstash Redis",       env: "REDIS_URL",               desc: "BullMQ job queue & scheduling",      docsUrl: "https://console.upstash.com" },
    { icon: Shield,    name: "Meta / Facebook App", env: "META_APP_ID",             desc: "Instagram OAuth & publishing",       docsUrl: "https://developers.facebook.com/apps" },
    { icon: Server,    name: "Neon PostgreSQL",     env: "DATABASE_URL",            desc: "Primary database (Prisma ORM)",      docsUrl: "https://console.neon.tech" },
  ];

  const [copied, setCopied] = useState<string | null>(null);
  function copyEnvKey(key: string) {
    navigator.clipboard.writeText(key);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-sm text-white/40 mt-0.5">Account, integrations & platform configuration</p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* ── Left column ───────────────────────────────────────────────── */}
        <div className="col-span-2 space-y-5">

          {/* Profile card */}
          <GlassCard className="p-5">
            <div className="flex items-center gap-2 mb-5">
              <User className="w-4 h-4 text-brand-light" />
              <h2 className="font-semibold text-white text-sm">Profile</h2>
            </div>
            <div className="flex items-center gap-4 mb-4">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-brand to-indigo-600 flex items-center justify-center text-white font-bold text-xl shadow-brand">
                {user?.name?.[0]?.toUpperCase() ?? user?.email?.[0]?.toUpperCase() ?? "U"}
              </div>
              <div>
                <p className="font-semibold text-white">{user?.name ?? "Admin"}</p>
                <p className="text-sm text-white/40">{user?.email}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] bg-brand/20 text-brand-light border border-brand/30 rounded-full px-2 py-0.5 font-medium">
                    Admin
                  </span>
                  <span className="text-[10px] bg-green-500/10 text-green-400 border border-green-500/20 rounded-full px-2 py-0.5 font-medium flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                    Active
                  </span>
                </div>
              </div>
            </div>
            <div className="p-3 rounded-xl bg-dark-base/40 border border-white/[0.06] flex items-center gap-3">
              <Mail className="w-4 h-4 text-white/30 flex-shrink-0" />
              <span className="text-sm text-white/60">{user?.email}</span>
            </div>
          </GlassCard>

          {/* Change password */}
          <GlassCard className="p-5">
            <div className="flex items-center gap-2 mb-5">
              <Lock className="w-4 h-4 text-brand-light" />
              <h2 className="font-semibold text-white text-sm">Change Password</h2>
            </div>
            <div className="space-y-3">
              <input
                type="password"
                className="input-glass w-full"
                placeholder="Current password"
                value={pwForm.current}
                onChange={e => setPwForm(f => ({ ...f, current: e.target.value }))}
              />
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="password"
                  className="input-glass w-full"
                  placeholder="New password (min 8 chars)"
                  value={pwForm.newPw}
                  onChange={e => setPwForm(f => ({ ...f, newPw: e.target.value }))}
                />
                <input
                  type="password"
                  className="input-glass w-full"
                  placeholder="Confirm new password"
                  value={pwForm.confirm}
                  onChange={e => setPwForm(f => ({ ...f, confirm: e.target.value }))}
                />
              </div>
              {pwError && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-400">
                  {pwError}
                </div>
              )}
              {pwSuccess && (
                <div className="p-3 rounded-xl bg-green-500/10 border border-green-500/20 flex items-center gap-2 text-green-400 text-sm">
                  <CheckCircle2 className="w-4 h-4" /> Password changed successfully
                </div>
              )}
              <button
                onClick={handleChangePw}
                disabled={changePwMutation.isPending || !pwForm.current || !pwForm.newPw}
                className="btn-primary flex items-center gap-2 disabled:opacity-40"
              >
                {changePwMutation.isPending
                  ? <><Loader2 className="w-4 h-4 animate-spin" /> Updating…</>
                  : <><Lock className="w-4 h-4" /> Update Password</>}
              </button>
            </div>
          </GlassCard>

          {/* API Integrations */}
          <GlassCard className="p-5">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Key className="w-4 h-4 text-brand-light" />
                <h2 className="font-semibold text-white text-sm">API Integrations</h2>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-white/30">Keys set in .env files</span>
                <button
                  onClick={() => refetchHealth()}
                  className="p-1.5 rounded-lg hover:bg-white/[0.06] text-white/30 hover:text-white/70 transition-colors"
                  title="Refresh status"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${healthLoading ? "animate-spin" : ""}`} />
                </button>
              </div>
            </div>

            {/* Backend health banner */}
            <div className={`flex items-center gap-3 p-3 rounded-xl border mb-4 text-xs font-medium
              ${healthData
                ? "bg-green-500/10 border-green-500/20 text-green-300"
                : "bg-red-500/10 border-red-500/20 text-red-300"}`}>
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${healthData ? "bg-green-400 animate-pulse" : "bg-red-400"}`} />
              {healthData
                ? `Backend online · ${healthData.service ?? "socialos-backend"} · ${healthData.version ?? "1.0.0"}`
                : "Backend offline — start with: npm run dev (backend)"}
            </div>

            <div className="space-y-2">
              {INTEGRATIONS.map(({ icon: Icon, name, env, desc, docsUrl }) => (
                <div key={name} className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-dark-base/40 border border-white/[0.06] group hover:border-white/[0.10] transition-colors">
                  <div className="w-8 h-8 rounded-lg bg-brand/10 flex items-center justify-center flex-shrink-0">
                    <Icon className="w-4 h-4 text-brand-light" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white/80 font-medium">{name}</p>
                    <p className="text-xs text-white/30">{desc}</p>
                  </div>
                  {/* Copy env key name */}
                  <button
                    onClick={() => copyEnvKey(env)}
                    className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-white/[0.06] text-white/30 hover:text-white/70 transition-all"
                    title={`Copy ${env}`}
                  >
                    {copied === env ? <CheckCircle2 className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                  <a href={docsUrl} target="_blank" rel="noopener noreferrer"
                    className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-white/[0.06] text-white/30 hover:text-white/70 transition-all"
                    title="Get API key"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                  <div className="flex items-center gap-1.5 text-xs font-medium text-green-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                    Configured
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 p-3 rounded-xl bg-brand/5 border border-brand/10 flex items-start gap-2">
              <Info className="w-3.5 h-3.5 text-brand-light flex-shrink-0 mt-0.5" />
              <p className="text-xs text-white/30 leading-relaxed">
                API keys are configured in <code className="text-brand-light font-mono">.env</code> (backend) and
                <code className="text-brand-light font-mono"> .env.local</code> (frontend). Never commit these files. Hover a row to copy the env variable name or open the provider dashboard.
              </p>
            </div>
          </GlassCard>

          {/* Danger Zone */}
          <GlassCard className="p-5 border border-red-500/10">
            <button
              className="flex items-center justify-between w-full"
              onClick={() => setDangerOpen(o => !o)}
            >
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-400" />
                <h2 className="font-semibold text-red-400 text-sm">Danger Zone</h2>
              </div>
              {dangerOpen ? <ChevronUp className="w-4 h-4 text-white/30" /> : <ChevronDown className="w-4 h-4 text-white/30" />}
            </button>

            {dangerOpen && (
              <div className="mt-5 space-y-3">
                <div className="p-4 rounded-xl border border-red-500/20 bg-red-500/5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium text-white">Sign Out</p>
                      <p className="text-xs text-white/40 mt-0.5">Sign out of all sessions on this device</p>
                    </div>
                    <button
                      onClick={() => { window.location.href = "/auth/login"; }}
                      className="flex items-center gap-2 px-3 py-2 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 text-xs font-medium transition-colors flex-shrink-0"
                    >
                      <LogOut className="w-3.5 h-3.5" /> Sign Out
                    </button>
                  </div>
                </div>

                <div className="p-4 rounded-xl border border-red-500/20 bg-red-500/5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium text-white">Clear All Agent Runs</p>
                      <p className="text-xs text-white/40 mt-0.5">Delete all generated content, posts, and design assets. This cannot be undone.</p>
                    </div>
                    <button
                      onClick={() => alert("Contact support to clear all data.")}
                      className="flex items-center gap-2 px-3 py-2 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 text-xs font-medium transition-colors flex-shrink-0"
                    >
                      <Trash2 className="w-3.5 h-3.5" /> Clear Data
                    </button>
                  </div>
                </div>
              </div>
            )}
          </GlassCard>
        </div>

        {/* ── Right column ─────────────────────────────────────────────── */}
        <div className="space-y-5">

          {/* Notifications */}
          <GlassCard className="p-5">
            <div className="flex items-center gap-2 mb-4">
              <Bell className="w-4 h-4 text-brand-light" />
              <h2 className="font-semibold text-white text-sm">Notifications</h2>
            </div>
            <div className="space-y-3">
              {(
                [
                  { key: "runComplete" as const, label: "Agent run complete",   desc: "When a pipeline finishes" },
                  { key: "runFailed"   as const, label: "Agent run failed",     desc: "On pipeline errors" },
                  { key: "published"   as const, label: "Post published",       desc: "On Instagram publish success" },
                  { key: "relearn"     as const, label: "Brand re-learned",     desc: "After AI self-learning runs" },
                ]
              ).map(({ key, label, desc }) => (
                <div key={key} className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-white/70">{label}</p>
                    <p className="text-[10px] text-white/30">{desc}</p>
                  </div>
                  <button onClick={() => toggleNotif(key)} className="flex-shrink-0">
                    {notifPrefs[key]
                      ? <ToggleRight className="w-8 h-8 text-brand-light" />
                      : <ToggleLeft  className="w-8 h-8 text-white/20" />}
                  </button>
                </div>
              ))}
            </div>
            <p className="text-[10px] text-white/20 mt-3">In-app toasts only · Email alerts coming soon</p>
          </GlassCard>

          {/* Meta App Setup Guide */}
          <GlassCard className="p-5">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-4 h-4 text-brand-light" />
              <h2 className="font-semibold text-white text-sm">Meta App Setup</h2>
            </div>
            <div className="space-y-2.5 text-xs">
              {[
                { step: "1", text: "Go to Meta for Developers" },
                { step: "2", text: "Create or open your App" },
                { step: "3", text: "Add Instagram Graph API product" },
                { step: "4", text: "Add OAuth redirect URI in App Dashboard" },
                { step: "5", text: "Add test users under Roles" },
                { step: "6", text: "Set META_APP_ID & META_APP_SECRET in .env" },
              ].map(({ step, text }) => (
                <div key={step} className="flex items-start gap-2">
                  <span className="w-4 h-4 rounded-full bg-brand/20 text-brand-light flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5">
                    {step}
                  </span>
                  <span className="text-white/40">{text}</span>
                </div>
              ))}
            </div>
            <a
              href="https://developers.facebook.com/apps"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 mt-4 text-xs text-brand-light hover:text-white transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Open Meta for Developers →
            </a>
          </GlassCard>

          {/* System Info */}
          <GlassCard variant="dark" className="p-5">
            <div className="flex items-center gap-2 mb-4">
              <Settings className="w-4 h-4 text-brand-light" />
              <h2 className="font-semibold text-white text-sm">System Info</h2>
            </div>
            <div className="space-y-2 text-xs">
              {[
                ["Agency",    "PerformEdge"],
                ["Platform",  "SocialOS v1.0"],
                ["Frontend",  "Next.js 15 + React 18"],
                ["Backend",   "Fastify 5 + BullMQ"],
                ["Agents",    "LangGraph + GPT-4o"],
                ["Database",  "Neon PostgreSQL"],
                ["Queue",     "BullMQ + Upstash Redis"],
                ["Storage",   "Supabase Storage"],
                ["Images",    "Freepik Mystic AI"],
                ["Instagram", "Meta Graph API v21"],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between items-center">
                  <span className="text-white/30">{k}</span>
                  <span className="text-white/60 font-medium">{v}</span>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
