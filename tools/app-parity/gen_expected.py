#!/usr/bin/env python3
"""Python 엔진 결과를 기대값으로 저장 → compare.js 가 JS 엔진과 대조.
사용: python3 gen_expected.py [N] > /tmp/expected.json
"""
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, ".claude", "skills", "saju-standard", "engine"))
import interpret as I  # noqa: E402
import mbti_layer as M  # noqa: E402
import saju_std as S  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
rng = random.Random(20261007)
cal = json.load(open(os.path.join(ROOT, "app", "data", "calendar.json"), encoding="utf-8"))
places = list(S.CITY_LON) + [None, None, None]
types = [a + b + c + d for a in "EI" for b in "SN" for c in "TF" for d in "JP"]


def rand_case():
    inp = {"sex": rng.choice(["male", "female", None]), "zishi": rng.choice(S.ZISHI_MODES), "place": rng.choice(places),
           "eot": rng.random() < 0.1, "seun_years": [2026, 2027], "mbti": rng.choice(types) + rng.choice(["", "", "-A", "-T"])}
    kind = rng.random()
    if kind < 0.15:  # 음력
        while True:
            y, m, d = rng.randint(1901, 2099), rng.randint(1, 12), rng.randint(1, 30)
            leap = rng.random() < 0.1
            try:
                S.lunar_to_solar(y, m, d, leap)
                break
            except ValueError:
                continue
        inp.update({"date": f"{y:04d}-{m:02d}-{d:02d}", "calendar": "lunar", "leap": leap})
        inp["time"] = None if rng.random() < 0.1 else f"{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}"
    elif kind < 0.35:  # 절입 경계 ±3분
        t, _ = rng.choice(cal["jie"])
        k = datetime.fromtimestamp(t, timezone.utc) + timedelta(hours=9, minutes=rng.randint(-3, 3))
        if k.year < 1901 or k.year > 2099:
            return rand_case()
        inp.update({"date": k.strftime("%Y-%m-%d"), "time": k.strftime("%H:%M"), "calendar": "solar"})
    elif kind < 0.45:  # 역사적 시간대·자시
        y = rng.choice([1908, 1912, 1948, 1949, 1950, 1951, 1954, 1955, 1957, 1960, 1961, 1987, 1988])
        d = datetime(y, 1, 1) + timedelta(days=rng.randint(0, 364))
        inp.update({"date": d.strftime("%Y-%m-%d"), "time": f"{rng.choice([0, 1, 2, 3, 22, 23])}:{rng.randint(0, 59):02d}".zfill(5), "calendar": "solar"})
    else:
        d = datetime(1901, 1, 1) + timedelta(days=rng.randint(0, 72000))
        inp.update({"date": d.strftime("%Y-%m-%d"), "calendar": "solar",
                    "time": None if rng.random() < 0.1 else f"{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}"})
    return inp


out = []
for _ in range(N):
    inp = rand_case()
    l1 = S.compute(inp)
    l2 = I.interpret(l1)
    t = M.parse_type(inp["mbti"])
    exp = {"l1": l1, "l2": l2, "mbti": {"stack": M.cognitive_stack(t), "compare": M.compare(t, l2, l1)["axes"],
                                       "timing": M.timing(t, l1, l2)["periods"]}}
    out.append({"input": inp, "expected": exp})
json.dump(out, sys.stdout, ensure_ascii=False)
