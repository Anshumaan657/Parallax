import { checkIntegrationAction } from "@/app/actions/workspace";
import { MutationForm } from "@/components/mutation-form";
import { PageHeader } from "@/components/page-header";
import { getIntegrationCapabilities, getIntegrationHealth, getIntegrations, requireSession } from "@/lib/api/server";
import { canManage, type IntegrationProvider } from "@/lib/api/types";

const providers: IntegrationProvider[] = ["github", "jira", "notion", "slack"];

export default async function IntegrationsPage() {
  const [connections, health, capabilityResults, session] = await Promise.all([getIntegrations(), getIntegrationHealth(), Promise.allSettled(providers.map((provider) => getIntegrationCapabilities(provider))), requireSession()]);
  const manager = canManage(session.current_workspace.role);
  return <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
    <PageHeader eyebrow="Connected systems" title="Integrations" description="Connection state, stored health, execution mode, and contract capabilities." />
    <div className="grid gap-4 lg:grid-cols-2">{providers.map((provider, index) => {
      const connection = connections.find((item) => item.name.toLowerCase() === provider);
      const state = health.find((item) => item.name.toLowerCase() === provider);
      const capabilityResult = capabilityResults[index];
      const capability = capabilityResult.status === "fulfilled" ? capabilityResult.value : null;
      return <article key={provider} className="rounded-xl border bg-card p-5">
        <div className="flex items-start justify-between gap-3"><div><h2 className="font-semibold capitalize">{capability?.name ?? provider}</h2><p className="mt-1 text-sm text-muted-foreground">{connection?.detail ?? state?.detail ?? "No connection detail."}</p></div><span className="rounded-full border px-2 py-1 text-xs capitalize">{state?.status ?? (connection?.connected ? "connected" : "unknown")}</span></div>
        <div className="mt-4 flex flex-wrap gap-2 text-xs"><span className="rounded bg-muted px-2 py-1">{capability?.mode ?? state?.mode ?? "unknown"} mode</span>{state?.last_checked_at && <time className="rounded bg-muted px-2 py-1">Checked {new Date(state.last_checked_at).toLocaleString()}</time>}</div>
        {capability ? <ul className="mt-4 divide-y border-y">{capability.capabilities.map((item) => <li key={item.operation} className="py-3"><div className="flex justify-between gap-3 text-sm"><span>{item.operation}</span><span className="capitalize text-muted-foreground">{item.access}</span></div><p className="mt-1 text-xs text-muted-foreground">{item.description}</p></li>)}</ul> : <p role="status" className="mt-4 rounded-lg border border-dashed p-3 text-sm text-muted-foreground">Capabilities could not be loaded; connection status remains available.</p>}
        {manager && <MutationForm action={checkIntegrationAction.bind(null, provider)} label="Run connection check" variant="outline" className="mt-4" />}
      </article>;
    })}</div>
  </main>;
}
