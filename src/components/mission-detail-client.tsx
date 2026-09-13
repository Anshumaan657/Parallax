"use client";

import Link from "next/link";
import { ArrowLeft, Check, Circle, ExternalLink, LoaderCircle, RotateCcw, TerminalSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { MissionStatusBadge, formatRelativeTime } from "@/components/mission-status";
import { useMission } from "@/lib/queries";

export function MissionDetailClient({ id }: { id: number }) {
  const mission = useMission(id);

  if (mission.isLoading) return <div className="mx-auto max-w-5xl space-y-4 px-4 py-8 sm:px-6 lg:px-8"><Skeleton className="h-9 w-64" /><Skeleton className="h-28 w-full" /><Skeleton className="h-80 w-full" /></div>;
  if (mission.error || !mission.data) return <div className="mx-auto max-w-3xl px-4 py-10"><div className="border border-destructive/20 bg-danger-soft p-6"><h1 className="text-lg font-semibold">Mission unavailable</h1><p className="mt-2 text-sm text-muted-foreground">The mission could not be loaded from the current data source.</p><Button nativeButton={false} className="mt-4" variant="outline" render={<Link href="/missions" />}>Back to missions</Button></div></div>;

  const item = mission.data;
  const running = item.status === "queued" || item.status === "running";
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <Button nativeButton={false} variant="ghost" size="sm" render={<Link href="/missions" />} className="mb-4 -ml-2 gap-2"><ArrowLeft className="size-4" />Missions</Button>
      <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(280px,0.7fr)]">
        <div className="min-w-0 space-y-5">
          <section className="border bg-card p-5 sm:p-6">
            <div className="flex flex-wrap items-center gap-2"><MissionStatusBadge status={item.status} /><span className="font-mono text-xs text-muted-foreground">MISSION-{item.id}</span><span className="text-xs text-muted-foreground">Updated {formatRelativeTime(item.updatedAt)}</span></div>
            <h1 className="mt-4 max-w-4xl [overflow-wrap:anywhere] text-xl font-semibold leading-8 sm:text-2xl">{item.prompt}</h1>
            <div className="mt-5 flex flex-wrap items-center gap-3 border-t pt-4 text-sm"><span className="rounded-md bg-muted px-2.5 py-1">{item.project}</span><span className="text-muted-foreground">{item.steps.length} completed tool {item.steps.length === 1 ? "call" : "calls"}</span>{running && <span className="flex items-center gap-2 text-info"><LoaderCircle className="size-4 animate-spin" />Agent is working</span>}</div>
          </section>

          <section className="border bg-card" aria-labelledby="timeline-title"><div className="flex min-h-12 items-center gap-2 border-b px-4"><TerminalSquare className="size-4 text-muted-foreground" /><h2 id="timeline-title" className="text-sm font-semibold">Tool activity</h2></div><ol className="divide-y px-4">
            {!item.steps.length && <li className="py-10 text-center text-sm text-muted-foreground">{item.status === "queued" ? "Waiting for the agent runner." : "No tool calls were recorded."}</li>}
            {item.steps.map((step) => <li key={`${step.step}-${step.at}`} className="grid grid-cols-[auto_minmax(0,1fr)] gap-3 py-4"><span className="mt-0.5 grid size-7 place-items-center rounded-full bg-success-soft text-success"><Check className="size-3.5" /></span><div className="min-w-0"><div className="flex flex-wrap items-baseline gap-2"><h3 className="font-mono text-sm font-semibold">{step.tool}</h3><time dateTime={step.at} className="font-mono text-xs text-muted-foreground">{new Date(step.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time></div>{Object.keys(step.input).length > 0 && <pre className="mt-2 overflow-x-auto rounded-md bg-surface-inset p-3 font-mono text-xs leading-5 text-muted-foreground">{JSON.stringify(step.input, null, 2)}</pre>}<p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">{step.output}</p></div></li>)}
            {running && <li className="grid grid-cols-[auto_minmax(0,1fr)] gap-3 py-4"><span className="mt-0.5 grid size-7 place-items-center rounded-full bg-info-soft text-info"><Circle className="size-3.5 fill-current" /></span><div><h3 className="text-sm font-medium">Waiting for the next operation</h3><p className="mt-1 text-sm text-muted-foreground">New activity will appear automatically.</p></div></li>}
          </ol></section>
        </div>

        <aside className="space-y-5">
          <section className="border bg-card p-5"><h2 className="text-sm font-semibold">Result</h2><p className="mt-3 text-sm leading-6 text-muted-foreground">{item.resultSummary ?? (running ? "Parallax will add a concise result when the mission finishes." : "No result summary was recorded.")}</p></section>
          <section className="border bg-card p-5"><h2 className="text-sm font-semibold">Actions</h2><div className="mt-3 space-y-2"><Button nativeButton={false} variant="outline" className="w-full justify-start gap-2" render={<Link href={`/dashboard?prompt=${encodeURIComponent(item.prompt)}`} />}><RotateCcw className="size-4" />Use as a new mission</Button><Button nativeButton={false} variant="ghost" className="w-full justify-start gap-2" render={<Link href="/integrations" />}><ExternalLink className="size-4" />Check connected apps</Button></div></section>
        </aside>
      </div>
      <p className="sr-only" aria-live="polite">Mission status is {item.status}.</p>
    </div>
  );
}
