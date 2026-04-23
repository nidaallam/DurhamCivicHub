# Durham Civic Hub — Status

## Current Phase
Part 3 (Automation) — daily fetch workflows

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

## Records Using Fallback Language
- County Manager FY2026-27 budget presentation: using "County Manager Claudia Hager presents" with verified source
- All other specific dates, dollar figures, and names have been verified against official sources

## Infrastructure Notes
- Git HTTPS push failing locally (no PAT/SSH configured). Commits are local only — push manually with `git push`
- Service worker installed at `/sw.js` — cache version `durhamcivichub-v2`
- GitHub Actions workflow: `.github/workflows/daily-fetch.yml` — requires `ANTHROPIC_API_KEY` secret
