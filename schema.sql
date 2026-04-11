
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
