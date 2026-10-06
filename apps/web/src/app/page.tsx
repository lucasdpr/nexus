import { redirect } from "next/navigation";

import { getSession } from "@/lib/session";

// Provisório: a landing page pública entra na Fase 8.
export default async function Home() {
  redirect((await getSession()) ? "/perguntar" : "/entrar");
}
