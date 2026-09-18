"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import BionicText from "@/components/BionicText";

type ThemePreference = "dark" | "light" | "system";
type TextSize = "compact" | "default" | "large";
type BionicMode = "off" | "on";
type BionicWeight = 1 | 2 | 3 | 4 | 5;
type ReadingSkin = "classic" | "bionic-soft";

const THEME_KEY = "raos-theme";
const SIZE_KEY = "raos-text-size";
const BIONIC_KEY = "raos-bionic-reading";
const BIONIC_STRENGTH_KEY = "raos-bionic-strength";
const BIONIC_WEIGHT_KEY = "raos-bionic-weight";
const READING_SKIN_KEY = "raos-reading-skin";
const READING_PREFERENCES_EVENT = "raos-reading-preferences-changed";
const CLASSIC_BIONIC_WEIGHTS: Record<BionicWeight, number> = { 1: 400, 2: 600, 3: 700, 4: 800, 5: 900 };
const SOFT_BIONIC_WEIGHTS: Record<BionicWeight, number> = { 1: 460, 2: 520, 3: 580, 4: 640, 5: 700 };

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

function applyPreferences(theme: ThemePreference, size: TextSize, bionic: BionicMode, strength: number, weight: BionicWeight, skin: ReadingSkin) {
  const root = document.documentElement;
  const fontWeight = skin === "bionic-soft" ? SOFT_BIONIC_WEIGHTS[weight] : CLASSIC_BIONIC_WEIGHTS[weight];
  root.dataset.theme = resolveTheme(theme);
  root.dataset.fontScale = size;
  root.dataset.bionic = bionic;
  root.dataset.bionicStrength = String(strength);
  root.dataset.bionicWeight = String(weight);
  root.dataset.readingSkin = skin;
  root.style.setProperty("--bionic-weight", String(fontWeight));
  root.style.setProperty("--bionic-shadow", "none");
  window.dispatchEvent(new Event(READING_PREFERENCES_EVENT));
}

export default function PreferencesPanel() {
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState<ThemePreference>("system");
  const [size, setSize] = useState<TextSize>("default");
  const [bionic, setBionic] = useState<BionicMode>("off");
  const [bionicStrength, setBionicStrength] = useState(60);
  const [bionicWeight, setBionicWeight] = useState<BionicWeight>(3);
  const [readingSkin, setReadingSkin] = useState<ReadingSkin>("classic");

  useEffect(() => {
    const storedTheme = (localStorage.getItem(THEME_KEY) as ThemePreference | null) || "system";
    const storedSize = (localStorage.getItem(SIZE_KEY) as TextSize | null) || "default";
    const storedBionic = (localStorage.getItem(BIONIC_KEY) as BionicMode | null) || "off";
    const storedStrength = normalizeStrength(localStorage.getItem(BIONIC_STRENGTH_KEY));
    const storedWeight = normalizeWeight(localStorage.getItem(BIONIC_WEIGHT_KEY));
    const storedSkin = (localStorage.getItem(READING_SKIN_KEY) as ReadingSkin | null) || "classic";
    setTheme(storedTheme); setSize(storedSize); setBionic(storedBionic); setBionicStrength(storedStrength); setBionicWeight(storedWeight); setReadingSkin(storedSkin);
    applyPreferences(storedTheme, storedSize, storedBionic, storedStrength, storedWeight, storedSkin);
    const media = window.matchMedia("(prefers-color-scheme: light)");
    const updateSystem = () => {
      if ((localStorage.getItem(THEME_KEY) || "system") === "system") document.documentElement.dataset.theme = media.matches ? "light" : "dark";
    };
    media.addEventListener("change", updateSystem);
    return () => media.removeEventListener("change", updateSystem);
  }, []);

  function persist(nextTheme = theme, nextSize = size, nextBionic = bionic, nextStrength = bionicStrength, nextWeight = bionicWeight, nextSkin = readingSkin) {
    localStorage.setItem(THEME_KEY, nextTheme); localStorage.setItem(SIZE_KEY, nextSize);
    localStorage.setItem(BIONIC_KEY, nextBionic); localStorage.setItem(BIONIC_STRENGTH_KEY, String(nextStrength)); localStorage.setItem(BIONIC_WEIGHT_KEY, String(nextWeight)); localStorage.setItem(READING_SKIN_KEY, nextSkin);
    applyPreferences(nextTheme, nextSize, nextBionic, nextStrength, nextWeight, nextSkin);
  }
  function changeTheme(next: ThemePreference) { setTheme(next); persist(next, size, bionic, bionicStrength, bionicWeight, readingSkin); }
  function changeSize(next: TextSize) { setSize(next); persist(theme, next, bionic, bionicStrength, bionicWeight, readingSkin); }
  function changeBionic(next: BionicMode) { setBionic(next); persist(theme, size, next, bionicStrength, bionicWeight, readingSkin); }
  function changeStrength(next: number) { setBionicStrength(next); persist(theme, size, bionic, next, bionicWeight, readingSkin); }
  function changeWeight(next: number) { const weight = Math.max(1, Math.min(5, Math.round(next))) as BionicWeight; setBionicWeight(weight); persist(theme, size, bionic, bionicStrength, weight, readingSkin); }
  function changeSkin(next: ReadingSkin) {
    const soft = next === "bionic-soft";
    const nextBionic: BionicMode = soft ? "on" : bionic;
    const nextStrength = soft && readingSkin !== "bionic-soft" ? 50 : bionicStrength;
    const nextWeight: BionicWeight = soft && readingSkin !== "bionic-soft" ? 3 : bionicWeight;
    setReadingSkin(next); setBionic(nextBionic); setBionicStrength(nextStrength); setBionicWeight(nextWeight);
    persist(theme, size, nextBionic, nextStrength, nextWeight, next);
  }

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
        <PreferenceRow title="Reading skin" description="Switch the Reader typography without changing source text or cognition."><div className="segmented-control"><button className={readingSkin==="classic"?"active":""} onClick={()=>changeSkin("classic")}>Classic</button><button className={readingSkin==="bionic-soft"?"active":""} onClick={()=>changeSkin("bionic-soft")}>Bionic Soft</button></div></PreferenceRow>
        <PreferenceRow title="Half-bold reading" description="Create visual fixation points at the beginning of Latin words."><div className="segmented-control"><button className={bionic==="off"?"active":""} onClick={()=>changeBionic("off")}>Off</button><button className={bionic==="on"?"active":""} onClick={()=>changeBionic("on")}>On</button></div></PreferenceRow>
        <PreferenceRow title="Half-bold strength" description="How much of each word becomes the fixation point."><RangeControl value={bionicStrength} min={10} max={100} step={5} suffix="%" onChange={changeStrength} /></PreferenceRow>
        <PreferenceRow title="Half-bold weight" description="How heavy the fixation letters appear; independent from strength."><RangeControl value={bionicWeight} min={1} max={5} step={1} onChange={changeWeight} /></PreferenceRow>
        {bionic === "on" && <div className="reader-note preference-reading-preview" style={{ marginTop: 18 }}><div className="eyebrow">Live preview</div><p><BionicText text="Research attention should feel easier to scan without changing the words. 仿生阅读应该帮助视线自然落点，而不是把文字切成一块一块。" strength={bionicStrength / 100} /></p></div>}
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
