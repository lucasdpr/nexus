import type { Transition } from "motion/react";

/** Mola padrão de toda interação do NEXUS: firme, com um leve assentamento no fim. */
export const SPRING: Transition = { type: "spring", stiffness: 350, damping: 25 };

/** Mola mais solta, para o "assentar" de uma gota (indicadores que trocam de lugar). */
export const LIQUID: Transition = { type: "spring", stiffness: 420, damping: 30, mass: 0.9 };

/** Os mesmos números da mola para `useSpring` (valores que seguem o ponteiro). */
export const SPRING_VALUE = { stiffness: 350, damping: 25 };
