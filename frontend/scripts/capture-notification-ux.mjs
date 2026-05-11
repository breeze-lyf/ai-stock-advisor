import { mkdir } from "node:fs/promises";
import path from "node:path";

import { chromium } from "playwright";

const FRONTEND_URL = process.env.FRONTEND_URL || "http://127.0.0.1:3000";
const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";
const OUTPUT_DIR = process.env.OUTPUT_DIR || "/tmp/ai-stock-advisor-shots";
const EMAIL = `codex-notify-${Date.now()}@example.com`;
const PASSWORD = "Password123";

async function registerAndLogin() {
  const registerResponse = await fetch(`${BACKEND_URL}/api/v1/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: EMAIL,
      password: PASSWORD,
    }),
  });

  if (!registerResponse.ok) {
    const detail = await registerResponse.text();
    throw new Error(`register failed: ${registerResponse.status} ${detail}`);
  }

  const tokenPayload = await registerResponse.json();

  const meResponse = await fetch(`${BACKEND_URL}/api/v1/user/me`, {
    headers: {
      Authorization: `Bearer ${tokenPayload.access_token}`,
    },
  });

  if (!meResponse.ok) {
    const detail = await meResponse.text();
    throw new Error(`user lookup failed: ${meResponse.status} ${detail}`);
  }

  const user = await meResponse.json();

  return {
    user,
    accessToken: tokenPayload.access_token,
    refreshToken: tokenPayload.refresh_token,
  };
}

async function seedNotificationHistory(accessToken) {
  const priorities = ["P0", "P1", "P2", "P3"];

  for (const priority of priorities) {
    await fetch(`${BACKEND_URL}/api/v1/notification-settings/notification-settings/test?priority=${priority}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
  }
}

async function capturePage(page, url, fileName) {
  await page.goto(url, { waitUntil: "networkidle" });
  await page.screenshot({
    path: path.join(OUTPUT_DIR, fileName),
    fullPage: true,
  });
}

async function captureNotificationSettings(page, fileName) {
  await page.goto(`${FRONTEND_URL}/settings`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /通知/ }).click();
  await page.screenshot({
    path: path.join(OUTPUT_DIR, fileName),
    fullPage: true,
  });
}

async function main() {
  await mkdir(OUTPUT_DIR, { recursive: true });
  const { accessToken, refreshToken } = await registerAndLogin();
  await seedNotificationHistory(accessToken);

  const browser = await chromium.launch();
  const context = await browser.newContext({
    colorScheme: "light",
    locale: "zh-CN",
    timezoneId: "Asia/Shanghai",
    viewport: { width: 1440, height: 1280 },
  });
  const page = await context.newPage();

  await page.addInitScript(
    ({ token, refresh }) => {
      window.localStorage.setItem("token", token);
      window.localStorage.setItem("refreshToken", refresh);
    },
    { token: accessToken, refresh: refreshToken }
  );

  await captureNotificationSettings(page, "settings-desktop-auth.png");
  await capturePage(page, `${FRONTEND_URL}/?tab=alerts`, "alerts-desktop-auth.png");

  const mobileContext = await browser.newContext({
    colorScheme: "light",
    locale: "zh-CN",
    timezoneId: "Asia/Shanghai",
    viewport: { width: 393, height: 1180 },
    isMobile: true,
    hasTouch: true,
  });
  const mobilePage = await mobileContext.newPage();

  await mobilePage.addInitScript(
    ({ token, refresh }) => {
      window.localStorage.setItem("token", token);
      window.localStorage.setItem("refreshToken", refresh);
    },
    { token: accessToken, refresh: refreshToken }
  );

  await captureNotificationSettings(mobilePage, "settings-mobile-auth.png");
  await capturePage(mobilePage, `${FRONTEND_URL}/?tab=alerts`, "alerts-mobile-auth.png");

  await mobileContext.close();
  await context.close();
  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
