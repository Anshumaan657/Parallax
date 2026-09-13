"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CreateMissionInput, Mission } from "@/lib/domain";

export const queryKeys = {
  missions: ["missions"] as const,
  mission: (id: number) => ["missions", id] as const,
  stats: ["dashboard", "stats"] as const,
  activity: ["dashboard", "activity"] as const,
  projects: ["dashboard", "projects"] as const,
  integrations: ["integrations"] as const,
};

const hasActiveMission = (missions?: Mission[]) => missions?.some((mission) => mission.status === "queued" || mission.status === "running") ?? false;

export function useMissions() {
  return useQuery({ queryKey: queryKeys.missions, queryFn: api.getMissions, refetchInterval: (query) => hasActiveMission(query.state.data) ? 4_000 : 30_000 });
}

export function useMission(id: number) {
  return useQuery({ queryKey: queryKeys.mission(id), queryFn: () => api.getMission(id), refetchInterval: (query) => query.state.data?.status === "queued" || query.state.data?.status === "running" ? 2_000 : false });
}

export function useDashboardStats(active: boolean) {
  return useQuery({ queryKey: queryKeys.stats, queryFn: api.getStats, refetchInterval: active ? 4_000 : 30_000 });
}

export function useActivity(active: boolean) {
  return useQuery({ queryKey: queryKeys.activity, queryFn: api.getActivity, refetchInterval: active ? 4_000 : 30_000 });
}

export function useProjects() {
  return useQuery({ queryKey: queryKeys.projects, queryFn: api.getProjects, staleTime: 60_000, refetchInterval: 60_000 });
}

export function useIntegrations() {
  return useQuery({ queryKey: queryKeys.integrations, queryFn: api.getIntegrations, staleTime: 60_000, refetchInterval: 60_000 });
}

export function useCreateMission() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateMissionInput) => api.createMission(input),
    onSuccess: (mission) => {
      queryClient.setQueryData<Mission[]>(queryKeys.missions, (current = []) => [mission, ...current.filter((item) => item.id !== mission.id)]);
      queryClient.setQueryData(queryKeys.mission(mission.id), mission);
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
