"use client";

function calculateTime(tick: number) {
  const hoursPerTick = 1;
  const totalHours = tick * hoursPerTick;
  const day = Math.floor(totalHours / 24) + 1;
  const hour = totalHours % 24;
  return { day, hour };
}

export function TopPanel({ worldState, onControl }: { worldState: any, onControl: (action: "start" | "pause" | "tick" | "advance") => void }) {
  const { world } = worldState;
  const { day, hour } = calculateTime(world.tick);
  
  const isRunning = world.status === "running";

  return (
    <div className="h-14 border-b border-zinc-800 bg-zinc-950 flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse"></div>
          <h1 className="text-cyan-500 font-bold tracking-widest uppercase">{world.name}</h1>
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
        </div>
      </div>
    </div>
  );
}
