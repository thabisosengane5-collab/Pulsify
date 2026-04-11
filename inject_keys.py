import os, shutil, re
from datetime import datetime

SUPABASE_URL  = "https://jjvjOAKYjkWCvzMxUcXkzA.supabase.co"
SUPABASE_ANON = "sb_publishable_jjvjOAKYjkWCvzMxUcXkzA_GMJLbg93"
MAPBOX_TOKEN  = "pk.eyJ1IjoidGhhY29sbGluMiIsImEiOiJjbW51Mm95cHEwYm8xMnJyMXEzaXgxMDBmIn0.nF80wBOn-jxhjpAIus9anw"
PAYSTACK_KEY  = "pk_test_ef8796acebf766e5dde7cc185b5135551779d78a"

CONFIG = f"""
const SUPABASE_URL      = "{SUPABASE_URL}";
const SUPABASE_ANON_KEY = "{SUPABASE_ANON}";
const MAPBOX_TOKEN      = "{MAPBOX_TOKEN}";
const PAYSTACK_PK       = "{PAYSTACK_KEY}";
const EVENTS_PER_PAGE   = 10;
const BIZ_SWIPE_LIMIT   = 6;
if (typeof mapboxgl !== 'undefined') mapboxgl.accessToken = MAPBOX_TOKEN;
let _sb = null;
function getSB() {{
  if (!_sb && typeof supabase !== 'undefined')
    _sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  return _sb;
}}
"""

if not os.path.exists("index.html"):
    print("ERROR: index.html not found. Make sure you are in /workspaces/Pulsify")
    exit(1)

shutil.copy("index.html", f"index.html.bak.{datetime.now().strftime('%H%M%S')}")
print("Backup created")

with open("index.html", "r") as f:
    html = f.read()

swaps = {
    "https://YOUR_PROJECT.supabase.co": SUPABASE_URL,
    "YOUR_ANON_KEY": SUPABASE_ANON,
    "YOUR_ANON_PUBLIC_KEY": SUPABASE_ANON,
    "pk.YOUR_MAPBOX_PUBLIC_TOKEN": MAPBOX_TOKEN,
    "YOUR_MAPBOX_TOKEN": MAPBOX_TOKEN,
    "pk_test_YOUR_KEY": PAYSTACK_KEY,
    "mapbox-gl-js/v3.3.0/mapbox-gl.css": "mapbox-gl-js/v3.4.0/mapbox-gl.css",
    "mapbox-gl-js/v3.3.0/mapbox-gl.js":  "mapbox-gl-js/v3.4.0/mapbox-gl.js",
}
for old, new in swaps.items():
    if old in html:
        html = html.replace(old, new)
        print(f"Replaced: {old[:50]}")

if "SUPABASE_URL" not in html:
    pos = html.rfind("<script>")
    if pos != -1:
        insert = pos + len("<script>") + 1
        html = html[:insert] + CONFIG + html[insert:]
        print("Config block injected")

with open("index.html", "w") as f:
    f.write(html)

print("\nDone. index.html updated.")
print("Next: python create_api.py")
