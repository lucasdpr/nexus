import type { Metadata } from "next";

import { AuditLog } from "./audit-log";

export const metadata: Metadata = { title: "Auditoria" };

export default function AuditPage() {
  return <AuditLog />;
}
