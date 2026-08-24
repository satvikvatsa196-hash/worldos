"use client";
import { useState } from "react";
import { createCounterfactual } from "../lib/api";

function calculateTime(tick: number) {
  const hoursPerTick = 1;
  const totalHours = tick * hoursPerTick;
  const day = Math.floor(totalHours / 24) + 1;
  const hour = totalHours % 24;
  return { day, hour };
}

export function TopPanel({ 
  worldState, 
  onControl, 
  onIntervene,
  allWorlds,
  onSelectWorld,
  onRefreshWorlds,
  onCompare,
  isComparing
}: { 
  worldState: any, 
  onControl: (action: "start" | "pause" | "tick" | "advance") => void, 
  onIntervene?: () => void,
  allWorlds?: any[],
  onSelectWorld?: (w: any) => void,
  onRefreshWorlds?: () => void,
  onCompare?: (targetId: string) => void,
  isComparing?: boolean
}) {
  const { world } = worldState;
  const { day, hour } = calculateTime(world.tick);
  
  const isRunning = world.status === "running";
  const [isBranching, setIsBranching] = useState(false);

  const handleBranch = async () => {
    if (!onRefreshWorlds || !onSelectWorld) return;
    setIsBranching(true);
    try {
      const res = await createCounterfactual(world.id);
      await onRefreshWorlds();
      // We will let the user select the branch manually or auto-switch
      // Let's auto switch to the new counterfactual
      const newlyFetchedWorlds = await fetch('http://localhost:8000/worlds').then(r => r.json());
      const newWorld = newlyFetchedWorlds.find((w: any) => w.id === res.world_id);
      if (newWorld) onSelectWorld(newWorld);
    } catch(e) {
      console.error(e);
    } finally {
      setIsBranching(false);
    }
  };

  return (
    <div className="h-14 border-b border-zinc-800 bg-zinc-950 flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse"></div>
          {allWorlds && onSelectWorld ? (
            <select 
              value={world.id}
              onChange={(e) => {
                const w = allWorlds.find(w => w.id === e.target.value);
                if (w) onSelectWorld(w);
              }}
              className="bg-transparent text-cyan-500 font-bold tracking-widest uppercase focus:outline-none appearance-none"
            >
              {allWorlds.map(w => (
                <option key={w.id} value={w.id} className="bg-zinc-900">{w.name}</option>
              ))}
            </select>
          ) : (
            <h1 className="text-cyan-500 font-bold tracking-widest uppercase">{world.name}</h1>
          )}
        </div>
        
        <div className="flex space-x-4 text-xs tracking-wider text-zinc-400 border-l border-zinc-800 pl-6">
          <div>
            <span className="text-zinc-600">DAY</span> <span className="text-zinc-200">{day.toString().padStart(4, '0')}</span>
          </div>
          <div>
            <span className="text-zinc-600">HR</span> <span className="text-zinc-200">{hour.toString().padStart(2, '0')}:00</span>
          </div>
          <div>
            <span className="text-zinc-600">TICK</span> <span className="text-zinc-200">{world.tick}</span>
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-2">
          <span className="text-xs text-zinc-600 tracking-wider uppercase">Status</span>
          <span className={`text-xs px-2 py-0.5 rounded-sm uppercase tracking-wider ${
            isRunning ? 'bg-green-500/10 text-green-500 border border-green-500/20' : 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
          }`}>
            {isRunning ? 'Running' : 'Paused'}
          </span>
        </div>

        <div className="flex bg-zinc-900 border border-zinc-800 rounded-md overflow-hidden p-1 space-x-1">
          <button 
            onClick={() => onControl("start")}
            className="px-3 py-1 text-xs hover:bg-zinc-800 hover:text-white transition-colors uppercase tracking-wider rounded-sm text-zinc-400"
          >
            Start
          </button>
          <button 
            onClick={() => onControl("pause")}
            className="px-3 py-1 text-xs hover:bg-zinc-800 hover:text-white transition-colors uppercase tracking-wider rounded-sm text-zinc-400"
          >
            Pause
          </button>
          <button 
            onClick={() => onControl("tick")}
            className="px-3 py-1 text-xs hover:bg-zinc-800 hover:text-white transition-colors uppercase tracking-wider rounded-sm text-zinc-400"
          >
            Step
          </button>
          <button 
            onClick={() => onControl("advance")}
            className="px-3 py-1 text-xs hover:bg-zinc-800 hover:text-white transition-colors uppercase tracking-wider rounded-sm text-zinc-400"
          >
            +10
          </button>
          
          {onIntervene && (
            <button 
              onClick={onIntervene}
              className="px-3 py-1 text-xs bg-red-900/30 text-red-400 hover:bg-red-900/60 hover:text-red-100 transition-colors uppercase tracking-wider rounded-sm ml-4 border border-red-900/50"
            >
              Intervene
            </button>
          )}

          <button 
            onClick={handleBranch}
            disabled={isBranching}
            className="px-3 py-1 text-xs bg-indigo-900/30 text-indigo-400 hover:bg-indigo-900/60 hover:text-indigo-100 transition-colors uppercase tracking-wider rounded-sm ml-1 border border-indigo-900/50"
          >
            {isBranching ? 'Branching...' : 'Branch CF'}
          </button>
          
          {onCompare && allWorlds && allWorlds.length > 1 && (
            <select
              value={isComparing ? "comparing" : ""}
              onChange={(e) => {
                if (e.target.value) onCompare(e.target.value);
                else onCompare("");
              }}
              className="px-2 py-1 text-xs bg-zinc-900 text-zinc-400 border border-zinc-800 rounded-sm focus:outline-none ml-1 uppercase"
            >
              <option value="">Compare...</option>
              {allWorlds.filter(w => w.id !== world.id).map(w => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </select>
          )}
        </div>
      </div>
    </div>
  );
}
