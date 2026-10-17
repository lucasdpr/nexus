import { expect, test } from "@playwright/test";

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? "admin@novaforja.example.com";
const ADMIN_PASSWORD = process.env.SEED_ADMIN_PASSWORD;

test("envia um documento, espera o processamento e pergunta com fonte citada", async ({ page }) => {
  if (!ADMIN_PASSWORD) throw new Error("Defina SEED_ADMIN_PASSWORD com a senha do administrador da demonstração.");

  // Código único por execução: o documento é achado só por ele, e o teste não depende dos
  // documentos de demonstração nem de execuções anteriores.
  const model = `zx${Date.now().toString(36)}`;
  const title = `manual-${model}`;
  const sourceLink = () => page.locator('aside[aria-label="Fontes da resposta"]').getByRole("link", { name: new RegExp(title) });

  await test.step("entra como administrador", async () => {
    await page.goto("/entrar");
    await page.getByLabel("E-mail").fill(ADMIN_EMAIL);
    await page.getByLabel("Senha").fill(ADMIN_PASSWORD);
    await page.getByRole("button", { name: "Entrar", exact: true }).click();
    await expect(page).toHaveURL(/\/painel$/);
  });

  await test.step("envia o documento", async () => {
    await page.goto("/biblioteca");
    await page.getByRole("button", { name: "Enviar documentos" }).first().click();
    await page.locator("input[type=file]").setInputFiles({
      name: `${title}.txt`,
      mimeType: "text/plain",
      buffer: Buffer.from(
        `Garantia do compressor ${model}\n\n` +
          `O prazo de garantia do compressor ${model} é de 24 meses a partir da data de instalação.\n`,
      ),
    });
    await page.getByRole("button", { name: "Enviar", exact: true }).click();
    await expect(page.getByText("Documento enviado. O processamento começou.")).toBeVisible();
    await page.keyboard.press("Escape");
  });

  await test.step("espera o worker deixar o documento pronto", async () => {
    await page.getByRole("searchbox", { name: "Buscar documentos pelo título" }).fill(model);
    await expect(page.getByRole("link", { name: title })).toBeVisible();
    await expect(page.getByText("Pronto", { exact: true })).toBeVisible({ timeout: 90_000 });
  });

  await test.step("pergunta e recebe a resposta com a fonte", async () => {
    await page.goto("/perguntar");
    await page.getByRole("textbox", { name: "Pergunta" }).fill(`Qual é o prazo de garantia do compressor ${model}?`);
    await page.getByRole("button", { name: "Enviar pergunta" }).click();

    // filter por texto, e não getByText: a resposta pode quebrar a frase em vários elementos.
    await expect(page.getByRole("article").filter({ hasText: "24 meses" })).toBeVisible({ timeout: 45_000 });
    await expect(sourceLink()).toBeVisible();
  });

  await test.step("abre o documento a partir da fonte, com o trecho grifado", async () => {
    await sourceLink().click();
    await expect(page).toHaveURL(/\/documentos\/[^/?]+\?.*trecho=/);
    await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
    await expect(page.locator("mark").first()).toContainText("24 meses");
  });
});
