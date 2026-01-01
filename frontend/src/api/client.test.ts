import { apiFetch, setToken } from "./client";

const originalFetch = global.fetch;
const originalLocation = window.location;

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
  const mockFetch = jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ ok: true }),
  });
  global.fetch = mockFetch as any;
  setToken("testtoken");

  await apiFetch("/test", { method: "POST", jsonBody: { foo: "bar" } });

  expect(mockFetch).toHaveBeenCalledTimes(1);
  const [, init] = mockFetch.mock.calls[0];
  expect((init?.headers as any)["Authorization"]).toBe("Bearer testtoken");
  expect((init?.headers as any)["X-Request-ID"]).toBeDefined();
  expect(init?.body).toBe(JSON.stringify({ foo: "bar" }));
});

test("plain object body is stringified", async () => {
  const mockFetch = jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({}),
  });
  global.fetch = mockFetch as any;
  await apiFetch("/plain", { method: "POST", body: { a: 1 } as any });
  const [, init] = mockFetch.mock.calls[0];
  expect(init?.body).toBe(JSON.stringify({ a: 1 }));
});

test("401 triggers redirect to /login", async () => {
  const mockFetch = jest.fn().mockResolvedValue({
    ok: false,
    status: 401,
    json: async () => ({ detail: "unauthorized" }),
  });
  global.fetch = mockFetch as any;

  const replaceSpy = jest.fn();
  Object.defineProperty(window, "location", {
    value: { ...window.location, replace: replaceSpy },
    writable: true,
  });

  const res = await apiFetch("/auth-check");
  expect(res.error?.status).toBe(401);
  expect(replaceSpy).toHaveBeenCalledWith("/login");
});
