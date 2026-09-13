"use client";

import Link from "next/link";
import { useActionState } from "react";

import { loginAction, registerAction, type AuthActionState } from "@/app/actions/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const initialState: AuthActionState = {};

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const action = mode === "login" ? loginAction : registerAction;
  const [state, formAction, pending] = useActionState(action, initialState);
  const register = mode === "register";

  return (
    <form action={formAction} className="space-y-4">
      {register ? (
        <>
          <Field label="Display name" name="display_name" defaultValue={state.fields?.display_name} autoComplete="name" />
          <Field label="Workspace name" name="workspace_name" defaultValue={state.fields?.workspace_name} autoComplete="organization" />
          <Field label="Workspace slug" name="workspace_slug" defaultValue={state.fields?.workspace_slug} pattern="[a-z0-9]+(?:-[a-z0-9]+)*" />
        </>
      ) : null}
      <Field label="Email" name="email" type="email" defaultValue={state.fields?.email} autoComplete="email" />
      <Field label="Password" name="password" type="password" minLength={register ? 12 : 1} autoComplete={register ? "new-password" : "current-password"} />
      {!register ? <Field label="Workspace ID (optional)" name="workspace_id" defaultValue={state.fields?.workspace_id} /> : null}
      {state.error ? (
        <div role="alert" className="rounded-lg border border-destructive/25 bg-danger-soft p-3 text-sm text-destructive">
          {state.error}{state.correlationId ? <span className="mt-1 block font-mono text-xs">Reference {state.correlationId}</span> : null}
        </div>
      ) : null}
      <Button className="h-11 w-full" type="submit" disabled={pending}>{pending ? "Submitting…" : register ? "Create workspace" : "Sign in"}</Button>
      <p className="text-center text-sm text-muted-foreground">
        {register ? "Already have an account? " : "Need a workspace? "}
        <Link className="font-medium text-primary hover:underline" href={register ? "/login" : "/register"}>{register ? "Sign in" : "Register"}</Link>
      </p>
    </form>
  );
}

function Field({ label, name, ...props }: React.ComponentProps<typeof Input> & { label: string; name: string }) {
  return <div className="space-y-2"><Label htmlFor={name}>{label}</Label><Input id={name} name={name} required={name !== "workspace_id"} {...props} /></div>;
}
