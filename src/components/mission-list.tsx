"use client";

import Link from "next/link";
import { ArrowRight, BriefcaseBusiness, CircleCheckBig, CircleX, Clock3, LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { Mission, MissionStatus } from "@/lib/domain";
import { formatRelativeTime, MissionStatusBadge } from "@/components/mission-status";

export function MissionList({ missions, loading = false, limit, filter = "all" }: { missions?: Mission[]; loading?: boolean; limit?: number; filter?: MissionStatus | "all" }) {
  if (loading) return <div className="space-y-2">{Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-[76px] w-full" />)}</div>;
  const filtered = (missions ?? []).filter((mission) => filter === "all" || mission.status === filter).slice(0, limit);

  if (!filtered.length) {
    return <div className="grid min-h-40 place-items-center border border-dashed bg-surface-inset px-6 text-center text-sm text-muted-foreground">No missions match this view.</div>;
  }

  return (
    <div className="divide-y border-y">
      {filtered.map((mission) => (
        <article key={mission.id} className="group grid min-w-0 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 py-3.5 sm:gap-4">
          <span className="grid size-9 place-items-center rounded-lg border bg-surface-inset text-muted-foreground">
            {mission.status === "running" ? <LoaderCircle className="size-4 text-info motion-safe:animate-spin" /> : mission.status === "completed" ? <CircleCheckBig className="size-4 text-success" /> : mission.status === "failed" ? <CircleX className="size-4 text-destructive" /> : mission.status === "queued" ? <Clock3 className="size-4" /> : <BriefcaseBusiness className="size-4 text-warning" />}
          </span>
          <div className="min-w-0">
            <Link href={`/missions/${mission.id}`} className="block truncate text-sm font-medium hover:text-primary">{mission.prompt}</Link>
            <div className="mt-1.5 flex min-w-0 flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <MissionStatusBadge status={mission.status} />
              <span>{mission.project}</span><span aria-hidden="true">·</span>
              <span className="font-mono">{mission.steps.length} tool {mission.steps.length === 1 ? "call" : "calls"}</span>
              <span aria-hidden="true">·</span><time dateTime={mission.updatedAt}>{formatRelativeTime(mission.updatedAt)}</time>
            </div>
          </div>
          <Button nativeButton={false} variant="ghost" size="icon" render={<Link href={`/missions/${mission.id}`} aria-label={`Open mission ${mission.id}`} />}><ArrowRight className="size-4" /></Button>
        </article>
      ))}
    </div>
  );
}
