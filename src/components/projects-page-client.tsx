"use client";

import { Cpu, Layers3, Smartphone, WalletCards } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { useProjects } from "@/lib/queries";

const icons = { wallet: WalletCards, layers: Layers3, cpu: Cpu, smartphone: Smartphone };

export function ProjectsPageClient() {
  const projects = useProjects();
  return <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8"><PageHeader eyebrow="Portfolio" title="Projects" description="Health values are supplied by the current backend snapshot." /><div className="grid gap-4 sm:grid-cols-2">{projects.isLoading ? Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-40" />) : projects.data?.map((project) => { const Icon = icons[project.icon as keyof typeof icons] ?? Layers3; return <article key={project.name} className="border bg-card p-5"><div className="flex items-center justify-between"><span className="grid size-10 place-items-center rounded-lg bg-surface-inset"><Icon className="size-5" /></span><span className="font-mono text-sm text-muted-foreground">{project.healthPercent}%</span></div><h2 className="mt-6 text-lg font-semibold">{project.name}</h2><div className="mt-3 h-2 overflow-hidden rounded-full bg-muted"><div className={`h-full rounded-full ${project.healthPercent >= 70 ? "bg-success" : project.healthPercent >= 50 ? "bg-warning" : "bg-destructive"}`} style={{ width: `${project.healthPercent}%` }} /></div></article>; })}</div></div>;
}

