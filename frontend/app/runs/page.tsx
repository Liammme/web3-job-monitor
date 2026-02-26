"use client";

import { useEffect, useState } from "react";
import AuthGuard from "../../components/AuthGuard";
import Nav from "../../components/Nav";
import { apiGet } from "../../components/api";

export default function RunsPage() {
  const [runs, setRuns] = useState<any[]>([]);

  useEffect(() => {
    apiGet("/runs").then(setRuns).catch(console.error);
  }, []);

  return (
    <AuthGuard>
      <main className="shell grid">
        <Nav />
        <div className="card">
          <h2>Crawl Runs</h2>
          <table className="table">
            <thead>
              <tr>
                <th>ID</th><th>Source</th><th>Status</th><th>Fetched</th><th>New</th><th>High</th><th>Error</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td>
                  <td>{r.source_id}</td>
                  <td>{r.status}</td>
                  <td>{r.fetched_count}</td>
                  <td>{r.new_count}</td>
                  <td>{r.high_priority_count}</td>
                  <td>{r.error_summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </AuthGuard>
  );
}
