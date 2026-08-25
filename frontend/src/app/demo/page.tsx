"use client";

import { useEffect, useState, useRef } from "react";
import { generateWorld, fetchWorldState, controlSimulation, fetchCausalChain, WS_BASE, API_BASE } from "../../lib/api";
import { CausalGraph } from "../../components/CausalGraph";

export default function DemoMode() {
  const [worldId, setWorldId] = useState<string | null>(null);
  const [worldState, setWorldState] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [majorEvent, setMajorEvent] = useState<any>(null);
  const [causalChain, setCausalChain] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const [inspectMode, setInspectMode] = useState<"none" | "character" | "faction" | "city" | "economy">("none");
  const [inspectEventId, setInspectEventId] = useState<string | null>(null);
  const [autoRun, setAutoRun] = useState(true);
  
  useEffect(() => {
    initDemo();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  useEffect(() => {
    let interval: any;
    if (autoRun && worldId && !majorEvent) {
      interval = setInterval(() => {
        controlSimulation(worldId, "tick").then(res => {
          setTick(res.current_tick);
        }).catch(console.error);
      }, 2000); // Slow enough to observe
    }
    return () => clearInterval(interval);
  }, [autoRun, worldId, majorEvent]);

  const initDemo = async () => {
    setLoading(true);
    try {
      const res = await generateWorld("grain_crisis");
      setWorldId(res.world_id);
      
      const state = await fetchWorldState(res.world_id);
      setWorldState(state);
      
      connectWebSocket(res.world_id);
      await controlSimulation(res.world_id, "start");
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const [wsStatus, setWsStatus] = useState<string>("Disconnected");

  const connectWebSocket = (id: string) => {
    try {
      setWsStatus(`Connecting to ${WS_BASE}/worlds/${id}...`);
      const ws = new WebSocket(`${WS_BASE}/worlds/${id}`);
      ws.onopen = () => setWsStatus("Connected!");
      ws.onerror = (err) => {
        console.error("WS Error", err);
        setWsStatus("Error connecting to WebSocket");
      };
      ws.onclose = (e) => {
        console.warn(`WebSocket Closed. Code: ${e.code}, Reason: ${e.reason}`);
        setWsStatus(`Closed (${e.code})`);
      };
      ws.onmessage = (event) => {
        try {
          console.log("Received WS message:", event.data);
          const data = JSON.parse(event.data);
          setEvents(prev => [data, ...prev].slice(0, 50));
          
          // Highlight major events
          const evtType = data.type?.toUpperCase() || "";
          if (evtType === "ECONOMIC_CRASH" || evtType === "RESOURCE_SHORTAGE" || evtType === "PROTEST" || data.payload?.is_major) {
            handleMajorEvent(id, data);
          }
        } catch (e) {
          console.error("Failed to parse WS message", e);
        }
      };
      wsRef.current = ws;
    } catch (e) {
      console.error("Failed to setup WebSocket", e);
      setWsStatus("Error connecting to WebSocket");
    }
  };

  const handleMajorEvent = async (wid: string, eventData: any) => {
    setMajorEvent(eventData);
    setAutoRun(false); // Pause to show event
    try {
      await new Promise(resolve => setTimeout(resolve, 500)); // Wait for tick to commit
      const chain = await fetchCausalChain(wid, eventData.id);
      setCausalChain(chain);
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen bg-black items-center justify-center font-mono text-cyan-400 flex-col">
        <div className="text-4xl mb-4 tracking-widest font-bold animate-pulse">INITIALIZING THE GRAIN CRISIS</div>
        <div className="text-zinc-500">Generating carefully balanced deterministic state...</div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-zinc-950 text-white font-mono overflow-hidden">
      {inspectEventId && worldId && worldState && (
        <CausalGraph 
          worldId={worldId} 
          eventId={inspectEventId} 
          characters={worldState.characters || []} 
          cities={worldState.cities || []} 
          factions={worldState.factions || []} 
          onSelectEntity={() => {}} 
          onClose={() => setInspectEventId(null)} 
        />
      )}

      {/* LEFT PANEL: Simulation State */}
      <div className="w-1/4 border-r border-zinc-800 p-6 flex flex-col bg-zinc-900/50 backdrop-blur-md">
        <h1 className="text-2xl font-bold tracking-widest text-cyan-400 mb-8 uppercase">WORLDOS<br/><span className="text-xs text-zinc-500">Demo Mode</span></h1>
        
        <div className="mb-6 bg-zinc-900 p-4 rounded border border-zinc-800">
          <div className="text-zinc-500 text-xs mb-1 uppercase tracking-widest">Global Status</div>
          <div className="text-3xl font-light tracking-wider">TICK {tick}</div>
          <div className="text-xs text-amber-500 mt-2 uppercase tracking-widest bg-amber-500/10 inline-block px-2 py-1 rounded">Scenario: The Grain Crisis</div>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar space-y-6">
          {(inspectMode === "city" || inspectMode === "none") && worldState?.cities.map((city: any) => (
            <div key={city.id} className="border border-zinc-800 rounded p-4 bg-zinc-950/50 animate-in fade-in">
              <div className="font-bold text-lg mb-2 text-zinc-300">{city.name}</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div><span className="text-zinc-500">POP:</span> {city.population}</div>
                <div><span className="text-zinc-500">WEALTH:</span> {Math.round(city.wealth)}</div>
                <div>
                  <span className="text-zinc-500">FOOD:</span> 
                  <span className={city.food_supply < city.population ? "text-red-500 ml-1" : "text-green-500 ml-1"}>
                    {Math.round(city.food_supply)}
                  </span>
                </div>
                <div>
                  <span className="text-zinc-500">UNREST:</span> 
                  <span className={city.unrest > 0.6 ? "text-red-500 ml-1" : "text-zinc-300 ml-1"}>
                    {(city.unrest * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>
          ))}

          {inspectMode === "faction" && worldState?.factions.map((faction: any) => (
            <div key={faction.id} className="border border-zinc-800 rounded p-4 bg-zinc-950/50 animate-in fade-in">
              <div className="font-bold text-lg mb-2 text-zinc-300">{faction.name}</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div><span className="text-zinc-500">TYPE:</span> {faction.type}</div>
                <div><span className="text-zinc-500">WEALTH:</span> {Math.round(faction.wealth)}</div>
                <div className="col-span-2">
                  <span className="text-zinc-500">INFLUENCE:</span> 
                  <span className="text-zinc-300 ml-1">{faction.power?.toFixed(0)}%</span>
                </div>
              </div>
            </div>
          ))}

          <div className="border border-zinc-800 rounded p-4 bg-zinc-950/50 mt-6">
             <div className="text-zinc-500 text-xs mb-2 uppercase tracking-widest">Market Prices</div>
             {worldState?.resources.map((res: any) => (
               <div key={res.id} className="flex justify-between items-center text-sm py-1 border-b border-zinc-800/50 last:border-0">
                 <span className={res.name === "Food" ? "text-amber-400 font-bold" : "text-zinc-400"}>{res.name}</span>
                 <span className="font-mono">{res.price.toFixed(2)} ¢</span>
               </div>
             ))}
          </div>
        </div>
      </div>

      {/* MAIN PANEL */}
      <div className="flex-1 relative bg-black flex flex-col">
        {/* Background visualizer */}
        <div className="absolute inset-0 opacity-20 pointer-events-none" style={{ backgroundImage: 'radial-gradient(circle at 50% 50%, #0891b2 0%, #000 70%)'}}></div>
        
        <div className="flex-1 p-8 flex flex-col relative z-10">
          
          {!majorEvent ? (
            <div className="flex-1 flex flex-col items-center justify-center">
              <div className="w-64 h-64 border-4 border-zinc-800 rounded-full flex items-center justify-center mb-8 relative">
                <div className={`absolute inset-0 rounded-full border-t-4 border-cyan-500 ${autoRun ? 'animate-spin' : ''}`}></div>
                <div className="text-zinc-500 tracking-widest text-sm uppercase">
                  {autoRun ? "Simulating" : "Paused"}
                </div>
              </div>
              <button 
                onClick={() => setAutoRun(!autoRun)}
                className="px-6 py-2 border border-zinc-700 hover:bg-zinc-800 transition-colors uppercase tracking-widest text-xs"
              >
                {autoRun ? "Pause Simulation" : "Resume Simulation"}
              </button>
            </div>
          ) : (
            <div className="flex-1 flex flex-col bg-zinc-950/90 border border-amber-500/30 rounded-lg p-8 shadow-[0_0_50px_rgba(245,158,11,0.1)] backdrop-blur-xl animate-in fade-in zoom-in duration-500 overflow-hidden">
              <div className="text-amber-500 text-sm font-bold tracking-widest uppercase mb-2">Critical Simulation Event</div>
              <h2 className="text-4xl font-bold text-white mb-8">{majorEvent.type.replace(/([A-Z])/g, ' $1').trim().toUpperCase()}</h2>
              
              <div className="grid grid-cols-2 gap-12 flex-1 overflow-hidden">
                <div className="space-y-6 overflow-y-auto custom-scrollbar pr-4">
                  <div>
                    <div className="text-zinc-500 text-xs uppercase tracking-widest mb-1">Event</div>
                    <div className="text-lg text-zinc-300 font-bold">
                      {majorEvent.payload?.event_name || majorEvent.type}
                    </div>
                  </div>
                  
                  <div>
                    <div className="text-zinc-500 text-xs uppercase tracking-widest mb-1">Actor</div>
                    <div className="text-lg text-cyan-400">
                      {majorEvent.actor_id || "World Simulation Engine"}
                    </div>
                  </div>

                  <div>
                    <div className="text-zinc-500 text-xs uppercase tracking-widest mb-1">Decision</div>
                    <div className="text-md text-zinc-300 bg-zinc-900/50 p-4 rounded border border-zinc-800 italic">
                      "{majorEvent.payload?.decision_summary || "An autonomous system action was executed."}"
                    </div>
                  </div>
                  
                  {causalChain && causalChain.ancestors.length > 0 && (
                    <div className="space-y-4 pt-4 border-t border-zinc-800">
                       <div className="text-amber-500/80 text-xs uppercase tracking-widest">Cause (Causal Chain)</div>
                       <div className="space-y-2">
                         {causalChain.ancestors.slice(-4).reverse().map((anc: any, i: number) => (
                           <div key={anc.id} className="pl-4 border-l-2 border-zinc-700 py-1 relative">
                             <div className="absolute w-2 h-2 rounded-full bg-amber-500/50 -left-[5px] top-3"></div>
                             <div className="text-[10px] text-zinc-500 mb-1">which resulted from (Tick {anc.tick}):</div>
                             <div className="text-sm text-zinc-300">{anc.type.replace(/([A-Z])/g, ' $1').trim()} - {anc.payload?.decision_summary || "Autonomous action"}</div>
                           </div>
                         ))}
                       </div>
                    </div>
                  )}
                </div>
                
                <div className="flex flex-col">
                   <div className="text-zinc-500 text-xs uppercase tracking-widest mb-4">Consequences & Data</div>
                   <div className="flex-1 bg-zinc-900/50 border border-zinc-800 rounded p-4 overflow-y-auto custom-scrollbar">
                     <pre className="text-xs text-amber-500/80 font-mono whitespace-pre-wrap">
                       {JSON.stringify(majorEvent.payload || majorEvent, null, 2)}
                     </pre>
                   </div>
                </div>
              </div>
              
              <div className="mt-8 flex justify-end space-x-4">
                <button 
                  onClick={() => setInspectEventId(majorEvent.id)}
                  className="px-8 py-3 bg-indigo-500/10 text-indigo-400 border border-indigo-500/50 hover:bg-indigo-500/20 transition-colors tracking-widest uppercase text-sm font-bold"
                >
                  Inspect Causal Graph
                </button>
                <button 
                  onClick={() => {
                    setMajorEvent(null);
                    setAutoRun(true);
                  }}
                  className="px-8 py-3 bg-amber-500/10 text-amber-500 border border-amber-500/50 hover:bg-amber-500/20 transition-colors tracking-widest uppercase text-sm font-bold"
                >
                  Acknowledge & Resume
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* RIGHT PANEL: Live Events Log */}
      <div className="w-1/4 border-l border-zinc-800 bg-zinc-950 flex flex-col">
        <div className="p-4 border-b border-zinc-800">
          <div className="flex justify-between items-center mb-2">
            <div className="text-zinc-500 text-xs uppercase tracking-widest">Live Telemetry</div>
            <div className={`text-[10px] uppercase px-2 py-1 rounded ${wsStatus === "Connected!" ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>{wsStatus}</div>
          </div>
          <div className="flex space-x-2">
            <button onClick={() => setInspectMode(inspectMode === "city" ? "none" : "city")} className={`flex-1 py-1 text-xs uppercase border ${inspectMode === "city" ? "border-cyan-500 text-cyan-500" : "border-zinc-800 text-zinc-500 hover:text-zinc-300"}`}>Cities</button>
            <button onClick={() => setInspectMode(inspectMode === "faction" ? "none" : "faction")} className={`flex-1 py-1 text-xs uppercase border ${inspectMode === "faction" ? "border-cyan-500 text-cyan-500" : "border-zinc-800 text-zinc-500 hover:text-zinc-300"}`}>Factions</button>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-2">
          {events.map((evt, i) => (
            <div key={i} className="text-xs p-3 border-l-2 border-zinc-800 bg-zinc-900/30 hover:bg-zinc-900/80 transition-colors cursor-pointer" onClick={() => handleMajorEvent(worldId!, evt)}>
              <div className="flex justify-between text-zinc-600 mb-1">
                <span>Tick {evt.tick}</span>
                <span>{evt.type}</span>
              </div>
              <div className="text-zinc-300 truncate">{evt.payload?.reason || evt.payload?.decision_summary || evt.type || "System Event"}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
