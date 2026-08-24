"use client";

import { useEffect, useState } from "react";
import { fetchWorlds, generateWorld } from "../lib/api";
import { Dashboard } from "../components/Dashboard";

export default function Home() {
  const [worlds, setWorlds] = useState<any[]>([]);
  const [selectedWorld, setSelectedWorld] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadWorlds();
  }, []);

  const loadWorlds = async () => {
    try {
      const data = await fetchWorlds();
      setWorlds(data);
      if (data.length > 0) {
        setSelectedWorld(data[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    setLoading(true);
    try {
      await generateWorld();
      await loadWorlds();
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen bg-black text-green-500 font-mono items-center justify-center">
        INITIALIZING WORLDOS OBSERVER...
      </div>
    );
  }

  if (!selectedWorld) {
    return (
      <div className="flex min-h-screen bg-zinc-950 flex-col items-center justify-center p-24 text-zinc-300 font-mono">
        <h1 className="text-4xl font-bold mb-4 text-cyan-500 tracking-widest">WORLDOS TERMINAL</h1>
        <p className="mb-8 text-zinc-500">No active simulations detected.</p>
        <button 
          onClick={handleGenerate}
          className="px-6 py-3 bg-zinc-900 border border-zinc-700 hover:bg-zinc-800 hover:text-white transition-colors uppercase tracking-widest text-sm"
        >
          Initialize New World
        </button>
      </div>
    );
  }

  return <Dashboard world={selectedWorld} />;
}
