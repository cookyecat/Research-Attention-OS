"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import PreferencesPanel from "@/components/PreferencesPanel";

const LINKS = [
  ["/", "Today", "What needs you now"],
  ["/inbox", "Inbox", "Add information"],
  ["/attention", "Attention", "Your filtered world"],
  ["/watch", "Watch", "Delegated monitoring"],
  ["/kernel", "Context", "What RAOS knows"],
] as const;

export default function Sidebar() {
  const pathname = usePathname();
  const systemActive = pathname.startsWith("/system");
  return (
    <aside className="sidebar">
      <div className="brand-block">
        <Link className="brand" href="/">RAOS</Link>
        <span className="brand-subtitle">Research Attention OS</span>
      </div>
      <div>
        <div className="nav-section-label">User space</div>
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
      </div>
      <div className="sidebar-bottom">
        <PreferencesPanel />
        <Link className={systemActive ? "system-entry active" : "system-entry"} href="/system">
          <span className="system-icon">⌘</span>
          <span>
            <strong>RAOS System</strong>
            <small>Inspect internals</small>
          </span>
        </Link>
      </div>
    </aside>
  );
}
