"use client";

import { WorldMap } from "./WorldMap";
import { EventTimeline } from "./EventTimeline";
import { CharacterInspector } from "./CharacterInspector";
import { FactionInspector } from "./FactionInspector";
import { CausalGraph } from "./CausalGraph";
import { useState } from "react";

export function MainView({ worldState, timeline, selectedEntity, onSelectEntity }: { worldState: any, timeline: any[], selectedEntity: any, onSelectEntity: (entity: any) => void }) {
  const { cities, characters, factions, resources } = worldState;
  const [showCausalGraph, setShowCausalGraph] = useState(false);

  return (
    <div className="flex w-full h-full relative">
      {showCausalGraph && selectedEntity?.id && (
        <CausalGraph 
          worldId={worldState.world.id}
          eventId={selectedEntity.id}
          characters={characters}
          cities={cities}
          factions={factions}
          onSelectEntity={(e) => {
            setShowCausalGraph(false);
            onSelectEntity(e);
          }}
          onClose={() => setShowCausalGraph(false)}
        />
      )}
      {/* Event Timeline */}
      <EventTimeline timeline={timeline} worldState={worldState} onSelectEntity={onSelectEntity} />

      {/* World Visualization */}
      <div className="flex-1 relative">
        <WorldMap worldState={worldState} onSelectEntity={onSelectEntity} />
        
        {/* Floating stats overlay */}
        <div className="absolute top-4 left-4 flex space-x-4 pointer-events-none">
          <div className="bg-black/50 border border-zinc-800 p-3 backdrop-blur-sm rounded">
            <div className="text-[10px] uppercase text-zinc-500">Populated Centers</div>
            <div className="text-xl font-light text-zinc-200">{cities.length}</div>
          </div>
          <div className="bg-black/50 border border-zinc-800 p-3 backdrop-blur-sm rounded">
            <div className="text-[10px] uppercase text-zinc-500">Active Agents</div>
            <div className="text-xl font-light text-zinc-200">{characters.length}</div>
          </div>
        </div>
      </div>

      {/* Selected Entity Inspector */}
      <div className="w-80 border-l border-zinc-800 bg-zinc-950 flex flex-col shrink-0 relative">
        <div className="p-3 border-b border-zinc-800 uppercase text-xs font-bold tracking-widest text-zinc-500 flex justify-between">
          <span>Entity Inspector</span>
          {selectedEntity && (
            <button onClick={() => onSelectEntity(null)} className="text-zinc-500 hover:text-zinc-300">×</button>
          )}
        </div>
        <div className="p-4 flex-1 overflow-y-auto custom-scrollbar">
          {selectedEntity ? (
            <div className="space-y-6">
              <div>
                <div className="text-xs text-zinc-500 uppercase tracking-widest">{selectedEntity.type}</div>
                <div className="text-xl text-cyan-400 font-bold tracking-wider">{selectedEntity.name}</div>
              </div>
              
              {selectedEntity.type === 'city' && (
                <>
                  <div className="space-y-3 border-t border-zinc-800 pt-4">
                    <div className="text-xs uppercase text-zinc-500 font-bold">Metrics</div>
                    <div className="flex justify-between text-xs">
                      <span className="text-zinc-500 uppercase">Population</span>
                      <span className="text-zinc-200 font-mono">{selectedEntity.population}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-zinc-500 uppercase">Wealth</span>
                      <span className="text-zinc-200 font-mono">{selectedEntity.wealth.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-zinc-500 uppercase">Food Supply</span>
                      <span className="text-zinc-200 font-mono">{selectedEntity.food_supply.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-zinc-500 uppercase">Unrest Level</span>
                      <span className={`font-mono ${selectedEntity.unrest > 0.5 ? 'text-red-400' : 'text-zinc-200'}`}>
                        {(selectedEntity.unrest * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-zinc-500 uppercase">Stability</span>
                      <span className="text-zinc-200 font-mono">{(selectedEntity.stability * 100).toFixed(1)}%</span>
                    </div>
                  </div>

                  <div className="space-y-3 border-t border-zinc-800 pt-4">
                    <div className="text-xs uppercase text-zinc-500 font-bold">Local Characters</div>
                    {characters.filter((c: any) => c.city_id === selectedEntity.id).map((char: any) => (
                      <div key={char.id} className="text-xs bg-zinc-900 border border-zinc-800 p-2 rounded cursor-pointer hover:border-zinc-600 transition-colors" onClick={() => onSelectEntity({ type: 'character', ...char })}>
                        <div className="font-bold text-zinc-300">{char.name}</div>
                        <div className="text-zinc-500 flex justify-between mt-1">
                          <span>{char.role}</span>
                          <span className="font-mono text-[10px]">W: {char.wealth.toFixed(0)}</span>
                        </div>
                      </div>
                    ))}
                    {characters.filter((c: any) => c.city_id === selectedEntity.id).length === 0 && (
                      <div className="text-xs text-zinc-600 italic">No notable characters</div>
                    )}
                  </div>

                  <div className="space-y-3 border-t border-zinc-800 pt-4">
                    <div className="text-xs uppercase text-zinc-500 font-bold">Faction Presence</div>
                    {Array.from(new Set(characters.filter((c: any) => c.city_id === selectedEntity.id && c.faction_id).map((c: any) => c.faction_id))).map((fid: any) => {
                      const faction = factions.find((f: any) => f.id === fid);
                      if (!faction) return null;
                      const members = characters.filter((c: any) => c.city_id === selectedEntity.id && c.faction_id === fid).length;
                      return (
                        <div 
                          key={fid} 
                          className="text-xs flex justify-between items-center bg-zinc-900 p-2 rounded border border-zinc-800 cursor-pointer hover:border-indigo-500 transition-colors"
                          onClick={() => onSelectEntity({ type: 'faction', id: fid })}
                        >
                          <span className="text-indigo-400 font-bold">{faction.name}</span>
                          <span className="text-zinc-500 font-mono">{members} members</span>
                        </div>
                      );
                    })}
                  </div>
                  
                  <div className="space-y-3 border-t border-zinc-800 pt-4">
                    <div className="text-xs uppercase text-zinc-500 font-bold">Global Market Prices</div>
                    {resources.map((res: any) => (
                      <div key={res.id} className="text-xs flex justify-between">
                        <span className="text-zinc-400 capitalize">{res.name}</span>
                        <span className="text-emerald-400 font-mono">${res.price.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {selectedEntity.type === 'character' && (
                <div className="absolute inset-0 z-20">
                  <CharacterInspector 
                    worldId={worldState.world.id} 
                    characterId={selectedEntity.id} 
                    onSelectEntity={onSelectEntity} 
                    onClose={() => onSelectEntity(null)} 
                  />
                </div>
              )}

              {selectedEntity.type === 'faction' && (
                <div className="absolute inset-0 z-20">
                  <FactionInspector 
                    worldId={worldState.world.id} 
                    factionId={selectedEntity.id} 
                    onSelectEntity={onSelectEntity} 
                    onClose={() => onSelectEntity(null)} 
                  />
                </div>
              )}

              {selectedEntity.type !== 'city' && selectedEntity.type !== 'character' && selectedEntity.type !== 'faction' && selectedEntity.entity_type !== 'event' && (
                <div className="space-y-2 border-t border-zinc-800 pt-4">
                  {Object.entries(selectedEntity).map(([key, val]) => {
                    if (key === 'id' || key === 'name' || key === 'type') return null;
                    return (
                      <div key={key} className="flex justify-between text-xs">
                        <span className="text-zinc-500 uppercase">{key}</span>
                        <span className="text-zinc-300 font-mono text-right">{JSON.stringify(val)}</span>
                      </div>
                    );
                  })}
                </div>
              )}

              {selectedEntity.entity_type === 'event' && (
                <div className="space-y-4 border-t border-zinc-800 pt-4">
                  <div className="flex justify-between items-center">
                    <div className="text-xs uppercase text-zinc-500 font-bold">Event Details</div>
                    <button 
                      onClick={() => setShowCausalGraph(true)}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] uppercase font-bold tracking-widest px-2 py-1 rounded transition-colors"
                    >
                      Trace Causality
                    </button>
                  </div>
                  
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-zinc-500 uppercase">Actor</span>
                      <span className="text-zinc-300">{characters.find((c: any) => c.id === selectedEntity.actor_id)?.name || selectedEntity.actor_id || 'System'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500 uppercase">Target</span>
                      <span className="text-zinc-300">{characters.find((c: any) => c.id === selectedEntity.target_id)?.name || selectedEntity.target_id || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500 uppercase">City</span>
                      <span className="text-zinc-300">{cities.find((c: any) => c.id === selectedEntity.city_id)?.name || selectedEntity.city_id || 'Global'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500 uppercase">Event Type</span>
                      <span className="text-cyan-400 font-mono">{selectedEntity.type}</span>
                    </div>
                  </div>

                  {selectedEntity.payload?.decision_summary && (
                    <div className="text-xs bg-zinc-900 border border-zinc-800 p-3 rounded">
                      <div className="text-zinc-500 uppercase mb-1">Decision Summary</div>
                      <div className="text-zinc-300 italic">"{selectedEntity.payload.decision_summary}"</div>
                    </div>
                  )}

                  {selectedEntity.payload?.consequences && (
                    <div className="text-xs bg-zinc-900 border border-zinc-800 p-3 rounded">
                      <div className="text-zinc-500 uppercase mb-1">Consequences</div>
                      <ul className="list-disc list-inside text-zinc-300">
                        {Array.isArray(selectedEntity.payload.consequences) ? 
                          selectedEntity.payload.consequences.map((c: any, i: number) => <li key={i}>{c}</li>) : 
                          <li>{JSON.stringify(selectedEntity.payload.consequences)}</li>}
                      </ul>
                    </div>
                  )}

                  {selectedEntity.parent_event_id && (
                    <div className="text-xs bg-zinc-900 border border-zinc-800 p-3 rounded cursor-pointer hover:border-zinc-600" 
                         onClick={() => {
                           const parent = timeline.find(e => e.id === selectedEntity.parent_event_id);
                           if (parent) onSelectEntity({...parent, entity_type: 'event'});
                         }}>
                      <div className="text-zinc-500 uppercase mb-1">Parent Event</div>
                      <div className="text-indigo-400 truncate">{timeline.find(e => e.id === selectedEntity.parent_event_id)?.description || selectedEntity.parent_event_id}</div>
                    </div>
                  )}

                  <div className="text-xs">
                    <div className="text-zinc-500 uppercase mb-2 font-bold border-t border-zinc-800 pt-3">Child Events</div>
                    <div className="space-y-2">
                      {timeline.filter(e => e.parent_event_id === selectedEntity.id).map(child => (
                        <div key={child.id} 
                             className="bg-zinc-900 border border-zinc-800 p-2 rounded cursor-pointer hover:border-zinc-600"
                             onClick={() => onSelectEntity({...child, entity_type: 'event'})}>
                          <div className="text-zinc-400 font-mono text-[10px] mb-1">TICK {child.tick}</div>
                          <div className="text-zinc-300 truncate">{child.description}</div>
                        </div>
                      ))}
                      {timeline.filter(e => e.parent_event_id === selectedEntity.id).length === 0 && (
                        <div className="text-zinc-600 italic">No child events recorded.</div>
                      )}
                    </div>
                  </div>
                  
                  <div className="text-[10px] text-zinc-600 font-mono mt-4 pt-4 border-t border-zinc-800">
                    Raw Payload:
                    <pre className="mt-2 overflow-x-auto">{JSON.stringify(selectedEntity.payload, null, 2)}</pre>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-zinc-600 text-xs text-center p-8">
              Select a city or entity on the map to inspect its details
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
