"use client";

import { useEffect, useState } from "react";
import AuthGuard from "../../components/AuthGuard";
import Nav from "../../components/Nav";
import { apiGet, apiRequest } from "../../components/api";

export default function SourcesPage() {
  const [sources, setSources] = useState<any[]>([]);

  const load = async () => setSources(await apiGet("/sources"));

  useEffect(() => {
    load();
  }, []);

  return (
    <AuthGuard>
      <main className="shell grid">
        <Nav />
        <div className="card">
          <h2>Sources</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th><th>Base URL</th><th>Enabled</th><th>Action</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => (
                <tr key={s.id}>
                  <td>{s.name}</td>
                  <td>{s.base_url}</td>
                  <td>{String(s.enabled)}</td>
                  <td>
                    <button onClick={async () => { await apiRequest(`/sources/${s.id}`, "PATCH", { enabled: !s.enabled }); await load(); }}>
                      {s.enabled ? "Disable" : "Enable"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </AuthGuard>
  );
}
