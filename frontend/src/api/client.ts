import { observeApiRequest } from "../observability/performance";

export const AUTH_SESSION_EXPIRED_EVENT = "ihos:session-expired";

export async function apiFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const started = performance.now();
  try {
    const response = await fetch(input, {
      ...init,
      credentials: "include",
    });
    observeApiRequest(
      performance.now() - started,
      response.ok ? "success" : "failure",
    );
    if (response.status === 401 && !String(input).includes("/auth/")) {
      window.dispatchEvent(new Event(AUTH_SESSION_EXPIRED_EVENT));
    }
    return response;
  } catch (reason) {
    const aborted =
      init.signal?.aborted ||
      (reason instanceof DOMException && reason.name === "AbortError");
    observeApiRequest(
      performance.now() - started,
      aborted ? "aborted" : "failure",
    );
    throw reason;
  }
}
