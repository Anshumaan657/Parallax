import { AppShell } from "@/components/app-shell";
import { SessionRefresher } from "@/components/session-refresher";
import { getReady, requireSession } from "@/lib/api/server";

export default async function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const [session, readiness] = await Promise.all([requireSession(), getReady().catch(() => null)]);
  return <AppShell session={session} readiness={readiness}><SessionRefresher expiresAt={session.expiresAt} />{children}</AppShell>;
}
