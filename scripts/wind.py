"""Genera data/wind.json en el formato de leaflet-velocity usando Open-Meteo (gratis, sin llave)."""
import json, math, time, urllib.request, urllib.parse, datetime

# Misma cuadrícula que usa la app (Atlántico, Caribe, Golfo y Pacífico este)
LO1, LA1, LO2, LA2, D = -130, 35, -30, -10, 2
NX = int((LO2 - LO1) / D) + 1   # 51
NY = int((LA1 - LA2) / D) + 1   # 23

lats = [LA1 - j * D for j in range(NY)]   # de norte a sur
lons = [LO1 + i * D for i in range(NX)]   # de oeste a este
points = [(la, lo) for la in lats for lo in lons]

def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            print("reintento", k + 1, e)
            time.sleep(10 * (k + 1))
    raise SystemExit("Open-Meteo no respondió")

speeds, dirs, ref = [], [], None
for s in range(0, len(points), 100):
    chunk = points[s:s + 100]
    q = urllib.parse.urlencode({
        "latitude": ",".join(str(p[0]) for p in chunk),
        "longitude": ",".join(str(p[1]) for p in chunk),
        "current": "wind_speed_10m,wind_direction_10m",
        "wind_speed_unit": "ms",
    })
    res = get("https://api.open-meteo.com/v1/forecast?" + q)
    if isinstance(res, dict):
        res = [res]
    for r in res:
        c = r["current"]
        speeds.append(c["wind_speed_10m"] or 0)
        dirs.append(c["wind_direction_10m"] or 0)
        ref = ref or c["time"]
    time.sleep(1)

# Dirección = de dónde VIENE el viento -> componentes u (este) y v (norte)
u = [round(-sp * math.sin(math.radians(d)), 2) for sp, d in zip(speeds, dirs)]
v = [round(-sp * math.cos(math.radians(d)), 2) for sp, d in zip(speeds, dirs)]

ref_time = (ref or datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M")) + ":00Z"
hdr = {"lo1": LO1, "la1": LA1, "lo2": LO2, "la2": LA2, "dx": D, "dy": D,
       "nx": NX, "ny": NY, "refTime": ref_time, "parameterCategory": 2}
out = [{"header": {**hdr, "parameterNumber": 2}, "data": u},
       {"header": {**hdr, "parameterNumber": 3}, "data": v}]

assert len(u) == NX * NY, "cuadrícula incompleta"
with open("data/wind.json", "w") as f:
    json.dump(out, f, separators=(",", ":"))
print("OK", NX, "x", NY, ref_time)
