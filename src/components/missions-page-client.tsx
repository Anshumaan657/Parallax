"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MissionList } from "@/components/mission-list";
import { PageHeader } from "@/components/page-header";
import type { MissionStatus } from "@/lib/domain";
import { useMissions } from "@/lib/queries";
import { useState } from "react";

export function MissionsPageClient() {
  const missions = useMissions();
  const [filter, setFilter] = useState<MissionStatus | "all">("all");
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <PageHeader eyebrow="Work history" title="Missions" description="Every request, tool call, outcome, and recoverable failure in one place." action={<Button nativeButton={false} render={<Link href="/dashboard?compose=1" />} className="gap-2"><Plus className="size-4" />New mission</Button>} />
      <section className="border bg-card">
        <div className="border-b p-3">
          <Tabs value={filter} onValueChange={(value) => setFilter(value as MissionStatus | "all")}>
            <TabsList className="h-auto flex-wrap justify-start"><TabsTrigger value="all">All</TabsTrigger><TabsTrigger value="running">Running</TabsTrigger><TabsTrigger value="queued">Queued</TabsTrigger><TabsTrigger value="completed">Completed</TabsTrigger><TabsTrigger value="failed">Failed</TabsTrigger></TabsList>
          </Tabs>
        </div>
        <div className="px-4 pb-2"><MissionList missions={missions.data} loading={missions.isLoading} filter={filter} /></div>
      </section>
      {missions.error && <p role="alert" className="mt-4 border border-destructive/20 bg-danger-soft p-3 text-sm text-destructive">Missions could not be loaded. Check the backend connection and retry.</p>}
    </div>
  );
}
