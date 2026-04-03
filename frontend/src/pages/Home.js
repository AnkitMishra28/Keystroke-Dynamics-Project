import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const API_URL = "https://keystroke-dynamics-project.onrender.com";

export default function Home() {
  const navigate = useNavigate();
  const MIN_KEYSTROKES = 20;
  
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [typedText, setTypedText] = useState("");
  const [keystrokes, setKeystrokes] = useState([]);
  const [result, setResult] = useState("");
  const [info, setInfo] = useState("");
  const [mode, setMode] = useState("login"); // "login" or "register"
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const activeKeyMapRef = useRef(new Map());

  const handleKeyDown = (e) => {
    if (e.repeat) {
      return;
    }

    if (!username.trim()) {
      setError("Please enter a username first");
      return;
    }

    setError("");
    setInfo("");
    const now = Date.now();

    const keyId = e.code || e.key;
    if (!keyId) {
      return;
    }

    if (!activeKeyMapRef.current.has(keyId)) {
      activeKeyMapRef.current.set(keyId, {
        key: e.key || "",
        down: now
      });
    }
  };

  const handleKeyUp = (e) => {
    const keyId = e.code || e.key;
    if (!keyId) {
      return;
    }

    const active = activeKeyMapRef.current.get(keyId);
    if (!active) {
      return;
    }

    const now = Date.now();
    setKeystrokes((prev) => [
      ...prev,
      {
        key: active.key,
        down: active.down,
        up: now
      }
    ]);

    activeKeyMapRef.current.delete(keyId);
  };

  const resetTiming = () => {
    activeKeyMapRef.current = new Map();
  };

  const resetPattern = () => {
    setTypedText("");
    setKeystrokes([]);
    setError("");
    setResult("");
    resetTiming();
  };

  const resetForm = () => {
    setUsername("");
    setPassword("");
    setInfo("");
    resetPattern();
  };

  const clearAuthSession = () => {
    localStorage.removeItem("authToken");
    localStorage.removeItem("lastUsername");
  };

  const register = async () => {
    if (!username.trim()) {
      setError("Username cannot be empty");
      return;
    }

    if (!password) {
      setError("Password is required");
      return;
    }

    if (keystrokes.length < MIN_KEYSTROKES) {
      setError(`Please type at least ${MIN_KEYSTROKES} keystrokes for registration`);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await axios.post(`${API_URL}/register`, {
        username,
        password,
        keystrokes
      });

      const data = res.data;
      if (data.ready_for_login) {
        setInfo(`Enrollment complete (${data.sample_count}/${data.required_samples}). You can login now.`);
        setMode("login");
      } else {
        setInfo(`Sample ${data.sample_count}/${data.required_samples} captured. Please type again and press Register.`);
      }

      resetPattern();
    } catch (err) {
      const backendMessage = err?.response?.data?.detail || err?.response?.data?.message;
      setError(backendMessage || "Registration failed. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const login = async () => {
    if (!username.trim()) {
      setError("Username cannot be empty");
      return;
    }

    if (!password) {
      setError("Password is required");
      return;
    }

    if (keystrokes.length < MIN_KEYSTROKES) {
      setError(`Please type at least ${MIN_KEYSTROKES} keystrokes to authenticate`);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await axios.post(`${API_URL}/login`, {
        username,
        password,
        keystrokes
      });

      if (res.data.status !== "success") {
        setError(res.data.message || "Authentication failed");
        return;
      }

      if (!res.data.token) {
        setError("Authentication succeeded but no access token was issued.");
        return;
      }

      localStorage.setItem("authToken", res.data.token);
      localStorage.setItem("lastUsername", username.trim());

      const score = res.data.score.toFixed(4);
      setResult(score);

      // Show result for a moment, then redirect
      setTimeout(() => {
        navigate("/dashboard", {
          state: {
            username,
            score,
            status: res.data.status,
            threshold: res.data.threshold,
            components: res.data.components
          }
        });
        resetForm();
      }, 1500);
    } catch (err) {
      const backendMessage = err?.response?.data?.detail || err?.response?.data?.message;
      setError(backendMessage || "Login failed. User not found or incorrect authentication.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen w-full bg-gradient-to-br from-black via-purple-950 to-black text-white overflow-x-hidden flex flex-col pt-24">

      {/* Background Glow */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute w-[800px] h-[800px] bg-purple-700 opacity-20 blur-3xl rounded-full top-[-200px] left-[-200px]" />
        <div className="absolute w-[800px] h-[800px] bg-pink-600 opacity-20 blur-3xl rounded-full bottom-[-200px] right-[-200px]" />
      </div>

      {/* HERO + FORM */}
      <div className="flex-1 flex flex-col items-center justify-center text-center px-6">

        <h1 className="text-6xl font-extrabold bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-500 bg-clip-text text-transparent drop-shadow-lg animate-glow">
          AI Keystroke Security
        </h1>

        <p className="mt-4 text-lg text-gray-300 max-w-xl">
          Secure authentication using behavioral biometrics powered by AI.
        </p>

        {/* LOGIN CARD */}
        <div className="mt-12 bg-white/10 backdrop-blur-xl p-8 rounded-xl w-[420px] border border-white/10 shadow-lg transition-all duration-300 hover:border-purple-400/50">

          <div className="flex gap-4 mb-6">
            <button
              onClick={() => {
                setMode("login");
                clearAuthSession();
                resetForm();
              }}
              className={`flex-1 px-4 py-2 rounded-lg font-semibold transition ${
                mode === "login"
                  ? "bg-gradient-to-r from-cyan-400 to-blue-500 text-black"
                  : "bg-black/40 text-gray-300 hover:text-white"
              }`}
            >
              Login
            </button>
            <button
              onClick={() => {
                setMode("register");
                clearAuthSession();
                resetForm();
              }}
              className={`flex-1 px-4 py-2 rounded-lg font-semibold transition ${
                mode === "register"
                  ? "bg-gradient-to-r from-pink-400 to-purple-500 text-black"
                  : "bg-black/40 text-gray-300 hover:text-white"
              }`}
            >
              Register
            </button>
          </div>

          <h2 className="text-lg mb-6 text-gray-300">
            {mode === "register" ? "Create Account" : "Authenticate"}
          </h2>

          {error && (
            <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded text-red-300 text-sm">
              {error}
            </div>
          )}

          {info && (
            <div className="mb-4 p-3 bg-cyan-500/20 border border-cyan-500/50 rounded text-cyan-300 text-sm">
              {info}
            </div>
          )}

          <input
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full p-3 mb-4 bg-black/40 border border-white/10 rounded-lg outline-none transition hover:border-purple-400/50 focus:border-purple-400"
          />

          <input
            type="password"
            placeholder={mode === "register" ? "Create password" : "Password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full p-3 mb-4 bg-black/40 border border-white/10 rounded-lg outline-none transition hover:border-purple-400/50 focus:border-purple-400"
          />

          <input
            placeholder="Type here to create pattern..."
            value={typedText}
            onChange={(e) => setTypedText(e.target.value)}
            onKeyDown={handleKeyDown}
            onKeyUp={handleKeyUp}
            className="w-full p-3 mb-4 bg-black/40 border border-white/10 rounded-lg outline-none transition hover:border-purple-400/50 focus:border-purple-400"
          />

          <div className="text-xs text-gray-400 mb-4">
            Keystrokes recorded: {keystrokes.length}/{MIN_KEYSTROKES}
          </div>

          <div className="flex gap-4">
            <button
              onClick={mode === "register" ? register : login}
              disabled={loading}
              className={`flex-1 px-4 py-3 rounded-lg font-semibold transition transform ${
                mode === "register"
                  ? "bg-gradient-to-r from-pink-400 to-purple-500 hover:scale-105 disabled:opacity-50"
                  : "bg-gradient-to-r from-cyan-400 to-blue-500 hover:scale-105 disabled:opacity-50"
              } text-black disabled:cursor-not-allowed`}
            >
              {loading ? "Processing..." : (mode === "register" ? "Register" : "Login")}
            </button>
            <button
              onClick={resetForm}
              className="flex-1 bg-black/40 border border-white/10 text-gray-300 px-4 py-3 rounded-lg hover:text-white transition"
            >
              Reset
            </button>
          </div>

          {result && (
            <div className="mt-6 p-4 bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-400/50 rounded-lg">
              <p className="text-sm text-gray-300 mb-1">Authentication Score</p>
              <h2 className="text-3xl font-bold text-cyan-400">
                {result}
              </h2>
              <p className="text-xs text-gray-400 mt-2">
                {parseFloat(result) > 0.8 ? "✅ Access Granted" : "❌ Access Denied"}
              </p>
            </div>
          )}

        </div>

        <div className="mt-12 text-gray-300 text-base md:text-lg">
          <p>📝 Tip: Type naturally for better authentication accuracy</p>
        </div>

      </div>

      {/* FOOTER */}
      <footer className="w-full mt-10">
        <div className="h-[1px] bg-gradient-to-r from-transparent via-purple-500 to-transparent mb-4"></div>
        <div className="text-center text-gray-300 text-base md:text-lg pb-6">
          Made with <span className="text-pink-500">❤️</span> by <span className="text-white font-semibold">Ankit Mishra</span>
        </div>
      </footer>

    </div>
  );
}
