import { expect, test, type Page } from "@playwright/test";

/** Mock the Saathi API so e2e never needs the backend or a real LLM. */
async function mockApi(page: Page) {
  await page.route("**/api/v1/**", (route) =>
    route.fulfill({ json: { data: [], meta: { requestId: "e2e" } } }),
  );
  await page.route("**/health", (route) => route.fulfill({ json: { status: "ok" } }));
  await page.route("**/api/v1/assistant/turns", async (route) => {
    const body = JSON.parse(route.request().postData() ?? "{}") as {
      text?: string;
      inputMode?: string;
    };
    expect(body.inputMode).toBe("text");
    const events = [
      ["meta", { conversationId: "conv-1", model: "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B" }],
      ["privacy", { entityCounts: { phone: 1, upi: 1 } }],
      ["token", { delta: "Namaste! " }],
      ["token", { delta: "Bill reminder set." }],
      ["pending_action", { id: "pa-1", summary: "Pay ₹1,240 electricity bill to <UPI_1>" }],
      ["done", { usage: { tokensIn: 120, tokensOut: 30 } }],
    ] as const;
    await route.fulfill({
      status: 200,
      headers: { "Content-Type": "text/event-stream", "X-Request-ID": "e2e-turn" },
      body: events
        .map(([event, data]) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`)
        .join(""),
    });
  });
}

test("landing page loads with the demo CTA", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Hinglish");
  await expect(page.getByRole("button", { name: "Try demo" }).first()).toBeVisible();
  await expect(page.getByText("nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")).toBeVisible();
});

test("console renders and the text fallback streams a reply", async ({ page }) => {
  // Simulate a browser without Web Speech recognition (e.g. Firefox).
  await page.addInitScript(() => {
    Object.defineProperty(window, "webkitSpeechRecognition", {
      value: undefined,
      configurable: true,
    });
    Object.defineProperty(window, "SpeechRecognition", { value: undefined, configurable: true });
  });
  await mockApi(page);
  await page.goto("/console");

  await expect(page.getByRole("heading", { name: "Voice console" })).toBeVisible();
  await expect(page.getByTestId("stt-fallback-notice")).toBeVisible();

  const input = page.getByPlaceholder("Type in Hindi, English or Hinglish…");
  await input.fill("Mera bijli ka bill 98xxxxxx10 pe remind karo");
  await input.press("Enter");

  const transcript = page.getByTestId("transcript");
  await expect(transcript).toContainText("Mera bijli ka bill");
  await expect(transcript).toContainText("Namaste! Bill reminder set.");
  await expect(page.getByTestId("entity-counts")).toContainText("Phone");
  await expect(page.getByTestId("inline-pending-actions")).toContainText("Pay ₹1,240");
});
