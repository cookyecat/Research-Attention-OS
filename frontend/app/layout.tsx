import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata = {
  title: "Research Attention OS",
  description: "Spend human attention only where it changes cognition.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <Sidebar />
          <main className="main-content">{children}</main>
        </div>
      </body>
    </html>
  );
}
