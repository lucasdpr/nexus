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
        className="size-[1.6em] rounded-[22%]"
      />
      NEXUS
    </span>
  );
}
