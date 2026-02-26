"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

const items = [
  ["/jobs", "Jobs"],
  ["/runs", "Runs"],
  ["/sources", "Sources"],
  ["/settings", "Settings"],
];

export default function Nav() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div className="nav">
      {items.map(([href, label]) => (
        <Link key={href} href={href} style={{ background: pathname === href ? "#e4f3ee" : "transparent" }}>
          {label}
        </Link>
      ))}
      <button
        onClick={() => {
          localStorage.removeItem("token");
          router.push("/login");
        }}
      >
        Logout
      </button>
    </div>
  );
}
