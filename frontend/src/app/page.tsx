export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24 bg-zinc-950 text-white">
      <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">WORLDOS</h1>
      <p className="mt-6 text-xl text-zinc-400">Autonomous persistent world simulation</p>
      
      <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl w-full">
        <div className="bg-zinc-900 border border-zinc-800 p-6 rounded-xl hover:border-zinc-700 transition-colors">
          <h2 className="text-xl font-semibold mb-2">Simulation Engine</h2>
          <p className="text-zinc-500 text-sm">Deterministic state mutation and event resolution</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 p-6 rounded-xl hover:border-zinc-700 transition-colors">
          <h2 className="text-xl font-semibold mb-2">Agent Cognition</h2>
          <p className="text-zinc-500 text-sm">Perception, memory retrieval, and structured decision making</p>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 p-6 rounded-xl hover:border-zinc-700 transition-colors">
          <h2 className="text-xl font-semibold mb-2">World State</h2>
          <p className="text-zinc-500 text-sm">Persistent entities, relationships, economies, and politics</p>
        </div>
      </div>
    </main>
  );
}
