import {
  apiActivityListSchema,
  apiIntegrationListSchema,
  apiMissionListSchema,
  apiProjectListSchema,
  apiStatsSchema,
  normalizeDate,
  normalizeMission,
  type ActivityItem,
  type CreateMissionInput,
  type DashboardStats,
  type Integration,
  type Mission,
  type Project,
} from "@/lib/domain";
import { mockApi } from "@/lib/mock-data";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const isMockMode = process.env.NEXT_PUBLIC_MOCK_MODE !== "false";

export class ApiError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function request(path: string, options?: RequestInit): Promise<unknown> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {}
    throw new ApiError(message, response.status);
  }
  return response.json();
}

const liveApi = {
  async getMissions(): Promise<Mission[]> {
    return apiMissionListSchema.parse(await request("/api/missions")).map(normalizeMission);
  },
  async getMission(id: number): Promise<Mission> {
    return normalizeMission(apiMissionListSchema.element.parse(await request(`/api/missions/${id}`)));
  },
  async createMission(input: CreateMissionInput): Promise<Mission> {
    return normalizeMission(apiMissionListSchema.element.parse(await request("/api/missions", { method: "POST", body: JSON.stringify(input) })));
  },
  async getStats(): Promise<DashboardStats> {
    const raw = apiStatsSchema.parse(await request("/api/dashboard/stats"));
    return { active: raw.active_tasks, completedThisWeek: raw.completed_this_week, blockedOrFailed: raw.blocked, queued: raw.awaiting_approval, projectHealthPercent: raw.project_health_pct };
  },
  async getActivity(): Promise<ActivityItem[]> {
    return apiActivityListSchema.parse(await request("/api/dashboard/activity")).map((item) => ({ id: item.id, icon: item.icon, title: item.title, detail: item.detail, createdAt: normalizeDate(item.created_at) }));
  },
  async getProjects(): Promise<Project[]> {
    return apiProjectListSchema.parse(await request("/api/dashboard/projects")).map((item) => ({ name: item.name, icon: item.icon, healthPercent: item.health_pct }));
  },
  async getIntegrations(): Promise<Integration[]> {
    return apiIntegrationListSchema.parse(await request("/api/integrations"));
  },
};

export const api = isMockMode ? mockApi : liveApi;

