import React from "react";

function renderToken(token: string, key: number) {
  if (/^\s+$/.test(token)) return <React.Fragment key={key}>{token}</React.Fragment>;
  const match = token.match(/^([^A-Za-z0-9À-ÖØ-öø-ÿ]*)([A-Za-z0-9À-ÖØ-öø-ÿ]+(?:['’][A-Za-z]+)?)(.*)$/);
  if (!match) return <React.Fragment key={key}>{token}</React.Fragment>;
  const [, before, word, after] = match;
  const chars = Array.from(word);
  if (chars.length < 2) return <React.Fragment key={key}>{token}</React.Fragment>;
  const cut = Math.max(1, Math.ceil(chars.length * 0.48));
  return (
    <React.Fragment key={key}>
      {before}<span className="bionic-prefix">{chars.slice(0, cut).join("")}</span>{chars.slice(cut).join("")}{after}
    </React.Fragment>
  );
}

export default function BionicText({ text }: { text: string }) {
  return <>{text.split(/(\s+)/).map(renderToken)}</>;
}
