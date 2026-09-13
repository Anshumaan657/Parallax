import { updateRoleAction } from "@/app/actions/workspace";
import { MutationForm } from "@/components/mutation-form";
import { PageHeader } from "@/components/page-header";
import { getMembers, requireSession } from "@/lib/api/server";
import type { WorkspaceRole } from "@/lib/api/types";

const roles: WorkspaceRole[] = ["owner", "admin", "manager", "reviewer", "viewer"];

export default async function TeamPage() {
  const [members, session] = await Promise.all([getMembers(), requireSession()]);
  const manager = session.current_workspace.role === "owner" || session.current_workspace.role === "admin";
  return <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
    <PageHeader eyebrow="Workspace access" title="Team" description="Members and roles from the current workspace." />
    <div className="overflow-x-auto rounded-xl border bg-card"><table className="w-full text-left text-sm"><thead className="border-b bg-muted/40"><tr><th className="p-4">Member</th><th className="p-4">Role</th><th className="p-4">Action</th></tr></thead><tbody className="divide-y">{members.map((member) => <tr key={member.user_id}><td className="p-4"><div className="font-medium">{member.display_name}</div><div className="text-xs text-muted-foreground">{member.email}</div></td><td className="p-4 capitalize">{member.role}</td><td className="p-4">{manager ? <MutationForm action={updateRoleAction.bind(null, member.user_id)} label="Update role" variant="outline"><select name="role" defaultValue={member.role} className="mb-2 min-h-9 rounded-lg border bg-background px-2">{roles.map((role) => <option key={role}>{role}</option>)}</select></MutationForm> : <span className="text-muted-foreground">Read only</span>}</td></tr>)}</tbody></table></div>
  </main>;
}
