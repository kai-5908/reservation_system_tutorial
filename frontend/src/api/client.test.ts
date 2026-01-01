import { apiFetch, setToken } from "./client";

const originalFetch = global.fetch;
const originalLocation = window.location;

// シンプルなモックレスポンス生成ヘルパー（Response型を満たす）
const jsonResponse = (body: unknown, status = 200): Response =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

beforeEach(() => {
  jest.resetAllMocks();
  setToken(null);
});

afterAll(() => {
  global.fetch = originalFetch as typeof fetch;
  Object.defineProperty(window, "location", {
    value: originalLocation,
    writable: true,
  });
});

test("jsonBody is stringified and sent with Authorization and X-Request-ID", async () => {
  const mockFetch = jest.fn<Promise<Response>, unknown[]>().mockResolvedValue(jsonResponse({ ok: true }));
  global.fetch = mockFetch as unknown as typeof fetch;
  setToken("testtoken");

  await apiFetch("/test", { method: "POST", jsonBody: { foo: "bar" } });

  expect(mockFetch).toHaveBeenCalledTimes(1);
  const call = mockFetch.mock.calls[0];
  const init = (call?.[1] ?? {}) as RequestInit;
  const headers = new Headers(init.headers);
  expect(headers.get("Authorization")).toBe("Bearer testtoken");
  expect(headers.get("X-Request-ID")).toBeTruthy();
  expect(init?.body).toBe(JSON.stringify({ foo: "bar" }));
});

test("plain object body is stringified", async () => {
  const mockFetch = jest.fn<Promise<Response>, unknown[]>().mockResolvedValue(jsonResponse({}));
  global.fetch = mockFetch as unknown as typeof fetch;
  await apiFetch("/plain", { method: "POST", jsonBody: { a: 1 } });
  const call = mockFetch.mock.calls[0];
  const init = (call?.[1] ?? {}) as RequestInit;
  expect(init?.body).toBe(JSON.stringify({ a: 1 }));
});

test("FormData body does not set JSON content-type", async () => {
  const mockFetch = jest.fn<Promise<Response>, unknown[]>().mockResolvedValue(jsonResponse({}));
  global.fetch = mockFetch as unknown as typeof fetch;
  const fd = new FormData();
  fd.append("file", new Blob(["test"], { type: "text/plain" }), "test.txt");
  await apiFetch("/upload", { method: "POST", body: fd });
  const call = mockFetch.mock.calls[0];
  const init = (call?.[1] ?? {}) as RequestInit;
  const headers = new Headers(init.headers);
  expect(headers.get("Content-Type")).toBeNull();
});

test("401 triggers redirect to /login", async () => {
  const mockFetch = jest.fn<Promise<Response>, unknown[]>().mockResolvedValue(
    jsonResponse({ detail: "unauthorized" }, 401)
  );
  global.fetch = mockFetch as unknown as typeof fetch;

  const replaceSpy = jest.fn();
  Object.defineProperty(window, "location", {
    value: { ...window.location, replace: replaceSpy },
    writable: true,
  });

  const res = await apiFetch("/auth-check");
  expect(res.error?.status).toBe(401);
  expect(replaceSpy).toHaveBeenCalledWith("/login");
});
