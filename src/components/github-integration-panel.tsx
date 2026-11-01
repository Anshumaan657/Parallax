import { GitBranch, GitPullRequest, KeyRound, Plus, ShieldCheck } from "lucide-react";

import {
  registerGitHubRepositoryAction,
  revokeGitHubTokenAction,
} from "@/app/actions/workspace";
import { MutationForm } from "@/components/mutation-form";
import { StreamResource } from "@/components/stream-resource";
import { Input } from "@/components/ui/input";
import { canManage, type GitHubRepository, type Integration, type IntegrationHealth, type MeResponse } from "@/lib/api/types";

export function GitHubIntegrationPanel({
  connections,
  repositories,
  health,
  session,
}: {
  connections: Promise<Integration[]>;
  repositories: Promise<GitHubRepository[]>;
  health: Promise<IntegrationHealth[]>;
  session: Promise<MeResponse>;
}) {
  return (
    <article className="overflow-hidden rounded-xl border bg-card lg:col-span-2">
      <header className="flex flex-col gap-4 border-b p-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="grid size-10 place-items-center rounded-lg bg-accent text-accent-foreground">
            <GitBranch className="size-5" aria-hidden="true" />
          </span>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-semibold">GitHub</h2>
              <span className="rounded-md bg-info-soft px-2 py-1 text-xs text-info">PR workflow</span>
            </div>
            <p className="mt-1 max-w-xl text-xs text-muted-foreground">
              Receive pull-request events, collect evidence, and publish approved review outcomes.
            </p>
          </div>
        </div>
        <StreamResource promise={connections} label="GitHub connection">
          {(items) => {
            const github = items.find((item) => item.name === "GitHub");
            return (
              <span className={github?.connected ? "rounded-md bg-success-soft px-2 py-1 text-xs text-success" : "rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground"}>
                {github?.connected ? "Connected" : "Disconnected"}
              </span>
            );
          }}
        </StreamResource>
      </header>

      <div className="grid gap-6 p-5 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-5">
          <div>
            <div className="mb-3 flex items-center gap-2">
              <GitPullRequest className="size-4 text-muted-foreground" aria-hidden="true" />
              <h3 className="font-medium">Registered repositories</h3>
            </div>
            <StreamResource promise={repositories} label="Registered repositories">
              {(items) => items.length ? (
                <ul className="divide-y rounded-lg border">
                  {items.map((repository) => (
                    <li key={repository.id} className="flex items-center justify-between gap-4 px-3 py-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{repository.full_name}</p>
                        <p className="mt-1 text-xs text-muted-foreground">Project webhook target · {repository.default_branch}</p>
                      </div>
                      <span className="shrink-0 rounded-md bg-success-soft px-2 py-1 text-xs text-success">Active</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="rounded-lg border border-dashed px-4 py-5 text-sm text-muted-foreground">
                  No repositories are registered yet.
                </div>
              )}
            </StreamResource>
          </div>

          <div className="rounded-lg bg-muted/60 p-4">
            <div className="flex items-start gap-3">
              <ShieldCheck className="mt-0.5 size-4 text-success" aria-hidden="true" />
              <p className="text-xs leading-5 text-muted-foreground">
                Webhooks are verified with a signature, duplicate deliveries are ignored, and GitHub writes require an approved Parallax action.
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-5 rounded-lg border bg-background p-4">
          <div>
            <div className="flex items-center gap-2">
              <Plus className="size-4 text-muted-foreground" aria-hidden="true" />
              <h3 className="font-medium">Register a repository</h3>
            </div>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">Use the owner/name format from GitHub. New pull requests will route to the General project.</p>
          </div>
          <MutationForm action={registerGitHubRepositoryAction} label="Register repository" pendingLabel="Registering…" variant="default">
            <label className="mb-3 block text-xs font-medium" htmlFor="github-full-name">
              Repository
              <Input id="github-full-name" name="full_name" className="mt-1.5" placeholder="acme/payments" required />
            </label>
            <label className="mb-4 block text-xs font-medium" htmlFor="github-default-branch">
              Default branch
              <Input id="github-default-branch" name="default_branch" className="mt-1.5" defaultValue="main" required />
            </label>
          </MutationForm>
          <StreamResource promise={session} label="GitHub controls">
            {(identity) => canManage(identity.current_workspace.role) ? (
              <div className="border-t pt-4">
                <MutationForm action={revokeGitHubTokenAction} label="Revoke GitHub token" pendingLabel="Revoking…" variant="destructive" />
              </div>
            ) : null}
          </StreamResource>
          <StreamResource promise={health} label="GitHub health">
            {(items) => {
              const item = items.find((entry) => entry.name === "GitHub");
              return <p className="flex items-center gap-2 text-xs text-muted-foreground"><KeyRound className="size-3.5" aria-hidden="true" />{item?.detail ?? "No health check has been run."}</p>;
            }}
          </StreamResource>
        </div>
      </div>
    </article>
  );
}
