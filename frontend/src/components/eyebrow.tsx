import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

/** Etiqueta pequeña, mono, tracked-wide, con el marcador "// " — ver plan del 2026-08-22. */
export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "font-mono text-[11px] tracking-wider text-muted-foreground uppercase",
        className
      )}
    >
      <span className="text-foreground/40">// </span>
      {children}
    </span>
  )
}
