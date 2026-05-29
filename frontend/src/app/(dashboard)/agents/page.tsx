"use client";
import { useState, useEffect, useRef } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { agentAPI, createSSEConnection } from "@/lib/api";
import { useAppStore, useActiveBrand } from "@/store/useAppStore";
import { GlassCard } from "@/components/ui/GlassCard";
import { AgentNode } from "@/components/ui/AgentNode";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { AGENT_LABELS, AGENT_ICONS, AGENT_DESCRIPTIONS, AGENT_PRODUCES, AGENT_METADATA } from "@/lib/utils";
import {
  Play, StopCircle, Download, ChevronDown, ChevronUp, Terminal,
  Clock, CheckCircle2, Layers, FileText, Presentation,
  Calendar, Paintbrush, RefreshCw, Target, TrendingUp,
  Search, Link2, Globe, Users, ListChecks, FileSearch,
} from "lucide-react";
import Link from "next/link";
import type { SSEEvent, AgentRun, AgentExecution } from "@/types";

const AGENT_ORDER = [
  "brandManager",
  "analyst",
  "researchAgent",
  "competitorTracker",
  "growthPlanner",
  "strategist",
  "copywriter",
  "designer",
];

// Estimated time per agent in seconds
const AGENT_TIMES: Record<string, number> = {
  brandManager:      5,
  analyst:          20,
  researchAgent:    15,
  competitorTracker: 10,
  growthPlanner:    20,
  strategist:       25,
  copywriter:       40,
  designer:         60,
};
const TOTAL_EST = Object.values(AGENT_TIMES).reduce((a, b) => a + b, 0);

type AgentStatuses = Record<string, AgentExecution>;

export default function AgentsPage() {
  const activeBrand = useActiveBrand();
  const { addSSEEvent, clearSSEEvents, sseEvents, setActiveRun, activeRun } = useAppStore();
  const [agentStatuses, setAgentStatuses] = useState<AgentStatuses>({});
  const [selectedAgentKey, setSelectedAgentKey] = useState<string | null>(null);
  const [showLogs, setShowLogs]           = useState(false);
  const [pipelineDone, setPipelineDone]   = useState(false);
  const [isPipelineActive, setIsPipelineActive] = useState(false); // true while pipeline running
  const [elapsedSec, setElapsedSec]       = useState(0);
  const [runOptions, setRunOptions]       = useState<{
    mode: string;
    daysAhead: number;
    followerGoal: string;
    currentFollowers: string;
  }>({ mode: "full", daysAhead: 15, followerGoal: "", currentFollowers: "" });
  const sseRef        = useRef<EventSource | null>(null);
  const logsEndRef    = useRef<HTMLDivElement>(null);
  const timerRef      = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef  = useRef<number | null>(null);
  // Keep a ref to activeRun so SSE callback always sees the latest value
  const activeRunRef  = useRef<AgentRun | null>(activeRun);
  useEffect(() => { activeRunRef.current = activeRun; }, [activeRun]);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [sseEvents]);

  // Cleanup
  useEffect(() => () => {
    sseRef.current?.close();
    if (timerRef.current) clearInterval(timerRef.current);
  }, []);

  // Pre-fill current followers from brand's live IG follower count
  useEffect(() => {
    if (activeBrand?.igFollowers && !runOptions.currentFollowers) {
      setRunOptions(o => ({ ...o, currentFollowers: String(activeBrand.igFollowers) }));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeBrand?.igFollowers]);

  // Polling fallback: when pipeline is active but SSE might have failed,
  // poll run status every 5 seconds to detect completion
  useEffect(() => {
    if (!isPipelineActive || pipelineDone || !activeRun) return;
    const poll = setInterval(async () => {
      try {
        const res = await agentAPI.status(activeRun.id);
        const run = res.data.run as AgentRun;
        if (run.status === "completed" || run.status === "failed" || run.status === "stopped") {
          setIsPipelineActive(false);
          setPipelineDone(true);
          if (run.status === "completed") {
            const pollPptUrl = run.pptUrl ?? activeRunRef.current?.pptUrl;
            setActiveRun({
              ...activeRunRef.current!,
              pptUrl:         pollPptUrl,
              excelUrl:       run.excelUrl ?? activeRunRef.current?.excelUrl,
              postsGenerated: run.postsGenerated ?? activeRunRef.current?.postsGenerated ?? 0,
            });
            // Auto-download PPT if found via polling
            if (pollPptUrl && !activeRunRef.current?.pptUrl) {
              try {
                const a = document.createElement("a");
                a.href = pollPptUrl; a.target = "_blank"; a.rel = "noopener noreferrer";
                document.body.appendChild(a); a.click(); document.body.removeChild(a);
              } catch {}
            }
          }
          if (timerRef.current) clearInterval(timerRef.current);
          refetchRuns();
        }
        // Update agent statuses from DB if we have them. Deep-merge per agent
        // so DB-side execution traces (steps/sources/files) survive even when
        // a live status object exists in `prev`.
        if (run.agentStatuses && Object.keys(run.agentStatuses).length > 0) {
          const dbStatuses = run.agentStatuses as AgentStatuses;
          setAgentStatuses(prev => {
            const merged: AgentStatuses = { ...prev };
            for (const [k, v] of Object.entries(dbStatuses)) {
              merged[k] = { ...(prev[k] ?? {}), ...v };
            }
            return merged;
          });
        }
      } catch {
        // ignore poll errors
      }
    }, 5000);
    return () => clearInterval(poll);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPipelineActive, pipelineDone, activeRun?.id]);

  // Run history
  const { data: runsData, refetch: refetchRuns } = useQuery({
    queryKey: ["runs", activeBrand?.id],
    queryFn: () => agentAPI.listRuns(activeBrand!.id).then((r) => r.data),
    enabled: !!activeBrand,
    staleTime: 30_000,
  });
  const pastRuns: AgentRun[] = (runsData?.runs ?? []).slice(0, 5);

  const startMutation = useMutation({
    mutationFn: () => {
      const goalNum    = parseInt(runOptions.followerGoal, 10);
      const currentNum = parseInt(runOptions.currentFollowers, 10);
      return agentAPI.run(activeBrand!.id, {
        mode:      runOptions.mode,
        daysAhead: runOptions.daysAhead,
        ...(goalNum    > 0  ? { followerGoal:    goalNum    } : {}),
        ...(currentNum >= 0 && runOptions.currentFollowers !== "" ? { currentFollowers: currentNum } : {}),
      });
    },
    onSuccess: (res) => {
      const run = res.data.run;
      setActiveRun(run);
      clearSSEEvents();
      setAgentStatuses({});
      setPipelineDone(false);
      setIsPipelineActive(true); // pipeline is now running
      setElapsedSec(0);

      // Start elapsed timer
      startTimeRef.current = Date.now();
      timerRef.current = setInterval(() => {
        setElapsedSec(Math.floor((Date.now() - startTimeRef.current!) / 1000));
      }, 1000);

      // Open SSE
      sseRef.current?.close();
      sseRef.current = createSSEConnection(
        run.id,
        (event: unknown) => {
          const e = event as SSEEvent;
          addSSEEvent(e);

          if (e.type === "agent_started" || e.type === "agent_progress") {
            setAgentStatuses((prev) => ({
              ...prev,
              [e.agentKey!]: { status: "running", message: e.message },
            }));
          } else if (e.type === "agent_completed") {
            setAgentStatuses((prev) => ({
              ...prev,
              [e.agentKey!]: { status: "completed", message: e.message },
            }));
          } else if (e.type === "agent_failed") {
            setAgentStatuses((prev) => ({
              ...prev,
              [e.agentKey!]: { status: "failed", message: e.message },
            }));
          } else if (e.type === "pipeline_complete") {
            // Merge the full execution traces (timing, steps, sources, files)
            // that the agents service aggregated into agentStatuses.
            const finalStatuses = e.data?.agentStatuses as AgentStatuses | undefined;
            if (finalStatuses && Object.keys(finalStatuses).length > 0) {
              setAgentStatuses((prev) => {
                const merged: AgentStatuses = { ...prev };
                for (const [k, v] of Object.entries(finalStatuses)) {
                  merged[k] = { ...(prev[k] ?? {}), ...v };
                }
                return merged;
              });
            }
            // Update activeRun with final outputs (use ref to avoid stale closure)
            const current = activeRunRef.current;
            const finalPptUrl   = (e.data?.pptUrl as string | undefined)    ?? current?.pptUrl;
            const finalExcelUrl = (e.data?.excelUrl as string | undefined)  ?? current?.excelUrl;
            if (e.data && current) {
              setActiveRun({
                ...current,
                pptUrl: finalPptUrl,
                excelUrl: finalExcelUrl,
                postsGenerated: (e.data?.postsGenerated as number | undefined) ?? current.postsGenerated,
              });
            }
            // Auto-download PPT when it's generated (browser will download .pptx automatically)
            if (finalPptUrl) {
              try {
                const a = document.createElement("a");
                a.href   = finalPptUrl;
                a.target = "_blank";
                a.rel    = "noopener noreferrer";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
              } catch {}
            }
            sseRef.current?.close();
            setPipelineDone(true);
            setIsPipelineActive(false);
            if (timerRef.current) clearInterval(timerRef.current);
            refetchRuns();
          } else if (e.type === "pipeline_failed") {
            sseRef.current?.close();
            setPipelineDone(true);
            setIsPipelineActive(false);
            if (timerRef.current) clearInterval(timerRef.current);
            refetchRuns();
          }
        },
        () => console.error("SSE connection error")
      );
    },
  });

  const stopMutation = useMutation({
    mutationFn: () => agentAPI.stopRun(activeRun!.id),
    onSuccess: () => {
      sseRef.current?.close();
      setActiveRun(null);
      setIsPipelineActive(false);
      setPipelineDone(false);
      if (timerRef.current) clearInterval(timerRef.current);
      refetchRuns();
    },
  });

  const completedCount = Object.values(agentStatuses).filter(s => s.status === "completed").length;
  const progressPct    = (completedCount / AGENT_ORDER.length) * 100;

  // Estimate remaining
  const completedAgents = AGENT_ORDER.filter(k => agentStatuses[k]?.status === "completed");
  const estimatedDone   = completedAgents.reduce((acc, k) => acc + (AGENT_TIMES[k] ?? 10), 0);
  const estRemainingSec = Math.max(0, TOTAL_EST - estimatedDone - elapsedSec);

  // isRunning is true from the moment pipeline starts until pipeline_complete/failed fires
  // (using isPipelineActive state, not startMutation.isPending which goes false immediately after 202)
  const isRunning = isPipelineActive;

  const pipelineStatus = (() => {
    if (isRunning) return "running";
    const statuses = Object.values(agentStatuses).map(s => s.status);
    if (pipelineDone && statuses.some(s => s === "failed") && !statuses.some(s => s === "completed")) return "failed";
    if (pipelineDone && completedCount > 0) return "completed";
    if (pipelineDone) return "completed";
    return "idle";
  })();

  // Format seconds to mm:ss
  function fmtTime(s: number) {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, "0")}`;
  }

  if (!activeBrand) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Agent Pipeline</h1>
          <p className="text-sm text-white/40 mt-0.5">Run AI agents to generate content calendar, designs & strategy</p>
        </div>
        <GlassCard className="p-20 flex flex-col items-center text-center">
          <div className="w-16 h-16 rounded-2xl bg-brand/10 flex items-center justify-center mb-4">
            <Play className="w-7 h-7 text-brand-light" />
          </div>
          <h2 className="text-lg font-semibold text-white mb-2">No brand selected</h2>
          <p className="text-sm text-white/40 max-w-xs mb-5">
            Select a brand from the sidebar to start running AI agents
          </p>
          <Link href="/brands" className="btn-primary text-sm">Go to Brand Hub</Link>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Agent Pipeline</h1>
          <p className="text-sm text-white/40 mt-0.5">
            {activeBrand.name} · AI-powered content generation
          </p>
        </div>
        <StatusBadge status={pipelineStatus as "idle" | "running" | "completed" | "failed" | "pending"} />
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* ── Config Panel ── */}
        <div className="col-span-1 space-y-4">
          <GlassCard className="p-5">
            <h2 className="font-semibold text-white text-sm mb-4">Run Configuration</h2>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-white/40 mb-1.5 block">Run Mode</label>
                <select
                  className="input-glass w-full"
                  value={runOptions.mode}
                  onChange={e => setRunOptions(o => ({ ...o, mode: e.target.value }))}
                  disabled={isRunning}
                >
                  <option value="full">Full Pipeline (all agents)</option>
                  <option value="growth_planner_only">Growth Planner (IG Audit + PPT)</option>
                  <option value="analyst_only">Analyst Only</option>
                  <option value="strategy_only">Strategy + Copy</option>
                  <option value="design_only">Design Only</option>
                </select>
                {runOptions.mode === "growth_planner_only" && (
                  <div className="mt-2 p-3 rounded-xl bg-purple-500/10 border border-purple-500/20">
                    <p className="text-[11px] text-purple-300 font-medium mb-1">Growth Planner Mode</p>
                    <p className="text-[10px] text-white/40 leading-relaxed">
                      Full Instagram audit — analyses every post, identifies what&apos;s working vs not working, builds content pillars, sets follower growth goals, and generates a comprehensive PPT report.
                    </p>
                  </div>
                )}
              </div>

              <div>
                <label className="text-xs text-white/40 mb-1.5 block">Days Ahead</label>
                <div className="flex items-center gap-2">
                  <input
                    type="range" min={7} max={30} step={1}
                    value={runOptions.daysAhead}
                    onChange={e => setRunOptions(o => ({ ...o, daysAhead: +e.target.value }))}
                    disabled={isRunning}
                    className="flex-1 accent-brand"
                  />
                  <span className="text-sm font-bold text-brand-light w-8 text-right">{runOptions.daysAhead}</span>
                </div>
                <p className="text-[10px] text-white/25 mt-1">Generates {runOptions.daysAhead} days of content</p>
              </div>
            </div>

            <div className="mt-5 space-y-2">
              {!isRunning ? (
                <button
                  onClick={() => startMutation.mutate()}
                  disabled={startMutation.isPending}
                  className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {startMutation.isPending
                    ? <><RefreshCw className="w-4 h-4 animate-spin" /> Starting…</>
                    : <><Play className="w-4 h-4" /> Start Pipeline</>}
                </button>
              ) : (
                <button
                  onClick={() => stopMutation.mutate()}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-red-500/15 hover:bg-red-500/25 border border-red-500/25 text-red-400 text-sm font-medium transition-all"
                >
                  <StopCircle className="w-4 h-4" /> Stop Pipeline
                </button>
              )}
            </div>

            {startMutation.isError && (
              <p className="text-xs text-red-400 mt-2">
                {(startMutation.error as { response?: { data?: { message?: string } } })
                  .response?.data?.message ?? "Failed to start run"}
              </p>
            )}

            {/* Timer */}
            {isRunning && (
              <div className="mt-4 pt-4 border-t border-white/[0.06]">
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="text-white/40 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5" /> Elapsed
                  </span>
                  <span className="text-white/60 font-mono">{fmtTime(elapsedSec)}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-white/40">Est. remaining</span>
                  <span className="text-brand-light font-mono">~{fmtTime(estRemainingSec)}</span>
                </div>
              </div>
            )}

            {/* Downloads after completion */}
            {pipelineDone && activeRun && (
              <div className="mt-4 pt-4 border-t border-white/[0.06]">
                <p className="text-xs text-white/40 mb-2.5 font-medium">Generated Outputs</p>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5 text-white/60">
                      <Calendar className="w-3.5 h-3.5 text-brand-light" />
                      Posts generated
                    </div>
                    <span className="font-bold text-brand-light">{activeRun.postsGenerated}</span>
                  </div>
                  {activeRun.pptUrl && (
                    <a href={activeRun.pptUrl} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-2 text-xs text-orange-400 hover:text-orange-300 transition-colors">
                      <Presentation className="w-3.5 h-3.5" />
                      {runOptions.mode === "growth_planner_only" ? "Growth Planner PPT (.pptx)" : "Strategy Deck (.pptx)"}
                    </a>
                  )}
                  {activeRun.excelUrl && (
                    <a href={activeRun.excelUrl} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-2 text-xs text-green-400 hover:text-green-300 transition-colors">
                      <FileText className="w-3.5 h-3.5" /> Content Calendar (.xlsx)
                    </a>
                  )}
                  <div className="flex gap-2 mt-2">
                    <Link href="/calendar" className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-brand/10 hover:bg-brand/20 border border-brand/20 text-brand-light text-xs font-medium transition-colors">
                      <Calendar className="w-3.5 h-3.5" /> Calendar
                    </Link>
                    <Link href="/designer" className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.08] border border-white/[0.08] text-white/60 text-xs font-medium transition-colors">
                      <Paintbrush className="w-3.5 h-3.5" /> Designs
                    </Link>
                  </div>
                </div>
              </div>
            )}
          </GlassCard>

          {/* ── Follower Growth Goal ── */}
          <GlassCard className="p-5">
            <div className="flex items-center gap-2 mb-4">
              <Target className="w-4 h-4 text-purple-400" />
              <h2 className="font-semibold text-white text-sm">Follower Growth Goal</h2>
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 ml-auto">Optional</span>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-white/40 mb-1.5 block">Current Followers</label>
                <input
                  type="number"
                  min={0}
                  placeholder="e.g. 12000"
                  value={runOptions.currentFollowers}
                  onChange={e => setRunOptions(o => ({ ...o, currentFollowers: e.target.value }))}
                  disabled={isRunning}
                  className="input-glass w-full"
                />
              </div>
              <div>
                <label className="text-xs text-white/40 mb-1.5 block">Target Followers</label>
                <input
                  type="number"
                  min={0}
                  placeholder="e.g. 50000"
                  value={runOptions.followerGoal}
                  onChange={e => setRunOptions(o => ({ ...o, followerGoal: e.target.value }))}
                  disabled={isRunning}
                  className="input-glass w-full"
                />
              </div>
            </div>

            <FollowerGoalCalculator
              currentFollowers={parseInt(runOptions.currentFollowers, 10) || 0}
              followerGoal={parseInt(runOptions.followerGoal, 10) || 0}
              daysAhead={runOptions.daysAhead}
              hasValues={runOptions.followerGoal !== ""}
            />
          </GlassCard>

          {/* Run History */}
          {pastRuns.length > 0 && (
            <GlassCard className="p-5">
              <div className="flex items-center gap-2 mb-3">
                <Layers className="w-4 h-4 text-brand-light" />
                <h2 className="font-semibold text-white text-sm">Recent Runs</h2>
              </div>
              <div className="space-y-2">
                {pastRuns.map((run, i) => (
                  <div key={run.id} className="flex items-center gap-2 py-1.5">
                    <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                      run.status === "completed" ? "bg-green-400"
                      : run.status === "failed"  ? "bg-red-400"
                      : run.status === "running" ? "bg-brand animate-pulse"
                      : "bg-white/20"
                    }`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-white/60 truncate">
                        {i === 0 ? "Latest" : new Date(run.createdAt).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                        {" · "}{run.postsGenerated} posts
                      </p>
                    </div>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                      run.status === "completed" ? "bg-green-500/10 text-green-400"
                      : run.status === "failed"  ? "bg-red-500/10 text-red-400"
                      : "bg-brand/10 text-brand-light"
                    }`}>
                      {run.status}
                    </span>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}
        </div>

        {/* ── Pipeline Visualizer ── */}
        <div className="col-span-2 space-y-4">
          <GlassCard className="p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-white text-sm">Pipeline Progress</h2>
              <span className="text-xs text-white/40">
                {completedCount}/{AGENT_ORDER.length} agents
                {isRunning && <span className="ml-2 text-brand-light animate-pulse">● running</span>}
              </span>
            </div>
            <ProgressBar value={progressPct} />

            <div className="grid grid-cols-2 gap-2 mt-4">
              {AGENT_ORDER.map((key) => {
                const agentData = agentStatuses[key];
                return (
                  <AgentNode
                    key={key}
                    agentKey={key}
                    status={(agentData?.status as "pending" | "running" | "completed" | "failed" | "skipped") ?? "pending"}
                    message={agentData?.message}
                    onClick={() => setSelectedAgentKey(key)}
                  />
                );
              })}
            </div>

            {/* Completion banner */}
            {pipelineDone && pipelineStatus === "completed" && (
              <div className="mt-4 p-4 rounded-xl bg-green-500/10 border border-green-500/20 flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-green-400 flex-shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-white">Pipeline Complete</p>
                  <p className="text-xs text-white/40 mt-0.5">
                    Generated {activeRun?.postsGenerated ?? completedCount} posts · Completed in {fmtTime(elapsedSec)}
                  </p>
                </div>
              </div>
            )}
          </GlassCard>

          {/* Generated Files — all PPT/Excel from every run for this brand */}
          <GeneratedFilesPanel runs={pastRuns} />

          {/* Live Logs */}
          <GlassCard variant="dark" className="p-5">
            <button
              onClick={() => setShowLogs(v => !v)}
              className="flex items-center justify-between w-full"
            >
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-brand-light" />
                <span className="text-sm font-medium text-white">Live Logs</span>
                {isRunning && <span className="w-2 h-2 rounded-full bg-brand-light animate-pulse" />}
                <span className="text-xs text-white/30 ml-1">({sseEvents.length})</span>
              </div>
              {showLogs ? <ChevronUp className="w-4 h-4 text-white/40" /> : <ChevronDown className="w-4 h-4 text-white/40" />}
            </button>

            {(showLogs || isRunning) && (
              <div className="mt-3 bg-dark-base/80 rounded-xl p-3 max-h-72 overflow-y-auto font-mono text-xs space-y-1">
                {sseEvents.length === 0 ? (
                  <p className="text-white/20 italic">Waiting for events…</p>
                ) : (
                  sseEvents.map((e, i) => (
                    <div key={i} className="flex gap-2 leading-relaxed">
                      <span className="text-white/20 flex-shrink-0 tabular-nums">
                        {e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : "--:--:--"}
                      </span>
                      <span className={
                        e.type === "agent_failed"   || e.type === "pipeline_failed"   ? "text-red-400"
                        : e.type === "agent_completed" || e.type === "pipeline_complete" ? "text-emerald-400"
                        : e.type === "agent_started"   ? "text-brand-light"
                        : "text-white/55"
                      }>
                        {e.agentKey ? `[${AGENT_LABELS[e.agentKey] ?? e.agentKey}] ` : ""}
                        {e.message ?? e.type}
                      </span>
                    </div>
                  ))
                )}
                <div ref={logsEndRef} />
              </div>
            )}
          </GlassCard>
        </div>
      </div>

      {/* Agent Detail Modal */}
      {selectedAgentKey && (
        <AgentDetailModal
          agentKey={selectedAgentKey}
          agentStatuses={agentStatuses}
          onClose={() => setSelectedAgentKey(null)}
        />
      )}
    </div>
  );
}

// ── Follower Goal Calculator ──────────────────────────────────────────────────

function FollowerGoalCalculator({
  currentFollowers,
  followerGoal,
  daysAhead,
  hasValues,
}: {
  currentFollowers: number;
  followerGoal: number;
  daysAhead: number;
  hasValues: boolean;
}) {
  if (!hasValues || followerGoal <= 0) {
    return (
      <p className="text-[10px] text-white/25 mt-3 leading-relaxed">
        Enter your target to see growth math and get a goal-adapted strategy
      </p>
    );
  }

  const gap      = Math.max(0, followerGoal - currentFollowers);
  const perDay   = daysAhead > 0 && gap > 0 ? gap / daysAhead : 0;
  const perWeek  = perDay * 7;
  const perMonth = perDay * 30;
  const progressPct = followerGoal > 0
    ? Math.min(100, Math.round((currentFollowers / followerGoal) * 100))
    : 0;
  const m25 = Math.round(currentFollowers + gap * 0.25);
  const m50 = Math.round(currentFollowers + gap * 0.50);
  const m75 = Math.round(currentFollowers + gap * 0.75);

  // Probability heuristic based on required daily growth
  const probability =
    perDay <= 0   ? 0
    : perDay <= 5  ? 88
    : perDay <= 15 ? 72
    : perDay <= 35 ? 52
    : perDay <= 70 ? 32
    : perDay <= 150 ? 18
    : 10;

  const probColor =
    probability >= 70 ? { bg: "bg-green-500/10", border: "border-green-500/20", text: "text-green-400" }
    : probability >= 40 ? { bg: "bg-yellow-500/10", border: "border-yellow-500/20", text: "text-yellow-400" }
    : { bg: "bg-red-500/10", border: "border-red-500/20", text: "text-red-400" };

  const probLabel =
    probability >= 70 ? "Achievable with consistent effort"
    : probability >= 40 ? "Aggressive — needs strong content cadence"
    : "Very aggressive — requires viral + paid strategy";

  function fmt(n: number) {
    return n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(Math.ceil(n));
  }

  return (
    <div className="mt-4 space-y-3">
      {/* Progress bar */}
      <div>
        <div className="flex justify-between text-[10px] text-white/40 mb-1.5">
          <span>{currentFollowers.toLocaleString()}</span>
          <span className="text-purple-400 font-medium">{progressPct}% of goal</span>
          <span>{followerGoal.toLocaleString()}</span>
        </div>
        <div className="relative h-2.5 bg-white/[0.08] rounded-full overflow-visible">
          <div
            className="absolute inset-y-0 left-0 bg-purple-500 rounded-full transition-all"
            style={{ width: `${Math.max(2, progressPct)}%` }}
          />
          {/* Milestone ticks */}
          {[25, 50, 75].map(pct => (
            <div
              key={pct}
              className="absolute top-0 bottom-0 w-px bg-white/30"
              style={{ left: `${pct}%` }}
            />
          ))}
        </div>
        {/* Milestone labels */}
        <div className="grid grid-cols-5 text-[9px] text-white/25 mt-1">
          <span />
          <span className="text-center">{(m25 / 1000).toFixed(1)}K</span>
          <span className="text-center">{(m50 / 1000).toFixed(1)}K</span>
          <span className="text-center">{(m75 / 1000).toFixed(1)}K</span>
          <span />
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-1.5">
        {[
          { label: "Need total", value: `+${gap.toLocaleString()}`, sub: "followers" },
          { label: "Per day",    value: `+${fmt(perDay)}`,          sub: "daily target" },
          { label: "Per week",   value: `+${fmt(perWeek)}`,         sub: "weekly target" },
          { label: "Per month",  value: `+${fmt(perMonth)}`,        sub: "monthly target" },
        ].map(({ label, value, sub }) => (
          <div key={label} className="p-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06]">
            <p className="text-[9px] text-white/30 uppercase tracking-wider">{label}</p>
            <p className="text-sm font-bold text-white mt-0.5">{value}</p>
            <p className="text-[9px] text-white/40">{sub}</p>
          </div>
        ))}
      </div>

      {/* Achievement probability */}
      <div className={`p-2.5 rounded-xl border ${probColor.bg} ${probColor.border}`}>
        <div className="flex items-center justify-between mb-0.5">
          <div className="flex items-center gap-1.5">
            <TrendingUp className="w-3 h-3 text-white/40" />
            <p className="text-[10px] text-white/50">Achievement Probability</p>
          </div>
          <p className={`text-sm font-bold ${probColor.text}`}>{probability}%</p>
        </div>
        <p className="text-[9px] text-white/35 leading-relaxed">{probLabel}</p>
      </div>

      {/* Milestones */}
      <div>
        <p className="text-[9px] text-white/30 uppercase tracking-wider mb-1.5">Milestones</p>
        <div className="space-y-1">
          {[
            { pct: "25%", value: m25 },
            { pct: "50%", value: m50 },
            { pct: "75%", value: m75 },
            { pct: "100%", value: followerGoal },
          ].map(({ pct, value }) => {
            const reached = currentFollowers >= value;
            return (
              <div key={pct} className="flex items-center gap-2">
                <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${reached ? "bg-purple-400" : "bg-white/15"}`} />
                <div className="flex-1 flex justify-between">
                  <span className={`text-[10px] ${reached ? "text-purple-400 font-medium" : "text-white/35"}`}>{pct}</span>
                  <span className={`text-[10px] font-mono ${reached ? "text-purple-400" : "text-white/40"}`}>
                    {value.toLocaleString()}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Agent Detail Modal ────────────────────────────────────────────────────────

type AgentStatusVal = "pending" | "running" | "completed" | "failed" | "skipped";

function fmtDuration(ms?: number | null): string {
  if (ms == null || ms < 0) return "—";
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${Math.round(s % 60)}s`;
}

function fmtClock(iso?: string): string {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }); }
  catch { return "—"; }
}

function MetaRow({ icon, title, items }: { icon: React.ReactNode; title: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-2">
        <span className="text-white/40">{icon}</span>
        <p className="text-[10px] font-semibold text-white/40 uppercase tracking-widest">{title}</p>
      </div>
      <ul className="space-y-1">
        {items.map((it, i) => (
          <li key={i} className="text-[13px] text-white/70 leading-relaxed flex gap-2">
            <span className="text-brand-light/60 mt-1.5 w-1 h-1 rounded-full bg-brand-light/50 flex-shrink-0" />
            <span>{it}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function AgentDetailModal({
  agentKey,
  agentStatuses,
  onClose,
}: {
  agentKey: string;
  agentStatuses: AgentStatuses;
  onClose: () => void;
}) {
  const label       = AGENT_LABELS[agentKey]       ?? agentKey;
  const icon        = AGENT_ICONS[agentKey]        ?? "🤖";
  const description = AGENT_DESCRIPTIONS[agentKey] ?? "";
  const produces    = AGENT_PRODUCES[agentKey]     ?? "";
  const meta        = AGENT_METADATA[agentKey];
  const agentData   = agentStatuses[agentKey];
  const status      = (agentData?.status ?? "pending") as AgentStatusVal;
  const message     = agentData?.message;

  const steps     = agentData?.steps ?? [];
  const queries   = agentData?.search_queries ?? [];
  const sources   = agentData?.sources_analyzed ?? [];
  const cats      = agentData?.source_categories ?? {};
  const platforms = agentData?.platforms_checked ?? [];
  const files     = agentData?.files_generated ?? [];

  // "After run" view is shown once the agent has actually executed.
  const hasExecution =
    status === "completed" || status === "failed" ||
    steps.length > 0 || !!agentData?.startedAt;

  const STATUS_BG: Record<AgentStatusVal, string> = {
    pending:   "bg-white/[0.06] text-white/40",
    running:   "bg-brand/15 text-brand-light border border-brand/30",
    completed: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
    failed:    "bg-red-500/10 text-red-400 border border-red-500/20",
    skipped:   "bg-white/[0.04] text-white/30",
  };
  const STATUS_LABEL: Record<AgentStatusVal, string> = {
    pending: "Pending", running: "Running", completed: "Completed",
    failed: "Failed",   skipped: "Skipped",
  };

  const sectionLabel = "text-[10px] font-semibold text-white/40 uppercase tracking-widest";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl rounded-2xl border border-white/[0.08] bg-[#0f1117] shadow-2xl max-h-[88vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start gap-3 p-6 pb-4 border-b border-white/[0.06]">
          <span className="text-3xl leading-none mt-0.5">{icon}</span>
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-semibold text-white">{label}</h2>
            <div className="flex items-center gap-2 mt-1">
              <span className={`inline-block text-[11px] font-medium px-2 py-0.5 rounded-full ${STATUS_BG[status]}`}>
                {STATUS_LABEL[status]}
              </span>
              <span className="text-[10px] text-white/30">
                {hasExecution ? "Execution report" : "Agent information"}
              </span>
            </div>
          </div>
          <button onClick={onClose} className="text-white/30 hover:text-white/70 transition text-xl leading-none mt-0.5">✕</button>
        </div>

        <div className="overflow-y-auto p-6 space-y-6">
          {message && (
            <div className="px-3 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.06]">
              <p className="text-xs text-white/60 leading-relaxed">{message}</p>
            </div>
          )}

          {!hasExecution ? (
            /* ───────────── BEFORE RUN — Agent Information Panel ───────────── */
            <>
              {meta ? (
                <>
                  <div className="grid sm:grid-cols-2 gap-5">
                    <div>
                      <p className={sectionLabel + " mb-2"}>Purpose</p>
                      <p className="text-[13px] text-white/70 leading-relaxed">{meta.purpose}</p>
                    </div>
                    <div>
                      <p className={sectionLabel + " mb-2"}>Objective</p>
                      <p className="text-[13px] text-white/70 leading-relaxed">{meta.objective}</p>
                    </div>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-x-6 gap-y-5">
                    <MetaRow icon={<FileText className="w-3.5 h-3.5" />}   title="Inputs Required"   items={meta.inputs} />
                    <MetaRow icon={<CheckCircle2 className="w-3.5 h-3.5" />} title="Expected Outputs" items={meta.outputs} />
                    <MetaRow icon={<Layers className="w-3.5 h-3.5" />}     title="Tools Used"        items={meta.tools} />
                    <MetaRow icon={<Globe className="w-3.5 h-3.5" />}      title="Data Sources"      items={meta.dataSources} />
                    <MetaRow icon={<Target className="w-3.5 h-3.5" />}     title="Dependencies"      items={meta.dependencies} />
                    <MetaRow icon={<ListChecks className="w-3.5 h-3.5" />} title="Success Criteria"  items={meta.successCriteria} />
                  </div>
                </>
              ) : (
                <div>
                  <p className={sectionLabel + " mb-2"}>What it does</p>
                  <p className="text-sm text-white/65 leading-relaxed">{description}</p>
                </div>
              )}

              {produces && (
                <div>
                  <p className={sectionLabel + " mb-2"}>Produces</p>
                  <div className="flex flex-wrap gap-1.5">
                    {produces.split(" · ").map((item) => (
                      <span key={item} className="text-[11px] px-2.5 py-1 rounded-full bg-brand/10 border border-brand/20 text-brand-light">
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            /* ───────────── AFTER RUN — Execution Report ───────────── */
            <>
              {/* Execution summary */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {[
                  { label: "Status",   value: STATUS_LABEL[status] },
                  { label: "Start",    value: fmtClock(agentData?.startedAt) },
                  { label: "End",      value: fmtClock(agentData?.completedAt) },
                  { label: "Duration", value: fmtDuration(agentData?.durationMs) },
                ].map(({ label: l, value }) => (
                  <div key={l} className="p-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06]">
                    <p className="text-[9px] text-white/30 uppercase tracking-wider">{l}</p>
                    <p className="text-[13px] font-semibold text-white mt-0.5 truncate">{value}</p>
                  </div>
                ))}
              </div>

              {/* Execution timeline */}
              {steps.length > 0 && (
                <div>
                  <div className="flex items-center gap-1.5 mb-3">
                    <Clock className="w-3.5 h-3.5 text-white/40" />
                    <p className={sectionLabel}>Execution Timeline</p>
                  </div>
                  <ol className="relative border-l border-white/[0.08] ml-1.5 space-y-3">
                    {steps.map((st, i) => (
                      <li key={i} className="ml-4">
                        <span className="absolute -left-[5px] mt-1.5 w-2 h-2 rounded-full bg-brand-light/70" />
                        <div className="flex items-start justify-between gap-3">
                          <p className="text-[13px] text-white/75 leading-snug">
                            <span className="text-white/35 mr-1.5">Step {i + 1}:</span>{st.label}
                          </p>
                          {st.timestamp && <span className="text-[10px] text-white/25 whitespace-nowrap mt-0.5">{fmtClock(st.timestamp)}</span>}
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {/* Research visibility — queries */}
              {queries.length > 0 && (
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <Search className="w-3.5 h-3.5 text-white/40" />
                    <p className={sectionLabel}>Search Queries Used</p>
                  </div>
                  <div className="space-y-1.5">
                    {queries.map((q, i) => (
                      <div key={i} className="text-[12px] text-white/65 px-2.5 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.05] font-mono leading-snug">
                        {q}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Platforms checked */}
              {platforms.length > 0 && (
                <div>
                  <p className={sectionLabel + " mb-2"}>Platforms Checked</p>
                  <div className="flex flex-wrap gap-1.5">
                    {platforms.map((p) => (
                      <span key={p} className="text-[11px] px-2.5 py-1 rounded-full bg-white/[0.05] border border-white/[0.08] text-white/60">{p}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Source tracking — categorised (competitor analysis) */}
              {Object.keys(cats).length > 0 && (
                <div>
                  <div className="flex items-center gap-1.5 mb-3">
                    <Users className="w-3.5 h-3.5 text-white/40" />
                    <p className={sectionLabel}>Sources Analyzed by Platform</p>
                  </div>
                  <div className="space-y-3">
                    {Object.entries(cats).map(([cat, list]) => (
                      <div key={cat}>
                        <p className="text-[11px] font-medium text-white/55 mb-1">{cat} <span className="text-white/30">({list.length})</span></p>
                        <div className="space-y-1">
                          {list.slice(0, 8).map((s, i) => (
                            <a key={i} href={s.url} target="_blank" rel="noopener noreferrer"
                               className="block text-[11px] text-brand-light/80 hover:text-brand-light truncate">
                              {s.title || s.url}
                            </a>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Research visibility — flat URL list (when not categorised) */}
              {Object.keys(cats).length === 0 && sources.length > 0 && (
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <Link2 className="w-3.5 h-3.5 text-white/40" />
                    <p className={sectionLabel}>URLs Analyzed ({sources.length})</p>
                  </div>
                  <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
                    {sources.map((s, i) => (
                      <a key={i} href={s.url} target="_blank" rel="noopener noreferrer"
                         className="block text-[11px] text-brand-light/80 hover:text-brand-light truncate">
                        {s.title || s.url}
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* File traceability */}
              {files.length > 0 && (
                <div>
                  <div className="flex items-center gap-1.5 mb-3">
                    <FileSearch className="w-3.5 h-3.5 text-white/40" />
                    <p className={sectionLabel}>Files Generated & Provenance</p>
                  </div>
                  <div className="space-y-3">
                    {files.map((f, i) => (
                      <div key={i} className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                        <div className="flex items-center gap-2 mb-1.5">
                          <FileText className="w-4 h-4 text-brand-light" />
                          <p className="text-[13px] font-medium text-white">{f.name}</p>
                          {f.data_confidence && (
                            <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${
                              f.data_confidence === "high" ? "bg-emerald-500/10 text-emerald-400"
                              : f.data_confidence === "medium" ? "bg-yellow-500/10 text-yellow-400"
                              : "bg-red-500/10 text-red-400"}`}>
                              {f.data_confidence} confidence
                            </span>
                          )}
                        </div>
                        {f.type && <p className="text-[11px] text-white/40 mb-2">{f.type}</p>}
                        {f.produced_from && f.produced_from.length > 0 && (
                          <>
                            <p className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Built from</p>
                            <ul className="space-y-0.5">
                              {f.produced_from.map((p, j) => (
                                <li key={j} className="text-[11px] text-white/60 flex gap-1.5">
                                  <span className="text-white/25">→</span><span>{p}</span>
                                </li>
                              ))}
                            </ul>
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Static reference (what this agent does) for context */}
              {description && (
                <div className="pt-2 border-t border-white/[0.06]">
                  <p className={sectionLabel + " mb-2"}>About this agent</p>
                  <p className="text-[13px] text-white/55 leading-relaxed">{description}</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Generated Files Panel ─────────────────────────────────────────────────────

type RunLike = { id: string; createdAt: string; mode?: string; pptUrl?: string; excelUrl?: string };

function GeneratedFilesPanel({ runs }: { runs: RunLike[] }) {
  type FileEntry = { runId: string; url: string; kind: "ppt" | "excel"; mode: string; createdAt: string; version: number };
  const entries: FileEntry[] = [];
  const oldestFirst = [...runs].sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime());
  const counters: Record<string, number> = {};
  for (const r of oldestFirst) {
    const mode = r.mode ?? "pipeline";
    if (r.pptUrl)   { const k = `${mode}|ppt`;   counters[k] = (counters[k] ?? 0) + 1; entries.push({ runId: r.id, url: r.pptUrl,   kind: "ppt",   mode, createdAt: r.createdAt, version: counters[k] }); }
    if (r.excelUrl) { const k = `${mode}|excel`; counters[k] = (counters[k] ?? 0) + 1; entries.push({ runId: r.id, url: r.excelUrl, kind: "excel", mode, createdAt: r.createdAt, version: counters[k] }); }
  }
  entries.reverse();

  const modeLabel = (m: string) =>
    m === "growth_planner_only" ? "Growth Planner" :
    m === "performance_report"  ? "Performance Report" :
    m === "full_pipeline"       ? "Full Pipeline" :
    m.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  const kindColor = (k: "ppt" | "excel") =>
    k === "ppt"
      ? { bg: "bg-purple-500/10", border: "border-purple-500/25", text: "text-purple-300", icon: "text-purple-400", label: "PPT" }
      : { bg: "bg-emerald-500/10", border: "border-emerald-500/25", text: "text-emerald-300", icon: "text-emerald-400", label: "XLSX" };

  return (
    <GlassCard className="p-5">
      <div className="flex items-center gap-2 mb-4">
        <FileText className="w-4 h-4 text-brand-light" />
        <h2 className="font-semibold text-white text-sm">Generated Files</h2>
        {entries.length > 0 && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.06] text-white/50">{entries.length} files · shared across team</span>
        )}
      </div>
      {entries.length === 0 ? (
        <div className="py-6 text-center">
          <FileText className="w-7 h-7 text-white/20 mx-auto mb-2" />
          <p className="text-sm text-white/40">No files yet</p>
          <p className="text-xs text-white/30 mt-1">Run a pipeline to generate PPT &amp; Excel files</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
          {entries.map((e) => {
            const c = kindColor(e.kind);
            const dateStr = new Date(e.createdAt).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
            return (
              <a key={`${e.runId}-${e.kind}`} href={e.url} target="_blank" rel="noopener noreferrer"
                className={`flex items-center gap-3 p-3 rounded-xl ${c.bg} border ${c.border} hover:bg-white/[0.04] transition-all group`}
              >
                <div className={`flex-shrink-0 w-8 h-8 rounded-lg bg-dark-base/40 flex items-center justify-center ${c.icon}`}>
                  <FileText className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-sm font-semibold ${c.text}`}>{modeLabel(e.mode)}</span>
                    <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${c.bg} ${c.text} border ${c.border}`}>v{e.version}</span>
                    <span className={`text-[10px] font-bold ${c.icon}`}>{c.label}</span>
                  </div>
                  <p className="text-[11px] text-white/40 mt-0.5">{dateStr}</p>
                </div>
                <Download className="w-4 h-4 text-white/30 group-hover:text-white/70 transition-colors" />
              </a>
            );
          })}
        </div>
      )}
    </GlassCard>
  );
}
