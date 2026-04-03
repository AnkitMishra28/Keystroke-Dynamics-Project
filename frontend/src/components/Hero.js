import { motion } from "framer-motion";

export default function Hero() {
  return (
    <div className="relative min-h-screen flex flex-col justify-center items-center text-center overflow-hidden">

      {/* DARK BASE */}
      <div className="absolute inset-0 bg-[#07010f]"></div>

      {/* GRADIENT LIGHT STRIPS (LIKE YOUR IMAGE) */}
      <div className="absolute w-[800px] h-[600px] bg-purple-500 opacity-30 blur-[200px] top-[10%] left-[20%]"></div>
      <div className="absolute w-[800px] h-[600px] bg-pink-500 opacity-30 blur-[200px] bottom-[10%] right-[20%]"></div>

      {/* CENTER GLOW PANEL */}
      <div className="absolute w-[600px] h-[200px] bg-gradient-to-r from-purple-500 via-pink-500 to-orange-500 opacity-20 blur-[120px]"></div>

      {/* TEXT */}
      <motion.h1
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-6xl font-bold text-white z-10"
      >
        Tools for the future
      </motion.h1>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="mt-4 text-gray-400 max-w-xl z-10"
      >
        AI-powered keystroke authentication system with behavioral biometrics.
      </motion.p>

      <motion.button
        whileHover={{ scale: 1.1 }}
        className="mt-6 px-6 py-3 bg-white text-black rounded-lg z-10"
      >
        Get Started
      </motion.button>

      {/* GLASS INPUT PANEL (MAIN UI LIKE IMAGE) */}
      <div className="mt-16 z-10 bg-white/10 backdrop-blur-xl border border-white/20 p-6 rounded-2xl w-[500px] shadow-2xl">

        <input
          placeholder="Ask Anything..."
          className="w-full p-3 bg-black/40 rounded-lg text-white mb-4"
        />

        <div className="flex gap-3 text-sm text-gray-300 flex-wrap">
          <span className="bg-white/10 px-3 py-1 rounded">Analyze</span>
          <span className="bg-white/10 px-3 py-1 rounded">Security</span>
          <span className="bg-white/10 px-3 py-1 rounded">Biometrics</span>
        </div>

      </div>

    </div>
  );
}