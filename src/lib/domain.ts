import { z } from "zod";

export const missionStatusSchema = z.enum([
  "queued",
  "running",
  "completed",
  "blocked",
  "failed",
]);

const apiMissionStepSchema = z.object({
  step: z.number().int().nonnegative(),
  tool: z.string(),
  input: z.record(z.string(), z.unknown()).default({}),
  output: z.string(),
  at: z.string(),
});

const apiMissionSchema = z.object({
  id: z.number().int(),
  prompt: z.string(),
  project: z.string(),
  status: missionStatusSchema,
  progress_current: z.number().int().nonnegative(),
  progress_total: z.number().int().positive(),
  result_summary: z.string().nullable().optional(),
  steps: z.array(apiMissionStepSchema).default([]),
  created_at: z.string(),
  updated_at: z.string(),
});

export const apiMissionListSchema = z.array(apiMissionSchema);

export const apiStatsSchema = z.object({
  active_tasks: z.number().int().nonnegative(),
  completed_this_week: z.number().int().nonnegative(),
  blocked: z.number().int().nonnegative(),
  awaiting_approval: z.number().int().nonnegative(),
  project_health_pct: z.number().min(0).max(100),
});

export const apiActivityListSchema = z.array(
  z.object({
    id: z.number().int(),
    icon: z.string(),
    title: z.string(),
    detail: z.string().default(""),
    created_at: z.string(),
  }),
);

export const apiProjectListSchema = z.array(
  z.object({
    name: z.string(),
    icon: z.string(),
    health_pct: z.number().min(0).max(100),
  }),
);

export const apiIntegrationListSchema = z.array(
  z.object({
    name: z.string(),
    connected: z.boolean(),
    detail: z.string().default(""),
  }),
);

export type MissionStatus = z.infer<typeof missionStatusSchema>;

export interface MissionStep {
  step: number;
  tool: string;
  input: Record<string, unknown>;
  output: string;
  at: string;
}

export interface Mission {
  id: number;
  prompt: string;
  project: string;
  status: MissionStatus;
  progressCurrent: number;
  progressTotal: number;
  resultSummary?: string;
  steps: MissionStep[];
  createdAt: string;
  updatedAt: string;
}

export interface DashboardStats {
  active: number;
  completedThisWeek: number;
  blockedOrFailed: number;
  queued: number;
  projectHealthPercent: number;
}

export interface ActivityItem {
  id: number;
  icon: string;
  title: string;
  detail: string;
  createdAt: string;
}

export interface Project {
  name: string;
  icon: string;
  healthPercent: number;
}

export interface Integration {
  name: string;
  connected: boolean;
  detail: string;
}

export interface CreateMissionInput {
  prompt: string;
  project: string;
}

export const featureCapabilities = {
  approvals: false,
  contextPacks: false,
  riskReview: false,
  realtime: false,
} as const;

export function normalizeDate(value: string): string {
  return /(?:Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`;
}

export function normalizeMission(raw: z.infer<typeof apiMissionSchema>): Mission {
  return {
    id: raw.id,
    prompt: raw.prompt,
    project: raw.project,
    status: raw.status,
    progressCurrent: raw.progress_current,
    progressTotal: raw.progress_total,
    resultSummary: raw.result_summary ?? undefined,
    steps: raw.steps.map((step) => ({ ...step, at: normalizeDate(step.at) })),
    createdAt: normalizeDate(raw.created_at),
    updatedAt: normalizeDate(raw.updated_at),
  };
}

