import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string | number;
  delta?: number;
  deltaLabel?: string;
  icon?: React.ReactNode;
  className?: string;
}

export function MetricCard({ label, value, delta, deltaLabel, icon, className }: MetricCardProps) {
  const isPositive = delta !== undefined && delta > 0;
  const isNegative = delta !== undefined && delta < 0;

  return (
    <div className={cn("metric-card", className)}>
      <div className="flex items-start justify-between mb-3">
        <p className="metric-label">{label}</p>
        {icon && (
          <div className="w-8 h-8 rounded-lg bg-brand/10 flex items-center justify-center">
            {icon}
          </div>
        )}
      </div>
      <p className="metric-value">{value}</p>
      {delta !== undefined && (
        <div className="flex items-center gap-1 mt-2">
          {isPositive ? (
            <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
          ) : isNegative ? (
            <TrendingDown className="w-3.5 h-3.5 text-red-400" />
          ) : (
            <Minus className="w-3.5 h-3.5 text-white/30" />
          )}
          <span
            className={cn(
              "metric-delta",
              isPositive ? "text-emerald-400" : isNegative ? "text-red-400" : "text-white/30"
            )}
          >
            {isPositive ? "+" : ""}{delta.toFixed(1)}%{deltaLabel ? ` ${deltaLabel}` : ""}
          </span>
        </div>
      )}
    </div>
  );
}
