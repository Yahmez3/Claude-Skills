# Win-back email

Trigger: 14 days since last `key_action`, and user reached activation.

**Subject:** `{{ specific_reason_to_come_back }}`

e.g.: `We fixed the sync bug` / `Your monthly report is ready` / `New: shared budgets`

---

{{ first_name }},

Haven't seen you in {{ app_name }} for a couple weeks. Quick note on what's changed:

- {{ concrete thing 1 — ideally something they specifically asked for or complained about }}
- {{ concrete thing 2 }}

If one of those is relevant: {{ deep_link_url }}

If not, what would bring you back? Reply and tell me — those replies steer what we build.

— {{ founder_name }}

---

**Don't:**
- Subject: "We miss you!" (grating, zero info)
- Imply guilt for not using
- Offer a discount as the first lever (trains users to wait for discounts)

**Variant to test:** personalized based on which feature they used most — mention an upgrade to THAT feature.
