"use client";

import { useEffect, useState, useMemo } from "react";
import ReactFlow, { Background, Controls, Node, Edge } from "reactflow";
import "reactflow/dist/style.css";
import { fetchCausalChain } from "../lib/api";

export function CausalGraph({ worldId, eventId, onSelectEntity, onClose, characters, cities, factions }: { worldId: string, eventId: string, onSelectEntity: (e: any) => void, onClose: () => void, characters: any[], cities: any[], factions: any[] }) {
  const [data, setData] = useState<{ selected_event: any, ancestors: any[], descendants: any[] } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchCausalChain(worldId, eventId).then(d => {
      if (active) {
        setData(d);
        setLoading(false);
      }
    }).catch(e => {
      console.error(e);
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [worldId, eventId]);

  const { nodes, edges } = useMemo(() => {
    if (!data) return { nodes: [], edges: [] };
    
    const nds: Node[] = [];
    const egs: Edge[] = [];
    
    let yPos = 50;
    const xPos = 250;
    const ySpacing = 120;

    const createNode = (evt: any, isTarget: boolean, index: number) => {
      // Resolve names
      const actor = characters.find(c => c.id === evt.actor_id)?.name || evt.actor_id;
      const target = characters.find(c => c.id === evt.target_id)?.name || evt.target_id;
      const desc = evt.payload?.decision_summary || evt.description || evt.type;
      
      const node: Node = {
        id: evt.id,
        position: { x: xPos, y: yPos + (index * ySpacing) },
        data: { 
          label: (
            <div className="flex flex-col text-left p-1 w-64">
              <div className="flex justify-between items-center mb-1 border-b border-zinc-800 pb-1">
                <span className="text-[10px] font-mono text-zinc-500">TICK {evt.tick}</span>
                <span className="text-[10px] uppercase text-cyan-500 font-bold tracking-widest">{evt.type}</span>
              </div>
              <div className="text-xs text-zinc-200 mt-1">{desc}</div>
              {actor && <div className="text-[10px] text-zinc-500 mt-2">Actor: <span className="text-indigo-400">{actor}</span></div>}
              {target && target !== actor && <div className="text-[10px] text-zinc-500">Target: <span className="text-pink-400">{target}</span></div>}
            </div>
          ) 
        },
        style: {
          background: isTarget ? '#18181b' : '#09090b',
          color: '#e4e4e7',
          border: isTarget ? '2px solid #06b6d4' : '1px solid #3f3f46',
          borderRadius: '6px',
          boxShadow: isTarget ? '0 0 20px rgba(6, 182, 212, 0.2)' : 'none',
        }
      };
      return node;
    };

    let currentIndex = 0;
    let prevId: string | null = null;

    // Ancestors
    data.ancestors.forEach((anc) => {
      nds.push(createNode(anc, false, currentIndex));
      if (prevId) {
        egs.push({
          id: `edge-${prevId}-${anc.id}`,
          source: prevId,
          target: anc.id,
          animated: true,
          style: { stroke: '#71717a' },
          markerEnd: { type: 'arrow' as any, color: '#71717a' }
        });
      }
      prevId = anc.id;
      currentIndex++;
    });

    // Target
    nds.push(createNode(data.selected_event, true, currentIndex));
    if (prevId) {
      egs.push({
        id: `edge-${prevId}-${data.selected_event.id}`,
        source: prevId,
        target: data.selected_event.id,
        animated: true,
        style: { stroke: '#06b6d4', strokeWidth: 2 },
        markerEnd: { type: 'arrow' as any, color: '#06b6d4' }
      });
    }
    prevId = data.selected_event.id;
    currentIndex++;

    // Descendants (assuming a straight line for simplicity, ReactFlow can handle trees if mapped properly, but sequential is fine for this view)
    data.descendants.forEach((desc) => {
      nds.push(createNode(desc, false, currentIndex));
      if (prevId) {
        egs.push({
          id: `edge-${prevId}-${desc.id}`,
          source: prevId, // Note: In a true tree, this should link to desc.parent_event_id. For safety:
          target: desc.id,
          animated: true,
          style: { stroke: '#71717a' },
          markerEnd: { type: 'arrow' as any, color: '#71717a' }
        });
      }
      // Overwrite prevId only if it's a straight line, to handle trees correctly:
      prevId = desc.id; 
      currentIndex++;
    });
    
    // Correct edges for descendants based on parent_event_id directly
    const correctedEdges = egs.filter(e => !e.id.startsWith('edge-target')).map(e => e);
    // Actually, just rebuild edges cleanly using parent_event_id:
    const finalEdges: Edge[] = [];
    nds.forEach(n => {
      const evt = [...data.ancestors, data.selected_event, ...data.descendants].find(e => e.id === n.id);
      if (evt && evt.parent_event_id) {
        // If parent exists in nodes, draw edge
        if (nds.find(pn => pn.id === evt.parent_event_id)) {
          finalEdges.push({
            id: `edge-${evt.parent_event_id}-${evt.id}`,
            source: evt.parent_event_id,
            target: evt.id,
            animated: true,
            style: { stroke: evt.id === data.selected_event.id ? '#06b6d4' : '#52525b', strokeWidth: evt.id === data.selected_event.id ? 2 : 1 },
            markerEnd: { type: 'arrow' as any, color: evt.id === data.selected_event.id ? '#06b6d4' : '#52525b' }
          });
        }
      }
    });

    return { nodes: nds, edges: finalEdges };
  }, [data, characters]);

  const [viewMode, setViewMode] = useState<'graph' | 'investigate'>('graph');

  if (loading) {
    return <div className="absolute inset-0 bg-black/80 z-50 flex items-center justify-center text-zinc-500 font-mono text-xs uppercase animate-pulse">Tracing Causal Vectors...</div>;
  }

  if (!data) {
    return null;
  }

  // Build the reverse causal chain for investigation mode
  const buildInvestigationChain = () => {
    const chain = [data.selected_event];
    let currentParentId = data.selected_event.parent_event_id;
    
    // We traverse ancestors to find parents
    while (currentParentId) {
      const parent = data.ancestors.find(a => a.id === currentParentId);
      if (parent) {
        chain.push(parent);
        currentParentId = parent.parent_event_id;
      } else {
        break;
      }
    }
    return chain;
  };

  const getActorName = (id: string) => characters.find(c => c.id === id)?.name || factions.find(f => f.id === id)?.name || id;

  return (
    <div className="absolute inset-0 bg-zinc-950 z-50 flex flex-col font-mono">
      <div className="p-4 border-b border-zinc-800 flex justify-between items-center bg-black">
        <div>
          <div className="text-xs uppercase text-zinc-500 tracking-widest font-bold">Causal Investigation</div>
          <div className="text-cyan-400 font-bold text-sm tracking-widest mt-1">EVENT {eventId.split('-')[0]}</div>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex bg-zinc-900 border border-zinc-800 rounded overflow-hidden">
            <button 
              className={`px-4 py-2 text-[10px] uppercase tracking-widest font-bold transition-colors ${viewMode === 'graph' ? 'bg-indigo-600 text-white' : 'text-zinc-500 hover:text-zinc-300'}`}
              onClick={() => setViewMode('graph')}
            >
              Graph View
            </button>
            <button 
              className={`px-4 py-2 text-[10px] uppercase tracking-widest font-bold transition-colors ${viewMode === 'investigate' ? 'bg-indigo-600 text-white' : 'text-zinc-500 hover:text-zinc-300'}`}
              onClick={() => setViewMode('investigate')}
            >
              Investigation Mode
            </button>
          </div>
          <button onClick={onClose} className="bg-zinc-900 border border-zinc-800 text-zinc-300 px-4 py-2 text-xs uppercase tracking-widest hover:bg-zinc-800 hover:text-white transition-colors rounded">
            Close Analysis
          </button>
        </div>
      </div>
      
      <div className="flex-1 relative bg-zinc-900 overflow-y-auto">
        {viewMode === 'graph' ? (
          <>
            <ReactFlow 
              nodes={nodes} 
              edges={edges}
              fitView
              onNodeClick={(e, node) => {
                const evt = [...data.ancestors, data.selected_event, ...data.descendants].find(x => x.id === node.id);
                if (evt) onSelectEntity({ ...evt, entity_type: 'event' });
              }}
            >
              <Background color="#27272a" gap={20} size={1} />
              <Controls className="bg-zinc-800 border-zinc-700 fill-zinc-400" />
            </ReactFlow>

            <div className="absolute bottom-6 left-6 pointer-events-none bg-black/60 p-4 border border-zinc-800 rounded backdrop-blur">
              <div className="text-xs font-bold text-zinc-500 uppercase mb-2">Graph Legend</div>
              <div className="flex items-center space-x-2 text-[10px] text-zinc-300 mb-1">
                <div className="w-3 h-3 border-2 border-cyan-500 bg-zinc-900 rounded-sm"></div>
                <span>Selected Event</span>
              </div>
              <div className="flex items-center space-x-2 text-[10px] text-zinc-300">
                <div className="w-3 h-3 border border-zinc-700 bg-black rounded-sm"></div>
                <span>Causal Link</span>
              </div>
            </div>
          </>
        ) : (
          <div className="p-8 max-w-4xl mx-auto space-y-12 pb-24">
            <div className="text-center mb-12">
              <h2 className="text-2xl font-bold text-red-500 tracking-widest mb-2">WHY DID THIS HAPPEN?</h2>
              <p className="text-zinc-500 text-sm">Deterministic Root Cause Analysis</p>
            </div>
            
            <div className="space-y-2 text-center">
              <div className="text-xl text-cyan-400 font-bold uppercase">{data.selected_event.description || data.selected_event.type}</div>
              <div className="text-xs text-zinc-500">TICK {data.selected_event.tick} | ACTOR: {getActorName(data.selected_event.actor_id) || 'SYSTEM'}</div>
            </div>

            {buildInvestigationChain().slice(1).map((evt, index) => (
              <div key={evt.id} className="flex flex-col items-center">
                <div className="h-12 w-0.5 bg-zinc-700 mb-2"></div>
                <div className="text-xs font-bold text-zinc-600 mb-4 tracking-widest">WHY?</div>
                <div className="h-12 w-0.5 bg-zinc-700 mb-6"></div>
                
                <div className="bg-zinc-950 border border-zinc-800 p-6 rounded-lg w-full shadow-lg">
                  <div className="flex justify-between items-start border-b border-zinc-800 pb-4 mb-4">
                    <div>
                      <div className="text-sm font-bold text-indigo-400 uppercase">{evt.description || evt.type}</div>
                      <div className="text-[10px] text-zinc-500 mt-1">TICK {evt.tick}</div>
                    </div>
                    <div className="text-right text-xs">
                      <div className="text-zinc-400">Actor: <span className="text-zinc-200">{getActorName(evt.actor_id) || 'SYSTEM'}</span></div>
                      {evt.target_id && <div className="text-zinc-400">Target: <span className="text-zinc-200">{getActorName(evt.target_id)}</span></div>}
                    </div>
                  </div>
                  
                  {evt.payload?.decision_summary && (
                    <div className="mb-4">
                      <div className="text-[10px] uppercase text-zinc-500 font-bold tracking-widest mb-1">Agent Decision</div>
                      <div className="text-sm text-zinc-300 italic">"{evt.payload.decision_summary}"</div>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-4">
                    {evt.payload?.consequences && (
                      <div className="bg-zinc-900 border border-zinc-800 p-3 rounded">
                        <div className="text-[10px] uppercase text-zinc-500 font-bold mb-2">Effects</div>
                        <ul className="list-disc list-inside text-xs text-zinc-400 space-y-1">
                          {Array.isArray(evt.payload.consequences) ? 
                            evt.payload.consequences.map((c: any, i: number) => <li key={i}>{c}</li>) : 
                            <li>{JSON.stringify(evt.payload.consequences)}</li>}
                        </ul>
                      </div>
                    )}
                    
                    <div className="bg-zinc-900 border border-zinc-800 p-3 rounded">
                      <div className="text-[10px] uppercase text-zinc-500 font-bold mb-2">Impact Analysis</div>
                      <div className="text-xs text-zinc-400 space-y-1 flex flex-col">
                        <span>Economic: {evt.payload?.economic_impact || 'Nominal'}</span>
                        <span>Political: {evt.payload?.political_impact || 'Nominal'}</span>
                        <span>Social: {evt.payload?.social_impact || 'Nominal'}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            
            {buildInvestigationChain().length === 1 && (
              <div className="text-center text-zinc-500 text-xs italic mt-12">
                This is a root event. No further deterministic causes exist in the historical log.
              </div>
            )}
            
            {/* Show downstream consequences if it's the target event */}
            {data.descendants.length > 0 && (
              <div className="mt-16 pt-16 border-t border-zinc-800">
                <div className="text-center mb-8">
                  <h3 className="text-xl font-bold text-amber-500 tracking-widest mb-2">DOWNSTREAM CONSEQUENCES</h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {data.descendants.map(desc => (
                    <div key={desc.id} className="bg-zinc-950 border border-zinc-800 p-4 rounded cursor-pointer hover:border-amber-500/50 transition-colors" onClick={() => onSelectEntity({ ...desc, entity_type: 'event' })}>
                      <div className="flex justify-between mb-2">
                        <span className="text-[10px] text-zinc-500">TICK {desc.tick}</span>
                        <span className="text-[10px] text-amber-500 uppercase font-bold">{desc.type}</span>
                      </div>
                      <div className="text-sm text-zinc-300">{desc.description || desc.type}</div>
                      <div className="text-xs text-zinc-500 mt-2">By {getActorName(desc.actor_id) || 'SYSTEM'}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </div>
        )}
      </div>
    </div>
  );
}
