# Tetote: Artisanal Japanese Ceramics Boutique

Tetote is a high-end, minimalist e-commerce platform and digital showroom dedicated to high-quality Japanese wares. The project emphasizes professional aesthetics, artisanal storytelling, and rigorous engineering standards.

## 🇯🇵 Design Philosophy
- **Minimalist Japanese Aesthetic:** The UI uses a warm, muted palette (**Bone White**, **Soft Charcoal**, **Muted Olive Earth**) to evoke a sense of calm and focus on the craftsmanship of the products.
- **Showroom Experience:** The platform serves as both a shop and a gallery. High-resolution imagery, smooth transitions (Splide & PhotoSwipe), and delicate typography (Cormorant Garamond) are central to the brand identity.
- **Professional & Zen:** Every interaction is designed to be intentional and non-intrusive. High-contrast colors are avoided in favor of organic, understated tones.

## 🛠 Engineering Standards & Practices
- **Vanilla over Frameworks:** We prioritize native web standards and vanilla JavaScript to maintain a lightweight, high-performance codebase. We use **npm** to manage core dependencies (Splide, PhotoSwipe) and **esbuild** for a lightweight bundling process.
- **Frontend Build Process:** We use Tailwind CSS for styling and esbuild for JavaScript bundling (Splide, PhotoSwipe). While Django template logic changes are immediate, you **must** run the build command whenever you add new Tailwind utility classes to templates or modify JavaScript in the `assets/` directory.
- **Security First:** Sensitive data (Stripe keys, Django secrets) is strictly managed via environment variables and protected by aggressive `.gitignore` and `pre-commit` rules.
- **High Test Coverage:** The project maintains near-total test coverage across both the Django backend (Python) and the modular frontend (Node/Vitest/JSDOM).
- **Hybrid Content Management:**
    - **Stripe:** Acts as the source of truth for **Products and Prices**.
    - **Wagtail CMS:** Powering the **Blog and artisanal storytelling** with a flexible StreamField-based editor.
    - **Django:** Acts as the source of truth for **Inventory (Stock)**, **Brands**, **Glaze**, **Product Types**, and **Shop Translations**.
- **Surgical Sync Logic:** Integration with Stripe is "surgical"—webhooks and sync commands only update specific fields (like `stripe_name` and `price`), ensuring that manual stock levels and translations managed in the Django Admin are never overwritten.
- **Consistency:** Coding practices are enforced via `Ruff` (linting/formatting) and custom git hooks.

## 🏗 Technical Stack
- **Backend:** Django 6.0+ (Python 3.14+)
- **CMS:** Wagtail 7.4+ (LTS)
- **Frontend:** Vanilla JS (ES Modules), Tailwind CSS
- **Database:** SQLite (Development) / `django-modeltranslation` (Shop) / Wagtail i18n (Blog)
- **Payments:** Stripe (Checkout Sessions & Webhooks)
- **Testing:**
    - **Django Test Suite** (including `WagtailPageTestCase`) for business logic and integrations.
    - **Playwright Integration Tests** for E2E user journeys (Chrome headless).
    - **Vitest & JSDOM** for isolated frontend unit testing.
- **Package Management:** `uv` (Python), `npm` (JS)

## 🚀 Key Features
- **Smart Filtering:** A rich, URL-persistent chip system allowing multiple selections and single-click toggles.
- **Persistent Cart:** A `localStorage` driven cart with real-time local stock verification.
- **Dynamic Showroom:** Smooth cross-fade hover effects and a high-performance, navigable fullscreen gallery (PhotoSwipe v5).
- **Wagtail-Powered Blog:** A highly flexible, StreamField-powered blog system for sharing event stories and ceramic techniques with native multi-language support.
- **Custom Toast System:** A non-intrusive, styled notification library for user feedback.

## 📋 Development
### Requirements
- `uv` installed
- `stripe-cli` (for local webhook testing)
- `node` & `npm` (for frontend tests)

### Commands
- **Run Server:** `uv run python manage.py runserver`
- **Sync Stripe:** `uv run python manage.py sync_stripe` (Updates products/prices without touching stock)
- **Build All Assets:** `npm run build` (Builds both CSS and JS)
- **Watch CSS:** `npm run watch:css` (Recommended during CSS development)
- **Watch JS:** `npm run watch:js` (Recommended during JS development)
- **Run Unit Tests:** `npm run test:unit` (Fast, no browser)
- **Run Integration Tests:** `npm run test:integration` (Playwright, headless browser)
- **Formatting:** `uv run ruff format .`

## 🔒 Security Note
Never hardcode secrets. Ensure `.env` is populated with `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET`.

## 📦 Deployment Note
Since generated assets (`styles.css` and JS bundles) are not tracked in Git, you **must** run the following commands in your deployment pipeline before `collectstatic`:
1. `npm install`
2. `npm run build`
3. `python manage.py collectstatic`
