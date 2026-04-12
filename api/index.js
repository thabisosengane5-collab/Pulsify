
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
