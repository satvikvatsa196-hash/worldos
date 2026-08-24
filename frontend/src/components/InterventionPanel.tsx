"use client";

import { useState } from "react";
import { triggerIntervention } from "../lib/api";

const INTERVENTIONS = [
  { type: "drought", name: "Introduce Drought", needsTarget: true, targetType: "city" },
  { type: "resource_shortage", name: "Introduce Resource Shortage", needsTarget: true, targetType: "city" },
  { type: "change_tax", name: "Change Tax Rate", needsTarget: true, targetType: "faction" },
  { type: "subsidy", name: "Introduce Subsidy", needsTarget: true, targetType: "faction" },
  { type: "embargo", name: "Impose Embargo", needsTarget: true, targetType: "city" },
  { type: "change_policy", name: "Change Policy", needsTarget: true, targetType: "faction" },
  { type: "inject_resources", name: "Inject Resources", needsTarget: true, targetType: "city" },
  { type: "remove_resources", name: "Remove Resources", needsTarget: true, targetType: "city" },
  { type: "trigger_election", name: "Trigger Election", needsTarget: true, targetType: "faction" },
  { type: "trade_disruption", name: "Trade Disruption", needsTarget: false, targetType: "none" }
];

export function InterventionPanel({ 
  worldId, 
  worldState, 
  onClose,
  selectedEntity 
}: { 
  worldId: string, 
  worldState: any, 
  onClose: () => void,
  selectedEntity?: any
}) {
  const [selectedIntervention, setSelectedIntervention] = useState<string | null>(null);
  const [targetId, setTargetId] = useState<string>("");
  const [payload, setPayload] = useState<string>("{}");
  const [status, setStatus] = useState<string>("");

  const handleTrigger = async () => {
    if (!selectedIntervention) return;
    setStatus("Triggering...");
    try {
      const parsedPayload = JSON.parse(payload);
      await triggerIntervention(worldId, selectedIntervention, targetId || undefined, parsedPayload);
      setStatus("Intervention successful.");
      setTimeout(() => setStatus(""), 3000);
    } catch (e: any) {
      setStatus(`Error: ${e.message}`);
    }
  };

  const currentIntervention = INTERVENTIONS.find(i => i.type === selectedIntervention);
  
  // Auto-fill target if selectedEntity matches
  const handleSelectIntervention = (type: string) => {
    setSelectedIntervention(type);
    const i = INTERVENTIONS.find(inv => inv.type === type);
    if (i && selectedEntity && i.targetType === selectedEntity.type) {
      setTargetId(selectedEntity.id);
    } else {
      setTargetId("");
    }
  };

  return (
    <div className="absolute top-16 right-4 w-96 bg-zinc-950 border border-zinc-800 rounded-lg shadow-2xl flex flex-col z-50 text-sm overflow-hidden">
      <div className="bg-red-900/20 p-3 border-b border-red-900/50 flex justify-between items-center text-red-500 font-bold uppercase tracking-widest text-xs">
        <span>Observer Intervention</span>
        <button onClick={onClose} className="hover:text-red-400">×</button>
      </div>

      <div className="p-4 space-y-4 max-h-[80vh] overflow-y-auto custom-scrollbar">
        <div>
          <label className="block text-xs uppercase text-zinc-500 mb-1">Select Action</label>
          <select 
            className="w-full bg-zinc-900 border border-zinc-800 rounded p-2 text-zinc-300 focus:outline-none focus:border-red-900"
            value={selectedIntervention || ""}
            onChange={(e) => handleSelectIntervention(e.target.value)}
          >
            <option value="" disabled>-- Choose Intervention --</option>
            {INTERVENTIONS.map(i => (
              <option key={i.type} value={i.type}>{i.name}</option>
            ))}
          </select>
        </div>

        {currentIntervention && (
          <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
            {currentIntervention.needsTarget && (
              <div>
                <label className="block text-xs uppercase text-zinc-500 mb-1">
                  Target {currentIntervention.targetType} ID
                </label>
                <div className="flex gap-2">
                  <input 
                    type="text" 
                    value={targetId}
                    onChange={(e) => setTargetId(e.target.value)}
                    className="flex-1 bg-zinc-900 border border-zinc-800 rounded p-2 text-zinc-300 focus:outline-none focus:border-red-900"
                    placeholder={`Enter UUID...`}
                  />
                  {selectedEntity && selectedEntity.type === currentIntervention.targetType && (
                    <button 
                      onClick={() => setTargetId(selectedEntity.id)}
                      className="bg-zinc-800 text-xs px-2 py-1 rounded hover:bg-zinc-700 uppercase tracking-widest text-zinc-400"
                    >
                      Use Selected
                    </button>
                  )}
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs uppercase text-zinc-500 mb-1">Payload (JSON)</label>
              <textarea 
                value={payload}
                onChange={(e) => setPayload(e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-800 rounded p-2 text-zinc-300 font-mono text-xs focus:outline-none focus:border-red-900"
                rows={4}
              />
            </div>

            <button 
              onClick={handleTrigger}
              className="w-full bg-red-900/50 hover:bg-red-900/80 text-red-100 py-3 rounded uppercase tracking-widest font-bold transition-colors border border-red-900/50"
            >
              Execute Intervention
            </button>
            
            {status && (
              <div className={`text-xs text-center uppercase tracking-widest p-2 rounded ${status.includes('Error') ? 'bg-red-900/20 text-red-400' : 'bg-green-900/20 text-green-400'}`}>
                {status}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
