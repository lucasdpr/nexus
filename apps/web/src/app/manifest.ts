import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "NEXUS",
    short_name: "NEXUS",
    description: "Pergunte aos documentos da sua empresa e veja o documento e a página de cada resposta.",
    lang: "pt-BR",
    start_url: "/perguntar",
    scope: "/",
    display: "standalone",
    background_color: "#130820",
    theme_color: "#130820",
    icons: [
      { src: "/brand/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/brand/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/brand/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
