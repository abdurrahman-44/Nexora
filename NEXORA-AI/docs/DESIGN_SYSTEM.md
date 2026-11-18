# NEXORA ERP — Glassmorphism Design System & Visual Identity

## 1. Visual Philosophy

NEXORA ERP combines **executive dark enterprise aesthetics** with **precision-engineered frosted glassmorphism**. Every surface is designed to maximize financial data legibility while delivering a futuristic, layered enterprise operating system experience.

---

## 2. Color Tokens (Dark & Light Themes)

### Dark Theme (Default)
| Token | Hex / RGBA | Usage |
| :--- | :--- | :--- |
| `--bg-main` | `#080D18` | Primary canvas background |
| `--bg-secondary` | `#101827` | Elevated section / table container background |
| `--surface-primary` | `#141F31` | High-contrast readable surface for dense data tables |
| `--surface-glass` | `rgba(255, 255, 255, 0.055)` | Translucent KPI cards, panels, command palette |
| `--surface-glass-hover` | `rgba(255, 255, 255, 0.085)` | Illuminated hover state |
| `--border-glass` | `rgba(255, 255, 255, 0.10)` | Fine 1px translucent border |
| `--border-glass-active` | `rgba(100, 139, 255, 0.45)` | Focused / active card border |
| `--accent-primary` | `#648BFF` | Primary interactive brand accent |
| `--accent-secondary` | `#8B7CFF` | Intelligence / AI Copilot accent |
| `--status-success` | `#20C997` | Balanced journals, positive cash flow, approved states |
| `--status-warning` | `#F4B740` | Low-stock warnings, pending approvals |
| `--status-danger` | `#F06464` | Overdue invoices, high-severity anomalies, rejections |
| `--text-main` | `#F5F7FC` | Primary headings & values (AAA contrast) |
| `--text-muted` | `#94A3B8` | Labels, metadata, timestamps |

### Light Theme
| Token | Hex / RGBA | Usage |
| :--- | :--- | :--- |
| `--bg-main` | `#F4F7FC` | Clean daylight canvas |
| `--bg-secondary` | `#FFFFFF` | Primary table & content surface |
| `--surface-glass` | `rgba(255, 255, 255, 0.78)` | Frosted daylight cards |
| `--border-glass` | `rgba(15, 23, 42, 0.09)` | Crisp subtle border |
| `--accent-primary` | `#456FEA` | High-contrast sapphire accent |
| `--text-main` | `#172033` | Deep slate ink |
| `--text-muted` | `#667085` | Secondary captions |

---

## 3. Core Glassmorphism CSS Classes

```css
.glass-panel {
  background: var(--surface-glass);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-glass);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.16);
}

.glass-sidebar {
  background: rgba(15, 23, 42, 0.78);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
}

.glass-table-container {
  background: rgba(20, 31, 49, 0.88);
  backdrop-filter: blur(16px);
  border: 1px solid var(--border-glass);
}
```

---

## 4. Typography & Numeric Formatting Rules

- **Font Family**: `Inter`, system-ui sans-serif (`JetBrains Mono` for SKUs, journal numbers, and account codes).
- **Financial & Quantitative Data**: Always apply `font-variant-numeric: tabular-nums` (`tabular-nums` in Tailwind) so LKR currency columns, debits/credits, and stock quantities align vertically to the decimal point.
- **Locale Standards**:
  - Default Currency: `LKR` (formatted as `LKR 1,245,000.00` or `Rs. 1,245,000.00`).
  - Default Date Display: `DD MMM YYYY` (e.g., `16 Nov 2026`).
  - Default Timezone: `Asia/Colombo` (`UTC+05:30`).
