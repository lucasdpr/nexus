"use client";

import { motion, useMotionTemplate, useMotionValue, useReducedMotion, useSpring, useTransform } from "motion/react";
import { useRef } from "react";

import { SPRING_VALUE } from "@/components/fx/motion";
import { cn } from "@/lib/utils";

type Props = React.ComponentProps<typeof motion.div> & {
  /** Inclina o cartão na direção do ponteiro (desligado em listas longas). */
  tilt?: boolean;
  /** Intensidade máxima da inclinação, em graus. */
  maxTilt?: number;
  /** Camada decorativa presa às bordas do cartão (atrás do conteúdo), como a onda da fila. */
  decoration?: React.ReactNode;
};

/**
 * Cartão de vidro fumê com duas reações ao ponteiro:
 * - brilho: um holofote radial que segue o mouse por dentro do vidro;
 * - inclinação 3D: rotateX/rotateY numa mola, para o cartão "pender" para o cursor.
 */
export function GlassCard({
  tilt = true,
  maxTilt = 6,
  decoration,
  className,
  children,
  style,
  ...props
}: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  // Posição do ponteiro de 0 a 1 dentro do cartão; 0,5 é o centro (repouso).
  const px = useMotionValue(0.5);
  const py = useMotionValue(0.5);
  const rotateX = useSpring(useTransform(py, [0, 1], [maxTilt, -maxTilt]), SPRING_VALUE);
  const rotateY = useSpring(useTransform(px, [0, 1], [-maxTilt, maxTilt]), SPRING_VALUE);
  const glowX = useTransform(px, (value) => `${value * 100}%`);
  const glowY = useTransform(py, (value) => `${value * 100}%`);
  const glow = useMotionTemplate`radial-gradient(420px circle at ${glowX} ${glowY}, rgb(176 38 255 / 0.16), transparent 60%)`;
  const tilting = tilt && !reduce;

  return (
    <motion.div
      ref={ref}
      onPointerMove={(event) => {
        const box = ref.current?.getBoundingClientRect();
        if (!box) return;
        px.set((event.clientX - box.left) / box.width);
        py.set((event.clientY - box.top) / box.height);
      }}
      onPointerLeave={() => {
        px.set(0.5);
        py.set(0.5);
      }}
      style={{ ...(tilting ? { rotateX, rotateY, transformPerspective: 900 } : {}), ...style }}
      className={cn(
        "group/glass glass relative overflow-hidden rounded-xl transition-colors hover:border-neon-indigo/50",
        className,
      )}
      {...props}
    >
      {/* Holofote que acompanha o ponteiro: só aparece com o mouse em cima. */}
      <motion.div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover/glass:opacity-100"
        style={{ background: glow }}
      />
      {decoration}
      <div className="relative">{children as React.ReactNode}</div>
    </motion.div>
  );
}
