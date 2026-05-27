# Novestia Design System

## Visual Language: "Functional Futurism"

Dark-first, glassmorphism cards, neon accent borders, precision typography. Inspired by tactical HUD interfaces.

## Color Tokens

| Token | Usage | CSS Variable |
|-------|-------|-------------|
| `background.primary` | Page background | `--background` |
| `background.elevated` | Card surfaces | `--card` |
| `background.subtle` | Hover/inset | `--accent` |
| `border.default` | Card borders | `--border` |
| `border.focus` | Active/focus | `--neon-blue` |
| `text.primary` | Main text | `--foreground` |
| `text.secondary` | Descriptions | `--muted-foreground` |
| `accent.positive` | Gains, success | `--neon-green` / `.text-gain` |
| `accent.negative` | Losses, danger | `--neon-red` / `.text-loss` |
| `accent.warning` | Caution | `--neon-amber` / `.text-warning` |
| `accent.info` | Primary actions | `--neon-blue` / `.text-info` |
| `accent.neutral` | AI, charts | `--neon-purple` / `.text-ai` |

## DO / DON'T

- **DO** use `formatCurrency()` from `lib/format.ts`
- **DON'T** hardcode `$${n.toFixed(2)}`
- **DO** use `glass-card` class for all card surfaces
- **DON'T** use `rounded-lg border bg-card`
- **DO** use `font-numbers` class for all financial data
- **DON'T** use `tabular-nums` directly
- **DO** use `text-gain` / `text-loss` for colored values
- **DON'T** use `text-green-600` / `text-red-600`
- **DO** use `KpiCard` component for all metric displays
- **DON'T** build custom metric cards
- **DO** use `PageHeader` for all page titles
- **DON'T** write `<h1>` directly in pages
- **DO** use `EmptyState` for all empty lists/charts
- **DON'T** write inline empty messages

## Shared Components

| Component | Location | Usage |
|-----------|----------|-------|
| `KpiCard` | `components/common/kpi-card.tsx` | All KPI metrics |
| `PageHeader` | `components/layout/page-header.tsx` | All page titles |
| `EmptyState` | `components/common/empty-state.tsx` | All empty states |
| `Skeleton` | `components/common/skeleton.tsx` | All loading states |
| `StockSearch` | `components/common/stock-search.tsx` | Stock search UI |

## Typography Scale

| Name | Classes | Usage |
|------|---------|-------|
| Display | `font-heading text-4xl font-bold` | Landing page hero |
| H1 | `font-heading text-xl sm:text-2xl font-bold` | Page titles |
| Label | `text-[10px] font-medium uppercase tracking-widest` | Section headers, card labels |
| Body | `text-sm` | Main content |
| Numbers | `font-numbers text-sm font-medium` | All financial data |
| Caption | `text-xs text-muted-foreground` | Timestamps, footnotes |

## Glow Effects

Applied via CSS classes from `globals.css`:
- `.glow-green` — positive/success states
- `.glow-red` — negative/danger states
- `.glow-amber` — warning states
- `.glow-blue` — info/primary states
- `.glow-purple` — AI/neutral states

## Chart Theme

All charts use tokens from `lib/charts/theme.ts`:
- Axis: 10px, muted color, no axis lines
- Tooltips: glassmorphic card style
- Gradients: 25% opacity fade to transparent
- Line colors: match accent tokens
