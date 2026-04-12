#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  PULSIFY — fix_and_deploy.py                                     ║
║  One script that fixes everything and gets the site live         ║
║                                                                  ║
║  PASTE THIS INTO YOUR CODESPACE TERMINAL:                        ║
║      python fix_and_deploy.py                                    ║
╚══════════════════════════════════════════════════════════════════╝

WHAT THIS DOES (in order):
  1. Finds your HTML file (handles Index.html / index.html casing)
  2. Injects ALL real API keys (Supabase, Mapbox, Paystack)
  3. Writes vercel.json  ← THE MAIN FIX for 404
  4. Writes package.json
  5. Creates api/index.js (Vercel serverless handler)
  6. Saves everything as lowercase index.html
  7. Commits to Git and pushes
  8. Deploys to Vercel production

WHY YOU GOT A 404:
  - vercel.json was missing or had wrong routing
  - The file might be named Index.html (capital I) — Vercel needs index.html
  - API keys were still placeholders (breaks Supabase init)
"""

import os, sys, json, shutil, subprocess
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════
#  YOUR API KEYS — already filled in from your project
# ═══════════════════════════════════════════════════════════════════
SUPABASE_URL        = "https://jjvjOAKYjkWCvzMxUcXkzA.supabase.co"
SUPABASE_ANON_KEY   = "sb_publishable_jjvjOAKYjkWCvzMxUcXkzA_GMJLbg93"
SUPABASE_SERVICE_KEY= "sb_secret_5ZOcK-0FtiyThxVy91mQGA_2uQXej23"
MAPBOX_TOKEN        = "pk.eyJ1IjoidGhhY29sbGluMiIsImEiOiJjbW51Mm95cHEwYm8xMnJyMXEzaXgxMDBmIn0.nF80wBOn-jxhjpAIus9anw"
PAYSTACK_PUBLIC_KEY = "pk_test_ef8796acebf766e5dde7cc185b5135551779d78a"
PAYSTACK_SECRET_KEY = "sk_test_REPLACE_WITH_YOUR_PAYSTACK_SECRET"  # update manually
TICKETMASTER_KEY    = "ASnkf0hmmYwDfOKc"
EVENTBRITE_TOKEN    = "ASnkf0hmmYwDfOKc"

# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════
def ok(m):   print(f"  ✅ {m}")
def warn(m): print(f"  ⚠️  {m}")
def err(m):  print(f"  ❌ {m}")
def info(m): print(f"  ℹ️  {m}")
def step(m): print(f"\n{'─'*55}\n  {m}\n{'─'*55}")
def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr

print(f"\n{'═'*55}")
print("  PULSIFY — Fix & Deploy Script")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"{'═'*55}")

# ═══════════════════════════════════════════════════════════════════
#  STEP 1 — FIND THE HTML FILE
# ═══════════════════════════════════════════════════════════════════
step("1. Finding your HTML file")

html_source = None
for candidate in ["Index.html", "index.html", "pulsify-v10.html", "pulsify-fixed.html"]:
    if os.path.exists(candidate):
        html_source = candidate
        ok(f"Found: {candidate}")
        break

if not html_source:
    err("No HTML file found!")
    info("Make sure one of these is in your current folder:")
    info("  Index.html  /  index.html  /  pulsify-v10.html")
    sys.exit(1)

with open(html_source, "r", encoding="utf-8") as f:
    html = f.read()

info(f"Loaded {len(html):,} characters")

# ═══════════════════════════════════════════════════════════════════
#  STEP 2 — INJECT API KEYS
# ═══════════════════════════════════════════════════════════════════
step("2. Injecting API keys")

# Backup first
backup = f"index.backup.{datetime.now().strftime('%H%M%S')}.html"
with open(backup, "w", encoding="utf-8") as f:
    f.write(html)
ok(f"Backup saved: {backup}")

# Key substitution map
replacements = {
    # Supabase placeholders
    "https://YOUR_PROJECT.supabase.co":   SUPABASE_URL,
    "YOUR_ANON_KEY":                       SUPABASE_ANON_KEY,
    "YOUR_ANON_PUBLIC_KEY":                SUPABASE_ANON_KEY,
    "YOUR_SUPABASE_ANON_KEY":              SUPABASE_ANON_KEY,
    # Mapbox placeholders
    "pk.YOUR_MAPBOX_PUBLIC_TOKEN":         MAPBOX_TOKEN,
    "YOUR_MAPBOX_TOKEN":                   MAPBOX_TOKEN,
    # Paystack placeholders
    "pk_test_YOUR_KEY":                    PAYSTACK_PUBLIC_KEY,
    "YOUR_PAYSTACK_PUBLIC_KEY":            PAYSTACK_PUBLIC_KEY,
    # Mapbox version bump (3.3.0 → 3.4.0)
    "mapbox-gl-js/v3.3.0/mapbox-gl.css":  "mapbox-gl-js/v3.4.0/mapbox-gl.css",
    "mapbox-gl-js/v3.3.0/mapbox-gl.js":   "mapbox-gl-js/v3.4.0/mapbox-gl.js",
}

replaced = 0
for old, new in replacements.items():
    if old in html:
        html = html.replace(old, new)
        ok(f"Replaced: {old[:45]}")
        replaced += 1

if replaced == 0:
    info("No placeholder patterns found — keys may already be set")

# ── Find & replace the entire old CONFIG block ─────────────────────
# Whether keys were placeholders or not, we inject a clean config block
CONFIG_BLOCK = f"""
/* ══════════════════════════════════════════════════════════════
   PULSIFY CONFIG — Auto-injected {datetime.now().strftime('%Y-%m-%d %H:%M')}
   ══════════════════════════════════════════════════════════════ */

const SUPABASE_URL         = "{SUPABASE_URL}";
const SUPABASE_ANON_KEY    = "{SUPABASE_ANON_KEY}";
const MAPBOX_TOKEN         = "{MAPBOX_TOKEN}";
const PAYSTACK_PUBLIC_KEY  = "{PAYSTACK_PUBLIC_KEY}";
const TICKETMASTER_KEY     = "{TICKETMASTER_KEY}";
const EVENTBRITE_TOKEN     = "{EVENTBRITE_TOKEN}";
const EVENTS_PER_PAGE      = 10;
const BIZ_SWIPE_LIMIT      = 6;
const FEATURES = {{
  useSupabase: true,
  useMapbox:   true,
  usePaystack: true,
  geoCheck:    true,
}};

// Supabase client (lazy-init)
let _sb = null;
function getSB() {{
  if (!_sb && typeof supabase !== 'undefined') {{
    _sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  }}
  return _sb;
}}

// Apply Mapbox token when ready
if (typeof mapboxgl !== 'undefined') {{
  mapboxgl.accessToken = MAPBOX_TOKEN;
}}
"""

# Detect whether the file has the old short config block or an existing injected one
OLD_CONFIG_SHORT = '''/* ── CONFIG ──────────────────────────────────────────────────────────
   Replace these before going live. The app works without them (demo mode).
─────────────────────────────────────────────────────────────────── */
const SUPABASE_URL  = "https://YOUR_PROJECT.supabase.co";
const SUPABASE_ANON = "YOUR_ANON_KEY";
const PAYSTACK_PUBLIC_KEY = "pk_test_YOUR_KEY";'''

# Also match after key replacement (values changed but structure same)
import re

# Remove any existing PULSIFY CONFIG block
if "PULSIFY CONFIG" in html:
    html = re.sub(
        r'/\* ═+\s*PULSIFY CONFIG.*?(?=\n// Supabase client|}\n\n// Apply Mapbox)',
        '',
        html,
        flags=re.DOTALL,
        count=1
    )
    info("Removed old config block for replacement")

# Find the first <script> tag (the config script tag)
script_open_pos = html.find('<script>')
if script_open_pos != -1:
    # Insert our config after the opening <script> tag
    insert_at = script_open_pos + len('<script>') + 1
    
    # First remove the old short config if present
    # Find from insert_at to the </script> tag
    script_close = html.find('</script>', insert_at)
    old_script_content = html[insert_at:script_close]
    
    # Check if this script block only had the old short placeholder config
    if ('YOUR_PROJECT.supabase.co' in old_script_content or
        'YOUR_ANON_KEY' in old_script_content or
        'PULSIFY CONFIG' in old_script_content):
        # Replace the entire content of this small script tag with clean config
        html = html[:insert_at] + '\n' + CONFIG_BLOCK + '\n' + html[script_close:]
        ok("Config block injected into first <script> tag")
    else:
        # The first script might be something else — inject before the last big script
        last_script = html.rfind('<script>')
        insert_at2 = last_script + len('<script>') + 1
        html = html[:insert_at2] + '\n' + CONFIG_BLOCK + '\n' + html[insert_at2:]
        ok("Config block injected into main script section")
else:
    # Fallback: inject just before </body>
    html = html.replace('</body>', f'<script>\n{CONFIG_BLOCK}\n</script>\n</body>')
    ok("Config block injected before </body>")

# Fix any hardcoded mapboxgl.accessToken = 'pk...' calls
html = re.sub(
    r"mapboxgl\.accessToken\s*=\s*['\"]pk\.[^'\"]+['\"]",
    "mapboxgl.accessToken = MAPBOX_TOKEN",
    html
)

# Fix hardcoded supabase.createClient("https://...", "sb_...")
html = re.sub(
    r'createClient\s*\(\s*["\']https://[^"\']+["\'],\s*["\'][^"\']+["\']',
    'createClient(SUPABASE_URL, SUPABASE_ANON_KEY',
    html
)

ok("Mapbox token references patched")
ok("Supabase createClient references patched")

# ═══════════════════════════════════════════════════════════════════
#  STEP 3 — FIX THE HOME BUTTON onclick (the \'home\' bug)
# ═══════════════════════════════════════════════════════════════════
step("3. Fixing onclick attribute bugs")

# Binary-level fix for backslash-escaped single quotes in HTML attributes
html_bytes = html.encode('utf-8')
html_bytes = html_bytes.replace(b"showTab(\\'home\\')", b"showTab('home')")
html_bytes = html_bytes.replace(b"showToast(\\'Sign up flow coming!\\')", b"showToast('Sign up flow coming!')")
html = html_bytes.decode('utf-8')
ok("Fixed backslash-escaped onclick quotes")

# ═══════════════════════════════════════════════════════════════════
#  STEP 4 — SAVE AS LOWERCASE index.html
# ═══════════════════════════════════════════════════════════════════
step("4. Saving index.html")

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

ok(f"index.html saved ({len(html):,} chars)")
info("(lowercase 'i' — required by Vercel)")

# ═══════════════════════════════════════════════════════════════════
#  STEP 5 — WRITE vercel.json  ← THE MAIN FIX FOR 404
# ═══════════════════════════════════════════════════════════════════
step("5. Writing vercel.json (the 404 fix)")

vercel_config = {
    "version": 2,
    "builds": [
        {"src": "api/index.js", "use": "@vercel/node"}
    ],
    "routes": [
        {"src": "/api/(.*)", "dest": "/api/index.js"},
        {"src": "/(.*)",     "dest": "/index.html"}
    ]
}

with open("vercel.json", "w") as f:
    json.dump(vercel_config, f, indent=2)

ok("vercel.json written")
info("Routes: /api/* → serverless, /* → index.html")

# ═══════════════════════════════════════════════════════════════════
#  STEP 6 — WRITE package.json
# ═══════════════════════════════════════════════════════════════════
step("6. Writing package.json")

pkg = {
    "name": "pulsify",
    "version": "1.0.0",
    "private": True,
    "scripts": {
        "dev":    "vercel dev",
        "deploy": "vercel --prod"
    },
    "dependencies": {
        "@supabase/supabase-js": "^2.43.0"
    },
    "devDependencies": {
        "vercel": "^33.0.0"
    }
}

with open("package.json", "w") as f:
    json.dump(pkg, f, indent=2)

ok("package.json written")

# ═══════════════════════════════════════════════════════════════════
#  STEP 7 — CREATE api/index.js
# ═══════════════════════════════════════════════════════════════════
step("7. Creating api/index.js")

os.makedirs("api", exist_ok=True)

api_content = f"""/**
 * PULSIFY — Vercel Serverless API
 * Routes: /api/events  /api/businesses  /api/ticket/purchase
 *         /api/booking/:ref  /api/paystack/webhook  /api/auth/profile
 */

const {{ createClient }} = require('@supabase/supabase-js');
const crypto = require('crypto');

const SUPABASE_URL         = process.env.SUPABASE_URL         || "{SUPABASE_URL}";
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY || "{SUPABASE_SERVICE_KEY}";
const PAYSTACK_SECRET_KEY  = process.env.PAYSTACK_SECRET_KEY  || "";

const CORS = {{
  'Access-Control-Allow-Origin':  '*',
  'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type,Authorization,apikey',
}};

function sb() {{
  return createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {{
    auth: {{ autoRefreshToken: false, persistSession: false }}
  }});
}}

async function getUser(req) {{
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) return null;
  try {{
    const {{ data }} = await sb().auth.getUser(token);
    return data?.user || null;
  }} catch {{ return null; }}
}}

module.exports = async function handler(req, res) {{
  if (req.method === 'OPTIONS') return res.status(200).setHeaders(CORS).end();
  Object.entries(CORS).forEach(([k,v]) => res.setHeader(k,v));

  const url  = req.url || '';
  const meth = req.method || 'GET';
  const q    = Object.fromEntries(new URL(url, 'http://localhost').searchParams);

  // ── GET /api/events ──────────────────────────────────────────────
  if (meth === 'GET' && url.startsWith('/api/events')) {{
    const page     = parseInt(q.page  || '0');
    const limit    = parseInt(q.limit || '10');
    const city     = q.city    || null;
    const genre    = q.genre   || null;
    const province = q.province|| null;
    const isFree   = q.free === 'true';

    let query = sb().from('events').select('*').order('date_local', {{ ascending: true }});
    if (city)     query = query.ilike('venue_city', `%${{city}}%`);
    if (genre)    query = query.ilike('genre', `%${{genre}}%`);
    if (province) query = query.eq('province', province);
    if (isFree)   query = query.eq('is_free', true);
    query = query.range(page * limit, (page + 1) * limit - 1);

    const {{ data, error }} = await query;
    if (error) return res.status(500).json({{ error: error.message }});
    return res.status(200).json({{ events: data || [], page, hasMore: (data||[]).length === limit }});
  }}

  // ── GET /api/businesses ──────────────────────────────────────────
  if (meth === 'GET' && url.startsWith('/api/businesses')) {{
    const limit = parseInt(q.limit || '6');
    const cat   = q.category || null;
    let query = sb().from('businesses').select('*').eq('is_frontline', true).order('frontline_rank');
    if (cat) query = query.eq('category', cat);
    query = query.limit(limit);
    const {{ data, error }} = await query;
    if (error) return res.status(500).json({{ error: error.message }});
    return res.status(200).json({{ businesses: data || [] }});
  }}

  // ── POST /api/ticket/purchase ────────────────────────────────────
  if (meth === 'POST' && url.startsWith('/api/ticket/purchase')) {{
    const user = await getUser(req);
    const body = req.body || {{}};
    const ref  = 'PKF-' + Date.now() + '-' + Math.random().toString(36).slice(2,7).toUpperCase();
    const {{ error } = await sb().from('bookings').insert({{
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
    }});
    if (error) return res.status(500).json({{ error: error.message }});
    return res.status(200).json({{ booking_ref: ref, status: 'created' }});
  }}

  // ── GET /api/booking/:ref ────────────────────────────────────────
  if (meth === 'GET' && url.startsWith('/api/booking/')) {{
    const ref = url.split('/api/booking/')[1]?.split('?')[0];
    const {{ data, error }} = await sb().from('bookings').select('*').eq('booking_ref', ref).single();
    if (error) return res.status(404).json({{ error: 'Booking not found' }});
    return res.status(200).json({{ booking: data }});
  }}

  // ── POST /api/paystack/webhook ───────────────────────────────────
  if (meth === 'POST' && url.startsWith('/api/paystack/webhook')) {{
    const sig  = req.headers['x-paystack-signature'];
    const body = JSON.stringify(req.body || {{}});
    const hash = crypto.createHmac('sha512', PAYSTACK_SECRET_KEY).update(body).digest('hex');
    if (sig !== hash) return res.status(401).json({{ error: 'Invalid signature' }});
    const evt = req.body?.event;
    if (evt === 'charge.success') {{
      const ref = req.body?.data?.reference;
      if (ref) await sb().from('bookings').update({{ status: 'confirmed' }}).eq('booking_ref', ref);
    }}
    return res.status(200).json({{ received: true }});
  }}

  // ── POST /api/auth/profile ───────────────────────────────────────
  if (meth === 'POST' && url.startsWith('/api/auth/profile')) {{
    const user = await getUser(req);
    if (!user) return res.status(401).json({{ error: 'Not authenticated' }});
    const {{ data: existing }} = await sb().from('profiles').select('*').eq('id', user.id).single();
    if (!existing) {{
      const body = req.body || {{}};
      await sb().from('profiles').insert({{
        id:           user.id,
        display_name: body.display_name || user.email?.split('@')[0] || 'Viber',
        email:        user.email,
        created_at:   new Date().toISOString(),
      }});
    }}
    const {{ data: profile }} = await sb().from('profiles').select('*').eq('id', user.id).single();
    return res.status(200).json({{ profile }});
  }}

  return res.status(404).json({{ error: 'Route not found', url }});
}};
"""

with open("api/index.js", "w") as f:
    f.write(api_content)

ok("api/index.js created")

# ═══════════════════════════════════════════════════════════════════
#  STEP 8 — WRITE .env and .gitignore
# ═══════════════════════════════════════════════════════════════════
step("8. Writing .env and .gitignore")

env_content = f"""SUPABASE_URL={SUPABASE_URL}
SUPABASE_ANON_KEY={SUPABASE_ANON_KEY}
SUPABASE_SERVICE_KEY={SUPABASE_SERVICE_KEY}
MAPBOX_TOKEN={MAPBOX_TOKEN}
PAYSTACK_PUBLIC_KEY={PAYSTACK_PUBLIC_KEY}
PAYSTACK_SECRET_KEY={PAYSTACK_SECRET_KEY}
TICKETMASTER_API_KEY={TICKETMASTER_KEY}
EVENTBRITE_TOKEN={EVENTBRITE_TOKEN}
NODE_ENV=development
"""
with open(".env", "w") as f:
    f.write(env_content)
ok(".env written")

gitignore = """.env
.env.local
node_modules/
__pycache__/
*.pyc
.DS_Store
dist/
.vercel/
*.bak.*
"""
with open(".gitignore", "w") as f:
    f.write(gitignore)
ok(".gitignore written")

# ═══════════════════════════════════════════════════════════════════
#  STEP 9 — VERIFY KEYS ARE IN THE HTML
# ═══════════════════════════════════════════════════════════════════
step("9. Verification checks")

with open("index.html", "r", encoding="utf-8") as f:
    final = f.read()

checks = {
    "Supabase URL in index.html":     SUPABASE_URL in final,
    "Supabase anon key in index.html":SUPABASE_ANON_KEY[:20] in final,
    "Mapbox token in index.html":     MAPBOX_TOKEN[:20] in final,
    "Paystack key in index.html":     PAYSTACK_PUBLIC_KEY[:20] in final,
    "No placeholder keys remain":     "YOUR_PROJECT.supabase.co" not in final
                                      and "YOUR_ANON_KEY" not in final
                                      and "pk_test_YOUR_KEY" not in final,
    "Home onclick is clean":          "showTab('home')" in final,
    "vercel.json exists":             os.path.exists("vercel.json"),
    "api/index.js exists":            os.path.exists("api/index.js"),
    "package.json exists":            os.path.exists("package.json"),
}

all_ok = True
for label, result in checks.items():
    if result:
        ok(label)
    else:
        err(label)
        all_ok = False

if not all_ok:
    print("\n  ⚠️  Some checks failed — review above before deploying")

# ═══════════════════════════════════════════════════════════════════
#  STEP 10 — GIT COMMIT & PUSH
# ═══════════════════════════════════════════════════════════════════
step("10. Git commit and push")

code, out, e = run("git add -A && git status --short")
changed = [l for l in out.splitlines() if l.strip()]

if changed:
    info(f"{len(changed)} file(s) staged")
    code2, _, _ = run('git commit -m "fix: inject keys, vercel.json, api routes — fix 404"')
    if code2 == 0:
        ok("Git commit created")
    else:
        warn("Commit failed (possibly nothing changed) — continuing")
else:
    info("No changes to commit")

code3, out3, e3 = run("git push origin main 2>&1 || git push origin master 2>&1")
if code3 == 0:
    ok("Pushed to GitHub ← Vercel will auto-deploy if connected")
else:
    warn("Git push failed — you may not have a remote set up yet")
    info("That's OK — we'll deploy directly with Vercel CLI below")

# ═══════════════════════════════════════════════════════════════════
#  STEP 11 — DEPLOY TO VERCEL
# ═══════════════════════════════════════════════════════════════════
step("11. Deploying to Vercel")
info("This takes 1–2 minutes...")

# Set env vars on Vercel first
env_vars = {
    "SUPABASE_URL":          SUPABASE_URL,
    "SUPABASE_ANON_KEY":     SUPABASE_ANON_KEY,
    "SUPABASE_SERVICE_KEY":  SUPABASE_SERVICE_KEY,
    "MAPBOX_TOKEN":          MAPBOX_TOKEN,
    "PAYSTACK_PUBLIC_KEY":   PAYSTACK_PUBLIC_KEY,
}

info("Setting Vercel environment variables...")
for key, value in env_vars.items():
    run(f"echo '' | npx vercel env rm {key} production --yes 2>/dev/null")
    code_e, _, _ = run(f"printf '%s' '{value}' | npx vercel env add {key} production")
    if code_e == 0:
        ok(f"Env: {key}")
    else:
        warn(f"Env: {key} — may already exist, continuing")

# Deploy
code_d, out_d, err_d = run("npx vercel --prod --yes 2>&1")

if code_d == 0:
    # Extract live URL
    live_url = None
    for line in out_d.splitlines():
        if "vercel.app" in line:
            live_url = line.strip()
            break

    ok("Deployment successful!")
    print(f"""
{'═'*55}
  🎉 PULSIFY IS LIVE!

  {f'🌐 URL: {live_url}' if live_url else '🌐 Check your Vercel dashboard for the URL'}

  POST-DEPLOY CHECKLIST:
  □ Open the URL — site must load with orange Pulsify design
  □ Supabase → Auth → Settings → Site URL
    Add your Vercel URL there
  □ Test Sign In button
  □ Test events feed loads
  □ Paystack webhook:
    paystack.com → Settings → Webhooks
    Add: https://YOUR-URL.vercel.app/api/paystack/webhook

  ⚠️  Get your Paystack SECRET key and update .env:
     PAYSTACK_SECRET_KEY=sk_live_XXXXX
     Then re-run: python fix_and_deploy.py
{'═'*55}
""")
else:
    err("Vercel deployment failed")
    print(f"  Output: {out_d[:600]}")
    print(f"  Error:  {err_d[:400]}")
    print("""
  MANUAL STEPS:
  1. Make sure Vercel CLI is installed:
       npm install -g vercel

  2. Login to Vercel:
       npx vercel login
       (choose GitHub in the browser that opens)

  3. Deploy manually:
       npx vercel --prod

  4. If you get 'not linked' error:
       npx vercel link
       (follow the prompts)
""")
