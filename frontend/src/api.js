const API_BASE = "/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message = data?.detail ?? `Request failed (${response.status})`;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }

  return data;
}

export function submitTransaction({ userId, amount, idempotencyKey }) {
  return request("/transaction", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      amount: Number(amount),
      idempotency_key: idempotencyKey,
    }),
  });
}

export function fetchUserSummary(userId) {
  return request(`/summary/${encodeURIComponent(userId)}`);
}

export function fetchRanking() {
  return request("/ranking");
}
