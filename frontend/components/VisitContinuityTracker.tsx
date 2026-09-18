"use client";

import { useEffect } from "react";
import { touchVisitContinuity } from "@/lib/visitContinuity";

export default function VisitContinuityTracker() {
  useEffect(() => {
    const touch = () => touchVisitContinuity();
    touch();
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") touch();
    }, 60_000);
    const onVisibility = () => { if (document.visibilityState === "visible") touch(); };
    const onPageHide = () => touch();
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("pagehide", onPageHide);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("pagehide", onPageHide);
    };
  }, []);
  return null;
}