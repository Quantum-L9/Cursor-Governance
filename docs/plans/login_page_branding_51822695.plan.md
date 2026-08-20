---
name: Website branding + Cognito quote form integration
overview: Brand the Odoo login/website with Scrap Management logo and company info, hide unused menus, and wire up Cognito Forms 'Get A Quote' to the existing web leads webhook.
todos:
  - id: create-module
    content: Create plasticos_website module skeleton (__init__.py, __manifest__.py)
    status: completed
  - id: logo-static
    content: Copy docs/only logo.png to plasticos_website/static/src/img/logo.png and set as company logo via XML
    status: completed
  - id: website-data
    content: Create data/website_data.xml — set website name, social URLs, deactivate unused menu items
    status: completed
  - id: footer-template
    content: Create views/website_templates.xml — override footer with company name + address, real social links
    status: completed
  - id: commit-push
    content: Stage, commit, push to staging
    status: completed
  - id: cognito-setup
    content: Provide Cognito Forms webhook setup instructions (URL, Bearer token, field mapping)
    status: pending
isProject: false
---

# Track 1: Website Branding (`plasticos_website` module)

## What changes


| Element             | Before (default)                                                    | After                                                                          |
| ------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Header logo         | "Your Logo" text                                                    | Scrap Management recycling logo (`docs/only logo.png`)                         |
| Header phone        | +1 555-555-5556                                                     | +1 704-698-5186 (from company.xml)                                             |
| Header menus        | Home, Shop, Events, Forum, Blog, Help, Courses, Appointment, Jobs   | Home only (all others hidden)                                                  |
| Footer "About us"   | Generic Odoo boilerplate                                            | "Scrap Management Inc — 10612-D Providence Rd #750, Charlotte, NC 28277"       |
| Footer email        | [info@yourcompany.example.com](mailto:info@yourcompany.example.com) | [info@scrapmanagement.com](mailto:info@scrapmanagement.com) (from company.xml) |
| Footer social links | Empty placeholder icons                                             | Real links from scrapmanagement.com (Instagram, Twitter/X, Facebook, LinkedIn) |


## File structure

```
plasticos_website/
  __init__.py                   (empty)
  __manifest__.py
  static/src/img/logo.png      (copied from docs/only logo.png)
  data/website_data.xml         (website record, logo, menus, social URLs)
  views/website_templates.xml   (footer override)
```

### 1. Logo

Copy `docs/only logo.png` to `plasticos_website/static/src/img/logo.png`. Set it as the company logo via `res.company` record in XML using `file="plasticos_website/static/src/img/logo.png"` on the `logo` field. This sets both the backend company logo and the website header logo.

### 2. `data/website_data.xml`

- Write `logo` on `base.main_company` using file attribute
- Write social media URLs on `website.default_website`:
  - `social_facebook`: from scrapmanagement.com footer (Facebook)
  - `social_twitter`: from scrapmanagement.com footer (Twitter/X)
  - `social_linkedin`: from scrapmanagement.com footer (LinkedIn)
  - `social_instagram`: from scrapmanagement.com footer (Instagram)
- Deactivate menu items by writing `is_visible=False`:
  - `website.menu_shop` (Shop)
  - `website_event.menu_events` (Events)
  - `website_forum.menu_forum` (Forum)
  - `website_blog.menu_blog` (Blog)
  - `website_helpdesk.menu_helpdesk` (Help)
  - `website_slides.menu_slides` (Courses)
  - `website_appointment.menu_appointment` (Appointment)
  - `website_hr_recruitment.menu_jobs` (Jobs)

### 3. `views/website_templates.xml`

- Inherit `website.footer_default` to replace the "About us" description paragraph with: company name + address (minimal one-liner)
- Social links will auto-populate from the `website` record social URL fields set above

### Key details

- `noupdate="1"` on company logo and footer text (one-time seed, UI edits preserved)
- `noupdate="0"` on menu deactivation (re-applies on upgrade to keep menus hidden)
- Some menu XML IDs may differ in Odoo 19 — will verify against actual module names before writing

---

# Track 2: Cognito Forms → Odoo Integration

**No code changes needed.** The [plasticos_web_leads](plasticos_web_leads/) module already has the webhook endpoint, AI triage pipeline, and configuration UI. This is purely a setup/configuration task.

### Steps (after build succeeds)

1. **In Odoo**: Navigate to Web Lead Config, click "Generate New API Key", copy the token
2. **In Cognito Forms**: On the quote form, add a Webhook action:
  - URL: `https://<odoo-staging-url>/api/v1/cognito-webhook`
  - Header: `Authorization: Bearer <api-key>`
  - Method: POST, Format: JSON
3. **Field mapping**: Cognito form fields should use names the module expects (EntryId, YourBusinessCompanyName, YourName, Email, Phone, DescribeYourMaterial, WhatIsTheQuantity, etc.)
4. **Test**: Submit the Cognito form, verify a `plasticos.web.lead` record appears in Odoo
5. **(Optional)**: Set OpenAI API key in Web Lead Config to enable AI triage (auto HOT/COLD classification)

I will provide detailed setup instructions after the branding module is deployed.