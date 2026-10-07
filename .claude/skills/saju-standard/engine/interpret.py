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

# [궁통보감] 일간 × 월지 조후 용신 (우선순위 순). 원문 대조본: references/johu-qiongtong.json
_JOHU_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "johu-qiongtong.json")
_JOHU_CELLS = json.load(open(_JOHU_PATH, encoding="utf-8"))["cells"]
JOHU = {S.STEMS.index(k[0]): {} for k in _JOHU_CELLS}
JOHU_COND = {S.STEMS.index(k[0]): {} for k in _JOHU_CELLS}
for _k, _v in _JOHU_CELLS.items():
    JOHU[S.STEMS.index(_k[0])][S.BRANCHES.index(_k[1])] = _v["stems"]
    JOHU_COND[S.STEMS.index(_k[0])][S.BRANCHES.index(_k[1])] = _v["conditional"]

SANGSIN = {  # [자평진전] 격국별 상신(相神) 십신군 — 원전 대조(references/gyeokguk-ziping.json)
    "정관격": ["재성", "인성"], "편관격": ["식상", "인성"], "정재격": ["식상", "관성"], "편재격": ["식상", "관성"],
    "정인격": ["관성", "비겁"], "편인격": ["관성", "비겁"], "식신격": ["재성", "비겁"], "상관격": ["재성", "인성"],
    "건록격": ["관성", "재성", "식상"], "양인격": ["관성"], "월겁격": ["관성", "재성", "식상"],
}
GYEOK_STATUS = ("성격", "성격(하)", "대기", "파격", "미정")  # 성격(하)=격은 서나 격이 낮음, 대기=带忌(성격이나 꺼리는 것이 섞임)


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
    cell = _JOHU_CELLS[S.STEMS[ds] + S.BRANCHES[mb]]
    return {"climate": climate, "table_stems": list(need_stems), "conditional_stems": list(cell["conditional"]),
            "evidence": cell["evidence"], "first_element": S.ELEMENTS_KO[first_el],
            "first_element_idx": first_el, "present": present, "priority": priority,
            "basis": f"[궁통보감] {S.STEMS[ds]}일간 {S.BRANCHES[mb]}월 → {'·'.join(need_stems)}"}


def gyeokguk(stems, branches, st=None):
    """[자평진전] 취격 + 성패(救应·带忌·刑冲). 근거 인용은 references/gyeokguk-ziping.json."""
    ds, dm, _ = _chart(stems, branches)
    mb = branches[1]
    vis = [(i, s) for i, s in enumerate(stems) if s is not None and i != 2]
    vis_stems = [s for _, s in vis]

    def merged(i, s):  # 다른 천간(일간 제외)과 오합되어 묶였는가
        return any(j != i and frozenset((s, t)) in S.STEM_HAP for j, t in vis)

    def god_free(name):  # 해당 십신이 투출해 있고 합으로 묶이지 않음
        return any(S.ten_god(ds, s) == name and not merged(i, s) for i, s in vis)

    def god_any(name):
        return any(S.ten_god(ds, s) == name for _, s in vis)

    def grp(name, free=True):
        return any(group_of(dm, S.STEM_EL[s]) == name and (not free or not merged(i, s)) for i, s in vis)

    def grp_count(name):
        return sum(group_of(dm, S.STEM_EL[s]) == name for _, s in vis)

    present = [b for b in branches if b is not None]
    # ── 취격 ──
    also = []
    if mb == ROK[ds]:
        name, basis = "건록격", f"월지 {S.BRANCHES[mb]} = 일간 건록"
    elif ds in YANGIN and mb == YANGIN[ds]:
        name, basis = "양인격", f"월지 {S.BRANCHES[mb]} = 일간 양인"
    else:
        name = None
        for sang, wang, go, el in S.SAMHAP:  # 会支: 월지를 포함한 삼합이 온전하면 격이 변한다
            if mb in (sang, wang, go) and {sang, wang, go} <= set(present) and el != dm:
                name = S.ten_god(ds, S.main_hidden(wang)) + "격"
                basis = f"월지 {S.BRANCHES[mb]} 포함 {''.join(S.BRANCHES[x] for x in (sang, wang, go))} 삼합 {S.ELEMENTS_KO[el]}국으로 변격"
                break
        if name is None:
            order = [h for h in (S.HIDDEN[mb][2], S.HIDDEN[mb][1], S.HIDDEN[mb][0]) if h is not None]
            out = [h for h in order if h in vis_stems]
            pick = out[0] if out else S.HIDDEN[mb][2]
            name = "월겁격" if S.STEM_EL[pick] == dm else S.ten_god(ds, pick) + "격"
            basis = f"월지 {S.BRANCHES[mb]} 지장간 {S.STEMS[pick]}" + (" 투출" if out else " 정기(미투출)")
            also = [S.ten_god(ds, h) + "격" for h in out[1:] if S.STEM_EL[h] != dm]

    # ── 성패 ──
    status, reason = "성격", []
    if name == "정관격":
        if god_free("편관"):
            status, reason = "파격", ["관살혼잡"]
        elif god_free("상관"):
            if grp("인성"):
                status, reason = ("파격", ["상관견관, 인성으로 구했으나 재가 인을 깨뜨림"]) if grp("재성") else ("성격", ["상관견관을 인성이 구함(官逢伤而透印以解之)"])
            else:
                status, reason = "파격", ["상관견관"]
        elif any(S.ten_god(ds, s) == "정관" and merged(i, s) for i, s in vis):
            status, reason = "대기", ["정관이 합으로 묶임"]
        elif grp("재성") or grp("인성"):
            reason = ["재·인이 관을 돕고 지킴(官喜透财以相生, 生印以护官)"]
        else:
            status, reason = "성격(하)", ["고관(孤官): 재·인 보좌 없음"]
        if god_any("편관") and not god_free("편관"):
            reason.append("편관이 합으로 제거됨(合杀留官)")
    elif name == "편관격":
        yangin_branch = ds in YANGIN and YANGIN[ds] in present
        if god_free("정관"):
            status, reason = "대기", ["관살혼잡: 관이나 살 중 하나를 걸러야 맑아짐(取清)"]
        elif grp("식상"):
            if grp("인성") and not grp("재성"):
                status, reason = "대기", ["식신제살 위에 인성이 식신을 누름(七煞逢食制而又逢印)"]
            else:
                reason = ["식신제살"]
        elif grp("인성"):
            status, reason = ("파격", ["살인상생인데 재가 인을 깨뜨림"]) if grp("재성") else ("성격", ["살인상생"])
        elif yangin_branch:
            reason = ["양인이 칠살을 대적(用刃当煞)"]
        elif grp("재성"):
            status, reason = "파격", ["칠살이 재를 만나 제어 없음(七煞逢财无制)"]
        else:
            status, reason = "미정", ["제화 없음"]
    elif name in ("정재격", "편재격"):
        if god_free("편관"):
            status, reason = ("성격", ["재투칠살을 식신이 제어"]) if grp("식상") else ("파격", ["재투칠살(财透七煞)"])
        elif grp_count("비겁") >= 2:
            if grp("식상"):
                reason = ["재봉겁을 식상이 화함(财逢劫而透食以化之)"]
            elif grp("관성"):
                reason = ["재봉겁을 관이 제어(生官以制之)"]
            else:
                status, reason = "파격", ["군겁쟁재(财轻比重)"]
        elif grp("관성") and grp("식상"):
            status, reason = "대기", ["재왕생관에 식상이 섞임(露食则杂)"]
        else:
            reason = ["식상생재" if grp("식상") else "재왕생관" if grp("관성") else "재 단독"]
    elif name in ("정인격", "편인격"):
        if st is not None and st["strong"] and god_free("편관"):
            status, reason = "파격", ["신강 인중에 칠살 투출(身强印重而透煞)"]
        elif grp("재성"):
            if grp("비겁") or not grp("재성", free=True) or grp_count("인성") > grp_count("재성"):
                reason = ["재가 인을 치나 겁재·합·인다로 구함(印逢财而劫财以解之)"]
            elif grp("관성"):
                status, reason = "성격(하)", ["재극인을 관이 통관"]
            else:
                status, reason = "파격", ["재극인"]
        elif grp("관성"):
            reason = ["관인상생(印喜官煞以相生)"]
        elif grp("비겁"):
            reason = ["겁재가 인을 보호(劫才以护印)"]
        else:
            status, reason = "성격(하)", ["인 단독"]
    elif name == "식신격":
        if grp("인성"):
            if grp("재성"):
                reason = ["재가 인을 제어해 식신을 보호(生财以护食)"]
            elif god_free("편관"):
                reason = ["효신을 만났으나 칠살을 취해 격을 이룸(就煞以成格)"]
            else:
                status, reason = "파격", ["효신탈식(정인·편인 모두 夺食)"]
        elif grp("재성") and god_free("편관"):
            status, reason = "파격", ["식신생재에 칠살 투출(生财露煞)"]
        elif god_free("편관"):
            reason = ["식신제살"]
        elif grp("재성"):
            reason = ["식신생재"]
        else:
            status, reason = "성격(하)", ["식신 단독"]
    elif name == "상관격":
        jinsu = ds in (6, 7) and mb in (11, 0)
        if god_free("정관"):
            if jinsu:
                reason = ["금수상관은 관을 기뻐함(金水独宜)"]
            elif grp("인성"):
                status, reason = "성격(하)", ["상관견관을 인성이 구함"]
            else:
                status, reason = "파격", ["상관견관(伤官非金水而见官)"]
        elif grp("재성") and god_free("편관"):
            status, reason = "파격", ["상관생재에 칠살 투출"]
        elif grp("인성") and grp("재성"):
            status, reason = "대기", ["상관패인에 재가 섞임"]
        elif grp("재성"):
            reason = ["상관생재(生财以化伤)"]
        elif grp("인성"):
            reason = ["상관패인(佩印以制伏)"]
        elif god_free("편관"):
            reason = ["상관가살"]
        else:
            status, reason = "미정", ["재·인 없음"]
    elif name == "양인격":
        if not grp("관성"):
            if grp("재성") and grp("식상"):
                status, reason = "성격(하)", ["관살 없이 재와 식상으로 씀(财根深而用伤食)"]
            else:
                status, reason = "파격", ["양인무관살(阳刃无官煞, 刃格败也)"]
        elif grp("식상") and not grp("인성"):
            status, reason = "파격", ["관살을 식상이 제거"]
        else:
            reason = ["관살이 양인을 제어(阳刃喜官煞以制伏)"]
    else:  # 건록격·월겁격
        if god_free("정관") and god_free("편관"):
            status, reason = "대기", ["관살혼잡: 取清 필요"]
        elif god_free("정관"):
            if god_free("상관"):
                status, reason = "파격", ["용관에 상관 투출"]
            elif grp("재성") or grp("인성"):
                reason = ["용관에 재·인 보좌(透官而逢财印)"]
            else:
                status, reason = "성격(하)", ["고관"]
        elif god_free("편관"):
            if grp("식상"):
                reason = ["용살에 제복(透煞而遇制伏)"]
            elif grp("재성"):
                status, reason = "파격", ["용살에 재가 살을 생함"]
            else:
                status, reason = "미정", ["칠살 제복 필요"]
        elif grp("재성"):
            status, reason = ("성격", ["용재에 식상(禄劫用财, 须带食伤)"]) if grp("식상") else ("성격(하)", ["용재에 식상 없음"])
        elif grp("식상"):
            reason = ["식상 설기(亦为秀气)"]
        elif grp("인성"):
            status, reason = "파격", ["재관 없이 인만 투출"]
        else:
            status, reason = "미정", ["재·관·식상 없음"]

    # 월령 형충 (辰戌·丑未는 冲动이라 제외)
    clash = [i for i in (0, 2, 3) if branches[i] is not None and (branches[i] - mb) % 12 == 6]
    if clash and frozenset((mb, branches[clash[0]])) not in (frozenset((4, 10)), frozenset((1, 7))):
        others = [b for i, b in enumerate(branches) if b is not None and i != 1]
        rescued = any(frozenset((mb, b)) in S.YUKHAP for b in others) or any(
            mb in (sg, wg, gg) and wg in {mb, *others} and len({sg, wg, gg} & {mb, *others}) >= 2
            and any(b in (sg, wg, gg) for b in others) for sg, wg, gg, _ in S.SAMHAP)
        cb = S.BRANCHES[branches[clash[0]]] + S.BRANCHES[mb]
        if rescued:
            reason.append(f"월령 충({cb})을 합이 풀어 줌(三合六合可以解之)")
        elif status in ("성격", "성격(하)", "대기"):
            status = "파격"
            reason.append(f"월령 충({cb})으로 파격(刑冲用神, 尤为破格)")
    sangsin = SANGSIN[name]
    return {"name": name, "basis": basis, "also": also, "status": status, "reason": reason, "sangsin_groups": sangsin,
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
    huisin = mother(chosen)
    supportive = (dm, mother(dm))
    if method == "억부" and not st["strong"] and huisin not in supportive:
        # 신약에서 용신의 어머니가 관성이면(살인상생) 그 관성이 바로 병이므로, 다른 생부 오행을 희신으로
        huisin = dm if chosen == mother(dm) else mother(dm)
    elif method == "억부" and st["strong"] and huisin in supportive:
        # 신강에서 식상 용신의 어머니(비겁)는 일간을 더 키우므로, 용신이 생하는 오행을 희신으로
        huisin = produces(chosen)
    return {
        "element": S.ELEMENTS_KO[chosen], "element_idx": chosen, "group": group_of(dm, chosen),
        "method": method, "reason": why, "confidence": confidence,
        "huisin": S.ELEMENTS_KO[huisin], "huisin_idx": huisin,
        "gisin": S.ELEMENTS_KO[controller(chosen)], "gisin_idx": controller(chosen),
        "strong": st["strong"],
        "jong": jong[0] if jong else None,
        "candidates": {
            "억부": {"element": S.ELEMENTS_KO[eb_el], "group": eb_group, "reason": eb_why, "tag": "[적천수]"},
            "조후": {"element": jh["first_element"], "stems": jh["table_stems"], "tag": "[궁통보감]"},
            "격국상신": {"elements": [S.ELEMENTS_KO[e] for e in sangsin_els], "groups": gk["sangsin_groups"], "tag": "[자평진전]"},
        },
    }


def luck_rating(dm, ysd, pillar60):
    """운 간지의 길흉. 천간 40%, 지지(정기) 60%.
    용신 +2, 희신 +1, 기신(용신을 극함) −2. 억부로 정한 경우 강약 방향에 거스르는 오행 −1
    (신약인데 식상·재·관, 신강인데 비겁·인성), 그 외 0."""
    ys, hs, gs = ysd["element_idx"], ysd["huisin_idx"], ysd["gisin_idx"]
    supportive = (dm, mother(dm))

    def val(el):
        if el == ys:
            return 2
        if el == hs:
            return 1
        if el == gs:
            return -2
        if ysd["method"] == "억부" and ((el in supportive) == ysd["strong"]):
            return -1
        return 0
    s_el = S.STEM_EL[pillar60 % 10]
    b_el = S.STEM_EL[S.main_hidden(pillar60 % 12)]
    v = 0.4 * val(s_el) + 0.6 * val(b_el)
    return round(v, 2), "길" if v >= 0.8 else "흉" if v <= -0.8 else "평"


def natal_relations(stems, branches, pillar60):
    """운 간지가 원국 각 기둥과 맺는 천간합·충, 지지 육합·충·형·파·해, 반합."""
    ls, lb = pillar60 % 10, pillar60 % 12
    out = []
    for i in range(4):
        s, b = stems[i], branches[i]
        if s is None:
            continue
        pos = S.POS[i] + "주"
        if frozenset((ls, s)) in S.STEM_HAP:
            out.append(f"{pos} 천간합({S.STEMS[ls]}{S.STEMS[s]})")
        if frozenset((ls, s)) in S.STEM_CHUNG:
            out.append(f"{pos} 천간충({S.STEMS[ls]}{S.STEMS[s]})")
        kb = frozenset((lb, b))
        if kb in S.YUKHAP:
            out.append(f"{pos} 육합({S.BRANCHES[lb]}{S.BRANCHES[b]})")
        if (lb - b) % 12 == 6:
            out.append(f"{pos} 충({S.BRANCHES[lb]}{S.BRANCHES[b]})")
        if kb in S.PA:
            out.append(f"{pos} 파({S.BRANCHES[lb]}{S.BRANCHES[b]})")
        if kb in S.HAE:
            out.append(f"{pos} 해({S.BRANCHES[lb]}{S.BRANCHES[b]})")
        if kb == frozenset((0, 3)) or (lb != b and any({lb, b} <= set(m) for m, _ in S.HYEONG_SETS)):
            out.append(f"{pos} 형({S.BRANCHES[lb]}{S.BRANCHES[b]})")
        for sang, wang, go, el in S.SAMHAP:
            if lb != b and {lb, b} <= {sang, wang, go} and wang in (lb, b):
                out.append(f"{pos} 반합({S.BRANCHES[lb]}{S.BRANCHES[b]}→{S.ELEMENTS_KO[el]})")
    return out


def interpret_core(stems, branches):
    st = strength(stems, branches)
    jh = johu(stems, branches)
    gk = gyeokguk(stems, branches, st)
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
    ys = core["yongsin"]
    core["ten_god_distribution"] = ten_god_distribution(stems, branches)
    core["palace"] = {"연주": "조상·초년(~19세)", "월주": "부모·형제·사회(20~39세)", "일주": "본인·배우자(40~59세)", "시주": "자녀·말년(60세~)"}
    if "daewoon" in l1:
        core["daewoon_rating"] = []
        for d in l1["daewoon"]["list"]:
            idx = S.parse_gz(d["pillar"])
            v, label = luck_rating(dm, ys, idx)
            core["daewoon_rating"].append({"pillar": d["pillar"], "age_from": d["age_from"], "score": v, "rating": label,
                                           "natal": natal_relations(stems, branches, idx)})
    core["seun_rating"] = []
    for s in l1.get("seun", []):
        idx = S.parse_gz(s["pillar"])
        v, label = luck_rating(dm, ys, idx)
        core["seun_rating"].append({"year": s["year"], "pillar": s["pillar"], "score": v, "rating": label,
                                    "natal": natal_relations(stems, branches, idx)})
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
