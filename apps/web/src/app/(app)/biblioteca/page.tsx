import type { Metadata } from "next";

import { Library } from "./library";

export const metadata: Metadata = { title: "Biblioteca" };

export default function LibraryPage() {
  return <Library />;
}
