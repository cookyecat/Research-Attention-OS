import "@fontsource-variable/inter";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import DeliveryListener from "@/components/DeliveryListener";
import VisitContinuityTracker from "@/components/VisitContinuityTracker";

export const metadata = {
  title: "Research Attention OS",
  description: "Spend human attention only where it changes cognition.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: `(function(){try{var t=localStorage.getItem('raos-theme')||'system';var s=localStorage.getItem('raos-text-size')||'default';var b=localStorage.getItem('raos-bionic-reading')||'off';var skin=localStorage.getItem('raos-reading-skin')||'classic';var st=parseInt(localStorage.getItem('raos-bionic-strength')||'60',10);st=Math.max(10,Math.min(100,isFinite(st)?Math.round(st/5)*5:60));var rw=localStorage.getItem('raos-bionic-weight')||'3';var legacy={soft:2,medium:3,strong:4};var w=legacy[rw]||parseInt(rw,10)||3;w=Math.max(1,Math.min(5,w));var classic={1:400,2:600,3:700,4:800,5:900};var soft={1:460,2:520,3:580,4:640,5:700};var fw=skin==='bionic-soft'?soft[w]:classic[w];var r=t==='system'?(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'):t;document.documentElement.dataset.theme=r;document.documentElement.dataset.fontScale=s;document.documentElement.dataset.bionic=b;document.documentElement.dataset.bionicStrength=String(st);document.documentElement.dataset.bionicWeight=String(w);document.documentElement.dataset.readingSkin=skin;document.documentElement.style.setProperty('--bionic-weight',String(fw));document.documentElement.style.setProperty('--bionic-shadow','none');}catch(e){}})();` }} />
      </head>
      <body>
        <VisitContinuityTracker />
        <div className="app-shell">
          <Sidebar />
          <main className="main-content">{children}</main>
        </div>
        <DeliveryListener />
      </body>
    </html>
  );
}
