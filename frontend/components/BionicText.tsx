"use client";

import React, { useEffect, useState } from "react";

const READING_PREFERENCES_EVENT = "raos-reading-preferences-changed";

function currentStrength() {
  if (typeof document === "undefined") return 0.6;
  const raw = Number(document.documentElement.dataset.bionicStrength || "60");
  return Math.max(0.1, Math.min(1, raw / 100));
}

function renderToken(token: string, key: number, strength: number) {
  if (/^\s+$/.test(token)) return <React.Fragment key={key}>{token}</React.Fragment>;
  const match = token.match(/^([^A-Za-z0-9À-ÖØ-öø-ÿ]*)([A-Za-z0-9À-ÖØ-öø-ÿ]+(?:['’][A-Za-z]+)?)(.*)$/);
  if (!match) return <React.Fragment key={key}>{token}</React.Fragment>;
  const [, before, word, after] = match;
  const chars = Array.from(word);
  if (chars.length < 2) return <React.Fragment key={key}>{token}</React.Fragment>;
  const cut = chars.length <= 2 ? chars.length : Math.max(1, Math.ceil(chars.length * strength));
  return (
    <React.Fragment key={key}>
      {before}<span className="bionic-prefix" style={{ textShadow: "var(--bionic-shadow, none)" }}>{chars.slice(0, cut).join("")}</span>{chars.slice(cut).join("")}{after}
    </React.Fragment>
  );
}

export default function BionicText({ text, strength }: { text: string; strength?: number }) {
  const [globalStrength, setGlobalStrength] = useState(0.6);

  useEffect(() => {
    const update = () => setGlobalStrength(currentStrength());
    update();
    window.addEventListener(READING_PREFERENCES_EVENT, update);
    return () => window.removeEventListener(READING_PREFERENCES_EVENT, update);
  }, []);

  const effectiveStrength = Math.max(0.1, Math.min(1, strength ?? globalStrength));
  return <>{text.split(/(\s+)/).map((token, key) => renderToken(token, key, effectiveStrength))}</>;
}
