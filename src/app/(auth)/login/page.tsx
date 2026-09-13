import { AuthForm } from "@/components/auth-form";

export default function LoginPage() {
  return <section className="w-full max-w-md rounded-2xl border bg-card p-6 shadow-sm sm:p-8"><div className="mb-7"><div className="mb-5 grid size-10 place-items-center rounded-xl bg-primary font-mono font-semibold text-primary-foreground">P</div><h1 className="text-2xl font-semibold">Sign in to Parallax</h1><p className="mt-2 text-sm text-muted-foreground">Use your workspace account to continue.</p></div><AuthForm mode="login" /></section>;
}
