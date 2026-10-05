import type { NextConfig } from "next";

// Lido no build: em imagens Docker o valor fica gravado no server.js gerado.
const apiUrl = process.env.API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  // O navegador fala só com o Next; /api/* é repassado ao FastAPI no mesmo domínio,
  // o que mantém o cookie de sessão first-party mesmo com a API hospedada em outro lugar.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiUrl}/api/:path*` }];
  },
};

export default nextConfig;
