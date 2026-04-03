export default function Features() {
  return (
    <div className="mt-40 grid grid-cols-3 gap-8 px-20 text-center">

      <div className="bg-white/5 p-6 rounded-xl border border-white/10">
        <h3 className="text-xl mb-2">AI Authentication</h3>
        <p className="text-gray-400">Behavior-based login using typing patterns.</p>
      </div>

      <div className="bg-white/5 p-6 rounded-xl border border-white/10">
        <h3 className="text-xl mb-2">Anomaly Detection</h3>
        <p className="text-gray-400">Detect intrusions instantly.</p>
      </div>

      <div className="bg-white/5 p-6 rounded-xl border border-white/10">
        <h3 className="text-xl mb-2">Analytics Dashboard</h3>
        <p className="text-gray-400">Visualize login behavior.</p>
      </div>

    </div>
  );
}