# Veins — Design System

> Стиль: **Terminal-dark + data-dense**. Вдохновение: Linear (утилитарность), VoltAgent (void-black + emerald), Vercel (типографика), Blur.io (neon-stroke CTAs).
> Правило: граф — герой экрана. Всё остальное — поддержка.

---

## Colors

```css
/* Backgrounds */
--bg-primary:   #0a0a0a;   /* void-black — основной фон */
--bg-secondary: #111116;   /* sidebar, панели */
--bg-elevated:  #1a1a22;   /* карточки, hover states */
--bg-input:     #16161e;   /* инпуты, поля */

/* Borders */
--border:       #242430;   /* основная граница */
--border-hover: #363645;   /* граница на hover */

/* Text */
--text-primary:   #f0f0f5;   /* заголовки */
--text-secondary: #8888a0;   /* подписи, meta */
--text-tertiary:  #55556a;   /* placeholder, disabled */

/* Status (NODE COLORS) */
--status-red:    #ef4444;   /* overload > 0.7 */
--status-yellow: #f59e0b;   /* overload 0.4-0.7 */
--status-green:  #10b981;   /* overload < 0.4 — emerald */

/* Accent */
--accent:        #10b981;   /* emerald — primary CTA, active states */
--accent-dim:    #10b98133; /* emerald 20% — glow, hover bg */

/* Graph */
--graph-bg:      #0a0a0a;
--graph-link:    rgba(255,255,255,0.12);
--graph-link-hover: rgba(16,185,129,0.4);
```

---

## Typography

```css
/* Font stack */
font-family: 'Inter', system-ui, -apple-system, sans-serif;
font-family-mono: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;

/* Scale */
--text-xs:   11px;  /* meta, timestamps */
--text-sm:   13px;  /* body secondary */
--text-base: 14px;  /* body primary */
--text-lg:   16px;  /* subtitles */
--text-xl:   20px;  /* section headers */
--text-2xl:  24px;  /* page title */

/* Weights: 400 (body), 500 (labels), 600 (headings) */
```

---

## Layout (Single Screen, No Routing)

```
┌──────────────────────────────────────────────────────────────┐
│  ◈ Veins          [Stress] [Collab] [Workload]          v0.1 │  ← Header 48px
├───────────────────────────────────────┬──────────────────────┤
│                                       │                      │
│                                       │  InsightPanel        │
│                                       │  (420px fixed)       │
│          ForceGraph3D                 │                      │
│          (flex-1, fills rest)         │  Empty state OR      │
│                                       │  Person card         │
│                                       │  + Signals           │
│                                       │  + Insights          │
│                                       │  + Actions           │
│                                       │                      │
└───────────────────────────────────────┴──────────────────────┘
```

- Header: `height: 48px`, `border-bottom: 1px solid var(--border)`
- Sidebar: `width: 420px`, `border-left: 1px solid var(--border)`, `overflow-y: auto`
- Graph: `flex: 1`, background `var(--graph-bg)`

---

## Component Specs

### Header
```tsx
// Логотип: моноширинный текст "◈ veins" + версия справа
// LayerToggle по центру
<header className="flex items-center justify-between px-4 h-12 border-b border-[--border]">
  <span className="font-mono text-sm text-[--accent]">◈ veins</span>
  <LayerToggle />
  <span className="font-mono text-xs text-[--text-tertiary]">v0.1.0</span>
</header>
```

### LayerToggle
```tsx
// Segmented control — 3 кнопки
// Active: bg accent-dim, text accent, border accent
// Inactive: transparent, text-secondary
// Hover: border-hover
const layers = [
  { id: "stress",   label: "Stress",   icon: "⬤" },
  { id: "collab",   label: "Collab",   icon: "⬡" },
  { id: "workload", label: "Workload", icon: "▦" },
]
// className active: "bg-[--accent-dim] text-[--accent] border-[--accent]"
// className idle:   "text-[--text-secondary] border-[--border] hover:border-[--border-hover]"
```

### GraphView (ForceGraph3D)
```tsx
// Node rendering
nodeVal={node => node.overload_score * 10 + 4}   // размер
nodeColor={node => {
  if (node.id === selectedId) return "#ffffff"    // выделенная — белая
  if (node.status === "red")    return "#ef4444"
  if (node.status === "yellow") return "#f59e0b"
  return "#10b981"  // green
}}
nodeOpacity={node => node.id === selectedId ? 1.0 : 0.85}

// Link rendering
linkColor={() => "rgba(255,255,255,0.12)"}
linkWidth={link => link.weight * 0.5 + 0.5}

// Node click highlight — выбранная нода увеличивается
// Реализуется через state selectedId + nodeVal:
nodeVal={node => {
  const base = node.overload_score * 10 + 4
  return node.id === selectedId ? base * 1.6 : base  // 60% bigger on select
}}

// Настройки
backgroundColor="#0a0a0a"
width={graphWidth}   // flex-1, считать через ref
height={height - 48} // минус header

// Node label (всплывает при hover)
nodeLabel={node => `${node.name} (${node.role})`}
```

### InsightPanel — Empty State
```tsx
<div className="flex flex-col items-center justify-center h-full gap-3 text-[--text-tertiary]">
  <span className="text-4xl opacity-30">◈</span>
  <p className="text-sm font-mono">select a node to inspect</p>
</div>
```

### InsightPanel — Person Card
```tsx
// Header секция
<div className="p-4 border-b border-[--border]">
  <div className="flex items-start gap-3">
    <img src={person.avatar_url} className="w-10 h-10 rounded-full opacity-90" />
    <div className="flex-1">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-base text-[--text-primary]">{person.name}</span>
        <StatusBadge status={person.status} />  // ⬤ RED / ⬤ YELLOW / ⬤ GREEN
      </div>
      <span className="text-xs text-[--text-secondary] font-mono">{person.role}</span>
    </div>
  </div>
  // Overload bar
  <div className="mt-3">
    <div className="flex justify-between text-xs text-[--text-tertiary] mb-1">
      <span className="font-mono">overload</span>
      <span className="font-mono">{(person.overload_score * 100).toFixed(0)}%</span>
    </div>
    <div className="h-1 bg-[--bg-elevated] rounded-full">
      <div
        className="h-1 rounded-full transition-all duration-500"
        style={{ width: `${person.overload_score * 100}%`, backgroundColor: statusColor }}
      />
    </div>
  </div>
</div>
```

### Signals Section
```tsx
// 6-7 прогресс-баров в компактной сетке
// Каждый: label (font-mono, xs, text-tertiary) + bar + value
<div className="p-4 border-b border-[--border]">
  <h3 className="text-xs font-mono text-[--text-tertiary] uppercase tracking-wider mb-3">signals</h3>
  {signals.map(({ key, label, value }) => (
    <div key={key} className="flex items-center gap-2 mb-2">
      <span className="text-xs font-mono text-[--text-secondary] w-36 shrink-0">{label}</span>
      <div className="flex-1 h-1 bg-[--bg-elevated] rounded-full">
        <div className="h-1 rounded-full bg-[--accent]" style={{ width: `${value * 100}%` }} />
      </div>
      <span className="text-xs font-mono text-[--text-tertiary] w-8 text-right">
        {(value * 100).toFixed(0)}
      </span>
    </div>
  ))}
</div>
```

### Insights Section (с Loading State)
```tsx
// Loading: skeleton pulses
{isLoading && (
  <div className="p-4 space-y-2">
    {[1,2,3].map(i => (
      <div key={i} className="h-3 bg-[--bg-elevated] rounded animate-pulse" style={{width: `${85 - i*10}%`}} />
    ))}
  </div>
)}

// Loaded: fade-in bullets
{insights && (
  <div className="p-4 border-b border-[--border]">
    <h3 className="text-xs font-mono text-[--text-tertiary] uppercase tracking-wider mb-3">insights</h3>
    {insights.insights.map((text, i) => (
      <div key={i} className="flex gap-2 mb-2 animate-fadeIn" style={{animationDelay: `${i * 80}ms`}}>
        <span className="text-[--accent] font-mono text-xs mt-0.5">›</span>
        <p className="text-sm text-[--text-secondary] leading-relaxed">{text}</p>
      </div>
    ))}
  </div>
)}
```

### ActionButtons
```tsx
// Primary: solid emerald
<button className="w-full py-2 px-4 bg-[--accent] text-black text-sm font-semibold rounded
                   hover:bg-emerald-400 transition-colors">
  What to do
</button>

// Secondary: outline
<button className="w-full py-2 px-4 border border-[--border] text-[--text-secondary] text-sm rounded
                   hover:border-[--border-hover] hover:text-[--text-primary] transition-colors">
  Write to {person.name}
</button>

// Recognition: subtle
<button className="w-full py-2 px-4 border border-[--accent-dim] text-[--accent] text-sm rounded
                   hover:bg-[--accent-dim] transition-colors font-mono">
  ✦ Recognition
</button>
```

---

## CSS Animations (globals.css)

```css
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}
.animate-fadeIn { animation: fadeIn 0.2s ease-out forwards; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}
.animate-pulse { animation: pulse 1.5s ease-in-out infinite; }
```

---

## Tailwind Config Additions

```js
// tailwind.config.js
theme: {
  extend: {
    colors: {
      veins: {
        bg:        '#0a0a0a',
        secondary: '#111116',
        elevated:  '#1a1a22',
        border:    '#242430',
        accent:    '#10b981',
        red:       '#ef4444',
        yellow:    '#f59e0b',
      }
    }
  }
}
```

---

## Do NOT

- ❌ Light theme
- ❌ Gradient backgrounds / glassmorphism
- ❌ Shadows (box-shadow) — только borders
- ❌ Icons everywhere — только где несут смысл
- ❌ Rounded cards с padding > 16px — tight и dense
- ❌ Lorem ipsum — только реальные данные или empty state
- ❌ React Router — один экран, один URL
- ❌ Redux/Zustand — useState достаточно
