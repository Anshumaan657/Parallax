import { DashboardClient } from "@/components/dashboard-client";

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ prompt?: string; compose?: string }>;
}) {
  const { prompt, compose } = await searchParams;
  return <DashboardClient initialPrompt={prompt} autoFocusComposer={compose === "1"} />;
}
