"use client";

import { useEffect, useState } from "react";

type ThemePreference = "dark" | "light" | "system";
type TextSize = "compact" | "default" | "large";

const THEME_KEY = "raos-theme";
const SIZE_KEY = "raos-text-size";

function resolveTheme(preference: ThemePreference) {
  if (preference !== "system") return preference;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function applyPreferences(theme: ThemePreference, size: TextSize) {
  document.documentElement.dataset.theme = resolveTheme(theme);
  document.documentElement.dataset.fontScale = size;
}

export default function PreferencesPanel() {
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState<ThemePreference>("system");
  const [size, setSize] = useState<TextSize>("default");

  useEffect(() => {
    const storedTheme = (localStorage.getItem(THEME_KEY) as ThemePreference | null) || "system";
    const storedSize = (localStorage.getItem(SIZE_KEY) as TextSize | null) || "default";
    setTheme(storedTheme);
    setSize(storedSize);
    applyPreferences(storedTheme, storedSize);
    const media = window.matchMedia("(prefers-color-scheme: light)");
    const updateSystem = () => {
      if ((localStorage.getItem(THEME_KEY) || "system") === "system") {
        document.documentElement.dataset.theme = media.matches ? "light" : "dark";
      }
    };
    media.addEventListener("change", updateSystem);
    return () => media.removeEventListener("change", updateSystem);
  }, []);

  function changeTheme(next: ThemePreference) {
    setTheme(next);
    localStorage.setItem(THEME_KEY, next);
    applyPreferences(next, size);
  }

  function changeSize(next: TextSize) {
    setSize(next);
    localStorage.setItem(SIZE_KEY, next);
    applyPreferences(theme, next);
  }

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button className="preferences-entry" onClick={() => setOpen(true)}>
        <span className="preferences-icon">Aa</span>
        <span><strong>Preferences</strong><small>Appearance & reading</small></span>
      </button>
      {open && (
        <div className="preferences-backdrop" onMouseDown={(event) => { if (event.currentTarget === event.target) setOpen(false); }}>
          <section className="preferences-panel" role="dialog" aria-modal="true" aria-label="RAOS Preferences">
            <header><div><div className="eyebrow">Preferences</div><h2>Make RAOS comfortable to read.</h2></div><button className="icon-button" onClick={() => setOpen(false)} aria-label="Close">×</button></header>
            <div className="preference-row">
              <div><strong>Theme</strong><p>Changes the entire RAOS interface.</p></div>
              <div className="segmented-control">
                {(["dark", "light", "system"] as ThemePreference[]).map((value) => <button key={value} className={theme === value ? "active" : ""} onClick={() => changeTheme(value)}>{value[0].toUpperCase() + value.slice(1)}</button>)}
              </div>
            </div>
            <div className="preference-row">
              <div><strong>Text size</strong><p>Applies to navigation, cards, and Reader.</p></div>
              <div className="segmented-control">
                {(["compact", "default", "large"] as TextSize[]).map((value) => <button key={value} className={size === value ? "active" : ""} onClick={() => changeSize(value)}>{value === "default" ? "Default" : value[0].toUpperCase() + value.slice(1)}</button>)}
              </div>
            </div>
            <p className="preferences-note">Saved in this browser. These are RAOS preferences, not developer-tool settings.</p>
          </section>
        </div>
      )}
    </>
  );
}
