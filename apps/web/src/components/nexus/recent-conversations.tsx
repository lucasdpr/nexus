"use client";

import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { api, unwrap } from "@/lib/api/client";
import { cn } from "@/lib/utils";

export function RecentConversations() {
  const pathname = usePathname();
  const conversations = useQuery({
    queryKey: ["conversations"],
    queryFn: () => unwrap(api.GET("/api/v1/chat/conversations", { params: { query: { limit: 12 } } })),
  });
  const items = (conversations.data ?? []).filter((conversation) => conversation.title);

  return (
    <div className="mt-6 min-h-0 flex-1 overflow-y-auto px-3">
      <div className="flex items-center justify-between px-2.5">
        <h2 className="text-[12px] text-muted-foreground">Conversas</h2>
        <Link
          href="/perguntar"
          className="grid size-7 place-items-center rounded-md text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
          aria-label="Nova conversa"
        >
          <Plus className="size-4" aria-hidden />
        </Link>
      </div>
      {items.length === 0 ? (
        <p className="px-2.5 py-2 text-[13px] text-muted-foreground">As perguntas que você fizer aparecem aqui.</p>
      ) : (
        <ul className="mt-1 space-y-0.5">
          {items.map((conversation) => {
            const href = `/perguntar/${conversation.id}`;
            return (
              <li key={conversation.id}>
                <Link
                  href={href}
                  aria-current={pathname === href ? "page" : undefined}
                  className={cn(
                    "block truncate rounded-md px-2.5 py-1.5 text-[13px] text-sidebar-foreground/75 hover:bg-sidebar-accent hover:text-sidebar-foreground",
                    pathname === href && "bg-sidebar-accent text-sidebar-foreground",
                  )}
                >
                  {conversation.title}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
