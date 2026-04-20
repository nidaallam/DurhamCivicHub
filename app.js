/* ============================================================
   Durham County Civic Hub — app.js
   ============================================================ */

// ── Mobile nav ─────────────────────────────────────────────
function toggleNav() {
  document.getElementById('mobileNav').classList.toggle('open');
}
document.addEventListener('click', function (e) {
  var nav    = document.getElementById('mobileNav');
  var toggle = document.querySelector('.nav-toggle');
  if (nav && nav.classList.contains('open') && !nav.contains(e.target) && e.target !== toggle) {
    nav.classList.remove('open');
  }
});

// ── Active nav on scroll ───────────────────────────────────
var navLinks     = document.querySelectorAll('.main-nav a');
var scrollSects  = document.querySelectorAll('section[id]');
function updateActiveNav() {
  var current = '';
  scrollSects.forEach(function (s) {
    if (window.scrollY >= s.offsetTop - 82) current = s.id;
  });
  navLinks.forEach(function (a) {
    a.classList.toggle('active', a.getAttribute('href') === '#' + current);
  });
}
window.addEventListener('scroll', updateActiveNav, { passive: true });

// ── Smooth scroll ──────────────────────────────────────────
document.querySelectorAll('a[href^="#"]').forEach(function (a) {
  a.addEventListener('click', function (e) {
    var target = document.querySelector(this.getAttribute('href'));
    if (!target) return;
    e.preventDefault();
    window.scrollTo({ top: target.getBoundingClientRect().top + window.scrollY - 72, behavior: 'smooth' });
    var mn = document.getElementById('mobileNav');
    if (mn) mn.classList.remove('open');
  });
});

// ── Story state ────────────────────────────────────────────
var activeTag    = 'all';
var searchTerm   = '';
var allStories   = [];   // populated by loadNews()

// ── Load news.json ─────────────────────────────────────────
function loadNews() {
  var grid    = document.getElementById('storiesGrid');
  var updated = document.getElementById('newsUpdated');
  if (!grid) return;

  // Show skeleton loading cards
  grid.innerHTML = [1,2,3,4,5,6].map(function() {
    return '<div class="story-card skeleton"><div class="skel-line skel-tag"></div>' +
           '<div class="skel-line skel-title"></div><div class="skel-line skel-title short"></div>' +
           '<div class="skel-line skel-body"></div><div class="skel-line skel-body"></div>' +
           '<div class="skel-line skel-body short"></div></div>';
  }).join('');

  fetch('news.json?t=' + Date.now())
    .then(function (r) {
      if (!r.ok) throw new Error('news.json not found');
      return r.json();
    })
    .then(function (data) {
      allStories = data.stories || [];

      // Show "last updated" timestamp
      if (updated && data.updated) {
        var d = new Date(data.updated);
        updated.textContent = 'Updated ' + d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
      }

      renderStories();
    })
    .catch(function () {
      // If fetch fails (e.g. opening file:// locally), fall back to static stories
      allStories = FALLBACK_STORIES;
      renderStories();
    });
}

// ── Render stories from allStories ────────────────────────
function renderStories() {
  var grid = document.getElementById('storiesGrid');
  var noResults = document.getElementById('noResults');
  if (!grid) return;

  var filtered = allStories.filter(function (s, i) {
    var tagMatch    = activeTag === 'all' || s.tag === activeTag;
    var searchMatch = !searchTerm ||
      s.title.toLowerCase().includes(searchTerm) ||
      s.excerpt.toLowerCase().includes(searchTerm) ||
      s.source.toLowerCase().includes(searchTerm);
    return tagMatch && searchMatch;
  });

  if (filtered.length === 0) {
    grid.innerHTML = '';
    if (noResults) {
      noResults.classList.remove('hidden');
      var term = document.getElementById('noResultsTerm');
      if (term) term.textContent = searchTerm || activeTag;
    }
    return;
  }
  if (noResults) noResults.classList.add('hidden');

  grid.innerHTML = filtered.map(function (s, i) {
    var isFeatured = i === 0 && activeTag === 'all' && !searchTerm;
    var tagLabel   = TAG_LABELS[s.tag] || s.tag;
    return [
      '<article class="story-card' + (isFeatured ? ' featured' : '') + '" data-tag="' + s.tag + '">',
        isFeatured ? '<span class="badge badge-featured">Featured</span>' : '',
        '<div class="story-meta">',
          '<span class="story-tag">' + tagLabel + '</span>',
          '<time datetime="' + s.date + '">' + s.displayDate + '</time>',
        '</div>',
        '<h3 class="story-title">',
          '<a href="' + escapeAttr(s.link) + '" target="_blank" rel="noopener">',
            escapeHtml(s.title),
          '</a>',
        '</h3>',
        s.excerpt ? '<p class="story-excerpt">' + escapeHtml(s.excerpt) + '</p>' : '',
        '<div class="story-footer">',
          '<span class="story-source">' + escapeHtml(s.source) + '</span>',
          '<a href="' + escapeAttr(s.link) + '" target="_blank" rel="noopener" class="story-read-more">Read more →</a>',
        '</div>',
      '</article>'
    ].join('');
  }).join('');
}

var TAG_LABELS = {
  'commissioners': 'Commissioners',
  'budget':        'Budget',
  'schools':       'Schools',
  'housing':       'Housing',
  'public-safety': 'Public Safety',
  'environment':   'Environment',
  'transit':       'Transit',
  'local':         'Local',
};

// ── Filter controls ────────────────────────────────────────
function filterStories(val) {
  searchTerm = val.toLowerCase().trim();
  renderStories();
}

function filterByTag(tag, btn) {
  activeTag = tag;
  document.querySelectorAll('.tag-btn').forEach(function (b) { b.classList.remove('active'); });
  if (btn) btn.classList.add('active');
  renderStories();
}

// ── HTML helpers ───────────────────────────────────────────
function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
function escapeAttr(s) {
  // Only allow http/https URLs
  var url = String(s).trim();
  if (!/^https?:\/\//i.test(url)) return '#';
  return url.replace(/"/g, '%22');
}

// ── Budget chart data (brand palette) ─────────────────────
var SPENDING = [
  { label: 'Education (DPS + DPAC)',        amount: 407, color: '#262E4F' },
  { label: 'Health & Human Services',       amount: 138, color: '#35567E' },
  { label: 'Public Safety',                amount:  87, color: '#207C91' },
  { label: 'Environment & Infrastructure',  amount:  52, color: '#6E9D97' },
  { label: 'General Government',            amount:  44, color: '#E18F1A' },
  { label: 'Debt Service',                  amount:  85, color: '#E97221' },
  { label: 'Capital Projects',              amount:  65, color: '#EBA85C' },
  { label: 'Other / Reserves',              amount:  90, color: '#DA421D' },
];

var REVENUE = [
  { label: 'Property Tax',   pct: 54, color: '#262E4F' },
  { label: 'State Funding',  pct: 22, color: '#207C91' },
  { label: 'Sales Tax',      pct: 10, color: '#E97221' },
  { label: 'Federal Funds',  pct:  7, color: '#E18F1A' },
  { label: 'Fees & Charges', pct:  4, color: '#6E9D97' },
  { label: 'Other Revenue',  pct:  3, color: '#EBA85C' },
];

function renderBudgetBars() {
  var el = document.getElementById('budgetBars');
  if (!el) return;
  var max = Math.max.apply(null, SPENDING.map(function(d){ return d.amount; }));
  el.innerHTML = SPENDING.map(function(d) {
    var pct = Math.round(d.amount / max * 100);
    return '<div class="budget-bar-row">' +
      '<div class="budget-bar-label"><span>' + d.label + '</span><span>$' + d.amount + 'M</span></div>' +
      '<div class="budget-bar-track"><div class="budget-bar-fill" style="width:' + pct + '%;background:' + d.color + '"></div></div>' +
      '</div>';
  }).join('');
}

function renderRevenue() {
  var el = document.getElementById('revenueGrid');
  if (!el) return;
  el.innerHTML = REVENUE.map(function(d) {
    return '<div class="revenue-item">' +
      '<div class="revenue-dot" style="background:' + d.color + '"></div>' +
      '<span class="revenue-name">' + d.label + '</span>' +
      '<span class="revenue-pct">' + d.pct + '%</span>' +
      '</div>';
  }).join('');
}

// ── Department table (budget page) ─────────────────────────
var DEPARTMENTS = [
  { name: 'Durham Public Schools',         fy24: 378.2, fy25: 407.4, pct: 41.2 },
  { name: 'Durham Co. Health & Human Svc', fy24: 127.6, fy25: 138.1, pct: 13.9 },
  { name: 'Sheriff & Public Safety',       fy24:  81.4, fy25:  87.3, pct:  8.8 },
  { name: 'Debt Service',                  fy24:  79.8, fy25:  84.9, pct:  8.6 },
  { name: 'Capital Projects',              fy24:  58.2, fy25:  65.0, pct:  6.6 },
  { name: 'General Government',            fy24:  40.9, fy25:  43.8, pct:  4.4 },
  { name: 'Environment & Open Space',      fy24:  47.3, fy25:  52.1, pct:  5.3 },
  { name: 'Community Development',         fy24:  38.6, fy25:  45.0, pct:  4.5 },
  { name: 'Durham Co. Library',            fy24:  14.8, fy25:  16.0, pct:  1.6 },
  { name: 'Animal Services',               fy24:   5.9, fy25:   6.4, pct:  0.6 },
  { name: 'Elections',                     fy24:   5.1, fy25:   5.7, pct:  0.6 },
  { name: 'Other / Reserves',              fy24:  18.2, fy25:  16.3, pct:  1.6 },
];

function renderDeptTable() {
  var tbody = document.getElementById('deptTableBody');
  if (!tbody) return;
  tbody.innerHTML = DEPARTMENTS.map(function(d) {
    var change    = d.fy25 - d.fy24;
    var changePct = ((change / d.fy24) * 100).toFixed(1);
    var changeHtml = change >= 0
      ? '<span class="change-up">▲ ' + changePct + '%</span>'
      : '<span class="change-neutral">▼ ' + Math.abs(changePct) + '%</span>';
    var barW = Math.round(d.pct / 45 * 100);
    return '<tr><td>' + d.name + '</td>' +
      '<td>$' + d.fy24.toFixed(1) + 'M</td>' +
      '<td>$' + d.fy25.toFixed(1) + 'M</td>' +
      '<td>' + changeHtml + '</td>' +
      '<td><div class="mini-bar-track"><div class="mini-bar-fill" style="width:' + barW + '%"></div></div></td></tr>';
  }).join('');
}

// ── Fallback stories (used if news.json can't be fetched) ──
var FALLBACK_STORIES = [
  {
    title: 'Durham County Commissioners Advance $968M FY2026 Budget',
    excerpt: 'The Board of Commissioners voted 4–1 to advance the proposed budget, which includes a 3.2-cent property tax increase and $45M for affordable housing.',
    link: 'https://www.heraldsun.com', source: 'Durham Herald-Sun',
    date: '2026-04-09', displayDate: 'April 9, 2026', tag: 'budget'
  },
  {
    title: 'DPS Requests $400M+ County Allocation in FY2027 Budget Ask',
    excerpt: 'Durham Public Schools is requesting the largest education budget ask in county history, prioritizing teacher pay and capital repairs.',
    link: 'https://www.wral.com', source: 'WRAL News',
    date: '2026-04-08', displayDate: 'April 8, 2026', tag: 'schools'
  },
  {
    title: 'County Affordable Housing Bond: Where Are We Two Years In?',
    excerpt: 'A status report on Durham County\'s $95M affordable housing bond shows 1,200 units funded, but advocates say the county must move faster.',
    link: 'https://indyweek.com', source: 'Indy Week',
    date: '2026-04-08', displayDate: 'April 8, 2026', tag: 'housing'
  },
  {
    title: 'Durham County Expands Crisis Intervention Team Countywide',
    excerpt: 'The co-responder mental health program will expand to all shifts in 2026 following a positive two-year pilot evaluation.',
    link: 'https://9thstreetjournal.org', source: '9th Street Journal',
    date: '2026-04-07', displayDate: 'April 7, 2026', tag: 'public-safety'
  },
  {
    title: 'Ellerbe Creek Restoration Gets $2M State Grant',
    excerpt: 'Durham County Stormwater Services will restore 1.4 miles of degraded habitat in northeast Durham.',
    link: 'https://www.wunc.org', source: 'WUNC (NPR)',
    date: '2026-04-07', displayDate: 'April 7, 2026', tag: 'environment'
  },
  {
    title: 'GoTriangle Proposes Durham-Chapel Hill BRT Expansion',
    excerpt: 'Regional transit planners presented an expanded bus rapid transit corridor projecting 18,000 daily riders by 2030.',
    link: 'https://indyweek.com', source: 'Indy Week',
    date: '2026-04-06', displayDate: 'April 6, 2026', tag: 'transit'
  },
];

// ── Init ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  loadNews();
  renderBudgetBars();
  renderRevenue();
  renderDeptTable();
});
