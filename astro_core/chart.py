# astro-core · cálculo astrológico sobre Swiss Ephemeris
# Copyright (C) 2026 Lafon Blanco SRL
#
# Este programa es software libre: podés redistribuirlo o modificarlo bajo los términos de la
# GNU Affero General Public License, versión 3, publicada por la Free Software Foundation.
# Se distribuye SIN GARANTÍA. Ver el archivo LICENSE.
#
# Usa Swiss Ephemeris (c) Astrodienst AG, a través de pyswisseph, bajo AGPL-3.0. Ver NOTICE.md.
#!/usr/bin/env python3
"""Cálculo de la carta natal (Swiss Ephemeris, pyswisseph, AGPL-3.0). compute(dict) -> dict; también corre por consola:
lee un JSON por stdin y escribe el resultado por stdout.

Entrada:  {"birth_utc":"1980-11-11 23:00:00","lat":-34.92,"lon":-57.95,"time_known":true,"house_system":"P","node":"mean"}
Salida:   ver src/Engine/AstroEngine.php (formato canónico) + 'positions' con longitudes exactas.
Efemérides: Moshier incorporado (sin archivos; precisión de décimas de segundo de arco para planetas).
"""
import json
import sys
from datetime import datetime

import swisseph as swe

SIGNS = ['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces']
BODIES = [('sun', swe.SUN), ('moon', swe.MOON), ('mercury', swe.MERCURY), ('venus', swe.VENUS), ('mars', swe.MARS),
          ('jupiter', swe.JUPITER), ('saturn', swe.SATURN), ('uranus', swe.URANUS), ('neptune', swe.NEPTUNE), ('pluto', swe.PLUTO)]
ELEMENT = {'aries': 'fire', 'leo': 'fire', 'sagittarius': 'fire', 'taurus': 'earth', 'virgo': 'earth', 'capricorn': 'earth',
           'gemini': 'air', 'libra': 'air', 'aquarius': 'air', 'cancer': 'water', 'scorpio': 'water', 'pisces': 'water'}
MODALITY = {'aries': 'cardinal', 'cancer': 'cardinal', 'libra': 'cardinal', 'capricorn': 'cardinal',
            'taurus': 'fixed', 'leo': 'fixed', 'scorpio': 'fixed', 'aquarius': 'fixed',
            'gemini': 'mutable', 'virgo': 'mutable', 'sagittarius': 'mutable', 'pisces': 'mutable'}
ASPECTS = [('conjunction', 0, 8), ('sextile', 60, 5), ('square', 90, 7), ('trine', 120, 8), ('opposition', 180, 8)]
LUMINARIES = {'sun', 'moon'}


def pos(lon):
    lon %= 360.0
    i = int(lon // 30)
    d = lon - i * 30
    return {'lon': round(lon, 6), 'sign': SIGNS[i], 'deg': round(d, 6)}


def house_of(lon, cusps):
    for i in range(12):
        a, b = cusps[i], cusps[(i + 1) % 12]
        if a <= b:
            if a <= lon < b:
                return i + 1
        elif lon >= a or lon < b:
            return i + 1
    return 12


def compute(inp):
    t = datetime.strptime(inp['birth_utc'], '%Y-%m-%d %H:%M:%S')
    hour = t.hour + t.minute / 60 + t.second / 3600
    jd = swe.julday(t.year, t.month, t.day, hour)
    flags = swe.FLG_MOSEPH | swe.FLG_SPEED
    known = bool(inp.get('time_known', True))

    cusps = None
    asc = mc = None
    if known:
        c, ascmc = swe.houses_ex(jd, float(inp['lat']), float(inp['lon']), inp.get('house_system', 'P').encode(), 0)
        cusps = [x % 360 for x in c]
        asc, mc = ascmc[0] % 360, ascmc[1] % 360

    planets = []
    for key, body in BODIES:
        xx, _ = swe.calc_ut(jd, body, flags)
        p = pos(xx[0])
        p.update(key=key, speed=round(xx[3], 6), retro=xx[3] < 0)
        p['house'] = house_of(xx[0] % 360, cusps) if cusps else None
        planets.append(p)
    node_body = swe.TRUE_NODE if inp.get('node') == 'true' else swe.MEAN_NODE
    xx, _ = swe.calc_ut(jd, node_body, flags)
    nn = pos(xx[0])
    nn.update(key='north_node', speed=round(xx[3], 6), retro=xx[3] < 0)
    nn['house'] = house_of(xx[0] % 360, cusps) if cusps else None
    planets.append(nn)
    sn = pos(xx[0] + 180)
    sn.update(key='south_node', speed=round(xx[3], 6), retro=xx[3] < 0)
    sn['house'] = house_of((xx[0] + 180) % 360, cusps) if cusps else None
    planets.append(sn)
    xx, _ = swe.calc_ut(jd, swe.MEAN_APOG, flags)
    li = pos(xx[0])
    li.update(key='lilith', speed=round(xx[3], 6), retro=False)
    li['house'] = house_of(xx[0] % 360, cusps) if cusps else None
    planets.append(li)

    angles = None
    houses = None
    if known:
        angles = {'asc': pos(asc), 'mc': pos(mc), 'dsc': pos(asc + 180), 'ic': pos(mc + 180)}
        houses = {str(i + 1): pos(cusps[i]) for i in range(12)}

    # aspectos entre los 10 planetas y, si hay hora, el Ascendente y el MC
    pts = [(p['key'], p['lon']) for p in planets if p['key'] in dict(BODIES)]
    if known:
        pts += [('asc', asc), ('mc', mc)]
    aspects = []
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            a, b = pts[i], pts[j]
            diff = abs(a[1] - b[1]) % 360
            diff = min(diff, 360 - diff)
            for name, ang, orb in ASPECTS:
                allowed = orb + (2 if (a[0] in LUMINARIES or b[0] in LUMINARIES) else 0)
                if a[0] in ('asc', 'mc') or b[0] in ('asc', 'mc'):
                    allowed = min(allowed, 5)
                if abs(diff - ang) <= allowed:
                    aspects.append({'a': a[0], 'b': b[0], 'type': name, 'orb': round(abs(diff - ang), 3)})
                    break

    main_pts = [p for p in planets if p['key'] in dict(BODIES)]
    balance = {'elements': {k: 0 for k in ('fire', 'earth', 'air', 'water')}, 'modalities': {k: 0 for k in ('cardinal', 'fixed', 'mutable')}}
    for p in main_pts:
        balance['elements'][ELEMENT[p['sign']]] += 1
        balance['modalities'][MODALITY[p['sign']]] += 1

    return {
        'provider': 'astro-core', 'engine_version': 'pyswisseph ' + swe.version + ' / Moshier', 'jd_ut': round(jd, 6),
        'house_system': inp.get('house_system', 'P'), 'node_type': inp.get('node', 'mean'),
        'planets': planets, 'angles': angles, 'houses': houses, 'aspects': aspects, 'balance': balance,
        'moon_sign_certain': True, 'svg': None,
    }


def main():
    json.dump(compute(json.load(sys.stdin)), sys.stdout, ensure_ascii=False)


if __name__ == '__main__':
    main()
