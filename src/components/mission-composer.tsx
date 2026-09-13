"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowUp, Sparkles } from "lucide-react";
import { useEffect } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useCreateMission, useProjects } from "@/lib/queries";

const missionFormSchema = z.object({
  prompt: z.string().trim().min(3, "Describe the mission in at least three characters.").max(4_000, "Keep the mission under 4,000 characters."),
  project: z.string().min(1),
});

type MissionForm = z.infer<typeof missionFormSchema>;

const suggestions = [
  "Summarize recent work",
  "Find open pull requests",
  "Update matching Jira issues",
  "Notify the team in Slack",
];

export function MissionComposer({ suggestedPrompt, autoFocus = false, onPromptUsed }: { suggestedPrompt?: string; autoFocus?: boolean; onPromptUsed?: () => void }) {
  const projects = useProjects();
  const createMission = useCreateMission();
  const form = useForm<MissionForm>({ resolver: zodResolver(missionFormSchema), defaultValues: { prompt: "", project: "General" } });
  const selectedProject = useWatch({ control: form.control, name: "project" });

  useEffect(() => {
    if (suggestedPrompt) {
      form.setValue("prompt", suggestedPrompt, { shouldDirty: true });
      onPromptUsed?.();
    }
    if (suggestedPrompt || autoFocus) document.getElementById("mission-prompt")?.focus();
  }, [autoFocus, form, onPromptUsed, suggestedPrompt]);

  const submit = form.handleSubmit(async (input) => {
    await createMission.mutateAsync(input);
    form.reset({ prompt: "", project: input.project });
  });

  return (
    <section id="mission-composer" aria-labelledby="mission-composer-title" className="border border-primary/30 bg-card shadow-[0_12px_36px_-28px_var(--primary)]">
      <div className="flex items-center gap-2 border-b bg-accent/45 px-4 py-3 sm:px-5">
        <Sparkles className="size-4 text-primary" aria-hidden="true" />
        <h2 id="mission-composer-title" className="text-sm font-semibold">Give Parallax a mission</h2>
        <span className="ml-auto text-xs text-muted-foreground">Enter to run · Shift+Enter for a new line</span>
      </div>
      <form onSubmit={submit} className="p-4 sm:p-5">
        <Label htmlFor="mission-prompt" className="sr-only">Mission instructions</Label>
        <Textarea
          id="mission-prompt"
          rows={3}
          placeholder="Review the Payments project, check what shipped, update matching Jira issues, and notify the team in Slack."
          className="min-h-24 resize-none border-0 bg-transparent px-0 text-base leading-7 shadow-none focus-visible:ring-0"
          aria-invalid={Boolean(form.formState.errors.prompt)}
          {...form.register("prompt")}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submit();
            }
          }}
        />
        {form.formState.errors.prompt && <p role="alert" className="mt-1 text-sm text-destructive">{form.formState.errors.prompt.message}</p>}
        {createMission.error && <p role="alert" className="mt-1 text-sm text-destructive">{createMission.error.message}</p>}

        <div className="mt-4 flex flex-col gap-3 border-t pt-4 xl:flex-row xl:items-end xl:justify-between">
          <div className="flex flex-wrap gap-2">
            {suggestions.map((suggestion) => (
              <button key={suggestion} type="button" onClick={() => form.setValue("prompt", suggestion, { shouldDirty: true })} className="min-h-9 rounded-md border bg-background px-3 text-sm text-muted-foreground hover:border-primary/40 hover:text-foreground">
                {suggestion}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 self-end">
            <Label htmlFor="mission-project" className="sr-only">Project</Label>
            <Select value={selectedProject} onValueChange={(value) => form.setValue("project", value ?? "General")}>
              <SelectTrigger id="mission-project" className="h-10 min-w-36 bg-background"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="General">General</SelectItem>
                {projects.data?.map((project) => <SelectItem key={project.name} value={project.name}>{project.name}</SelectItem>)}
              </SelectContent>
            </Select>
            <Button type="submit" size="lg" className="h-10 gap-2 px-4" disabled={createMission.isPending}>
              {createMission.isPending ? "Submitting" : "Run mission"}<ArrowUp className="size-4" aria-hidden="true" />
            </Button>
          </div>
        </div>
      </form>
    </section>
  );
}
