# astro-core · cálculo astrológico sobre Swiss Ephemeris
# Copyright (C) 2026 Lafon Blanco SRL
#
# Este programa es software libre: podés redistribuirlo o modificarlo bajo los términos de la
# GNU Affero General Public License, versión 3, publicada por la Free Software Foundation.
# Se distribuye SIN GARANTÍA. Ver el archivo LICENSE.
#
# Usa Swiss Ephemeris (c) Astrodienst AG, a través de pyswisseph, bajo AGPL-3.0. Ver NOTICE.md.
#!/usr/bin/env python3
"""Tránsitos con el motor LOCAL de prueba (pyswisseph, AGPL; sólo desarrollo, no se despliega).
Entrada (stdin JSON): {"natal": <carta canónica>, "start_local":"2026-10-21","days":7,"offset_min":-180}
Salida: cielo de "hoy" (12:00 locales), aspectos activos hoy sobre la carta natal, Luna día por día,
aspectos exactos y cambios de signo de la Luna dentro de la ventana, y fase lunar."""
import json
import sys
from datetime import datetime, timedelta

import swisseph as swe

SIGNS = ['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces']
BODIES = [('sun', swe.SUN), ('moon', swe.MOON), ('mercury', swe.MERCURY), ('venus', swe.VENUS), ('mars', swe.MARS),
          ('jupiter', swe.JUPITER), ('saturn', swe.SATURN), ('uranus', swe.URANUS), ('neptune', swe.NEPTUNE), ('pluto', swe.PLUTO)]
ASPECTS = [('conjunction', 0), ('sextile', 60), ('square', 90), ('trine', 120), ('opposition', 180)]
ORB_NOW = {'moon': 3.0, 'sun': 2.0, 'mercury': 2.0, 'venus': 2.0, 'mars': 2.0, 'jupiter': 2.0, 'saturn': 2.0, 'uranus': 1.5, 'neptune': 1.5, 'pluto': 1.5}
TARGETS = ['sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn', 'asc', 'mc']
FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED


def jd_of(dt):
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60 + dt.second / 3600)


def sky(jd):
    out = {}
    for k, b in BODIES:
        xx, _ = swe.calc_ut(jd, b, FLAGS)
        out[k] = (xx[0] % 360, xx[3])
    return out


def house_of(lon, cusps):
    if not cusps:
        return None
    for i in range(12):
        a, b = cusps[i], cusps[(i + 1) % 12]
        if (a <= b and a <= lon < b) or (a > b and (lon >= a or lon < b)):
            return i + 1
    return 12


def pos(lon):
    i = int(lon // 30)
    return {'lon': round(lon, 4), 'sign': SIGNS[i], 'deg': round(lon - i * 30, 4)}


def diff180(x):
    return (x + 180) % 360 - 180


def refine(lo, hi, state, utc):
    """Instante (a ~segundos) en que state(jd) cambia de valor entre lo y hi."""
    s0 = state(jd_of(utc(lo)))
    for _ in range(20):
        mid = lo + (hi - lo) / 2
        if state(jd_of(utc(mid))) == s0:
            lo = mid
        else:
            hi = mid
    return hi


def compute(inp):
    natal = inp['natal']
    off = timedelta(minutes=int(inp.get('offset_min', -180)))
    day0 = datetime.strptime(inp['start_local'], '%Y-%m-%d')
    days = int(inp.get('days', 7))
    nlon = {p['key']: p['lon'] for p in natal['planets']}
    if natal.get('angles'):
        nlon['asc'] = natal['angles']['asc']['lon']
        nlon['mc'] = natal['angles']['mc']['lon']
    cusps = [natal['houses'][str(i)]['lon'] for i in range(1, 13)] if natal.get('houses') else None
    targets = [t for t in TARGETS if t in nlon]

    def utc(local):
        return local - off

    # ---- hoy 12:00 local
    now_local = day0 + timedelta(hours=12)
    s = sky(jd_of(utc(now_local)))
    planets = []
    for k, _ in BODIES:
        lon, sp = s[k]
        p = pos(lon)
        p.update(key=k, retro=sp < 0, speed=round(sp, 4), house=house_of(lon, cusps))
        planets.append(p)
    elong = (s['moon'][0] - s['sun'][0]) % 360
    # ---- aspectos activos hoy
    active = []
    for k, _ in BODIES:
        lon, sp = s[k]
        for t in targets:
            d = (lon - nlon[t]) % 360
            for name, ang in ASPECTS:
                for a in {ang % 360, (360 - ang) % 360}:
                    o = abs(diff180(d - a))
                    if o <= ORB_NOW[k]:
                        # se acerca si la distancia al ángulo exacto decrece
                        d2 = (lon + sp * 0.1 - nlon[t]) % 360
                        applying = abs(diff180(d2 - a)) < o
                        active.append({'t': k, 'n': t, 'type': name, 'orb': round(o, 3), 'applying': applying})
    # ---- Luna día por día
    moon_days = []
    for i in range(days):
        loc = day0 + timedelta(days=i, hours=12)
        lon = sky(jd_of(utc(loc)))['moon'][0]
        p = pos(lon)
        p.update(date=loc.strftime('%Y-%m-%d'), house=house_of(lon, cusps))
        moon_days.append(p)
    # ---- eventos exactos de la ventana (paso de 1 h + bisección)
    events = []
    start = day0
    steps = days * 24
    prev = None
    for h in range(steps + 1):
        loc = start + timedelta(hours=h)
        prev_s = prev
        cur = sky(jd_of(utc(loc)))
        if prev_s is not None:
            for k, _ in BODIES:
                for t in targets:
                    for name, ang in ASPECTS:
                        for a in {ang % 360, (360 - ang) % 360}:
                            f0 = diff180(prev_s[k][0] - nlon[t] - a)
                            f1 = diff180(cur[k][0] - nlon[t] - a)
                            if f0 * f1 <= 0 and abs(f0) + abs(f1) < 10:
                                lo, hi = loc - timedelta(hours=1), loc
                                for _ in range(20):
                                    mid = lo + (hi - lo) / 2
                                    fm = diff180(sky(jd_of(utc(mid)))[k][0] - nlon[t] - a)
                                    if f0 * fm <= 0:
                                        hi = mid
                                    else:
                                        lo = mid
                                        f0 = fm
                                ex = lo + (hi - lo) / 2
                                events.append({'kind': 'aspect', 't': k, 'n': t, 'type': name, 'when': ex.strftime('%Y-%m-%d %H:%M'),
                                               'retro': cur[k][1] < 0, 'house': house_of(sky(jd_of(utc(ex)))[k][0], cusps)})
            # estaciones: el planeta se detiene y cambia de sentido
            for k, _ in BODIES:
                if k in ('sun', 'moon'):
                    continue
                if (prev_s[k][1] < 0) != (cur[k][1] < 0):
                    ex = refine(loc - timedelta(hours=1), loc, lambda j, k=k: sky(j)[k][1] < 0, utc)
                    events.append({'kind': 'station', 't': k, 'direction': 'retro' if cur[k][1] < 0 else 'direct',
                                   'when': ex.strftime('%Y-%m-%d %H:%M'), 'sign': SIGNS[int(cur[k][0] // 30)],
                                   'house': house_of(cur[k][0], cusps)})
            # ingreso lunar a un signo
            if int(prev_s['moon'][0] // 30) != int(cur['moon'][0] // 30):
                lon = cur['moon'][0]
                ex = refine(loc - timedelta(hours=1), loc, lambda j: int(sky(j)['moon'][0] // 30), utc)
                events.append({'kind': 'moon_ingress', 'when': ex.strftime('%Y-%m-%d %H:%M'), 'sign': SIGNS[int(lon // 30)], 'house': house_of(lon, cusps)})
            # luna nueva / llena
            e0 = (prev_s['moon'][0] - prev_s['sun'][0]) % 360
            e1 = (cur['moon'][0] - cur['sun'][0]) % 360
            if e0 > 300 and e1 < 60:
                ex = refine(loc - timedelta(hours=1), loc, lambda j: ((sky(j)['moon'][0] - sky(j)['sun'][0]) % 360) < 180, utc)
                events.append({'kind': 'new_moon', 'when': ex.strftime('%Y-%m-%d %H:%M'), 'sign': SIGNS[int(cur['moon'][0] // 30)], 'house': house_of(cur['moon'][0], cusps)})
            if e0 < 180 <= e1:
                ex = refine(loc - timedelta(hours=1), loc, lambda j: ((sky(j)['moon'][0] - sky(j)['sun'][0]) % 360) < 180, utc)
                events.append({'kind': 'full_moon', 'when': ex.strftime('%Y-%m-%d %H:%M'), 'sign': SIGNS[int(cur['moon'][0] // 30)], 'house': house_of(cur['moon'][0], cusps)})
        prev = cur
    events.sort(key=lambda e: e['when'])
    return {'date': day0.strftime('%Y-%m-%d'), 'days': days, 'offset_min': int(off.total_seconds() // 60), 'planets': planets,
               'elongation': round(elong, 2), 'active': active, 'moon_days': moon_days, 'events': events,
               'engine_version': 'pyswisseph ' + swe.version + ' / Moshier'}


def main():
    json.dump(compute(json.load(sys.stdin)), sys.stdout, ensure_ascii=False)


if __name__ == '__main__':
    main()
