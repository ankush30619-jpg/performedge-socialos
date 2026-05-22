import { cn } from "@/lib/utils";

type Status = "idle" | "running" | "completed" | "failed" | "pending";

const STATUS_CONFIG: Record<Status, { label: string; className: string }> = {
  idle: { label: "Idle", className: "bg-white/10 text-white/50" },
  pending: { label: "Pending", className: "bg-yellow-500/20 text-yellow-400" },
  running: { label: "Running", className: "bg-brand/20 text-brand-light animate-pulse" },
  completed: { label: "Completed", className: "bg-emerald-500/20 text-emerald-400" },
  failed: { label: "Failed", className: "bg-red-500/20 text-red-400" },
};

interface StatusBadgeProps {
  status: Status;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.idle;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium",
        cfg.className,
        className
      )}
    >
      <span
        className={cn(
          "w-1.5 h-1.5 rounded-full",
          status === "running"
            ? "bg-brand-light"
            : status === "completed"
            ? "bg-emerald-400"
            : status === "failed"
            ? "bg-red-400"
            : "bg-white/30"
        )}
      />
      {cfg.label}
    </span>
  );
}
