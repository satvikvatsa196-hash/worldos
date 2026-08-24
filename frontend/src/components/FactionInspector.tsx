"use client";

import { useEffect, useState } from "react";
import { fetchFactionDetails } from "../lib/api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, RadialBarChart, RadialBar, Legend } from "recharts";

export function FactionInspector({ worldId, factionId, onSelectEntity, onClose }: { worldId: string, factionId: string, onSelectEntity: (e: any) => void, onClose: () => void }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchFactionDetails(worldId, factionId).then(d => {
      if (active) {
        setData(d);
        setLoading(false);
      }
    }).catch(e => {
      console.error(e);
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [worldId, factionId]);

  if (loading) {
    return <div className="p-8 text-center text-indigo-500 font-mono text-xs uppercase animate-pulse">Decrypting Faction Logs...</div>;
  }

  if (!data) {
    return <div className="p-8 text-center text-red-500 font-mono text-xs">Error retrieving faction data.</div>;
  }

  const influenceData = [
    { name: 'Power', value: data.power, fill: '#ec4899' },
    { name: 'Wealth', value: data.wealth, fill: '#10b981' },
    { name: 'Influence', value: data.influence, fill: '#6366f1' },
  ];

  return (
    <div className="flex flex-col h-full bg-zinc-950 font-mono">
      <div className="p-3 border-b border-zinc-800 uppercase text-xs font-bold tracking-widest text-zinc-500 flex justify-between shrink-0 sticky top-0 bg-zinc-950 z-10">
        <span>Faction Intelligence</span>
        <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">×</button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar space-y-6">
        
        {/* OVERVIEW */}
        <div>
          <div className="text-xs text-zinc-500 uppercase tracking-widest">Organization</div>
          <div className="text-xl text-indigo-400 font-bold tracking-wider">{data.name}</div>
          <div className="text-zinc-400 text-xs mt-1">{data.type} • {data.ideology}</div>
          
          <div className="grid grid-cols-2 gap-4 mt-4 bg-zinc-900 border border-zinc-800 p-3 rounded">
            <div>
              <div className="text-[10px] text-zinc-500 uppercase">Leader</div>
              {data.leader ? (
                <div 
                  className="text-xs text-cyan-400 cursor-pointer hover:underline truncate"
                  onClick={() => onSelectEntity({ type: 'character', id: data.leader.id })}
                >
                  {data.leader.name}
                </div>
              ) : (
                <div className="text-xs text-zinc-500">Decentralized</div>
              )}
            </div>
            <div>
              <div className="text-[10px] text-zinc-500 uppercase">Members</div>
              <div className="text-xs text-zinc-300 font-mono">{data.members.length} Active</div>
            </div>
            <div>
              <div className="text-[10px] text-zinc-500 uppercase">Treasury</div>
              <div className="text-xs text-emerald-400 font-mono">${data.wealth.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-[10px] text-zinc-500 uppercase">Power Projection</div>
              <div className="text-xs text-pink-400 font-mono">{data.power.toFixed(1)}</div>
            </div>
          </div>
        </div>

        {/* VISUALIZATIONS */}
        <div className="space-y-3">
          <div className="text-xs uppercase text-zinc-500 font-bold tracking-widest border-b border-zinc-800 pb-1">Strategic Metrics</div>
          <div className="grid grid-cols-1 gap-4">
            <div className="bg-zinc-900 border border-zinc-800 p-2 rounded h-40 flex flex-col">
              <span className="text-[10px] text-zinc-500 uppercase text-center mb-1">Influence Profile</span>
              <div className="flex-1 w-full min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={influenceData} layout="vertical" margin={{ top: 0, right: 20, left: -20, bottom: 0 }}>
                    <XAxis type="number" hide />
                    <YAxis dataKey="name" type="category" tick={{ fontSize: 10, fill: '#71717a' }} axisLine={false} tickLine={false} width={80} />
                    <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', fontSize: '10px' }} itemStyle={{ color: '#d4d4d8' }} />
                    <Bar dataKey="value" radius={[0, 2, 2, 0]} barSize={12} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>

        {/* MEMBERS */}
        <div className="space-y-3">
          <div className="text-xs uppercase text-zinc-500 font-bold tracking-widest border-b border-zinc-800 pb-1">Known Operatives</div>
          <div className="space-y-2 max-h-48 overflow-y-auto custom-scrollbar pr-2">
            {data.members.length === 0 ? <div className="text-xs text-zinc-600 italic">No registered operatives.</div> : data.members.map((m: any) => (
              <div 
                key={m.id} 
                className="bg-zinc-900 border border-zinc-800 p-2 rounded text-xs flex justify-between items-center cursor-pointer hover:border-cyan-500 transition-colors"
                onClick={() => onSelectEntity({ type: 'character', id: m.id })}
              >
                <div>
                  <div className="text-cyan-400 font-bold">{m.name}</div>
                  <div className="text-[10px] text-zinc-500">{m.occupation}</div>
                </div>
                <div className="text-emerald-500 font-mono text-[10px]">${m.wealth.toFixed(0)}</div>
              </div>
            ))}
          </div>
        </div>

        {/* GOALS & RELATIONSHIPS */}
        <div className="grid grid-cols-1 gap-6">
          <div className="space-y-3">
            <div className="text-xs uppercase text-zinc-500 font-bold tracking-widest border-b border-zinc-800 pb-1">Strategic Objectives</div>
            <div className="space-y-2">
              {data.goals.length === 0 ? <div className="text-xs text-zinc-600 italic">No stated objectives.</div> : data.goals.map((g: any, i: number) => (
                <div key={i} className="bg-zinc-900 border-l-2 border-indigo-500 p-2 text-xs flex justify-between items-center">
                  <span className="text-zinc-300 capitalize">{g.type.replace('_', ' ')}</span>
                  <span className="text-[10px] bg-indigo-500/10 text-indigo-400 px-1 rounded">{g.status}</span>
                </div>
              ))}
            </div>
          </div>
          
          <div className="space-y-3">
            <div className="text-xs uppercase text-zinc-500 font-bold tracking-widest border-b border-zinc-800 pb-1">Faction Relations</div>
            <div className="space-y-2">
              {data.relationships.length === 0 ? <div className="text-xs text-zinc-600 italic">No formal treaties or rivalries.</div> : data.relationships.map((r: any, i: number) => (
                <div key={i} className="text-xs text-zinc-400">Relation recorded.</div>
              ))}
            </div>
          </div>
        </div>

        {/* DECISIONS & ACTIVITY */}
        <div className="space-y-3">
          <div className="text-xs uppercase text-zinc-500 font-bold tracking-widest border-b border-zinc-800 pb-1">Organizational Decisions</div>
          <div className="space-y-3">
            {data.decisions.length === 0 ? <div className="text-xs text-zinc-600 italic">No decisions logged.</div> : data.decisions.map((d: any) => {
              const act = d.action || {};
              return (
                <div key={d.id} className="bg-zinc-900 border border-zinc-800 p-3 rounded space-y-2 text-xs">
                  <div className="flex justify-between items-center border-b border-zinc-800 pb-1">
                    <span className="text-zinc-500 font-mono text-[10px]">TICK {d.tick}</span>
                    <span className="text-indigo-400 font-mono text-[10px]">CONF {(d.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-zinc-500 uppercase block mb-0.5">Directive</span>
                    <span className="text-emerald-400 font-bold">[{act.selected_action || "EXECUTE"}]</span> <span className="text-zinc-300">{d.decision_summary}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        
        <div className="space-y-3">
          <div className="text-xs uppercase text-zinc-500 font-bold tracking-widest border-b border-zinc-800 pb-1">Recent Actions (Events)</div>
          <div className="space-y-2">
            {data.recent_actions.length === 0 ? <div className="text-xs text-zinc-600 italic">No recent events.</div> : data.recent_actions.map((e: any) => (
              <div key={e.id} className="text-[10px] bg-zinc-900 border border-zinc-800 p-2 rounded cursor-pointer hover:border-zinc-600" onClick={() => onSelectEntity({...e, entity_type: 'event'})}>
                <div className="text-zinc-500 font-mono mb-0.5">TICK {e.tick} | {e.type}</div>
                <div className="text-zinc-300 truncate">{e.description}</div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
