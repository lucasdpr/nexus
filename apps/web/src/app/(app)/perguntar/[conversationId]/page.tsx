import type { Metadata } from "next";

import { Chat } from "../chat";

export const metadata: Metadata = { title: "Conversa" };

export default async function ConversationPage({ params }: PageProps<"/perguntar/[conversationId]">) {
  const { conversationId } = await params;
  return <Chat key={conversationId} conversationId={conversationId} />;
}
