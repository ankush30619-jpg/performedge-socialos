"use client";
import { useState, useEffect, useRef } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { agentAPI, createSSEConnection } from "@/lib/api";
import { useAppStore, useActiveBrand } from "@/store/useAppStore";
import { GlassCard } from "@/components/ui/GlassCard";
import { AgentNode } from "@/components/ui/AgentNode";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { AGENT_LABELS } from "@/lib/utils";
import {
  Play, StopCircle, Download, ChevronDown, ChevronUp, Terminal,
  Clock, CheckCircle2, Layers, FileText, Presentation,
  Calendar, Paintbrush, RefreshCw,
} from "lucide-react";
import Link from "next/link";
import type { SSEEvent, AgentRun } from "@/types";

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

type AgentStatuses = Record<string, { status: string; message?: string }>;

export default function AgentsPage() {
  const activeBrand = useActiveBrand();
  const { addSSEEvent, clearSSEEvents, sseEvents, setActiveRun, activeRun } = useAppStore();
  const [agentStatuses, setAgentStatuses] = useState<AgentStatuses>({});
  const [showLogs, setShowLogs]           = useState(false);
  const [pipelineDone, setPipelineDone]   = useState(false);
  const [isPipelineActive, setIsPipelineActive] = useState(false); // true while pipeline running
  const [elapsedSec, setElapsedSec]       = useState(0);
  const [runOptions, setRunOptions]       = useState({ mode: "full", daysAhead: 15 });
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
        // Update agent statuses from DB if we have them
        if (run.agentStatuses && Object.keys(run.agentStatuses).length > 0) {
          setAgentStatuses(prev => ({ ...run.agentStatuses as AgentStatuses, ...prev }));
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
    mutationFn: () => agentAPI.run(activeBrand!.id, {
      mode:      runOptions.mode,
      daysAhead: runOptions.daysAhead,
    }),
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
    </div>
  );
}
