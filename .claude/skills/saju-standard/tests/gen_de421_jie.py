#!/usr/bin/env python3
"""JPL DE421 천체력으로 1900~2050년 12절(節) 절입 순간(UTC)을 계산해 tests/data/jie_de421.json 으로 저장.

엔진(lunar-python)과 독립된 기준값이다. 개발용 스크립트라 skyfield, skyfield-data 가 필요하다:
  python3 -m venv venv && venv/bin/pip install skyfield skyfield-data
  python3 gen_de421_jie.py [venv/lib/python3.X/site-packages]
"""
import json
import os
import sys

if len(sys.argv) > 1:
    sys.path.insert(0, sys.argv[1])

from skyfield.api import Loader  # noqa: E402
from skyfield.framelib import ecliptic_frame  # noqa: E402
from skyfield.searchlib import find_discrete  # noqa: E402
from skyfield_data import get_skyfield_data_path  # noqa: E402

# 태양 황경 → 절 이름 (월지 시작)
JIE = {285: "小寒", 315: "立春", 345: "惊蛰", 15: "清明", 45: "立夏", 75: "芒种",
       105: "小暑", 135: "立秋", 165: "白露", 195: "寒露", 225: "立冬", 255: "大雪"}

load = Loader(get_skyfield_data_path(), expire=False)
ts = load.timescale(builtin=True)
eph = load("de421.bsp")
earth, sun = eph["earth"], eph["sun"]


def segment(t):
    lon = earth.at(t).observe(sun).apparent().frame_latlon(ecliptic_frame)[1].degrees
    return (lon // 15).astype(int)


segment.step_days = 5

out = []
t0, t1 = ts.utc(1900, 1, 2), ts.utc(2050, 12, 31)
times, values = find_discrete(t0, t1, segment)
for t, v in zip(times, values):
    deg = int(v) * 15
    if deg in JIE:
        out.append({"name": JIE[deg], "deg": deg, "utc": t.utc_strftime("%Y-%m-%dT%H:%M:%SZ")})

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "jie_de421.json")
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
    json.dump({"source": "JPL DE421 via skyfield, apparent geocentric ecliptic longitude of date",
               "count": len(out), "jie": out}, f, ensure_ascii=False, indent=0)
print(len(out), "jie written to", path)
