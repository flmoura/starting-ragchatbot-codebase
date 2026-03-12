# Frontend Changes

## Dark/Light Theme Toggle

### Feature Summary
Added a dark/light mode toggle button that allows users to switch between the existing dark theme and a new light theme. The preference is persisted in `localStorage`.

---

### Files Modified

#### `frontend/index.html`
- Added a `<button id="themeToggle">` element fixed to the top-right corner, outside the main `.container`.
- The button contains two inline SVG icons:
  - `.icon-sun` — shown in dark mode (click to switch to light)
  - `.icon-moon` — shown in light mode (click to switch to dark)
- Both icons have `aria-hidden="true"`; the button itself carries a descriptive `aria-label`.

#### `frontend/style.css`
- **Light mode variables** — Added a `[data-theme="light"]` selector block on `<body>` that overrides the dark-mode `:root` defaults:
  - `--background: #f8fafc`
  - `--surface: #ffffff`
  - `--surface-hover: #e2e8f0`
  - `--text-primary: #0f172a`
  - `--text-secondary: #64748b`
  - `--border-color: #cbd5e1`
  - `--shadow`, `--focus-ring`, `--welcome-bg`, `--welcome-border` adjusted for light context
  - `--theme-toggle-bg/border/color` variables for the button's own appearance
- **Smooth transitions** — Added a global `transition` rule on `body` and `body *` for `background-color`, `border-color`, `color`, and `box-shadow` (0.3s ease), creating a smooth cross-fade when switching themes.
- **Toggle button styles** — `#themeToggle` is `position: fixed; top: 1rem; right: 1rem; z-index: 1000`. It is a 44×44 px circle with hover (scale + blue border), focus (ring), and active (scale down) states.
- **Icon visibility** — `.icon-moon` is hidden by default; `[data-theme="light"] .icon-sun` hides the sun and reveals the moon.
- **Light-mode code blocks** — `[data-theme="light"] .message-content code` and `pre` use a reduced-opacity dark overlay so inline code stays readable on white backgrounds.

#### `frontend/script.js`
- Added `themeToggle` to the DOM element declarations.
- **`initTheme()`** — reads `localStorage.getItem('theme')` (defaulting to `'dark'`) and sets `document.body.setAttribute('data-theme', saved)` on page load. Also sets the initial `aria-label` on the toggle button.
- **`toggleTheme()`** — reads the current `data-theme` attribute, flips it, writes it back to the `<body>` element and persists the new value in `localStorage`. Updates `aria-label` accordingly.
- **Event listeners in `setupEventListeners()`**:
  - `click` — calls `toggleTheme()`
  - `keydown` — calls `toggleTheme()` on `Enter` or `Space` (with `preventDefault()`) for full keyboard accessibility.
