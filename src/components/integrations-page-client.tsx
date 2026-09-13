"use client";

import { CheckCircle2, CircleAlert, ExternalLink, PlugZap } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { Integration } from "@/lib/domain";
import { useIntegrations } from "@/lib/queries";

function IntegrationCard({ integration }: { integration: Integration }) {
  return (
    <Card className="h-full min-w-0 overflow-hidden">
      <CardHeader className="gap-4">
        <div className="flex items-start justify-between gap-4">
          <div className="grid size-11 shrink-0 place-items-center rounded-xl border bg-muted text-primary">
            <PlugZap className="size-5" aria-hidden="true" />
          </div>
          <Badge variant={integration.connected ? "secondary" : "outline"}>
            {integration.connected ? (
              <CheckCircle2 className="size-3.5" aria-hidden="true" />
            ) : (
              <CircleAlert className="size-3.5" aria-hidden="true" />
            )}
            {integration.connected ? "Connected" : "Not connected"}
          </Badge>
        </div>
        <div className="min-w-0">
          <CardTitle>{integration.name}</CardTitle>
          <CardDescription className="mt-1 break-words">
            {integration.detail || "Available to mission workflows."}
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-4">
        <div className="flex-1 rounded-xl border bg-muted/45 p-3 text-sm text-muted-foreground">
          {integration.connected
            ? "Parallax can use this connection within the permissions already granted."
            : "Connect this service before selecting it in a live mission."}
        </div>
        <Button variant="outline" className="w-full" disabled>
          Manage connection
          <ExternalLink className="size-4" aria-hidden="true" />
        </Button>
        <p className="text-xs text-muted-foreground">
          Connection management is reserved for the next backend milestone.
        </p>
      </CardContent>
    </Card>
  );
}

export function IntegrationsPageClient() {
  const integrations = useIntegrations();

  return (
    <div className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <PageHeader
        eyebrow="Connected systems"
        title="Integrations"
        description="See which work systems Parallax can inspect or update while a mission runs."
      />

      {integrations.error ? (
        <div className="mb-6 rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          We could not load integrations. Check the API connection and try again.
        </div>
      ) : null}

      <div className="grid items-stretch gap-4 md:grid-cols-2 xl:grid-cols-3">
        {integrations.isLoading
          ? Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-52 rounded-2xl" />
            ))
          : integrations.data?.map((integration) => (
              <IntegrationCard key={integration.name} integration={integration} />
            ))}
      </div>
    </div>
  );
}
