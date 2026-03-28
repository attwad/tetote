# Tetote: Artisanal Japanese Ceramics Boutique

Tetote is a high-end, minimalist e-commerce platform and digital showroom dedicated to high-quality Japanese wares. The project emphasizes professional aesthetics, artisanal storytelling, and rigorous engineering standards.

## 🇯🇵 Design Philosophy
- **Minimalist Japanese Aesthetic:** The UI uses a warm, muted palette (**Bone White**, **Soft Charcoal**, **Muted Olive Earth**) to evoke a sense of calm and focus on the craftsmanship of the products.
- **Showroom Experience:** The platform serves as both a shop and a gallery. High-resolution imagery, smooth transitions (Embla Carousel), and delicate typography (Cormorant Garamond) are central to the brand identity.
- **Professional & Zen:** Every interaction is designed to be intentional and non-intrusive. High-contrast colors are avoided in favor of organic, understated tones.

## 🛠 Engineering Standards & Practices
- **Vanilla over Frameworks:** We prioritize native web standards and vanilla JavaScript to maintain a lightweight, high-performance codebase and avoid unnecessary third-party dependencies. One exception is tailwindcss that must be used for CSS.
- **Security First:** Sensitive data (Stripe keys, Django secrets) is strictly managed via environment variables and protected by aggressive `.gitignore` and `pre-commit` rules.
- **High Test Coverage:** The project maintains near-total test coverage across both the Django backend (Python) and the modular frontend (Node/Vitest/JSDOM).
- **Hybrid Content Management:**
    - **Stripe:** Acts as the source of truth for **Products and Prices**.
    - **Django:** Acts as the source of truth for **Inventory (Stock)**, **Brands**, **Glaze**, **Product Types**, and **Translations**.
- **Surgical Sync Logic:** Integration with Stripe is "surgical"—webhooks and sync commands only update specific fields (like `stripe_name` and `price`), ensuring that manual stock levels and translations managed in the Django Admin are never overwritten.
- **Consistency:** Coding practices are enforced via `Ruff` (linting/formatting) and custom git hooks.

## 🏗 Technical Stack
- **Backend:** Django 6.0+ (Python 3.14+)
- **Frontend:** Vanilla JS (ES Modules), Tailwind CSS
- **Database:** SQLite (Development) / `django-modeltranslation` (EN, DE, FR, JA)
- **Payments:** Stripe (Checkout Sessions & Webhooks)
- **Testing:**
    - **Django Test Suite** for business logic and integrations.
    - **Vitest & JSDOM** for isolated frontend unit testing.
- **Package Management:** `uv` (Python), `npm` (JS)

## 🚀 Key Features
- **Smart Filtering:** A rich, URL-persistent chip system allowing multiple selections and single-click toggles.
- **Persistent Cart:** A `localStorage` driven cart with real-time local stock verification.
- **Dynamic Showroom:** Smooth cross-fade hover effects and a native `<dialog>` based fullscreen viewer.
- **Artisanal Blog:** A Markdown-powered blog system for sharing event stories and ceramic techniques.
- **Custom Toast System:** A non-intrusive, styled notification library for user feedback.

## 📋 Development
### Requirements
- `uv` installed
- `stripe-cli` (for local webhook testing)
- `node` & `npm` (for frontend tests)

### Commands
- **Run Server:** `uv run python manage.py runserver`
- **Sync Stripe:** `uv run python manage.py sync_stripe` (Updates products/prices without touching stock)
- **Run All Tests:** `uv run python manage.py test && npm test`
- **Formatting:** `uv run ruff format .`

## 🔒 Security Note
Never hardcode secrets. Ensure `.env` is populated with `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET`.
