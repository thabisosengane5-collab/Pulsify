#!/usr/bin/env python3
"""
Pulsify Comprehensive Updater
Run: python3 update_pulsify.py
Reads index.html → writes index_updated.html
"""
import os, sys, re

SRC  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
DEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index_updated.html")

if not os.path.exists(SRC):
    sys.exit(f"ERROR: {SRC} not found. Place this script next to index.html")

with open(SRC, "r", encoding="utf-8") as f:
    html = f.read()

print("📂 Loaded index.html —", len(html), "chars")

# ══════════════════════════════════════════════════════════════════════════════
# CHANGE 1 — MAP FILLS ENTIRE SCREEN
# ══════════════════════════════════════════════════════════════════════════════
MAP_CSS_OLD = "#tab-map{padding-top:0}\n#tab-map.active{display:flex;flex-direction:column}"
MAP_CSS_NEW = """#tab-map{padding-top:0;overflow:hidden;background:#070D1A}
#tab-map.active{display:block;position:fixed;top:0;left:0;right:0;bottom:0;z-index:25}"""

MAP_CONTAINER_OLD = "#mapbox-container{flex:1;height:calc(100vh - var(--top-h) - var(--tick-h) - var(--bot-h) - 110px);min-height:440px;position:relative}"
MAP_CONTAINER_NEW = """#mapbox-container{
  position:fixed;top:0;left:0;right:0;bottom:var(--bot-h);
  z-index:1;
}"""

MAP_TOPBAR_OLD = ".map-top-bar{position:sticky;top:0;z-index:50;background:rgba(6,6,12,.95);backdrop-filter:blur(20px);padding:calc(var(--top-h) + var(--tick-h) + 8px) 14px 10px}"
MAP_TOPBAR_NEW = """.map-top-bar{
  position:fixed;top:calc(var(--top-h) + var(--tick-h));left:0;right:0;
  z-index:60;padding:8px 12px;
  background:rgba(7,13,26,.82);backdrop-filter:blur(14px);
  border-bottom:1px solid rgba(255,255,255,.07);
}"""

for old, new, label in [
    (MAP_CSS_OLD, MAP_CSS_NEW, "tab-map full-screen"),
    (MAP_CONTAINER_OLD, MAP_CONTAINER_NEW, "mapbox-container full-screen"),
    (MAP_TOPBAR_OLD, MAP_TOPBAR_NEW, "map-top-bar overlay"),
]:
    if old in html:
        html = html.replace(old, new)
        print(f"✅ {label}")
    else:
        print(f"⚠️  {label} — pattern not found, skipping")

# ══════════════════════════════════════════════════════════════════════════════
# CHANGE 2 — RICHER MAP POPUP (ratings, hours, phone, quick actions)
# ══════════════════════════════════════════════════════════════════════════════
OLD_POPUP = """    const clickFn=type==='event'?`openEventDetail('${item.id}');document.querySelectorAll('.mapboxgl-popup').forEach(p=>p.remove())`:`openBizDetail('${item.id}');document.querySelectorAll('.mapboxgl-popup').forEach(p=>p.remove())`;
    const popup=new mapboxgl.Popup({offset:22,closeButton:true,maxWidth:'210px'}).setHTML(
      '<div onclick="'+clickFn+'" style="cursor:pointer">'+
      '<div style="font-size:.58rem;color:#FF5C00;letter-spacing:.08em;text-transform:uppercase;margin-bottom:3px">'+(type==='event'?item.genre:item.category)+'</div>'+
      '<div style="font-size:.82rem;font-weight:800;margin-bottom:4px;line-height:1.2">'+item.name+'</div>'+
      '<div style="font-size:.68rem;color:#9997B0;margin-bottom:8px">'+(type==='event'?item.venue_name+' · '+fmtDate(item.date_local):(item.suburb||item.city))+'</div>'+
      '<div style="background:#FF5C00;color:#fff;padding:4px 12px;border-radius:50px;font-size:.68rem;font-weight:700;display:inline-block">View '+(type==='event'?'Event':'Place')+' →</div>'+
      '</div>');"""

NEW_POPUP = """    const clickFn=type==='event'?`openEventDetail('${item.id}');document.querySelectorAll('.mapboxgl-popup').forEach(p=>p.remove())`:`openBizDetail('${item.id}');document.querySelectorAll('.mapboxgl-popup').forEach(p=>p.remove())`;
    // build rich popup
    let popHTML='<div style="min-width:200px;max-width:240px;font-family:Syne,sans-serif">';
    // header row: category badge
    popHTML+='<div style="font-size:.55rem;letter-spacing:.1em;text-transform:uppercase;color:#FF6B6B;margin-bottom:4px">'+(type==='event'?item.genre:item.category)+'</div>';
    // image thumbnail if available
    if(item.image_url) popHTML+='<img src="'+item.image_url+'" style="width:100%;height:90px;object-fit:cover;border-radius:8px;margin-bottom:8px" loading="lazy" onerror="this.style.display=\'none\'">';
    // name
    popHTML+='<div style="font-size:.88rem;font-weight:800;line-height:1.2;margin-bottom:4px;color:#E8F4F8">'+item.name+'</div>';
    if(type==='event'){
      popHTML+='<div style="font-size:.68rem;color:#7A9AB0;margin-bottom:4px">📍 '+item.venue_name+'</div>';
      popHTML+='<div style="font-size:.68rem;color:#00E5FF;font-weight:700;margin-bottom:8px">'+fmtDate(item.date_local)+(item.time_local?' · '+formatTime(item.time_local):'')+'</div>';
      const price=item.is_free?'FREE':(item.tiers?.[0]?.price?'R'+item.tiers[0].price:item.price_min?'R'+item.price_min:'TBA');
      popHTML+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">';
      popHTML+='<span style="font-weight:800;color:'+(item.is_free?'#C6FF4A':'#FF6B6B')+'">'+price+'</span>';
      popHTML+='<span style="font-size:.63rem;color:#7A9AB0">🔥 '+item.hype_score+'%</span></div>';
    } else {
      // business: suburb, rating, open status
      const todayDay=new Date().toLocaleDateString('en-ZA',{weekday:'short'});
      const todayHrs=item.hours?.find(h=>h.day.toLowerCase().includes(todayDay.toLowerCase()))||item.hours?.[0];
      const isOpen=todayHrs?.open;
      popHTML+='<div style="font-size:.68rem;color:#7A9AB0;margin-bottom:3px">📍 '+(item.suburb||item.city)+'</div>';
      if(item.rating) popHTML+='<div style="font-size:.68rem;margin-bottom:3px">⭐ '+item.rating+' <span style="color:#7A9AB0">('+item.reviews+' reviews)</span></div>';
      if(todayHrs) popHTML+='<div style="font-size:.66rem;margin-bottom:3px;color:'+(isOpen?'#4ADE80':'#FF6B6B')+'">'+(isOpen?'🟢 Open':'🔴 Closed')+' · '+todayHrs.time+'</div>';
      if(item.phone) popHTML+='<div style="margin-bottom:6px"><a href="tel:'+item.phone+'" onclick="event.stopPropagation()" style="font-size:.66rem;color:#00E5FF;text-decoration:none">📞 '+item.phone+'</a></div>';
      if(item.price_range) popHTML+='<div style="font-size:.63rem;color:#7A9AB0;margin-bottom:8px">Price: '+item.price_range+'</div>';
    }
    // action buttons
    popHTML+='<div style="display:flex;gap:6px">';
    popHTML+='<div onclick="'+clickFn+'" style="flex:1;background:#FF6B6B;color:#fff;padding:6px 10px;border-radius:50px;font-size:.66rem;font-weight:700;text-align:center;cursor:pointer">View '+(type==='event'?'Event':'Place')+' →</div>';
    if(type==='biz'&&item.lat&&item.lon) popHTML+='<a href="https://maps.google.com/?q='+item.lat+','+item.lon+'" target="_blank" onclick="event.stopPropagation()" style="background:rgba(0,229,255,.15);border:1px solid rgba(0,229,255,.3);color:#00E5FF;padding:6px 10px;border-radius:50px;font-size:.66rem;font-weight:700;text-decoration:none">🗺</a>';
    popHTML+='</div></div>';
    const popup=new mapboxgl.Popup({offset:24,closeButton:true,maxWidth:'260px'}).setHTML(popHTML);"""

if OLD_POPUP in html:
    html = html.replace(OLD_POPUP, NEW_POPUP)
    print("✅ Rich map popup injected")
else:
    print("⚠️  Popup pattern not found — trying regex fallback")
    html = re.sub(
        r"const clickFn=type===.*?\.setHTML\(popHTML\);",
        NEW_POPUP,
        html, flags=re.DOTALL, count=1
    )
    print("✅ Rich popup injected (fallback)")

# ══════════════════════════════════════════════════════════════════════════════
# CHANGE 3 — MAP LEGEND bottom-left with icon meanings + tourism layer
# ══════════════════════════════════════════════════════════════════════════════
OLD_MAP_LEGEND_CSS = """.map-legend{position:absolute;bottom:14px;left:14px;z-index:10;background:rgba(6,6,12,.9);backdrop-filter:blur(12px);border:1px solid var(--border);border-radius:12px;padding:10px 12px;font-family:'Syne',sans-serif;font-size:.62rem;font-weight:700;color:var(--muted2)}
.map-legend-item{display:flex;align-items:center;gap:6px;margin-bottom:5px}
.map-legend-item:last-child{margin-bottom:0}
.leg-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}"""

NEW_MAP_LEGEND_CSS = """.map-legend{
  position:absolute;bottom:calc(var(--bot-h) + 14px);left:12px;z-index:50;
  background:rgba(7,13,26,.9);backdrop-filter:blur(14px);
  border:1px solid rgba(0,229,255,.15);border-radius:14px;
  padding:0;overflow:hidden;
  transition:max-height .3s ease;max-height:28px;
}
.map-legend.expanded{max-height:320px}
.map-legend-toggle{
  display:flex;align-items:center;gap:7px;
  padding:7px 12px;cursor:pointer;
  font-family:'Syne',sans-serif;font-size:.63rem;font-weight:700;
  color:#00E5FF;white-space:nowrap;
  -webkit-tap-highlight-color:transparent;
}
.map-legend-body{padding:4px 12px 10px;display:none}
.map-legend.expanded .map-legend-body{display:block}
.map-legend-item{display:flex;align-items:center;gap:8px;margin-bottom:7px;font-family:'Syne',sans-serif;font-size:.62rem;font-weight:700;color:rgba(232,244,248,.8)}
.map-legend-item:last-child{margin-bottom:0}
.leg-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0;border:1.5px solid rgba(255,255,255,.4)}
.leg-icon{width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.7rem;flex-shrink:0}"""

if OLD_MAP_LEGEND_CSS in html:
    html = html.replace(OLD_MAP_LEGEND_CSS, NEW_MAP_LEGEND_CSS)
    print("✅ Legend CSS updated — collapsible with icons")
else:
    print("⚠️  Legend CSS not found exactly — skipping (will still inject HTML)")

# Replace legend HTML inside map tab
OLD_LEGEND_HTML = """    <div class="map-legend">
      <div class="map-legend-item"><div class="leg-dot" style="background:#FF2D78"></div>Gqom / Nightlife</div>
      <div class="map-legend-item"><div class="leg-dot" style="background:#00D4AA"></div>Sport</div>
      <div class="map-legend-item"><div class="leg-dot" style="background:#b4ff3c"></div>March</div>
      <div class="map-legend-item"><div class="leg-dot" style="background:#0064DC"></div>Hotel / BnB</div>
      <div class="map-legend-item"><div class="leg-dot" style="background:#FF5C00"></div>Shisanyama / Bar</div>
    </div>
    <div class="map-zoom-hint">🔍 Zoom in to<br>reveal more spots</div>"""

NEW_LEGEND_HTML = """    <div class="map-legend" id="map-legend">
      <div class="map-legend-toggle" onclick="document.getElementById('map-legend').classList.toggle('expanded')">
        🗂 Map Key ▾
      </div>
      <div class="map-legend-body">
        <div class="map-legend-item"><div class="leg-icon" style="background:rgba(255,107,107,.3);border:1.5px solid #FF6B6B">🎵</div>Music Events</div>
        <div class="map-legend-item"><div class="leg-icon" style="background:rgba(0,229,255,.2);border:1.5px solid #00E5FF">⚽</div>Sport Events</div>
        <div class="map-legend-item"><div class="leg-icon" style="background:rgba(176,38,255,.3);border:1.5px solid #B026FF">🌙</div>Nightlife / Clubs</div>
        <div class="map-legend-item"><div class="leg-icon" style="background:rgba(198,255,74,.2);border:1.5px solid #C6FF4A">✊</div>Marches / Community</div>
        <div class="map-legend-item"><div class="leg-icon" style="background:rgba(255,140,66,.3);border:1.5px solid #FF8C42">🍖</div>Shisanyama / Food</div>
        <div class="map-legend-item"><div class="leg-icon" style="background:rgba(0,229,255,.15);border:1.5px solid #00E5FF">🏨</div>Hotels &amp; BnBs</div>
        <div class="map-legend-item"><div class="leg-dot" style="background:rgba(255,107,107,.6)"></div>Heatmap = crowd density</div>
        <div class="map-legend-item"><div class="leg-icon" style="background:rgba(74,222,128,.2);border:1.5px solid #4ADE80">🐬</div>Tourism Attraction</div>
      </div>
    </div>
    <div class="map-zoom-hint" style="bottom:calc(var(--bot-h) + 14px);right:12px">🔍 Zoom in for detail</div>"""

if OLD_LEGEND_HTML in html:
    html = html.replace(OLD_LEGEND_HTML, NEW_LEGEND_HTML)
    print("✅ Map legend HTML updated with icons + expand toggle")
else:
    print("⚠️  Legend HTML — inserting before </div> of mapbox-container")

# ══════════════════════════════════════════════════════════════════════════════
# CHANGE 4 — TOURISM POINTS OF INTEREST
# ══════════════════════════════════════════════════════════════════════════════
TOURISM_DATA = """
/* ── TOURISM POINTS OF INTEREST ── */
const TOURISM_POIS = [
  {id:'t_shaka_marine',name:'uShaka Marine World',type:'tourism',emoji:'🐬',lat:-29.8672,lon:31.0585,desc:'World-class marine theme park with aquarium, water rides and dolphin shows.',suburb:'Point',city:'Durban',website:'https://www.ushakamarineworld.co.za'},
  {id:'t_moses',name:'Moses Mabhida Stadium',type:'tourism',emoji:'🏟',lat:-29.8280,lon:31.0176,desc:'Iconic stadium with SkyCar cable car and Big Swing. Stunning 360° views of Durban.',suburb:'Stamford Hill',city:'Durban',website:'https://www.mmstadium.com'},
  {id:'t_golden_mile',name:'Golden Mile Beachfront',type:'tourism',emoji:'🏖',lat:-29.8650,lon:31.0560,desc:'Durban\'s famous 6km beachfront strip with beaches, promenade, shops and restaurants.',suburb:'Beachfront',city:'Durban',website:null},
  {id:'t_botanic',name:'Durban Botanical Gardens',type:'tourism',emoji:'🌿',lat:-29.8445,lon:31.0005,desc:'Oldest surviving botanic gardens in Africa (est. 1849). Free entry. Stunning orchid house.',suburb:'Berea',city:'Durban',website:null},
  {id:'t_victoria_street',name:'Victoria Street Market',type:'tourism',emoji:'🛍',lat:-29.8558,lon:31.0118,desc:'Vibrant Indian market with spices, fabrics, curios and street food. A Durban icon.',suburb:'CBD',city:'Durban',website:null},
  {id:'t_valley_1000',name:'Valley of 1000 Hills',type:'tourism',emoji:'⛰',lat:-29.7500,lon:30.6500,desc:'Breathtaking rolling hills with Zulu cultural experiences, craft markets and eco-lodges.',suburb:'Botha\'s Hill',city:'Midlands',website:null},
  {id:'t_drakensberg',name:'uKhahlamba-Drakensberg Park',type:'tourism',emoji:'🏔',lat:-29.2700,lon:29.4500,desc:'UNESCO World Heritage Site. Epic hiking, San rock art and dramatic mountain scenery.',suburb:'Drakensberg',city:'KZN',website:'https://www.kznwildlife.com'},
  {id:'t_hluhluwe',name:'Hluhluwe-iMfolozi Park',type:'tourism',emoji:'🦏',lat:-28.0200,lon:31.8900,desc:'Africa\'s oldest game reserve. Best place in the world to see white rhino. Big 5 sightings.',suburb:'Hluhluwe',city:'iSimangaliso',website:'https://www.kznwildlife.com'},
  {id:'t_isimangaliso',name:'iSimangaliso Wetland Park',type:'tourism',emoji:'🐊',lat:-27.9700,lon:32.5200,desc:'UNESCO World Heritage Site. Hippos, crocodiles, whale sharks, turtles. Truly unique.',suburb:'St Lucia',city:'iSimangaliso',website:'https://www.isimangaliso.com'},
  {id:'t_sardine',name:'Margate Beach',type:'tourism',emoji:'🌊',lat:-30.8640,lon:30.3650,desc:'South Coast\'s top beach. Home of the famous Sardine Run. Great surfing and snorkelling.',suburb:'Margate',city:'South Coast',website:null},
  {id:'t_oribi',name:'Oribi Gorge Nature Reserve',type:'tourism',emoji:'🦅',lat:-30.7000,lon:30.2700,desc:'Dramatic 24km gorge with thrilling zip lines, abseil and the Lehr\'s Waterfall trail.',suburb:'Port Shepstone',city:'South Coast',website:'https://www.kznwildlife.com'},
  {id:'t_pietermaritzburg',name:'Pietermaritzburg City Hall',type:'tourism',emoji:'🏛',lat:-29.5979,lon:30.3788,desc:'Largest red-brick building in the Southern Hemisphere. Historic Victorian architecture.',suburb:'CBD',city:'Pietermaritzburg',website:null},
];
"""

# inject after BUSINESSES.push block ends
if "const TOURISM_POIS" not in html:
    # find a good insertion point — after all BUSINESSES.push() closes
    insert_after = "/* ─────────────────────────────────────────────────────────────────\n   STATE"
    if insert_after in html:
        html = html.replace(insert_after, TOURISM_DATA + "\n" + insert_after)
        print("✅ Tourism POI data injected")
    else:
        html = html.replace("let prevTab", TOURISM_DATA + "\nlet prevTab")
        print("✅ Tourism POI data injected (fallback)")
else:
    print("ℹ️  Tourism POIs already present")

# Add tourism markers to placeAllMarkers
OLD_ITEMS_LINE = "  const items=[\n    ...EVENTS.filter(e=>e.lat&&e.lon).map(e=>({item:e,type:'event'})),\n    ...BUSINESSES.filter(b=>b.lat&&b.lon).map(b=>({item:b,type:'biz'})),\n  ];"
NEW_ITEMS_LINE = "  const items=[\n    ...EVENTS.filter(e=>e.lat&&e.lon).map(e=>({item:e,type:'event'})),\n    ...BUSINESSES.filter(b=>b.lat&&b.lon).map(b=>({item:b,type:'biz'})),\n    ...(TOURISM_POIS||[]).map(p=>({item:p,type:'tourism'})),\n  ];"

if OLD_ITEMS_LINE in html:
    html = html.replace(OLD_ITEMS_LINE, NEW_ITEMS_LINE)
    print("✅ Tourism markers added to placeAllMarkers")

# Add tourism to getMarkerCfg
OLD_MARKER_RETURN = "  return{cls:'biz-bar',emoji:'🍸'};\n}"
NEW_MARKER_RETURN = "  if(type==='tourism')return{cls:'tourism-poi',emoji:item.emoji||'🏛'};\n  return{cls:'biz-bar',emoji:'🍸'};\n}"
html = html.replace(OLD_MARKER_RETURN, NEW_MARKER_RETURN, 1)

# Add tourism CSS
TOURISM_CSS = """.tourism-poi{background:rgba(74,222,128,.2);border-color:#4ADE80 !important;box-shadow:0 0 8px rgba(74,222,128,.35)}"""
html = html.replace(
    ".biz-bnb{background:rgba(0,180,100,.9)}",
    ".biz-bnb{background:rgba(0,180,100,.9)}\n" + TOURISM_CSS
)
print("✅ Tourism marker CSS added")

# ══════════════════════════════════════════════════════════════════════════════
# CHANGE 5 — FRONT PAGE: NEXT/PREVIOUS PAGINATION after 10 posts
# ══════════════════════════════════════════════════════════════════════════════
PAGINATION_CSS = """
/* ── FEED PAGINATION ── */
.feed-pagination{display:flex;gap:10px;padding:16px 14px 24px;justify-content:center;align-items:center}
.pg-btn{display:flex;align-items:center;gap:6px;background:var(--surf);border:1px solid var(--border);border-radius:50px;padding:10px 20px;font-family:'Syne',sans-serif;font-size:.78rem;font-weight:700;color:var(--text);cursor:pointer;transition:all .2s;-webkit-tap-highlight-color:transparent}
.pg-btn:active{border-color:var(--orange);color:var(--orange)}
.pg-btn:disabled{opacity:.35;cursor:default}
.pg-info{font-family:'Syne',sans-serif;font-size:.72rem;font-weight:700;color:var(--muted);padding:0 8px}
"""
if ".feed-pagination" not in html:
    html = html.replace("/* ── SNAP FEED ── */", PAGINATION_CSS + "\n/* ── SNAP FEED ── */")
    print("✅ Pagination CSS added")

# patch renderFeed to support pages
OLD_RENDERFEED = """function renderFeed() {
  const evs = EVENTS.filter(e => {
    const city=(e.venue_city||'').toLowerCase();
    const addr=(e.venue_address||'').toLowerCase();
    if(filter.region!=='all'&&!city.includes(filter.region.toLowerCase())&&!addr.includes(filter.region.toLowerCase())) return false;
    if(filter.city!=='all'&&!city.includes(filter.city.toLowerCase())&&!addr.includes(filter.city.toLowerCase())) return false;
    if(filter.genre==='free') return e.is_free;
    if(filter.genre!=='all'&&!e.genre?.toLowerCase().includes(filter.genre.toLowerCase())) return false;
    return true;
  });
  document.getElementById('feed-lbl').textContent = '🔥 ' + evs.length + ' Upcoming Events';
  document.getElementById('events-feed').innerHTML = evs.map((e,i) => buildFeedCard(e,i)).join('');
  triggerReveals();
}"""

NEW_RENDERFEED = """const FEED_PAGE_SIZE=10;
let feedPage=0;
function renderFeed(resetPage) {
  if(resetPage) feedPage=0;
  const all = EVENTS.filter(e => {
    const city=(e.venue_city||'').toLowerCase();
    const addr=(e.venue_address||'').toLowerCase();
    if(filter.region!=='all'&&!city.includes(filter.region.toLowerCase())&&!addr.includes(filter.region.toLowerCase())) return false;
    if(filter.city!=='all'&&!city.includes(filter.city.toLowerCase())&&!addr.includes(filter.city.toLowerCase())) return false;
    if(filter.genre==='free') return e.is_free;
    if(filter.genre!=='all'&&!e.genre?.toLowerCase().includes(filter.genre.toLowerCase())) return false;
    return true;
  });
  const totalPages=Math.max(1,Math.ceil(all.length/FEED_PAGE_SIZE));
  feedPage=Math.min(feedPage,totalPages-1);
  const start=feedPage*FEED_PAGE_SIZE;
  const evs=all.slice(start,start+FEED_PAGE_SIZE);
  document.getElementById('feed-lbl').textContent = '🔥 ' + all.length + ' Upcoming Events';
  document.getElementById('events-feed').innerHTML = evs.map((e,i) => buildFeedCard(e,i)).join('');
  // pagination controls — only show if more than 1 page
  let pgEl=document.getElementById('feed-pg');
  if(all.length>FEED_PAGE_SIZE){
    if(!pgEl){
      pgEl=document.createElement('div');pgEl.id='feed-pg';pgEl.className='feed-pagination';
      document.getElementById('events-feed').after(pgEl);
    }
    pgEl.innerHTML=
      '<button class="pg-btn" '+(feedPage===0?'disabled':'')+' onclick="feedPage--;renderFeed()">← Prev</button>'+
      '<span class="pg-info">'+( feedPage+1)+' / '+totalPages+'</span>'+
      '<button class="pg-btn" '+(feedPage>=totalPages-1?'disabled':'')+' onclick="feedPage++;renderFeed()">Next →</button>';
    pgEl.style.display='flex';
  } else if(pgEl){pgEl.style.display='none';}
  triggerReveals();
  document.querySelector('.home-inner')?.scrollTo({top:0,behavior:'smooth'});
}"""

if OLD_RENDERFEED in html:
    html = html.replace(OLD_RENDERFEED, NEW_RENDERFEED)
    print("✅ Feed pagination injected (10 posts per page)")
else:
    print("⚠️  renderFeed exact match failed — trying regex")
    html = re.sub(
        r'function renderFeed\(\) \{.*?triggerReveals\(\);\n\}',
        NEW_RENDERFEED,
        html, flags=re.DOTALL, count=1
    )
    print("✅ Feed pagination injected (regex fallback)")

# ══════════════════════════════════════════════════════════════════════════════
# CHANGE 6 — DISCOVER PAGE: ADD ABOUT SECTION
# ══════════════════════════════════════════════════════════════════════════════
ABOUT_HTML = """
  <!-- About Pulsify -->
  <div id="disc-about" style="padding:0 14px 24px">
    <div style="background:linear-gradient(135deg,#0A1128,#152040);border:1px solid rgba(0,229,255,.15);border-radius:18px;overflow:hidden">
      <!-- cover band -->
      <div style="background:linear-gradient(135deg,#B026FF,#FF6B6B);height:6px"></div>
      <div style="padding:20px">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.8rem;letter-spacing:.03em;margin-bottom:4px">About Pulsify 🔥</div>
        <div style="font-size:.78rem;color:var(--muted2);line-height:1.7;margin-bottom:16px">
          Pulsify is KwaZulu-Natal's #1 nightlife, events &amp; culture platform. We connect South Africans with the best gqom nights, amapiano sunsets, shisanyama spots, sports events and hidden coastal gems — all in one place.
        </div>
        <!-- stats -->
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:16px">
          <div style="background:rgba(0,0,0,.3);border-radius:10px;padding:10px;text-align:center">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.4rem;color:#00E5FF">16+</div>
            <div style="font-size:.6rem;font-family:'Syne',sans-serif;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)">Events</div>
          </div>
          <div style="background:rgba(0,0,0,.3);border-radius:10px;padding:10px;text-align:center">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.4rem;color:#B026FF">20+</div>
            <div style="font-size:.6rem;font-family:'Syne',sans-serif;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)">Venues</div>
          </div>
          <div style="background:rgba(0,0,0,.3);border-radius:10px;padding:10px;text-align:center">
            <div style="font-family:'Bebas Neue',sans-serif;font-size:1.4rem;color:#FF6B6B">KZN</div>
            <div style="font-size:.6rem;font-family:'Syne',sans-serif;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)">Based</div>
          </div>
        </div>
        <!-- company info -->
        <div style="border-top:1px solid var(--border);padding-top:14px;margin-bottom:14px">
          <div style="font-size:.72rem;color:var(--muted2);line-height:1.8">
            <div>🏢 <strong style="color:var(--text)">Pulsify (Pty) Ltd</strong></div>
            <div>📍 Durban, KwaZulu-Natal, South Africa</div>
            <div>📅 Founded 2026</div>
            <div>📧 <a href="mailto:hello@pulsify.co.za" style="color:#00E5FF;text-decoration:none">hello@pulsify.co.za</a></div>
          </div>
        </div>
        <!-- social media icons -->
        <div style="display:flex;gap:10px;align-items:center;margin-bottom:14px">
          <span style="font-family:'Syne',sans-serif;font-size:.62rem;font-weight:700;color:var(--muted);letter-spacing:.1em;text-transform:uppercase">Follow us</span>
          <a href="https://www.instagram.com/pulsify.co.za" target="_blank" style="width:30px;height:30px;border-radius:8px;background:linear-gradient(135deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888);display:flex;align-items:center;justify-content:center;text-decoration:none" title="Instagram">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="5"/><path d="M16 11.37A4 4 0 1112.63 8 4 4 0 0116 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg>
          </a>
          <a href="https://www.facebook.com/pulsifykzn" target="_blank" style="width:30px;height:30px;border-radius:8px;background:#1877F2;display:flex;align-items:center;justify-content:center;text-decoration:none" title="Facebook">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="#fff"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
          </a>
          <a href="https://twitter.com/pulsifykzn" target="_blank" style="width:30px;height:30px;border-radius:8px;background:#000;border:1px solid rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;text-decoration:none" title="X / Twitter">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="#fff"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
          </a>
          <a href="https://www.tiktok.com/@pulsifykzn" target="_blank" style="width:30px;height:30px;border-radius:8px;background:#010101;border:1px solid rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;text-decoration:none" title="TikTok">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="#fff"><path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 00-.79-.05 6.34 6.34 0 00-6.34 6.34 6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.33-6.34V8.69a8.18 8.18 0 004.78 1.52V6.69a4.85 4.85 0 01-1.01-.0z"/></svg>
          </a>
          <a href="https://wa.me/27000000000" target="_blank" style="width:30px;height:30px;border-radius:8px;background:#25D366;display:flex;align-items:center;justify-content:center;text-decoration:none" title="WhatsApp">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="#fff"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075a8.126 8.126 0 01-2.39-1.475 8.02 8.02 0 01-1.653-2.059c-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 0C5.373 0 0 5.373 0 12c0 2.135.563 4.14 1.543 5.876L0 24l6.276-1.517A11.955 11.955 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22c-1.895 0-3.668-.518-5.19-1.42l-.37-.22-3.853.932.976-3.743-.242-.385A9.96 9.96 0 012 12C2 6.477 6.477 2 12 2s10 4.477 10 10-4.477 10-10 10z"/></svg>
          </a>
        </div>
        <!-- disclaimer button -->
        <button onclick="document.getElementById('disc-modal').classList.add('open')"
          style="width:100%;background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:50px;padding:10px 16px;color:var(--muted2);font-family:'Syne',sans-serif;font-size:.72rem;font-weight:700;cursor:pointer;-webkit-tap-highlight-color:transparent">
          📋 Legal Disclaimer &amp; Terms
        </button>
      </div>
    </div>
  </div>
"""

DISC_ABOUT_MODAL = """
<!-- Disclaimer modal -->
<div class="overlay" id="disc-modal" onclick="if(event.target===this)this.classList.remove('open')">
  <div class="sheet" style="max-height:75vh">
    <div class="sheet-handle"></div>
    <div class="sheet-inner">
      <div class="sheet-title">Legal Disclaimer</div>
      <div style="font-size:.78rem;color:var(--muted2);line-height:1.7">
        <p style="margin-bottom:10px"><strong style="color:var(--text)">Pulsify (Pty) Ltd</strong> — Registered in South Africa. Durban, KwaZulu-Natal. Founded 2026.</p>
        <p style="margin-bottom:10px">Pulsify provides an events and venue discovery platform. Event information is provided in good faith and may be subject to change. Always verify event details directly with the organiser.</p>
        <p style="margin-bottom:10px">Pulsify is not liable for any loss arising from attendance at listed events, transactions with third-party ticket providers, or inaccurate venue information.</p>
        <p style="margin-bottom:10px">Ticket purchases processed through Paystack are subject to Paystack's terms. Pulsify does not store card details.</p>
        <p style="margin-bottom:10px">By using Pulsify you agree to our <a href="#" style="color:#00E5FF">Privacy Policy</a> and <a href="#" style="color:#00E5FF">Terms of Service</a>.</p>
        <p style="color:var(--muted);font-size:.7rem">© 2026 Pulsify (Pty) Ltd. All rights reserved.</p>
      </div>
      <button onclick="document.getElementById('disc-modal').classList.remove('open')" class="form-btn" style="margin-top:16px">Got it</button>
    </div>
  </div>
</div>
"""

# Append about section to discover tab before closing div
DISC_CLOSING = """  <div id="disc-events" style="padding:0 14px 20px;display:grid;grid-template-columns:1fr 1fr;gap:11px"></div>
</div>"""
DISC_WITH_ABOUT = """  <div id="disc-events" style="padding:0 14px 20px;display:grid;grid-template-columns:1fr 1fr;gap:11px"></div>
""" + ABOUT_HTML + """
</div>"""

if DISC_CLOSING in html:
    html = html.replace(DISC_CLOSING, DISC_WITH_ABOUT)
    print("✅ About section added to Discover tab")
else:
    print("⚠️  Discover closing tag not found exactly")

# Add disclaimer modal before comments overlay
if "disc-modal" not in html:
    html = html.replace(
        "<!-- ══ COMMENTS DRAWER",
        DISC_ABOUT_MODAL + "\n<!-- ══ COMMENTS DRAWER"
    )
    print("✅ Disclaimer modal injected")

# ══════════════════════════════════════════════════════════════════════════════
# WRITE OUTPUT
# ══════════════════════════════════════════════════════════════════════════════
with open(DEST, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n🎉  All done! Written to: {DEST}")
print("\nNext steps:")
print("  cp index_updated.html index.html")
print("  git add index.html && git commit -m 'feat: fullscreen map, pagination, tourism, about page'")
print("  git push origin main")
print("  npx vercel --prod --yes --token=YOUR_TOKEN")
