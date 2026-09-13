import type {
  ActivityItem,
  CreateMissionInput,
  DashboardStats,
  Integration,
  Mission,
  MissionStep,
  Project,
} from "@/lib/domain";

const now = Date.now();
const isoAgo = (minutes: number) => new Date(now - minutes * 60_000).toISOString();

let nextMissionId = 105;
const startedAt = new Map<number, number>();

let missions: Mission[] = [
  {
    id: 104,
    prompt: "Check recently merged Payments pull requests and summarize what shipped.",
    project: "Payments",
    status: "completed",
    progressCurrent: 3,
    progressTotal: 10,
    resultSummary: "Reviewed the latest merged pull requests and prepared a concise Payments release summary.",
    steps: [
      { step: 1, tool: "list_recent_merged_prs", input: { repo: "acme/payments" }, output: "Found 4 recently merged pull requests.", at: isoAgo(18) },
      { step: 2, tool: "get_pull_request_status", input: { repo: "acme/payments", pr_number: 482 }, output: "PR #482 is merged with all checks complete.", at: isoAgo(17) },
      { step: 3, tool: "create_notion_note", input: { title: "Payments release summary" }, output: "Created the requested release note.", at: isoAgo(16) },
    ],
    createdAt: isoAgo(21),
    updatedAt: isoAgo(16),
  },
  {
    id: 103,
    prompt: "Find open Core pull requests that still need attention.",
    project: "Core",
    status: "completed",
    progressCurrent: 1,
    progressTotal: 10,
    resultSummary: "Found two open pull requests. One is ready for review and one remains a draft.",
    steps: [{ step: 1, tool: "list_open_pull_requests", input: { repo: "acme/core" }, output: "#91 ready for review; #94 remains a draft.", at: isoAgo(72) }],
    createdAt: isoAgo(74),
    updatedAt: isoAgo(72),
  },
  {
    id: 102,
    prompt: "Post the weekly platform update to the engineering channel.",
    project: "Platform",
    status: "failed",
    progressCurrent: 1,
    progressTotal: 10,
    resultSummary: "Slack rejected the configured channel. Confirm the channel ID and try again.",
    steps: [{ step: 1, tool: "post_slack_message", input: { channel: "#engineering" }, output: "Slack API returned channel_not_found.", at: isoAgo(135) }],
    createdAt: isoAgo(138),
    updatedAt: isoAgo(135),
  },
];

const projects: Project[] = [
  { name: "Payments", icon: "wallet", healthPercent: 78 },
  { name: "Platform", icon: "layers", healthPercent: 64 },
  { name: "Core", icon: "cpu", healthPercent: 91 },
  { name: "Mobile", icon: "smartphone", healthPercent: 47 },
];

const integrations: Integration[] = [
  { name: "GitHub", connected: true, detail: "acme/platform" },
  { name: "Jira", connected: true, detail: "ACME" },
  { name: "Notion", connected: false, detail: "Token required" },
  { name: "Slack", connected: true, detail: "#engineering" },
];

const pause = () => new Promise((resolve) => setTimeout(resolve, 180));

function refreshCreatedMissions() {
  const current = Date.now();
  missions = missions.map((mission) => {
    const start = startedAt.get(mission.id);
    if (!start) return mission;
    const elapsed = current - start;
    if (elapsed < 1_400) return mission;

    const steps: MissionStep[] = [
      { step: 1, tool: "list_open_pull_requests", input: { repo: "acme/payments" }, output: "Found 3 open pull requests.", at: new Date(start + 1_400).toISOString() },
      ...(elapsed > 3_500 ? [{ step: 2, tool: "search_issues", input: { project: mission.project }, output: "Matched 2 Jira issues to completed work.", at: new Date(start + 3_500).toISOString() }] : []),
      ...(elapsed > 5_500 ? [{ step: 3, tool: "post_slack_message", input: { channel: "#payments" }, output: "Posted the requested status update.", at: new Date(start + 5_500).toISOString() }] : []),
    ];

    if (elapsed > 7_000) {
      startedAt.delete(mission.id);
      return {
        ...mission,
        status: "completed" as const,
        progressCurrent: steps.length,
        steps,
        resultSummary: "Reviewed the project, matched completed engineering work to Jira, and posted the requested team update.",
        updatedAt: new Date(start + 7_000).toISOString(),
      };
    }

    return { ...mission, status: "running" as const, progressCurrent: steps.length, steps, updatedAt: new Date().toISOString() };
  });
}

export const mockApi = {
  async getMissions(): Promise<Mission[]> {
    await pause();
    refreshCreatedMissions();
    return [...missions];
  },
  async getMission(id: number): Promise<Mission> {
    await pause();
    refreshCreatedMissions();
    const mission = missions.find((item) => item.id === id);
    if (!mission) throw new Error("Mission not found");
    return mission;
  },
  async createMission(input: CreateMissionInput): Promise<Mission> {
    await pause();
    const createdAt = new Date().toISOString();
    const mission: Mission = {
      id: nextMissionId++,
      prompt: input.prompt,
      project: input.project,
      status: "queued",
      progressCurrent: 0,
      progressTotal: 10,
      steps: [],
      createdAt,
      updatedAt: createdAt,
    };
    startedAt.set(mission.id, Date.now());
    missions = [mission, ...missions];
    return mission;
  },
  async getStats(): Promise<DashboardStats> {
    await pause();
    refreshCreatedMissions();
    return {
      active: missions.filter((m) => m.status === "queued" || m.status === "running").length,
      completedThisWeek: missions.filter((m) => m.status === "completed").length,
      blockedOrFailed: missions.filter((m) => m.status === "blocked" || m.status === "failed").length,
      queued: missions.filter((m) => m.status === "queued").length,
      projectHealthPercent: Math.round(projects.reduce((sum, project) => sum + project.healthPercent, 0) / projects.length),
    };
  },
  async getProjects() { await pause(); return projects; },
  async getIntegrations() { await pause(); return integrations; },
  async getActivity(): Promise<ActivityItem[]> {
    await pause();
    refreshCreatedMissions();
    return missions.flatMap((mission) => mission.steps.map((step) => ({ id: mission.id * 100 + step.step, icon: step.tool, title: step.tool.replaceAll("_", " "), detail: step.output, createdAt: step.at }))).sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt)).slice(0, 8);
  },
};

export { projects as mockProjects };

