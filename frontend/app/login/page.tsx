"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiBase } from "../../components/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function onLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const res = await fetch(`${apiBase}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      setError("登录失败，请检查账号密码");
      return;
    }
    const data = await res.json();
    localStorage.setItem("token", data.access_token);
    router.push("/jobs");
  }

  return (
    <main className="shell">
      <div className="card" style={{ maxWidth: 420, margin: "80px auto" }}>
        <h2>Web3 岗位监控登录</h2>
        <form onSubmit={onLogin} className="grid">
          <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="username" />
          <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" type="password" />
          <button type="submit">登录</button>
        </form>
        {error && <p style={{ color: "#b02a37" }}>{error}</p>}
      </div>
    </main>
  );
}
