# Admin Documentation

## Quick Links

- [Manage Products](/admin/shop/product/) — Edit descriptions, stock levels, and gallery images.
- [Manage Brands](/admin/shop/brand/) — Add or edit information for ceramicist brands.
- [Manage Top Page Carousel](/admin/shop/carouselimage/) — Update the home page images.
- [Manage News Items](/cms/pages/22/) — Write new updates for the front page.
- [Manage Blog Posts](/cms/pages/21/) — Write new stories and announcements.
- [Manage Glazes](/admin/shop/glaze/) — Configure available glaze types.
- [Manage Product Types](/admin/shop/producttype/) — Define categories (e.g., Bowls, Vases).
- [Store Settings](/admin/shop/storesettings/) — Pause or resume all sales.
- [Store Announcements](/admin/shop/storeannouncement/) — Manage the promotional banner on the site.
- [Stripe Dashboard](https://dashboard.stripe.com/products) — Manage your source-of-truth products and prices.

---

## Operations Guide

### 1. Adding a New Product
To add a new product to your store, follow these steps:

1. **Create in Stripe:** Log in to your Stripe Dashboard and create a new Product. The product must contain a name, a price and a photo.
2. **Automatic Sync:** The product will automatically appear in your tetote admin panel within seconds.
3. **Enhance:** Go to the [Products](/admin/shop/product/) section, select the new product, and:
   - Assign it to a **Brand**, **Glaze**, and **Product Type**. You can create those if they do not exist already.
   - Set the **Stock Quantity**.
   - Add additional **Gallery Images** if needed. The stripe dashboard only allows to set one photo, you can upload up to 8 photos per product.
   - Set the product to **Public** to make it visible on the site.

### 2. Pausing Sales
If you need to temporarily disable checkout for all products:

1. Go to [Store Settings](/admin/shop/storesettings/).
2. Toggle the **Sales Paused** checkbox.
3. Save. Customers will still be able to browse but won't be able to add items to their cart.

### 3. Displaying a Site-wide Announcement
To show a banner message at the top of the site (e.g., for holiday closures):

1. Go to [Store Announcements](/admin/shop/storeannouncement/).
2. Create a new announcement or edit an existing one.
3. Check the **Is Active** box. Ensure only one announcement is active at a time.

### 4. Managing the Top Page (Carousel)
The Top Page at `/` features a carousel of images that can be managed through the **Django Admin**.

1. Go to the [Manage Carousel Images](/admin/shop/carouselimage/) section.
2. To add a new image:
   - Click "Add Carousel Image".
   - Upload your image and give it a title (optional).
   - Set an **Order** (lower numbers appear first).
   - Ensure **Is Active** is checked.
3. To reorder or disable images:
   - You can edit the **Order** and **Is Active** fields directly in the list view.
4. Click **Save** to make the changes live.

*Note: Images will automatically stretch to fill the width. For best results, use high-resolution landscape images.*

---

## Blogging & Markdown Guide

When writing blog posts or product descriptions, you can use **Markdown** to format your text.

### Markdown Cheat Sheet

| Style | Syntax | Result |
|-------|--------|--------|
| **Bold** | `**text**` | **Bold text** |
| *Italic* | `*text*` | *Italic text* |
| [Link](https://google.com) | `[Label](url)` | [Link Label](url) |
| List | `- Item` | - Item |
| Numbered List | `1. Item` | 1. Item |
| Title | `# Title text` |  |
| Medium Header | `## Medium header` | |
| Small Header | `### Small header` | |
| Image | `![Alt Text](url)` | Embeds an image<br>(drag and drop an image file<br>into the text box to upload) |


### Writing Tips

- Use **H2 (##)** for section titles within your blog posts.
- Use **Bold** for emphasis, but sparingly.
- Keep paragraphs short for better readability on mobile devices.
