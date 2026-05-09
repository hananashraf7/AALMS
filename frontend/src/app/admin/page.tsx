"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function AdminLogin() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      const res = await fetch('http://localhost:8000/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem("adminAuth", data.username);
        localStorage.setItem("adminName", data.name);
        router.push("/admin/dashboard");
      } else {
        setError(data.detail || "Invalid credentials");
      }
    } catch {
      setError("Network error communicating with backend");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center">
      <div className="w-full max-w-sm space-y-8">

        {/* Logo */}
        <div className="flex flex-col items-center gap-3">
          <div className="w-14 h-14 rounded-2xl bg-[#1a1a1a] flex items-center justify-center shadow-md">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-7 h-7 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-bold tracking-tight text-[#1a1a1a]">Admin Access</h1>
            <p className="text-gray-400 text-xs mt-1 tracking-wide">AALMS — Secure Portal</p>
          </div>
        </div>

        {/* Login Card */}
        <div className="card-panel p-7 space-y-5">
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-[11px] font-semibold mb-1.5 text-gray-500 tracking-wide">Username</label>
              <input
                type="text"
                className="w-full p-3.5 rounded-xl form-input"
                placeholder="Enter username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                autoComplete="username"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold mb-1.5 text-gray-500 tracking-wide">Password</label>
              <input
                type="password"
                className="w-full p-3.5 rounded-xl form-input"
                placeholder="Enter password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-100 text-red-600 p-3 rounded-xl text-xs font-medium text-center">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full btn-primary py-3.5 rounded-xl"
            >
              {isLoading ? 'Verifying...' : 'Sign In'}
            </button>
          </form>

          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-gray-100" />
            <p className="text-[10px] text-gray-300 tracking-wider">Secured by AALMS</p>
            <div className="flex-1 h-px bg-gray-100" />
          </div>
        </div>
      </div>
    </div>
  );
}
