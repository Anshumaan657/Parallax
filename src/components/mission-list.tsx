import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { MissionStatusBadge, formatRelativeTime } from "@/components/mission-status";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { Mission, MissionStatus } from "@/lib/api/types";

export function MissionListSkeleton({ rows = 5 }: { rows?: number }) {
  return <div className="space-y-2">{Array.from({ length: rows }).map((_, index) => <Skeleton key={index} className="h-[76px] w-full rounded-xl" />)}</div>;
}

export function MissionList({ missions, limit, filter = "all" }: { missions: Mission[]; limit?: number; filter?: MissionStatus | "all" }) {
  const filtered = missions.filter((mission) => filter === "all" || mission.status === filter).slice(0, limit);
  if (!filtered.length) return <div className="grid min-h-40 place-items-center rounded-xl border border-dashed bg-surface-inset px-6 text-center text-sm text-muted-foreground">No missions match this view.</div>;
  return <div className="divide-y border-y">{filtered.map((mission) => <article key={mission.id} className="group grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-3 py-3.5 sm:gap-4"><div className="min-w-0"><Link href={`/missions/${mission.id}`} className="block truncate text-sm font-medium hover:text-primary">{mission.prompt}</Link><div className="mt-1.5 flex min-w-0 flex-wrap items-center gap-2 text-xs text-muted-foreground"><MissionStatusBadge status={mission.status} /><span>{mission.project}</span><span aria-hidden="true">·</span><span className="font-mono">{mission.progress_current}/{mission.progress_total} steps</span><span aria-hidden="true">·</span><time dateTime={mission.updated_at}>{formatRelativeTime(mission.updated_at)}</time></div></div><Button nativeButton={false} variant="ghost" size="icon" render={<Link href={`/missions/${mission.id}`} aria-label={`Open mission ${mission.id}`} />}><ArrowRight className="size-4" /></Button></article>)}</div>;
}
