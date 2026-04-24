# Veins — Design Guidelines

> **STATUS:** placeholder. Лилит дополнит из векторки (`memory_search("DESIGN.md frontend awesome-design-md")`).
> До тех пор Agent E (Frontend) использует базовые правила ниже.

---

## Philosophy

- **Dark theme by default.** Dashboard на светлом фоне в 2026 выглядит устаревшим.
- **One accent color.** Один яркий цвет для call-to-action (красный/оранжевый для alerts Ивана).
- **Minimal chrome.** Никаких bordered cards с тенями. Flat, typographic, много whitespace.
- **Graph — герой экрана.** Граф занимает 65-75% ширины. Sidebar справа.
- **Клик на ноду = мгновенная реакция.** Skeleton loader на 200ms, потом insight.

---

## Colors

```css
--bg-primary:   #0a0a0f;     /* почти чёрный */
--bg-secondary: #13131a;     /* чуть светлее — sidebar */
--bg-elevated:  #1c1c26;     /* карточки */
--border:       #26262f;

--text-primary:   #f0f0f5;
--text-secondary: #9090a0;
--text-tertiary:  #606070;

--status-green:  #10b981;
--status-yellow: #f59e0b;
--status-red:    #ef4444;

--accent:        #8b5cf6;    /* violet — для CTA */
```

## Typography

- Font stack: `Inter, system-ui, sans-serif`
- Mono: `JetBrains Mono, ui-monospace`
- Headline: 24-32px, weight 600
- Body: 14-16px, weight 400
- Small/meta: 12px, weight 500

## Layout (single screen)

```
┌─────────────────────────────────────────────────────────────┐
│  Veins logo             [stress] [collab] [workload]    v0.1│
├────────────────────────────────────┬────────────────────────┤
│                                    │                        │
│                                    │  [Avatar]              │
│                                    │  Ivan Petrov           │
│          3D FORCE GRAPH            │  Senior Backend        │
│                                    │  Status: 🔴 RED        │
│   (ноды — люди, размер = overload) │  Overload: 0.82        │
│                                    │  ─────────────────     │
│                                    │  Insights              │
│                                    │  • ...                 │
│                                    │  • ...                 │
│                                    │                        │
│                                    │  [Что делать]          │
│                                    │  [Написать Ивану]      │
│                                    │  [Recognition]         │
└────────────────────────────────────┴────────────────────────┘
```

Sidebar: fixed 420px ширина. Граф — остальное.

## Component rules

- **GraphView**: `react-force-graph-3d` с background = `--bg-primary`. Node size = `overload_score * 8 + 4`. Node color по status. Links = `--border` с opacity 0.4.
- **LayerToggle**: segmented control, 3 кнопки в шапке. Активная — accent background. Клик → мгновенное обновление графа (без loading spinner).
- **InsightPanel**: появляется когда выбрана нода. Пустое состояние = "Select a person to see AI insights".
- **ActionButtons**: три кнопки столбцом. Primary = фиолет, secondary — transparent с border.

## Animation

- Граф: force simulation по умолчанию (библиотечная).
- Клик на ноду → node pulse (scale 1 → 1.3 → 1 за 400ms).
- Insight-панель: fade-in + slide-up 200ms.
- Layer toggle: fade между слоями за 300ms.

## Не делать

- ❌ Gradient backgrounds, glass-morphism — устаревший trend 2022.
- ❌ Иконки в каждом элементе. Иконка только где она несёт смысл.
- ❌ Placeholder data на экране демо. Пустое состояние ≠ lorem ipsum.
- ❌ Светлая тема. Не успеем сделать переключатель.

---

## TODO для Лилит (после memory_search)

- [ ] Референсы из `awesome-design-md` (ElevenLabs, VoltAgent, Linear)
- [ ] Точная типографика + spacing scale
- [ ] Стиль карточки человека (glassmorphism vs flat)
- [ ] Анимация появления insight (каждая bullet letter-by-letter?)
