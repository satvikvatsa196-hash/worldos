"use client";

import { useEffect, useState, useRef } from "react";
import { 
  fetchWorldState, 
  fetchWorldTimeline, 
  controlSimulation, 
  WS_BASE 
} from "../lib/api";
import { TopPanel } from "./TopPanel";
import { MainView } from "./MainView";
import { BottomPanel } from "./BottomPanel";

export function Dashboard({ world }: { world: any }) {
  const [worldState, setWorldState] = useState<any>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<any>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const loadData = async () => {
    try {
      const state = await fetchWorldState(world.id);
      setWorldState(state);
      const events = await fetchWorldTimeline(world.id);
      setTimeline(events);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadData();
    
    // Connect to WebSocket for real-time events
    const ws = new WebSocket(`${WS_BASE}/worlds/${world.id}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // On new event, append to timeline and reload state for simplicity
        setTimeline((prev) => [data, ...prev]);
        loadData(); // Re-fetch state to update graphs and lists
      } catch (e) {
        console.error("WS Parse error", e);
      }
    };

    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send("ping");
      }
    }, 15000);

    return () => {
      clearInterval(pingInterval);
      ws.close();
    };
  }, [world.id]);

  if (!worldState) {
    return (
      <div className="flex items-center justify-center h-screen bg-black text-green-500 font-mono">
        INITIALIZING SENSOR ARRAY...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-zinc-300 font-mono text-sm overflow-hidden flex flex-col selection:bg-green-900 selection:text-green-400">
      <TopPanel 
        worldState={worldState} 
        onControl={async (action) => {
          await controlSimulation(world.id, action);
          loadData();
        }}
      />
      
      <div className="flex-1 flex overflow-hidden">
        <MainView 
          worldState={worldState} 
          timeline={timeline}
          selectedEntity={selectedEntity}
          onSelectEntity={setSelectedEntity}
        />
      </div>

      <div className="h-64 border-t border-zinc-800 bg-zinc-950 p-4">
        <BottomPanel worldState={worldState} />
      </div>
    </div>
  );
}
