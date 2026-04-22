# Durham Civic Hub: Master Brief

I'm Nida Allam, Durham County Commissioner and owner of civichub.nidaallam.com. You're going to do a comprehensive overhaul of the site. Read this entire brief before starting any work. Work through the phases in order. After each phase, deploy to a preview URL, summarize what changed, and wait for my approval before moving on.
My email for commits, notifications, and error alerts: nidaallam@nidaallam.com

## Part 1: Setup

Complete all of Part 1 before touching any site code.

### 1.1 Git attribution

Configure this repo so commits appear as mine:
Run git config user.name "Nida Allam"
Run git config user.email "nidaallam@nidaallam.com"
Do NOT include "Co-Authored-By: Claude" lines in any commit.
Do NOT include "Generated with Claude Code" or any robot emoji in commit messages.
Write plain, human-style commit messages.
Add CLAUDE.md, .claude/, and any AI-tool config files to .gitignore.

### 1.2 Save this brief to the repo

Create /docs/ at the repo root.
Create /docs/master-brief.md and paste this entire brief into it.
Commit with message "Add site work brief."
Do not deploy to production. We'll use preview URLs throughout.

### 1.3 Hosting note

The site is currently on GitHub Pages with a public repo. Do not make the repo private; that breaks GitHub Pages on the free plan. If at any point we need a private repo, tell me first so we can migrate to Cloudflare Pages.

### 1.4 Voice and tone rules (apply to everything you write)

This site is written in Nida's personal voice. She is warm, casual, community-centered, and uses exclamation points naturally. Every piece of copy you write must follow these rules:
- Use exclamation points naturally. Keep existing ones. Add new ones where appropriate. Do not strip them out.
- No em dashes anywhere. Ever. Replace with commas, periods, or restructured sentences. Em dashes are the #1 AI tell on this site.
- Use "you" and "neighbors," never "residents" or "individuals."
- Flowing sentences, not stacked fragments. Not "Free. Nonpartisan. Built for Durham." Instead: "Free, nonpartisan, and built for Durham."
- Rhetorical questions and long flowing thoughts are good.
- Community-over-self framing. "We" and "our" are preferred over "I," except when Nida is speaking directly.
- Words to avoid sitewide (grep every HTML file for these and rewrite any hits):
  curated, seamless, robust, leverage, delve, foster (as verb),
  navigate the complexities, vibrant, bustling, nestled, tapestry,
  realm, landscape (as metaphor), empower, streamline, ensure,
  multifaceted, myriad, plethora, holistic, paradigm, elevate,
  resonate, underscore, akin to, testament to, at its core,
  in the realm of, it is important to note, it is worth noting,
  furthermore, moreover, in conclusion, in summary, crucial, pivotal

### 1.5 Automation philosophy

The goal is zero manual maintenance after initial setup. Apply these principles to every feature:
- If a feature requires me to manually update content, automate the source or do not build the feature.
- If a feature requires me to respond to form submissions, do not build it.
- No subscriber databases, email lists, or signup flows I have to manage.
- The only inbound-communication mechanism is the email CTAs on the Connect page, which go straight to my inbox.
- Every automated fetch includes error detection. If a source breaks, one email to me with the error and the script name. Not recurring.
- Every automated fetch includes link validation. Broken URLs get logged.
- If any item in this brief violates these principles, tell me and propose an alternative.

---

## Part 2: Fact-check and truthfulness audit (do this FIRST, before any other changes)

The site contains news items, phone numbers, meeting dates, and budget figures that may not all correspond to real sources. Before any other work:
- news.html: For every news item, verify it corresponds to a real published source (news article, press release, agenda item, or official announcement). If you can't verify it with a real URL to a real source, remove it. Do not leave any news item whose event you can't confirm. Show me the before-and-after list.
- resources.html: Verify every phone number against the organization's official site. Verify every address is current. Flag any you can't verify so I can check manually.
- meetings.html and "What's Happening Now" on index.html: Every meeting date, time, and location must match the official source (dconc.gov, durhamnc.gov, or dpsnc.net). Remove or fix anything that doesn't.
- All budget pages (budget.html, budget-county.html, budget-city.html, budget-schools.html, cip.html): Every dollar figure must match official adopted budget documents. Verify every number.
- voting.html: Verify every elected official is currently holding that office. Every bio URL must resolve to the correct person.

---

## Part 3: Audit fixes

### 3.1 Broken links

- transit.html, Durham Transit Plan card: Label currently says "durhamtransitplan.com" (domain doesn't resolve). Href currently gotriangle.org/about-us/ (wrong page). Fix href to https://engagedurham.com/DocumentCenter/View/559/2023-Durham-County-Transit-Plan?bidId=. Update label to "engagedurham.com (Durham County Transit Plan)".
- transit.html, Rail paragraph: Same bad link. Same fix.
- news.html, Ellerbe Creek Greenway story: Currently links to /Facilities/Facility/Details/96 (City Hall Annex page). If there's a real source for this story, link to it. Otherwise link to https://www.dprplaymore.org/595/Trails-Greenways. If the underlying event isn't real, remove the story entirely.

### 3.2 Data errors

- budget.html: CIP total currently shown as "$1.12B." Correct figure is $1.23B ($537.6M City + $550.2M 2022 County bond + $143.6M County capital). Fix.
- resources.html intro: "Programs and services for Durham neighbors housing help, food assistance…" is missing a comma. Rewrite to: "Programs and services for Durham neighbors! Housing help, food assistance, health care, legal aid, and more."

### 3.3 URL canonicalization

- Standardize on www.dconc.gov across every HTML file. Find and replace href="https://dconc.gov/ with href="https://www.dconc.gov/ sitewide. Verify each replacement still resolves.
- Pick one canonical path for Boards and Commissions (/Board-of-Commissioners/Boards-and-Commissions is likely correct; verify) and use it everywhere.
- Add trailing slashes: https://gotriangle.org → https://gotriangle.org/, same for www.dconc.gov, www.dpsnc.net, www.durhamnc.gov, www.thedcrc.org.

### 3.4 AI tells

- Grep every HTML file for the em dash character (U+2014). Replace every instance with a comma, a period, or a restructured sentence. Known locations: news.html banner, transit.html (multiple), resources.html reproductive health and DV sections, index.html "Why I Built This" section, "How to Ride" steps on transit.html.
- news.html: "Curated local news from Durham County sources" → "Local news from Durham County sources".

### 3.5 Voice rewrites

- news.html top banner. Currently: "What's happening in Durham government. Budget decisions, schools, housing, transit, and public health. All links go to official sources." Rewrite to: "Here's what's happening in Durham government right now! Budget fights, schools, housing, transit, public health. Every link goes straight to an official source."
- budget-city.html tax line. Currently: "Residents inside city limits pay both city and county taxes." Rewrite to: "If you live inside city limits, you pay both a city and a county tax rate!"

### 3.6 Buttons and links audit

Write a script that visits every page, finds every anchor and button, and verifies:
- Every href resolves to a real non-404 page.
- Every button with an onclick handler actually does something.
- No displayed label contradicts its href (e.g. label "Email Clerk" with empty href).

Produce a report of everything broken. Fix all broken items, including:
- The "email Clerk" buttons that are currently broken. They should open a pre-filled email draft to clerk@dconc.gov with subject "Public Comment for [Meeting Body] on [Date]" using mailto: links.

### 3.7 URLs should be buttons, not typed-out text

Audit every page for instances where a URL is displayed as visible label text (like "godurhamtransit.org" or "engagedurham.com"). Convert every one into a properly styled button with a human-readable action label.

### 3.8 Icon and graphic consistency

The site currently uses native emojis that render differently on iPhone, Android, Windows, and Chrome. Replace every emoji with Lucide icons (lucide.dev, free, MIT licensed, SVG-based). Use a single consistent weight and style. Match icon color to the brand palette. The Durham bull brand mark can stay but render it as a custom SVG, not the native emoji.

### 3.9 News page is not rendering

Debug news.html, test it in Chrome, Safari, and mobile, find the root cause, and fix it. Show me before and after.

### 3.10 Weather alert banner covering nav

Fix: Banner should push the nav down when an alert is active. Both visible. Nav dropdowns must remain usable. Works on mobile (375px wide) and desktop.

### 3.11 Weather alert is not working at all

Audit the current implementation. Fix the NWS zone code, User-Agent header, and CORS issues. Set up scheduled GitHub Action that hits NWS API hourly, writes to /data/alerts.json, and have the front-end read the JSON. Test with a fake active alert. Write a comment in the script explaining what was broken and why the fix works.

---

## Part 4: Data layer foundation

### 4.1 Create /data/ folder

Move all hardcoded content from HTML into JSON files. HTML pages read from JSON at build time.

Every JSON file has this top-level structure:
```json
{
  "lastFetched": "2026-04-22T00:00:00Z",
  "source": "description of where this came from",
  "data": [ ... actual content ... ]
}
```

### 4.2 GitHub Actions scaffolding

Create these workflow files (scaffolding only for now):
- daily-fetch.yml (news, meetings, elections, alerts — runs daily 7am ET)
- hourly-alerts.yml (weather alerts — runs hourly)
- monthly-check.yml (resources link check — runs 1st of month)
- yearly-fetch.yml (budget, officials — manual trigger)

### 4.3 Universal "last updated" footer

Add a shared component that reads the relevant JSON's lastFetched timestamp and shows "Last updated: [date]" at the bottom of each data-driven page.

---

## Part 5: Automation with guardrails

All automated fetches auto-merge updates to production when the data passes realistic sanity checks. If a fetch fails a check, it pauses and sends me one email with a one-click approve link (GitHub Actions workflow_dispatch URL). If I don't act on the email within 7 days, the fetch auto-approves anyway.

### 5.1 Budget fetches

Auto-merge if new top-line total is 0% to 12% higher than previous. Hold for approval if negative growth or more than 12% higher. Block and email "scraper broken" if new total differs by more than 25% either direction.
Runs yearly (manual trigger after budget adoption in late June).

### 5.2 Officials fetch

Sources: ncleg.gov, dconc.gov, durhamnc.gov, dpsnc.net.
Guardrails: Auto-merge if 0 to 2 officials changed. Hold if 3+ changed. Block if fewer than 20 or more than 30 returned.
Runs yearly (manual trigger after November elections).

### 5.3 News fetch

Sources: dconc.gov, durhamnc.gov/rss.aspx, dpsnc.net, gotriangle.org/feed/.
Generate a one-sentence "what this means for you" line using the Anthropic Claude API (ANTHROPIC_API_KEY in GitHub Actions secrets). Cache per URL.
Guardrails: Auto-merge if fewer than 10 items changed. Hold if 10+ changed. Block if all items disappeared.
Runs daily 7am ET.

### 5.4 Meetings fetch (runs DAILY)

Sources: BOCC, City Council, DPS Board, Planning Commission.
Each meeting record includes: title, body, date, time, location, agenda URL, livestream URL, Zoom URL, public comment deadline.
Generate /meetings.ics on every build.
Runs daily 7am ET.

### 5.5 CIP fetch

Source: Durham open data portal. Fall back to annual PDF scrape.
Runs weekly Sunday night.

### 5.6 Elections fetch

Source: ncsbe.gov/voting/upcoming-election.
Runs monthly (1st of month).

### 5.7 Weather alerts

Source: api.weather.gov/alerts/active?zone=NCC063.
Write to /data/alerts.json.
Runs hourly.

### 5.8 Resources link check

Monthly. Log 404s in /data/validation-log.json.

### 5.9 Global automation rules

- Every run writes to /data/changelog.json.
- Every run writes to /data/validation-log.json.
- Never send more than one email per issue.
- Auto-rollback if deploy fails.
- Write each fetch script to output to a temp file, validate, only overwrite if validation passes.

---

## Part 6: Feature additions

### 6.1 iCalendar subscribe button

On meetings.html, add a prominent "Subscribe to Durham meetings in your calendar" button. Include "Add to Google Calendar," "Add to Apple Calendar," "Add to Outlook" deep-link buttons.

### 6.2 RSS feed

Generate /news.xml from /data/news.json on every build. "Subscribe via RSS" button on news.html.

### 6.3 "Speak at a meeting" helper (meetings.html)

Four-step walkthrough: pick body, show rules, show upcoming meeting details, draft generator using Claude API (server-side, Cloudflare Worker or Netlify Function). Pre-filled mailto: link to clerk@dconc.gov.

### 6.4 Voting page upgrades

Live election countdown, "What's on my ballot" deep-link, Voter ID reminder card, "How to vote" three-tab micro-guide.

### 6.5 Resources page upgrades

Search box, pinned "Most urgent" section (988, Durham Crisis Response Center, Siembra NC, HEART), Google Maps pin links, "Español disponible" tag.

### 6.6 My Durham upgrades

"Save this address" with localStorage, trash/recycling day, nearest fire station, nearest police substation, school attendance zone, "Email these results," print view.

### 6.7 Connect page warmth rewrite

Intro in Nida's voice, response time note, office hours, FAQ, "What I'm working on right now" card from /data/issues.json.

### 6.8 News page upgrades

Search box, sort toggle, "what this means for you" line per item.

---

## Part 7: Deeper features

### 7.1 Issues tracker page

issues.html — "What's the County working on?" Each issue: title, plain-language summary, status, next key date, "How to weigh in" CTA. Store in /issues/ folder as markdown.

### 7.2 Civic glossary

glossary.html — Durham government terms in plain English. Link key terms sitewide.

### 7.3 Advocacy toolkit

advocacy.html — Contact your reps, show up, organize (list withheld pending confirmation), rapid response.

### 7.4 Budget Explorer upgrades

Compare to other NC counties, historical 5-year slider, expanded tax receipt calculator, "Share this" PDF.

---

## Part 8: Polish and infrastructure

### 8.1 Spanish language toggle

EN/ES toggle. Phase 1: home, My Durham, Resources, Voting, Connect. Resources must be human-translated (partner with El Centro Hispano).

### 8.2 Progressive Web App

manifest.json, service worker for offline caching, "Add to home screen" prompt on mobile after second visit.

### 8.3 Open Graph share cards

Generate OG images for every page at build time.

### 8.4 Analytics and feedback

Plausible analytics. Footer "Something missing? Broken link? Tell me!" widget. Thumbs up/down on resource cards and news items.

### 8.5 Accessibility pass

Alt text, WCAG AA contrast, keyboard navigation, ARIA attributes, axe DevTools audit.

---

## Part 9: QA checklist (run after every phase)

**Links:** Every internal link resolves. Every external link returns 200. No href mismatches. Every button works.

**Voice:** Zero em dashes. Zero banned words. Exclamation points where natural. No "residents" or "individuals."

**Facts:** Budget figures match official docs. Elected officials verified. Crisis-line numbers tested.

**Data freshness:** Every data-driven page shows "Last updated." No GitHub Action failed in last 48 hours.

**Mobile:** Clean at 375px wide. Buttons thumb-sized. No horizontal scroll. Nav dropdowns work with alerts banner.

**Accessibility:** axe DevTools zero critical issues. Keyboard-only navigation reaches everything.

---

## Start here

Begin with Part 1, then Part 2. Do not touch Part 3 until Parts 1 and 2 are complete and verified. Report back after each part and wait for my sign-off.
