# Design Inspiration — from Dualios Dual Canvas

## Apple-Style Design Language Observed

### Color & Theme
- **Dark mode first** — deep black/charcoal background (#1a1a1a range)
- **Minimal color accents** — green/blue avatar dots, green progress bars, red for warnings (0/100 score)
- **Muted text** — light gray on dark, not pure white
- **No harsh borders** — elements defined by subtle background differences

### Layout Patterns
- **3-panel layout**: collapsible left sidebar | main canvas | right panel (Inputs/Outputs)
- **Top breadcrumb bar** with logo → path → action buttons → avatar → share
- **Bottom toolbar (dock-style)** — centered, with icon buttons + branded integrations (Notion, Canva, Instagram, Google)
- **Floating controls** — bottom-right: Live dial, monitor toggle, zoom percentage

### Component Styles
- **Cards** — rounded corners, slight background lift, no visible borders
- **Dropdown menus** — dark glass effect, list with icons + chevrons for submenus
- **Tabs** — subtle segmented control (Lessons/Learnings, Inputs/Outputs)
- **Chips/tags** — small rounded pills for metadata (dates, budgets, role names like "Step", "Task 1")
- **Progress bars** — thin, colored (green for progress, gray for empty)
- **Checklists** — circle radio buttons, clean list items
- **Tables** — minimal, header row slightly different, green status dots
- **Chat UI** — conversation bubbles, "Thought for X seconds" indicator, file creation events

### Interaction Patterns
- **Collapsible sidebar** — chevron toggle, smooth transition
- **+ button** to add items (steps) — instant insertion with auto-numbering
- **Three-dot menu** → nested submenus with hover-reveal panels
- **Toggle buttons** — active state with subtle highlight
- **Segmented tabs** — click to switch content in place

### Typography
- **Clean sans-serif** — likely SF Pro or Inter
- **Hierarchy** — bold headers, regular body, muted secondary text
- **Compact** — tight line height, efficient use of space

### Key Apple-isms
1. **Restraint** — very few colors, no gradients on UI chrome
2. **Depth through darkness** — lighter surfaces float above darker backgrounds
3. **Dock-style toolbar** — reminiscent of macOS dock
4. **Rounded everything** — buttons, cards, inputs, chips
5. **Icon-forward** — most buttons are icons only, labels on hover/special cases
6. **Glassmorphism hints** — semi-transparent overlays on menus
7. **$5.00 cost indicator** — bottom-left, subtle but always visible

### For Our Agentic Browser UI
Apply these patterns to:
- **Browser control panel** — dark theme, minimal, icon-driven
- **Task/session sidebar** — collapsible, step-based
- **Safety dashboard** — evaluation criteria style (score/100, key metrics)
- **Proxy status** — chip-style indicators (residential ✓, mobile ✓)
- **Content sanitizer view** — before/after markdown preview
- **Action log** — chat-style timeline like the Inputs tab
