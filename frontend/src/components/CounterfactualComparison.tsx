"use client";

import { useEffect, useState } from "react";
import { compareWorlds } from "../lib/api";

export function CounterfactualComparison({ 
  baseWorldId, 
  targetWorldId, 
  onClose 
}: { 
  baseWorldId: string, 
  targetWorldId: string, 
  onClose: () => void 
}) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadComparison();
  }, [baseWorldId, targetWorldId]);

  const loadComparison = async () => {
    setLoading(true);
    try {
      const result = await compareWorlds(baseWorldId, targetWorldId);
      setData(result);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !data) {
    return (
      <div className="absolute inset-0 bg-black/90 z-40 flex items-center justify-center font-mono text-indigo-500">
        ANALYZING DIVERGENCE METRICS...
      </div>
    );
  }

  const { original, counterfactual } = data;

  const MetricRow = ({ label, originalVal, cfVal, formatter = (v: any) => v }: any) => {
    const diff = cfVal - originalVal;
    let colorClass = "text-zinc-400";
    if (diff > 0) colorClass = "text-emerald-400";
    if (diff < 0) colorClass = "text-red-400";

    return (
      <div className="flex border-b border-zinc-800/50 py-3 text-sm hover:bg-zinc-900/50">
        <div className="w-1/3 text-zinc-500 uppercase tracking-widest px-4">{label}</div>
        <div className="w-1/3 px-4 font-mono">{formatter(originalVal)}</div>
        <div className="w-1/3 px-4 font-mono flex justify-between items-center">
          <span>{formatter(cfVal)}</span>
          {diff !== 0 && (
            <span className={`text-[10px] ${colorClass}`}>
              {diff > 0 ? '+' : ''}{formatter(diff)}
            </span>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="absolute inset-0 bg-zinc-950 z-40 flex flex-col font-mono text-zinc-300 overflow-hidden">
      <div className="bg-indigo-900/20 border-b border-indigo-900/50 p-4 shrink-0 flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-indigo-400 uppercase tracking-widest flex items-center space-x-3">
            <span>Divergence Analysis</span>
            <span className="bg-indigo-500/20 text-indigo-300 text-[10px] px-2 py-1 rounded border border-indigo-500/30">
              SIMULATED ALTERNATIVE TRAJECTORY
            </span>
          </h2>
          <p className="text-[10px] text-zinc-500 mt-1 uppercase tracking-wider">
            Disclaimer: Do NOT claim scientific causal inference. This is a heuristic simulation model.
          </p>
        </div>
        <button 
          onClick={onClose}
          className="bg-zinc-800 hover:bg-zinc-700 text-white px-4 py-2 rounded uppercase tracking-widest text-xs transition-colors"
        >
          Close Comparison
        </button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-8">
        <div className="max-w-5xl mx-auto space-y-8">
          
          <div className="grid grid-cols-3 text-xs uppercase tracking-widest text-zinc-600 border-b border-zinc-800 pb-2 px-4">
            <div>Metric</div>
            <div className="text-cyan-500">{original.name} (Base)</div>
            <div className="text-indigo-400">{counterfactual.name} (Branch)</div>
          </div>

          <div className="bg-black/50 border border-zinc-800 rounded-lg overflow-hidden">
            <MetricRow label="Tick / Time" originalVal={original.tick} cfVal={counterfactual.tick} />
            <MetricRow label="Avg Grain Price" originalVal={original.grain_price} cfVal={counterfactual.grain_price} formatter={(v: number) => v.toFixed(2)} />
            <MetricRow label="Total Food Supply" originalVal={original.food_supply} cfVal={counterfactual.food_supply} formatter={(v: number) => v.toFixed(0)} />
            <MetricRow label="Global Wealth" originalVal={original.wealth} cfVal={counterfactual.wealth} formatter={(v: number) => v.toFixed(0)} />
            <MetricRow label="Avg Unrest Level" originalVal={original.unrest} cfVal={counterfactual.unrest} formatter={(v: number) => (v * 100).toFixed(1) + '%'} />
            <MetricRow label="Gov Approval (Stability)" originalVal={original.government_approval} cfVal={counterfactual.government_approval} formatter={(v: number) => (v * 100).toFixed(1) + '%'} />
            <MetricRow label="Trade Volume" originalVal={original.trade_volume} cfVal={counterfactual.trade_volume} formatter={(v: number) => v.toFixed(0)} />
            <MetricRow label="Faction Influence" originalVal={original.faction_influence} cfVal={counterfactual.faction_influence} formatter={(v: number) => v.toFixed(0)} />
            <MetricRow label="Population Movement" originalVal={original.population_movement} cfVal={counterfactual.population_movement} />
          </div>

          <div className="grid grid-cols-2 gap-8 pt-4">
            <div>
              <h3 className="text-sm uppercase tracking-widest text-cyan-500 mb-4 px-2 border-b border-zinc-800 pb-2">
                Major Events (Base)
              </h3>
              <div className="space-y-2">
                {original.major_events.map((e: any) => (
                  <div key={e.id} className="bg-zinc-900 border border-zinc-800 p-3 rounded text-xs">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-cyan-400 font-bold">{e.type}</span>
                      <span className="text-zinc-500 font-mono">Tick {e.tick}</span>
                    </div>
                    <div className="text-zinc-400 font-mono truncate">{JSON.stringify(e.payload)}</div>
                  </div>
                ))}
                {original.major_events.length === 0 && <div className="text-zinc-600 text-xs italic px-2">No major events recorded.</div>}
              </div>
            </div>

            <div>
              <h3 className="text-sm uppercase tracking-widest text-indigo-400 mb-4 px-2 border-b border-zinc-800 pb-2">
                Major Events (Branch)
              </h3>
              <div className="space-y-2">
                {counterfactual.major_events.map((e: any) => (
                  <div key={e.id} className="bg-indigo-950 border border-indigo-900/50 p-3 rounded text-xs">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-indigo-400 font-bold">{e.type}</span>
                      <span className="text-zinc-500 font-mono">Tick {e.tick}</span>
                    </div>
                    <div className="text-zinc-400 font-mono truncate">{JSON.stringify(e.payload)}</div>
                  </div>
                ))}
                {counterfactual.major_events.length === 0 && <div className="text-zinc-600 text-xs italic px-2">No major events recorded.</div>}
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
