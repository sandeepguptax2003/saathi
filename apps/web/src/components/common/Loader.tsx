import { Loader2Icon } from "lucide-react";

import { cn } from "@/lib/utils";

export interface LoaderProps {
  label?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
  /** Show the label visibly next to the spinner (otherwise screen-reader only). */
  showLabel?: boolean;
}

const SIZE = { sm: "size-4", md: "size-6", lg: "size-10" } as const;

export function Loader({ label = "Loading…", size = "md", className, showLabel }: LoaderProps) {
  return (
    <span role="status" className={cn("inline-flex items-center gap-2", className)}>
      <Loader2Icon aria-hidden="true" className={cn("animate-spin text-primary", SIZE[size])} />
      <span className={showLabel ? "text-sm text-muted-foreground" : "sr-only"}>{label}</span>
    </span>
  );
}
