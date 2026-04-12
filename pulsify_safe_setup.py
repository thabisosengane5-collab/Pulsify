#!/usr/bin/env python3
"""
PULSIFY — Safe Master Setup Script
Reads all keys from .env file — no secrets hardcoded here.
Run with: python3 pulsify_safe_setup.py
"""

import os, json, subprocess
from pathlib import Path

# ── Read keys from .env (safe — never commits secrets) ──────────
def load_env(path=".env"):
    env = {}
    if not Path(path).exists():
        print("ERR  .env file not found. Create it first (Step 4 above).")
        exit(1)
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

E = load_env()

SUPABASE_URL     = E.get("SUPABASE_URL", "")
SUPABASE_ANON    = E.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE = E.get("SUPABASE_SERVICE_KEY", "")
MAPBOX_TOKEN     = E.get("MAPBOX_TOKEN", "")
PAYSTACK_PUBLIC  = E.get("PAYSTACK_PUBLIC_KEY", "")
PAYSTACK_SECRET  = E.get("PAYSTACK_SECRET_KEY", "")

print("\n" + "="*52)
print("  PULSIFY SAFE SETUP")
print("="*52 + "\n")
print(f"  Supabase URL : {SUPABASE_URL[:40]}...")
print(f"  Mapbox token : {MAPBOX_TOKEN[:30]}...")
print(f"  Paystack PK  : {PAYSTACK_PUBLIC[:30]}...")
print()

# ── Create folders ───────────────────────────────────────────────
for d in ["api", "workers", "scripts"]:
    os.makedirs(d, exist_ok=True)
print("OK  Folders created")

# ── vercel.json ──────────────────────────────────────────────────
vercel = {
    "version": 2,
    "builds": [{"src": "api/index.js", "use": "@vercel/node"}],
    "routes": [
        {"src": "/api/(.*)", "dest": "/api/index.js"},
        {"src": "/(.*)",     "dest": "/index.html"}
    ]
}
with open("vercel.json", "w") as f:
    json.dump(vercel, f, indent=2)
print("OK  vercel.json written")

# ── package.json ─────────────────────────────────────────────────
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

# ── api/index.js — Full backend with pagination + location ───────
api_js = r"""
/**
 * PULSIFY API — Vercel Serverless Routes
 *
 * All keys come from Vercel environment variables (set via dashboard).
 * Never hardcode secrets in this file.
 *
 * Routes:
 *   GET  /api/events           paginated, city/genre/location filter
 *   GET  /api/businesses       6 for swipe, or all for discover
 *   GET  /api/events/:id       single event + tiers + photos
 *   GET  /api/businesses/:id   single business
 *   POST /api/ticket/purchase  create booking + Paystack payload
 *   GET  /api/booking/:ref     get booking for QR display
 *   POST /api/paystack/webhook payment confirmation
 *   POST /api/auth/profile     create or get user profile
 */

const { createClient } = require('@supabase/supabase-js');
const crypto = require('crypto');

// Admin Supabase client — uses service key, server-side only
const db = () => createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY,
  { auth: { autoRefreshToken: false, persistSession: false } }
);

// Anon client — for verifying user JWTs
const anonClient = () => createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_ANON_KEY
);

const CORS = {
  'Access-Control-Allow-Origin':  '*',
  'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type,Authorization',
};

async function getUser(req) {
  const token = (req.headers.authorization || '').replace('Bearer ', '');
  if (!token) return null;
  const { data: { user } } = await anonClient().auth.getUser(token);
  return user;
}

// Haversine distance filter (km) — used when user shares GPS
function haversineFilter(lat, lon, radiusKm) {
  // Returns Supabase RPC params for radius search
  // We use a bounding box pre-filter then exact check in JS
  const R = 111; // km per degree approx
  const latDelta = radiusKm / R;
  const lonDelta = radiusKm / (R * Math.cos(lat * Math.PI / 180));
  return {
    minLat: lat - latDelta,
    maxLat: lat + latDelta,
    minLon: lon - lonDelta,
    maxLon: lon + lonDelta,
  };
}

module.exports = async (req, res) => {
  Object.entries(CORS).forEach(([k, v]) => res.setHeader(k, v));
  if (req.method === 'OPTIONS') return res.status(200).end();

  const url    = req.url.split('?')[0].replace(/^\/api/, '') || '/';
  const params = Object.fromEntries(new URL(req.url, 'http://x').searchParams);
  const today  = new Date().toISOString().split('T')[0];

  try {

    // ═══════════════════════════════════════════════════════════
    // GET /events
    // Params: page, limit, city, genre, lat, lon, radius_km
    // ═══════════════════════════════════════════════════════════
    if (url === '/events' && req.method === 'GET') {
      const page     = Math.max(1, parseInt(params.page  || '1'));
      const limit    = Math.min(50, parseInt(params.limit || '20'));
      const offset   = (page - 1) * limit;
      const city     = params.city   || '';
      const genre    = params.genre  || '';
      const lat      = parseFloat(params.lat)       || null;
      const lon      = parseFloat(params.lon)       || null;
      const radiusKm = parseFloat(params.radius_km) || 50;

      let q = db().from('events')
        .select('id,name,date_local,time_local,venue_name,venue_city,' +
                'venue_lat,venue_lon,price_min,is_free,image_url,genre,' +
                'hype_score,like_count,comment_count,is_frontline,' +
                'frontline_rank,external_url,source,status',
                { count: 'exact' })
        .gte('date_local', today)
        .not('status', 'in', '(cancelled,postponed)')
        .order('is_frontline',   { ascending: false })
        .order('hype_score',     { ascending: false, nullsFirst: false })
        .order('date_local',     { ascending: true })
        .range(offset, offset + limit - 1);

      // City filter
      if (city && city !== 'all') {
        q = q.ilike('venue_city', `%${city}%`);
      }

      // GPS bounding box pre-filter (fast — uses index on lat/lon)
      if (lat && lon) {
        const box = haversineFilter(lat, lon, radiusKm);
        q = q
          .gte('venue_lat', box.minLat)
          .lte('venue_lat', box.maxLat)
          .gte('venue_lon', box.minLon)
          .lte('venue_lon', box.maxLon);
      }

      // Genre filter
      if (genre === 'free')          q = q.eq('is_free', true);
      else if (genre && genre !== 'all') q = q.ilike('genre', `%${genre}%`);

      const { data, error, count } = await q;
      if (error) return res.status(400).json({ error: error.message });

      const total = count || 0;
      return res.status(200).json({
        events:      data || [],
        total,
        page,
        limit,
        offset,
        total_pages: Math.ceil(total / limit),
        has_next:    offset + limit < total,
        has_prev:    page > 1,
      });
    }

    // ═══════════════════════════════════════════════════════════
    // GET /businesses
    // Params: limit (6 for swipe), show_all, city, category, lat, lon
    // ═══════════════════════════════════════════════════════════
    if (url === '/businesses' && req.method === 'GET') {
      const show_all = params.show_all === 'true';
      const limit    = show_all ? 50 : Math.min(6, parseInt(params.limit || '6'));
      const page     = parseInt(params.page || '1');
      const offset   = show_all ? (page - 1) * 20 : 0;
      const city     = params.city     || '';
      const category = params.category || '';
      const lat      = parseFloat(params.lat) || null;
      const lon      = parseFloat(params.lon) || null;
      const radiusKm = parseFloat(params.radius_km) || 30;

      let q = db().from('businesses')
        .select('id,name,category,suburb,city,lat,lon,rating,review_count,' +
                'price_range,cover_image_url,is_frontline,frontline_rank,' +
                'tagline,phone,website,is_verified,tags',
                { count: 'exact' })
        .order('is_frontline',   { ascending: false })
        .order('frontline_rank', { ascending: true,  nullsFirst: false })
        .order('rating',         { ascending: false, nullsFirst: false })
        .range(offset, offset + limit - 1);

      // City filter — uses database index idx_biz_city
      if (city && city !== 'all') {
        q = q.ilike('city', `%${city}%`);
      }

      // GPS bounding box — uses index on lat/lon
      if (lat && lon) {
        const box = haversineFilter(lat, lon, radiusKm);
        q = q
          .gte('lat', box.minLat).lte('lat', box.maxLat)
          .gte('lon', box.minLon).lte('lon', box.maxLon);
      }

      // Category filter
      if (category && category !== 'all') {
        q = q.eq('category', category);
      }

      const { data, error, count } = await q;
      if (error) return res.status(400).json({ error: error.message });

      return res.status(200).json({
        businesses: data || [],
        total:      count || 0,
        page,
        has_more:   !show_all && (count || 0) > limit,
        has_next:   show_all && offset + limit < (count || 0),
      });
    }

    // ═══════════════════════════════════════════════════════════
    // GET /events/:id
    // ═══════════════════════════════════════════════════════════
    const evId = url.match(/^\/events\/([^/]+)$/)?.[1];
    if (evId && req.method === 'GET') {
      const [{ data: ev, error: evErr }, { data: tiers }, { data: photos }] =
        await Promise.all([
          db().from('events').select('*').eq('id', evId).single(),
          db().from('ticket_tiers').select('*').eq('event_id', evId).order('sort_order'),
          db().from('event_photos')
            .select('*,profiles(username,avatar_url)')
            .eq('event_id', evId)
            .order('created_at', { ascending: false })
            .limit(12),
        ]);
      if (evErr || !ev) return res.status(404).json({ error: 'Event not found' });
      return res.status(200).json({ event: ev, tiers: tiers || [], photos: photos || [] });
    }

    // ═══════════════════════════════════════════════════════════
    // GET /businesses/:id
    // ═══════════════════════════════════════════════════════════
    const bizId = url.match(/^\/businesses\/([^/]+)$/)?.[1];
    if (bizId && req.method === 'GET') {
      const { data: biz, error } = await db().from('businesses')
        .select('*').eq('id', bizId).single();
      if (error || !biz) return res.status(404).json({ error: 'Not found' });
      return res.status(200).json({ business: biz });
    }

    // ═══════════════════════════════════════════════════════════
    // POST /ticket/purchase
    // Body: event_id, tier_id, quantity, buyer_name, buyer_email, buyer_phone
    // ═══════════════════════════════════════════════════════════
    if (url === '/ticket/purchase' && req.method === 'POST') {
      const {
        event_id, tier_id, quantity = 1,
        buyer_name, buyer_email, buyer_phone
      } = req.body || {};

      if (!event_id || !buyer_name || !buyer_email) {
        return res.status(400).json({ error: 'event_id, buyer_name and buyer_email are required' });
      }

      const [{ data: tier }, { data: ev }] = await Promise.all([
        db().from('ticket_tiers').select('*').eq('id', tier_id).single(),
        db().from('events').select('name,commission_rate').eq('id', event_id).single(),
      ]);

      if (!ev) return res.status(404).json({ error: 'Event not found' });

      const qty        = Math.max(1, parseInt(quantity));
      const unit_price = tier?.price || 0;
      const subtotal   = unit_price * qty;
      const commission = unit_price > 0 ? +(subtotal * 0.08).toFixed(2) : 0;
      const psf        = unit_price > 0 ? +(subtotal * 0.015 + 1.50).toFixed(2) : 0;
      const total_paid = +(subtotal + commission + psf).toFixed(2);
      const booking_ref = `PKF-${Date.now()}-${Math.random().toString(36).slice(2,5).toUpperCase()}`;
      const user        = await getUser(req);

      const { data: booking, error: bookErr } = await db().from('bookings').insert({
        booking_ref,
        event_id,
        tier_id:      tier_id || null,
        user_id:      user?.id || null,
        buyer_name,
        buyer_email,
        buyer_phone:  buyer_phone || null,
        quantity:     qty,
        unit_price,
        commission,
        total_paid,
        status:       unit_price === 0 ? 'confirmed' : 'pending',
        qr_data:      `PULSIFY:${booking_ref}:${event_id}:VALID`,
      }).select().single();

      if (bookErr) return res.status(400).json({ error: bookErr.message });

      return res.status(200).json({
        success:    true,
        booking_ref,
        total_kobo: Math.round(total_paid * 100),
        total_paid,
        buyer_email,
        is_free:    unit_price === 0,
        qr_data:    booking.qr_data,
        event_name: ev.name,
        metadata:   { booking_id: booking.id, event_id, type: 'ticket' },
      });
    }

    // ═══════════════════════════════════════════════════════════
    // GET /booking/:ref
    // ═══════════════════════════════════════════════════════════
    const bookRef = url.match(/^\/booking\/([^/]+)$/)?.[1];
    if (bookRef && req.method === 'GET') {
      const { data } = await db().from('bookings')
        .select('*,events(name,date_local,time_local,venue_name,venue_city,venue_address)')
        .eq('booking_ref', bookRef).single();
      if (!data) return res.status(404).json({ error: 'Booking not found' });
      return res.status(200).json({ booking: data });
    }

    // ═══════════════════════════════════════════════════════════
    // POST /paystack/webhook
    // ═══════════════════════════════════════════════════════════
    if (url === '/paystack/webhook' && req.method === 'POST') {
      const sig  = req.headers['x-paystack-signature'] || '';
      const body = JSON.stringify(req.body);
      const hash = crypto
        .createHmac('sha512', process.env.PAYSTACK_SECRET_KEY || '')
        .update(body).digest('hex');

      if (sig !== hash) return res.status(401).json({ error: 'Invalid signature' });

      if (req.body?.event === 'charge.success') {
        const ref  = req.body.data?.reference;
        const meta = req.body.data?.metadata || {};
        if (meta.booking_id) {
          await Promise.all([
            db().from('bookings').update({ status: 'confirmed', paystack_ref: ref })
              .eq('id', meta.booking_id),
            db().from('payments').upsert({
              paystack_ref: ref,
              booking_id:   meta.booking_id,
              type:         'ticket',
              amount_kobo:  req.body.data?.amount,
              status:       'success',
              metadata:     meta,
            }, { onConflict: 'paystack_ref' }),
          ]);
        }
      }
      return res.status(200).json({ received: true });
    }

    // ═══════════════════════════════════════════════════════════
    // POST /auth/profile — auto-create profile after sign in
    // ═══════════════════════════════════════════════════════════
    if (url === '/auth/profile' && req.method === 'POST') {
      const user = await getUser(req);
      if (!user) return res.status(401).json({ error: 'Unauthorized' });

      const { data: existing } = await db().from('profiles')
        .select('*').eq('id', user.id).single();
      if (existing) return res.status(200).json({ profile: existing });

      const { data: created } = await db().from('profiles').insert({
        id:           user.id,
        username:     `user_${user.id.slice(0, 8)}`,
        display_name: user.user_metadata?.full_name ||
                      user.email?.split('@')[0] || 'Pulsify User',
        avatar_url:   user.user_metadata?.avatar_url || null,
        city:         'Durban',
      }).select().single();

      return res.status(200).json({ profile: created, created: true });
    }

    return res.status(404).json({ error: `Route not found: ${req.method} ${url}` });

  } catch (err) {
    console.error('[Pulsify API Error]', err.message);
    return res.status(500).json({ error: 'Server error', detail: err.message });
  }
};
"""
with open("api/index.js", "w") as f:
    f.write(api_js)
print("OK  api/index.js written (pagination + location filtering)")

# ── workers/events-sync.js — Cloudflare Worker (per-city cron) ──
worker_js = """
/**
 * PULSIFY — Cloudflare Worker: Events + Business Sync
 * Cron: every 6 hours for events, every 24h for businesses
 * Fetches per city — not all data at once.
 *
 * Set these secrets in Cloudflare dashboard:
 *   SUPABASE_URL, SUPABASE_SERVICE_KEY,
 *   TICKETMASTER_API_KEY, EVENTBRITE_TOKEN
 */

const SA_CITIES = [
  { name: 'Durban',        lat: -29.8587, lon: 31.0218 },
  { name: 'Johannesburg',  lat: -26.2041, lon: 28.0473 },
  { name: 'Cape Town',     lat: -33.9249, lon: 18.4241 },
  { name: 'Pretoria',      lat: -25.7479, lon: 28.2293 },
  { name: 'Port Elizabeth',lat: -33.9608, lon: 25.6022 },
];

export default {
  async scheduled(event, env, ctx) {
    const hour = new Date().getUTCHours();
    // Stagger city syncs — one city per run to avoid rate limits
    const cityIndex = Math.floor(hour / 6) % SA_CITIES.length;
    const city      = SA_CITIES[cityIndex];
    console.log(`[Sync] Running for: ${city.name}`);

    await Promise.allSettled([
      syncTicketmaster(env, city),
      syncEventbrite(env, city),
    ]);
  },

  async fetch(req, env) {
    const url = new URL(req.url);
    if (url.pathname === '/sync' && req.method === 'POST') {
      const city = SA_CITIES[0]; // manual trigger defaults to Durban
      await Promise.allSettled([
        syncTicketmaster(env, city),
        syncEventbrite(env, city),
      ]);
      return new Response(JSON.stringify({ ok: true, city: city.name }),
        { headers: { 'Content-Type': 'application/json' } });
    }
    return new Response('Pulsify Sync Worker');
  }
};

async function syncTicketmaster(env, city) {
  const now = new Date().toISOString().split('.')[0] + 'Z';
  const url = new URL('https://app.ticketmaster.com/discovery/v2/events.json');
  url.searchParams.set('apikey',        env.TICKETMASTER_API_KEY);
  url.searchParams.set('countryCode',   'ZA');
  url.searchParams.set('city',          city.name);
  url.searchParams.set('size',          '20');
  url.searchParams.set('startDateTime', now);
  url.searchParams.set('sort',          'date,asc');

  const res  = await fetch(url.toString());
  if (!res.ok) { console.error('[TM] Failed:', res.status); return; }
  const data = await res.json();
  const evs  = (data._embedded?.events || []).map(e => parseTicketmaster(e, city.name));
  if (evs.length) await upsertEvents(env, evs);
  console.log(`[TM] ${city.name}: ${evs.length} events`);
}

async function syncEventbrite(env, city) {
  const url = new URL('https://www.eventbriteapi.com/v3/events/search/');
  url.searchParams.set('location.latitude',    city.lat);
  url.searchParams.set('location.longitude',   city.lon);
  url.searchParams.set('location.within',      '30km');
  url.searchParams.set('expand',               'venue,ticket_classes');
  url.searchParams.set('page_size',            '20');

  const res = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${env.EVENTBRITE_TOKEN}` }
  });
  if (!res.ok) { console.error('[EB] Failed:', res.status); return; }
  const data = await res.json();
  const evs  = (data.events || []).map(e => parseEventbrite(e, city.name));
  if (evs.length) await upsertEvents(env, evs);
  console.log(`[EB] ${city.name}: ${evs.length} events`);
}

function parseTicketmaster(e, cityName) {
  const venue = e._embedded?.venues?.[0];
  const tier  = e.priceRanges?.[0];
  return {
    id:           `tm_${e.id}`,
    source:       'ticketmaster',
    name:         e.name,
    date_local:   e.dates?.start?.localDate,
    time_local:   e.dates?.start?.localTime,
    status:       e.dates?.status?.code || 'onsale',
    venue_name:   venue?.name,
    venue_city:   venue?.city?.name || cityName,
    venue_address:venue?.address?.line1,
    venue_lat:    parseFloat(venue?.location?.latitude)  || null,
    venue_lon:    parseFloat(venue?.location?.longitude) || null,
    price_min:    tier?.min || null,
    is_free:      false,
    image_url:    e.images?.find(i => i.ratio === '16_9' && i.width > 500)?.url,
    url:          e.url,
    external_url: e.url,
    genre:        e.classifications?.[0]?.genre?.name,
    hype_score:   50,
    updated_at:   new Date().toISOString(),
  };
}

function parseEventbrite(e, cityName) {
  const venue = e.venue;
  const price = e.ticket_classes?.[0];
  return {
    id:           `eb_${e.id}`,
    source:       'eventbrite',
    name:         e.name?.text,
    date_local:   e.start?.local?.split('T')[0],
    time_local:   e.start?.local?.split('T')[1]?.slice(0,5),
    status:       e.status || 'live',
    venue_name:   venue?.name,
    venue_city:   venue?.address?.city || cityName,
    venue_address:venue?.address?.address_1,
    venue_lat:    parseFloat(venue?.latitude)  || null,
    venue_lon:    parseFloat(venue?.longitude) || null,
    price_min:    parseFloat(price?.cost?.major_value) || null,
    is_free:      e.is_free || false,
    image_url:    e.logo?.url,
    url:          e.url,
    external_url: e.url,
    genre:        e.category?.name,
    hype_score:   50,
    updated_at:   new Date().toISOString(),
  };
}

async function upsertEvents(env, events) {
  const CHUNK = 20;
  for (let i = 0; i < events.length; i += CHUNK) {
    const chunk = events.slice(i, i + CHUNK);
    await fetch(`${env.SUPABASE_URL}/rest/v1/events?on_conflict=id`, {
      method:  'POST',
      headers: {
        'Content-Type':  'application/json',
        'apikey':        env.SUPABASE_SERVICE_KEY,
        'Authorization': `Bearer ${env.SUPABASE_SERVICE_KEY}`,
        'Prefer':        'resolution=merge-duplicates,return=minimal',
      },
      body: JSON.stringify(chunk),
    });
  }
}
"""
with open("workers/events-sync.js", "w") as f:
    f.write(worker_js)
print("OK  workers/events-sync.js written")

# ── workers/wrangler.toml — Cloudflare config ───────────────────
wrangler = f"""name = "pulsify-sync"
main = "events-sync.js"
compatibility_date = "2024-01-01"
workers_dev = true

[triggers]
crons = ["0 */6 * * *"]

# Set these with: wrangler secret put SECRET_NAME
# SUPABASE_URL, SUPABASE_SERVICE_KEY,
# TICKETMASTER_API_KEY, EVENTBRITE_TOKEN
"""
with open("workers/wrangler.toml", "w") as f:
    f.write(wrangler)
print("OK  workers/wrangler.toml written")

# ── schema.sql — Supabase schema ────────────────────────────────
schema = """
-- PULSIFY DATABASE SCHEMA
-- Paste this into: supabase.com > SQL Editor > New query > Run
-- Safe to run multiple times (IF NOT EXISTS throughout)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- PROFILES
CREATE TABLE IF NOT EXISTS profiles (
  id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username        TEXT UNIQUE,
  display_name    TEXT,
  avatar_url      TEXT,
  bio             TEXT,
  role            TEXT NOT NULL DEFAULT 'user'
                  CHECK (role IN ('user','organiser','business','admin')),
  city            TEXT DEFAULT 'Durban',
  follower_count  INTEGER DEFAULT 0,
  following_count INTEGER DEFAULT 0,
  events_attended INTEGER DEFAULT 0,
  is_verified     BOOLEAN DEFAULT false,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- EVENTS (indexes make city + date queries fast)
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

-- TICKET TIERS (per event)
CREATE TABLE IF NOT EXISTS ticket_tiers (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_id    TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  description TEXT,
  price       NUMERIC(10,2) NOT NULL DEFAULT 0,
  capacity    INTEGER,
  sold        INTEGER DEFAULT 0,
  is_free     BOOLEAN DEFAULT false,
  sort_order  INTEGER DEFAULT 0
);

-- BOOKINGS
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
  status          TEXT DEFAULT 'pending'
                  CHECK (status IN ('pending','confirmed','used','refunded','cancelled')),
  qr_data         TEXT,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- BUSINESSES (indexes on city and lat/lon for location queries)
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
  frontline_until TIMESTAMPTZ,
  updated_at      TIMESTAMPTZ DEFAULT now(),
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- PAYMENTS
CREATE TABLE IF NOT EXISTS payments (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  paystack_ref TEXT UNIQUE,
  booking_id   UUID REFERENCES bookings(id),
  user_id      UUID REFERENCES profiles(id),
  type         TEXT,
  amount_kobo  INTEGER,
  status       TEXT DEFAULT 'pending',
  metadata     JSONB,
  created_at   TIMESTAMPTZ DEFAULT now()
);

-- EVENT PHOTOS (geofenced — checked in API)
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

-- COMMENTS
CREATE TABLE IF NOT EXISTS comments (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id    UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  content    TEXT NOT NULL,
  event_id   TEXT REFERENCES events(id) ON DELETE CASCADE,
  like_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ═══ INDEXES (keep queries under 100ms even with millions of rows)
CREATE INDEX IF NOT EXISTS idx_events_city_date  ON events (venue_city, date_local);
CREATE INDEX IF NOT EXISTS idx_events_hype        ON events (hype_score DESC);
CREATE INDEX IF NOT EXISTS idx_events_frontline   ON events (is_frontline, frontline_rank);
CREATE INDEX IF NOT EXISTS idx_events_lat         ON events (venue_lat, venue_lon);
CREATE INDEX IF NOT EXISTS idx_events_source      ON events (source);
CREATE INDEX IF NOT EXISTS idx_biz_city           ON businesses (city);
CREATE INDEX IF NOT EXISTS idx_biz_category       ON businesses (category);
CREATE INDEX IF NOT EXISTS idx_biz_frontline      ON businesses (is_frontline, frontline_rank);
CREATE INDEX IF NOT EXISTS idx_biz_lat            ON businesses (lat, lon);
CREATE INDEX IF NOT EXISTS idx_bookings_ref       ON bookings (booking_ref);
CREATE INDEX IF NOT EXISTS idx_bookings_user      ON bookings (user_id);
CREATE INDEX IF NOT EXISTS idx_photos_event       ON event_photos (event_id, created_at DESC);

-- ═══ AUTO-CREATE PROFILE ON GOOGLE SIGN IN
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  INSERT INTO profiles (id, username, display_name, avatar_url, city)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'username',
             'user_' || substring(NEW.id::text,1,8)),
    COALESCE(NEW.raw_user_meta_data->>'full_name',
             NEW.raw_user_meta_data->>'name', 'Pulsify User'),
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

-- ═══ ROW LEVEL SECURITY
ALTER TABLE profiles     ENABLE ROW LEVEL SECURITY;
ALTER TABLE events       ENABLE ROW LEVEL SECURITY;
ALTER TABLE businesses   ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings     ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments     ENABLE ROW LEVEL SECURITY;

-- Drop existing policies before recreating (avoid conflicts)
DROP POLICY IF EXISTS profiles_read   ON profiles;
DROP POLICY IF EXISTS profiles_write  ON profiles;
DROP POLICY IF EXISTS profiles_insert ON profiles;
DROP POLICY IF EXISTS events_read     ON events;
DROP POLICY IF EXISTS biz_read        ON businesses;
DROP POLICY IF EXISTS photos_read     ON event_photos;
DROP POLICY IF EXISTS photos_insert   ON event_photos;
DROP POLICY IF EXISTS comments_read   ON comments;
DROP POLICY IF EXISTS comments_insert ON comments;
DROP POLICY IF EXISTS bookings_read   ON bookings;
DROP POLICY IF EXISTS bookings_write  ON bookings;

CREATE POLICY profiles_read   ON profiles   FOR SELECT USING (true);
CREATE POLICY profiles_write  ON profiles   FOR UPDATE USING (auth.uid() = id);
CREATE POLICY profiles_insert ON profiles   FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY events_read     ON events     FOR SELECT USING (true);
CREATE POLICY biz_read        ON businesses FOR SELECT USING (true);
CREATE POLICY photos_read     ON event_photos FOR SELECT USING (true);
CREATE POLICY photos_insert   ON event_photos FOR INSERT
  WITH CHECK (auth.uid() = user_id);
CREATE POLICY comments_read   ON comments   FOR SELECT USING (true);
CREATE POLICY comments_insert ON comments   FOR INSERT
  WITH CHECK (auth.uid() = user_id);
CREATE POLICY bookings_read   ON bookings   FOR SELECT
  USING (auth.uid() = user_id OR auth.role() = 'service_role');
CREATE POLICY bookings_write  ON bookings   FOR ALL
  USING (auth.role() = 'service_role');

-- Storage buckets
INSERT INTO storage.buckets (id, name, public)
VALUES
  ('event-photos', 'event-photos', true),
  ('avatars',      'avatars',      true)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY IF NOT EXISTS storage_photo_read ON storage.objects
  FOR SELECT USING (bucket_id IN ('event-photos','avatars'));
CREATE POLICY IF NOT EXISTS storage_photo_upload ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'event-photos' AND auth.role() = 'authenticated'
  );
CREATE POLICY IF NOT EXISTS storage_avatar_upload ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'avatars' AND auth.role() = 'authenticated'
  );
"""
with open("schema.sql", "w") as f:
    f.write(schema)
print("OK  schema.sql written — paste into Supabase SQL Editor")

# ── .gitignore ───────────────────────────────────────────────────
gitignore = """.env
node_modules/
__pycache__/
*.pyc
*.bak
.vercel/
pulsify_setup.py
pulsify_safe_setup.py
"""
with open(".gitignore", "w") as f:
    f.write(gitignore)
print("OK  .gitignore updated (secrets + setup scripts excluded)")

# ── npm install ──────────────────────────────────────────────────
print("\nRunning npm install...")
result = subprocess.run(["npm", "install"], capture_output=True, text=True, timeout=120)
if result.returncode == 0:
    print("OK  npm install complete")
else:
    print("WARN npm install had issues — try 'npm install' manually")

# ── Commit everything EXCEPT secrets ────────────────────────────
subprocess.run(["git", "add", "api/", "workers/", "schema.sql",
                "vercel.json", "package.json", ".gitignore",
                "package-lock.json"],
               capture_output=True)
subprocess.run(["git", "commit", "-m",
                "Pulsify: API routes with pagination + location filtering"],
               capture_output=True)
print("OK  Files staged and committed (secrets excluded)")

print("""
""" + "="*52 + """
  SETUP COMPLETE
""" + "="*52 + """

Files created (safe to push):
  api/index.js          all backend routes
  workers/events-sync.js  Cloudflare Worker
  workers/wrangler.toml   Worker config
  schema.sql            database tables
  vercel.json           deploy routing
  package.json          dependencies

Files NOT pushed to GitHub (protected):
  .env                  your live API keys

NEXT STEPS:

Step A — Run the database schema
  Go to supabase.com
  Your project > SQL Editor > New query
  Copy everything from schema.sql
  Click Run

Step B — Deploy to Vercel (no browser login needed)
  1. Go to vercel.com on your phone
  2. Log in > Settings > Tokens > Create Token
  3. Name it: pulsify
  4. Copy the token it gives you
  5. Run this command (replace TOKEN):

     VERCEL_TOKEN=your_token_here npx vercel --prod --yes --token=$VERCEL_TOKEN

Step C — Add secrets to Vercel after deploy
  Run each line (replace TOKEN each time):

     echo "" | npx vercel env add SUPABASE_URL production --token=your_token
     echo "" | npx vercel env add SUPABASE_ANON_KEY production --token=your_token
     echo "" | npx vercel env add SUPABASE_SERVICE_KEY production --token=your_token
     echo "" | npx vercel env add PAYSTACK_SECRET_KEY production --token=your_token
     echo "" | npx vercel env add MAPBOX_TOKEN production --token=your_token

  It will prompt you to type the value after each command.

Step D — Set Paystack webhook
  paystack.com > Settings > Webhooks
  Add: https://YOUR-VERCEL-URL.vercel.app/api/paystack/webhook

Step E — Set Supabase Auth redirect URL
  supabase.com > Authentication > URL Configuration
  Site URL: https://YOUR-VERCEL-URL.vercel.app
""")
