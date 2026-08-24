"use client";

import { useState, useMemo } from "react";

export function EventTimeline({ timeline, worldState, onSelectEntity }: { timeline: any[], worldState: any, onSelectEntity: (entity: any) => void }) {
  const { characters, factions, cities } = worldState;
  
  const [filterType, setFilterType] = useState<string>("ALL");
  const [filterEntity, setFilterEntity] = useState<string>("ALL");

  const filteredTimeline = useMemo(() => {
    return timeline.filter(event => {
      if (filterType !== "ALL" && event.type !== filterType) return false;
      if (filterEntity !== "ALL") {
        const matchesEntity = event.actor_id === filterEntity || 
                              event.target_id === filterEntity || 
                              event.city_id === filterEntity || 
                              event.faction_id === filterEntity;
        if (!matchesEntity) return false;
      }
      return true;
    });
  }, [timeline, filterType, filterEntity]);

  const groupedTimeline = useMemo(() => {
    const groups: { [key: number]: any[] } = {};
    filteredTimeline.forEach(event => {
      const day = Math.floor(event.tick / 24) + 1;
      if (!groups[day]) groups[day] = [];
      groups[day].push(event);
    });
    return groups;
  }, [filteredTimeline]);

  const allTypes = Array.from(new Set(timeline.map(e => e.type)));

  return (
    <div className="flex flex-col h-full w-96 border-r border-zinc-800 bg-zinc-950 shrink-0">
      <div className="p-3 border-b border-zinc-800 uppercase text-xs font-bold tracking-widest text-zinc-500 flex flex-col space-y-2">
        <div>World Events</div>
        <div className="flex space-x-2">
          <select 
            className="bg-zinc-900 border border-zinc-700 text-zinc-300 text-[10px] p-1 rounded outline-none flex-1"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
          >
            <option value="ALL">All Event Types</option>
            {allTypes.map(t => <option key={t as string} value={t as string}>{t as string}</option>)}
          </select>
          <select 
            className="bg-zinc-900 border border-zinc-700 text-zinc-300 text-[10px] p-1 rounded outline-none flex-1"
            value={filterEntity}
            onChange={(e) => setFilterEntity(e.target.value)}
          >
            <option value="ALL">All Entities</option>
            <optgroup label="Cities">
              {cities.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </optgroup>
            <optgroup label="Factions">
              {factions.map((f: any) => <option key={f.id} value={f.id}>{f.name}</option>)}
            </optgroup>
          </select>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
        {Object.entries(groupedTimeline).sort(([a], [b]) => Number(b) - Number(a)).map(([day, events]) => (
          <div key={day} className="mb-6">
            <div className="text-zinc-500 font-bold tracking-widest text-xs mb-3 border-b border-zinc-800 pb-1">
              DAY {day}
            </div>
            <div className="space-y-2">
              {events.sort((a, b) => b.tick - a.tick).map((event: any) => {
                const hour = (event.tick % 24).toString().padStart(2, '0');
                const isMajor = event.type === 'FactionWar' || event.type === 'EconomicCrash' || event.payload?.is_major;
                
                return (
                  <div 
                    key={event.id || event.tick + Math.random()} 
                    onClick={() => onSelectEntity({ ...event, entity_type: 'event' })}
                    className={`text-xs pl-3 py-2 cursor-pointer transition-colors border-l-2 ${isMajor ? 'border-amber-500 bg-amber-500/5 hover:bg-amber-500/10' : 'border-zinc-700 hover:bg-zinc-900'}`}
                  >
                    <div className="flex items-start space-x-3">
                      <div className={`font-mono ${isMajor ? 'text-amber-400' : 'text-zinc-500'}`}>{hour}:00</div>
                      <div className="flex-1">
                        <div className={isMajor ? 'text-amber-300 font-bold' : 'text-zinc-300'}>{event.description}</div>
                        {event.payload?.decision_summary && (
                          <div className="text-zinc-500 mt-1 italic leading-relaxed">
                            "{event.payload.decision_summary}"
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
        {Object.keys(groupedTimeline).length === 0 && (
          <div className="text-zinc-600 text-xs text-center p-4">No events found matching filters.</div>
        )}
      </div>
    </div>
  );
}
