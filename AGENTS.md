# Instructions for AI Agents

Welcome to Tetote. This document provides critical procedural and architectural guidance for agents contributing to this codebase. Adhering to these rules is mandatory to maintain the project's minimalist integrity and engineering rigor.

## 🏗 Core Architecture
- **Hybrid Data Model:** Stripe is the source of truth for **Product IDs and Price amounts**. Django is the source of truth for all the rest.
- **Surgical Syncing:** When handling Stripe webhooks or sync commands (see `integrations/views.py`), **NEVER** overwrite the `name` (translatable), `description`, or `stock_quantity` fields if the product already exists. Only look at fields that are part of the message sent in the webhook and update those fields only.
- **Vanilla First:** Do not introduce frontend frameworks (React, Tailwind, etc.). Use Vanilla JS (ES Modules) and Vanilla CSS. Maintain the CSS variables defined in `templates/base.html`.

## 🎨 Design System
- **Palette:**
    - Background: `#fdfcfb` (Bone White)
    - Primary Text: `#2c2c2c` (Soft Charcoal)
    - Accents: `#4a5d4e` (Muted Olive)
- **Typography:** Primary font is **Cormorant Garamond**. Use it for all UI elements, including form inputs and buttons.
- **State:** Drawer and filter states must be persisted in the URL (e.g., `?expanded=true`).

## 🛠 Engineering Standards
- **Test Coverage:** Maintain 95%+ coverage.
    - Use Django standard tests for backend logic.
    - Use **Vitest + JSDOM** for frontend logic (no browser-only tests).
- **Code Quality:**
    - Formatting/Linting is strictly enforced by **Ruff**.
    - Run `uv run ruff format .` before finishing any task.
- **Localization:** All user-facing strings **must** be wrapped in `{% translate %}` or `gettext_lazy`. The project uses `django-modeltranslation`.

## 🧪 Testing Workflow
1. **Backend:** `uv run python manage.py test`
2. **Frontend:** `npm test`
3. **Surgical Verification:** If you modify sync logic, verify that manual local data (like stock) is preserved after a sync.

## 🐙 GitHub Workflow
- **Issue Management:** Always prefer closing issues automatically via git commit messages (e.g., `Closes #18`) in the push to the remote, rather than using the `gh` CLI directly.

## 🔒 Security
- Do not commit `.env` or `db.sqlite3`.
- Sensitive keys are accessed via `django-environ`.
