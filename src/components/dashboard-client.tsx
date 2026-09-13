"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Activity, CheckCheck, CircleAlert, Clock3, ListTodo } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MissionComposer } from "@/components/mission-composer";
import { MissionList } from "@/components/mission-list";
import { ActivityPanel, AgentInsightsPanel, ConnectedAppsPanel, ProjectsPanel, QuickActionsPanel } from "@/components/dashboard-panels";
import type { MissionStatus } from "@/lib/domain";
import { isMockMode } from "@/lib/api";
import { useActivity, useDashboardStats, useIntegrations, useMissions, useProjects } from "@/lib/queries";

const statItems = [
  { key: "active", label: "Active", icon: Activity, filter: "running" as MissionStatus },
  { key: "completedThisWeek", label: "Completed · 7d", icon: CheckCheck, filter: "completed" as MissionStatus },
  { key: "blockedOrFailed", label: "Needs attention", icon: CircleAlert, filter: "failed" as MissionStatus },
  { key: "queued", label: "Queued", icon: Clock3, filter: "queued" as MissionStatus },
] as const;

export function DashboardClient({ initialPrompt, autoFocusComposer = false }: { initialPrompt?: string; autoFocusComposer?: boolean }) {
  const missions = useMissions();
  const active = missions.data?.some((mission) => mission.status === "queued" || mission.status === "running") ?? false;
  const stats = useDashboardStats(active);
  const projects = useProjects();
  const integrations = useIntegrations();
  const activity = useActivity(active);
  const [filter, setFilter] = useState<MissionStatus | "all">("all");
  const [suggestedPrompt, setSuggestedPrompt] = useState<string | undefined>(initialPrompt);

  const metrics = useMemo(() => stats.data ? { ...stats.data } : undefined, [stats.data]);

  return (
    <div className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0"><p className="mb-1 font-mono text-xs font-medium uppercase tracking-[0.16em] text-primary">Engineering operations</p><h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Mission control</h1><p className="mt-1 text-sm text-muted-foreground">Track agent work across connected systems.</p></div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground"><span className={`size-2 rounded-full ${active ? "bg-info" : "bg-success"}`} aria-hidden="true" /><span>{active ? "Agent is working" : "Agent is ready"}</span>{isMockMode && <span className="rounded border bg-warning-soft px-2 py-0.5 text-xs text-foreground">Simulated</span>}</div>
      </header>

      <section aria-label="Mission summary" className="mb-5 grid border bg-card sm:grid-cols-2 xl:grid-cols-[repeat(4,minmax(0,1fr))_1.1fr]">
        {statItems.map(({ key, label, icon: Icon, filter: itemFilter }) => <button key={key} type="button" onClick={() => setFilter((current) => current === itemFilter ? "all" : itemFilter)} className={`flex min-h-24 items-center gap-3 border-b px-4 text-left hover:bg-surface-inset sm:border-r xl:border-b-0 ${filter === itemFilter ? "bg-accent/60" : ""}`}><span className="grid size-9 place-items-center rounded-lg bg-surface-inset"><Icon className="size-4" /></span><span><span className="block font-mono text-2xl font-semibold">{metrics ? metrics[key] : "—"}</span><span className="block text-sm text-muted-foreground">{label}</span></span></button>)}
        <div className="flex min-h-24 items-center gap-3 px-4 sm:col-span-2 xl:col-span-1"><div className="grid size-12 place-items-center rounded-full border-[5px] border-accent font-mono text-xs font-semibold">{metrics ? `${Math.round(metrics.projectHealthPercent)}%` : "—"}</div><div><div className="text-sm font-medium">Project health</div><div className="text-xs text-muted-foreground">Backend snapshot</div></div></div>
      </section>

      <div className="mb-5"><MissionComposer suggestedPrompt={suggestedPrompt} autoFocus={autoFocusComposer} onPromptUsed={() => setSuggestedPrompt(undefined)} /></div>

      <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(290px,0.82fr)]">
        <section className="min-w-0 border bg-card" aria-labelledby="recent-missions-title"><div className="flex min-h-12 items-center justify-between border-b px-4"><div className="flex items-center gap-2"><ListTodo className="size-4 text-muted-foreground" /><h2 id="recent-missions-title" className="text-sm font-semibold">Recent missions</h2>{filter !== "all" && <button onClick={() => setFilter("all")} className="rounded border px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground">Clear filter</button>}</div><Button nativeButton={false} variant="ghost" size="sm" render={<Link href="/missions" />}>View all</Button></div><div className="px-4 pb-2"><MissionList missions={missions.data} loading={missions.isLoading} limit={6} filter={filter} /></div></section>
        <div className="min-w-0 space-y-5"><ConnectedAppsPanel integrations={integrations.data} loading={integrations.isLoading} /><ActivityPanel activity={activity.data} loading={activity.isLoading} /></div>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-3"><ProjectsPanel projects={projects.data} loading={projects.isLoading} /><AgentInsightsPanel missions={missions.data} /><QuickActionsPanel onPick={(prompt) => setSuggestedPrompt(prompt)} /></div>
      {(missions.error || stats.error || projects.error || integrations.error || activity.error) && <div role="alert" className="mt-5 border border-destructive/20 bg-danger-soft p-3 text-sm text-destructive">Some operational data could not be loaded. The available panels remain usable.</div>}
      <p className="sr-only" aria-live="polite">{active ? "A Parallax mission is running." : "No missions are currently running."}</p>
    </div>
  );
}
