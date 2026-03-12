# Frontend Code Quality Changes

## Overview

Added frontend code quality tooling to enforce consistent formatting and catch common JavaScript issues.

## New Files

### `package.json`
Defines the project's npm configuration and quality scripts:
- `npm run format` — formats all frontend JS/CSS/HTML with Prettier
- `npm run format:check` — checks formatting without modifying files (CI-safe)
- `npm run lint` — lints `frontend/script.js` with ESLint
- `npm run lint:fix` — auto-fixes ESLint issues where possible
- `npm run quality` — runs both format check and lint (use in CI)
- `npm run quality:fix` — runs both formatter and lint auto-fix (use locally)

### `.prettierrc`
Prettier configuration for consistent formatting across all frontend files:
- Single quotes in JS
- Semicolons required
- 2-space indentation
- 100-character print width
- Trailing commas in ES5 contexts
- LF line endings

### `eslint.config.js`
ESLint flat config for `frontend/script.js`:
- Extends `@eslint/js` recommended ruleset
- Globals declared: `document`, `window`, `console`, `fetch`, `Date`, `marked`
- Rules:
  - `no-var`: error (enforce `let`/`const`)
  - `prefer-const`: warn
  - `eqeqeq`: error (enforce `===`)
  - `no-unused-vars`: warn

## Modified Files

### `frontend/script.js`
Applied Prettier-consistent formatting:
- Removed double blank lines between function sections
- Removed trailing whitespace on blank lines inside `setupEventListeners()`
- Normalized indentation in the `keypress` event handler callback (2-space indent)

## Setup Instructions

```bash
# Install dependencies (first time only)
npm install

# Check formatting and lint
npm run quality

# Auto-fix formatting and linting issues
npm run quality:fix
```
