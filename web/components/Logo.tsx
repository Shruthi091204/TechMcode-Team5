import React from "react";
import { BRAND } from "../lib/brand";

interface LogoProps {
  size?: number;
  showWordmark?: boolean;
  showDescriptor?: boolean;
}

// Monogram: a rounded red tile with a crosshair "pinpoint the cause" glyph.
export default function Logo({ size = 30, showWordmark = true, showDescriptor = false }: LogoProps) {
  return (
    <span className="flex items-center gap-2.5 select-none">
      <span
        aria-hidden
        style={{ width: size, height: size }}
        className="relative shrink-0 rounded-[8px] bg-[var(--accent-red)] shadow-[0_2px_10px_rgba(229,9,20,0.35)] flex items-center justify-center"
      >
        <svg width={size * 0.62} height={size * 0.62} viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round">
          <circle cx="12" cy="12" r="6.2" />
          <path d="M12 1.6v3.2M12 19.2v3.2M1.6 12h3.2M19.2 12h3.2" />
          <circle cx="12" cy="12" r="1.6" fill="white" stroke="none" />
        </svg>
      </span>
      {showWordmark ? (
        <span className="flex flex-col leading-none">
          <span className="text-[15px] font-black tracking-tight text-white">{BRAND.name}</span>
          {showDescriptor ? (
            <span className="text-[9.5px] font-semibold uppercase tracking-[0.1em] text-[var(--text-tertiary)] mt-0.5">
              {BRAND.full}
            </span>
          ) : null}
        </span>
      ) : null}
    </span>
  );
}
