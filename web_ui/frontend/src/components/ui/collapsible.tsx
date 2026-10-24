"use client";

import * as React from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface CollapsibleProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
  title: React.ReactNode;
  /** Small colored bar accent next to the title */
  accentClassName?: string;
  /** Optional icon rendered before the accent bar */
  icon?: React.ReactNode;
  /** Short one-line summary shown next to the title (e.g. current value) */
  summary?: React.ReactNode;
  defaultOpen?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

/**
 * Card-style collapsible section used to group configuration settings.
 * Uncontrolled by default; pass `open`/`onOpenChange` to control it.
 */
const Collapsible = React.forwardRef<HTMLDivElement, CollapsibleProps>(
  (
    {
      title,
      accentClassName = "bg-primary",
      icon,
      summary,
      defaultOpen = false,
      open,
      onOpenChange,
      className,
      children,
      ...props
    },
    ref
  ) => {
    const [internalOpen, setInternalOpen] = React.useState(defaultOpen);
    const isControlled = open !== undefined;
    const isOpen = isControlled ? open : internalOpen;

    const toggle = () => {
      const next = !isOpen;
      if (!isControlled) setInternalOpen(next);
      onOpenChange?.(next);
    };

    return (
      <div
        ref={ref}
        className={cn(
          "bg-card border border-border/50 rounded-xl shadow-sm backdrop-blur-md overflow-hidden",
          className
        )}
        {...props}
      >
        <button
          type="button"
          onClick={toggle}
          aria-expanded={isOpen}
          className="w-full flex items-center gap-3 px-6 py-4 text-left hover:bg-muted/30 transition-colors"
        >
          {icon}
          <span className={cn("w-2 h-6 rounded-full shrink-0", accentClassName)} />
          <span className="text-xl font-bold">{title}</span>
          {summary && (
            <span className="text-xs text-muted-foreground truncate hidden sm:inline">
              {summary}
            </span>
          )}
          <ChevronDown
            className={cn(
              "w-5 h-5 ml-auto shrink-0 text-muted-foreground transition-transform duration-200",
              isOpen && "rotate-180"
            )}
          />
        </button>
        {isOpen && (
          <div className="px-6 pb-6 pt-1 border-t border-border/30">
            <div className="pt-4 space-y-4">{children}</div>
          </div>
        )}
      </div>
    );
  }
);
Collapsible.displayName = "Collapsible";

export { Collapsible };
