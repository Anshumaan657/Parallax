"use server";
import { revalidatePath } from "next/cache";
import { checkIntegration, registerGitHubRepository, revokeGitHubToken, updateMemberRole } from "@/lib/api/server";
import type { IntegrationProvider, WorkspaceRole } from "@/lib/api/types";
import { ApiError } from "@/lib/api/errors";
import type { MutationState } from "@/app/actions/missions";

const failure = (error: unknown): MutationState => error instanceof ApiError ? { error: error.message, correlationId: error.correlationId } : { error: "The request could not be completed." };

export async function checkIntegrationAction(provider: IntegrationProvider, state: MutationState, formData: FormData): Promise<MutationState> { void state; void formData; try { await checkIntegration(provider); } catch (error) { return failure(error); } revalidatePath("/integrations"); return {}; }
export async function registerGitHubRepositoryAction(state: MutationState, formData: FormData): Promise<MutationState> {
  try {
    const fullName = String(formData.get("full_name") ?? "").trim();
    const defaultBranch = String(formData.get("default_branch") ?? "main").trim() || "main";
    if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(fullName)) return { error: "Enter a repository as owner/name." };
    await registerGitHubRepository({ full_name: fullName, default_branch: defaultBranch });
  } catch (error) { return failure(error); }
  revalidatePath("/integrations");
  return {};
}
export async function revokeGitHubTokenAction(state: MutationState, formData: FormData): Promise<MutationState> {
  void state; void formData;
  try { await revokeGitHubToken(); } catch (error) { return failure(error); }
  revalidatePath("/integrations");
  return {};
}
export async function updateRoleAction(userId: string, _: MutationState, formData: FormData): Promise<MutationState> { const role = String(formData.get("role")) as WorkspaceRole; if (!["owner", "admin", "manager", "reviewer", "viewer"].includes(role)) return { error: "Select a valid workspace role." }; try { await updateMemberRole(userId, role); } catch (error) { return failure(error); } revalidatePath("/team"); return {}; }
