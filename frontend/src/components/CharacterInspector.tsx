"use client";

import { useEffect, useState } from "react";
import { fetchCharacterDetails } from "../lib/api";

export function CharacterInspector({ worldId, characterId, onSelectEntity, onClose }: { worldId: string, characterId: string, onSelectEntity: (e: any) => void, onClose: () => void }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchCharacterDetails(worldId, characterId).then(d => {
      if (active) {
        setData(d);
        setLoading(false);
      }
    }).catch(e => {
      console.error(e);
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [worldId, characterId]);

  if (loading) {
    return <div className="p-8 text-center text-zinc-500 font-mono text-xs uppercase animate-pulse">Scanning Bio-Signatures...</div>;
  }

  if (!data) {
    return <div className="p-8 text-center text-red-500 font-mono text-xs">Error retrieving character profile.</div>;
  }

  const renderBar = (value: number, color: string = "bg-green-500") => (
    <div className="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden flex">
      <div className={`${color} h-full`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );

  return (
    <div className="flex flex-col h-full bg-zinc-950 font-mono">
      <div className="p-3 border-b border-zinc-800 uppercase text-xs font-bold tracking-widest text-zinc-500 flex justify-between shrink-0 sticky top-0 bg-zinc-950 z-10">
        <span>Agent Profile</span>
        <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">×</button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar space-y-6">
        
        {/* OVERVIEW */}
        <div>
          <div className="text-xs text-zinc-500 uppercase tracking-widest">Subject</div>
          <div className="text-xl text-cyan-400 font-bold tracking-wider">{data.name}</div>
          <div className="text-zinc-400 text-xs mt-1">{data.occupation} • {data.status}</div>
          
          <div className="grid grid-cols-2 gap-4 mt-4 bg-zinc-900 border border-zinc-800 p-3 rounded">
            <div>
              <div className="text-[10px] text-zinc-500 uppercase">Location</div>
              <div 
                className="text-xs text-indigo-400 cursor-pointer hover:underline"
                onClick={() => data.city && onSelectEntity({ type: 'city', id: data.city.id })}
              >
                {data.city?.name || "Nomadic"}
              </div>
            </div>
            <div>
              <div className="text-[10px] text-zinc-500 uppercase">Affiliation</div>
              <div className="text-xs text-zinc-300">{data.faction?.name || "Independent"}</div>
            </div>
            <div>
              <div className="text-[10px] text-zinc-500 uppercase">Wealth</div>
              <div className="text-xs text-emerald-400 font-mono">${data.wealth.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-[10px] text-zinc-500 uppercase">Health</div>
              <div className="text-xs text-zinc-300 font-mono">{data.health.toFixed(1)}%</div>
            </div>
          </div>
        </div>

        {/* NEEDS */}
        <div className="space-y-3">
          <div className="text-xs uppercase text-zinc-500 font-bold tracking-widest border-b border-zinc-800 pb-1">Hierarchy of Needs</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            {Object.entries(data.needs || {}).map(([need, val]) => (
              <div key={need}>
                <div className="flex justify-between text-[10px] uppercase mb-1">
                  <span className="text-zinc-400">{need}</span>
                  <span className="text-zinc-500 font-mono">{(val as number).toFixed(0)}</span>
                </div>
                {renderBar(val as number, (val as number) < 30 ? 'bg-red-500' : 'bg-cyan-500')}
              </div>
            ))}
          </div>
        </div>

        {/* PERSONALITY */}
        <div className="space-y-3">
          <div className="text-xs uppercase text-zinc-500 font-bold tracking-widest border-b border-zinc-800 pb-1">Personality Matrix</div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(data.personality || {}).map(([k, v]) => {
              if (k === 'needs') return null;
              return (
                <div key={k} className="bg-zinc-900 border border-zinc-800 px-2 py-1 rounded text-[10px] flex space-x-2">
                  <span className="text-zinc-500 uppercase">{k}</span>
                  <span className="text-zinc-300">{typeof v === 'number' ? v.toFixed(2) : String(v)}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* GOALS */}
        <div className="space-y-3">
          <div className="text-xs uppercase text-zinc-500 font-bold tracking-widest border-b border-zinc-800 pb-1">Active Directives (Goals)</div>
          <div className="space-y-2">
            {data.goals.length === 0 ? <div className="text-xs text-zinc-600 italic">No active goals.</div> : data.goals.sort((a:any,b:any) => b.priority - a.priority).map((g: any) => (
              <div key={g.id} className="bg-zinc-900 border border-zinc-800 p-2 rounded flex justify-between items-center">
                <span className="text-xs text-zinc-300">{g.description}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${g.status === 'active' ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' : 'text-zinc-500'}`}>
                  {g.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* BELIEFS */}
        <div className="space-y-3">
          <div className="text-xs uppercase text-zinc-500 font-bold tracking-widest border-b border-zinc-800 pb-1">Core Beliefs</div>
          <div className="space-y-2">
            {data.beliefs.length === 0 ? <div className="text-xs text-zinc-600 italic">No strong beliefs formed.</div> : data.beliefs.map((b: any) => (
              <div key={b.id} className="bg-zinc-900 border border-zinc-800 p-2 rounded text-xs flex justify-between">
                <span className="text-zinc-300">{b.belief_type} regarding {b.subject_type}</span>
                <span className="text-zinc-500 font-mono">Val: {b.value.toFixed(1)} | Conf: {b.confidence.toFixed(1)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* RELATIONSHIPS */}
        <div className="space-y-3">
          <div className="text-xs uppercase text-zinc-500 font-bold tracking-widest border-b border-zinc-800 pb-1">Social Graph</div>
          <div className="space-y-2">
            {data.relationships.length === 0 ? <div className="text-xs text-zinc-600 italic">No relationships recorded.</div> : data.relationships.map((r: any) => (
              <div 
                key={r.id} 
                className="bg-zinc-900 border border-zinc-800 p-2 rounded text-xs cursor-pointer hover:border-indigo-500 transition-colors"
                onClick={() => onSelectEntity({ type: 'character', id: r.target_id })}
              >
                <div className="text-indigo-400 font-bold mb-1">Target ID: {r.target_id.split('-')[0]}...</div>
                <div className="flex space-x-3 text-[10px] font-mono text-zinc-400">
                  <span>TRU {r.trust.toFixed(1)}</span>
                  <span>RES {r.respect.toFixed(1)}</span>
                  <span>FRN {r.friendship.toFixed(1)}</span>
                  <span>FER {r.fear.toFixed(1)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* MEMORIES */}
        <div className="space-y-3">
          <div className="text-xs uppercase text-zinc-500 font-bold tracking-widest border-b border-zinc-800 pb-1">Memory Banks</div>
          <div className="space-y-2">
            {data.memories.length === 0 ? <div className="text-xs text-zinc-600 italic">Memory banks empty.</div> : data.memories.sort((a:any, b:any) => b.tick - a.tick).map((m: any) => (
              <div key={m.id} className="bg-zinc-900 border-l-2 border-indigo-500 p-2 text-xs">
                <div className="text-zinc-500 font-mono text-[10px] mb-1">TICK {m.tick} | IMP {m.importance.toFixed(1)} | {m.type}</div>
                <div className="text-zinc-300 italic">"{m.summary}"</div>
              </div>
            ))}
          </div>
        </div>

        {/* RECENT DECISIONS */}
        <div className="space-y-3">
          <div className="text-xs uppercase text-zinc-500 font-bold tracking-widest border-b border-zinc-800 pb-1">Cognitive Decisions</div>
          <div className="space-y-3">
            {data.decisions.length === 0 ? <div className="text-xs text-zinc-600 italic">No cognitive decisions logged.</div> : data.decisions.sort((a:any, b:any) => b.tick - a.tick).map((d: any) => {
              const act = d.action || {};
              return (
                <div key={d.id} className="bg-zinc-900 border border-zinc-800 p-3 rounded space-y-2 text-xs">
                  <div className="flex justify-between items-center border-b border-zinc-800 pb-1">
                    <span className="text-zinc-500 font-mono text-[10px]">TICK {d.tick}</span>
                    <span className="text-cyan-500 font-mono text-[10px]">CONF {(d.confidence * 100).toFixed(0)}%</span>
                  </div>
                  
                  {act.situation_summary && (
                    <div>
                      <span className="text-[10px] text-zinc-500 uppercase block mb-0.5">Situation</span>
                      <span className="text-zinc-300">{act.situation_summary}</span>
                    </div>
                  )}
                  
                  {act.goal && (
                    <div>
                      <span className="text-[10px] text-zinc-500 uppercase block mb-0.5">Target Goal</span>
                      <span className="text-zinc-300">{act.goal}</span>
                    </div>
                  )}
                  
                  <div>
                    <span className="text-[10px] text-zinc-500 uppercase block mb-0.5">Decision</span>
                    <span className="text-emerald-400 font-bold">[{act.selected_action || "THINK"}]</span> <span className="text-zinc-300">{d.decision_summary}</span>
                  </div>
                  
                  {act.result && (
                    <div>
                      <span className="text-[10px] text-zinc-500 uppercase block mb-0.5">Expected Result</span>
                      <span className="text-zinc-400 italic">{act.result}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

      </div>
    </div>
  );
}
