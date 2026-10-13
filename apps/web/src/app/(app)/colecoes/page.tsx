import type { Metadata } from "next";

import { CollectionsAdmin } from "./collections-admin";

export const metadata: Metadata = { title: "Coleções" };

export default function CollectionsPage() {
  return <CollectionsAdmin />;
}
