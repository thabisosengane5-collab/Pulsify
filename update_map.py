#!/usr/bin/env python3
"""
Pulsify Map Updater
Run: python3 update_map.py
Reads index.html → writes index_updated.html
"""
import re, os, sys

SRC  = os.path.join(os.path.dirname(__file__), "index.html")
DEST = os.path.join(os.path.dirname(__file__), "index_updated.html")

if not os.path.exists(SRC):
    sys.exit(f"ERROR: {SRC} not found – make sure index.html is in the same folder as this script.")

with open(SRC, "r", encoding="utf-8") as f:
    html = f.read()

# ─────────────────────────────────────────────────────────────────────────────
# 1. CSS VARIABLES – new cool/vibrant palette
# ─────────────────────────────────────────────────────────────────────────────
OLD_VARS = """:root{
  --bg:#06060C;--bg2:#0D0D18;--surf:#12121F;--surf2:#1A1A2E;
  --border:rgba(255,255,255,0.07);--border2:rgba(255,255,255,0.13);
  --orange:#FF5C00;--lime:#C6FF4A;--pink:#FF2D78;--purple:#7B2FFF;--teal:#00D4AA;
  --text:#F0EEF8;--muted:#6B6880;--muted2:#9997B0;
  --top-h:60px;--tick-h:32px;--bot-h:72px;--card-r:20px;
}"""

NEW_VARS = """:root{
  --bg:#070D1A;--bg2:#0A1128;--surf:#0F1A30;--surf2:#152040;
  --border:rgba(0,229,255,0.08);--border2:rgba(0,229,255,0.18);
  --orange:#FF6B6B;--lime:#00E5FF;--pink:#FF6B6B;--purple:#B026FF;--teal:#00E5FF;
  --cyan:#00E5FF;--coral:#FF6B6B;--neon:#B026FF;
  --text:#E8F4F8;--muted:#4A6080;--muted2:#7A9AB0;
  --top-h:60px;--tick-h:32px;--bot-h:72px;--card-r:20px;
}"""

if OLD_VARS in html:
    html = html.replace(OLD_VARS, NEW_VARS)
    print("✅ CSS variables updated to cool/vibrant palette")
else:
    # Fallback: just patch the :root block
    html = re.sub(
        r':root\s*\{[^}]+\}',
        NEW_VARS,
        html, count=1
    )
    print("✅ CSS variables patched (fallback)")

# ─────────────────────────────────────────────────────────────────────────────
# 2. MAP CSS – full-screen container + new dropdown filter bar
# ─────────────────────────────────────────────────────────────────────────────
OLD_MAP_CSS = """/* ── MAPBOX EXPLORE TAB ── */
#tab-map{padding-top:0}
#tab-map.active{display:flex;flex-direction:column}
.map-top-bar{position:sticky;top:0;z-index:50;background:rgba(6,6,12,.95);backdrop-filter:blur(20px);padding:calc(var(--top-h) + var(--tick-h) + 8px) 14px 10px}
.map-top-bar h2{font-family:'Bebas Neue',sans-serif;font-size:1.6rem;letter-spacing:.03em;margin-bottom:8px}
.map-filter-row{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none}
.map-filter-row::-webkit-scrollbar{display:none}
#mapbox-container{flex:1;height:calc(100vh - var(--top-h) - var(--tick-h) - var(--bot-h) - 110px);min-height:440px;position:relative}"""

NEW_MAP_CSS = """/* ── MAPBOX EXPLORE TAB ── */
#tab-map{padding-top:0;overflow:hidden}
#tab-map.active{display:flex;flex-direction:column}
.map-top-bar{
  position:absolute;top:calc(var(--top-h) + var(--tick-h));left:0;right:0;
  z-index:50;
  background:rgba(7,13,26,.88);
  backdrop-filter:blur(16px);
  padding:10px 12px 8px;
  border-bottom:1px solid var(--border2);
}
.map-top-bar h2{display:none}
/* dropdown filter row */
.map-filter-row{display:flex;gap:7px;align-items:center}
.map-select{
  flex:1;background:rgba(15,26,48,.9);
  border:1px solid var(--border2);
  border-radius:50px;
  color:var(--text);
  font-family:'Syne',sans-serif;font-size:.68rem;font-weight:700;
  padding:7px 10px;outline:none;cursor:pointer;
  -webkit-appearance:none;appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 24 24' fill='none' stroke='%2300E5FF' stroke-width='3'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 8px center;
  padding-right:24px;
}
.map-select option{background:#0A1128;color:var(--text)}
.map-select:focus{border-color:var(--cyan)}
/* full-screen map */
#mapbox-container{
  position:absolute;
  top:calc(var(--top-h) + var(--tick-h) + 54px);
  left:0;right:0;
  bottom:var(--bot-h);
  overflow:hidden;
}"""

if OLD_MAP_CSS in html:
    html = html.replace(OLD_MAP_CSS, NEW_MAP_CSS)
    print("✅ Map CSS replaced with full-screen + dropdown layout")
else:
    # Fallback regex patch
    html = re.sub(
        r'/\* ── MAPBOX EXPLORE TAB ── \*/.*?#mapbox-container\{[^}]+\}',
        NEW_MAP_CSS,
        html, flags=re.DOTALL, count=1
    )
    print("✅ Map CSS patched (fallback)")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Marker CSS – slim SVG-friendly markers
# ─────────────────────────────────────────────────────────────────────────────
OLD_MARKER_CSS = """.mb-marker{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.05rem;border:2.5px solid #fff;cursor:pointer;transition:transform .2s;box-shadow:0 2px 12px rgba(0,0,0,.5)}
.mb-marker:hover{transform:scale(1.18)}
.mb-marker-wrap{display:flex;flex-direction:column;align-items:center;cursor:pointer}
.ev-gqom{background:rgba(255,45,120,.9)}.ev-nightlife{background:rgba(123,47,255,.9)}.ev-sport{background:rgba(0,212,170,.9)}.ev-march{background:rgba(180,255,60,.85)}.ev-music{background:rgba(255,92,0,.9)}.biz-shisa{background:rgba(220,50,0,.9)}.biz-hotel{background:rgba(0,100,220,.9)}.biz-bar{background:rgba(150,0,200,.9)}.biz-bnb{background:rgba(0,180,100,.9)}"""

NEW_MARKER_CSS = """.mb-marker{
  width:32px;height:32px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  border:1.5px solid rgba(255,255,255,.55);
  cursor:pointer;transition:transform .2s,box-shadow .2s;
  box-shadow:0 1px 8px rgba(0,0,0,.45);
  background:rgba(10,17,40,.85);
  backdrop-filter:blur(4px);
}
.mb-marker svg{width:15px;height:15px;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;fill:none}
.mb-marker:hover{transform:scale(1.22);box-shadow:0 2px 16px rgba(0,229,255,.4)}
.mb-marker-wrap{display:flex;flex-direction:column;align-items:center;cursor:pointer}
/* slim coloured borders per type */
.ev-gqom{border-color:#FF6B6B;box-shadow:0 0 8px rgba(255,107,107,.5)}
.ev-gqom svg{stroke:#FF6B6B}
.ev-nightlife{border-color:#B026FF;box-shadow:0 0 8px rgba(176,38,255,.5)}
.ev-nightlife svg{stroke:#B026FF}
.ev-sport{border-color:#00E5FF;box-shadow:0 0 8px rgba(0,229,255,.45)}
.ev-sport svg{stroke:#00E5FF}
.ev-march{border-color:#C6FF4A;box-shadow:0 0 8px rgba(198,255,74,.4)}
.ev-march svg{stroke:#C6FF4A}
.ev-music{border-color:#FF6B6B;box-shadow:0 0 8px rgba(255,107,107,.4)}
.ev-music svg{stroke:#FF6B6B}
.biz-shisa{border-color:#FF8C42;box-shadow:0 0 8px rgba(255,140,66,.4)}
.biz-shisa svg{stroke:#FF8C42}
.biz-hotel{border-color:#00E5FF;box-shadow:0 0 8px rgba(0,229,255,.35)}
.biz-hotel svg{stroke:#00E5FF}
.biz-bar{border-color:#B026FF;box-shadow:0 0 8px rgba(176,38,255,.4)}
.biz-bar svg{stroke:#B026FF}
.biz-bnb{border-color:#4ADE80;box-shadow:0 0 8px rgba(74,222,128,.35)}
.biz-bnb svg{stroke:#4ADE80}"""

if OLD_MARKER_CSS in html:
    html = html.replace(OLD_MARKER_CSS, NEW_MARKER_CSS)
    print("✅ Marker CSS updated to slim SVG style")
else:
    html = re.sub(
        r'\.mb-marker\{.*?\.biz-bnb\{[^}]+\}',
        NEW_MARKER_CSS,
        html, flags=re.DOTALL, count=1
    )
    print("✅ Marker CSS patched (fallback)")

# ─────────────────────────────────────────────────────────────────────────────
# 4. MAP TAB HTML – replace chip bar with three dropdowns
# ─────────────────────────────────────────────────────────────────────────────
OLD_MAP_HTML = """<!-- ══════════════════════════════════════════════════════════════════
  MAP TAB — MAPBOX
══════════════════════════════════════════════════════════════════ -->
<div class="panel" id="tab-map">
  <div class="map-top-bar">
    <h2>🗺 Explore the Map</h2>
    <div class="map-filter-row" id="map-filter-row">
      <button class="chip filled active" onclick="setMapFilter(this,'all')">✦ All</button>
      <button class="chip filled" onclick="setMapFilter(this,'gqom')">🔊 Gqom</button>
      <button class="chip filled" onclick="setMapFilter(this,'nightlife')">🌙 Clubs</button>
      <button class="chip filled" onclick="setMapFilter(this,'sport')">⚽ Sport</button>
      <button class="chip filled" onclick="setMapFilter(this,'march')">✊ Marches</button>
      <button class="chip filled" onclick="setMapFilter(this,'hotel')">🏡 Stay</button>
    </div>
  </div>
  <div id="mapbox-container">
    <div class="map-legend">
      <div class="map-legend-item"><div class="leg-dot" style="background:#FF2D78"></div>Gqom / Nightlife</div>
      <div class="map-legend-item"><div class="leg-dot" style="background:#00D4AA"></div>Sport</div>
      <div class="map-legend-item"><div class="leg-dot" style="background:#b4ff3c"></div>March</div>
      <div class="map-legend-item"><div class="leg-dot" style="background:#0064DC"></div>Hotel / BnB</div>
      <div class="map-legend-item"><div class="leg-dot" style="background:#FF5C00"></div>Shisanyama / Bar</div>
    </div>
    <div class="map-zoom-hint">🔍 Zoom in to<br>reveal more spots</div>
  </div>
</div>"""

NEW_MAP_HTML = """<!-- ══════════════════════════════════════════════════════════════════
  MAP TAB — MAPBOX
══════════════════════════════════════════════════════════════════ -->
<div class="panel" id="tab-map">
  <div class="map-top-bar">
    <div class="map-filter-row" id="map-filter-row">
      <select class="map-select" id="map-cat" onchange="applyMapDropdowns()">
        <option value="all">✦ All</option>
        <option value="events">🎉 Events</option>
        <option value="food">🍽 Food</option>
        <option value="nightlife">💃 Clubs</option>
        <option value="stays">🏨 Stays</option>
      </select>
      <select class="map-select" id="map-genre" onchange="applyMapDropdowns()">
        <option value="all">🎶 All Music</option>
        <option value="amapiano">Amapiano</option>
        <option value="gqom">Gqom</option>
        <option value="maskandi">Maskandi</option>
        <option value="house">House</option>
        <option value="jazz">Jazz</option>
      </select>
      <select class="map-select" id="map-radius" onchange="applyMapDropdowns()">
        <option value="0">📍 Any Dist</option>
        <option value="5">5 km</option>
        <option value="20">20 km</option>
        <option value="50">50 km</option>
      </select>
    </div>
  </div>
  <div id="mapbox-container">
    <div class="map-zoom-hint" style="bottom:24px;right:14px">🔍 Zoom in to reveal spots</div>
  </div>
</div>"""

if OLD_MAP_HTML in html:
    html = html.replace(OLD_MAP_HTML, NEW_MAP_HTML)
    print("✅ Map tab HTML replaced with dropdown filters")
else:
    # Regex fallback
    html = re.sub(
        r'<!-- ══+\s*MAP TAB.*?</div>\s*</div>\s*(?=\n<!-- ══)',
        NEW_MAP_HTML + "\n",
        html, flags=re.DOTALL, count=1
    )
    print("✅ Map tab HTML patched (fallback)")

# ─────────────────────────────────────────────────────────────────────────────
# 5. SVG MARKER ICONS – replace emoji with thin SVG icons
# ─────────────────────────────────────────────────────────────────────────────
# Replace getMarkerCfg to return SVG instead of emoji
OLD_GET_MARKER = """function getMarkerCfg(item,type){
  if(type==='event'){
    const g=(item.genre||'').toLowerCase();
    if(g.includes('gqom'))return{cls:'ev-gqom',emoji:'🔊'};
    if(g.includes('sport'))return{cls:'ev-sport',emoji:'⚽'};
    if(g.includes('march'))return{cls:'ev-march',emoji:'✊'};
    if(g.includes('nightlife'))return{cls:'ev-nightlife',emoji:'🌙'};
    return{cls:'ev-music',emoji:'🎶'};
  }
  const c=item.category;
  if(c==='hotel')return{cls:'biz-hotel',emoji:'🏨'};
  if(c==='bnb')return{cls:'biz-bnb',emoji:'🏡'};
  if(c==='club')return{cls:'ev-nightlife',emoji:'💃'};
  if(c==='shisanyama')return{cls:'biz-shisa',emoji:'🥩'};
  return{cls:'biz-bar',emoji:'🍸'};
}"""

NEW_GET_MARKER = """/* SVG icon strings for slim markers */
const SVG_ICONS={
  music:'<svg viewBox="0 0 24 24"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>',
  sport:'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 000 20M2 12h20"/></svg>',
  march:'<svg viewBox="0 0 24 24"><path d="M18 11V6l-6-3-6 3v5l6 8 6-8z"/></svg>',
  nightlife:'<svg viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>',
  food:'<svg viewBox="0 0 24 24"><path d="M3 2v7c0 1.66 1.34 3 3 3h1v10h2V12h1c1.66 0 3-1.34 3-3V2h-2v5H9V2H7v5H5V2H3z"/><path d="M16 2v20h2V14h3V2c-2.76 0-5 2.24-5 5v4"/></svg>',
  cocktail:'<svg viewBox="0 0 24 24"><path d="M8 2h8l1 4H7L8 2z"/><path d="M7 6l5 7v9"/><path d="M12 22H9m0 0h6"/><path d="M7 6l5 5 5-5"/></svg>',
  hotel:'<svg viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
  bnb:'<svg viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><path d="M9 22V12h6v10"/></svg>',
};
function getMarkerCfg(item,type){
  if(type==='event'){
    const g=(item.genre||'').toLowerCase();
    if(g.includes('gqom'))return{cls:'ev-gqom',svg:SVG_ICONS.music};
    if(g.includes('sport'))return{cls:'ev-sport',svg:SVG_ICONS.sport};
    if(g.includes('march'))return{cls:'ev-march',svg:SVG_ICONS.march};
    if(g.includes('nightlife')||g.includes('club'))return{cls:'ev-nightlife',svg:SVG_ICONS.nightlife};
    return{cls:'ev-music',svg:SVG_ICONS.music};
  }
  const c=item.category;
  if(c==='hotel')return{cls:'biz-hotel',svg:SVG_ICONS.hotel};
  if(c==='bnb')return{cls:'biz-bnb',svg:SVG_ICONS.bnb};
  if(c==='club')return{cls:'ev-nightlife',svg:SVG_ICONS.nightlife};
  if(c==='shisanyama'||c==='restaurant')return{cls:'biz-shisa',svg:SVG_ICONS.food};
  return{cls:'biz-bar',svg:SVG_ICONS.cocktail};
}"""

if OLD_GET_MARKER in html:
    html = html.replace(OLD_GET_MARKER, NEW_GET_MARKER)
    print("✅ getMarkerCfg updated with SVG icons")
else:
    html = re.sub(
        r'function getMarkerCfg\(item,type\)\{.*?\}',
        NEW_GET_MARKER,
        html, flags=re.DOTALL, count=1
    )
    print("✅ getMarkerCfg patched (fallback)")

# ─────────────────────────────────────────────────────────────────────────────
# 6. placeAllMarkers – use SVG instead of emoji
# ─────────────────────────────────────────────────────────────────────────────
OLD_INNER_MARKER = "    dot.textContent=cfg.emoji;"
NEW_INNER_MARKER = "    dot.innerHTML=cfg.svg||cfg.emoji||'';"

html = html.replace(OLD_INNER_MARKER, NEW_INNER_MARKER)
print("✅ Marker innerHTML uses SVG")

# ─────────────────────────────────────────────────────────────────────────────
# 7. HEATMAP + DROPDOWN FILTER JS
# ─────────────────────────────────────────────────────────────────────────────
HEATMAP_JS = """
/* ── HEATMAP + DROPDOWN MAP FILTERS ── */
function buildHeatmapData(){
  const features=[
    ...EVENTS.filter(e=>e.lat&&e.lon).map(e=>({
      type:'Feature',geometry:{type:'Point',coordinates:[e.lon,e.lat]},
      properties:{weight:1,type:'event',genre:(e.genre||'').toLowerCase(),category:'event'}
    })),
    ...BUSINESSES.filter(b=>b.lat&&b.lon).map(b=>({
      type:'Feature',geometry:{type:'Point',coordinates:[b.lon,b.lat]},
      properties:{weight:0.7,type:'biz',genre:'',category:b.category}
    }))
  ];
  return{type:'FeatureCollection',features};
}

function addHeatmapLayer(){
  if(!mapboxMap||mapboxMap.getLayer('pulsify-heat'))return;
  if(!mapboxMap.getSource('pulsify-heat')){
    mapboxMap.addSource('pulsify-heat',{type:'geojson',data:buildHeatmapData()});
  }
  mapboxMap.addLayer({
    id:'pulsify-heat',type:'heatmap',source:'pulsify-heat',
    maxzoom:14,
    paint:{
      'heatmap-weight':['interpolate',['linear'],['get','weight'],0,0,1,1],
      'heatmap-intensity':['interpolate',['linear'],['zoom'],0,0.4,9,1.2],
      'heatmap-color':['interpolate',['linear'],['heatmap-density'],
        0,'rgba(10,17,40,0)',
        0.2,'rgba(0,229,255,0.25)',
        0.5,'rgba(176,38,255,0.55)',
        0.8,'rgba(255,107,107,0.75)',
        1,'rgba(255,107,107,0.95)'
      ],
      'heatmap-radius':['interpolate',['linear'],['zoom'],0,20,9,40],
      'heatmap-opacity':['interpolate',['linear'],['zoom'],7,0.8,14,0.2],
    }
  },'waterway-label');
}

function applyMapDropdowns(){
  const cat=document.getElementById('map-cat')?.value||'all';
  const genre=document.getElementById('map-genre')?.value||'all';
  const radius=parseFloat(document.getElementById('map-radius')?.value||'0');
  allMapMarkers.forEach(m=>{
    const el=m.marker.getElement();
    let show=true;
    // category filter
    if(cat!=='all'){
      if(cat==='events'&&m.type!=='event') show=false;
      if(cat==='food'&&!(m.category==='shisanyama'||m.category==='restaurant')) show=false;
      if(cat==='nightlife'&&!(m.category==='club'||m.genre?.includes('nightlife')||m.genre?.includes('gqom'))) show=false;
      if(cat==='stays'&&!(m.category==='hotel'||m.category==='bnb')) show=false;
    }
    // genre filter
    if(genre!=='all'&&m.type==='event'){
      if(!m.genre?.includes(genre)) show=false;
    }
    el.style.display=show?'flex':'none';
  });
  // update heatmap source
  if(mapboxMap&&mapboxMap.getSource('pulsify-heat')){
    const filtered=buildHeatmapData();
    filtered.features=filtered.features.filter(f=>{
      if(cat==='events'&&f.properties.type!=='event') return false;
      if(cat==='stays'&&!['hotel','bnb'].includes(f.properties.category)) return false;
      if(genre!=='all'&&!f.properties.genre?.includes(genre)) return false;
      return true;
    });
    mapboxMap.getSource('pulsify-heat').setData(filtered);
  }
}
"""

# Insert heatmap JS before closing script tag
if "addHeatmapLayer" not in html:
    html = html.replace(
        "\nfunction catGrad(c)",
        HEATMAP_JS + "\nfunction catGrad(c)"
    )
    print("✅ Heatmap + dropdown JS injected")
else:
    print("ℹ️  Heatmap JS already present – skipping")

# ─────────────────────────────────────────────────────────────────────────────
# 8. Call addHeatmapLayer after map loads
# ─────────────────────────────────────────────────────────────────────────────
OLD_MAP_LOAD = "  mapboxMap.on('load',()=>{ placeAllMarkers(); });"
NEW_MAP_LOAD = "  mapboxMap.on('load',()=>{ placeAllMarkers(); addHeatmapLayer(); });"

if OLD_MAP_LOAD in html:
    html = html.replace(OLD_MAP_LOAD, NEW_MAP_LOAD)
    print("✅ Map load hook updated to include heatmap")

# ─────────────────────────────────────────────────────────────────────────────
# 9. Replace old setMapFilter calls with applyMapDropdowns + keep compat shim
# ─────────────────────────────────────────────────────────────────────────────
SHIM = """
/* backwards-compat shim */
function setMapFilter(btn,f){activeMapFilter=f;applyMapDropdowns();}
"""
if "setMapFilter" in html and "backwards-compat shim" not in html:
    html = html.replace(
        "function setMapFilter(btn,f){",
        SHIM + "function setMapFilter(btn,f){"
    )
    print("✅ setMapFilter shim added")

# ─────────────────────────────────────────────────────────────────────────────
# 10. Ticker / orange accent → coral colour patch
# ─────────────────────────────────────────────────────────────────────────────
# The ticker background was hardcoded orange – update to coral
html = html.replace(
    ".ticker-wrap{position:fixed;top:var(--top-h);left:0;right:0;height:var(--tick-h);z-index:700;background:var(--orange)",
    ".ticker-wrap{position:fixed;top:var(--top-h);left:0;right:0;height:var(--tick-h);z-index:700;background:linear-gradient(90deg,#B026FF,#FF6B6B)"
)
print("✅ Ticker gradient updated")

# ─────────────────────────────────────────────────────────────────────────────
# WRITE OUTPUT
# ─────────────────────────────────────────────────────────────────────────────
with open(DEST, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n🎉  Done!  Output written to: {DEST}")
print("Next steps:")
print("  cp index_updated.html index.html")
print("  git add index.html && git commit -m 'feat: upgraded map' && git push origin main")
print("  npx vercel --prod --yes --token=YOUR_TOKEN")
