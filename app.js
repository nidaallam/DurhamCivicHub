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
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;')
    .replace(/'/g,'&#39;');
}

// ── Mobile nav toggle ─────────────────────────────────────────
function toggleNav() {
  document.getElementById('mainNav')?.classList.toggle('open');
}

// ── Nav dropdowns ─────────────────────────────────────────────
function buildNavDropdowns() {
  const nav = document.getElementById('mainNav');
  if (!nav) return;

  const NAV_CONFIG = {
    'meetings.html': [
      { label: 'Meetings & Calendar',      url: 'meetings.html',                  header: true },
      { label: 'Board of Commissioners',   url: 'meetings.html#commissioners'   },
      { label: 'Durham City Council',      url: 'meetings.html#city-council'    },
      { label: 'DPS Board of Education',   url: 'meetings.html#dps'             },
      { label: 'Boards & Commissions',     url: 'meetings.html#advisory'        },
    ],
    'budget.html': [
      { label: 'Budget Hub',               url: 'budget.html',                    header: true },
      { label: 'Budget Explorer',          url: 'budget-explorer.html'          },
      { divider: true },
      { label: 'Durham County Budget',     url: 'budget-county.html'            },
      { label: 'City of Durham Budget',    url: 'budget-city.html'              },
      { label: 'DPS Budget',               url: 'budget-schools.html'           },
      { label: 'Capital Projects (CIP)',   url: 'cip.html'                      },
    ],
    'voting.html': [
      { label: 'Voting & Officials',       url: 'voting.html',                    header: true },
      { label: 'Register to Vote',         url: 'https://www.ncsbe.gov/registering/how-register', external: true },
      { label: 'Check Registration',       url: 'https://vt.ncsbe.gov/RegLkup/',  external: true },
      { label: 'Find Polling Place',       url: 'https://vt.ncsbe.gov/PPLkup/',   external: true },
    ],
  };

  nav.querySelectorAll('.nav-link').forEach(link => {
    const href  = link.getAttribute('href');
    const items = NAV_CONFIG[href];
    if (!items) return;

    // Wrap in nav-item
    const wrapper = document.createElement('div');
    wrapper.className = 'nav-item';
    link.parentNode.insertBefore(wrapper, link);
    wrapper.appendChild(link);

    // Chevron indicator
    const chevron    = document.createElement('span');
    chevron.className = 'nav-chevron';
    chevron.textContent = '▾';
    link.appendChild(chevron);

    // Build dropdown
    const dropdown = document.createElement('div');
    dropdown.className = 'nav-dropdown';
    dropdown.innerHTML = items.map(item => {
      if (item.divider) return '<div class="nav-dropdown-divider"></div>';
      const cls = item.header ? 'nav-dropdown-link nav-dropdown-link--header' : 'nav-dropdown-link';
      const ext = item.external ? ' target="_blank" rel="noopener"' : '';
      return `<a class="${cls}" href="${item.url}"${ext}>${item.label}</a>`;
    }).join('');
    wrapper.appendChild(dropdown);

    // Mobile: first click opens dropdown; second click navigates
    link.addEventListener('click', function(e) {
      if (window.innerWidth >= 640) return; // desktop uses CSS :hover
      if (!wrapper.classList.contains('open')) {
        e.preventDefault();
        nav.querySelectorAll('.nav-item.open').forEach(w => {
          if (w !== wrapper) w.classList.remove('open');
        });
        wrapper.classList.add('open');
      }
    });
  });

  // Close dropdowns when clicking outside
  document.addEventListener('click', function(e) {
    if (!nav.contains(e.target)) {
      nav.querySelectorAll('.nav-item.open').forEach(w => w.classList.remove('open'));
    }
  });
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
    { title: 'Home',                 url: 'index.html',           desc: 'Durham Civic Hub home page — navigator and what\'s happening now.' },
    { title: 'News & Updates',       url: 'news.html',            desc: 'Curated local government news from Durham County, the City, and DPS.' },
    { title: 'Meetings & Calendar',  url: 'meetings.html',        desc: 'BOCC, City Council, DPS Board, Planning Commission, agendas, and civic calendar.' },
    { title: 'Budgets',              url: 'budget.html',          desc: 'Durham County, City of Durham, and Durham Public Schools budgets.' },
    { title: 'Budget Explorer',      url: 'budget-explorer.html', desc: 'Interactive budget explorer — spending by area, funding sources, department breakdowns.' },
    { title: 'Durham County Budget', url: 'budget-county.html',   desc: 'County budget documents, dashboard, and FY2026-27 process.' },
    { title: 'City of Durham Budget','url': 'budget-city.html',   desc: 'City budget documents, Finance Department, and City Council.' },
    { title: 'DPS Budget',           url: 'budget-schools.html',  desc: 'Durham Public Schools budget, funding sources, and documents.' },
    { title: 'Voting & Elected Officials', url: 'voting.html',    desc: 'Register to vote, find your polling place, and learn about your representatives.' },
    { title: 'Connect',              url: 'connect.html',         desc: 'Contact and follow Commissioner Nida Allam — social media, events, town halls.' },
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
    <div class="meetings-group" id="advisory">
      <h2 class="meetings-group-title">Advisory Boards &amp; Commissions</h2>
      ${advisory.map(renderBodyCard).join('')}
    </div>
  `;

  // Hash-based scroll: handle #commissioners, #city-council, #dps, #advisory, etc.
  const hash = window.location.hash;
  if (hash) {
    setTimeout(() => {
      const el = document.getElementById(hash.slice(1));
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 120);
  }
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
let calendarData   = null;
let calView        = 'grid';  // 'grid' | 'list'
let calGridYear    = null;
let calGridMonth   = null;    // 0-indexed
let calActiveFilter = null;

const CAL_COLOR_MAP = {
  government:  '#207C91',
  budget:      '#E97221',
  hearing:     '#DA421E',
  schools:     '#3B82F6',
  community:   '#6E9D97',
  health:      '#D97706',
  announcement:'#EBA85C',
};

function calColor(category) {
  return CAL_COLOR_MAP[(category || '').toLowerCase()] || '#207C91';
}

async function loadCalendar() {
  const container = document.getElementById('calendarContainer');
  if (!container) return;
  try {
    const res  = await fetch('calendar.json');
    calendarData = await res.json();
    // Default to current month
    const now = new Date();
    calGridYear  = now.getFullYear();
    calGridMonth = now.getMonth();
    setCalView('grid');
  } catch {
    container.innerHTML = '<p style="color:var(--muted)">Could not load calendar data.</p>';
  }
}

function setCalView(mode) {
  calView = mode;
  document.getElementById('calViewGrid')?.classList.toggle('active', mode === 'grid');
  document.getElementById('calViewList')?.classList.toggle('active', mode === 'list');
  document.getElementById('calMonthNav').style.display = mode === 'grid' ? 'flex' : 'none';
  document.getElementById('calDayDetail').style.display = 'none';
  renderCalendar(calendarData, document.getElementById('calendarContainer'));
}

function calFilterCat(cat, btn) {
  calActiveFilter = cat;
  document.querySelectorAll('#calCatFilters .tag-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  closeDayDetail();
  renderCalendar(calendarData, document.getElementById('calendarContainer'));
}

function closeDayDetail() {
  document.getElementById('calDayDetail').style.display = 'none';
  document.querySelectorAll('.cal-grid-cell--selected').forEach(c => c.classList.remove('cal-grid-cell--selected'));
}

function renderCalendar(data, container) {
  if (!data || !data.events || !data.events.length) {
    container.innerHTML = '<p style="color:var(--muted)">No upcoming events.</p>';
    return;
  }
  if (calView === 'grid') {
    renderCalendarGrid(data, container);
  } else {
    renderCalendarList(data, container);
  }
}

// ── Grid view ─────────────────────────────────────────────────
function renderCalendarGrid(data, container) {
  const events = data.events;
  const year   = calGridYear;
  const month  = calGridMonth;

  // Update month label + wire nav buttons
  const label = new Date(year, month, 1).toLocaleDateString('en-US', {month:'long', year:'numeric'});
  const el = document.getElementById('calMonthLabel');
  if (el) el.textContent = label;

  document.getElementById('calPrevBtn').onclick = () => {
    calGridMonth--;
    if (calGridMonth < 0) { calGridMonth = 11; calGridYear--; }
    renderCalendarGrid(data, container);
    closeDayDetail();
  };
  document.getElementById('calNextBtn').onclick = () => {
    calGridMonth++;
    if (calGridMonth > 11) { calGridMonth = 0; calGridYear++; }
    renderCalendarGrid(data, container);
    closeDayDetail();
  };
  document.getElementById('calTodayBtn').onclick = () => {
    const now = new Date();
    calGridYear  = now.getFullYear();
    calGridMonth = now.getMonth();
    renderCalendarGrid(data, container);
    closeDayDetail();
  };

  // Filter events by active category, then index by date
  const filteredEvents = calActiveFilter
    ? events.filter(ev => (ev.category || '').toLowerCase() === calActiveFilter)
    : events;
  const byDate = {};
  filteredEvents.forEach(ev => {
    (byDate[ev.date] = byDate[ev.date] || []).push(ev);
  });

  // First day of month (0=Sun) and number of days
  const firstDay  = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const today     = new Date();
  const todayStr  = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`;

  // Build grid cells: pad before and after
  const DAY_NAMES = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  let cells = '';

  // Header row
  cells += DAY_NAMES.map(d => `<div class="cal-grid-header">${d}</div>`).join('');

  // Pre-month days from previous month
  const prevMonthDays = new Date(year, month, 0).getDate();
  for (let i = firstDay - 1; i >= 0; i--) {
    cells += `<div class="cal-grid-cell cal-grid-cell--other-month" data-count="0">
      <span class="cal-grid-day-num">${prevMonthDays - i}</span>
    </div>`;
  }

  // Days in current month
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${String(month+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
    const dayEvents = byDate[dateStr] || [];
    const isToday = dateStr === todayStr;
    const chips   = dayEvents.slice(0, 3).map(ev =>
      `<span class="cal-chip" style="background:${calColor(ev.category)}" title="${esc(ev.title)}">${esc(ev.title)}</span>`
    ).join('');
    const more = dayEvents.length > 3
      ? `<span class="cal-chip cal-chip--more">+${dayEvents.length - 3} more</span>`
      : '';
    cells += `
      <div class="cal-grid-cell${isToday ? ' cal-grid-cell--today' : ''}"
           data-date="${dateStr}" data-count="${dayEvents.length}"
           onclick="showDayDetail('${dateStr}', this)">
        <span class="cal-grid-day-num">${d}</span>
        ${chips}${more}
      </div>`;
  }

  // Post-month filler
  const cellsUsed = firstDay + daysInMonth;
  const remainder = 7 - (cellsUsed % 7);
  if (remainder < 7) {
    for (let d = 1; d <= remainder; d++) {
      cells += `<div class="cal-grid-cell cal-grid-cell--other-month" data-count="0">
        <span class="cal-grid-day-num">${d}</span>
      </div>`;
    }
  }

  container.innerHTML = `<div class="cal-grid-wrap"><div class="cal-grid">${cells}</div></div>`;
}

function showDayDetail(dateStr, cell) {
  const allDay  = (calendarData?.events || []).filter(ev => ev.date === dateStr);
  const events  = calActiveFilter
    ? allDay.filter(ev => (ev.category || '').toLowerCase() === calActiveFilter)
    : allDay;
  const detail = document.getElementById('calDayDetail');
  const body   = document.getElementById('calDayDetailBody');
  const title  = document.getElementById('calDayDetailTitle');

  // Deselect previous
  document.querySelectorAll('.cal-grid-cell--selected').forEach(c => c.classList.remove('cal-grid-cell--selected'));
  cell.classList.add('cal-grid-cell--selected');

  const [y, m, d] = dateStr.split('-').map(Number);
  const label = new Date(y, m-1, d).toLocaleDateString('en-US', {weekday:'long', month:'long', day:'numeric', year:'numeric'});
  title.textContent = label;

  if (!events.length) {
    body.innerHTML = '<p style="font-size:.875rem;color:#6b7280;padding:.25rem 0">No events this day.</p>';
  } else {
    body.innerHTML = events.map(ev => {
      const color = calColor(ev.category);
      const links = (ev.links || []).map(l =>
        `<a class="cal-detail-link" href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)}</a>`
      ).join('');
      return `
        <div class="cal-detail-event">
          <div class="cal-detail-dot" style="background:${color}"></div>
          <div class="cal-detail-info">
            <div class="cal-detail-name">${esc(ev.title)}</div>
            <div class="cal-detail-meta">
              ${ev.time ? `🕐 ${esc(ev.time)}` : ''}
              ${ev.location ? ` · 📍 ${esc(ev.location)}` : ''}
            </div>
            ${links ? `<div class="cal-detail-links">${links}</div>` : ''}
          </div>
        </div>`;
    }).join('');
  }

  detail.style.display = 'block';
  detail.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── List view ─────────────────────────────────────────────────
function renderCalendarList(data, container) {
  const events = calActiveFilter
    ? data.events.filter(ev => (ev.category || '').toLowerCase() === calActiveFilter)
    : data.events;

  if (!events.length) {
    container.innerHTML = '<p style="color:var(--muted)">No events match this filter.</p>';
    return;
  }

  // Group by month
  const byMonth = {};
  events.forEach(ev => {
    const [y, m] = ev.date.split('-');
    const key    = `${y}-${m}`;
    (byMonth[key] = byMonth[key] || []).push(ev);
  });

  container.innerHTML = Object.entries(byMonth).sort().map(([key, evs]) => {
    const [y, m] = key.split('-').map(Number);
    const monthLabel = new Date(y, m-1, 1).toLocaleDateString('en-US',{month:'long',year:'numeric'});
    return `
      <div class="cal-month">
        <div class="cal-month-label">${esc(monthLabel)}</div>
        ${evs.map(ev => {
          const d     = new Date(ev.date + 'T00:00:00');
          const color = calColor(ev.category);
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
                ${ev.time     ? `<div class="cal-event-time">🕐 ${esc(ev.time)}</div>` : ''}
                ${ev.location ? `<div class="cal-event-loc">📍 ${esc(ev.location)}</div>` : ''}
                ${rel         ? `<div class="cal-event-rel">${esc(rel)}</div>` : ''}
                ${links}
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }).join('');
}

// ── Language Selector ─────────────────────────────────────────
function injectLanguageSelector() {
  const nav = document.getElementById('mainNav');
  if (!nav) return;

  const LANGUAGES = [
    { code: 'es',    label: 'Español' },
    { code: 'ar',    label: 'العربية' },
    { code: 'vi',    label: 'Tiếng Việt' },
    { code: 'zh-CN', label: '中文 (简体)' },
    { code: 'fr',    label: 'Français' },
    { code: 'pt',    label: 'Português' },
    { code: 'hi',    label: 'हिन्दी' },
    { code: 'tl',    label: 'Tagalog' },
    { code: 'ko',    label: '한국어' },
    { code: 'am',    label: 'አማርኛ' },
  ];

  const wrapper = document.createElement('div');
  wrapper.className = 'nav-lang-wrap';

  const btn = document.createElement('button');
  btn.className = 'nav-lang-btn';
  btn.setAttribute('aria-haspopup', 'true');
  btn.setAttribute('aria-expanded', 'false');
  btn.setAttribute('aria-label', 'Translate this page');
  btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg> Language`;

  const dropdown = document.createElement('div');
  dropdown.className = 'nav-lang-dropdown';
  dropdown.setAttribute('role', 'menu');
  dropdown.innerHTML = LANGUAGES.map(l =>
    `<a class="nav-lang-option" href="#" data-lang="${l.code}" role="menuitem">${l.label}</a>`
  ).join('');

  wrapper.appendChild(btn);
  wrapper.appendChild(dropdown);
  nav.appendChild(wrapper);

  btn.addEventListener('click', e => {
    e.stopPropagation();
    const open = wrapper.classList.toggle('open');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  dropdown.querySelectorAll('.nav-lang-option').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      const lang = a.dataset.lang;
      const url  = encodeURIComponent(window.location.href);
      window.open(`https://translate.google.com/translate?sl=en&tl=${lang}&u=${url}`, '_blank', 'noopener');
      wrapper.classList.remove('open');
      btn.setAttribute('aria-expanded', 'false');
    });
  });

  document.addEventListener('click', () => {
    wrapper.classList.remove('open');
    btn.setAttribute('aria-expanded', 'false');
  });
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Inject search UI, nav dropdowns, and language selector on every page
  injectSearchUI();
  buildNavDropdowns();
  injectLanguageSelector();

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
    case 'news':
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
