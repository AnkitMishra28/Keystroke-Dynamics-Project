import { useState, useEffect, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend
} from "recharts";

const API_URL = "https://keystroke-dynamics-project.onrender.com";

export default function Dashboard() {
  const location = useLocation();
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [score, setScore] = useState("");
  const [status, setStatus] = useState("");
  const [threshold, setThreshold] = useState(null);
  const [components, setComponents] = useState(null);
  const [analytics, setAnalytics] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    // Get username from navigation state or localStorage
    if (location.state?.username) {
      setUsername(location.state.username);
      setScore(location.state.score);
      setStatus(location.state.status);
      setThreshold(location.state.threshold ?? null);
      setComponents(location.state.components ?? null);
      // Store in localStorage for page refresh
      localStorage.setItem("lastUsername", location.state.username);
    } else {
      // Try to get from localStorage
      const stored = localStorage.getItem("lastUsername");
      if (stored) {
        setUsername(stored);
      } else {
        navigate("/");
        return;
      }
    }
  }, [location, navigate]);

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const token = localStorage.getItem("authToken");
      if (!token) {
        setError("Session expired. Please login again.");
        navigate("/");
        return;
      }

      const headers = {
        Authorization: `Bearer ${token}`
      };

      const [analyticsRes, alertsRes] = await Promise.all([
        axios.get(`${API_URL}/analytics/${username}`, { headers }),
        axios.get(`${API_URL}/alerts/${username}`, { headers })
      ]);

      const sessions = analyticsRes.data.sessions.map((s, i) => ({
        id: i + 1,
        score: Number(s.score),
        status: s.status,
        threshold: s.threshold !== undefined ? Number(s.threshold) : null,
        maxSimilarity: s.max_similarity !== undefined ? Number(s.max_similarity) : null,
        statScore: s.stat_score !== undefined ? Number(s.stat_score) : null,
        sequenceLength: s.sequence_length !== undefined ? Number(s.sequence_length) : null,
        time: s.time ? new Date(s.time).toLocaleString() : "Unknown"
      }));

      setAnalytics(sessions);

      const recentAlerts = (alertsRes.data.alerts || []).map((a, i) => ({
        id: i + 1,
        reason: a.reason || "unknown",
        ip: a.ip || "unknown",
        time: a.time ? new Date(a.time).toLocaleString() : "Unknown"
      }));
      setAlerts(recentAlerts);

      if (sessions.length > 0 && sessions[sessions.length - 1].threshold !== null) {
        const latest = sessions[sessions.length - 1];
        setThreshold((prev) => prev ?? latest.threshold);
        setComponents((prev) => prev ?? {
          max_similarity: latest.maxSimilarity,
          stat_score: latest.statScore
        });
      }
    } catch (err) {
      if (err.response?.status === 401 || err.response?.status === 403) {
        localStorage.removeItem("authToken");
        localStorage.removeItem("lastUsername");
        setError("Session expired or unauthorized. Please login again.");
        navigate("/");
        return;
      }
      setError("Failed to load analytics. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [username, navigate]);

  useEffect(() => {
    if (username) {
      fetchAnalytics();
    }
  }, [username, fetchAnalytics]);

  const handleLogout = () => {
    localStorage.removeItem("authToken");
    localStorage.removeItem("lastUsername");
    navigate("/");
  };

  const metricColorClass = (value, rowThreshold) => {
    if (value === null || value === undefined || rowThreshold === null || rowThreshold === undefined) {
      return "text-gray-300";
    }
    return value >= rowThreshold ? "text-green-400" : "text-red-400";
  };

  const keyCountColorClass = (value) => {
    if (value === null || value === undefined) {
      return "text-gray-300";
    }
    return value >= 20 ? "text-green-400" : "text-red-400";
  };

  if (loading) {
    return (
      <div className="min-h-screen w-full bg-gradient-to-br from-black via-purple-950 to-black text-white flex items-center justify-center pt-24">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400"></div>
          <p className="mt-4 text-gray-300">Loading analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-black via-purple-950 to-black text-white overflow-x-hidden pt-24">

      {/* Background Glow */}
      <div className="absolute w-[800px] h-[800px] bg-purple-700 opacity-20 blur-3xl rounded-full top-0 left-[-200px]" />
      <div className="absolute w-[800px] h-[800px] bg-pink-600 opacity-20 blur-3xl rounded-full bottom-0 right-[-200px]" />

      {/* Content */}
      <div className="relative z-10 max-w-6xl mx-auto px-6 pb-10">

        {/* Header */}
        <div className="flex justify-between items-center mb-10">
          <div>
            <h1 className="text-4xl font-extrabold bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-500 bg-clip-text text-transparent">
              Analytics Dashboard
            </h1>
            <p className="text-gray-400 mt-2">Welcome back, <span className="text-cyan-300 font-semibold">{username}</span></p>
          </div>
          <button
            onClick={handleLogout}
            className="bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 text-red-300 px-6 py-2 rounded-lg transition"
          >
            Logout
          </button>
        </div>

        {/* Stats Cards */}
        {score && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
            <div className="bg-white/5 backdrop-blur-xl p-6 rounded-xl border border-white/10 hover:border-cyan-400/50 transition">
              <p className="text-gray-400 text-sm mb-2">Latest Auth Score</p>
              <h2 className="text-3xl font-bold text-cyan-400">{score}</h2>
              <p className="text-xs text-gray-500 mt-2">Last authentication</p>
            </div>

            <div className="bg-white/5 backdrop-blur-xl p-6 rounded-xl border border-white/10 hover:border-purple-400/50 transition">
              <p className="text-gray-400 text-sm mb-2">Status</p>
              <h2 className="text-2xl font-bold">
                {status === "success" ? (
                  <span className="text-green-400">✅ Success</span>
                ) : (
                  <span className="text-red-400">❌ Failed</span>
                )}
              </h2>
              <p className="text-xs text-gray-500 mt-2">{status === "success" ? "Access granted" : "Access denied"}</p>
            </div>

            <div className="bg-white/5 backdrop-blur-xl p-6 rounded-xl border border-white/10 hover:border-pink-400/50 transition">
              <p className="text-gray-400 text-sm mb-2">Total Sessions</p>
              <h2 className="text-3xl font-bold text-pink-400">{analytics.length}</h2>
              <p className="text-xs text-gray-500 mt-2">Authentication attempts</p>
            </div>

            <div className="bg-white/5 backdrop-blur-xl p-6 rounded-xl border border-white/10 hover:border-cyan-300/50 transition">
              <p className="text-gray-400 text-sm mb-2">Decision Quality</p>
              <div className="space-y-1 text-sm">
                <p className="text-gray-300">Threshold: <span className="text-cyan-300 font-semibold">{threshold !== null ? threshold.toFixed(4) : "N/A"}</span></p>
                <p className="text-gray-300">Max Similarity: <span className="text-cyan-300 font-semibold">{components?.max_similarity !== null && components?.max_similarity !== undefined ? Number(components.max_similarity).toFixed(4) : "N/A"}</span></p>
                <p className="text-gray-300">Stat Score: <span className="text-cyan-300 font-semibold">{components?.stat_score !== null && components?.stat_score !== undefined ? Number(components.stat_score).toFixed(4) : "N/A"}</span></p>
              </div>
              <p className="text-xs text-gray-500 mt-2">Hybrid scoring overview</p>
            </div>
          </div>
        )}

        {error && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300">
            {error}
          </div>
        )}

        <div className="mb-6 p-4 bg-cyan-500/10 border border-cyan-400/30 rounded-lg text-cyan-200 text-sm">
          Register samples are used for enrollment/profile building. Analytics and session history track login attempts only.
        </div>

        {alerts.length > 0 ? (
          <div className="mb-10 bg-red-500/10 backdrop-blur-xl p-6 rounded-xl border border-red-400/30">
            <h2 className="text-xl font-bold mb-4 text-red-300">Suspicious Attempts Alert</h2>
            <div className="space-y-2 text-sm">
              {alerts.slice(0, 5).map((alert) => (
                <div key={alert.id} className="flex flex-col md:flex-row md:items-center md:justify-between bg-black/30 border border-red-400/20 rounded-lg px-4 py-3">
                  <p className="text-red-200">Reason: <span className="font-semibold">{alert.reason}</span></p>
                  <p className="text-gray-300">IP: {alert.ip}</p>
                  <p className="text-gray-400">{alert.time}</p>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {/* Chart */}
        {analytics.length > 0 ? (
          <div className="bg-white/5 backdrop-blur-xl p-8 rounded-xl border border-white/10 mb-10">
            <h2 className="text-xl font-bold mb-6 text-gray-200">Authentication Scores Trend</h2>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={analytics}>
                <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                <XAxis
                  dataKey="id"
                  stroke="#aaa"
                  label={{ value: "Attempt Number", position: "insideBottomRight", offset: -5 }}
                />
                <YAxis
                  stroke="#aaa"
                  domain={[0, 1]}
                  label={{ value: "Score", angle: -90, position: "insideLeft" }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(0, 0, 0, 0.8)",
                    border: "1px solid #666",
                    borderRadius: "8px"
                  }}
                  labelStyle={{ color: "#fff" }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#00ffff"
                  strokeWidth={3}
                  dot={{ fill: "#00ffff", r: 4 }}
                  activeDot={{ r: 6 }}
                  name="Auth Score"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : null}

        {/* Sessions Table */}
        {analytics.length > 0 ? (
          <div className="bg-white/5 backdrop-blur-xl p-8 rounded-xl border border-white/10">
            <h2 className="text-xl font-bold mb-6 text-gray-200">Session History</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left py-3 px-4 text-gray-400 font-semibold">#</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-semibold">Score</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-semibold">Threshold</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-semibold">Max Sim</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-semibold">Stat</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-semibold">Keys</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-semibold">Status</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-semibold">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {analytics.map((session, idx) => (
                    <tr key={idx} className="border-b border-white/5 hover:bg-white/5 transition">
                      <td className="py-3 px-4 text-gray-300">{session.id}</td>
                      <td className="py-3 px-4">
                        <span className="text-cyan-400 font-mono font-semibold">{session.score.toFixed(4)}</span>
                      </td>
                      <td className="py-3 px-4 text-cyan-300 font-mono">
                        {session.threshold !== null ? session.threshold.toFixed(4) : "N/A"}
                      </td>
                      <td className={`py-3 px-4 font-mono ${metricColorClass(session.maxSimilarity, session.threshold)}`}>
                        {session.maxSimilarity !== null ? session.maxSimilarity.toFixed(4) : "N/A"}
                      </td>
                      <td className={`py-3 px-4 font-mono ${metricColorClass(session.statScore, session.threshold)}`}>
                        {session.statScore !== null ? session.statScore.toFixed(4) : "N/A"}
                      </td>
                      <td className={`py-3 px-4 ${keyCountColorClass(session.sequenceLength)}`}>
                        {session.sequenceLength !== null ? session.sequenceLength : "N/A"}
                      </td>
                      <td className="py-3 px-4">
                        {session.status === "success" ? (
                          <span className="text-green-400">✅ Success</span>
                        ) : (
                          <span className="text-red-400">❌ Failed</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-gray-400">{session.time}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="bg-white/5 backdrop-blur-xl p-8 rounded-xl border border-white/10 text-center">
            <p className="text-gray-400">No session history yet. Authenticate to see data.</p>
          </div>
        )}

      </div>

    </div>
  );
}
