# Instructions for AI Agents

Welcome to Tetote. This document provides critical procedural and architectural guidance for agents contributing to this codebase. Adhering to these rules is mandatory to maintain the project's minimalist integrity and engineering rigor.

## 🏗 Core Architecture
- **Hybrid Data Model:** Stripe is the source of truth for **Product IDs and Price amounts**. Django is the source of truth for all the rest.
- **Surgical Syncing:** When handling Stripe webhooks or sync commands (see `integrations/views.py`), **NEVER** overwrite the `name` (translatable), `description`, or `stock_quantity` fields if the product already exists. Only look at fields that are part of the message sent in the webhook and update those fields only.
- **Vanilla First:** Do not introduce frontend frameworks (React, Vue, etc.). Use Vanilla JS (ES Modules) and Tailwind for CSS. Use **npm run build** to bundle assets.
- **Frontend Build:** When adding new Tailwind classes to templates, or modifying styles and scripts in the `assets/` directory, you **MUST** run `npm run build` to update the static assets.

## 🎨 Design System
- **Palette:**
    - Background: `#fdfcfb` (Bone White)
    - Primary Text: `#2c2c2c` (Soft Charcoal)
    - Accents: `#4a5d4e` (Muted Olive)
- **Typography:** Primary font is **Cormorant Garamond**. For Japanese content (`lang="ja"`), the font switches to **Noto Serif JP**. Use `font-serif` for all UI elements, including form inputs and buttons.
- **State:** Drawer and filter states must be persisted in the URL (e.g., `?expanded=true`).

## 🛠 Engineering Standards
- **Test Coverage:** Maintain 95%+ coverage.
    - Use Django standard tests for backend logic.
- **Code Quality:**
    - Formatting/Linting is strictly enforced by **Ruff**.
    - Run `uv run ruff format .` before finishing any task.
- **Localization:**
    - All user-facing strings **must** be wrapped in `{% translate %}` or `gettext_lazy`.
    - The **Shop** and **Blog** use `django-modeltranslation`.
- **CMS Management:**
    - The **Django Admin** (`/admin/`) is for commerce, inventory, brands, and the blog.

## 🧪 Testing Workflow
1. **Unit Tests:** `npm run test:unit` (Backend + Frontend unit tests)
2. **Integration Tests:** `npm run test:integration` (Playwright E2E journeys)
3. **Surgical Verification:** If you modify sync logic, verify that manual local data (like stock) is preserved after a sync.

## 🐙 GitHub Workflow
- **Issue Management:** Always prefer closing issues automatically via git commit messages (e.g., `Closes #18`) in the push to the remote, rather than using the `gh` CLI directly.

## Stripe integration
- **Documentation:** https://docs.stripe.com/ is the source of truth, find what you need there when you need it.
- **stripe-cli:** can be used for local webhook testing.

## 🔒 Security
- Do not commit `.env` or `db.sqlite3`.
- Sensitive keys are accessed via `django-environ`.

## Others

More general project guidance and information is written in @README.md
