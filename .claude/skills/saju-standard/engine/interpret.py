#!/usr/bin/env python3
"""saju-standard L2 해석 결정론 모듈 (설계서 §3).

감명 순서: 일간·월령 → 강약(억부) → 조후 → 격국 → 용신 결정 → 운의 길흉.
결정론 판단만 JSON으로 내고, 문장 서술은 LLM이 이 결과와 references/interpretation-standard.md 만
근거로 쓴다. 원전 태그: [적천수] 억부 [궁통보감] 조후 [자평진전] 격국·상신.

CLI:
  python3 interpret.py --date 1995-08-15 --time 14:30 --sex male      # L1+L2
  python3 saju_std.py ... | python3 interpret.py --stdin               # L1 JSON 입력
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import saju_std as S  # noqa: E402

# 오행 관계 (e: 0木 1火 2土 3金 4水)
def produces(e):  # e가 생하는 오행
    return (e + 1) % 5


def controls(e):  # e가 극하는 오행
    return (e + 2) % 5


def mother(e):  # e를 생하는 오행
    return (e - 1) % 5


def controller(e):  # e를 극하는 오행
    return (e - 2) % 5


GROUP_NAMES = {"비겁": 0, "식상": 1, "재성": 2, "관성": 3, "인성": 4}


def group_of(dm_el, el):
    """일간 오행 기준 십신군 이름."""
    return ["비겁", "식상", "재성", "관성", "인성"][(el - dm_el) % 5]


def group_el(dm_el, group):
    return (dm_el + GROUP_NAMES[group]) % 5


# 위치 가중치 [연간, 연지, 월간, 월지, 일지, 시간, 시지] — 월지(월령) 최대
WEIGHTS = {"ys": 10, "yb": 10, "ms": 10, "mb": 30, "db": 15, "hs": 10, "hb": 15}

ROK = [2, 3, 5, 6, 5, 6, 8, 9, 11, 0]          # 일간별 건록 지지
YANGIN = {0: 3, 2: 6, 4: 6, 6: 9, 8: 0}       # 양간 양인 지지

# [궁통보감] 일간 × 월지 조후 용신 (우선순위 순). 子=0 … 亥=11. verify:원전
JOHU = {
    0: {2: "丙癸", 3: "庚丙丁戊己", 4: "庚丁壬", 5: "癸丁庚", 6: "癸丁庚", 7: "癸丁庚", 8: "庚丁壬", 9: "庚丁丙", 10: "庚甲丁壬癸", 11: "庚丁丙戊", 0: "丁庚丙", 1: "丁庚丙"},
    1: {2: "丙癸", 3: "丙癸", 4: "癸丙戊", 5: "癸", 6: "癸丙", 7: "癸丙", 8: "丙癸己", 9: "癸丙丁", 10: "癸辛", 11: "丙戊", 0: "丙", 1: "丙"},
    2: {2: "壬庚", 3: "壬己", 4: "壬甲", 5: "壬癸庚", 6: "壬庚", 7: "壬庚", 8: "壬戊", 9: "壬癸", 10: "甲壬", 11: "甲戊庚壬", 0: "壬戊己", 1: "壬甲"},
    3: {2: "甲庚", 3: "庚甲", 4: "甲庚", 5: "甲庚", 6: "壬庚癸", 7: "甲壬庚", 8: "甲庚丙戊", 9: "甲庚丙戊", 10: "甲庚戊", 11: "甲庚", 0: "甲庚", 1: "甲庚"},
    4: {2: "丙甲癸", 3: "丙甲癸", 4: "甲丙癸", 5: "甲丙癸", 6: "壬甲丙", 7: "癸丙甲", 8: "丙癸甲", 9: "丙癸", 10: "甲丙癸", 11: "甲丙", 0: "丙甲", 1: "丙甲"},
    5: {2: "丙庚甲", 3: "甲癸丙", 4: "丙癸甲", 5: "癸丙", 6: "癸丙", 7: "癸丙", 8: "丙癸", 9: "丙癸", 10: "甲丙癸", 11: "丙甲戊", 0: "丙甲戊", 1: "丙甲戊"},
    6: {2: "戊甲壬丙丁", 3: "丁甲庚丙", 4: "甲丁壬癸", 5: "壬戊丙丁", 6: "壬癸", 7: "丁甲", 8: "丁甲", 9: "丁甲丙", 10: "甲壬", 11: "丁丙", 0: "丁甲丙", 1: "丙丁甲"},
    7: {2: "己壬庚", 3: "壬甲", 4: "壬甲", 5: "壬甲癸", 6: "壬己癸", 7: "壬庚甲", 8: "壬甲戊", 9: "壬甲", 10: "壬甲", 11: "壬丙", 0: "丙戊壬甲", 1: "丙壬戊己"},
    8: {2: "庚丙戊", 3: "戊辛庚", 4: "甲庚", 5: "壬辛庚癸", 6: "癸庚辛", 7: "辛甲", 8: "戊丁", 9: "甲庚", 10: "甲丙", 11: "戊丙庚", 0: "戊丙", 1: "丙丁甲"},
    9: {2: "辛丙", 3: "庚辛", 4: "丙辛甲", 5: "辛", 6: "庚辛壬癸", 7: "庚辛壬癸", 8: "丁", 9: "辛丙", 10: "辛甲壬癸", 11: "庚辛戊丁", 0: "丙辛", 1: "丙丁"},
}

SANGSIN = {  # [자평진전] 격국별 상신(相神) 십신군
    "정관격": ["재성", "인성"], "편관격": ["식상", "인성"], "정재격": ["식상", "관성"], "편재격": ["식상", "관성"],
    "정인격": ["관성"], "편인격": ["관성", "재성"], "식신격": ["재성"], "상관격": ["재성", "인성"],
    "건록격": ["관성", "재성"], "양인격": ["관성"], "월겁격": ["관성", "재성"],
}


def _chart(stems, branches):
    """stems/branches: [연,월,일,시] 인덱스, 시는 None 가능."""
    ds = stems[2]
    dm = S.STEM_EL[ds]
    pos = [("ys", stems[0], True), ("yb", branches[0], False), ("ms", stems[1], True), ("mb", branches[1], False),
           ("db", branches[2], False), ("hs", stems[3], True), ("hb", branches[3], False)]
    items = []
    for key, v, is_stem in pos:
        if v is None:
            continue
        el = S.STEM_EL[v] if is_stem else S.STEM_EL[S.main_hidden(v)]
        items.append((key, v, is_stem, el))
    return ds, dm, items


def weighted_elements(stems, branches):
    """지장간 가중 오행 분포 (천간 1, 지지 지장간 0.2/0.2/0.6 또는 0.3/0.7)."""
    c = [0.0] * 5
    for s in stems:
        if s is not None:
            c[S.STEM_EL[s]] += 1
    for b in branches:
        if b is None:
            continue
        parts = [h for h in S.HIDDEN[b] if h is not None]
        ws = [0.3, 0.7] if len(parts) == 2 else [0.2, 0.2, 0.6]
        for h, w in zip(parts, ws):
            c[S.STEM_EL[h]] += w
    return c


def strength(stems, branches):
    """[적천수] 억부: 득령·득지·득세 + 위치 가중 점수(0~100)."""
    ds, dm, items = _chart(stems, branches)
    sup = lambda el: el == dm or el == mother(dm)  # noqa: E731
    total = sum(WEIGHTS[k] for k, *_ in items)
    score = sum(WEIGHTS[k] for k, _, _, el in items if sup(el)) * 100 / total
    month_el = next(el for k, _, _, el in items if k == "mb")
    day_el = next(el for k, _, _, el in items if k == "db")
    others = [el for k, _, _, el in items if k not in ("mb", "db")]
    deuk_ryeong = sup(month_el)
    deuk_ji = sup(day_el)
    deuk_se = sum(map(sup, others)) * 2 >= len(others)
    # 통근: 지지 지장간 어디에든 일간 오행 또는 인성 오행이 있는가
    rooted = any(S.STEM_EL[h] in (dm, mother(dm)) for b in branches if b is not None for h in S.HIDDEN[b] if h is not None)
    if score >= 80:
        grade = "극신강"
    elif score >= 60:
        grade = "신강"
    elif score >= 40:
        grade = "중화"
    elif score >= 20:
        grade = "신약"
    else:
        grade = "극신약"
    return {"score": round(score, 1), "grade": grade, "strong": score >= 50,
            "deuk_ryeong": deuk_ryeong, "deuk_ji": deuk_ji, "deuk_se": deuk_se, "rooted": rooted}


def johu(stems, branches):
    """[궁통보감] 조후."""
    ds, mb = stems[2], branches[1]
    need_stems = JOHU[ds][mb]
    first_el = S.STEM_EL[S.STEMS.index(need_stems[0])]
    c = weighted_elements(stems, branches)
    climate = "한" if mb in (11, 0, 1) else "난" if mb in (5, 6, 7) else "온"
    need_el = 1 if climate == "한" else 4 if climate == "난" else None
    priority = mb in (0, 1, 6, 7) and need_el is not None and c[need_el] < 1.0
    present = [ch for ch in need_stems if S.STEMS.index(ch) in [s for s in stems if s is not None]
               or any(S.STEMS.index(ch) in [h for h in S.HIDDEN[b] if h is not None] for b in branches if b is not None)]
    return {"climate": climate, "table_stems": list(need_stems), "first_element": S.ELEMENTS_KO[first_el],
            "first_element_idx": first_el, "present": present, "priority": priority,
            "basis": f"[궁통보감] {S.STEMS[ds]}일간 {S.BRANCHES[mb]}월 → {'·'.join(need_stems)}"}


def gyeokguk(stems, branches):
    """[자평진전] 월지 기준 격국 + 성패."""
    ds, dm, items = _chart(stems, branches)
    mb = branches[1]
    visible = [s for i, s in enumerate(stems) if s is not None and i != 2]
    vis_groups = [group_of(dm, S.STEM_EL[s]) for s in visible]
    vis_gods = [S.ten_god(ds, s) for s in visible]

    if mb == ROK[ds]:
        name, basis = "건록격", f"월지 {S.BRANCHES[mb]} = 일간 건록"
    elif ds in YANGIN and mb == YANGIN[ds]:
        name, basis = "양인격", f"월지 {S.BRANCHES[mb]} = 일간 양인"
    elif S.STEM_EL[S.main_hidden(mb)] == dm:
        name, basis = "월겁격", f"월지 정기가 일간과 같은 오행"
    else:
        hidden = [h for h in (S.HIDDEN[mb][2], S.HIDDEN[mb][1], S.HIDDEN[mb][0]) if h is not None]
        out = next((h for h in hidden if h in visible and S.STEM_EL[h] != dm), None)
        pick = out if out is not None else S.HIDDEN[mb][2]
        god = S.ten_god(ds, pick)
        name = god + "격"
        basis = f"월지 {S.BRANCHES[mb]} 지장간 {S.STEMS[pick]}" + (" 투출" if out is not None else " 정기(미투출)")

    has = lambda g: g in vis_groups  # noqa: E731
    god_has = lambda g: g in vis_gods  # noqa: E731
    status, reason = "성격", []
    if name == "정관격":
        if god_has("상관") and not has("인성"):
            status, reason = "파격", ["상관견관(인성 구제 없음)"]
        elif god_has("편관"):
            status, reason = "파격", ["관살혼잡"]
        else:
            reason = ["재·인 보좌" if (has("재성") or has("인성")) else "관 단독"]
    elif name == "편관격":
        if has("식상") or has("인성"):
            reason = ["식신제살" if god_has("식신") or god_has("상관") else "살인상생"]
        elif has("재성"):
            status, reason = "파격", ["재생살(제화 없음)"]
        else:
            status, reason = "미정", ["제화 미비"]
    elif name in ("정재격", "편재격"):
        if vis_groups.count("비겁") >= 2 and not (has("식상") or has("관성")):
            status, reason = "파격", ["군겁쟁재"]
        else:
            reason = ["식상생재" if has("식상") else "재왕생관" if has("관성") else "재 단독"]
    elif name in ("정인격", "편인격"):
        if has("재성") and not has("관성"):
            status, reason = "파격", ["재극인"]
        else:
            reason = ["관인상생" if has("관성") else "인 단독"]
    elif name == "식신격":
        if god_has("편인") and not has("재성"):
            status, reason = "파격", ["효신탈식(도식)"]
        else:
            reason = ["식신생재" if has("재성") else "식신 단독"]
    elif name == "상관격":
        if god_has("정관") and not has("인성"):
            status, reason = "파격", ["상관견관"]
        else:
            reason = ["상관생재" if has("재성") else "상관패인" if has("인성") else "상관 단독"]
    else:  # 건록·양인·월겁
        if has("관성"):
            reason = ["관살로 제어"]
        elif has("재성") or has("식상"):
            reason = ["재·식상으로 설기"]
        else:
            status, reason = "미정", ["제어·설기 부족"]
    sangsin = SANGSIN[name]
    return {"name": name, "basis": basis, "status": status, "reason": reason, "sangsin_groups": sangsin,
            "sangsin_elements": [S.ELEMENTS_KO[group_el(dm, g)] for g in sangsin], "tag": "[자평진전]"}


def eokbu_yongsin(stems, branches, st):
    """[적천수] 억부 용신."""
    ds, dm, _ = _chart(stems, branches)
    c = weighted_elements(stems, branches)
    grp = {g: c[group_el(dm, g)] for g in GROUP_NAMES}
    if st["strong"]:
        if grp["인성"] > grp["비겁"]:
            g, why = "재성", "인성 과다 → 재성으로 인성 제어"
        elif grp["관성"] < 0.8:
            g, why = ("관성", "비겁 과다 → 관성으로 제어") if grp["재성"] >= 0.8 else ("식상", "비겁 과다 → 식상으로 설기")
        else:
            g, why = "관성", "비겁 과다 → 관성으로 제어"
    else:
        heavy = max(("식상", "재성", "관성"), key=lambda k: grp[k])
        if heavy == "재성":
            g, why = "비겁", "재성 과다 → 비겁으로 감당"
        else:
            g, why = "인성", f"{heavy} 과다 → 인성으로 {'설기 차단' if heavy == '식상' else '살인상생'}"
    return g, why


def yongsin(stems, branches, st, jh, gk):
    """§3.1 5단계 용신 결정."""
    ds, dm, _ = _chart(stems, branches)
    c = weighted_elements(stems, branches)
    eb_group, eb_why = eokbu_yongsin(stems, branches, st)
    eb_el = group_el(dm, eb_group)
    jong = None
    if st["score"] >= 85 and not any(group_of(dm, S.STEM_EL[s]) == "관성" for s in stems if s is not None):
        jong = ("종왕격", dm, "일간 세력 극단·관살 무투 → 비겁 순종")
    elif st["score"] <= 15 and not st["rooted"]:
        top = max(("식상", "재성", "관성"), key=lambda g: c[group_el(dm, g)])
        jong = ({"식상": "종아격", "재성": "종재격", "관성": "종살격"}[top], group_el(dm, top), f"무근·극약 → {top} 순종")
    if jong:
        chosen, method, why = jong[1], "종격", jong[2]
    elif jh["priority"]:
        chosen, method, why = jh["first_element_idx"], "조후", "한난 극단 + 조후 오행 부족 → 조후 우선"
    else:
        chosen, method, why = eb_el, "억부", eb_why
    sangsin_els = [group_el(dm, g) for g in gk["sangsin_groups"]]
    agree = sum([chosen == eb_el, chosen == jh["first_element_idx"], chosen in sangsin_els])
    confidence = "높음" if agree >= 2 else "보통" if agree == 1 else "낮음"
    return {
        "element": S.ELEMENTS_KO[chosen], "element_idx": chosen, "group": group_of(dm, chosen),
        "method": method, "reason": why, "confidence": confidence,
        "huisin": S.ELEMENTS_KO[mother(chosen)], "gisin": S.ELEMENTS_KO[controller(chosen)],
        "jong": jong[0] if jong else None,
        "candidates": {
            "억부": {"element": S.ELEMENTS_KO[eb_el], "group": eb_group, "reason": eb_why, "tag": "[적천수]"},
            "조후": {"element": jh["first_element"], "stems": jh["table_stems"], "tag": "[궁통보감]"},
            "격국상신": {"elements": [S.ELEMENTS_KO[e] for e in sangsin_els], "groups": gk["sangsin_groups"], "tag": "[자평진전]"},
        },
    }


def luck_rating(dm, ys, pillar60):
    """운 간지의 길흉: 용신·희신 +, 기신 −, 그 외 0. 천간 40%, 지지 60%."""
    s_el = S.STEM_EL[pillar60 % 10]
    b_el = S.STEM_EL[S.main_hidden(pillar60 % 12)]
    def val(el):
        if el == ys:
            return 2
        if el == mother(ys):
            return 1
        if el == controller(ys):
            return -2
        if el == produces(ys):
            return -1  # 용신을 설기
        return 0
    v = 0.4 * val(s_el) + 0.6 * val(b_el)
    return round(v, 2), "길" if v >= 0.8 else "흉" if v <= -0.8 else "평"


def interpret_core(stems, branches):
    st = strength(stems, branches)
    jh = johu(stems, branches)
    gk = gyeokguk(stems, branches)
    ys = yongsin(stems, branches, st, jh, gk)
    return {"strength": st, "johu": jh, "gyeokguk": gk, "yongsin": ys}


def ten_god_distribution(stems, branches):
    ds = stems[2]
    out = {}
    for i, s in enumerate(stems):
        if s is not None and i != 2:
            g = S.ten_god(ds, s)
            out[g] = out.get(g, 0) + 1
    for b in branches:
        if b is not None:
            g = S.ten_god(ds, S.main_hidden(b))
            out[g] = out.get(g, 0) + 1
    return out


def interpret(l1):
    """L1 결과 JSON → L2 해석 JSON."""
    p = l1["pillars"]
    order = ("year", "month", "day", "hour")
    stems = [S.STEMS.index(p[k]["stem"]["char"]) if p[k] else None for k in order]
    branches = [S.BRANCHES.index(p[k]["branch"]["char"]) if p[k] else None for k in order]
    core = interpret_core(stems, branches)
    dm = S.STEM_EL[stems[2]]
    ys = core["yongsin"]["element_idx"]
    core["ten_god_distribution"] = ten_god_distribution(stems, branches)
    core["palace"] = {"연주": "조상·초년(~19세)", "월주": "부모·형제·사회(20~39세)", "일주": "본인·배우자(40~59세)", "시주": "자녀·말년(60세~)"}
    if "daewoon" in l1:
        core["daewoon_rating"] = []
        for d in l1["daewoon"]["list"]:
            idx = S.parse_gz(d["pillar"])
            v, label = luck_rating(dm, ys, idx)
            core["daewoon_rating"].append({"pillar": d["pillar"], "age_from": d["age_from"], "score": v, "rating": label})
    core["seun_rating"] = []
    for s in l1.get("seun", []):
        v, label = luck_rating(dm, ys, S.parse_gz(s["pillar"]))
        core["seun_rating"].append({"year": s["year"], "pillar": s["pillar"], "score": v, "rating": label})
    return core


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--stdin" in argv:
        l1 = json.load(sys.stdin)
    else:
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = S.main(argv)
        if code:
            print(buf.getvalue())
            return code
        l1 = json.loads(buf.getvalue())
    print(json.dumps({"l1": l1, "l2": interpret(l1)}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
