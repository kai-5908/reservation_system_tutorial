// ランダムなリクエストIDを作るために UUID を使う
import { v4 as uuidv4 } from "uuid";

// --- 設計の意図 ---
// - 最小限の fetch ラッパー。
// - 各API呼び出しで毎回書く面倒な処理（Bearerヘッダ、Request-ID、JSON stringify、401リダイレクト）をここで吸収。
// - 個別APIのパラメータ（If-Match 等）は呼び出し側で指定する前提。
// - POST/PUT/PATCH を使うときは options.method を必ず明示する（指定漏れは GET になるので注意）。

// HTTPメソッドの型（指定漏れ防止用）
export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

// エラーを呼び出し側で扱いやすい形にするための型
export type ApiError = {
  status: number;
  message: string;
};

// 成功/失敗の両方を一つの戻り値で扱うための型
export type ApiResponse<T> = {
  data: T | null;
  error: ApiError | null;
};

// APIのベースURL（環境変数がなければローカル）
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
// トークンを保管する localStorage キー名
const TOKEN_STORAGE_KEY = "access_token";
// 401 のときに飛ばすログインページ（あとで調整OK）
const LOGIN_PATH = "/login"; // TODO: adjust to actual login path

// 毎回ユニークなリクエストIDを作る
function generateRequestId(): string {
  // RFC準拠のUUIDでリクエストIDを生成（ブラウザ差異を避けるためuuid依存）。
  return uuidv4();
}

// localStorage からトークンを取り出す（SSR時は何もしない）
function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

// localStorage にトークンを保存/削除するヘルパー
export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // ignore storage errors
  }
}

// HeadersInit を安全にマージして Headers を返す（Headers インスタンスも展開する）
function buildHeaders(extra?: HeadersInit, useJsonContentType: boolean = true): Headers {
  const headers = new Headers();
  if (useJsonContentType) {
    headers.set("Content-Type", "application/json");
  }
  // 呼び出し側のヘッダを上書き優先で取り込む
  if (extra) {
    const tmp = new Headers(extra);
    tmp.forEach((value, key) => headers.set(key, value));
  }
  // ローカルストレージからBearerを注入（なければ何もしない）。
  const token = getToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  // 相関用の Request-ID を自動付与（既に指定されていれば触らない）。
  if (!headers.has("X-Request-ID")) {
    headers.set("X-Request-ID", generateRequestId());
  }
  return headers;
}

// 相対パスをフルURLに変換（絶対URLならそのまま）
function buildUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `${API_BASE}${path}`;
}

// 共通のfetchラッパー。ジェネリック<T>で戻り値の型を呼び出し側が指定できる。
export async function apiFetch<T>(
  path: string,
  options: RequestInit & { method?: HttpMethod; jsonBody?: unknown } = {}
): Promise<ApiResponse<T>> {
  // エンドポイントのURLを作る
  const url = buildUrl(path);
  // 呼び出し側から渡されたオプションを展開。methodを指定しないとGETになるので注意。
  const { method = "GET", headers, body, jsonBody, ...rest } = options;
  // JSON系は jsonBody を優先（自動で stringify）。body がプレーンオブジェクトなら stringify。
  let payload: BodyInit | null | undefined = body ?? null;
  if (jsonBody !== undefined) {
    payload = JSON.stringify(jsonBody);
  } else if (
    payload !== null &&
    typeof payload === "object" &&
    !(payload instanceof FormData) &&
    !(payload instanceof Blob) &&
    !(payload instanceof ArrayBuffer)
  ) {
    payload = JSON.stringify(payload);
  }
  // Content-Type は FormData/Blob などの場合は自動設定しない（ブラウザに任せる）
  const useJsonContentType = !(
    payload !== null &&
    (payload instanceof FormData || payload instanceof Blob || payload instanceof ArrayBuffer)
  );

  // fetch に渡す最終的な RequestInit
  const init: RequestInit = {
    method,
    headers: buildHeaders(headers, useJsonContentType),
    body: payload,
    ...rest,
  };

  try {
    // 実際にHTTPリクエストを投げる
    const res = await fetch(url, init);
    if (res.status === 401) {
      // 未認証はログイン画面へ飛ばす（画面遷移が許容される前提）。
      if (typeof window !== "undefined") {
        window.location.replace(LOGIN_PATH);
      }
      return { data: null, error: { status: 401, message: "unauthorized" } };
    }
    // レスポンスボディをJSONとして読んでみる（読めない場合はnull）
    let json: unknown = null;
    try {
      json = await res.json();
    } catch {
      json = null;
    }
    // ステータスコードが 2xx 以外ならエラーとして返す
    if (!res.ok) {
      const detail =
        typeof json === "object" && json !== null && "detail" in json
          ? (json as { detail: unknown }).detail
          : res.statusText;
      return { data: null, error: { status: res.status, message: String(detail) } };
    }
    // 正常時は JSON を data として返す。型チェックは呼び出し側で行う前提。
    return { data: json as T, error: null };
  } catch (err) {
    // ネットワークエラー等
    return { data: null, error: { status: 0, message: (err as Error).message } };
  }
}
