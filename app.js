/* ─────────────────────────────────────────────────────────────
   Durham Civic Hub — app.js
   Handles: news, meetings, calendar, site-wide search
   ───────────────────────────────────────────────────────────── */

'use strict';

// ── State ─────────────────────────────────────────────────────
let allStories   = [];
let activeTag    = null;
let searchQuery  = '';
let newsData     = null;
let meetingsData = null;

// ── Utility ───────────────────────────────────────────────────
function relDay(isoDate) {
  const d    = new Date(isoDate + 'T00:00:00');
  const now  = new Date();
  now.setHours(0,0,0,0);
  const diff = Math.round((d - now) / 86400000);
  if (diff === 0)  return 'Today';
  if (diff === 1)  return 'Tomorrow';
  if (diff === -1) return 'Yesterday';
  if (diff > 1 && diff <= 7)  return `In ${diff} days`;
  if (diff < 0 && diff >= -7) return `${Math.abs(diff)} days ago`;
  return '';
}

function fmt(isoDate) {
  const [y, m, d] = isoDate.split('-').map(Number);
  return new Date(y, m-1, d).toLocaleDateString('en-US',
    { month:'short', day:'numeric', year:'numeric' });
}

function fmtLong(isoDate) {
  const [y, m, d] = isoDate.split('-').map(Number);
  return new Date(y, m-1, d).toLocaleDateString('en-US',
    { weekday:'short', month:'short', day:'numeric' });
}

function esc(str) {
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Mobile nav toggle ─────────────────────────────────────────
function toggleNav() {
  document.getElementById('mainNav')?.classList.toggle('open');
}

// ── Search overlay ────────────────────────────────────────────
function openSearch() {
  document.getElementById('searchOverlay').classList.add('open');
  document.getElementById('siteSearchInput').focus();
}
function closeSearch() {
  document.getElementById('searchOverlay').classList.remove('open');
  document.getElementById('siteSearchInput').value = '';
  document.getElementById('siteSearchResults').innerHTML = '';
}

function runSiteSearch(q) {
  const results = document.getElementById('siteSearchResults');
  q = q.trim().toLowerCase();
  if (q.length < 2) { results.innerHTML = ''; return; }

  const hits = [];

  // Search pages (static)
  const pages = [
    { title: 'News & Updates',       url: 'index.html',           desc: 'Latest local government news from Durham County, the City, and DPS.' },
    { title: 'Meeting Schedules',    url: 'meetings.html',        desc: 'BOCC, City Council, DPS Board, Planning Commission, and more.' },
    { title: 'Civic Calendar',       url: 'calendar.html',        desc: 'Public hearings, board meetings, and community events.' },
    { title: 'Budgets',              url: 'budget.html',          desc: 'Durham County, City of Durham, and Durham Public Schools budgets.' },
    { title: 'Budget Explorer',      url: 'budget-explorer.html', desc: 'Interactive budget explorer — spending by area, YoY changes, line items for all three Durham entities.' },
    { title: 'Durham County Budget', url: 'budget-county.html',   desc: 'County budget documents, dashboard, and FY2026-27 process.' },
    { title: 'City of Durham Budget','url': 'budget-city.html',   desc: 'City budget documents, Finance Department, and City Council.' },
    { title: 'DPS Budget',           url: 'budget-schools.html',  desc: 'Durham Public Schools budget, funding sources, and documents.' },
    { title: 'Voting & Elected Officials', url: 'voting.html',    desc: 'Register to vote, find your polling place, and learn about your representatives.' },
  ];
  pages.forEach(p => {
    if (p.title.toLowerCase().includes(q) || p.desc.toLowerCase().includes(q)) {
      hits.push({ type: 'page', title: p.title, url: p.url, desc: p.desc });
    }
  });

  // Search news stories (if loaded)
  if (newsData?.stories) {
    newsData.stories.forEach(s => {
      const haystack = (s.title + ' ' + s.excerpt + ' ' + (s.tags||[]).join(' ')).toLowerCase();
      if (haystack.includes(q)) {
        hits.push({ type: 'news', title: s.title, url: s.link, desc: s.excerpt?.slice(0,120) + '…', date: s.date });
      }
    });
  }

  // Search meetings (if loaded)
  if (meetingsData?.bodies) {
    meetingsData.bodies.forEach(body => {
      if (body.name.toLowerCase().includes(q) || body.description?.toLowerCase().includes(q)) {
        hits.push({ type: 'meeting', title: body.name, url: 'meetings.html#' + body.id, desc: body.schedule });
      }
    });
  }

  if (!hits.length) {
    results.innerHTML = '<div class="search-no-results">No results found for "<strong>' + esc(q) + '</strong>"</div>';
    return;
  }

  results.innerHTML = hits.slice(0,12).map(h => `
    <a class="search-result-item" href="${esc(h.url)}" ${h.url.startsWith('http') ? 'target="_blank" rel="noopener"' : ''}>
      <span class="search-result-type">${esc(h.type)}</span>
      <span class="search-result-title">${esc(h.title)}</span>
      ${h.date ? `<span class="search-result-date">${esc(h.date)}</span>` : ''}
      ${h.desc ? `<span class="search-result-desc">${esc(h.desc)}</span>` : ''}
    </a>
  `).join('');
}

function injectSearchUI() {
  // Add search button to nav
  const nav = document.getElementById('mainNav');
  if (nav) {
    const btn = document.createElement('button');
    btn.className   = 'nav-search-btn';
    btn.setAttribute('aria-label', 'Search site');
    btn.innerHTML   = '🔍';
    btn.onclick     = openSearch;
    nav.appendChild(btn);
  }

  // Inject overlay into body
  const overlay = document.createElement('div');
  overlay.id        = 'searchOverlay';
  overlay.className = 'search-overlay';
  overlay.innerHTML = `
    <div class="search-modal">
      <div class="search-modal-header">
        <input id="siteSearchInput" class="search-modal-input"
               type="search" placeholder="Search news, meetings, budget, voting…"
               autocomplete="off" />
        <button class="search-modal-close" onclick="closeSearch()" aria-label="Close search">✕</button>
      </div>
      <div id="siteSearchResults" class="search-modal-results"></div>
    </div>
  `;
  document.body.appendChild(overlay);

  // Close on backdrop click
  overlay.addEventListener('click', e => { if (e.target === overlay) closeSearch(); });

  // Close on Escape
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeSearch();
  });

  // Live search
  document.getElementById('siteSearchInput').addEventListener('input', e => {
    runSiteSearch(e.target.value);
  });
}


// ── Entity badge helper ───────────────────────────────────────
function entityBadge(source) {
  const s = (source || '').toLowerCase();
  if (s.includes('durham county') || s.includes('dconc') || s.includes('commissioner'))
    return '<span class="entity-badge entity-badge--county">Durham County</span>';
  if (s.includes('city of durham') || s.includes('durhamnc') || s.includes('city council'))
    return '<span class="entity-badge entity-badge--city">City of Durham</span>';
  if (s.includes('durham public schools') || s.includes('dps') || s.includes('dpsnc'))
    return '<span class="entity-badge entity-badge--dps">Durham Public Schools</span>';
  if (s.includes('wral') || s.includes('indy week') || s.includes('abc11') || s.includes('newsline') || s.includes('observer') || s.includes('herald'))
    return '<span class="entity-badge entity-badge--press">Press</span>';
  return '';
}

// ── News ──────────────────────────────────────────────────────
async function loadNews() {
  const grid = document.getElementById('storiesGrid');
  const upd  = document.getElementById('newsUpdated');
  try {
    const res = await fetch('news.json');
    newsData  = await res.json();
    allStories = newsData.stories || [];
    if (upd && newsData.updated) {
      upd.textContent = `Updated ${fmt(newsData.updated)} · Local government news from Durham County sources`;
    }
    buildTagFilters();
    renderStories();
  } catch {
    // fallback HTML already in place
  }
}

function buildTagFilters() {
  const bar = document.getElementById('tagFilters');
  if (!bar) return;
  const tags = [...new Set(allStories.flatMap(s => s.tags || []))].sort();
  bar.innerHTML = `<button class="tag-btn active" onclick="filterByTag(null,this)">All</button>` +
    tags.map(t => `<button class="tag-btn" onclick="filterByTag('${t}',this)">${esc(t)}</button>`).join('');
}

function filterByTag(tag, btn) {
  activeTag = tag;
  document.querySelectorAll('#tagFilters .tag-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderStories();
}

function filterStories() {
  return allStories.filter(s => {
    const tagOk   = !activeTag || (s.tags||[]).includes(activeTag);
    const queryOk = !searchQuery ||
      (s.title + s.excerpt).toLowerCase().includes(searchQuery.toLowerCase());
    return tagOk && queryOk;
  });
}

function renderStories() {
  const grid = document.getElementById('storiesGrid');
  if (!grid) return;
  const stories = filterStories();
  if (!stories.length) {
    grid.innerHTML = '<p style="color:var(--muted);padding:2rem 0;">No stories match your filter.</p>';
    return;
  }
  grid.innerHTML = stories.map((s, i) => {
    const tag = (s.tags||[s.tag]).filter(Boolean).slice(0,1)
                  .map(t => `<span class="story-tag">${esc(t)}</span>`).join('');
    const img = s.image
      ? `<a href="${esc(s.link)}" target="_blank" rel="noopener" class="story-img-link">
           <img class="story-img" src="${esc(s.image)}" alt="" loading="lazy" />
         </a>`
      : '';
    return `
    <article class="story-card${i === 0 ? ' story-card--lead' : ''}${s.image ? ' story-card--has-img' : ''}">
      ${img}
      <div class="story-body">
        <div class="story-meta">
          ${tag}
          ${entityBadge(s.source)}
          <span class="story-source">${esc(s.source)}</span>
          <span class="story-date">${esc(s.displayDate || s.date)}</span>
        </div>
        <h3 class="story-title">
          <a href="${esc(s.link)}" target="_blank" rel="noopener">${esc(s.title)}</a>
        </h3>
        ${s.excerpt ? `<p class="story-excerpt">${esc(s.excerpt)}</p>` : ''}
        <a class="story-read-more" href="${esc(s.link)}" target="_blank" rel="noopener">Read more →</a>
      </div>
    </article>
  `;
  }).join('');
}

// ── Meetings ──────────────────────────────────────────────────
async function loadMeetings() {
  const container = document.getElementById('meetingsContainer');
  if (!container) return;
  try {
    const res    = await fetch('meetings.json');
    meetingsData = await res.json();
    renderMeetings(meetingsData, container);
  } catch {
    // fallback HTML already in place
  }
}


function entityBadgeForBody(body) {
  const id   = body.id || '';
  const name = (body.name || '').toLowerCase();
  // Elected boards
  if (id === 'commissioners')  return '<span class="entity-badge entity-badge--county">Durham County</span>';
  if (id === 'city-council')   return '<span class="entity-badge entity-badge--city">City of Durham</span>';
  if (id === 'dps')            return '<span class="entity-badge entity-badge--dps">Durham Public Schools</span>';
  // City boards
  const cityIds = ['board-of-adjustment','planning','bicycle-pedestrian','workers-rights',
    'civilian-police-review','racial-equity','environmental-affairs','historic-preservation',
    'cultural-advisory','open-space-trails','jccpc','workforce-development','human-relations',
    'housing-appeals','recreation-advisory','citizens-advisory','housing-authority'];
  if (cityIds.includes(id)) return '<span class="entity-badge entity-badge--city">City of Durham</span>';
  // Joint city-county
  const jointIds = ['homeless-services','cultural-advisory','environmental-affairs',
    'historic-preservation','jccpc','bicycle-pedestrian','open-space-trails'];
  if (jointIds.includes(id)) return '<span class="entity-badge entity-badge--joint">City &amp; County</span>';
  // County boards
  return '<span class="entity-badge entity-badge--county">Durham County</span>';
}

function renderBodyCard(body) {
  return `
    <section class="meetings-section" id="${esc(body.id)}">
      <div class="meeting-body-header">
        <div>
          <div class="meeting-body-name">${esc(body.name)}</div>
          <div class="meeting-body-entity">${entityBadgeForBody(body)}</div>
          <div class="meeting-body-desc">${esc(body.description || '')}</div>
        </div>
      </div>
      <div class="meeting-body-meta">
        <span>📅 ${esc(body.schedule)}</span>
        <span>📍 ${esc(body.location)}</span>
      </div>
      <div>
        ${(body.meetings || []).map(m => renderMeetingRow(m)).join('')}
      </div>
      <a class="archive-link" href="${esc(body.archiveUrl)}" target="_blank" rel="noopener">Agendas & Minutes →</a>
    </section>
  `;
}

function renderMeetings(data, container) {
  const elected  = data.bodies.filter(b => b.group === 'elected');
  const advisory = data.bodies.filter(b => b.group === 'advisory' || !b.group);

  // Build sticky jump bar
  const jumpBar = document.getElementById('jumpBar');
  if (jumpBar) {
    const allBodies = [...elected, ...advisory];
    jumpBar.innerHTML =
      `<span class="jump-label">Jump to:</span>` +
      allBodies.map(b =>
        `<a href="#${esc(b.id)}" class="jump-link">${esc(b.name)}</a>`
      ).join('');
  }

  container.innerHTML = `
    <div class="meetings-group">
      <h2 class="meetings-group-title">Elected Boards</h2>
      ${elected.map(renderBodyCard).join('')}
    </div>
    <div class="meetings-group">
      <h2 class="meetings-group-title">Advisory Boards &amp; Commissions</h2>
      ${advisory.map(renderBodyCard).join('')}
    </div>
  `;
}

function renderMeetingRow(m) {
  const rel   = relDay(m.date);
  const label = m.status === 'upcoming' ? 'meeting-status--upcoming'
              : m.status === 'cancelled' ? 'meeting-status--cancelled'
              : 'meeting-status--past';
  const links = (m.links || []).map(l =>
    `<a class="meeting-link${l.primary ? ' meeting-link--primary' : ''}"
        href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)}</a>`
  ).join('');
  return `
    <div class="meeting-row">
      <div class="meeting-date-display">
        ${rel ? `<span class="meeting-rel-day">${esc(rel)}</span>` : ''}
        <span class="meeting-row-date">${esc(fmt(m.date))}</span>
      </div>
      <div class="meeting-row-info">
        <div class="meeting-type">${esc(m.type)}</div>
        <span class="meeting-status ${label}">${esc(m.status)}</span>
      </div>
      <div class="meeting-row-links">${links}</div>
    </div>
  `;
}

// ── Calendar ──────────────────────────────────────────────────
async function loadCalendar() {
  const container = document.getElementById('calendarContainer');
  if (!container) return;
  try {
    const res  = await fetch('calendar.json');
    const data = await res.json();
    renderCalendar(data, container);
  } catch {
    // fallback HTML
  }
}

function renderCalendar(data, container) {
  if (!data.events || !data.events.length) {
    container.innerHTML = '<p style="color:var(--muted)">No upcoming events.</p>';
    return;
  }

  // Group by month
  const byMonth = {};
  data.events.forEach(ev => {
    const [y, m] = ev.date.split('-');
    const key    = `${y}-${m}`;
    (byMonth[key] = byMonth[key] || []).push(ev);
  });

  const COLOR_MAP = {
    government:  'var(--teal)',
    budget:      'var(--orange)',
    hearing:     'var(--rust)',
    schools:     'var(--blue)',
    community:   'var(--sage)',
    health:      'var(--gold)',
    announcement:'var(--peach)',
  };

  container.innerHTML = Object.entries(byMonth).sort().map(([key, evs]) => {
    const [y, m] = key.split('-').map(Number);
    const monthLabel = new Date(y, m-1, 1).toLocaleDateString('en-US',{month:'long',year:'numeric'});
    return `
      <div class="cal-month">
        <div class="cal-month-label">${esc(monthLabel)}</div>
        ${evs.map(ev => {
          const d     = new Date(ev.date + 'T00:00:00');
          const color = COLOR_MAP[ev.category?.toLowerCase()] || 'var(--teal)';
          const rel   = relDay(ev.date);
          const links = (ev.links || []).map(l =>
            `<a class="cal-event-link" href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)}</a>`
          ).join('');
          return `
            <div class="cal-event" style="--event-color:${color}">
              <div class="cal-event-date">
                <span class="cal-day-name">${d.toLocaleDateString('en-US',{weekday:'short'})}</span>
                <span class="cal-day-num">${d.getDate()}</span>
              </div>
              <div class="cal-event-body">
                ${ev.category ? `<div class="cal-event-cat">${esc(ev.category)}</div>` : ''}
                <div class="cal-event-title">${esc(ev.title)}</div>
                ${ev.time   ? `<div class="cal-event-time">🕐 ${esc(ev.time)}</div>` : ''}
                ${ev.location ? `<div class="cal-event-loc">📍 ${esc(ev.location)}</div>` : ''}
                ${rel ? `<div class="cal-event-rel">${esc(rel)}</div>` : ''}
                ${links}
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }).join('');
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Inject search UI on every page
  injectSearchUI();

  // News search wiring
  const ns = document.getElementById('newsSearch');
  if (ns) {
    ns.addEventListener('input', e => {
      searchQuery = e.target.value;
      renderStories();
    });
  }

  // Page-specific init
  const page = document.body.dataset.page;
  switch (page) {
    case 'home':
      loadNews();
      break;
    case 'meetings':
      loadMeetings();
      break;
    case 'calendar':
      loadCalendar();
      break;
  }
});
