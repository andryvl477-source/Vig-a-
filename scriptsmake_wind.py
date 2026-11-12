#!/usr/bin/env python3
"""Descarga viento a 10 m del GFS (NOAA NOMADS) y lo guarda como wind.json
en el formato que espera leaflet-velocity. Si el ciclo más reciente aún no
existe, retrocede al anterior (hasta 24 h)."""
import json, sys, urllib.request, urllib.error, datetime as dt
import numpy as np, xarray as xr

LO1, LO2, LA1, LA2 = -130, -30, 35, -10      # misma zona del mapa de la app
OUT = sys.argv[1] if len(sys.argv) > 1 else "wind.json"

def url_for(day, cyc):
    return ("https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_1p00.pl"
            f"?file=gfs.t{cyc:02d}z.pgrb2.1p00.f000"
            "&var_UGRD=on&var_VGRD=on&lev_10_m_above_ground=on"
            f"&subregion=&leftlon={LO1}&rightlon={LO2}&toplat={LA1}&bottomlat={LA2}"
            f"&dir=%2Fgfs.{day:%Y%m%d}%2F{cyc:02d}%2Fatmos")

def download():
    now = dt.datetime.now(dt.timezone.utc)
    base = now.replace(minute=0, second=0, microsecond=0)
    base -= dt.timedelta(hours=base.hour % 6)
    for back in range(0, 5):                      # hasta 4 ciclos atrás
        t = base - dt.timedelta(hours=6 * back)
        u = url_for(t, t.hour)
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "vigia-wind/1.0"})
            data = urllib.request.urlopen(req, timeout=60).read()
            if data[:4] == b"GRIB":
                open("gfs.grib2", "wb").write(data)
                print("OK ciclo", t.isoformat())
                return t
            print("sin GRIB en", t, "->", data[:80])
        except urllib.error.HTTPError as e:
            print("no disponible", t, e.code)
    sys.exit("No se pudo descargar ningún ciclo de GFS")

ref = download()
ds = xr.open_dataset("gfs.grib2", engine="cfgrib")
u = ds["u10"]; v = ds["v10"]
lon = ((u.longitude + 180) % 360) - 180          # 0..360 -> -180..180
u = u.assign_coords(longitude=lon).sortby("longitude").sortby("latitude", ascending=False)
v = v.assign_coords(longitude=lon).sortby("longitude").sortby("latitude", ascending=False)

lats = u.latitude.values; lons = u.longitude.values
d = float(abs(lons[1] - lons[0]))
nx, ny = len(lons), len(lats)

def hdr(n):
    return {"parameterCategory": 2, "parameterNumber": n,
            "lo1": float(lons[0]), "la1": float(lats[0]),
            "lo2": float(lons[-1]), "la2": float(lats[-1]),
            "dx": d, "dy": d, "nx": nx, "ny": ny,
            "refTime": ref.strftime("%Y-%m-%dT%H:%M:%SZ")}

def flat(a):
    return [round(float(x), 2) if np.isfinite(x) else 0 for x in a.values.ravel()]

json.dump([{"header": hdr(2), "data": flat(u)},
           {"header": hdr(3), "data": flat(v)}], open(OUT, "w"), separators=(",", ":"))
print("escrito", OUT, f"{nx}x{ny}", ref)
