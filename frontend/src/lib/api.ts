export const API_BASE = "http://localhost:8000";
export const WS_BASE = "ws://localhost:8000/ws";

export async function fetchWorlds() {
  const res = await fetch(`${API_BASE}/worlds`);
  if (!res.ok) throw new Error("Failed to fetch worlds");
  return res.json();
}

export async function generateWorld() {
  const res = await fetch(`${API_BASE}/worlds/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: "New World " + Math.floor(Math.random() * 1000),
      seed: Math.floor(Math.random() * 1000000),
      cities: 4,
      characters: 30,
      factions: 4
    })
  });
  if (!res.ok) throw new Error("Failed to generate world");
  return res.json();
}

export async function fetchWorldState(worldId: string) {
  const res = await fetch(`${API_BASE}/worlds/${worldId}/state`);
  if (!res.ok) throw new Error("Failed to fetch world state");
  return res.json();
}

export async function fetchWorldTimeline(worldId: string) {
  const res = await fetch(`${API_BASE}/worlds/${worldId}/timeline`);
  if (!res.ok) throw new Error("Failed to fetch world timeline");
  return res.json();
}

export async function controlSimulation(worldId: string, action: "start" | "pause" | "tick" | "advance") {
  const url = `${API_BASE}/worlds/${worldId}/simulation/${action}`;
  const options: RequestInit = { method: "POST" };
  
  if (action === "advance") {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify({ ticks: 10 }); // Advance by 10 ticks for now
  }
  
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`Failed to ${action} simulation`);
  return res.json();
}

export async function fetchCharacterDetails(worldId: string, characterId: string) {
  const res = await fetch(`${API_BASE}/worlds/${worldId}/characters/${characterId}`);
  if (!res.ok) throw new Error("Failed to fetch character details");
  return res.json();
}

export async function fetchFactionDetails(worldId: string, factionId: string) {
  const res = await fetch(`${API_BASE}/worlds/${worldId}/factions/${factionId}`);
  if (!res.ok) throw new Error("Failed to fetch faction details");
  return res.json();
}

export async function fetchCausalChain(worldId: string, eventId: string) {
  const res = await fetch(`${API_BASE}/worlds/${worldId}/events/${eventId}/causal-chain`);
  if (!res.ok) throw new Error("Failed to fetch causal chain");
  return res.json();
}

export async function triggerIntervention(worldId: string, type: string, targetId?: string, payload?: any) {
  const res = await fetch(`${API_BASE}/worlds/${worldId}/interventions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      type,
      target_id: targetId || null,
      payload: payload || {}
    })
  });
  if (!res.ok) throw new Error(`Failed to trigger intervention: ${type}`);
  return res.json();
}

export async function createCounterfactual(worldId: string) {
  const res = await fetch(`${API_BASE}/worlds/${worldId}/counterfactual`, {
    method: "POST"
  });
  if (!res.ok) throw new Error("Failed to create counterfactual");
  return res.json();
}

export async function compareWorlds(worldId: string, targetWorldId: string) {
  const res = await fetch(`${API_BASE}/worlds/${worldId}/compare/${targetWorldId}`);
  if (!res.ok) throw new Error("Failed to compare worlds");
  return res.json();
}
