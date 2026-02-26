"use client";

import { useEffect, useState } from "react";
import AuthGuard from "../../components/AuthGuard";
import Nav from "../../components/Nav";
import { apiGet, apiRequest } from "../../components/api";

export default function SettingsPage() {
  const [scoring, setScoring] = useState("{}");
  const [notifications, setNotifications] = useState("{}");

  useEffect(() => {
    apiGet("/settings/scoring").then((x) => setScoring(JSON.stringify(x, null, 2))).catch(console.error);
    apiGet("/settings/notifications").then((x) => setNotifications(JSON.stringify(x, null, 2))).catch(console.error);
  }, []);

  return (
    <AuthGuard>
      <main className="shell grid">
        <Nav />
        <div className="grid grid-2">
          <div className="card grid">
            <h2>Scoring Config</h2>
            <textarea rows={20} value={scoring} onChange={(e) => setScoring(e.target.value)} />
            <button onClick={async () => await apiRequest("/settings/scoring", "PUT", JSON.parse(scoring))}>Save</button>
          </div>
          <div className="card grid">
            <h2>Notification Config</h2>
            <textarea rows={20} value={notifications} onChange={(e) => setNotifications(e.target.value)} />
            <button onClick={async () => await apiRequest("/settings/notifications", "PUT", JSON.parse(notifications))}>Save</button>
          </div>
        </div>
      </main>
    </AuthGuard>
  );
}
