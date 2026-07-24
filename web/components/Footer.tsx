import React from "react";
import { BRAND } from "../lib/brand";

export default function Footer() {
  return (
    <footer className="border-t border-[var(--line-hairline)] mt-auto">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-5 flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px] text-[var(--text-tertiary)]">
        <span className="font-semibold">
          <span className="text-[var(--text-secondary)]">{BRAND.name}</span> · {BRAND.full}
        </span>
        <span className="flex items-center gap-2">
          <span>Built for Tech Mahindra CODE · The Ultimate Hack League</span>
          <span className="text-[var(--line-strong)]" aria-hidden>·</span>
          <span className="font-mono">{BRAND.version}</span>
        </span>
      </div>
    </footer>
  );
}
