import { MissionDetailClient } from "@/components/mission-detail-client";

export default async function MissionPage(props: PageProps<"/missions/[id]">) {
  const { id } = await props.params;
  return <MissionDetailClient id={Number(id)} />;
}

