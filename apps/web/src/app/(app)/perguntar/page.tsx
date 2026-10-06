import type { Metadata } from "next";

import { Chat } from "./chat";

export const metadata: Metadata = { title: "Perguntar" };

export default function NewConversationPage() {
  return <Chat />;
}
