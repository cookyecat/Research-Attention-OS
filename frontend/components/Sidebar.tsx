"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  ["/", "Today", "What needs you now"],
  ["/inbox", "Inbox", "Add information"],
  ["/attention", "Attention", "Your filtered world"],
  ["/watch", "Watch", "Delegated monitoring"],
  ["/kernel", "Kernel", "Your cognitive state"],
] as const;

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sidebar">
      <div className="brand-block">
        <Link className="brand" href="/">RAOS</Link>
        <span className="brand-subtitle">Research Attention OS</span>
      </div>
      <nav className="primary-nav" aria-label="Primary navigation">
        {LINKS.map(([href, label, description]) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link className={active ? "nav-item active" : "nav-item"} href={href} key={href}>
              <span>{label}</span>
              <small>{description}</small>
            </Link>
          );
        })}
      </nav>
      <div className="sidebar-footer">
        <span className="status-dot" />
        <div>
          <strong>Dogfood live</strong>
          <small>Research-aligned cognition</small>
        </div>
      </div>
    </aside>
  );
}
