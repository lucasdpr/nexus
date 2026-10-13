import type { Metadata } from "next";

import { UsersAdmin } from "./users-admin";

export const metadata: Metadata = { title: "Usuários" };

export default function UsersPage() {
  return <UsersAdmin />;
}
