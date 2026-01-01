/* シンプルな空き枠検索ページ */
"use client";
import { useState } from "react";
import { apiFetch } from "@/api/client";
import styles from "./page.module.css";

type SlotStatus = "open" | "closed" | "blocked";

type SlotAvailability = {
  id: number;
  shop_id: number;
  seat_id: number | null;
  starts_at: string;
  ends_at: string;
  status: SlotStatus;
};

type AvailabilityResponse = {
  items: SlotAvailability[];
};

const toISO = (d: Date) => d.toISOString();

export default function Home() {
  const [shopId, setShopId] = useState("1");
  const [seatId, setSeatId] = useState("");
  const [start, setStart] = useState(() => {
    const now = new Date();
    return toISO(now).slice(0, 16); // yyyy-MM-ddTHH:mm
  });
  const [end, setEnd] = useState(() => {
    const nextHour = new Date(Date.now() + 60 * 60 * 1000);
    return toISO(nextHour).slice(0, 16);
  });
  const [partySize, setPartySize] = useState("2");
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SlotAvailability[]>([]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setMessage(null);
    setLoading(true);
    setResults([]);
    try {
      const params = new URLSearchParams({
        start: new Date(start).toISOString(),
        end: new Date(end).toISOString(),
      });
      if (seatId.trim()) {
        params.set("seat_id", seatId.trim());
      }
      if (partySize.trim()) {
        params.set("party_size", partySize.trim());
      }
      const res = await apiFetch<AvailabilityResponse>(
        `/shops/${shopId}/slots/availability?${params.toString()}`
      );
      if (res.error) {
        setMessage(res.error.detail ?? "検索でエラーが発生しました");
        return;
      }
      setResults(res.data?.items ?? []);
      if ((res.data?.items?.length ?? 0) === 0) {
        setMessage("該当する空き枠はありませんでした");
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "予期せぬエラー");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <header className={styles.header}>
          <h1>空き枠検索</h1>
          <p>
            `localStorage.access_token` にアクセストークンを保存した状態で検索してください。
            日付は JST のローカル入力を ISO に変換して送信します。
          </p>
        </header>

        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.row}>
            <label>
              店舗ID
              <input
                type="number"
                min="1"
                value={shopId}
                onChange={(e) => setShopId(e.target.value)}
                required
              />
            </label>
            <label>
              席ID（任意）
              <input
                type="number"
                min="1"
                value={seatId}
                onChange={(e) => setSeatId(e.target.value)}
                placeholder="指定しない場合は空欄"
              />
            </label>
            <label>
              予約人数
              <input
                type="number"
                min="1"
                value={partySize}
                onChange={(e) => setPartySize(e.target.value)}
              />
            </label>
          </div>

          <div className={styles.row}>
            <label>
              開始日時 (JST)
              <input
                type="datetime-local"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                required
              />
            </label>
            <label>
              終了日時 (JST)
              <input
                type="datetime-local"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                required
              />
            </label>
          </div>

          <div className={styles.actions}>
            <button type="submit" disabled={loading}>
              {loading ? "検索中..." : "検索する"}
            </button>
          </div>
        </form>

        {message && <div className={styles.message}>{message}</div>}

        <section className={styles.results}>
          <h2>検索結果</h2>
          {results.length === 0 && !message && (
            <div className={styles.empty}>まだ検索していません</div>
          )}
          {results.length > 0 && (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>席ID</th>
                  <th>開始</th>
                  <th>終了</th>
                  <th>ステータス</th>
                </tr>
              </thead>
              <tbody>
                {results.map((slot) => (
                  <tr key={slot.id}>
                    <td>{slot.id}</td>
                    <td>{slot.seat_id ?? "-"}</td>
                    <td>{slot.starts_at}</td>
                    <td>{slot.ends_at}</td>
                    <td>{slot.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </main>
    </div>
  );
}
