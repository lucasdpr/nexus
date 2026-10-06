import { redirect } from "next/navigation";

import { AppShell } from "@/components/nexus/app-shell";
import { getSession } from "@/lib/session";

export default async function AppLayout({ children }: LayoutProps<"/">) {
  const me = await getSession();
  if (!me) redirect("/entrar");
  return <AppShell me={me}>{children}</AppShell>;
}
