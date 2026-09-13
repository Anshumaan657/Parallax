import { Badge } from "@/components/ui/badge";
import type { MissionStatus } from "@/lib/domain";
import { cn } from "@/lib/utils";

const statusConfig: Record<MissionStatus, { label: string; className: string }> = {
  queued: { label: "Queued", className: "border-border bg-muted text-muted-foreground" },
  running: { label: "Running", className: "border-info/25 bg-info-soft text-foreground" },
  completed: { label: "Completed", className: "border-success/25 bg-success-soft text-foreground" },
  blocked: { label: "Blocked", className: "border-warning/30 bg-warning-soft text-foreground" },
  failed: { label: "Failed", className: "border-destructive/25 bg-danger-soft text-destructive" },
};

export function MissionStatusBadge({ status }: { status: MissionStatus }) {
  const config = statusConfig[status];
  return (
    <Badge variant="outline" className={cn("gap-1.5", config.className)}>
      <span className={cn("size-1.5 rounded-full", status === "running" ? "bg-info" : status === "completed" ? "bg-success" : status === "failed" ? "bg-destructive" : status === "blocked" ? "bg-warning" : "bg-muted-foreground")} aria-hidden="true" />
      {config.label}
    </Badge>
  );
}

export function formatRelativeTime(value: string) {
  const minutes = Math.max(0, Math.round((Date.now() - Date.parse(value)) / 60_000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

