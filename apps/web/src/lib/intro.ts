/**
 * Abertura depois do login. A tela de login anuncia onde a logo está; a abertura, montada no
 * layout raiz (que sobrevive à troca de rota), anima a logo a partir dali enquanto o app carrega.
 */
const EVENT = "nexus:intro";

export type IntroOrigin = { x: number; y: number; size: number };

export function startIntro(): void {
  const box = document.querySelector<HTMLElement>("[data-logo]")?.getBoundingClientRect();
  const origin: IntroOrigin = box ? { x: box.left, y: box.top, size: box.width } : { x: 24, y: 24, size: 28 };
  window.dispatchEvent(new CustomEvent<IntroOrigin>(EVENT, { detail: origin }));
}

export function onIntro(listener: (origin: IntroOrigin) => void): () => void {
  const handler = (event: Event) => listener((event as CustomEvent<IntroOrigin>).detail);
  window.addEventListener(EVENT, handler);
  return () => window.removeEventListener(EVENT, handler);
}
