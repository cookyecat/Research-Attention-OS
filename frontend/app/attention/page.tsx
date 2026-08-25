import { Suspense } from "react";
import AttentionPage from "./AttentionClient";

export default function Page() {
  return (
    <Suspense fallback={<p>Loading attention…</p>}>
      <AttentionPage />
    </Suspense>
  );
}
