"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import BionicText from "@/components/BionicText";

type ThemePreference = "dark" | "light" | "system";
type TextSize = "compact" | "default" | "large";
type BionicMode = "off" | "on";
type BionicWeight = 1 | 2 | 3 | 4 | 5;

const THEME_KEY = "raos-theme";
const SIZE_KEY = "raos-text-size";
const BIONIC_KEY = "raos-bionic-reading";
const BIONIC_STRENGTH_KEY = "raos-bionic-strength";
const BIONIC_WEIGHT_KEY = "raos-bionic-weight";
const READING_PREFERENCES_EVENT = "raos-reading-preferences-changed";
const BIONIC_WEIGHT_STYLES: Record<BionicWeight, { fontWeight: number; shadow: string }> = {
  1: { fontWeight: 400, shadow: "none" },
  2: { fontWeight: 600, shadow: "none" },
  3: { fontWeight: 700, shadow: "0.3px 0 0 currentColor, -0.3px 0 0 currentColor, 0 0.3px 0 currentColor, 0 -0.3px 0 currentColor" },
  4: { fontWeight: 800, shadow: "0.5px 0 0 currentColor, -0.5px 0 0 currentColor, 0 0.5px 0 currentColor, 0 -0.5px 0 currentColor" },
  5: { fontWeight: 900, shadow: "0.75px 0 0 currentColor, -0.75px 0 0 currentColor, 0 0.75px 0 currentColor, 0 -0.75px 0 currentColor" },
};

function resolveTheme(preference: ThemePreference) {
  if (preference !== "system") return preference;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function normalizeWeight(raw: string | null): BionicWeight {
  const legacy: Record<string, BionicWeight> = { soft: 2, medium: 3, strong: 4 };
  if (raw && legacy[raw]) return legacy[raw];
  const value = Number(raw || 3);
  return Math.max(1, Math.min(5, Number.isFinite(value) ? Math.round(value) : 3)) as BionicWeight;
}

function normalizeStrength(raw: string | null) {
  const value = Number(raw || 60);
  return Math.max(10, Math.min(100, Number.isFinite(value) ? Math.round(value / 5) * 5 : 60));
}

function applyPreferences(theme: ThemePreference, size: TextSize, bionic: BionicMode, strength: number, weight: BionicWeight) {
  const root = document.documentElement;
  const weightStyle = BIONIC_WEIGHT_STYLES[weight];
  root.dataset.theme = resolveTheme(theme);
  root.dataset.fontScale = size;
  root.dataset.bionic = bionic;
  root.dataset.bionicStrength = String(strength);
  root.dataset.bionicWeight = String(weight);
  root.style.setProperty("--bionic-weight", String(weightStyle.fontWeight));
  root.style.setProperty("--bionic-shadow", bionic === "on" ? weightStyle.shadow : "none");
  window.dispatchEvent(new Event(READING_PREFERENCES_EVENT));
}

export default function PreferencesPanel() {
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState<ThemePreference>("system");
  const [size, setSize] = useState<TextSize>("default");
  const [bionic, setBionic] = useState<BionicMode>("off");
  const [bionicStrength, setBionicStrength] = useState(60);
  const [bionicWeight, setBionicWeight] = useState<BionicWeight>(3);

  useEffect(() => {
    const storedTheme = (localStorage.getItem(THEME_KEY) as ThemePreference | null) || "system";
    const storedSize = (localStorage.getItem(SIZE_KEY) as TextSize | null) || "default";
    const storedBionic = (localStorage.getItem(BIONIC_KEY) as BionicMode | null) || "off";
    const storedStrength = normalizeStrength(localStorage.getItem(BIONIC_STRENGTH_KEY));
    const storedWeight = normalizeWeight(localStorage.getItem(BIONIC_WEIGHT_KEY));
    setTheme(storedTheme); setSize(storedSize); setBionic(storedBionic); setBionicStrength(storedStrength); setBionicWeight(storedWeight);
    applyPreferences(storedTheme, storedSize, storedBionic, storedStrength, storedWeight);
    const media = window.matchMedia("(prefers-color-scheme: light)");
    const updateSystem = () => {
      if ((localStorage.getItem(THEME_KEY) || "system") === "system") document.documentElement.dataset.theme = media.matches ? "light" : "dark";
    };
    media.addEventListener("change", updateSystem);
    return () => media.removeEventListener("change", updateSystem);
  }, []);

  function persist(nextTheme = theme, nextSize = size, nextBionic = bionic, nextStrength = bionicStrength, nextWeight = bionicWeight) {
    localStorage.setItem(THEME_KEY, nextTheme); localStorage.setItem(SIZE_KEY, nextSize);
    localStorage.setItem(BIONIC_KEY, nextBionic); localStorage.setItem(BIONIC_STRENGTH_KEY, String(nextStrength)); localStorage.setItem(BIONIC_WEIGHT_KEY, String(nextWeight));
    applyPreferences(nextTheme, nextSize, nextBionic, nextStrength, nextWeight);
  }
  function changeTheme(next: ThemePreference) { setTheme(next); persist(next, size, bionic, bionicStrength, bionicWeight); }
  function changeSize(next: TextSize) { setSize(next); persist(theme, next, bionic, bionicStrength, bionicWeight); }
  function changeBionic(next: BionicMode) { setBionic(next); persist(theme, size, next, bionicStrength, bionicWeight); }
  function changeStrength(next: number) { setBionicStrength(next); persist(theme, size, bionic, next, bionicWeight); }
  function changeWeight(next: number) { const weight = Math.max(1, Math.min(5, Math.round(next))) as BionicWeight; setBionicWeight(weight); persist(theme, size, bionic, bionicStrength, weight); }

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const modal = open ? createPortal(
    <div className="preferences-backdrop" onMouseDown={(event) => { if (event.currentTarget === event.target) setOpen(false); }}>
      <section className="preferences-panel" role="dialog" aria-modal="true" aria-label="RAOS Preferences">
        <header><div><div className="eyebrow">Preferences</div><h2>Make RAOS comfortable to read.</h2></div><button className="icon-button" onClick={() => setOpen(false)} aria-label="Close">×</button></header>
        <PreferenceRow title="Theme" description="Changes the entire RAOS interface"><div className="segmented-control">{(["dark","light","system"] as ThemePreference[]).map(v => <button key={v} className={theme===v?"active":""} onClick={()=>changeTheme(v)}>{v[0].toUpperCase()+v.slice(1)}</button>)}</div></PreferenceRow>
        <PreferenceRow title="Text size" description="Applies to navigation, cards, and Reader."><div className="segmented-control">{(["compact","default","large"] as TextSize[]).map(v => <button key={v} className={size===v?"active":""} onClick={()=>changeSize(v)}>{v==="default"?"Default":v[0].toUpperCase()+v.slice(1)}</button>)}</div></PreferenceRow>
        <PreferenceRow title="Half-bold reading" description="Create visual fixation points at the beginning of Latin words."><div className="segmented-control"><button className={bionic==="off"?"active":""} onClick={()=>changeBionic("off")}>Off</button><button className={bionic==="on"?"active":""} onClick={()=>changeBionic("on")}>On</button></div></PreferenceRow>
        <PreferenceRow title="Half-bold strength" description="How much of each word becomes the fixation point."><RangeControl value={bionicStrength} min={10} max={100} step={5} suffix="%" onChange={changeStrength} /></PreferenceRow>
        <PreferenceRow title="Half-bold weight" description="How heavy the fixation letters appear; independent from strength."><RangeControl value={bionicWeight} min={1} max={5} step={1} onChange={changeWeight} /></PreferenceRow>
        {bionic === "on" && <div className="reader-note" style={{ marginTop: 18 }}><div className="eyebrow">Live preview</div><p style={{ fontSize: 16, lineHeight: 1.65 }}><BionicText text="Research attention should feel easier to scan without changing the words." strength={bionicStrength / 100} /></p></div>}
        <p className="preferences-note">Saved in this browser. Strength changes the highlighted word fraction; weight changes only visual boldness. Source text and RAOS cognition remain untouched.</p>
      </section>
    </div>,
    document.body
  ) : null;

  return <>
    <button className="preferences-entry" onClick={() => setOpen(true)}><span className="preferences-icon">Aa</span><span><strong>Preferences</strong><small>Appearance & reading</small></span></button>
    {modal}
  </>;
}

function PreferenceRow({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return <div className="preference-row"><div><strong>{title}</strong><p>{description}</p></div>{children}</div>;
}

function RangeControl({ value, min, max, step, suffix = "", onChange }: { value: number; min: number; max: number; step: number; suffix?: string; onChange: (value: number) => void }) {
  return <div style={{ display: "grid", gridTemplateColumns: "minmax(150px, 220px) 44px", alignItems: "center", gap: 10 }}>
    <input type="range" min={min} max={max} step={step} value={value} aria-label="Reading preference" onChange={(event) => onChange(Number(event.target.value))} style={{ padding: 0, border: 0, background: "transparent", boxShadow: "none" }} />
    <strong style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{value}{suffix}</strong>
  </div>;
}
