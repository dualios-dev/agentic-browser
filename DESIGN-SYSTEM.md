# Dualios Design System — Complete Reference for Agentic Browser

## Source
Extracted from Dualios-testing repo (imam branch), dual-canvas page + globals.css + Figma inspection skill.

---

## 1. CSS Variables (Most Used)

### Colors — Core
```css
--background: #0f0f0f;
--foreground: #ffffff;
--card-background: rgba(0, 0, 0, 0.10);
--card-border: rgba(255, 255, 255, 0.15);
--card-border-elevated: rgba(255, 255, 255, 0.30);
--card-separator: rgba(255, 255, 255, 0.05);
--card-background-subtle: rgba(40, 40, 40, 0.70);
```

### Colors — Text
```css
--text-primary: rgba(255, 255, 255, 0.85);
--text-secondary: rgba(255, 255, 255, 0.55);
--text-placeholder: rgba(255, 255, 255, 0.25);
--text-highlight: #1A6FE6;
```

### Colors — Buttons
```css
--btn-primary-bg: var(--cosmic-50);        /* #F2F2F7 */
--btn-primary-hover: var(--cosmic-200);     /* #D1D1D6 */
--btn-primary-text: var(--cosmic-950);      /* #050505 */
--btn-secondary-bg: rgba(255, 255, 255, 0.10);
--btn-secondary-hover: rgba(255, 255, 255, 0.15);
--btn-ghost-hover: rgba(255, 255, 255, 0.10);
```

### Colors — Cosmic Scale (Graydust)
```css
--cosmic-50:  #F2F2F7;   --cosmic-500: #616166;
--cosmic-100: #E6E6EB;   --cosmic-600: #47474D;
--cosmic-200: #D1D1D6;   --cosmic-700: #2B2B2E;
--cosmic-300: #B3B3B8;   --cosmic-800: #1C1C1F;
--cosmic-400: #8C8C91;   --cosmic-900: #121212;
                          --cosmic-950: #050505;
```

### Colors — Brand (Blue)
```css
--brand-500: #4087EA;
--brand-600: #1A6FE6;
--brand-700: #155CBF;
--brand-800: #114A99;
```

### Colors — Semantic
```css
--destructive: #FF4D4D;
--positive: #00FF85;
--success-600: #32C382;
--danger-600: #DF2E16;
--warning-600: #F5B100;
--purple-600: #8E62EF;
```

### Border Radius
```css
--radius-sm: 6px;   --radius: 8px;     --radius-md: 10px;
--radius-lg: 12px;  --radius-xl: 16px; --radius-2xl: 20px;
```

### Typography
```css
--font-sans: 'General Sans', -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: 'IBM Plex Mono', monospace;
Font sizes: 12px (xs), 14px (sm), 16px (base)
Font weights: 400 (normal), 500 (medium), 600 (semibold)
```

---

## 2. Glassmorphism System

### Default Glass (cards, sidebars, bars)
```css
.liquid-glass {
  background: var(--card-background);          /* rgba(0,0,0,0.10) */
  backdrop-filter: blur(150px);
  border: 1px solid var(--card-border);        /* rgba(255,255,255,0.15) */
  box-shadow: 0 2px 32px 0 rgba(0,0,0,0.20);
}
```

### Elevated Glass (popups, overlays, dock)
```css
.liquid-glass-elevated {
  background: rgba(18, 18, 20, 0.82);
  backdrop-filter: blur(150px) saturate(120%);
  border: 1px solid var(--card-border-elevated);  /* rgba(255,255,255,0.30) */
  box-shadow: 0 2px 32px 0 rgba(0,0,0,0.20);
}
```

### Apple Liquid Glass (special components only)
```css
.apple-liquid-glass {
  background-color: color-mix(in srgb, #bbbbbc 12%, transparent);
  backdrop-filter: blur(8px) saturate(150%);
  box-shadow: /* complex inner light/dark reflexes */;
}
```

### SVG Displacement Filter (Chromium refraction effect)
```html
<feTurbulence type="fractalNoise" baseFrequency="0.008" numOctaves={4} seed={2} />
<feDisplacementMap scale={60} xChannelSelector="R" yChannelSelector="G" />
<feGaussianBlur stdDeviation={1.2} />
<feColorMatrix type="saturate" values="1.15" />
```

---

## 3. Component Patterns

### Button Sizes
| Size | Height | Padding | Radius | Font |
|------|--------|---------|--------|------|
| md | 40px | px-12 py-8 | 8px | 14px |
| sm | 28px | px-8 py-2 | 6px | 12px |

### Icon Button Sizes
| Size | Dimensions | Padding | Radius | Icon |
|------|-----------|---------|--------|------|
| md | 40×40 | 12px | 8px | 16px |
| sm | 32×32 | 8px | 6px | 16px |
| xs | 28×28 | 6px | 6px | 16px |
| xxs | 24×24 | 4px | 6px | 14px |

### Button Variants
- **Primary**: bg `#F2F2F7`, text `#050505`, hover `#D1D1D6`
- **Secondary**: bg `rgba(71,71,77,0.6)`, text `#F2F2F7`, hover `rgba(71,71,77,1)`
- **Ghost**: transparent, hover `rgba(255,255,255,0.1)`
- **Destructive**: red tint variants for each type

### Popup Shell
- Position: `absolute top-0 left-full ml-8px`
- Default: 350×716px
- Class: `liquid-glass-elevated rounded-[12px] p-[8px]`
- Gap between items: 6px
- Hidden scrollbar, overflow-y auto

### Docker (Bottom Toolbar)
- Class: `apple-liquid-glass` with `card-background-subtle` bg
- Rounded: 16px
- Gap: 4px, padding: 4px
- Divider: 1px solid `var(--card-separator)`, height 32px
- Tool icons → divider → brand logos → add button

### Dropdown Menu
- Class: `liquid-glass-elevated rounded-[12px] p-[4px]`
- Items: `px-12 py-10 rounded-[8px]`
- Hover: `bg-[rgba(255,255,255,0.06)]`
- Icon: 18px, strokeWidth 1.5, color `var(--text-secondary)`
- Text: General Sans, 400, 14px, color `var(--text-primary)`
- Chevron: 16px, color `var(--text-placeholder)`

### LayerBar (Left Sidebar)
- Default width: 200px (min 180, max 380)
- Collapsible with chevron toggle
- Profile menu with icons
- Page list with selection highlight
- Resizable via drag handle

### Top Bar
- `liquid-glass rounded-[12px] p-[4px]`
- Logo → breadcrumb (/ separated) → action buttons
- Right group: avatar dots → inbox/bell → audio toggle → sidebar toggle → Share button

---

## 4. Layout Patterns

### Main Canvas Layout
```
h-screen w-full flex overflow-hidden
├── Left sidebar (LayerBar, collapsible)
├── Main area (flex-1, p-12px, bg rgba(5,5,5,1))
│   ├── Top bar (absolute, left/right/top 12px)
│   ├── ReactFlow canvas (full width/height)
│   ├── Docker (absolute, bottom 12px, centered)
│   └── Zoom controls (absolute, bottom-right 12px)
└── Right sidebar (280px, conditional, liquid-glass)
```

### Canvas Background
```css
background: #1C1C1E;  /* ReactFlow */
background: rgba(5, 5, 5, 1);  /* Container */
```

### Body Background
```css
background: linear-gradient(135deg, #0f0f0f 0%, #1a1a1a 50%, #0f0f0f 100%);
/* Plus radial gradient overlays for subtle light spots */
```

---

## 5. Animation & Transitions

```css
/* Fade in */
@keyframes fadeIn { from { opacity:0; transform:translateY(10px) } to { opacity:1; transform:translateY(0) } }
.fade-in { animation: fadeIn 0.3s ease }

/* Shimmer */
@keyframes shimmer { 0% { background-position: 200% 0 } 100% { background-position: -200% 0 } }
.animate-shimmer { animation: shimmer 2.5s linear infinite }

/* Standard transitions */
transition-colors: 0.2s ease
button active: transform scale(0.98)
liquid-glass transitions: 400ms cubic-bezier(1, 0, 0.4, 1)
```

---

## 6. Figma-to-Code Rules

| Figma | Code |
|-------|------|
| Auto layout Vertical, Gap 8 | `flex flex-col gap-2` |
| Auto layout Horizontal, Gap 4 | `flex flex-row gap-1` |
| W: Fill, H: Hug | `w-full h-auto` or `flex-1` |
| Corner radius 12 | `rounded-[12px]` |
| Stroke Inside 1px | `border border-[var(--token)]` |
| Font: General Sans, Regular, 12, 150% | `font-sans text-xs leading-[150%]` |
| Clip content ON | `overflow-hidden` |

---

## 7. Icon System
- Library: **lucide-react**
- Default size: 16px
- Default strokeWidth: 1.5 (menus), 2 (buttons)
- Color: `var(--text-secondary)` for menu icons, `var(--text-primary)` for action icons
- Brand icons: SVG files in `/public/icons/`

## 8. State Management
- **Zustand** store for canvas state
- Types for popups, tasks, roles, criteria, learnings, lesson cards
- All state co-located in `store.ts`
