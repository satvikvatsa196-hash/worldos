"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

export function BottomPanel({ worldState }: { worldState: any }) {
  const { cities, factions, resources } = worldState;

  return (
    <div className="h-full flex flex-col">
      <div className="text-xs uppercase text-zinc-500 mb-2 font-bold tracking-widest">Global Metrics</div>
      <div className="flex-1 grid grid-cols-3 gap-6">
        
        {/* Population / Wealth Chart */}
        <div className="bg-zinc-900 border border-zinc-800 rounded p-4 flex flex-col">
          <div className="text-[10px] uppercase text-zinc-400 mb-2">City Wealth & Population</div>
          <div className="flex-1 w-full min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={cities} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#71717a' }} axisLine={false} tickLine={false} />
                <YAxis yAxisId="left" tick={{ fontSize: 10, fill: '#71717a' }} axisLine={false} tickLine={false} />
                <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10, fill: '#71717a' }} axisLine={false} tickLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', fontSize: '12px' }}
                  itemStyle={{ color: '#d4d4d8' }}
                />
                <Bar yAxisId="left" dataKey="population" fill="#3b82f6" radius={[2, 2, 0, 0]} />
                <Bar yAxisId="right" dataKey="wealth" fill="#10b981" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Politics Chart */}
        <div className="bg-zinc-900 border border-zinc-800 rounded p-4 flex flex-col">
          <div className="text-[10px] uppercase text-zinc-400 mb-2">Faction Power Distribution</div>
          <div className="flex-1 w-full min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={factions} layout="vertical" margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" width={80} tick={{ fontSize: 10, fill: '#71717a' }} axisLine={false} tickLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', fontSize: '12px' }}
                  itemStyle={{ color: '#d4d4d8' }}
                />
                <Bar dataKey="power" radius={[0, 2, 2, 0]}>
                  {factions.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={['#6366f1', '#ec4899', '#f59e0b', '#8b5cf6'][index % 4]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Resources Chart */}
        <div className="bg-zinc-900 border border-zinc-800 rounded p-4 flex flex-col">
          <div className="text-[10px] uppercase text-zinc-400 mb-2">Resource Prices</div>
          <div className="flex-1 w-full min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={resources} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#71717a' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#71717a' }} axisLine={false} tickLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', fontSize: '12px' }}
                  itemStyle={{ color: '#d4d4d8' }}
                />
                <Bar dataKey="price" fill="#f43f5e" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>
    </div>
  );
}
