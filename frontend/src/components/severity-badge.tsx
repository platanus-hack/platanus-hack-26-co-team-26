import { cn } from "@/lib/utils"
import type { Severity } from "@/lib/types"

const LABEL: Record<Severity, string> = {
  critical: "crítica",
  high: "alta",
  medium: "media",
  low: "baja",
}

const DOT: Record<Severity, string> = {
  critical: "bg-severity-critical",
  high: "bg-severity-high",
  medium: "bg-severity-medium",
  low: "bg-severity-low",
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span className="inline-flex shrink-0 items-center gap-1.5 font-mono text-[11px] tracking-wide text-muted-foreground uppercase">
      <span className={cn("size-1.5 shrink-0", DOT[severity])} aria-hidden />
      {LABEL[severity]}
    </span>
  )
}
