# App Store listing — working draft

Fill out both platforms. Run `aso_lint.py` before submitting.

## iOS (App Store Connect)

### App Name (≤30 chars)
`{{ brand }} — {{ category_hook }}`

### Subtitle (≤30 chars)
`{{ one-line value prop }}`

### Keywords (≤100 chars, comma-separated, no spaces, single words, no repeats from Name/Subtitle)
```
kw1,kw2,kw3,kw4,kw5,kw6,kw7,kw8,kw9,kw10
```

### Promotional Text (≤170 chars) — update per release
`What's new in this version, or seasonal hook. Indexed: no.`

### Description (≤4000 chars) — the web page for SEO
```
{{ Opening line that restates the promise. One sentence. }}

{{ Paragraph 1 — who it's for and the problem }}

{{ Paragraph 2 — what it does (verbs, not features) }}

KEY FEATURES
• {{ feature 1 — benefit-led }}
• {{ feature 2 }}
• {{ feature 3 }}
• {{ feature 4 }}

{{ Paragraph 3 — social proof: press, numbers, testimonial }}

{{ Paragraph 4 — privacy / trust where relevant }}

SUBSCRIPTIONS (if applicable)
• {{ Plan name }} — {{ price }} / month ({{ period }})
• {{ Plan name }} — {{ price }} / year
Payment charged to Apple ID. Subscriptions auto-renew unless canceled ≥24h before period end. Manage in Settings. [Privacy Policy URL] [Terms URL]
```

---

## Android (Google Play Console)

### Title (≤30 chars)
`{{ brand }}: {{ category_hook }}`

### Short description (≤80 chars) — HEAVILY indexed, this is ASO gold on Play
`{{ value prop + 1 keyword + 1 keyword — this is the most important 80 chars }}`

### Full description (≤4000 chars)
Same structure as iOS — but know that every word is indexed. Aim for natural density (<5% per keyword). Stuffing gets penalized.

```
{{ opening }}

{{ 2-3 paragraphs with target keywords woven in naturally }}

▸ {{ feature }}
▸ {{ feature }}
▸ {{ feature }}

{{ trust + subscription block as above }}
```

### Graphics spec

| Asset | iOS | Android |
|---|---|---|
| Icon | 1024×1024 PNG, no alpha | 512×512 PNG |
| Screenshots (6.7") | 1290×2796 | 1080×1920+ |
| Feature graphic | — | 1024×500 |
| Preview video | up to 30s | up to 30s |
