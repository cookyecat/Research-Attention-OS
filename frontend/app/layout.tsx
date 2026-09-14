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
        <script dangerouslySetInnerHTML={{ __html: `(function(){try{var t=localStorage.getItem('raos-theme')||'system';var s=localStorage.getItem('raos-text-size')||'default';var b=localStorage.getItem('raos-bionic-reading')||'off';var w=localStorage.getItem('raos-bionic-weight')||'medium';var weights={soft:'600',medium:'700',strong:'800'};var r=t==='system'?(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'):t;document.documentElement.dataset.theme=r;document.documentElement.dataset.fontScale=s;document.documentElement.dataset.bionic=b;document.documentElement.style.setProperty('--bionic-weight',weights[w]||'700');}catch(e){}})();` }} />
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
