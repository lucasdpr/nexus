"use client";

import { createContext, useContext } from "react";

import type { Me } from "@/lib/api/client";

const MeContext = createContext<Me | null>(null);

export const MeProvider = MeContext.Provider;

/** Usuário logado (validado no servidor pelo layout da área logada). */
export function useMe(): Me {
  const me = useContext(MeContext);
  if (!me) throw new Error("useMe precisa estar dentro da área logada.");
  return me;
}

/** Só a interface usa isto, para não mostrar ações que a API recusaria. */
export function canManageDocuments(me: Me): boolean {
  return me.user.role !== "MEMBER";
}
