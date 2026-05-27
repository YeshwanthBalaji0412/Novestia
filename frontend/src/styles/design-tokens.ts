/**
 * Novestia Design Tokens — Single source of truth.
 *
 * Every color, size, and shadow in the app references these tokens.
 * No component should hardcode hex values or pixel sizes.
 *
 * Colors are defined as CSS custom property references so they work
 * with Tailwind's `var()` system and adapt to light/dark mode.
 */

export const colors = {
  background: {
    primary: "var(--background)",         // page bg — deep near-black
    elevated: "var(--card)",              // card bg — slightly lighter
    subtle: "var(--accent)",              // hover/inset surfaces
  },
  border: {
    default: "var(--border)",             // faint card borders
    focus: "var(--neon-blue)",            // active/focus state
  },
  text: {
    primary: "var(--foreground)",          // main text
    secondary: "var(--muted-foreground)",  // descriptions, labels
    tertiary: "var(--muted-foreground)",   // chart axes, timestamps
  },
  accent: {
    positive: "var(--neon-green)",         // gains, success
    negative: "var(--neon-red)",           // losses, danger
    warning: "var(--neon-amber)",          // caution, after-hours
    info: "var(--neon-blue)",              // primary actions, links
    neutral: "var(--neon-purple)",         // AI, charts, neutral data
  },
} as const;

export const typography = {
  display: { size: "text-4xl sm:text-5xl", weight: "font-bold", family: "font-heading" },
  h1: { size: "text-xl sm:text-2xl", weight: "font-bold", family: "font-heading" },
  h2: { size: "text-lg", weight: "font-semibold", family: "font-heading" },
  body: { size: "text-sm", weight: "font-normal", family: "font-sans" },
  label: { size: "text-[10px]", weight: "font-medium", extra: "uppercase tracking-widest" },
  caption: { size: "text-xs", weight: "font-normal", family: "font-sans" },
  mono: { size: "text-sm", weight: "font-medium", family: "font-numbers" },
} as const;

export const spacing = {
  xs: 4,    // 1
  sm: 8,    // 2
  md: 12,   // 3
  lg: 16,   // 4
  xl: 24,   // 6
  "2xl": 32, // 8
  "3xl": 48, // 12
  "4xl": 64, // 16
} as const;

export const radii = {
  sm: "rounded-md",    // 6px
  md: "rounded-lg",    // 10px
  lg: "rounded-xl",    // 16px
} as const;

export const glow = {
  positive: "0 0 20px oklch(0.78 0.2 155 / 0.3), 0 0 6px oklch(0.78 0.2 155 / 0.15)",
  negative: "0 0 20px oklch(0.7 0.23 18 / 0.3), 0 0 6px oklch(0.7 0.23 18 / 0.15)",
  warning: "0 0 20px oklch(0.8 0.17 80 / 0.3), 0 0 6px oklch(0.8 0.17 80 / 0.15)",
  info: "0 0 20px oklch(0.75 0.2 240 / 0.3), 0 0 6px oklch(0.75 0.2 240 / 0.15)",
  neutral: "0 0 20px oklch(0.7 0.27 290 / 0.3), 0 0 6px oklch(0.7 0.27 290 / 0.15)",
} as const;

/** Map accent name → Tailwind glow class from globals.css */
export const glowClass = {
  positive: "glow-green",
  negative: "glow-red",
  warning: "glow-amber",
  info: "glow-blue",
  neutral: "glow-purple",
} as const;

/** Map accent name → text color class */
export const accentTextClass = {
  positive: "text-gain",
  negative: "text-loss",
  warning: "text-warning",
  info: "text-info",
  neutral: "text-ai",
} as const;

export type Accent = keyof typeof glowClass;

/** Determine accent based on numeric sign */
export function getDeltaAccent(value: number): Accent {
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return "info";
}
