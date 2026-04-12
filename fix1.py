import re, os

f = None
for name in ["index.html","Index.html","pulsify-v10.html"]:
    if os.path.exists(name):
        f = name
        break

if not f:
    print("ERROR: No HTML file found")
    exit(1)

print(f"Found: {f}")
with open(f, "r", encoding="utf-8") as fh:
    html = fh.read()

def fix_static_onclicks(html):
    def replacer(m):
        return m.group(0).replace("\\'", "'")
    return re.sub(r'onclick="[^"]*"', replacer, html)

html = fix_static_onclicks(html)
print("Fixed onclick quotes")

html = html.replace("html,body{height:100%;overflow:hidden}", "html{height:100%}body{height:100%;overflow:hidden}")
print("Fixed scroll block")

html = html.replace("panel.style.display=(name==='home')?'flex':'block';", "panel.style.display='block';")
print("Fixed showTab display")

html = html.replace('<div class="panel active" id="tab-home">', '<div class="panel active" id="tab-home" style="display:block">', 1)
print("Fixed home panel")

SUPABASE_URL      = "https://jjvjOAKYjkWCvzMxUcXkzA.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_jjvjOAKYjkWCvzMxUcXkzA_GMJLbg93"
MAPBOX_TOKEN      = "pk.eyJ1IjoidGhhY29sbGluMiIsImEiOiJjbW51Mm95cHEwYm8xMnJyMXEzaXgxMDBmIn0.nF80wBOn-jxhjpAIus9anw"
PAYSTACK_KEY      = "pk_test_ef8796acebf766e5dde7cc185b5135551779d78a"

replacements = {
    "https://YOUR_PROJECT.supabase.co": SUPABASE_URL,
    "YOUR_ANON_KEY": SUPABASE_ANON_KEY,
    "YOUR_ANON_PUBLIC_KEY": SUPABASE_ANON_KEY,
    "YOUR_SUPABASE_ANON_KEY": SUPABASE_ANON_KEY,
    "pk_test_YOUR_KEY": PAYSTACK_KEY,
    "YOUR_PAYSTACK_PUBLIC_KEY": PAYSTACK_KEY,
    "YOUR_MAPBOX_TOKEN": MAPBOX_TOKEN,
    "pk.YOUR_MAPBOX_PUBLIC_TOKEN": MAPBOX_TOKEN,
    "pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw": MAPBOX_TOKEN,
}

for old, new in replacements.items():
    if old in html:
        html = html.replace(old, new)
        print(f"Replaced key: {old[:40]}")

CONFIG = f"""
const SUPABASE_URL        = "{SUPABASE_URL}";
const SUPABASE_ANON_KEY   = "{SUPABASE_ANON_KEY}";
const MAPBOX_TOKEN        = "{MAPBOX_TOKEN}";
const PAYSTACK_PUBLIC_KEY = "{PAYSTACK_KEY}";
const MB_TOKEN            = "{MAPBOX_TOKEN}";
let _sb = null;
function getSB() {{
  if (!_sb && typeof supabase !== 'undefined') {{
    _sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  }}
  return _sb;
}}
if (typeof mapboxgl !== 'undefined') {{
  mapboxgl.accessToken = MAPBOX_TOKEN;
}}
"""

first_script = html.find('<script>')
if first_script != -1:
    insert_at = first_script + len('<script>')
    script_end = html.find('</script>', insert_at)
    block = html[insert_at:script_end]
    if 'YOUR_PROJECT' in block or 'SUPABASE_URL' in block or 'PAYSTACK_PUBLIC_KEY' in block:
        html = html[:insert_at] + '\n' + CONFIG + '\n' + html[script_end:]
        print("Config injected into first script tag")
    else:
        last_script = html.rfind('<script>')
        ins = last_script + len('<script>')
        html = html[:ins] + '\n' + CONFIG + '\n' + html[ins:]
        print("Config injected into main script tag")

html = re.sub(r"mapboxgl\.accessToken\s*=\s*['\"]pk\.[^'\"]+['\"]", "mapboxgl.accessToken = MAPBOX_TOKEN", html)
print("Patched mapboxgl.accessToken")

import json
vercel = {
    "routes": [
        {"src": "/api/(.*)", "dest": "/api/index.js"},
        {"src": "/(.*)", "dest": "/index.html"}
    ]
}
with open("vercel.json", "w") as vf:
    json.dump(vercel, vf, indent=2)
print("vercel.json written")

with open("index.html", "w", encoding="utf-8") as fh:
    fh.write(html)
print(f"index.html saved ({len(html):,} chars)")
print("ALL FIXES DONE")
