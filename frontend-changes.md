# Frontend Changes

## Code Quality Tooling

Added frontend code quality tooling to enforce consistent formatting and catch common JavaScript issues.

### New Files

#### `package.json`
Defines the project's npm configuration and quality scripts:
- `npm run format` — formats all frontend JS/CSS/HTML with Prettier
- `npm run format:check` — checks formatting without modifying files (CI-safe)
- `npm run lint` — lints `frontend/script.js` with ESLint
- `npm run lint:fix` — auto-fixes ESLint issues where possible
- `npm run quality` — runs both format check and lint (use in CI)
- `npm run quality:fix` — runs both formatter and lint auto-fix (use locally)

#### `.prettierrc`
Prettier configuration for consistent formatting across all frontend files:
- Single quotes in JS
- Semicolons required
- 2-space indentation
- 100-character print width
- Trailing commas in ES5 contexts
- LF line endings

#### `eslint.config.js`
ESLint flat config for `frontend/script.js`:
- Extends `@eslint/js` recommended ruleset
- Globals declared: `document`, `window`, `console`, `fetch`, `Date`, `marked`
- Rules:
  - `no-var`: error (enforce `let`/`const`)
  - `prefer-const`: warn
  - `eqeqeq`: error (enforce `===`)
  - `no-unused-vars`: warn

### Setup Instructions

```bash
# Install dependencies (first time only)
npm install

# Check formatting and lint
npm run quality

# Auto-fix formatting and linting issues
npm run quality:fix
```

---

## Dark/Light Theme Toggle

### Feature Summary
Added a dark/light mode toggle button that allows users to switch between the existing dark theme and a new light theme. The preference is persisted in `localStorage`.

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
