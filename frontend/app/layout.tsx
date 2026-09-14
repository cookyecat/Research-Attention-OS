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
        <script dangerouslySetInnerHTML={{ __html: `(function(){try{var t=localStorage.getItem('raos-theme')||'system';var s=localStorage.getItem('raos-text-size')||'default';var b=localStorage.getItem('raos-bionic-reading')||'off';var st=parseInt(localStorage.getItem('raos-bionic-strength')||'60',10);st=Math.max(10,Math.min(100,isFinite(st)?Math.round(st/5)*5:60));var rw=localStorage.getItem('raos-bionic-weight')||'3';var legacy={soft:2,medium:3,strong:4};var w=legacy[rw]||parseInt(rw,10)||3;w=Math.max(1,Math.min(5,w));var styles={1:{w:'400',s:'none'},2:{w:'600',s:'none'},3:{w:'700',s:'0.3px 0 0 currentColor, -0.3px 0 0 currentColor, 0 0.3px 0 currentColor, 0 -0.3px 0 currentColor'},4:{w:'800',s:'0.5px 0 0 currentColor, -0.5px 0 0 currentColor, 0 0.5px 0 currentColor, 0 -0.5px 0 currentColor'},5:{w:'900',s:'0.75px 0 0 currentColor, -0.75px 0 0 currentColor, 0 0.75px 0 currentColor, 0 -0.75px 0 currentColor'}};var r=t==='system'?(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'):t;document.documentElement.dataset.theme=r;document.documentElement.dataset.fontScale=s;document.documentElement.dataset.bionic=b;document.documentElement.dataset.bionicStrength=String(st);document.documentElement.dataset.bionicWeight=String(w);document.documentElement.style.setProperty('--bionic-weight',styles[w].w);document.documentElement.style.setProperty('--bionic-shadow',b==='on'?styles[w].s:'none');}catch(e){}})();` }} />
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
