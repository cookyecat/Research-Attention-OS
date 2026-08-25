import Link from "next/link";
import "./globals.css";

export const metadata = {
  title: "Research Attention OS",
  description: "Allocate finite attention to information that can change the Kernel.",
};

const LINKS = [
  ["/", "Home"],
  ["/inbox", "Inbox"],
  ["/attention", "Attention"],
  ["/kernel", "Kernel"],
  ["/watch", "Watch"],
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <nav className="side">
            <h1>RAOS</h1>
            <p>Attention is the scarce resource. Documents are not the unit of cognition.</p>
            {LINKS.map(([href, label]) => (
              <Link key={href} href={href}>
                {label}
              </Link>
            ))}
          </nav>
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
