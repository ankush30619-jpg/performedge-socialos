import { cn } from "@/lib/utils";
import { AGENT_LABELS, AGENT_ICONS } from "@/lib/utils";
import { CheckCircle2, XCircle, Loader2, Clock } from "lucide-react";

type AgentStatus = "pending" | "running" | "completed" | "failed" | "skipped";

interface AgentNodeProps {
  agentKey: string;
  status: AgentStatus;
  message?: string;
  className?: string;
}

const STATUS_CLASSES: Record<AgentStatus, string> = {
  pending: "agent-node-pending",
  running: "agent-node-running",
  completed: "agent-node-done",
  failed: "agent-node-failed",
  skipped: "opacity-40",
};

const StatusIcon = ({ status }: { status: AgentStatus }) => {
  if (status === "completed") return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
  if (status === "failed") return <XCircle className="w-3.5 h-3.5 text-red-400" />;
  if (status === "running") return <Loader2 className="w-3.5 h-3.5 text-brand-light animate-spin" />;
  return <Clock className="w-3.5 h-3.5 text-white/30" />;
};

export function AgentNode({ agentKey, status, message, className }: AgentNodeProps) {
  const label = AGENT_LABELS[agentKey] ?? agentKey;
  const icon = AGENT_ICONS[agentKey] ?? "🤖";

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div
        className={cn(
          "flex items-center gap-2.5 px-3 py-2.5 rounded-xl border transition-all duration-300",
          STATUS_CLASSES[status]
        )}
      >
        <span className="text-base leading-none">{icon}</span>
        <span className="text-sm font-medium text-white/80 flex-1">{label}</span>
        <StatusIcon status={status} />
      </div>
      {message && (
        <p className="text-[11px] text-white/40 px-1 line-clamp-2">{message}</p>
      )}
    </div>
  );
}
