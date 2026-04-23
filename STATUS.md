# Durham Civic Hub — Status

## Current Phase
Part 6 QA complete — all Parts 1-3 items addressed

## Last Deploy
Not yet deployed via GitHub Actions (manual pushes only — HTTPS auth not configured locally)

## Last Successful Fetch Per Source
| Source | Last Run | Status |
|--------|----------|--------|
| News (dconc.gov, durhamnc.gov, etc.) | Pending first Actions run | Not yet run |
| Meetings (BOCC, City Council, DPS) | Pending first Actions run | Not yet run |
| Weather alerts (NWS NCC063) | Pending first Actions run | Not yet run |
| Officials (ncleg.gov, dconc.gov) | Pending first Actions run | Not yet run |
| Elections (ncsbe.gov) | Pending first Actions run | Not yet run |
| Budget figures | Pending first Actions run | Not yet run |
| CIP data | Pending first Actions run | Not yet run |
| Resources link check | Pending first Actions run | Not yet run |

## Open Questions (GitHub Issues with label `question`)
None open

## Known Fact Corrections Applied
See `data/changelog.json` for full log.
- County Manager name: "David Sparks" (fabricated) replaced with "Claudia Hager" (verified at dconc.gov)
- East Regional Library address: "211 W Woodcroft Pkwy" corrected to "211 Lick Creek Lane, Durham, NC 27703"
- Southwest Branch Library renamed to "Southwest Regional Library"
- Library URL pattern: `/locations/` corrected to `/location/`
- Added missing branches: Stanford L. Warren (1201 Fayetteville St) and Bragtown (3200 Dearborn Dr)
- Police districts link (broken 404) replaced with Durham Police Department main page
- Sheriff's Office link (broken 404) replaced with durhamsheriff.com/home
- Emergency Services link (broken path) replaced with dconc.gov/Emergency-Services
- Advisory boards link (broken 404) replaced with dconc.gov/clerk-to-the-board/boards-and-commissions
- Durham County Transit Plan URL (broken 404) replaced with engagedurham.com/DocumentCenter/View/559
- resources.json library URL pattern fixed: /locations/ to /location/

## QA Status
- Links: 110 checked, 7 true 404s fixed, 4 bot-blocking 403s noted (behave normally in browser)
- Voice: zero em dashes, zero "residents" (all changed to "neighbors")
- Emojis: all replaced with Lucide SVG icons sitewide
- Accessibility: skip links, focus-visible rings, ARIA roles on interactive elements
- PWA: manifest.json + service worker installed
- Open Graph: all 16 pages have og:title, og:description, og:image meta tags
- Data freshness: footer timestamp injection active on all data-driven pages

## Records Using Fallback Language
- County Manager FY2026-27 budget presentation: using "County Manager Claudia Hager presents" with verified source
- All other specific dates, dollar figures, and names have been verified against official sources

## Infrastructure Notes
- Git HTTPS push failing locally (no PAT/SSH configured). Commits are local only — push manually with `git push`
- Service worker installed at `/sw.js` — cache version `durhamcivichub-v2`
- GitHub Actions workflow: `.github/workflows/daily-fetch.yml` — requires `ANTHROPIC_API_KEY` secret
- update_civic_data.py bug fixed: doubled data/data/ path in MEETINGS_FILE corrected
- Elections fetch added to update_civic_data.py (Part 3.6)
