"use client";

import { useMemo } from "react";
import ReactFlow, { Background, Controls, Node, Edge } from "reactflow";
import "reactflow/dist/style.css";

function hashString(str: string) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash |= 0;
  }
  return hash;
}

export function WorldMap({ worldState, onSelectEntity }: { worldState: any, onSelectEntity: (entity: any) => void }) {
  const { cities, characters, factions } = worldState;

  const { nodes, edges } = useMemo(() => {
    const nds: Node[] = [];
    const egs: Edge[] = [];

    // Calculate deterministic positions
    cities.forEach((city: any) => {
      const h = Math.abs(hashString(city.id));
      // Spread across a reasonable coordinate plane
      const x = (h % 1000);
      const y = ((h * 13) % 800);
      
      const cityChars = characters.filter((c: any) => c.city_id === city.id);
      const hasUnrest = city.unrest > 0.5;

      nds.push({
        id: `city-${city.id}`,
        type: 'default',
        position: { x, y },
        data: { 
          label: (
            <div className="flex flex-col items-center">
              <div className="font-bold text-cyan-400 tracking-wider text-sm">{city.name}</div>
              <div className="text-[10px] text-zinc-400 mt-1">POP {city.population}</div>
              {hasUnrest && <div className="text-[10px] text-red-500 font-bold animate-pulse mt-1">HIGH UNREST</div>}
              <div className="w-full bg-zinc-800 h-1 mt-2 rounded-full overflow-hidden flex">
                <div className="bg-green-500 h-full" style={{ width: `${Math.min(100, city.wealth / 50)}%` }} />
              </div>
            </div>
          )
        },
        style: { 
          background: '#18181b', 
          color: '#cbd5e1', 
          border: `1px solid ${hasUnrest ? '#ef4444' : '#3f3f46'}`, 
          borderRadius: '8px', 
          padding: '12px',
          width: 140,
          boxShadow: hasUnrest ? '0 0 15px rgba(239, 68, 68, 0.2)' : '0 4px 6px rgba(0, 0, 0, 0.3)'
        }
      });
    });

    factions.forEach((faction: any, i: number) => {
      nds.push({
        id: `faction-${faction.id}`,
        type: 'default',
        position: { x: 50 + (i * 200), y: -100 },
        data: { 
          label: (
            <div className="flex flex-col items-center">
              <div className="font-bold text-indigo-400 tracking-wider text-xs">🛡️ {faction.name}</div>
              <div className="text-[10px] text-zinc-400 mt-1">{faction.type}</div>
            </div>
          )
        },
        style: { 
          background: '#1e1b4b', 
          color: '#c7d2fe', 
          border: '1px solid #3730a3', 
          borderRadius: '8px', 
          padding: '8px',
          width: 120,
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)'
        }
      });
    });

    // Create Trade Routes (Edges) based on proximity
    for (let i = 0; i < nds.length; i++) {
      let closestDist = Infinity;
      let closestJ = -1;
      let secondClosestDist = Infinity;
      let secondClosestJ = -1;

      for (let j = 0; j < nds.length; j++) {
        if (i === j) continue;
        const dx = nds[i].position.x - nds[j].position.x;
        const dy = nds[i].position.y - nds[j].position.y;
        const dist = Math.sqrt(dx*dx + dy*dy);
        
        if (dist < closestDist) {
          secondClosestDist = closestDist;
          secondClosestJ = closestJ;
          closestDist = dist;
          closestJ = j;
        } else if (dist < secondClosestDist) {
          secondClosestDist = dist;
          secondClosestJ = j;
        }
      }
      
      // Connect to closest
      if (closestJ !== -1) {
        const edgeId = `route-${Math.min(i, closestJ)}-${Math.max(i, closestJ)}`;
        if (!egs.find(e => e.id === edgeId)) {
          egs.push({
            id: edgeId,
            source: nds[i].id,
            target: nds[closestJ].id,
            animated: true,
            style: { stroke: '#10b981', strokeWidth: 1.5, opacity: 0.4 }
          });
        }
      }
      // Connect to second closest for more web-like map
      if (secondClosestJ !== -1) {
        const edgeId = `route-${Math.min(i, secondClosestJ)}-${Math.max(i, secondClosestJ)}`;
        if (!egs.find(e => e.id === edgeId)) {
          egs.push({
            id: edgeId,
            source: nds[i].id,
            target: nds[secondClosestJ].id,
            animated: true,
            style: { stroke: '#3b82f6', strokeWidth: 1, opacity: 0.2 }
          });
        }
      }
    }

    return { nodes: nds, edges: egs };
  }, [cities, characters, factions]);

  return (
    <div className="w-full h-full bg-zinc-900 relative">
      <ReactFlow 
        nodes={nodes} 
        edges={edges}
        fitView
        onNodeClick={(e, node) => {
          const type = node.id.split('-')[0];
          const id = node.id.substring(type.length + 1);
          if (type === 'city') {
            const entity = cities.find((c: any) => c.id === id);
            if (entity) onSelectEntity({ type: 'city', ...entity });
          } else if (type === 'faction') {
            const entity = factions.find((f: any) => f.id === id);
            if (entity) onSelectEntity({ type: 'faction', ...entity });
          }
        }}
      >
        <Background color="#27272a" gap={24} size={1.5} />
        <Controls className="bg-zinc-800 border-zinc-700 fill-zinc-400" />
      </ReactFlow>
      
      {/* Floating Legend */}
      <div className="absolute bottom-4 left-4 bg-black/60 border border-zinc-800 p-4 backdrop-blur-md rounded-lg pointer-events-none">
        <div className="text-xs uppercase font-bold text-zinc-500 mb-2 tracking-widest">Map Legend</div>
        <div className="flex items-center space-x-2 mb-1">
          <div className="w-3 h-0.5 bg-emerald-500 opacity-60"></div>
          <span className="text-[10px] text-zinc-400">Primary Trade Route</span>
        </div>
        <div className="flex items-center space-x-2 mb-1">
          <div className="w-3 h-0.5 bg-blue-500 opacity-40"></div>
          <span className="text-[10px] text-zinc-400">Secondary Trade Route</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 border border-red-500 rounded-sm"></div>
          <span className="text-[10px] text-zinc-400">Civil Unrest</span>
        </div>
      </div>
    </div>
  );
}
