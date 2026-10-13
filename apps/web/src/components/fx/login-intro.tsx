"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { onIntro, type IntroOrigin } from "@/lib/intro";

const PARTICLES = 36;
const COLORS = ["#b026ff", "#bf5af2", "#06b6d4", "#6366f1", "#f0abfc"];
/** Tempo mínimo da logo no centro, mesmo que o app carregue antes. */
const MIN_FLIGHT_MS = 950;
/** Se o app demorar demais (API dormindo), a abertura não segura a tela para sempre. */
const MAX_WAIT_MS = 6000;

type Stage = "idle" | "fly" | "dissolve" | "reveal";
type Run = { origin: IntroOrigin; logoSize: number; viewport: { w: number; h: number } };

/**
 * Abertura do app depois do login, em três tempos:
 * 1. a logo sai de onde estava na tela de login e vai, numa mola, até o centro, crescendo
 *    (enquanto isso o painel carrega por trás da cortina);
 * 2. quando o app está pronto, ela se desfaz: desfoca, infla e some, soltando partículas de luz;
 * 3. um buraco circular se abre do centro da cortina e revela o aplicativo.
 * Quem pede "reduzir movimento" entra direto, sem abertura.
 */
export function LoginIntro() {
  const reduce = useReducedMotion();
  const pathname = usePathname();
  const [run, setRun] = useState<Run | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [minElapsed, setMinElapsed] = useState(false);

  useEffect(
    () =>
      onIntro((origin) => {
        if (reduce) return;
        const w = window.innerWidth;
        const h = window.innerHeight;
        // No celular a logo ocupa no máximo 42% da largura.
        setRun({ origin, logoSize: Math.round(Math.min(168, w * 0.42)), viewport: { w, h } });
        setStage("fly");
        setMinElapsed(false);
        setTimeout(() => setMinElapsed(true), MIN_FLIGHT_MS);
        setTimeout(() => setMinElapsed(true), MAX_WAIT_MS);
      }),
    [reduce],
  );

  // Só se desfaz quando a rota já é a do app (o painel montou atrás da cortina). A folga de
  // 150 ms deixa o painel pintar antes, para a montagem não engolir o começo do "desfazer".
  // Temporizador comum (não requestAnimationFrame, que o navegador pausa em aba oculta).
  const appReady = pathname !== "/entrar";
  useEffect(() => {
    if (stage !== "fly" || !minElapsed) return;
    const timer = setTimeout(() => setStage("dissolve"), appReady ? 150 : MAX_WAIT_MS - MIN_FLIGHT_MS);
    return () => clearTimeout(timer);
  }, [stage, minElapsed, appReady]);

  // Os tempos seguintes encadeiam pelo fim de cada animação, não por relógio: assim cada um
  // roda inteiro mesmo num aparelho lento.
  const finish = () => {
    setStage("idle");
    setRun(null);
  };

  // Rede de segurança: se uma animação não terminar (aba em segundo plano), a cortina some.
  // Vale para qualquer tempo: a cortina nunca fica mais que alguns segundos na tela.
  useEffect(() => {
    if (stage === "idle") return;
    const timer = setTimeout(() => {
      setStage("idle");
      setRun(null);
    }, stage === "fly" ? MAX_WAIT_MS + 2000 : 4000);
    return () => clearTimeout(timer);
  }, [stage]);

  if (!run || stage === "idle") return null;

  const { origin, logoSize, viewport } = run;
  // Partida: o centro da logo na tela de login, relativo ao centro da tela.
  const startX = origin.x + origin.size / 2 - viewport.w / 2;
  const startY = origin.y + origin.size / 2 - viewport.h / 2;
  const reach = Math.min(viewport.w, viewport.h) * 0.45;

  return (
    <motion.div
      aria-hidden
      className="pointer-events-none fixed inset-0 z-[100] grid place-items-center overflow-hidden"
      // Cortina com um buraco que cresce do centro: o app aparece por dentro dele.
      initial={{ "--hole": "0%" } as never}
      animate={{ "--hole": stage === "reveal" ? "150%" : "0%" } as never}
      transition={{ duration: 0.85, ease: [0.65, 0, 0.35, 1] }}
      onAnimationComplete={() => stage === "reveal" && finish()}
      style={{
        background: "var(--background)",
        maskImage: "radial-gradient(circle at 50% 50%, transparent var(--hole), #000 calc(var(--hole) + 8%))",
        WebkitMaskImage: "radial-gradient(circle at 50% 50%, transparent var(--hole), #000 calc(var(--hole) + 8%))",
      }}
    >
      {/* A cortina nasce transparente e escurece enquanto a logo decola (sem corte seco). */}
      <motion.div
        className="absolute inset-0 bg-background"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.35 }}
      />

      {/* Halo atrás da logo, que acende quando ela chega ao centro. */}
      <motion.div
        className="absolute rounded-full bg-neon-violet/40 blur-3xl"
        style={{ width: logoSize * 1.8, height: logoSize * 1.8 }}
        initial={{ opacity: 0, scale: 0.4 }}
        animate={stage === "fly" ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 1.8 }}
        transition={{ duration: 0.7, ease: "easeOut" }}
      />

      <motion.div
        className="relative"
        initial={{ x: startX, y: startY, scale: origin.size / logoSize, rotate: 0 }}
        animate={
          stage === "fly"
            ? { x: 0, y: 0, scale: 1, rotate: 360 }
            : { x: 0, y: 0, scale: 1.45, rotate: 360, opacity: 0, filter: "blur(18px)" }
        }
        transition={
          stage === "fly"
            ? { type: "spring", stiffness: 120, damping: 16, mass: 0.9 }
            : { duration: 0.55, ease: "easeIn" }
        }
        onAnimationComplete={() => stage === "dissolve" && setStage("reveal")}
      >
        <Image
          src="/brand/icon-512.png"
          alt=""
          width={logoSize}
          height={logoSize}
          priority
          className="rounded-[22%] shadow-[0_0_60px_-6px_var(--neon-violet)] ring-1 ring-neon-violet/60"
        />
      </motion.div>

      {/* Partículas: a logo "se desfaz" em pontos de luz que voam para fora. */}
      <AnimatePresence>
        {stage !== "fly" &&
          Array.from({ length: PARTICLES }, (_, index) => {
            const angle = (index / PARTICLES) * Math.PI * 2 + (index % 3) * 0.35;
            const distance = reach * (0.45 + ((index * 53) % 100) / 180);
            const size = 4 + (index % 4) * 2;
            const color = COLORS[index % COLORS.length];
            return (
              <motion.span
                key={index}
                className="absolute rounded-full"
                style={{ width: size, height: size, background: color, boxShadow: `0 0 12px ${color}` }}
                initial={{ x: 0, y: 0, opacity: 1, scale: 1 }}
                animate={{ x: Math.cos(angle) * distance, y: Math.sin(angle) * distance, opacity: 0, scale: 0.2 }}
                transition={{ duration: 0.9 + (index % 5) * 0.08, ease: [0.16, 1, 0.3, 1] }}
              />
            );
          })}
      </AnimatePresence>
    </motion.div>
  );
}
