import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata = {
  title: "Research Attention OS",
  description: "Spend human attention only where it changes cognition.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: `(function(){try{var t=localStorage.getItem('raos-theme')||'system';var s=localStorage.getItem('raos-text-size')||'default';var r=t==='system'?(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'):t;document.documentElement.dataset.theme=r;document.documentElement.dataset.fontScale=s;}catch(e){}})();` }} />
      </head>
      <body>
        <div className="app-shell">
          <Sidebar />
          <main className="main-content">{children}</main>
        </div>
      </body>
    </html>
  );
}
