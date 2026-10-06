#!/usr/bin/env python3
"""saju-standard L1 검증 세트 (설계서 §5.1).

  T1  절입 경계: 1900~2050 DE421 절입 순간 ±1분에서 연·월주 전환 (1,812절 × 2)
  T2  일주 연속성: 1900~2099 전 일자, 자체 산술 vs lunar-python
  T3  독립 재계산: 무작위 시각에서 연·월주를 DE421 절기표로 다시 계산해 대조
  T4  역사적 시간대: 서머타임·UTC+8:30·공백/중복 시각
  T5  음력 변환: 1900~2099 전 일자 왕복 + 알려진 윤달·명절
  T6  자시 모드: yaja / jeongja / midnight
  Y26 2026년: KASI 절입표 대조, 절입 ±2분 출생, 2026 전 일자 × 12시진 전수

사용: python3 run_tests.py [--quick]
"""
import bisect
import json
import os
import random
import sys
import time
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))
import saju_std as S  # noqa: E402
from lunar_python import Solar  # noqa: E402

QUICK = "--quick" in sys.argv
JIE_BRANCH = {"小寒": 1, "立春": 2, "惊蛰": 3, "清明": 4, "立夏": 5, "芒种": 6,
              "小暑": 7, "立秋": 8, "白露": 9, "寒露": 10, "立冬": 11, "大雪": 0}
UTC = timezone.utc

results = []


def report(name, ok, total, detail=""):
    results.append((name, ok, total, detail))
    mark = "PASS" if ok == total else "FAIL"
    print(f"[{mark}] {name}: {ok}/{total} {detail}", flush=True)


def parse_utc(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


DE = [(parse_utc(x["utc"]), x["name"]) for x in json.load(open(os.path.join(HERE, "data", "jie_de421.json")))["jie"]]
DE_T = [t for t, _ in DE]


def expected_year_month(utc):
    """DE421 절기표만으로 연·월주를 독립 계산."""
    i = bisect.bisect_right(DE_T, utc) - 1
    branch = JIE_BRANCH[DE[i][1]]
    j = i
    while DE[j][1] != "立春":
        j -= 1
    y = DE[j][0].astimezone(S.KOREA_TZ).year
    yi = S.year_pillar_of(y)
    first = ((yi % 10) % 5 * 2 + 2) % 10
    stem = (first + (branch - 2) % 12) % 10
    return yi, S.gz_index(stem, branch)


# ── T1 ──────────────────────────────────────────────────────────────────
def t1():
    ok = total = 0
    worst = []
    diffs = []
    for t, name in DE[1:]:
        b = JIE_BRANCH[name]
        for delta, exp_b in ((-60, (b - 1) % 12), (60, b)):
            total += 1
            _, mi = S.year_month_pillars(t + timedelta(seconds=delta))
            if mi % 12 == exp_b:
                ok += 1
            elif len(worst) < 5:
                worst.append(f"{name} {t.isoformat()} {delta:+d}s")
        (_, lib_t), _ = S.surrounding_jie(t + timedelta(hours=2))
        diffs.append(abs((lib_t - t).total_seconds()))
    diffs.sort()
    report("T1 절입 ±1분 월주 전환", ok, total,
           f"| lib vs DE421 오차 중앙 {diffs[len(diffs)//2]:.0f}s, 최대 {diffs[-1]:.0f}s" + (f" | 예: {worst}" if worst else ""))
    # 입춘 연주 전환
    ok = total = 0
    for t, name in DE[1:]:
        if name != "立春":
            continue
        y = t.astimezone(S.KOREA_TZ).year
        for delta, exp in ((-60, S.year_pillar_of(y - 1)), (60, S.year_pillar_of(y))):
            total += 1
            yi, _ = S.year_month_pillars(t + timedelta(seconds=delta))
            ok += yi == exp
    report("T1 입춘 ±1분 연주 전환", ok, total)


# ── T2 + T5 ─────────────────────────────────────────────────────────────
def t2_t5():
    d, end = date(1900, 1, 1), date(2099, 12, 31)
    step = 7 if QUICK else 1
    ok2 = ok5 = total = 0
    bad2, bad5 = [], []
    while d <= end:
        total += 1
        lun = Solar.fromYmd(d.year, d.month, d.day).getLunar()
        if S.gz_name(S.day_index(d)) == lun.getDayInGanZhi():
            ok2 += 1
        elif len(bad2) < 3:
            bad2.append(d.isoformat())
        try:
            back = S.lunar_to_solar(lun.getYear(), abs(lun.getMonth()), lun.getDay(), lun.getMonth() < 0)
            ok5 += back == d
        except ValueError as e:
            if len(bad5) < 3:
                bad5.append(f"{d}: {e}")
        d += timedelta(days=step)
    report("T2 일주 자체산술=lunar-python", ok2, total, str(bad2) if bad2 else "")
    report("T5 음력 왕복 변환", ok5, total, str(bad5) if bad5 else "")
    known = [  # (음력 y, m, d, 윤달, 기대 양력)
        (2026, 1, 1, False, "2026-02-17"),   # 2026 설날
        (2026, 8, 15, False, "2026-09-25"),  # 2026 추석
        (2025, 1, 1, False, "2025-01-29"),   # 2025 설날
        (2024, 8, 15, False, "2024-09-17"),  # 2024 추석
        (2023, 2, 1, True, "2023-03-22"),    # 2023 윤2월
        (2025, 6, 1, True, "2025-07-25"),    # 2025 윤6월
        (2020, 4, 1, True, "2020-05-23"),    # 2020 윤4월
    ]
    ok = 0
    bad = []
    for y, m, dd, leap, exp in known:
        got = S.lunar_to_solar(y, m, dd, leap).isoformat()
        ok += got == exp
        if got != exp:
            bad.append(f"{y}-{m}-{dd}{'(윤)' if leap else ''}: {got}≠{exp}")
    report("T5 알려진 음력 날짜", ok, len(known), str(bad) if bad else "")
    errs = 0
    for y, m, dd, leap in [(2023, 3, 1, True), (2024, 1, 30, False), (2023, 2, 30, True)]:
        try:
            S.lunar_to_solar(y, m, dd, leap)
        except ValueError:
            errs += 1
    report("T5 존재하지 않는 음력 거부", errs, 3)


# ── T3 ──────────────────────────────────────────────────────────────────
def t3():
    rng = random.Random(20261006)
    n = 2000 if QUICK else 100000
    lo = datetime(1900, 2, 10, tzinfo=UTC).timestamp()
    hi = datetime(2050, 12, 1, tzinfo=UTC).timestamp()
    ok = 0
    bad = []
    for _ in range(n):
        utc = datetime.fromtimestamp(rng.uniform(lo, hi), UTC).replace(microsecond=0)
        got = S.year_month_pillars(utc)
        exp = expected_year_month(utc)
        if got == exp:
            ok += 1
        elif len(bad) < 5:
            bad.append(f"{utc.isoformat()} got {list(map(S.gz_name, got))} exp {list(map(S.gz_name, exp))}")
    report("T3 무작위 연·월주 vs DE421 독립 재계산", ok, n, str(bad) if bad else "")


# ── T4 ──────────────────────────────────────────────────────────────────
def t4():
    cases = [
        # (입력, 검사 함수, 설명)
        ({"date": "1955-01-15", "time": "07:10"}, lambda r: r["pillars"]["hour"]["pillar"] == "壬辰" and r["time"]["utc_offset_hours"] == 8.5, "UTC+8:30 시기 서울 진태양시 辰시"),
        ({"date": "1988-07-15", "time": "07:50", "longitude": 135}, lambda r: r["pillars"]["hour"]["pillar"] == "辛卯" and r["time"]["dst"], "1988 서머타임 반영 卯시"),
        ({"date": "1958-06-15", "time": "06:50"}, lambda r: r["time"]["utc_offset_hours"] == 9.5, "1958 서머타임(+9:30)"),
        ({"date": "1987-05-10", "time": "02:30"}, lambda r: any("존재하지 않는" in w for w in r["warnings"]), "1987 서머타임 시작 공백 시각 경고"),
        ({"date": "1988-10-09", "time": "02:30"}, lambda r: any("두 번" in w for w in r["warnings"]), "1988 서머타임 종료 중복 시각 경고"),
        ({"date": "1961-08-10", "time": "00:15"}, lambda r: any("존재하지 않는" in w for w in r["warnings"]), "1961 +8:30→+9 전환 공백 시각 경고"),
        ({"date": "1990-07-01", "time": "12:00"}, lambda r: not r["time"]["dst"] and r["time"]["utc_offset_hours"] == 9, "1990 서머타임 없음"),
    ]
    ok = 0
    bad = []
    for inp, check, desc in cases:
        r = S.compute(inp)
        if check(r):
            ok += 1
        else:
            bad.append(desc)
    report("T4 역사적 시간대", ok, len(cases), str(bad) if bad else "")


# ── T6 ──────────────────────────────────────────────────────────────────
def t6():
    d = date(2026, 3, 10)
    nd = d + timedelta(days=1)
    di, ndi = S.day_index(d), S.day_index(nd)
    zi = 0  # 子
    exp = {
        "yaja": (di, S.gz_index(S.hour_stem(ndi, zi), zi)),
        "jeongja": (ndi, S.gz_index(S.hour_stem(ndi, zi), zi)),
        "midnight": (di, S.gz_index(S.hour_stem(di, zi), zi)),
    }
    ok = 0
    for mode, (ed, eh) in exp.items():
        r = S.compute({"date": "2026-03-10", "time": "23:30", "longitude": 135, "zishi": mode})
        ok += r["pillars"]["day"]["pillar"] == S.gz_name(ed) and r["pillars"]["hour"]["pillar"] == S.gz_name(eh)
    for mode in S.ZISHI_MODES:  # 00:30은 모든 모드에서 당일 일주
        r = S.compute({"date": "2026-03-11", "time": "00:30", "longitude": 135, "zishi": mode})
        ok += r["pillars"]["day"]["pillar"] == S.gz_name(ndi) and r["pillars"]["hour"]["pillar"] == S.gz_name(S.gz_index(S.hour_stem(ndi, 0), 0))
    report("T6 자시 모드", ok, 6)
    # 시진 경계: 서울 경도 보정 후 07:00 경계
    r1 = S.compute({"date": "2026-03-10", "time": "07:31", "longitude": 135})
    r2 = S.compute({"date": "2026-03-10", "time": "06:59", "longitude": 135})
    report("T6 시진 경계(07:00)", int(r1["pillars"]["hour"]["branch"]["char"] == "辰") + int(r2["pillars"]["hour"]["branch"]["char"] == "卯"), 2)


# ── 2026 ────────────────────────────────────────────────────────────────
def y2026():
    kasi = json.load(open(os.path.join(HERE, "data", "kasi_jie_2026.json")))["jie"]
    ok = 0
    worst = 0
    for k in kasi:
        kst = datetime.strptime(k["kst"], "%Y-%m-%d %H:%M").replace(tzinfo=S.KOREA_TZ).astimezone(UTC)
        de = next(t for t, n in DE if n == k["name"] and t.astimezone(S.KOREA_TZ).year == 2026)
        (_, lib), _ = S.surrounding_jie(de + timedelta(hours=2))
        d1 = abs((de - kst).total_seconds())
        d2 = abs((lib - kst).total_seconds())
        worst = max(worst, d1, d2)
        ok += d1 < 60 and d2 < 60
    report("Y26 KASI 2026 절입표 = DE421 = 엔진(1분 이내)", ok, len(kasi), f"| 최대 차이 {worst:.0f}s")

    # 절입 ±2분 출생 (서울, KST 입력)
    month_names = {"小寒": ("戊子", "己丑", "乙巳", "乙巳"), "立春": ("己丑", "庚寅", "乙巳", "丙午")}
    seq = ["庚寅", "辛卯", "壬辰", "癸巳", "甲午", "乙未", "丙申", "丁酉", "戊戌", "己亥", "庚子"]
    names = ["立春", "惊蛰", "清明", "立夏", "芒种", "小暑", "立秋", "白露", "寒露", "立冬", "大雪"]
    for i in range(1, len(names)):
        month_names[names[i]] = (seq[i - 1], seq[i], "丙午", "丙午")
    ok = total = 0
    bad = []
    for k in kasi:
        t = datetime.strptime(k["kst"], "%Y-%m-%d %H:%M")
        bm, am, by, ay = month_names[k["name"]]
        for shift, em, ey in ((-2, bm, by), (2, am, ay)):
            tt = t + timedelta(minutes=shift)
            r = S.compute({"date": tt.strftime("%Y-%m-%d"), "time": tt.strftime("%H:%M")})
            total += 1
            got = (r["pillars"]["month"]["pillar"], r["pillars"]["year"]["pillar"])
            if got == (em, ey) and "jie" in r["alternatives"]:
                ok += 1
            else:
                bad.append(f"{k['name']} {shift:+d}분: {got} ≠ {(em, ey)}")
    report("Y26 절입 ±2분 출생 연·월주 + 경계경고", ok, total, str(bad[:4]) if bad else "")

    # 오늘(2026-10-06): 독립 엔진(destiny) 출력 丙午년 丁酉월 癸丑일과 대조
    r = S.compute({"date": "2026-10-06", "time": "12:00"})
    got = tuple(r["pillars"][k]["pillar"] for k in ("year", "month", "day"))
    report("Y26 2026-10-06 = 丙午 丁酉 癸丑", int(got == ("丙午", "丁酉", "癸丑")), 1, "" if got == ("丙午", "丁酉", "癸丑") else str(got))

    # 2026 전 일자 × 12시진 전수: 연·월주 DE421 독립 재계산 대조 + 일·시주 규칙 검사
    ok = total = 0
    bad = []
    d = date(2026, 1, 1)
    while d.year == 2026:
        for h in range(0, 24, 2):
            total += 1
            r = S.compute({"date": d.isoformat(), "time": f"{h:02d}:30", "sex": "male" if h % 4 else "female",
                           "seun_years": [2026]})
            utc = datetime.strptime(r["time"]["utc"], "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
            ey, em = expected_year_month(utc)
            lmt = datetime.strptime(r["time"]["local_solar_time"], "%Y-%m-%d %H:%M")
            exp_h = S.hour_branch(lmt.hour * 60 + lmt.minute)
            p = r["pillars"]
            good = (p["year"]["pillar"] == S.gz_name(ey) and p["month"]["pillar"] == S.gz_name(em)
                    and p["hour"]["branch"]["char"] == S.BRANCHES[exp_h]
                    and len(r["daewoon"]["list"]) == 10 and r["seun"][0]["pillar"] == "丙午")
            ok += good
            if not good and len(bad) < 3:
                bad.append(f"{d} {h:02d}:30")
        d += timedelta(days=1)
    report("Y26 2026 전 일자×12시진 전수", ok, total, str(bad) if bad else "")


if __name__ == "__main__":
    t0 = time.time()
    for fn in (t1, t2_t5, t3, t4, t6, y2026):
        fn()
    total_ok = sum(r[1] for r in results)
    total = sum(r[2] for r in results)
    failed = [r[0] for r in results if r[1] != r[2]]
    print(f"\n합계 {total_ok}/{total} 통과, 실패 항목 {len(failed)}개, {time.time() - t0:.0f}s")
    sys.exit(1 if failed else 0)
