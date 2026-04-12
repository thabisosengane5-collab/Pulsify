/**
 * PULSIFY — Vercel Serverless API
 * Routes: /api/events  /api/businesses  /api/ticket/purchase
 *         /api/booking/:ref  /api/paystack/webhook  /api/auth/profile
 */

const { createClient } = require('@supabase/supabase-js');
const crypto = require('crypto');

const SUPABASE_URL         = process.env.SUPABASE_URL         || "https://jjvjOAKYjkWCvzMxUcXkzA.supabase.co";
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY || "sb_secret_5ZOcK-0FtiyThxVy91mQGA_2uQXej23";
const PAYSTACK_SECRET_KEY  = process.env.PAYSTACK_SECRET_KEY  || "";

const CORS = {
  'Access-Control-Allow-Origin':  '*',
  'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type,Authorization,apikey',
};

function sb() {
  return createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false }
  });
}

async function getUser(req) {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) return null;
  try {
    const { data } = await sb().auth.getUser(token);
    return data?.user || null;
  } catch { return null; }
}

module.exports = async function handler(req, res) {
  if (req.method === 'OPTIONS') return res.status(200).setHeaders(CORS).end();
  Object.entries(CORS).forEach(([k,v]) => res.setHeader(k,v));

  const url  = req.url || '';
  const meth = req.method || 'GET';
  const q    = Object.fromEntries(new URL(url, 'http://localhost').searchParams);

  // ── GET /api/events ──────────────────────────────────────────────
  if (meth === 'GET' && url.startsWith('/api/events')) {
    const page     = parseInt(q.page  || '0');
    const limit    = parseInt(q.limit || '10');
    const city     = q.city    || null;
    const genre    = q.genre   || null;
    const province = q.province|| null;
    const isFree   = q.free === 'true';

    let query = sb().from('events').select('*').order('date_local', { ascending: true });
    if (city)     query = query.ilike('venue_city', `%${city}%`);
    if (genre)    query = query.ilike('genre', `%${genre}%`);
    if (province) query = query.eq('province', province);
    if (isFree)   query = query.eq('is_free', true);
    query = query.range(page * limit, (page + 1) * limit - 1);

    const { data, error } = await query;
    if (error) return res.status(500).json({ error: error.message });
    return res.status(200).json({ events: data || [], page, hasMore: (data||[]).length === limit });
  }

  // ── GET /api/businesses ──────────────────────────────────────────
  if (meth === 'GET' && url.startsWith('/api/businesses')) {
    const limit = parseInt(q.limit || '6');
    const cat   = q.category || null;
    let query = sb().from('businesses').select('*').eq('is_frontline', true).order('frontline_rank');
    if (cat) query = query.eq('category', cat);
    query = query.limit(limit);
    const { data, error } = await query;
    if (error) return res.status(500).json({ error: error.message });
    return res.status(200).json({ businesses: data || [] });
  }

  // ── POST /api/ticket/purchase ────────────────────────────────────
  if (meth === 'POST' && url.startsWith('/api/ticket/purchase')) {
    const user = await getUser(req);
    const body = req.body || {};
    const ref  = 'PKF-' + Date.now() + '-' + Math.random().toString(36).slice(2,7).toUpperCase();
    const { error } = await sb().from('bookings').insert({
      booking_ref:  ref,
      event_id:     body.event_id,
      user_id:      user?.id || null,
      buyer_name:   body.name,
      buyer_email:  body.email,
      tier_name:    body.tier_name,
      quantity:     body.quantity || 1,
      amount_zar:   body.amount_zar,
      status:       body.amount_zar === 0 ? 'confirmed' : 'pending',
      created_at:   new Date().toISOString(),
    });
    if (error) return res.status(500).json({ error: error.message });
    return res.status(200).json({ booking_ref: ref, status: 'created' });
  }

  // ── GET /api/booking/:ref ────────────────────────────────────────
  if (meth === 'GET' && url.startsWith('/api/booking/')) {
    const ref = url.split('/api/booking/')[1]?.split('?')[0];
    const { data, error } = await sb().from('bookings').select('*').eq('booking_ref', ref).single();
    if (error) return res.status(404).json({ error: 'Booking not found' });
    return res.status(200).json({ booking: data });
  }

  // ── POST /api/paystack/webhook ───────────────────────────────────
  if (meth === 'POST' && url.startsWith('/api/paystack/webhook')) {
    const sig  = req.headers['x-paystack-signature'];
    const body = JSON.stringify(req.body || {});
    const hash = crypto.createHmac('sha512', PAYSTACK_SECRET_KEY).update(body).digest('hex');
    if (sig !== hash) return res.status(401).json({ error: 'Invalid signature' });
    const evt = req.body?.event;
    if (evt === 'charge.success') {
      const ref = req.body?.data?.reference;
      if (ref) await sb().from('bookings').update({ status: 'confirmed' }).eq('booking_ref', ref);
    }
    return res.status(200).json({ received: true });
  }

  // ── POST /api/auth/profile ───────────────────────────────────────
  if (meth === 'POST' && url.startsWith('/api/auth/profile')) {
    const user = await getUser(req);
    if (!user) return res.status(401).json({ error: 'Not authenticated' });
    const { data: existing } = await sb().from('profiles').select('*').eq('id', user.id).single();
    if (!existing) {
      const body = req.body || {};
      await sb().from('profiles').insert({
        id:           user.id,
        display_name: body.display_name || user.email?.split('@')[0] || 'Viber',
        email:        user.email,
        created_at:   new Date().toISOString(),
      });
    }
    const { data: profile } = await sb().from('profiles').select('*').eq('id', user.id).single();
    return res.status(200).json({ profile });
  }

  return res.status(404).json({ error: 'Route not found', url });
};
