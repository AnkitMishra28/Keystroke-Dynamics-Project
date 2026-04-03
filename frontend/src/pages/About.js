export default function About() {
  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-black via-purple-950 to-black text-white overflow-x-hidden pt-24">

      {/* Background Glow */}
      <div className="absolute w-[800px] h-[800px] bg-purple-700 opacity-20 blur-3xl rounded-full top-0 left-[-200px]" />
      <div className="absolute w-[800px] h-[800px] bg-pink-600 opacity-20 blur-3xl rounded-full bottom-0 right-[-200px]" />

      {/* Content */}
      <div className="relative z-10 max-w-4xl mx-auto px-6 py-16">

        <h1 className="text-5xl font-extrabold bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-500 bg-clip-text text-transparent mb-8">
          About Keystroke AI
        </h1>

        <div className="space-y-8">

          {/* What is it */}
          <div className="bg-white/5 backdrop-blur-xl p-8 rounded-xl border border-white/10">
            <h2 className="text-2xl font-bold text-cyan-400 mb-4">What is Keystroke Authentication?</h2>
            <p className="text-gray-300 leading-relaxed">
              Keystroke authentication is a biometric security method that analyzes your unique typing patterns. 
              Each person has a distinct way of typing—different typing speed, rhythm, and pressure. 
              KeystrokeAI builds a profile from multiple enrollment samples and uses a strict hybrid decision engine during login.
            </p>
          </div>

          {/* How it works */}
          <div className="bg-white/5 backdrop-blur-xl p-8 rounded-xl border border-white/10">
            <h2 className="text-2xl font-bold text-purple-400 mb-4">How It Works</h2>
            <div className="space-y-4">
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full flex items-center justify-center text-black font-bold">1</div>
                <div>
                  <h3 className="font-semibold text-white mb-2">Register</h3>
                  <p className="text-gray-400">Type naturally for 3 to 5 enrollment samples. We extract dwell and flight timings and store only your latest 5 biometric samples.</p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-pink-400 to-purple-500 rounded-full flex items-center justify-center text-black font-bold">2</div>
                <div>
                  <h3 className="font-semibold text-white mb-2">Process</h3>
                  <p className="text-gray-400">The backend generates transformer embeddings, computes typing distribution statistics, and normalizes signals before scoring.</p>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-purple-400 to-pink-500 rounded-full flex items-center justify-center text-black font-bold">3</div>
                <div>
                  <h3 className="font-semibold text-white mb-2">Authenticate</h3>
                  <p className="text-gray-400">Login uses hybrid scoring (80% embedding similarity + 20% statistical similarity) with an adaptive threshold. Same-user behavior passes; mismatched behavior fails.</p>
                </div>
              </div>
            </div>
          </div>

          {/* Technology */}
          <div className="bg-white/5 backdrop-blur-xl p-8 rounded-xl border border-white/10">
            <h2 className="text-2xl font-bold text-pink-400 mb-4">Technology Stack</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div className="bg-black/40 p-4 rounded-lg border border-white/10">
                <p className="text-cyan-400 font-semibold">Frontend</p>
                <p className="text-gray-400 text-sm">React 19 + Tailwind CSS + Recharts</p>
              </div>
              <div className="bg-black/40 p-4 rounded-lg border border-white/10">
                <p className="text-purple-400 font-semibold">Backend</p>
                <p className="text-gray-400 text-sm">FastAPI + PyTorch + MongoDB</p>
              </div>
              <div className="bg-black/40 p-4 rounded-lg border border-white/10">
                <p className="text-pink-400 font-semibold">AI Model</p>
                <p className="text-gray-400 text-sm">Transformer Neural Network</p>
              </div>
            </div>
          </div>

          {/* Why use it */}
          <div className="bg-white/5 backdrop-blur-xl p-8 rounded-xl border border-white/10">
            <h2 className="text-2xl font-bold text-cyan-400 mb-4">Why Choose Keystroke Authentication?</h2>
            <ul className="space-y-3 text-gray-300">
              <li className="flex items-start gap-3">
                <span className="text-green-400 font-bold">✓</span>
                <span><strong>Unique & Personal:</strong> Your typing pattern is unique, much like a fingerprint</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-400 font-bold">✓</span>
                <span><strong>No Hardware Required:</strong> Works with any keyboard</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-400 font-bold">✓</span>
                <span><strong>Difficult to Spoof:</strong> Hard to replicate someone's exact typing pattern</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-400 font-bold">✓</span>
                <span><strong>Strict by Design:</strong> Adaptive thresholds and hard mismatch checks reduce false acceptance</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-400 font-bold">✓</span>
                <span><strong>AI-Powered:</strong> Machine learning improves accuracy over time</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-400 font-bold">✓</span>
                <span><strong>Privacy-Friendly:</strong> No camera or microphone needed</span>
              </li>
            </ul>
          </div>

          {/* Contact */}
          <div className="bg-gradient-to-r from-cyan-500/20 to-purple-500/20 backdrop-blur-xl p-8 rounded-xl border border-cyan-400/50">
            <h2 className="text-2xl font-bold text-cyan-300 mb-4">Get Started Today</h2>
            <p className="text-gray-300 mb-6">
              Experience the future of authentication with AI-powered keystroke biometrics.
            </p>
            <a
              href="/"
              className="inline-block bg-gradient-to-r from-cyan-400 to-blue-500 text-black px-8 py-3 rounded-lg font-semibold hover:scale-105 transition"
            >
              Try Now
            </a>
          </div>

        </div>

      </div>

    </div>
  );
}
