export const AUTH_SESSION_EXPIRED_EVENT = "ihos:session-expired";

export async function apiFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const response = await fetch(input, {
    ...init,
    credentials: "include",
  });
  if (response.status === 401 && !String(input).includes("/auth/")) {
    window.dispatchEvent(new Event(AUTH_SESSION_EXPIRED_EVENT));
  }
  return response;
}
