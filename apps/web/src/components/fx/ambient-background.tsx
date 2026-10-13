/**
 * Luz ambiente: três manchas de cor desfocadas que derivam devagar atrás do conteúdo.
 * Só CSS (transform + border-radius), para não custar JavaScript a cada quadro; com
 * "reduzir movimento" ligado elas ficam paradas.
 */
export function AmbientBackground() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="animate-blob absolute -top-[18vh] -left-[12vw] size-[55vmax] bg-neon-violet/35 blur-3xl" />
      <div
        className="animate-blob absolute top-[30vh] -right-[18vw] size-[48vmax] bg-neon-cyan/20 blur-3xl"
        style={{ animationDelay: "-7s", animationDuration: "26s" }}
      />
      <div
        className="animate-blob absolute -bottom-[25vh] left-[20vw] size-[42vmax] bg-neon-indigo/25 blur-3xl"
        style={{ animationDelay: "-14s", animationDuration: "30s" }}
      />
      {/* Vinheta leve nas bordas: o centro fica livre para a luz aparecer. */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_40%,rgb(9_9_11/0.7)_100%)]" />
    </div>
  );
}
