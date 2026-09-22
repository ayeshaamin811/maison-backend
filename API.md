# Products API

Read-only catalogue API for the storefront. No auth — every endpoint is public.

**Base URL**

| Environment | URL |
| --- | --- |
| Local | `http://127.0.0.1:8000/api` |
| Production | `https://<your-service>.up.railway.app/api` |

Put it in one place in the frontend:

```js
// src/lib/api.js  (Create React App, so REACT_APP_ prefix)
export const API_BASE =
  process.env.REACT_APP_API_BASE || "http://127.0.0.1:8000/api";
```

CORS is allow-listed, not open. `http://localhost:3000` and `http://127.0.0.1:3000`
work out of the box; any other origin has to be added to the backend's
`CORS_ALLOWED_ORIGINS` env var or the browser will block the request.

---

## `GET /api/products/`

Paginated list, 24 per page. Only products marked active in the admin appear.

```json
{
  "count": 26,
  "next": "http://127.0.0.1:8000/api/products/?page=2",
  "previous": null,
  "results": [ /* product objects, see below */ ]
}
```

`next` / `previous` are complete URLs — follow them directly rather than
rebuilding the query string.

### Query parameters

All of these combine freely.

| Param | Example | Notes |
| --- | --- | --- |
| `category` | `?category=casual` | Matches a collection, edit **or** fabric slug |
| `collection` | `?collection=casual` | One collection slug per product |
| `fabric` | `?fabric=lawn` | Optional on a product |
| `edit` | `?edit=new-arrivals` | Repeatable; two `edit` params mean **both** |
| `is_best_seller` | `?is_best_seller=true` | `true` / `false` |
| `size` | `?size=M` | Matches one label in the product's `sizes` |
| `min_price` | `?min_price=5000` | Plain number, no `Rs.` |
| `max_price` | `?max_price=9000` | Plain number, no `Rs.` |
| `search` | `?search=velvet` | Name, SKU, shirt detail, composition, collection |
| `sort` | `?sort=price-asc` | See below |
| `page` | `?page=2` | 1-indexed |
| `page_size` | `?page_size=48` | Optional override, capped at 96 |

`collection`, `fabric` and `size` also accept a comma-separated list
(`?size=M,L`), which reads as **any of**.

**`category` vs `collection`/`edit`/`fabric`.** `category` is the server-side
twin of the storefront's `product.category.includes(slug)` — it matches any of
the three without the caller knowing which kind of slug it has. Use it for
routes like `/collection/<slug>`, where the slug may be either a collection
(`casual`) or an edit (`new-arrivals`). Use the precise params for a filter
sidebar, where you do know. Repeating `?category=` narrows:
`?category=casual&category=new-arrivals` means in both.

**Slugs** — these are fixed and match the URLs already live on the storefront:

- `collection`: `solids` `embroidered` `unstitched` `casual` `west` `formals`
- `fabric`: `lawn` `crepe` `matte-twill` `linen` `silk`
- `edit`: `new-arrivals` `formal-edit` `co-ordsets` `fusion-edit`

**`sort` values** — omit for catalogue order (the order the grid renders today):

`newest` · `oldest` · `price-asc` · `price-desc` · `name-asc` · `name-desc` · `best-sellers`

### Error behaviour

Filtering is forgiving on purpose, because these params come from URLs a user
can edit:

- An unknown slug returns **200 with `count: 0`**, never a 404.
- A malformed `min_price` / `max_price` / `sort` is **ignored**, not rejected.
- `?page=` beyond the last page is the one exception — that returns **404**.

```
GET /api/products/?collection=does-not-exist   ->  200  { "count": 0, "results": [] }
GET /api/products/?sort=banana                 ->  200  (default order)
GET /api/products/?page=99                     ->  404
```

---

## `GET /api/products/<id>/`

A single product, same object shape as a `results` entry. Returns **404** for an
unknown id or a product deactivated in the admin.

---

## Product object

```json
{
  "id": 1,
  "name": "2 Pc Printed Cambric Suit",
  "category": ["casual", "new-arrivals", "lawn"],
  "sku": "MB-MN26-08-BLACK-EX LARGE",
  "price": "Rs.6,990.00",
  "priceValue": 6990.0,
  "oldPrice": null,
  "discount": null,
  "rewardMin": "Rs. 280",
  "rewardMax": "Rs. 699",
  "image": "http://127.0.0.1:8000/media/products/image-1.webp",
  "hoverImage": "http://127.0.0.1:8000/media/products/image-1-hover.webp",
  "images": [
    "http://127.0.0.1:8000/media/products/image-1.webp",
    "http://127.0.0.1:8000/media/products/image-1-hover.webp"
  ],
  "composition": "2 Piece - Shirt & Trouser",
  "shirtDetail": "Printed Straight Shirt",
  "details": ["Fabric: Cambric", "Wash Care: Dry clean only", "Country of Origin: Pakistan"],
  "sizes": ["XS", "S", "M", "L", "XL"],
  "stock": 2,
  "isBestSeller": false
}
```

### Field notes

**`priceValue` is the number to do maths with.** `price` is a pre-formatted
display string. Use `priceValue` for cart totals and never re-parse `price` —
the parse works, but it is one formatting change away from silently producing
wrong totals.

```js
// Yes
const total = items.reduce((sum, i) => sum + i.priceValue * i.qty, 0);

// No
const total = items.reduce((sum, i) => sum + parseFloat(i.price.replace(/Rs\.|,/g, "")) * i.qty, 0);
```

**`oldPrice` and `discount` are `null` when there is no markdown** — not `""`,
not `0`. Render the strikethrough only when `oldPrice` is truthy.

**`rewardMin` / `rewardMax` use a different format** from `price`: `"Rs. 280"`,
with a space and no decimals. They are display-only.

**`category` is one flat array** of collection slug, then edit slugs, then the
fabric slug if the product has one. It is what the existing filter logic on the
frontend already reads, so nothing there needs to change.

**Image URLs are always absolute** and safe to drop straight into `src`. In
production they point at the Cloudflare R2 domain rather than the API host —
never concatenate a base URL onto them.

**`images` is the gallery.** It falls back to `[image, hoverImage]` when a
product has no gallery rows, so it always has at least one entry.

---

## Examples

```js
const res = await fetch(`${API_BASE}/products/?collection=casual&page=1`);
const { count, next, results } = await res.json();
```

```js
// Combined filters
`${API_BASE}/products/?collection=west&edit=co-ordsets&min_price=5000&sort=price-asc`

// Best sellers for the home page
`${API_BASE}/products/?is_best_seller=true`

// Product detail page
`${API_BASE}/products/${id}/`
```

---

## Where the data comes from

Products are managed entirely in the Django admin at `/admin/` — add, edit,
deactivate, upload images, reorder gallery shots. Anything saved there shows up
in this API on the next request. No deploy, no code change, no seed script.

The 26 products currently in the database were ported from the frontend's old
`src/data/products.jsx`, so the shape matches what the components already expect.
