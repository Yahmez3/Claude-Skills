# Onboarding email sequence

Drip triggered by `signup_completed`. Every email has ONE job. Don't stack CTAs.

---

## Email 1 — 10 minutes after signup
**Subject:** `Get started in 60 seconds`
**From:** `{{ founder_name }} <{{ founder_name }}@{{ domain }}>`

Hey {{ first_name }},

Thanks for trying {{ app_name }}. The fastest way to get value: {{ activation step — one concrete action }}.

Here's how: {{ 2-3 sentence walkthrough or single link into the app at the right screen }}.

Reply to this email if you get stuck — it comes straight to me.

— {{ founder_name }}

---

## Email 2 — 24h after signup, only if NOT activated
**Subject:** `Stuck? Here's the 2-minute version`
**Trigger:** `signup_completed` AND NOT `activation` within 24h

{{ first_name }},

Most people who get value from {{ app_name }} do {{ activation step }} in the first day. If you haven't yet, it's usually because of {{ top friction }}.

Here's the fix: {{ one specific step }}.

If that's not the blocker, tell me what is — I'll help personally.

---

## Email 3 — 3 days after activation
**Subject:** `One more thing worth trying`
**Trigger:** `activation` + 3d

You've done {{ activation step }} — good. The feature people tell us they wish they'd found sooner is {{ feature }}.

[See it in action →]({{ deep_link }})

---

## Email 4 — 7 days after signup
**Subject:** `What's working, what's not?`
**Trigger:** 7d after signup

Would love 60 seconds of honesty: what's the ONE thing {{ app_name }} doesn't do that you wish it did?

Just reply. No form, no tracking. We read every one.

---

## Notes

- Send from a real person's address, not `noreply@`. Doubles reply rate.
- Plain text. No big brand header images. It triggers promo-tab classification.
- First-name merge only. Don't fake familiarity beyond that.
- Unsubscribe link in the footer, but keep it transactional where legally valid.
