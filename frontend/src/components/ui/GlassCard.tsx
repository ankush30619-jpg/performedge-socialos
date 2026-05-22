"use client";
import { cn } from "@/lib/utils";
import { motion, type MotionProps } from "framer-motion";
import { forwardRef } from "react";

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "raised" | "dark" | "brand";
  animate?: boolean;
  motionProps?: MotionProps;
}

const variants = {
  default: "bg-dark-mid/60 backdrop-blur-xl border border-white/[0.08]",
  raised: "bg-dark-raised/50 backdrop-blur-xl border border-white/[0.1] shadow-glass",
  dark: "bg-dark-base/80 backdrop-blur-xl border border-white/[0.06]",
  brand: "bg-brand/10 backdrop-blur-xl border border-brand/30",
};

export const GlassCard = forwardRef<HTMLDivElement, GlassCardProps>(
  ({ className, variant = "default", animate = true, motionProps, children, ...props }, ref) => {
    const baseClass = cn(variants[variant], "rounded-2xl", className);

    if (animate) {
      return (
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className={baseClass}
          {...motionProps}
          {...(props as unknown as MotionProps)}
        >
          {children}
        </motion.div>
      );
    }

    return (
      <div ref={ref} className={baseClass} {...props}>
        {children}
      </div>
    );
  }
);
GlassCard.displayName = "GlassCard";
