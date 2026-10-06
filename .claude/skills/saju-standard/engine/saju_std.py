#!/usr/bin/env python3
"""saju-standard L1 계산 엔진.

설계: docs/saju-standard-design.md §2

  입력 시각 ─▶ IANA Asia/Seoul(서머타임·UTC+8:30) ─▶ UTC 순간
     ├─▶ UTC+8 환산 ─▶ lunar-python 절기 판정 ─▶ 연주·월주
     └─▶ LMT(경도) [+균시차] ─▶ 자시 모드 ─▶ 일주·시주

연·월주는 절대 순간으로, 일·시주는 출생지 지방시로 정한다. lunar-python의 절기 시각은
UTC+8 기준이므로 한국 시계 시각을 그대로 넣으면 절입 판정이 1시간 어긋난다.

CLI:
  python3 saju_std.py --date 1995-08-15 --time 14:30 --sex male
  python3 saju_std.py --date 1995-07-20 --calendar lunar --time 14:30 --sex female --place 부산
  python3 saju_std.py --stdin < input.json
"""

import argparse
import glob
import json
import math
import os
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, glob.glob(os.path.join(_HERE, "vendor", "lunar-python-*"))[0])
from lunar_python import Lunar, LunarYear, Solar  # noqa: E402

ENGINE_VERSION = "0.1.0"
KOREA_TZ = ZoneInfo("Asia/Seoul")
LIB_TZ = timezone(timedelta(hours=8))  # lunar-python 절기 시각 기준
SEOUL_LON = 126.978

# ── 기본 테이블 ─────────────────────────────────────────────────────────
STEMS = "甲乙丙丁戊己庚辛壬癸"
STEMS_KO = "갑을병정무기경신임계"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
BRANCHES_KO = "자축인묘진사오미신유술해"
ELEMENTS = "木火土金水"
ELEMENTS_KO = ["목", "화", "토", "금", "수"]
STEM_EL = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]
BRANCH_EL = [4, 2, 0, 0, 2, 1, 1, 2, 3, 3, 2, 4]
# 지장간 (여기, 중기, 정기) — 없는 자리는 None
HIDDEN = {
    0: (8, None, 9), 1: (9, 7, 5), 2: (4, 2, 0), 3: (0, None, 1),
    4: (1, 9, 4), 5: (4, 6, 2), 6: (2, 5, 3), 7: (3, 1, 5),
    8: (4, 8, 6), 9: (6, None, 7), 10: (7, 3, 4), 11: (4, 0, 8),
}
TEN_GODS = ["비견", "겁재", "식신", "상관", "편재", "정재", "편관", "정관", "편인", "정인"]
LIFE_STAGES = ["장생", "목욕", "관대", "건록", "제왕", "쇠", "병", "사", "묘", "절", "태", "양"]
LIFE_START = [11, 6, 2, 9, 2, 9, 5, 0, 8, 3]  # 일간별 장생 지지
ZISHI_MODES = ("yaja", "jeongja", "midnight")

# 출생지 경도 (시/도 대표 도시)
CITY_LON = {
    "서울": 126.978, "인천": 126.705, "수원": 127.029, "경기": 127.029, "춘천": 127.730, "강원": 128.168,
    "강릉": 128.876, "대전": 127.385, "세종": 127.289, "청주": 127.489, "충북": 127.489, "천안": 127.114,
    "충남": 126.800, "전주": 127.148, "전북": 127.148, "광주": 126.852, "전남": 126.463, "목포": 126.392,
    "대구": 128.601, "경북": 128.889, "포항": 129.343, "부산": 129.075, "울산": 129.311, "창원": 128.681,
    "경남": 128.681, "제주": 126.531, "평양": 125.754,
}


def gz_name(idx60):
    return STEMS[idx60 % 10] + BRANCHES[idx60 % 12]


def gz_ko(idx60):
    return STEMS_KO[idx60 % 10] + BRANCHES_KO[idx60 % 12]


def gz_index(stem, branch):
    """천간·지지 인덱스 → 60갑자 인덱스."""
    return (6 * stem - 5 * branch) % 60


def parse_gz(text):
    return gz_index(STEMS.index(text[0]), BRANCHES.index(text[1]))


# ── 1. 시간 정규화 ──────────────────────────────────────────────────────
def lunar_to_solar(y, m, d, leap):
    if leap and LunarYear.fromYear(y).getLeapMonth() != m:
        raise ValueError(f"{y}년에는 윤{m}월이 없습니다.")
    try:
        s = Lunar.fromYmd(y, -m if leap else m, d).getSolar()
    except Exception as e:  # 라이브러리는 범위 오류를 Exception으로 던진다
        raise ValueError(f"존재하지 않는 음력 날짜입니다: {e}") from None
    back = s.getLunar()
    if (back.getYear(), abs(back.getMonth()), back.getDay(), back.getMonth() < 0) != (y, m, d, bool(leap)):
        raise ValueError("존재하지 않는 음력 날짜입니다.")
    return date(s.getYear(), s.getMonth(), s.getDay())


def local_to_utc(naive, tz=KOREA_TZ):
    """법정 시각 → UTC. 서머타임 공백 시각은 앞으로 밀고, 중복 시각은 이른 쪽을 쓴다."""
    warnings = []
    a0 = naive.replace(tzinfo=tz, fold=0)
    a1 = naive.replace(tzinfo=tz, fold=1)
    utc = a0.astimezone(timezone.utc)
    if utc.astimezone(tz).replace(tzinfo=None) != naive:
        warnings.append("입력 시각이 서머타임 전환으로 존재하지 않는 시각이라 전환 후 시각으로 계산했습니다.")
    elif a0.utcoffset() != a1.utcoffset():
        warnings.append("입력 시각이 서머타임 종료로 두 번 존재하는 시각이라 앞선 시각으로 계산했습니다.")
    return utc, a0.utcoffset(), a0.dst(), warnings


def equation_of_time_min(dt_utc):
    """균시차(분, 진태양시 − 평균태양시). NOAA 근사, 오차 ±0.5분."""
    n = dt_utc.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1 + (dt_utc.hour - 12) / 24)
    return 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                     - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))


# ── 2. 기둥 계산 ────────────────────────────────────────────────────────
def _lib_lunar(utc):
    t = utc.astimezone(LIB_TZ)
    return Solar.fromYmdHms(t.year, t.month, t.day, t.hour, t.minute, t.second).getLunar()


def year_month_pillars(utc):
    lun = _lib_lunar(utc)
    return parse_gz(lun.getYearInGanZhiExact()), parse_gz(lun.getMonthInGanZhiExact())


def _jie_utc(jq):
    s = jq.getSolar()
    return datetime(s.getYear(), s.getMonth(), s.getDay(), s.getHour(), s.getMinute(), s.getSecond(),
                    tzinfo=LIB_TZ).astimezone(timezone.utc)


def surrounding_jie(utc):
    """출생 순간 직전·직후의 절(節) 이름과 UTC 순간."""
    lun = _lib_lunar(utc)
    prev, nxt = lun.getPrevJie(), lun.getNextJie()
    p, n = _jie_utc(prev), _jie_utc(nxt)
    if p > utc:  # 경계 순간 보정
        p = _jie_utc(_lib_lunar(utc - timedelta(days=1)).getPrevJie())
    if n <= utc:
        n = _jie_utc(_lib_lunar(utc + timedelta(days=1)).getNextJie())
    return (prev.getName(), p), (nxt.getName(), n)


def day_index(d):
    """양력 날짜 → 일주 60갑자 인덱스 (2000-01-01 = 戊午 = 54)."""
    return (d.toordinal() - date(2000, 1, 1).toordinal() + 54) % 60


def hour_branch(minutes):
    return ((minutes + 60) // 120) % 12


def hour_stem(day_idx, branch):
    return ((day_idx % 10) % 5 * 2 + branch) % 10


def day_hour_pillars(lmt, mode):
    """지방시 기준 일주·시주. mode: yaja | jeongja | midnight (설계서 §2.3)."""
    minutes = lmt.hour * 60 + lmt.minute
    br = hour_branch(minutes)
    d = lmt.date()
    if minutes >= 23 * 60:
        nxt = d + timedelta(days=1)
        day_d, base_d = {"yaja": (d, nxt), "jeongja": (nxt, nxt), "midnight": (d, d)}[mode]
    else:
        day_d = base_d = d
    di = day_index(day_d)
    return di, gz_index(hour_stem(day_index(base_d), br), br)


# ── 3. 파생값 ───────────────────────────────────────────────────────────
def ten_god(day_stem, other_stem):
    de, oe = STEM_EL[day_stem], STEM_EL[other_stem]
    rel = (oe - de) % 5  # 0 같음, 1 내가 생, 2 내가 극, 3 나를 극, 4 나를 생
    same = (day_stem % 2) == (other_stem % 2)
    return TEN_GODS[[0, 2, 4, 6, 8][rel] + (0 if same else 1)]


def main_hidden(branch):
    return HIDDEN[branch][2]


def life_stage(day_stem, branch):
    start = LIFE_START[day_stem]
    step = (branch - start) % 12 if day_stem % 2 == 0 else (start - branch) % 12
    return LIFE_STAGES[step]


def gongmang(day_idx):
    start = (day_idx % 12 - day_idx % 10) % 12
    return [(start + 10) % 12, (start + 11) % 12]


SAMHAP = [(8, 0, 4, 4), (2, 6, 10, 1), (5, 9, 1, 3), (11, 3, 7, 0)]  # (생,왕,고, 오행)
BANGHAP = [(2, 3, 4, 0), (5, 6, 7, 1), (8, 9, 10, 3), (11, 0, 1, 4)]
YUKHAP = {frozenset(p): el for p, el in [((0, 1), 2), ((2, 11), 0), ((3, 10), 1), ((4, 9), 3), ((5, 8), 4), ((6, 7), 1)]}
STEM_HAP = {frozenset(p): el for p, el in [((0, 5), 2), ((1, 6), 3), ((2, 7), 4), ((3, 8), 0), ((4, 9), 1)]}
STEM_CHUNG = [frozenset(p) for p in [(0, 6), (1, 7), (2, 8), (3, 9)]]
PA = [frozenset(p) for p in [(0, 9), (6, 3), (2, 11), (5, 8), (4, 1), (10, 7)]]
HAE = [frozenset(p) for p in [(0, 7), (1, 6), (2, 5), (3, 4), (8, 11), (9, 10)]]
HYEONG_SETS = [((2, 5, 8), "인사신 삼형"), ((1, 10, 7), "축술미 삼형")]
POS = ["연", "월", "일", "시"]


def interactions(stems, branches):
    out = []
    idx = [i for i in range(4) if stems[i] is not None]
    for a in idx:
        for b in idx:
            if a >= b:
                continue
            sa, sb, ba, bb = stems[a], stems[b], branches[a], branches[b]
            pair = f"{POS[a]}-{POS[b]}"
            k = frozenset((sa, sb))
            if k in STEM_HAP:
                out.append({"type": "천간합", "at": pair, "chars": STEMS[sa] + STEMS[sb], "element": ELEMENTS_KO[STEM_HAP[k]]})
            if k in STEM_CHUNG:
                out.append({"type": "천간충", "at": pair, "chars": STEMS[sa] + STEMS[sb]})
            kb = frozenset((ba, bb))
            if kb in YUKHAP:
                out.append({"type": "육합", "at": pair, "chars": BRANCHES[ba] + BRANCHES[bb], "element": ELEMENTS_KO[YUKHAP[kb]]})
            if (ba - bb) % 12 == 6:
                out.append({"type": "충", "at": pair, "chars": BRANCHES[ba] + BRANCHES[bb]})
            if kb in PA:
                out.append({"type": "파", "at": pair, "chars": BRANCHES[ba] + BRANCHES[bb]})
            if kb in HAE:
                out.append({"type": "해", "at": pair, "chars": BRANCHES[ba] + BRANCHES[bb]})
            if kb == frozenset((0, 3)):
                out.append({"type": "형", "at": pair, "chars": BRANCHES[ba] + BRANCHES[bb], "name": "자묘 상형"})
            if ba == bb and ba in (4, 6, 9, 11):
                out.append({"type": "형", "at": pair, "chars": BRANCHES[ba] * 2, "name": "자형"})
    present = set(branches[i] for i in idx)
    for sang, wang, go, el in SAMHAP:
        have = {sang, wang, go} & present
        if len(have) == 3:
            out.append({"type": "삼합", "chars": "".join(BRANCHES[x] for x in (sang, wang, go)), "element": ELEMENTS_KO[el]})
        elif len(have) == 2 and wang in have:
            out.append({"type": "반합", "chars": "".join(BRANCHES[x] for x in sorted(have)), "element": ELEMENTS_KO[el]})
    for a, b, c, el in BANGHAP:
        if {a, b, c} <= present:
            out.append({"type": "방합", "chars": BRANCHES[a] + BRANCHES[b] + BRANCHES[c], "element": ELEMENTS_KO[el]})
    for members, name in HYEONG_SETS:
        have = set(members) & present
        if len(have) >= 2:
            out.append({"type": "형", "chars": "".join(BRANCHES[x] for x in members if x in have), "name": name + ("" if len(have) == 3 else "(부분)")})
    return out


def sinsal(stems, branches, pillars60):
    ds = stems[2]
    known = [i for i in range(4) if branches[i] is not None]
    found = []

    def mark(name, targets, basis):
        for i in known:
            if branches[i] in targets:
                found.append({"name": name, "at": POS[i], "char": BRANCHES[branches[i]], "basis": basis})

    for base_pos in (0, 2):  # 연지·일지 기준
        b = branches[base_pos]
        for sang, wang, go, _ in SAMHAP:
            if b in (sang, wang, go):
                dohwa = {8: 9, 2: 3, 5: 6, 11: 0}[sang]
                yeokma = {8: 2, 2: 8, 5: 11, 11: 5}[sang]
                mark("도화살", {dohwa}, POS[base_pos] + "지")
                mark("역마살", {yeokma}, POS[base_pos] + "지")
                mark("화개살", {go}, POS[base_pos] + "지")
    cheoneul = {0: (1, 7), 4: (1, 7), 6: (1, 7), 1: (0, 8), 5: (0, 8), 2: (11, 9), 3: (11, 9), 7: (2, 6), 8: (5, 3), 9: (5, 3)}
    mark("천을귀인", set(cheoneul[ds]), "일간")
    munchang = {0: 5, 1: 6, 2: 8, 3: 9, 4: 8, 5: 9, 6: 11, 7: 0, 8: 2, 9: 3}
    mark("문창귀인", {munchang[ds]}, "일간")
    if ds % 2 == 0:
        mark("양인살", {{0: 3, 2: 6, 4: 6, 6: 9, 8: 0}[ds]}, "일간")
    if pillars60[2] in [parse_gz(x) for x in ("庚辰", "庚戌", "壬辰", "壬戌", "戊戌")]:
        found.append({"name": "괴강살", "at": "일", "char": gz_name(pillars60[2]), "basis": "일주"})
    baekho = {parse_gz(x) for x in ("甲辰", "乙未", "丙戌", "丁丑", "戊辰", "壬戌", "癸丑")}
    for i, p in enumerate(pillars60):
        if p is not None and p in baekho:
            found.append({"name": "백호살", "at": POS[i], "char": gz_name(p), "basis": "주"})
    uniq, seen = [], set()
    for f in found:
        key = (f["name"], f["at"])
        if key not in seen:
            seen.add(key)
            uniq.append(f)
    return uniq


def element_counts(stems, branches, hidden_weight=False):
    c = [0.0] * 5
    for s in stems:
        if s is not None:
            c[STEM_EL[s]] += 1
    for b in branches:
        if b is None:
            continue
        if hidden_weight:
            parts = [h for h in HIDDEN[b] if h is not None]
            weights = [0.3, 0.7] if len(parts) == 2 else [0.2, 0.2, 0.6]
            for h, w in zip(parts, weights):
                c[STEM_EL[h]] += w
        else:
            c[BRANCH_EL[b]] += 1
    return {ELEMENTS_KO[i]: round(c[i], 2) for i in range(5)}


def daewoon(utc, birth_local, year_stem, month60, sex, count=10):
    forward = (year_stem % 2 == 0) == (sex == "male")
    (pn, p), (nn, n) = surrounding_jie(utc)
    delta = (n - utc) if forward else (utc - p)
    days = delta.total_seconds() / 86400
    total_months = round(days * 4)  # 3일 = 1년 → 1일 = 4개월
    sy, sm = divmod(total_months, 12)
    start = birth_local + timedelta(days=round(days * 365.2422 / 3))
    items = []
    for k in range(1, count + 1):
        idx = (month60 + (k if forward else -k)) % 60
        items.append({"order": k, "pillar": gz_name(idx), "ko": gz_ko(idx), "age_from": sy + 10 * (k - 1),
                      "year_from": start.year + 10 * (k - 1)})
    return {"direction": "순행" if forward else "역행", "basis_jie": nn if forward else pn,
            "start_age": {"years": sy, "months": sm}, "start_date": start.date().isoformat(), "list": items}


def year_pillar_of(year):
    return (year - 4) % 60


# ── 4. 메인 계산 ────────────────────────────────────────────────────────
def compute(inp):
    """inp: date(YYYY-MM-DD), time(HH:MM|None), calendar(solar|lunar), leap(bool), sex(male|female|None),
    place(도시명) | longitude, eot(bool), zishi(yaja|jeongja|midnight), seun_years([int])."""
    warnings = []
    y, m, d = map(int, inp["date"].split("-"))
    cal = inp.get("calendar", "solar")
    if cal == "lunar":
        sd = lunar_to_solar(y, m, d, inp.get("leap", False))
    else:
        sd = date(y, m, d)
    time_known = bool(inp.get("time"))
    hh, mm = map(int, inp["time"].split(":")) if time_known else (12, 0)
    if not time_known:
        warnings.append("태어난 시각 미상: 시주를 비우고 정오 기준으로 연·월·일주를 계산했습니다.")

    if inp.get("longitude") is not None:
        lon, lon_src = float(inp["longitude"]), "직접 입력"
    elif inp.get("place"):
        if inp["place"] not in CITY_LON:
            raise ValueError(f"알 수 없는 출생지: {inp['place']} (경도를 직접 입력하세요)")
        lon, lon_src = CITY_LON[inp["place"]], inp["place"]
    else:
        lon, lon_src = SEOUL_LON, "서울(기본값)"
    use_eot = bool(inp.get("eot", False))
    mode = inp.get("zishi", "yaja")
    if mode not in ZISHI_MODES:
        raise ValueError(f"zishi는 {ZISHI_MODES} 중 하나여야 합니다.")

    naive = datetime(sd.year, sd.month, sd.day, hh, mm)
    utc, offset, dst, tw = local_to_utc(naive)
    warnings += tw
    eot = equation_of_time_min(utc)
    lmt = (utc + timedelta(minutes=lon * 4 + (eot if use_eot else 0))).replace(tzinfo=None)

    yi, mi = year_month_pillars(utc)
    if time_known:
        di, hi = day_hour_pillars(lmt, mode)
    else:
        di, hi = day_index(sd), None
    pillars = [yi, mi, di, hi]
    stems = [p % 10 if p is not None else None for p in pillars]
    branches = [p % 12 if p is not None else None for p in pillars]
    ds = stems[2]

    # 경계 경고
    alternatives = {}
    (pn, p_utc), (nn, n_utc) = surrounding_jie(utc)
    for name, t in ((pn, p_utc), (nn, n_utc)):
        gap = abs((utc - t).total_seconds()) / 60
        if gap <= 30:
            before = year_month_pillars(t - timedelta(minutes=1))
            after = year_month_pillars(t + timedelta(minutes=1))
            warnings.append(f"절입({name}) {gap:.0f}분 거리: 출생 시각 오차에 따라 연·월주가 바뀔 수 있습니다.")
            alternatives["jie"] = {"name": name, "at_kst": t.astimezone(KOREA_TZ).strftime("%Y-%m-%d %H:%M"),
                                   "before": [gz_name(x) for x in before], "after": [gz_name(x) for x in after]}
    if time_known:
        minutes = lmt.hour * 60 + lmt.minute + lmt.second / 60
        to_edge = min((minutes - 60) % 120, 120 - (minutes - 60) % 120)
        if to_edge <= 15:
            warnings.append(f"시 경계 {to_edge:.0f}분 거리: 출생 시각·경도 오차에 따라 시주가 바뀔 수 있습니다.")
            alt = []
            for shift in (-16, 16):
                _, h2 = day_hour_pillars(lmt + timedelta(minutes=shift), mode)
                if h2 != hi:
                    alt.append(gz_name(h2))
            alternatives["hour"] = alt
        if lmt.hour == 23 or lmt.hour == 0:
            alternatives["zishi"] = {mm_: dict(zip(("day", "hour"), map(gz_name, day_hour_pillars(lmt, mm_))))
                                     for mm_ in ZISHI_MODES}
            warnings.append(f"자시 구간: 학파에 따라 일주·시주가 달라집니다(적용: {mode}).")

    def pillar_info(i):
        p = pillars[i]
        if p is None:
            return None
        s, b = p % 10, p % 12
        return {
            "pillar": gz_name(p), "ko": gz_ko(p),
            "stem": {"char": STEMS[s], "ko": STEMS_KO[s], "element": ELEMENTS_KO[STEM_EL[s]], "yin": s % 2 == 1,
                     "ten_god": "일간" if i == 2 else ten_god(ds, s)},
            "branch": {"char": BRANCHES[b], "ko": BRANCHES_KO[b], "element": ELEMENTS_KO[BRANCH_EL[b]],
                       "ten_god": ten_god(ds, main_hidden(b)),
                       "hidden": [STEMS[h] for h in HIDDEN[b] if h is not None],
                       "life_stage": life_stage(ds, b)},
        }

    result = {
        "engine": {"name": "saju-standard", "version": ENGINE_VERSION},
        "input": {"date": inp["date"], "calendar": cal, "leap": bool(inp.get("leap", False)),
                  "time": inp.get("time"), "sex": inp.get("sex"), "zishi": mode},
        "time": {
            "solar_date": sd.isoformat(),
            "utc_offset_hours": offset.total_seconds() / 3600, "dst": bool(dst),
            "utc": utc.strftime("%Y-%m-%d %H:%M"),
            "longitude": lon, "longitude_source": lon_src,
            "equation_of_time_min": round(eot, 1), "eot_applied": use_eot,
            "local_solar_time": lmt.strftime("%Y-%m-%d %H:%M"),
            "prev_jie": {"name": pn, "kst": p_utc.astimezone(KOREA_TZ).strftime("%Y-%m-%d %H:%M")},
            "next_jie": {"name": nn, "kst": n_utc.astimezone(KOREA_TZ).strftime("%Y-%m-%d %H:%M")},
        },
        "pillars": {k: pillar_info(i) for i, k in enumerate(("year", "month", "day", "hour"))},
        "day_master": {"char": STEMS[ds], "ko": STEMS_KO[ds], "element": ELEMENTS_KO[STEM_EL[ds]], "yin": ds % 2 == 1},
        "elements": {"visible": element_counts(stems, branches), "with_hidden": element_counts(stems, branches, True)},
        "gongmang": [BRANCHES[x] for x in gongmang(di)],
        "interactions": interactions(stems, branches),
        "sinsal": sinsal(stems, branches, pillars),
        "alternatives": alternatives,
        "warnings": warnings,
    }
    sex = inp.get("sex")
    if sex in ("male", "female"):
        result["daewoon"] = daewoon(utc, naive, stems[0], mi, sex)
    else:
        warnings.append("성별 미상: 대운(순행/역행)을 계산하지 않았습니다.")
    seun = inp.get("seun_years") or []
    result["seun"] = [{"year": yy, "pillar": gz_name(year_pillar_of(yy)), "ko": gz_ko(year_pillar_of(yy)),
                       "stem_ten_god": ten_god(ds, year_pillar_of(yy) % 10),
                       "branch_ten_god": ten_god(ds, main_hidden(year_pillar_of(yy) % 12))} for yy in seun]
    return result


def summary_line(r):
    p = r["pillars"]
    cols = [p[k]["pillar"] if p[k] else "□□" for k in ("hour", "day", "month", "year")]
    return "시 일 월 연: " + " ".join(cols)


def main(argv=None):
    ap = argparse.ArgumentParser(description="saju-standard 계산 엔진")
    ap.add_argument("--stdin", action="store_true", help="표준입력 JSON")
    ap.add_argument("--date")
    ap.add_argument("--time", help="HH:MM (모르면 생략)")
    ap.add_argument("--calendar", default="solar", choices=["solar", "lunar"])
    ap.add_argument("--leap", action="store_true", help="음력 윤달")
    ap.add_argument("--sex", choices=["male", "female"])
    ap.add_argument("--place", help="출생지 (예: 서울, 부산)")
    ap.add_argument("--longitude", type=float)
    ap.add_argument("--eot", action="store_true", help="균시차 적용")
    ap.add_argument("--zishi", default="yaja", choices=ZISHI_MODES)
    ap.add_argument("--seun", default="", help="세운 연도들, 쉼표 구분 (예: 2026,2027)")
    ap.add_argument("--brief", action="store_true", help="한 줄 요약만 출력")
    a = ap.parse_args(argv)
    if a.stdin:
        inp = json.load(sys.stdin)
    else:
        if not a.date:
            ap.error("--date 가 필요합니다")
        inp = {"date": a.date, "time": a.time, "calendar": a.calendar, "leap": a.leap, "sex": a.sex,
               "place": a.place, "longitude": a.longitude, "eot": a.eot, "zishi": a.zishi,
               "seun_years": [int(x) for x in a.seun.split(",") if x.strip()]}
    try:
        r = compute(inp)
    except ValueError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 2
    print(summary_line(r) if a.brief else json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
