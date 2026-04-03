import { Link, useLocation } from "react-router-dom";

export default function Navbar() {
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  const linkClass = (path) => `
    transition relative py-2
    ${isActive(path)
      ? "text-cyan-400 font-semibold"
      : "text-gray-300 hover:text-white"
    }
  `;

  return (
    <div className="fixed top-0 w-full flex justify-between items-center px-10 py-4 z-50 bg-black/30 backdrop-blur-lg border-b border-white/10">

      <Link to="/" className="text-2xl font-extrabold text-white tracking-wide hover:text-cyan-400 transition">
        KeystrokeAI
      </Link>

      <div className="flex gap-8">
        <Link to="/" className={linkClass("/")}>
          Home
        </Link>
        <Link to="/dashboard" className={linkClass("/dashboard")}>
          Dashboard
        </Link>
        <Link to="/about" className={linkClass("/about")}>
          About
        </Link>
      </div>

      <Link
        to="/"
        className="bg-gradient-to-r from-cyan-400 to-blue-500 text-black px-4 py-2 rounded-lg hover:scale-105 transition font-semibold"
      >
        Home
      </Link>

    </div>
  );
}