"use client";

import { useReducedMotion, useSpring, useTransform, motion } from "motion/react";
import { useEffect } from "react";

/** Número que "rola" até o valor novo numa mola, em vez de trocar de repente. */
export function AnimatedNumber({ value, className }: { value: number; className?: string }) {
  const reduce = useReducedMotion();
  const spring = useSpring(reduce ? value : 0, { stiffness: 120, damping: 20 });
  const display = useTransform(spring, (current) => Math.round(current).toLocaleString("pt-BR"));

  useEffect(() => {
    spring.set(value);
  }, [spring, value]);

  return <motion.span className={className}>{display}</motion.span>;
}
