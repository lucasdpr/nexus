import Image from "next/image";

import { cn } from "@/lib/utils";

/** Marca do produto: o "N" da logo seguido do nome. */
export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex w-fit items-center gap-2 font-semibold tracking-[0.18em]", className)}>
      <Image
        src="/brand/icon-192.png"
        alt=""
        width={96}
        height={96}
        priority
        data-logo
        className="size-[1.6em] rounded-[22%] shadow-[0_0_18px_-2px_var(--neon-violet)] ring-1 ring-neon-violet/50"
      />
      NEXUS
    </span>
  );
}
