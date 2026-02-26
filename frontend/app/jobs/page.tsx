"use client";

import { useEffect, useState } from "react";
import AuthGuard from "../../components/AuthGuard";
import Nav from "../../components/Nav";
import { apiGet, apiRequest } from "../../components/api";

export default function JobsPage() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    const data = await apiGet(`/jobs?q=${encodeURIComponent(q)}`);
    setJobs(data);
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <AuthGuard>
      <main className="shell grid">
        <Nav />
        <div className="card grid">
          <h2>Jobs</h2>
          <div className="grid grid-2">
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="关键词过滤" />
            <button onClick={load}>搜索</button>
          </div>
          <button onClick={async () => { await apiRequest("/crawl/trigger", "POST"); await load(); }}>手动触发抓取</button>
          {loading ? <p>loading...</p> : null}
          <table className="table">
            <thead>
              <tr>
                <th>Title</th><th>Company</th><th>Location</th><th>Score</th><th>Link</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id}>
                  <td>{job.title}</td>
                  <td>{job.company}</td>
                  <td>{job.location}</td>
                  <td className={job.score?.decision === "high" ? "badge-high" : "badge-low"}>
                    {job.score ? `${job.score.total_score} (${job.score.decision})` : "-"}
                  </td>
                  <td><a href={job.canonical_url} target="_blank">open</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </AuthGuard>
  );
}
