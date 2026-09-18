import { Suspense } from "react";
import InboxPage from "./InboxClient";

export default function Page() {
  return (
    <Suspense fallback={<p>Loading Inbox…</p>}>
      <InboxPage />
    </Suspense>
  );
}
