import { expect, Page, test } from "@playwright/test";

const user = {
  id: "00000000-0000-0000-0000-000000000088",
  email: "ipad-acceptance@ironhousecontracting.com",
  display_name: "iPad Acceptance Operator",
  role: "admin",
  is_active: true,
  password_reset_required: false,
  last_login_at: null,
  created_at: "2026-07-29T00:00:00Z",
  updated_at: "2026-07-29T00:00:00Z",
};

type ApiState = {
  interruptChat: boolean;
  assistantMessage: string;
};

type HarnessSnapshot = {
  instances: number;
  starts: number;
  activeSessions: number;
  maximumActiveSessions: number;
  aborts: number;
  speechCancels: number;
  spoken: string[];
};

async function installVoiceHarness(page: Page) {
  await page.addInitScript(() => {
    type RecognitionResultHandler = ((event: {
      results: ArrayLike<{ 0: { transcript: string } }>;
    }) => void) | null;
    type RecognitionErrorHandler = ((event: { error?: string }) => void) | null;
    type MockUtterance = {
      text: string;
      lang: string;
      onend: (() => void) | null;
      onerror: (() => void) | null;
    };

    class MockRecognition {
      continuous = false;
      interimResults = false;
      lang = "";
      onresult: RecognitionResultHandler = null;
      onend: (() => void) | null = null;
      onerror: RecognitionErrorHandler = null;
      active = false;

      constructor() {
        harness.instances.push(this);
      }

      start() {
        harness.starts += 1;
        if (harness.startFailures > 0) {
          harness.startFailures -= 1;
          throw new Error("Injected recognition start failure");
        }
        if (!this.active) {
          this.active = true;
          harness.activeSessions += 1;
          harness.maximumActiveSessions = Math.max(
            harness.maximumActiveSessions,
            harness.activeSessions,
          );
        }
      }

      stop() {
        this.release();
        harness.stops += 1;
      }

      abort() {
        this.release();
        harness.aborts += 1;
      }

      emit(transcript: string) {
        this.onresult?.({ results: [{ 0: { transcript } }] });
      }

      fail(error: string) {
        this.release();
        this.onerror?.({ error });
      }

      end() {
        this.release();
        this.onend?.();
      }

      private release() {
        if (!this.active) return;
        this.active = false;
        harness.activeSessions = Math.max(0, harness.activeSessions - 1);
      }
    }

    class MockSpeechSynthesisUtterance implements MockUtterance {
      lang = "";
      onend: (() => void) | null = null;
      onerror: (() => void) | null = null;

      constructor(public text: string) {}
    }

    Object.defineProperty(window.navigator, "platform", {
      configurable: true,
      value: "MacIntel",
    });
    Object.defineProperty(window.navigator, "maxTouchPoints", {
      configurable: true,
      value: 5,
    });

    const harness = {
      instances: [] as MockRecognition[],
      starts: 0,
      stops: 0,
      aborts: 0,
      activeSessions: 0,
      maximumActiveSessions: 0,
      startFailures: 0,
      speechCancels: 0,
      holdSpeech: false,
      spoken: [] as string[],
      activeUtterance: null as MockUtterance | null,
      emitLatest(transcript: string) {
        this.instances.at(-1)?.emit(transcript);
      },
      failLatest(error: string) {
        this.instances.at(-1)?.fail(error);
      },
      endLatest() {
        this.instances.at(-1)?.end();
      },
      snapshot() {
        return {
          instances: this.instances.length,
          starts: this.starts,
          activeSessions: this.activeSessions,
          maximumActiveSessions: this.maximumActiveSessions,
          aborts: this.aborts,
          speechCancels: this.speechCancels,
          spoken: [...this.spoken],
        };
      },
    };

    const browserWindow = window as typeof window & {
      webkitSpeechRecognition?: typeof MockRecognition;
      SpeechRecognition?: typeof MockRecognition;
      __IHOS_VOICE_E2E__?: typeof harness;
    };
    browserWindow.webkitSpeechRecognition = MockRecognition;
    browserWindow.SpeechRecognition = MockRecognition;
    browserWindow.__IHOS_VOICE_E2E__ = harness;
    Object.defineProperty(window, "SpeechSynthesisUtterance", {
      configurable: true,
      value: MockSpeechSynthesisUtterance,
    });
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: {
        cancel() {
          harness.speechCancels += 1;
          harness.activeUtterance = null;
        },
        speak(utterance: MockUtterance) {
          harness.spoken.push(utterance.text);
          harness.activeUtterance = utterance;
          if (!harness.holdSpeech) {
            window.setTimeout(() => {
              if (harness.activeUtterance === utterance) {
                harness.activeUtterance = null;
                utterance.onend?.();
              }
            }, 0);
          }
        },
      },
    });
  });
}

async function mockApi(page: Page, apiState: ApiState) {
  let authenticated = false;
  await page.route("http://localhost:8000/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;

    if (path.endsWith("/auth/me")) {
      await route.fulfill(
        authenticated
          ? { status: 200, json: { authentication: "authenticated", user } }
          : { status: 401, json: { detail: "Sign in is required." } },
      );
      return;
    }
    if (path.endsWith("/auth/login") && request.method() === "POST") {
      authenticated = true;
      await route.fulfill({ status: 200, json: { authentication: "authenticated", user } });
      return;
    }
    if (path.endsWith("/auth/logout") && request.method() === "POST") {
      authenticated = false;
      await route.fulfill({ status: 204 });
      return;
    }
    if (path.endsWith("/auth/me/permissions")) {
      await route.fulfill({
        status: 200,
        json: { role: "admin", modules: { projects: ["read"], suppliers: ["read"] } },
      });
      return;
    }
    if (path.endsWith("/iron-house-chat/messages") && request.method() === "POST") {
      if (apiState.interruptChat) {
        await route.abort("failed");
        return;
      }
      await route.fulfill({
        status: 200,
        json: {
          conversation: { id: "voice-acceptance-conversation" },
          user_message: {
            id: "voice-acceptance-user-message",
            role: "user",
            content: "Acceptance request",
            status: "completed",
          },
          assistant_message: {
            id: "voice-acceptance-assistant-message",
            role: "assistant",
            content: apiState.assistantMessage,
            status: "completed",
          },
        },
      });
      return;
    }
    await route.fulfill({ status: 200, json: { items: [], total: 0 } });
  });
}

async function signIn(page: Page) {
  await page.goto("/");
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password").fill("Disposable-iPad-acceptance-only");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Iron House Dashboard" })).toBeVisible();
}

async function harnessSnapshot(page: Page): Promise<HarnessSnapshot> {
  return page.evaluate(() => {
    const browserWindow = window as typeof window & {
      __IHOS_VOICE_E2E__?: { snapshot: () => HarnessSnapshot };
    };
    if (!browserWindow.__IHOS_VOICE_E2E__) throw new Error("Voice harness is unavailable.");
    return browserWindow.__IHOS_VOICE_E2E__.snapshot();
  });
}

async function emitLatest(page: Page, transcript: string) {
  await page.evaluate((value) => {
    const browserWindow = window as typeof window & {
      __IHOS_VOICE_E2E__?: { emitLatest: (transcript: string) => void };
    };
    browserWindow.__IHOS_VOICE_E2E__?.emitLatest(value);
  }, transcript);
}

test.beforeEach(async ({ page }, testInfo) => {
  test.skip(
    !["mobile-chromium", "ipad-webkit"].includes(testInfo.project.name),
    "The voice acceptance suite targets mobile Apple lifecycle behavior.",
  );
  await installVoiceHarness(page);
});

test("one enable action supports ten iPad commands without duplicate sessions", async ({ page }) => {
  const apiState = { interruptChat: false, assistantMessage: "Acceptance response." };
  await mockApi(page, apiState);
  await signIn(page);
  await page.getByRole("button", { name: "Enable hands-free Hey Chat" }).click();

  const commands = [
    "Hey Chat, go home",
    "Hey Chat, go home",
    "Hey Chat, go home",
    "Hey Chat, go home",
    "Hey Chat, go home",
    "Hey Chat, go home",
    "Hey Chat, go home",
    "Hey Chat, go home",
    "Hey Chat, go home",
    "Hey Chat, go home",
  ];

  for (const command of commands) {
    const before = await harnessSnapshot(page);
    await emitLatest(page, command);
    await expect
      .poll(async () => (await harnessSnapshot(page)).instances)
      .toBe(before.instances + 1);
  }

  const snapshot = await harnessSnapshot(page);
  expect(snapshot.maximumActiveSessions).toBe(1);
  expect(snapshot.activeSessions).toBe(1);
  expect(snapshot.starts).toBe(11);
  await expect(page.getByRole("heading", { name: "Iron House Dashboard" })).toBeVisible();

  const metrics = await page.evaluate(() => window.__IHOS_PERFORMANCE__?.snapshot());
  expect(metrics?.voice.commands).toBe(10);
  expect(metrics?.voice.maximum_active_recognition_sessions).toBe(1);

  await page.getByRole("button", { name: "Stop hands-free Hey Chat" }).click();
  expect((await harnessSnapshot(page)).activeSessions).toBe(0);
  expect((await page.evaluate(() => window.__IHOS_PERFORMANCE__?.snapshot()))
    ?.voice.resources).toEqual({
    active_recognition_sessions: 0,
    active_restart_timers: 0,
    active_speech_watchdogs: 0,
    active_requests: 0,
  });
});

test("permission denial and background return fail closed", async ({ page }) => {
  const apiState = { interruptChat: false, assistantMessage: "Acceptance response." };
  await mockApi(page, apiState);
  await signIn(page);
  await page.getByRole("button", { name: "Enable hands-free Hey Chat" }).click();

  await page.evaluate(() => {
    const browserWindow = window as typeof window & {
      __IHOS_VOICE_E2E__?: { failLatest: (error: string) => void };
    };
    browserWindow.__IHOS_VOICE_E2E__?.failLatest("not-allowed");
  });

  await expect(page.getByRole("alert")).toContainText("Microphone permission was denied");
  await expect(page.getByRole("button", { name: "Enable hands-free Hey Chat" })).toBeVisible();
  expect((await harnessSnapshot(page)).activeSessions).toBe(0);

  await page.getByRole("button", { name: "Enable hands-free Hey Chat" }).click();
  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "hidden",
    });
    document.dispatchEvent(new Event("visibilitychange"));
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "visible",
    });
    document.dispatchEvent(new Event("visibilitychange"));
  });

  await expect(page.getByRole("button", { name: "Enable hands-free Hey Chat" })).toBeVisible();
  expect((await harnessSnapshot(page)).activeSessions).toBe(0);
});

test("start failure, no-speech, and end storms recover with one session", async ({ page }) => {
  const apiState = { interruptChat: false, assistantMessage: "Acceptance response." };
  await mockApi(page, apiState);
  await signIn(page);
  await page.evaluate(() => {
    const browserWindow = window as typeof window & {
      __IHOS_VOICE_E2E__?: { startFailures: number };
    };
    if (browserWindow.__IHOS_VOICE_E2E__) browserWindow.__IHOS_VOICE_E2E__.startFailures = 1;
  });

  await page.getByRole("button", { name: "Enable hands-free Hey Chat" }).click();
  await expect.poll(async () => (await harnessSnapshot(page)).instances).toBe(2);

  await page.evaluate(() => {
    const browserWindow = window as typeof window & {
      __IHOS_VOICE_E2E__?: {
        failLatest: (error: string) => void;
        endLatest: () => void;
      };
    };
    browserWindow.__IHOS_VOICE_E2E__?.failLatest("no-speech");
    browserWindow.__IHOS_VOICE_E2E__?.endLatest();
    browserWindow.__IHOS_VOICE_E2E__?.endLatest();
  });
  await expect.poll(async () => (await harnessSnapshot(page)).instances).toBe(3);

  const snapshot = await harnessSnapshot(page);
  expect(snapshot.maximumActiveSessions).toBe(1);
  expect(snapshot.activeSessions).toBe(1);
});

test("network interruption recovers and long speech cleans up on Stop", async ({ page }) => {
  const apiState = { interruptChat: true, assistantMessage: "Acceptance response." };
  await mockApi(page, apiState);
  await signIn(page);
  await page.getByRole("button", { name: "Enable hands-free Hey Chat" }).click();
  await emitLatest(page, "Hey Chat, summarize project risks");

  await expect(page.getByRole("alert")).toBeVisible();
  await expect.poll(async () => (await harnessSnapshot(page)).instances).toBeGreaterThan(1);
  expect((await harnessSnapshot(page)).maximumActiveSessions).toBe(1);

  apiState.interruptChat = false;
  apiState.assistantMessage = "A ".repeat(500);
  await page.evaluate(() => {
    const browserWindow = window as typeof window & {
      __IHOS_VOICE_E2E__?: { holdSpeech: boolean };
    };
    if (browserWindow.__IHOS_VOICE_E2E__) browserWindow.__IHOS_VOICE_E2E__.holdSpeech = true;
  });
  await emitLatest(page, "Hey Chat, read the long project summary");

  await expect(page.getByText("Speaking the answer")).toBeVisible();
  const activeMetrics = await page.evaluate(() => window.__IHOS_PERFORMANCE__?.snapshot());
  expect(activeMetrics?.voice.resources.active_recognition_sessions).toBe(0);
  expect(activeMetrics?.voice.resources.active_speech_watchdogs).toBe(1);

  await page.getByRole("button", { name: "Stop hands-free Hey Chat" }).click();
  const finalMetrics = await page.evaluate(() => window.__IHOS_PERFORMANCE__?.snapshot());
  expect(finalMetrics?.voice.resources).toEqual({
    active_recognition_sessions: 0,
    active_restart_timers: 0,
    active_speech_watchdogs: 0,
    active_requests: 0,
  });
  expect((await harnessSnapshot(page)).speechCancels).toBeGreaterThan(0);
});

test("logout releases the active recognition session", async ({ page }) => {
  const apiState = { interruptChat: false, assistantMessage: "Acceptance response." };
  await mockApi(page, apiState);
  await signIn(page);
  await page.getByRole("button", { name: "Enable hands-free Hey Chat" }).click();
  expect((await harnessSnapshot(page)).activeSessions).toBe(1);

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  expect((await harnessSnapshot(page)).activeSessions).toBe(0);
  expect((await page.evaluate(() => window.__IHOS_PERFORMANCE__?.snapshot()))
    ?.voice.resources).toEqual({
    active_recognition_sessions: 0,
    active_restart_timers: 0,
    active_speech_watchdogs: 0,
    active_requests: 0,
  });
});
