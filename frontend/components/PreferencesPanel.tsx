"use client";

import { useEffect, useState } from "react";

type ThemePreference = "dark" | "light" | "system";
type TextSize = "compact" | "default" | "large";
type BionicMode = "off" | "on";
type BionicWeight = "soft" | "medium" | "strong";

const THEME_KEY = "raos-theme";
const SIZE_KEY = "raos-text-size";
const BIONIC_KEY = "raos-bionic-reading";
const BIONIC_WEIGHT_KEY = "raos-bionic-weight";
const BIONIC_WEIGHTS: Record<BionicWeight, string> = { soft: "600", medium: "700", strong: "800" };

function resolveTheme(preference: ThemePreference) {
  if (preference !== "system") return preference;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function applyPreferences(theme: ThemePreference, size: TextSize, bionic: BionicMode, weight: BionicWeight) {
  document.documentElement.dataset.theme = resolveTheme(theme);
  document.documentElement.dataset.fontScale = size;
  document.documentElement.dataset.bionic = bionic;
  document.documentElement.style.setProperty("--bionic-weight", BIONIC_WEIGHTS[weight]);
}

export default function PreferencesPanel() {
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState<ThemePreference>("system");
  const [size, setSize] = useState<TextSize>("default");
  const [bionic, setBionic] = useState<BionicMode>("off");
  const [bionicWeight, setBionicWeight] = useState<BionicWeight>("medium");

  useEffect(() => {
    const storedTheme = (localStorage.getItem(THEME_KEY) as ThemePreference | null) || "system";
    const storedSize = (localStorage.getItem(SIZE_KEY) as TextSize | null) || "default";
    const storedBionic = (localStorage.getItem(BIONIC_KEY) as BionicMode | null) || "off";
    const storedWeight = (localStorage.getItem(BIONIC_WEIGHT_KEY) as BionicWeight | null) || "medium";
    setTheme(storedTheme); setSize(storedSize); setBionic(storedBionic); setBionicWeight(storedWeight);
    applyPreferences(storedTheme, storedSize, storedBionic, storedWeight);
    const media = window.matchMedia("(prefers-color-scheme: light)");
    const updateSystem = () => {
      if ((localStorage.getItem(THEME_KEY) || "system") === "system") document.documentElement.dataset.theme = media.matches ? "light" : "dark";
    };
    media.addEventListener("change", updateSystem);
    return () => media.removeEventListener("change", updateSystem);
  }, []);

  function persist(nextTheme = theme, nextSize = size, nextBionic = bionic, nextWeight = bionicWeight) {
    localStorage.setItem(THEME_KEY, nextTheme); localStorage.setItem(SIZE_KEY, nextSize);
    localStorage.setItem(BIONIC_KEY, nextBionic); localStorage.setItem(BIONIC_WEIGHT_KEY, nextWeight);
    applyPreferences(nextTheme, nextSize, nextBionic, nextWeight);
  }
  function changeTheme(next: ThemePreference) { setTheme(next); persist(next, size, bionic, bionicWeight); }
  function changeSize(next: TextSize) { setSize(next); persist(theme, next, bionic, bionicWeight); }
  function changeBionic(next: BionicMode) { setBionic(next); persist(theme, size, next, bionicWeight); }
  function changeWeight(next: BionicWeight) { setBionicWeight(next); persist(theme, size, bionic, next); }

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey); return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return <>
    <button className="preferences-entry" onClick={() => setOpen(true)}><span className="preferences-icon">Aa</span><span><strong>Preferences</strong><small>Appearance & reading</small></span></button>
    {open && <div className="preferences-backdrop" onMouseDown={(event) => { if (event.currentTarget === event.target) setOpen(false); }}>
      <section className="preferences-panel" role="dialog" aria-modal="true" aria-label="RAOS Preferences">
        <header><div><div className="eyebrow">Preferences</div><h2>Make RAOS comfortable to read.</h2></div><button className="icon-button" onClick={() => setOpen(false)} aria-label="Close">×</button></header>
        <PreferenceRow title="Theme" description="Changes the entire RAOS interface"><div className="segmented-control">{(["dark","light","system"] as ThemePreference[]).map(v => <button key={v} className={theme===v?"active":""} onClick={()=>changeTheme(v)}>{v[0].toUpperCase()+v.slice(1)}</button>)}</div></PreferenceRow>
        <PreferenceRow title="Text size" description="Applies to navigation, cards, and Reader."><div className="segmented-control">{(["compact","default","large"] as TextSize[]).map(v => <button key={v} className={size===v?"active":""} onClick={()=>changeSize(v)}>{v==="default"?"Default":v[0].toUpperCase()+v.slice(1)}</button>)}</div></PreferenceRow>
        <PreferenceRow title="Half-bold reading" description="Bold the first half of Latin words to create visual fixation points."><div className="segmented-control"><button className={bionic==="off"?"active":""} onClick={()=>changeBionic("off")}>Off</button><button className={bionic==="on"?"active":""} onClick={()=>changeBionic("on")}>On</button></div></PreferenceRow>
        <PreferenceRow title="Half-bold weight" description="Adjust how strongly the fixation points stand out."><div className="segmented-control">{(["soft","medium","strong"] as BionicWeight[]).map(v => <button key={v} className={bionicWeight===v?"active":""} onClick={()=>changeWeight(v)}>{v[0].toUpperCase()+v.slice(1)}</button>)}</div></PreferenceRow>
        <p className="preferences-note">Saved in this browser. Reading aids change presentation only; Source text and RAOS cognition remain untouched.</p>
      </section>
    </div>}
  </>;
}

function PreferenceRow({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return <div className="preference-row"><div><strong>{title}</strong><p>{description}</p></div>{children}</div>;
}
