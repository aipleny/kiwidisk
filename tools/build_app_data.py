#!/usr/bin/env python3
"""브라우저 엔진(app/saju-engine.js)용 달력 데이터 생성 → app/data/calendar.json

- jie:   12절 절입 순간 [UTC 초, 월지 인덱스] 1899~2101 (lunar-python, UTC+8 → UTC 환산)
- lunar: 음력 월 [월 시작일(1970-01-01 기준 일수), 음력 연, 월, 윤달 0/1, 일수] 1900~2100
- tz:    Asia/Seoul 오프셋 전환 [UTC 초, 오프셋 초] 1900~2100 (서머타임·UTC+8:30 포함)
- johu:  궁통보감 조후표 (references/johu-qiongtong.json 의 stems·conditional·evidence)
"""
import glob
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, ".claude", "skills", "saju-standard")
sys.path.insert(0, glob.glob(os.path.join(SKILL, "engine", "vendor", "lunar-python-*"))[0])
from lunar_python import Solar  # noqa: E402

UTC = timezone.utc
CST = timezone(timedelta(hours=8))
JIE_BRANCH = {"小寒": 1, "立春": 2, "惊蛰": 3, "清明": 4, "立夏": 5, "芒种": 6,
              "小暑": 7, "立秋": 8, "白露": 9, "寒露": 10, "立冬": 11, "大雪": 0}
EPOCH = date(1970, 1, 1)


def jie_table():
    seen = {}
    for y in range(1899, 2102):
        for k, s in Solar.fromYmd(y, 6, 1).getLunar().getJieQiTable().items():
            if k in JIE_BRANCH:
                t = datetime(s.getYear(), s.getMonth(), s.getDay(), s.getHour(), s.getMinute(), s.getSecond(), tzinfo=CST)
                seen[int(t.timestamp())] = JIE_BRANCH[k]
    return sorted([t, b] for t, b in seen.items())


def lunar_table():
    out = []
    d, end = date(1900, 1, 31), date(2101, 1, 1)
    prev = None
    while d < end:
        lun = Solar.fromYmd(d.year, d.month, d.day).getLunar()
        key = (lun.getYear(), lun.getMonth())
        if key != prev:
            if out:
                out[-1][4] = (d - EPOCH).days - out[-1][0]
            out.append([(d - EPOCH).days, lun.getYear(), abs(lun.getMonth()), 1 if lun.getMonth() < 0 else 0, 0])
            prev = key
        d += timedelta(days=1)
    out[-1][4] = (end - EPOCH).days - out[-1][0]
    return out


def tz_table():
    z = ZoneInfo("Asia/Seoul")
    off = lambda ts: int(datetime.fromtimestamp(ts, UTC).astimezone(z).utcoffset().total_seconds())  # noqa: E731
    t = int(datetime(1900, 1, 1, tzinfo=UTC).timestamp())
    end = int(datetime(2100, 12, 31, tzinfo=UTC).timestamp())
    cur = off(t)
    out = [[t, cur]]
    step = 6 * 3600
    while t < end:
        n = t + step
        if off(n) != cur:
            lo, hi = t, n
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if off(mid) == cur:
                    lo = mid
                else:
                    hi = mid
            cur = off(hi)
            out.append([hi, cur])
        t = n
    return out


if __name__ == "__main__":
    johu = json.load(open(os.path.join(SKILL, "references", "johu-qiongtong.json"), encoding="utf-8"))
    data = {
        "generated": datetime.now(UTC).strftime("%Y-%m-%d"),
        "jie": jie_table(),
        "lunar": lunar_table(),
        "tz": tz_table(),
        "johu": {k: {"stems": v["stems"], "conditional": v["conditional"], "evidence": v["evidence"]}
                 for k, v in johu["cells"].items()},
    }
    path = os.path.join(ROOT, "app", "data", "calendar.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print({k: len(v) for k, v in data.items() if isinstance(v, (list, dict))}, os.path.getsize(path), "bytes")
