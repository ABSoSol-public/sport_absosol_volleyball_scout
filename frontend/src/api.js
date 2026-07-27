const BASE = "/api";

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* Antwort ohne JSON-Body */
    }
    throw new Error(detail);
  }
  return response.json();
}

export const api = {
  listTeams: () => request("/teams"),
  createTeam: (data) => request("/teams", { method: "POST", body: JSON.stringify(data) }),
  getTeam: (id) => request(`/teams/${id}`),
  addPlayer: (teamId, data) =>
    request(`/teams/${teamId}/players`, { method: "POST", body: JSON.stringify(data) }),

  listMatches: () => request("/matches"),
  createMatch: (data) => request("/matches", { method: "POST", body: JSON.stringify(data) }),
  getMatch: (id) => request(`/matches/${id}`),

  liveState: (matchId) => request(`/matches/${matchId}/live/state`),
  startSet: (matchId, data) =>
    request(`/matches/${matchId}/live/set`, { method: "POST", body: JSON.stringify(data) }),
  rally: (matchId, data) =>
    request(`/matches/${matchId}/live/rally`, { method: "POST", body: JSON.stringify(data) }),
  substitution: (matchId, data) =>
    request(`/matches/${matchId}/live/substitution`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  timeout: (matchId, data) =>
    request(`/matches/${matchId}/live/timeout`, { method: "POST", body: JSON.stringify(data) }),
  undo: (matchId) => request(`/matches/${matchId}/live/undo`, { method: "POST" }),
};
