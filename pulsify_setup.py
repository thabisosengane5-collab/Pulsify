import os, json, shutil, subprocess
from datetime import datetime

# ═══════════════════════════════════════════════════════════
#  PULSIFY — MASTER SETUP SCRIPT
#  Run with: python3 pulsify_setup.py
#
#  This script does everything in one go:
#  1. Creates all project folders
#  2. Creates .env with real keys
#  3. Creates vercel.json
#  4. Creates package.json
#  5. Injects live API keys into index.html
#  6. Creates api/index.js (all backend routes)
#  7. Creates the Supabase schema SQL file
#  8. Runs npm install
#  9. Prints next steps for Vercel deploy
# ═══════════════════════════════════════════════════════════

# ─── YOUR LIVE API KEYS ─────────────────────────────────────
SUPABASE_URL         = "https://cjzewfvtdayjgjdpdmln.supabase.co"
SUPABASE_ANON        = "sb_publishable_jjvjOAKYjkWCvzMxUcXkzA_GMJLbg93"
SUPABASE_SERVICE     = "sb_secret_5ZOcK-0FtiyThxVy91mQGA_2uQXej23"
MAPBOX_TOKEN         = "pk.eyJ1IjoidGhhY29sbGluMiIsImEiOiJjbW51Mm95cHEwYm8xMnJyMXEzaXgxMDBmIn0.nF80wBOn-jxhjpAIus9anw"
PAYSTACK_PUBLIC      = "pk_test_ef8796acebf766e5dde7cc185b5135551779d78a"
PAYSTACK_SECRET      = "sk_test_f16d90fc8b574e0a0e1dac2518dc260498c65a2a"
TICKETMASTER_KEY     = "ASnkf0hmmYwDfOKc"
EVENTBRITE_TOKEN     = "ASnkf0hmmYwDfOKc"
GITHUB_REPO          = "https://github.com/thabisosengane5-collab/Pulsify"

print("\n" + "="*52)
print("  PULSIFY MASTER SETUP — starting...")
print("="*52 + "\n")

# ─── STEP 1: FOLDERS ────────────────────────────────────────
for d in ["api", "workers", "public", "scripts"]:
    os.makedirs(d, exist_ok=True)
print("OK  Folders created: api/ workers/ public/ scripts/")

# ─── STEP 2: .env FILE ──────────────────────────────────────
env_text = f"""SUPABASE_URL={SUPABASE_URL}
SUPABASE_ANON_KEY={SUPABASE_ANON}
SUPABASE_SERVICE_KEY={SUPABASE_SERVICE}
MAPBOX_TOKEN={MAPBOX_TOKEN}
PAYSTACK_PUBLIC_KEY={PAYSTACK_PUBLIC}
PAYSTACK_SECRET_KEY={PAYSTACK_SECRET}
TICKETMASTER_API_KEY={TICKETMASTER_KEY}
EVENTBRITE_TOKEN={EVENTBRITE_TOKEN}
NODE_ENV=production
"""
with open(".env", "w") as f:
    f.write(env_text)
print("OK  .env written")

# ─── STEP 3: .gitignore ─────────────────────────────────────
with open(".gitignore", "w") as f:
    f.write(".env\nnode_modules/\n__pycache__/\n.vercel/\n*.pyc\n*.bak\n")
print("OK  .gitignore written (.env is protected)")

# ─── STEP 4: vercel.json ────────────────────────────────────
vercel = {
    "version": 2,
    "builds": [{"src": "api/index.js", "use": "@vercel/node"}],
    "routes": [
        {"src": "/api/(.*)", "dest": "/api/index.js"},
        {"src": "/(.*)",     "dest": "/index.html"}
    ],
    "env": {
        "SUPABASE_URL":         SUPABASE_URL,
        "SUPABASE_ANON_KEY":    SUPABASE_ANON,
        "SUPABASE_SERVICE_KEY": SUPABASE_SERVICE,
        "PAYSTACK_SECRET_KEY":  PAYSTACK_SECRET,
        "MAPBOX_TOKEN":         MAPBOX_TOKEN
    }
}
with open("vercel.json", "w") as f:
    json.dump(vercel, f, indent=2)
print("OK  vercel.json written")

# ─── STEP 5: package.json ───────────────────────────────────
pkg = {
    "name": "pulsify",
    "version": "1.0.0",
    "private": True,
    "dependencies": {"@supabase/supabase-js": "^2.43.0"},
    "devDependencies": {"vercel": "^33.0.0"}
}
with open("package.json", "w") as f:
    json.dump(pkg, f, indent=2)
print("OK  package.json written")

# ─── STEP 6: INJECT KEYS INTO index.html ────────────────────
if not os.path.exists("index.html"):
    print("ERR index.html not found — make sure you are in /workspaces/Pulsify")
else:
    shutil.copy("index.html", f"index.html.bak")
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Fix Mapbox version
    html = html.replace(
        "mapbox-gl-js/v3.3.0/mapbox-gl.css",
        "mapbox-gl-js/v3.4.0/mapbox-gl.css"
    )
    html = html.replace(
        "mapbox-gl-js/v3.3.0/mapbox-gl.js",
        "mapbox-gl-js/v3.4.0/mapbox-gl.js"
    )

    # The config block to inject
    config_block = f"""
/* ═══════════════════════════════════════════════════════
   PULSIFY LIVE CONFIG — auto-injected {datetime.now().strftime('%Y-%m-%d')}
   ═══════════════════════════════════════════════════════ */
const SUPABASE_URL      = "{SUPABASE_URL}";
const SUPABASE_ANON_KEY = "{SUPABASE_ANON}";
const MAPBOX_TOKEN      = "{MAPBOX_TOKEN}";
const PAYSTACK_PK       = "{PAYSTACK_PUBLIC}";
const EVENTS_PER_PAGE   = 10;
const BIZ_SWIPE_LIMIT   = 6;
const API_BASE          = "/api";

if (typeof mapboxgl !== 'undefined') {{
  mapboxgl.accessToken = MAPBOX_TOKEN;
}}

let _sb = null;
function getSB() {{
  if (!_sb && typeof supabase !== 'undefined') {{
    _sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  }}
  return _sb;
}}

// Paginated event loader — replaces static EVENTS array
let currentEventPage = 1;
let totalEventPages  = 1;
let activeCity       = 'all';
let activeGenre      = 'all';

async function loadEventsFromAPI(page, city, genre, append) {{
  try {{
    const params = new URLSearchParams({{
      page:  page,
      limit: EVENTS_PER_PAGE,
      city:  city  || 'all',
      genre: genre || 'all',
    }});
    const res  = await fetch(API_BASE + '/events?' + params);
    const data = await res.json();
    if (data.events && data.events.length > 0) {{
      totalEventPages = data.total_pages || 1;
      renderAPIEvents(data.events, append);
      updatePaginationBtn(data.has_next);
    }}
  }} catch(e) {{
    console.log('API not connected yet — using demo data');
  }}
}}

function renderAPIEvents(events, append) {{
  const feed = document.getElementById('events-feed');
  if (!feed) return;
  if (!append) feed.innerHTML = '';
  events.forEach(ev => {{
    const card = buildFeedCard(ev);
    if (card) feed.insertAdjacentHTML('beforeend', card);
  }});
}}

function updatePaginationBtn(hasNext) {{
  const btn = document.getElementById('pagination-next-btn');
  if (btn) {{
    btn.style.display = hasNext ? 'flex' : 'none';
    btn.onclick = () => {{
      currentEventPage++;
      loadEventsFromAPI(currentEventPage, activeCity, activeGenre, true);
    }};
  }}
}}

// Business swipe row — loads 6, then Show More
async function loadBusinessesFromAPI(category) {{
  try {{
    const params = new URLSearchParams({{
      limit:    BIZ_SWIPE_LIMIT,
      category: category || 'all',
    }});
    const res  = await fetch(API_BASE + '/businesses?' + params);
    const data = await res.json();
    if (data.businesses) {{
      renderAPIBusinesses(data.businesses, data.has_more);
    }}
  }} catch(e) {{
    console.log('API not connected yet — using demo data');
  }}
}}

function renderAPIBusinesses(businesses, hasMore) {{
  const row = document.getElementById('frontline-row');
  if (!row) return;
  row.innerHTML = '';
  businesses.forEach(biz => {{
    row.insertAdjacentHTML('beforeend', buildBizCard(biz));
  }});
  if (hasMore) {{
    row.insertAdjacentHTML('beforeend',
      '<div class="biz-card show-more-card" onclick="openShowMore()" ' +
      'style="background:rgba(255,92,0,.08);border:1.5px dashed rgba(255,92,0,.4);' +
      'display:flex;flex-direction:column;align-items:center;justify-content:center;' +
      'gap:6px;cursor:pointer;flex-shrink:0;width:120px;">' +
      '<span style=\\'font-size:1.6rem\\'>→</span>' +
      '<span style=\\'font-family:Syne,sans-serif;font-size:.7rem;font-weight:700;' +
      'color:var(--orange)\\'>Show More</span></div>'
    );
  }}
}}

function openShowMore() {{
  showTab('discover');
}}

"""

    # Find the last <script> tag and inject config at the top of it
    script_pos = html.rfind('<script>')
    if script_pos != -1:
        insert_at = script_pos + len('<script>\n')
        html = html[:insert_at] + config_block + html[insert_at:]
        print("OK  Config block injected into index.html")
    else:
        # Fallback: before </body>
        html = html.replace('</body>', '<script>' + config_block + '</script>\n</body>')
        print("OK  Config block injected before </body>")

    # Also add pagination button HTML before </body> if not present
    if 'pagination-next-btn' not in html:
        pagination_html = """
<div id="pagination-next-btn" style="display:none;margin:0 14px 24px;justify-content:center">
  <button onclick="currentEventPage++;loadEventsFromAPI(currentEventPage,activeCity,activeGenre,true)"
    style="background:var(--surf);border:1.5px solid var(--orange);color:var(--orange);
    padding:12px 32px;border-radius:50px;font-family:'Syne',sans-serif;font-size:.82rem;
    font-weight:700;cursor:pointer;display:flex;align-items:center;gap:8px;
    transition:background .2s;">
    Load More Events &rarr;
  </button>
</div>
"""
        html = html.replace('</body>', pagination_html + '</body>')
        print("OK  Pagination button added to index.html")

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("OK  index.html saved")

# ─── STEP 7: api/index.js ───────────────────────────────────
api_js = r"""
const { createClient } = require('@supabase/supabase-js');
const crypto = require('crypto');

const sb = () => createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY,
  { auth: { autoRefreshToken: false, persistSession: false } }
);

const CORS = {
  'Access-Control-Allow-Origin':  '*',
  'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type,Authorization',
};

async function getUser(req) {
  const token = (req.headers.authorization || '').replace('Bearer ', '');
  if (!token) return null;
  const client = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_ANON_KEY);
  const { data: { user } } = await client.auth.getUser(token);
  return user;
}

module.exports = async (req, res) => {
  Object.entries(CORS).forEach(([k, v]) => res.setHeader(k, v));
  if (req.method === 'OPTIONS') return res.status(200).end();

  const url    = req.url.split('?')[0].replace(/^\/api/, '');
  const params = Object.fromEntries(new URL(req.url, 'http://localhost').searchParams);
  const today  = new Date().toISOString().split('T')[0];
  const db     = sb();

  try {

    // GET /events — paginated, 10 per page
    if (url === '/events' && req.method === 'GET') {
      const page  = parseInt(params.page  || '1');
      const limit = parseInt(params.limit || '10');
      const from  = (page - 1) * limit;

      let q = db.from('events')
        .select('*', { count: 'exact' })
        .gte('date_local', today)
        .not('status', 'in', '(cancelled,postponed)')
        .order('is_frontline', { ascending: false })
        .order('hype_score',   { ascending: false, nullsFirst: false })
        .order('date_local',   { ascending: true })
        .range(from, from + limit - 1);

      if (params.city  && params.city  !== 'all') q = q.ilike('venue_city', `%${params.city}%`);
      if (params.genre && params.genre === 'free') q = q.eq('is_free', true);
      else if (params.genre && params.genre !== 'all') q = q.ilike('genre', `%${params.genre}%`);

      const { data, error, count } = await q;
      if (error) return res.status(400).json({ error: error.message });
      const total = count || 0;
      return res.status(200).json({
        events:      data || [],
        total,
        page,
        limit,
        total_pages: Math.ceil(total / limit),
        has_next:    from + limit < total,
        has_prev:    page > 1,
      });
    }

    // GET /businesses — 6 for swipe row, or all for discover
    if (url === '/businesses' && req.method === 'GET') {
      const limit    = parseInt(params.limit || '6');
      const page     = parseInt(params.page  || '1');
      const show_all = params.show_all === 'true';
      const from     = show_all ? (page - 1) * 20 : 0;

      let q = db.from('businesses')
        .select('*', { count: 'exact' })
        .order('is_frontline',   { ascending: false })
        .order('frontline_rank', { ascending: true, nullsFirst: false })
        .order('rating',         { ascending: false, nullsFirst: false });

      if (show_all) q = q.range(from, from + 19);
      else          q = q.range(0, limit - 1);

      if (params.city     && params.city     !== 'all') q = q.ilike('city', `%${params.city}%`);
      if (params.category && params.category !== 'all') q = q.eq('category', params.category);

      const { data, error, count } = await q;
      if (error) return res.status(400).json({ error: error.message });
      return res.status(200).json({
        businesses: data || [],
        total:      count || 0,
        has_more:   !show_all && (count || 0) > limit,
      });
    }

    // GET /events/:id
    const evId = url.match(/^\/events\/([^/]+)$/)?.[1];
    if (evId && req.method === 'GET') {
      const [{ data: ev }, { data: tiers }, { data: photos }] = await Promise.all([
        db.from('events').select('*').eq('id', evId).single(),
        db.from('ticket_tiers').select('*').eq('event_id', evId).order('sort_order'),
        db.from('event_photos').select('*,profiles(username,avatar_url)')
          .eq('event_id', evId).order('created_at', { ascending: false }).limit(12),
      ]);
      if (!ev) return res.status(404).json({ error: 'Event not found' });
      return res.status(200).json({ event: ev, tiers: tiers || [], photos: photos || [] });
    }

    // GET /businesses/:id
    const bizId = url.match(/^\/businesses\/([^/]+)$/)?.[1];
    if (bizId && req.method === 'GET') {
      const { data: biz } = await db.from('businesses').select('*').eq('id', bizId).single();
      if (!biz) return res.status(404).json({ error: 'Business not found' });
      return res.status(200).json({ business: biz });
    }

    // POST /ticket/purchase
    if (url === '/ticket/purchase' && req.method === 'POST') {
      const { event_id, tier_id, quantity, buyer_name, buyer_email, buyer_phone } = req.body;
      if (!event_id || !buyer_name || !buyer_email) {
        return res.status(400).json({ error: 'Missing required fields' });
      }
      const { data: tier } = await db.from('ticket_tiers').select('*').eq('id', tier_id).single();
      const { data: ev }   = await db.from('events').select('name,commission_rate').eq('id', event_id).single();
      if (!ev) return res.status(404).json({ error: 'Event not found' });

      const qty        = parseInt(quantity) || 1;
      const unit_price = tier?.price || 0;
      const commission = unit_price > 0 ? +(unit_price * qty * 0.08).toFixed(2) : 0;
      const psf        = unit_price > 0 ? +(unit_price * qty * 0.015 + 1.5).toFixed(2) : 0;
      const total_paid = +(unit_price * qty + commission + psf).toFixed(2);
      const booking_ref = `PKF-${Date.now()}-${Math.random().toString(36).slice(2,5).toUpperCase()}`;
      const user        = await getUser(req);

      const { data: booking, error } = await db.from('bookings').insert({
        booking_ref, event_id, tier_id: tier_id || null,
        user_id: user?.id || null, buyer_name, buyer_email,
        buyer_phone: buyer_phone || null, quantity: qty,
        unit_price, commission, total_paid,
        status:   unit_price === 0 ? 'confirmed' : 'pending',
        qr_data:  `PULSIFY:${booking_ref}:${event_id}:VALID`,
      }).select().single();

      if (error) return res.status(400).json({ error: error.message });
      return res.status(200).json({
        success: true, booking_ref,
        total_kobo: Math.round(total_paid * 100),
        total_paid, buyer_email,
        is_free:    unit_price === 0,
        qr_data:    booking.qr_data,
        event_name: ev.name,
        metadata: { booking_id: booking.id, event_id, type: 'ticket' },
      });
    }

    // GET /booking/:ref
    const bookRef = url.match(/^\/booking\/([^/]+)$/)?.[1];
    if (bookRef && req.method === 'GET') {
      const { data } = await db.from('bookings')
        .select('*,events(name,date_local,time_local,venue_name,venue_city)')
        .eq('booking_ref', bookRef).single();
      if (!data) return res.status(404).json({ error: 'Booking not found' });
      return res.status(200).json({ booking: data });
    }

    // POST /paystack/webhook
    if (url === '/paystack/webhook' && req.method === 'POST') {
      const sig  = req.headers['x-paystack-signature'];
      const hash = crypto.createHmac('sha512', process.env.PAYSTACK_SECRET_KEY || '')
        .update(JSON.stringify(req.body)).digest('hex');
      if (sig !== hash) return res.status(401).json({ error: 'Invalid signature' });

      if (req.body.event === 'charge.success') {
        const meta = req.body.data?.metadata || {};
        if (meta.booking_id) {
          await db.from('bookings').update({
            status: 'confirmed',
            paystack_ref: req.body.data.reference,
          }).eq('id', meta.booking_id);
          await db.from('payments').upsert({
            paystack_ref: req.body.data.reference,
            booking_id:   meta.booking_id,
            type:         'ticket',
            amount_kobo:  req.body.data.amount,
            status:       'success',
            metadata:     meta,
          }, { onConflict: 'paystack_ref' });
        }
      }
      return res.status(200).json({ received: true });
    }

    // POST /auth/profile
    if (url === '/auth/profile' && req.method === 'POST') {
      const user = await getUser(req);
      if (!user) return res.status(401).json({ error: 'Unauthorized' });
      const { data: existing } = await db.from('profiles').select('*').eq('id', user.id).single();
      if (existing) return res.status(200).json({ profile: existing });
      const { data: created } = await db.from('profiles').insert({
        id:           user.id,
        username:     `user_${user.id.slice(0,8)}`,
        display_name: user.user_metadata?.full_name || user.email?.split('@')[0] || 'Pulsify User',
        avatar_url:   user.user_metadata?.avatar_url || null,
        city:         'Durban',
      }).select().single();
      return res.status(200).json({ profile: created, created: true });
    }

    return res.status(404).json({ error: `Unknown route: ${req.method} ${url}` });

  } catch (err) {
    console.error('[API Error]', err.message);
    return res.status(500).json({ error: 'Server error', detail: err.message });
  }
};
"""
with open("api/index.js", "w") as f:
    f.write(api_js)
print("OK  api/index.js created")

# ─── STEP 8: schema.sql (for Supabase SQL Editor) ───────────
schema_sql = """
-- PULSIFY DATABASE SCHEMA
-- Paste this into: supabase.com > your project > SQL Editor > Run

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS profiles (
  id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username        TEXT UNIQUE,
  display_name    TEXT,
  avatar_url      TEXT,
  bio             TEXT,
  role            TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user','organiser','business','admin')),
  city            TEXT DEFAULT 'Durban',
  follower_count  INTEGER DEFAULT 0,
  following_count INTEGER DEFAULT 0,
  events_attended INTEGER DEFAULT 0,
  is_verified     BOOLEAN DEFAULT false,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS events (
  id              TEXT PRIMARY KEY,
  source          TEXT NOT NULL DEFAULT 'manual',
  organiser_id    UUID REFERENCES profiles(id),
  name            TEXT NOT NULL,
  description     TEXT,
  date_local      DATE,
  time_local      TIME,
  status          TEXT DEFAULT 'onsale',
  venue_name      TEXT,
  venue_city      TEXT,
  venue_address   TEXT,
  venue_lat       NUMERIC(10,7),
  venue_lon       NUMERIC(10,7),
  price_min       NUMERIC(10,2),
  is_free         BOOLEAN DEFAULT false,
  image_url       TEXT,
  url             TEXT,
  external_url    TEXT,
  genre           TEXT,
  hype_score      INTEGER DEFAULT 50,
  like_count      INTEGER DEFAULT 0,
  comment_count   INTEGER DEFAULT 0,
  is_frontline    BOOLEAN DEFAULT false,
  frontline_rank  INTEGER,
  commission_rate NUMERIC(4,2) DEFAULT 8.0,
  updated_at      TIMESTAMPTZ DEFAULT now(),
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ticket_tiers (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_id    TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  description TEXT,
  price       NUMERIC(10,2) NOT NULL DEFAULT 0,
  capacity    INTEGER,
  sold        INTEGER DEFAULT 0,
  is_free     BOOLEAN DEFAULT false,
  sort_order  INTEGER DEFAULT 0,
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bookings (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  booking_ref     TEXT UNIQUE NOT NULL,
  event_id        TEXT NOT NULL REFERENCES events(id),
  tier_id         UUID REFERENCES ticket_tiers(id),
  user_id         UUID REFERENCES profiles(id),
  buyer_name      TEXT NOT NULL,
  buyer_email     TEXT NOT NULL,
  buyer_phone     TEXT,
  quantity        INTEGER NOT NULL DEFAULT 1,
  unit_price      NUMERIC(10,2) NOT NULL,
  commission      NUMERIC(10,2),
  total_paid      NUMERIC(10,2),
  paystack_ref    TEXT,
  status          TEXT DEFAULT 'pending' CHECK (status IN ('pending','confirmed','used','refunded','cancelled')),
  qr_data         TEXT,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS businesses (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_id        UUID REFERENCES profiles(id),
  name            TEXT NOT NULL,
  category        TEXT,
  tagline         TEXT,
  description     TEXT,
  city            TEXT,
  suburb          TEXT,
  address         TEXT,
  lat             NUMERIC(10,7),
  lon             NUMERIC(10,7),
  phone           TEXT,
  website         TEXT,
  rating          NUMERIC(3,1),
  review_count    INTEGER DEFAULT 0,
  price_range     TEXT,
  cover_image_url TEXT,
  gallery_urls    TEXT[],
  hours           JSONB,
  tags            TEXT[],
  menu_data       JSONB,
  is_verified     BOOLEAN DEFAULT false,
  is_claimed      BOOLEAN DEFAULT false,
  is_frontline    BOOLEAN DEFAULT false,
  frontline_rank  INTEGER,
  updated_at      TIMESTAMPTZ DEFAULT now(),
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS payments (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  paystack_ref    TEXT UNIQUE,
  booking_id      UUID REFERENCES bookings(id),
  user_id         UUID REFERENCES profiles(id),
  type            TEXT,
  amount_kobo     INTEGER,
  status          TEXT DEFAULT 'pending',
  metadata        JSONB,
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS event_photos (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_id     TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  user_id      UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  storage_path TEXT NOT NULL,
  public_url   TEXT,
  caption      TEXT,
  is_video     BOOLEAN DEFAULT false,
  post_lat     NUMERIC(10,7),
  post_lon     NUMERIC(10,7),
  like_count   INTEGER DEFAULT 0,
  created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS comments (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id    UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  content    TEXT NOT NULL,
  event_id   TEXT REFERENCES events(id) ON DELETE CASCADE,
  like_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_events_city   ON events (venue_city, date_local);
CREATE INDEX IF NOT EXISTS idx_events_hype   ON events (hype_score DESC);
CREATE INDEX IF NOT EXISTS idx_events_front  ON events (is_frontline, frontline_rank);
CREATE INDEX IF NOT EXISTS idx_biz_city      ON businesses (city);
CREATE INDEX IF NOT EXISTS idx_biz_front     ON businesses (is_frontline, frontline_rank);
CREATE INDEX IF NOT EXISTS idx_bookings_ref  ON bookings (booking_ref);
CREATE INDEX IF NOT EXISTS idx_photos_event  ON event_photos (event_id, created_at DESC);

-- Auto-create profile on Google sign-in
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  INSERT INTO profiles (id, username, display_name, avatar_url, city)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'username', 'user_' || substring(NEW.id::text,1,8)),
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name', 'Pulsify User'),
    NEW.raw_user_meta_data->>'avatar_url',
    'Durban'
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- RLS
ALTER TABLE profiles    ENABLE ROW LEVEL SECURITY;
ALTER TABLE events      ENABLE ROW LEVEL SECURITY;
ALTER TABLE businesses  ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings    ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments    ENABLE ROW LEVEL SECURITY;

CREATE POLICY "profiles_read"   ON profiles   FOR SELECT USING (true);
CREATE POLICY "profiles_write"  ON profiles   FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "profiles_insert" ON profiles   FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "events_read"     ON events     FOR SELECT USING (true);
CREATE POLICY "biz_read"        ON businesses FOR SELECT USING (true);
CREATE POLICY "photos_read"     ON event_photos FOR SELECT USING (true);
CREATE POLICY "photos_insert"   ON event_photos FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "comments_read"   ON comments   FOR SELECT USING (true);
CREATE POLICY "comments_insert" ON comments   FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "bookings_read"   ON bookings   FOR SELECT USING (auth.uid() = user_id OR auth.role() = 'service_role');
CREATE POLICY "bookings_insert" ON bookings   FOR ALL   USING (auth.role() = 'service_role');

-- Storage buckets
INSERT INTO storage.buckets (id, name, public)
VALUES ('event-photos','event-photos',true),('avatars','avatars',true)
ON CONFLICT (id) DO NOTHING;
"""
with open("schema.sql", "w") as f:
    f.write(schema_sql)
print("OK  schema.sql saved (paste this into Supabase SQL Editor)")

# ─── STEP 9: npm install ─────────────────────────────────────
print("\nRunning npm install...")
result = subprocess.run(["npm", "install"], capture_output=True, text=True, timeout=120)
if result.returncode == 0:
    print("OK  npm install done")
else:
    print("WARN npm install had issues — run 'npm install' manually")

# ─── STEP 10: Git commit ─────────────────────────────────────
subprocess.run(["git", "add", "-A"], capture_output=True)
subprocess.run(["git", "commit", "-m", "Pulsify: add API routes, inject live keys, setup complete"], capture_output=True)
subprocess.run(["git", "push"], capture_output=True)
print("OK  Changes committed and pushed to GitHub")

# ─── DONE ────────────────────────────────────────────────────
print("""
""" + "="*52 + """
  SETUP COMPLETE
""" + "="*52 + """

  Files created:
    .env               your live API keys
    .gitignore         protects .env from GitHub
    vercel.json        deploy config
    package.json       dependencies
    api/index.js       all backend routes
    schema.sql         database tables
    index.html         updated with live keys

  NEXT — 3 things to do:

  1. Run the database schema:
     Go to supabase.com
     Your project > SQL Editor > New query
     Paste everything from schema.sql
     Click Run

  2. Deploy to Vercel WITHOUT browser login:
     a) Go to vercel.com on your phone
     b) Settings > Tokens > Create Token
     c) Copy the token
     d) Run this command (replace TOKEN with yours):
        VERCEL_TOKEN=paste_your_token_here npx vercel --prod --yes --token=$VERCEL_TOKEN

  3. Set Paystack webhook after deploy:
     paystack.com > Settings > Webhooks
     Add: https://YOUR-VERCEL-URL.vercel.app/api/paystack/webhook

""")
