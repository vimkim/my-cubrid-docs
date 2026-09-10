---
name: warp-brand
description: Apply Warp brand guidelines to any output -- UI, HTML/CSS components, docs, launch pages, social assets, and AI-facing instructions. Use this whenever output should look and sound unmistakably Warp.
---
# Warp Brand System
## Overview
This skill encodes Warp's brand system: color tokens, typography, voice, logo usage, component rules, and implementation snippets for both human-facing and machine-facing outputs.
**Keywords**: Warp brand, design system, brand voice, terminal UX, agentic UX, Matter Sans, Matter Mono, logo rules, docs styling, AI prompt style
## 1. Colors
### Primary
**Core Tokens**
| Token | Hex |
|---|---|
| `color/neutral/black` | `#121212` |
| `color/neutral/white` | `#ffffff` |
| `color/neutral/off-white` | `#faf9f6` |
| `accent` | `#9c58f0` |
**Accent Scale (Lilac)**
`accent/lilac-600` is the primary accent.
| Token | Hex |
|---|---|
| `accent/lilac-600` | `#9c58f0` |
| `accent/lilac-400` | `#c59fff` |
| `accent/lilac-200` | `#d2b5ff` |
| `accent/lilac-100` | `#e1d0ff` |
**Neutral Scale**
| Token | Hex |
|---|---|
| `color/neutral/neutral-95` | `#1e1e1d` |
| `color/neutral/neutral-90` | `#292929` |
| `color/neutral/neutral-80` | `#404040` |
| `color/neutral/neutral-70` | `#585756` |
| `color/neutral/neutral-60` | `#6f6e6d` |
| `color/neutral/neutral-50` | `#868584` |
| `color/neutral/neutral-40` | `#9d9d9b` |
| `color/neutral/neutral-30` | `#b4b4b2` |
| `color/neutral/neutral-20` | `#cccbc8` |
| `color/neutral/neutral-10` | `#e3e2df` |
| `color/neutral/neutral-5` | `#eeedeb` |
**Neutral Shades (Darken and Lighten)**
| Token | Hex |
|---|---|
| `color/darken/darken-95` | `#121212f2` |
| `color/darken/darken-90` | `#121212e5` |
| `color/darken/darken-80` | `#121212cc` |
| `color/darken/darken-70` | `#121212b2` |
| `color/darken/darken-60` | `#12121299` |
| `color/darken/darken-50` | `#12121280` |
| `color/darken/darken-40` | `#12121266` |
| `color/darken/darken-30` | `#1212124d` |
| `color/darken/darken-20` | `#12121233` |
| `color/darken/darken-10` | `#1212121a` |
| `color/lighten/lighten-95` | `#faf9f6f2` |
| `color/lighten/lighten-90` | `#faf9f6e5` |
| `color/lighten/lighten-80` | `#faf9f6cc` |
| `color/lighten/lighten-70` | `#faf9f6b2` |
| `color/lighten/lighten-60` | `#faf9f699` |
| `color/lighten/lighten-50` | `#faf9f680` |
| `color/lighten/lighten-40` | `#faf9f666` |
| `color/lighten/lighten-30` | `#faf9f64d` |
| `color/lighten/lighten-20` | `#faf9f633` |
| `color/lighten/lighten-10` | `#faf9f61a` |
| `color/lighten/lighten-5` | `#faf9f60d` |
### Secondary
**Core Colors**
| Token | Hex |
|---|---|
| `brand-color/brand-green` | `#34895c` |
| `brand-color/brand-blue` | `#2e5d9e` |
| `brand-color/brand-purple` | `#754dac` |
**Scales**
| Family | Scale |
|---|---|
| Green | `#15281f`, `#296043`, `#34895c`, `#1ca05a`, `#789b88`, `#b6c9bf` |
| Blue | `#0f2748`, `#224577`, `#2e5d9e`, `#1458b8`, `#6f839f`, `#acb8c8` |
| Purple | `#35244c`, `#4c3172`, `#754dac`, `#7032c8`, `#8979a0`, `#b8acc8` |
### Tertiary
**Core Colors**
| Token | Hex |
|---|---|
| `color/teal/teal-60` | `#4d9989` |
| `color/pink/pink-60` | `#a43787` |
| `color/red/red-60` | `#c6372a` |
| `color/yellow/yellow-60` | `#c0872a` |
**Scales**
| Family | Scale |
|---|---|
| Teal | `#293d39`, `#396a60`, `#4d9989`, `#34b298`, `#799c92`, `#bfc5c3` |
| Pink | `#471a3b`, `#862d6e`, `#a43787`, `#bf409d`, `#a57899`, `#c8acc2` |
| Red | `#44201d`, `#76251e`, `#c6372a`, `#d22d1e`, `#ae756f`, `#dcb9b7` |
| Yellow | `#4d391a`, `#7a571f`, `#c0872a`, `#e5a01a`, `#bd9f65`, `#e3d7bf` |
### Dark Surfaces
- Large dark surfaces should use `color/neutral/black` (`#121212`).
- Text on dark should use `color/neutral/off-white` (`#faf9f6`) or `color/neutral/white` (`#ffffff`).
- Primary accent on dark should use `accent/lilac-600` (`#9c58f0`) with lighter lilac tints (`#c59fff`, `#d2b5ff`) for hover/focus.
## 2. Typography
### Typefaces
| Variable | Font | Fallback | Use |
|---|---|---|---|
| `--warp-font-sans` | Matter | DM Sans, system sans-serif | Default Text + Short Text tokens |
| `--warp-font-mono` | Matter Mono | Roboto Mono, system monospace | Code + Caps Mono tokens |
### Default Text Scale (Matter / Regular / 400)
| Token | Size | Line Height | Tracking |
|---|---|---|---|
| `Default Text/Text .625/Regular` | 10px | `1.4` | `+1.5` |
| `Default Text/Text .75/Regular` | 12px | `1.4` | `+1.5` |
| `Default Text/Text .875/Regular` | 14px | `1.4` | `+1` |
| `Default Text/Text 1/Regular` | 16px | `1.4` | `+0.5` |
| `Default Text/Text 1.125/Regular` | 18px | `1.4` | `0` |
| `Default Text/Text 1.25/Regular` | 20px | `1.4` | `0` |
| `Default Text/Text 1.375/Regular` | 22px | `1.3` | `0` |
| `Default Text/Text 1.5/Regular` | 24px | `1.3` | `-1` |
| `Default Text/Text 1.75/Regular` | 28px | `1.3` | `-1` |
| `Default Text/Text 2/Regular` | 32px | `1.2` | `-1` |
| `Default Text/Text 2.5/Regular` | 40px | `1.15` | `-1.5` |
| `Default Text/Text 3/Regular` | 48px | `1.15` | `-2` |
| `Default Text/Text 3.5/Regular` | 56px | `1.05` | `-2` |
| `Default Text/Text 4/Regular` | 64px | `1.05` | `-2.5` |
| `Default Text/Text 5/Regular` | 80px | `1` | `-2.5` |
| `Default Text/Text 6/Regular` | 96px | `1` | `-2.5` |
| `Default Text/Text 8/Regular` | 128px | `1` | `-2.5` |
| `Default Text/Text 10/Regular` | 160px | `1` | `-3` |
### Short Text Scale (Matter / Regular / 400)
| Token | Size | Line Height | Tracking |
|---|---|---|---|
| `Short Text/Text .625/Regular` | 10px | `1` | `+1.5` |
| `Short Text/Text .75/Regular` | 12px | `1` | `+1.5` |
| `Short Text/Text .875/Regular` | 14px | `1` | `+1` |
| `Short Text/Text 1/Regular` | 16px | `1` | `+0.5` |
| `Short Text/Text 1.125/Regular` | 18px | `1` | `0` |
| `Short Text/Text 1.25/Regular` | 20px | `1` | `0` |
| `Short Text/Text 1.375/Regular` | 22px | `1` | `0` |
| `Short Text/Text 1.5/Regular` | 24px | `1` | `-1` |
| `Short Text/Text 1.75/Regular` | 28px | `1` | `-1` |
| `Short Text/Text 2/Regular` | 32px | `1` | `-1` |
| `Short Text/Text 2.5/Regular` | 40px | `1` | `-1.5` |
| `Short Text/Text 3/Regular` | 48px | `1` | `-2` |
| `Short Text/Text 3.5/Regular` | 56px | `1` | `-2` |
| `Short Text/Text 4/Regular` | 64px | `1` | `-2.5` |
| `Short Text/Text 5/Regular` | 80px | `1` | `-2.5` |
| `Short Text/Text 6/Regular` | 96px | `1` | `-2.5` |
| `Short Text/Text 8/Regular` | 128px | `1` | `-2.5` |
| `Short Text/Text 10/Regular` | 160px | `1` | `-3` |
### Code Scale (Matter Mono / Regular / 400)
| Token | Size | Line Height | Tracking |
|---|---|---|---|
| `Code/Code .625` | 10px | `1` | `+5` |
| `Code/Code .75` | 12px | `1` | `+5` |
| `Code/Code .875` | 14px | `1` | `+5` |
| `Code/Code 1` | 16px | `1` | `+5` |
| `Code/Code 1.125` | 18px | `1` | `+5` |
| `Code/Code 1.25` | 20px | `1` | `+5` |
| `Code/Code 1.375` | 22px | `1` | `+5` |
| `Code/Code 1.5` | 24px | `1` | `+5` |
| `Code/Code 1.75` | 28px | `1` | `+5` |
| `Code/Code 2` | 32px | `1` | `+2.5` |
| `Code/Code 2.5` | 40px | `1` | `+2.5` |
| `Code/Code 3` | 48px | `1` | `+2.5` |
| `Code/Code 3.5` | 56px | `1` | `+2.5` |
| `Code/Code 4` | 64px | `1` | `+2.5` |
| `Code/Code 5` | 80px | `1` | `+2.5` |
| `Code/Code 6` | 96px | `1` | `+2.5` |
| `Code/Code 8` | 128px | `1` | `0` |
| `Code/Code 10` | 160px | `1` | `0` |
### Caps Mono Scale (Matter Mono / Regular / 400)
| Token | Size | Line Height | Tracking |
|---|---|---|---|
| `Caps Mono/Caps Mono .625` | 10px | `1` | `+20` |
| `Caps Mono/Caps Mono .75` | 12px | `1` | `+20` |
| `Caps Mono/Caps Mono .875` | 14px | `1` | `+20` |
| `Caps Mono/Caps Mono 1` | 16px | `1` | `+20` |
| `Caps Mono/Caps Mono 1.125` | 18px | `1` | `+20` |
| `Caps Mono/Caps Mono 1.25` | 20px | `1` | `+20` |
### Typesetting Rules
- Target **50-75 characters** per line for body copy.
- For Default Text tokens, line-height moves from `1.4` at small sizes to `1` at large display sizes.
- Short Text and Code tokens keep line-height at `1`.
- Use Matter Mono for metadata, labels, section tags, and machine-oriented snippets.
- Avoid excessive font mixing. Default to Matter + Matter Mono only.
### CSS Quick Reference
```css
/* Body + UI */
:root {
  --warp-font-sans: 'Matter', 'DM Sans', sans-serif;
  --warp-font-mono: 'Matter Mono', 'Roboto Mono', monospace;
  --text-1: 16px;
  --text-1-line-height: 1.4;
  --text-1-tracking: 0.5;
  --code-075: 12px;
  --code-075-line-height: 1;
  --code-075-tracking: 5;
}
body {
  font-family: var(--warp-font-sans);
  color: #121212;
}
.mono-label {
  font-family: var(--warp-font-mono);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-size: 12px;
}
```
## 3. Voice & Copy
### Core Voice Attributes
- **Truth-seeking** -- prioritize technical correctness over hype.
- **Highly technical** -- use concrete implementation language.
- **Thoroughly researched** -- reference evidence and explicit constraints.
- **Matter-of-fact** -- concise, objective, no fluff.
### Do / Don't
| Do | Don't |
|---|---|
| "Use this command to inspect active sessions and verify state transitions." | "This revolutionary feature supercharges your workflow." |
| "If typecheck fails, fix the reported path before proceeding." | "It should probably work without changes." |
| "Default to deterministic behavior and explicit fallbacks." | "Try some magic and see what happens." |
### Style Rules
- Use short, direct sentences.
- Favor imperative phrasing for instructions.
- Keep claims verifiable and specific.
- Avoid marketing superlatives and generic buzzwords.
### Terminology
- Capitalize product names and surface names: **Warp**, **Warp Drive**, **Agent Mode**, **Notebooks**, **Blocks**.
- Use "agentic" only when relevant to workflows/automation.
- Prefer "developer workflow" over generic phrases like "user journey."
## 4. Components
### General Rules
- Preserve canonical spacing, interaction patterns, and semantics from Warp web components.
- Keep container edges mostly sharp for documentation surfaces unless a component explicitly defines radius.
- Use lilac accent (`#9C58F0`) intentionally for emphasis and active states.
### Pill / Label
```css
.pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border: 1px solid #d8c8d4;
  background: #faf9f6;
  color: #121212;
  font-family: 'Matter Mono', 'Roboto Mono', monospace;
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
```
### Buttons
**Reference component:** `Web-components / node 11:536`
**Importance + default appearance**
| Importance | Background | Text | Backdrop | Typical use |
|---|---|---|---|---|
| `Primary` | `#faf9f6` | `#121212e5` | none | high-emphasis CTA |
| `Secondary` | `rgba(64,64,64,0.5)` | `#faf9f6e5` | `blur(16px)` | lower-emphasis CTA on dark surfaces |
**Interactive states**
| State | Background token/value | Text |
|---|---|---|
| Hover | `rgba(41,41,41,0.5)` | `#faf9f6e5` |
| Active | `rgba(88,87,86,0.5)` | `#faf9f6e5` |
| Focus | ring `0 0 0 4px rgba(255,255,255,0.2)` | unchanged |
**Core size mapping**
| Size token | Text token | Padding (y x) | Radius |
|---|---|---|---|
| `.75` | `Short Text/Text .75/Medium` (12px) | `8px 12px` | `4px` |
| `1` | `Short Text/Text 1/Medium` (16px) | `12px 16px` | `4px` |
| `1.125` | `Short Text/Text 1.125/Medium` (18px) | `12px 16px` | `6px` |
```css
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 12px 16px;
  font-family: 'Matter', 'DM Sans', sans-serif;
  font-size: 16px;
  font-weight: 500;
  line-height: 1;
  letter-spacing: 0.08px;
  text-decoration: none;
}
.btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.2);
}
.btn-primary {
  background: #faf9f6;
  color: rgba(18, 18, 18, 0.9);
}
.btn-secondary {
  background: rgba(64, 64, 64, 0.5);
  color: rgba(250, 249, 246, 0.9);
  backdrop-filter: blur(16px);
}
.btn:hover {
  background: rgba(41, 41, 41, 0.5);
  color: rgba(250, 249, 246, 0.9);
}
.btn:active {
  background: rgba(88, 87, 86, 0.5);
  color: rgba(250, 249, 246, 0.9);
}
```
### Cards
```css
.card {
  background: #ffffff;
  border: 1px solid #d8c8d4;
  padding: 24px;
}
```
## 5. Data Visualization
Warp data visualizations should be legible, implementation-oriented, and contrast-safe.
### Rules
1. Use clear hierarchy: title, axis/legend labels, then data emphasis.
2. Prefer flat fills over gradients unless a specific chart demands gradient encoding.
3. For most charts and diagrams, default to a black background (`#121212`) with white bars/lines (`#FFFFFF`); use lilac (`#9C58F0`) only when necessary for emphasis.
4. Use brand tones intentionally:
   - Primary series: `#754DAC` or `#2E5D9E`
   - Secondary/supporting series: `#4D9989`, `#34895C`
   - Alert/error values: `#C6372A`
5. Use mono labels for technical metrics.
6. Maintain chart container borders at `1px` with subtle stroke tokens.
### Example Palette Mapping
```
Background:   #121212
Bars/Lines:   #FFFFFF
Accent:       #9C58F0 (only when necessary)
Secondary:    #2E5D9E
Support:      #4D9989
Positive:     #34895C
Warning:      #C0872A
Error:        #C6372A
Border:       #D8C8D4
```
## 6. Logo Usage
- Use official Warp lockup and glyph assets only.
- Keep glyph and wordmark proportions fixed.
- Preserve clear spacing around the lockup.
- On dark backgrounds, use light/white logo rendering.
- Never rotate, distort, recolor beyond approved context treatments, or apply drop shadows.
- Never change glyph/wordmark ordering or geometry.
## 7. Spacing & Layout
Base spacing scale:
```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-6: 24px;
--space-8: 32px;
--space-12: 48px;
--space-16: 64px;
--space-24: 96px;
```
Layout guidance:
- Use consistent spacing increments.
- Keep docs content width stable and readable.
- Prefer visual rhythm over dense stacking.
## 8. CSS Token Starter
```css
:root {
  --warp-white: #ffffff;
  --warp-off-white: #faf9f6;
  --warp-black: #121212;
  --warp-green: #34895c;
  --warp-blue: #2e5d9e;
  --warp-purple: #754dac;
  --warp-teal: #4d9989;
  --warp-pink: #a43787;
  --warp-accent: #9c58f0;
  --warp-red: #c6372a;
  --warp-yellow: #c0872a;
  --warp-stroke: #d8c8d4;
}
```
## How to Apply This Skill
**For HTML/CSS components**: use Warp tokens, Matter typography, and objective interaction language.
**For copy**: write direct, technically grounded, and matter-of-fact. Avoid hype and ambiguity.
**For docs and machine-facing context**: include explicit constraints, concrete examples, and clear decision rules.
**For branding surfaces**: keep logo integrity, consistent spacing, and contrast-safe color use.
