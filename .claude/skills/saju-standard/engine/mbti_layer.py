#!/usr/bin/env python3
"""saju-standard L3 MBTI 레이어 (설계서 §4).

원칙
  - 사용자가 스스로 밝힌 유형만 받는다. 사주로 MBTI를 추정하지 않는다.
  - saju_std / interpret 를 import 하지 않는다. 사주 쪽 결과(JSON)를 데이터로만 받는다.
  - 사주↔MBTI 대응은 '이론적 매핑(가설)'이며 결과에 항상 그 라벨을 단다.

기능
  1. tone      말투 개인화 프로필
  2. compare   "타고난 결 vs 지금의 나" 비교 카드
  3. timing    대운·세운 십신 × 인지기능 성장 과제
  4. compat    사주 + MBTI 이중 궁합

CLI:
  python3 mbti_layer.py --type INFP
  python3 interpret.py --date ... --seun 2026 > me.json
  python3 mbti_layer.py --type INFP --saju me.json
  python3 mbti_layer.py --type INFP --saju me.json --partner-type ESTJ --partner-saju you.json --mode team
"""
import argparse
import json
import sys

NOTE = "이론적 매핑(가설)입니다. 사주에서 MBTI를 판정하지 않으며, 검증된 상관관계가 아닙니다."
TYPES = {a + b + c + d for a in "EI" for b in "SN" for c in "TF" for d in "JP"}
FUNC_KO = {"Ni": "내향 직관", "Ne": "외향 직관", "Si": "내향 감각", "Se": "외향 감각",
           "Ti": "내향 사고", "Te": "외향 사고", "Fi": "내향 감정", "Fe": "외향 감정"}
POSITION_KO = ["주기능", "부기능", "3차 기능", "열등 기능"]


def parse_type(t):
    """'ENFP', 'enfp-t', 'INTJ-A' → 4글자 유형. 정체성 접미사는 parse_identity 로 따로 읽는다."""
    raw = (t or "").strip().upper()
    core = raw.split("-")[0]
    if core not in TYPES or (raw != core and raw[5:] not in ("A", "T")):
        raise ValueError(f"MBTI 유형 4글자를 입력하세요 (예: INFP, ENFP-T). 입력값: {t!r}")
    return core


def parse_identity(t):
    """16Personalities 정체성 지표(-A 확신형 / -T 민감형). MBTI 공식 지표가 아니다."""
    raw = (t or "").strip().upper()
    return raw[5:] if len(raw) == 6 and raw[4] == "-" else None


def flip(att):
    return "e" if att == "i" else "i"


def opposite(fn):
    return {"N": "S", "S": "N", "T": "F", "F": "T"}[fn]


def cognitive_stack(t):
    """Beebe 모형: 주·부·3차·열등."""
    ei, sn, tf, jp = t
    judge, perceive = tf, sn
    if ei == "E":
        dom = (judge if jp == "J" else perceive, "e")
    else:
        dom = (perceive if jp == "J" else judge, "i")
    aux_fn = perceive if dom[0] == judge else judge
    aux = (aux_fn, flip(dom[1]))
    tert = (opposite(aux[0]), dom[1])
    inf = (opposite(dom[0]), flip(dom[1]))
    return [f + a for f, a in (dom, aux, tert, inf)]


# ── 1. 말투 ─────────────────────────────────────────────────────────────
TONE = {
    "E": "대화하듯 주고받고, 바로 해볼 수 있는 행동을 제안", "I": "생각을 정리할 성찰 질문을 남기고, 혼자 소화할 여지를 둠",
    "S": "구체적 사례·시기·숫자로 말함", "N": "큰 흐름·의미·가능성부터 말함",
    "T": "근거와 구조를 먼저, 결론을 분명하게", "F": "마음과 관계의 맥락을 먼저 짚고 공감하며 전달",
    "J": "단계별 계획·우선순위·기한으로 정리", "P": "여러 선택지와 작은 실험으로 열어 둠",
}


IDENTITY_TONE = {
    "T": "주의할 대목은 불안을 키우지 않게 '대비하면 되는 것'으로 말하고, 바로 할 수 있는 작은 다음 걸음과 함께 전달",
    "A": "돌려 말하지 않고 핵심부터 직설적으로, 대신 놓치기 쉬운 위험 신호는 분명히 짚음",
}


def tone(t, identity=None):
    rules = [TONE[c] for c in t]
    if identity in IDENTITY_TONE:
        rules.append(IDENTITY_TONE[identity])
    return {"type": t, "identity": identity, "rules": rules,
            "instruction": "해석 내용은 바꾸지 말고 전달 방식만 아래 규칙대로 조정한다.",
            "identity_note": "-A/-T는 16Personalities의 정체성 지표로 MBTI 공식 지표가 아니며, 말투 조정에만 쓴다." if identity else None}


# ── 2. 비교 카드 ────────────────────────────────────────────────────────
GROUP = {"비견": "비겁", "겁재": "비겁", "식신": "식상", "상관": "식상", "편재": "재성", "정재": "재성",
         "편관": "관성", "정관": "관성", "편인": "인성", "정인": "인성"}

# 축별 사주 신호 (가설). 값: (+ 쪽 글자 신호, − 쪽 글자 신호)
AXIS_SIGNALS = {
    "EI": ({"식상": 1.0, "비겁": 0.5, "목": 0.3, "화": 0.5}, {"인성": 1.0, "수": 0.5, "금": 0.3}),
    "SN": ({"재성": 1.0, "토": 0.5}, {"인성": 0.7, "상관": 0.6, "수": 0.3}),
    "TF": ({"관성": 0.6, "재성": 0.5, "금": 0.5}, {"식신": 0.6, "정인": 0.5, "화": 0.3, "목": 0.3}),
    "JP": ({"관성": 1.0, "정인": 0.4}, {"식상": 0.8, "편재": 0.3, "편인": 0.3}),
}
AXIS_TALK = {
    "EI": ("표현·발산의 기운", "내면·수용의 기운"),
    "SN": ("현실·실물 감각", "직관·의미 탐색"),
    "TF": ("규범·결과 중심 판단", "관계·감정 중심 판단"),
    "JP": ("질서·계획 지향", "자유·변화 지향"),
}


def saju_signals(l2, l1=None):
    sig = {}
    for god, n in l2.get("ten_god_distribution", {}).items():
        sig[god] = sig.get(god, 0) + n
        sig[GROUP[god]] = sig.get(GROUP[god], 0) + n
    if l1:
        for el, v in l1["elements"]["with_hidden"].items():
            sig[el] = sig.get(el, 0) + v
    return sig


def compare(t, l2, l1=None):
    sig = saju_signals(l2, l1)
    axes = []
    for axis, (plus, minus) in AXIS_SIGNALS.items():
        p = sum(sig.get(k, 0) * w for k, w in plus.items())
        m = sum(sig.get(k, 0) * w for k, w in minus.items())
        diff = p - m
        lean = axis[0] if diff > 0.5 else axis[1] if diff < -0.5 else "균형"
        self_letter = t["EISNTFJP".index(axis[0]) // 2]
        match = lean == "균형" or lean == self_letter
        talk = AXIS_TALK[axis][0 if lean == axis[0] else 1] if lean != "균형" else "양쪽 기운이 비슷함"
        if lean == "균형":
            point = f"사주는 {axis[0]}/{axis[1]} 어느 쪽으로도 기울지 않아, 지금의 {self_letter} 성향은 선택과 습관의 결과일 수 있어요."
        elif match:
            point = f"사주의 {talk}이(가) 지금의 {self_letter} 성향과 같은 방향이에요. 타고난 결을 그대로 쓰는 영역입니다."
        else:
            point = (f"사주는 {talk} 쪽인데 지금은 {self_letter} 성향이에요. 환경·역할 속에서 발달시킨 면일 수 있어요. "
                     f"어느 쪽이 더 편한지 떠올려 보세요.")
        axes.append({"axis": axis, "saju_lean": lean, "saju_score": round(diff, 2), "self": self_letter,
                     "match": match, "talking_point": point})
    return {"type": t, "axes": axes, "match_count": sum(a["match"] for a in axes), "note": NOTE}


# ── 3. 시기 × 인지기능 ──────────────────────────────────────────────────
THEME = {
    "비겁": ("자기주도·독립·경쟁", ["Ti", "Fi", "Se"]),
    "식상": ("표현·창작·말하기", ["Ne", "Se", "Fe"]),
    "재성": ("실행·성과·현실 관리", ["Te", "Se", "Si"]),
    "관성": ("책임·규범·조직 안의 역할", ["Te", "Si", "Fe"]),
    "인성": ("배움·성찰·내면 정리", ["Ni", "Si", "Ti", "Fi"]),
}
STEM_EL = dict(zip("甲乙丙丁戊己庚辛壬癸", [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]))
BRANCH_MAIN = dict(zip("子丑寅卯辰巳午未申酉戌亥", "癸己甲乙戊丙丁己庚辛戊壬"))
GROUP_ORDER = ["비겁", "식상", "재성", "관성", "인성"]


def group_of(day_stem, char):
    el = STEM_EL[char] if char in STEM_EL else STEM_EL[BRANCH_MAIN[char]]
    return GROUP_ORDER[(el - STEM_EL[day_stem]) % 5]


def timing(t, l1, l2=None):
    stack = cognitive_stack(t)
    ds = l1["day_master"]["char"]
    periods = [("세운", s["year"], s["pillar"]) for s in l1.get("seun", [])]
    periods += [("대운", f"{d['age_from']}세~", d["pillar"]) for d in l1.get("daewoon", {}).get("list", [])[:8]]
    rating = {}
    if l2:
        for r in l2.get("seun_rating", []):
            rating[("세운", r["year"])] = r["rating"]
        for r in l2.get("daewoon_rating", []):
            rating[("대운", f"{r['age_from']}세~")] = r["rating"]
    out = []
    for kind, when, pillar in periods:
        g = group_of(ds, pillar[1])  # 지지(60%) 기준 주제
        theme, funcs = THEME[g]
        pos = min((stack.index(f), f) for f in funcs if f in stack) if any(f in stack for f in funcs) else None
        if pos is None:
            fn, role = funcs[0], "새로운 기능"
            msg = f"{theme}의 시기. 평소 쓰지 않는 {FUNC_KO[fn]}({fn})을 가볍게 연습해 볼 때예요."
        else:
            idx, fn = pos
            role = POSITION_KO[idx]
            if idx <= 1:
                msg = f"{theme}의 시기. 당신의 {role} {FUNC_KO[fn]}({fn})이 그대로 힘을 쓰는 때예요."
            else:
                msg = f"{theme}의 시기. {role}인 {FUNC_KO[fn]}({fn})을 키울 성장 과제가 주어지는 때예요."
        out.append({"kind": kind, "when": when, "pillar": pillar, "group": g, "theme": theme,
                    "function": fn, "role": role, "luck": rating.get((kind, when)), "message": msg})
    return {"type": t, "stack": stack, "periods": out, "note": NOTE}


# ── 4. 이중 궁합 ────────────────────────────────────────────────────────
STEM_HAP = {frozenset(p) for p in ["甲己", "乙庚", "丙辛", "丁壬", "戊癸"]}
STEM_CHUNG = {frozenset(p) for p in ["甲庚", "乙辛", "丙壬", "丁癸"]}
BR = "子丑寅卯辰巳午未申酉戌亥"
YUKHAP = {frozenset(p) for p in ["子丑", "寅亥", "卯戌", "辰酉", "巳申", "午未"]}
EL_KO = ["목", "화", "토", "금", "수"]


def saju_compat(l1a, l2a, l1b, l2b):
    da, db = l1a["pillars"]["day"]["pillar"], l1b["pillars"]["day"]["pillar"]
    points, score = [], 0
    if frozenset((da[0], db[0])) in STEM_HAP:
        score += 2
        points.append(f"일간 천간합({da[0]}{db[0]}): 서로 끌리는 결")
    if frozenset((da[0], db[0])) in STEM_CHUNG:
        score -= 1
        points.append(f"일간 충({da[0]}{db[0]}): 판단 방식이 부딪히기 쉬움")
    if frozenset((da[1], db[1])) in YUKHAP:
        score += 2
        points.append(f"일지 육합({da[1]}{db[1]}): 생활 리듬이 맞물림")
    if (BR.index(da[1]) - BR.index(db[1])) % 12 == 6:
        score -= 2
        points.append(f"일지 충({da[1]}{db[1]}): 생활 공간·습관 조율 필요")
    ya, yb = l2a["yongsin"]["element"], l2b["yongsin"]["element"]
    ea, eb = l1a["elements"]["with_hidden"], l1b["elements"]["with_hidden"]
    if eb.get(ya, 0) >= 2:
        score += 1
        points.append(f"상대가 내 용신({ya}) 기운을 넉넉히 가짐")
    if ea.get(yb, 0) >= 2:
        score += 1
        points.append(f"내가 상대 용신({yb}) 기운을 넉넉히 가짐")
    return {"score": score, "points": points or ["두드러진 합·충 없음: 무난한 조합"]}


def mbti_compat(a, b, mode):
    sa, sb = cognitive_stack(a), cognitive_stack(b)
    points, score = [], 0
    shared = set(sa[:2]) & set(sb[:2])
    if shared:
        score += len(shared)
        points.append(f"주·부기능 공유({', '.join(sorted(shared))}): 대화 주파수가 맞음")
    if sa[0] == sb[3] or sb[0] == sa[3]:
        score += 1
        points.append("한쪽의 주기능이 다른 쪽의 열등기능: 서로의 약점을 채워 주지만 피로할 수 있음")
    if a[1] == b[1]:
        score += 1
        points.append(f"인식 방식 같음({a[1]}): 관심사·말의 결이 비슷함")
    else:
        points.append("인식 방식 다름(S/N): 구체와 큰 그림을 나눠 맡으면 좋음")
    if mode == "team":
        if a[3] != b[3]:
            score += 1
            points.append("J/P 조합: 계획과 유연성을 분담하기 좋음")
        if a[2] != b[2]:
            points.append("T/F 조합: 결정 기준(논리/사람)을 미리 합의하세요")
    else:
        if a[2] != b[2]:
            points.append("T/F 다름: 위로가 필요한 순간과 해결이 필요한 순간을 구분해 말해 주세요")
        if a[0] != b[0]:
            score += 1
            points.append("E/I 균형: 바깥 활동과 쉬는 시간을 번갈아 맞추기 좋음")
    return {"score": score, "stacks": {a: sa, b: sb}, "points": points}


def compat(ta, tb, mode="love", saju_a=None, saju_b=None):
    out = {"mode": mode, "mbti": mbti_compat(ta, tb, mode),
           "caution": "궁합은 경향과 대화 포인트일 뿐이며, 상대의 동의 없이 상대 사주를 단정하지 않습니다.",
           "note": NOTE}
    if saju_a and saju_b:
        out["saju"] = saju_compat(saju_a["l1"], saju_a["l2"], saju_b["l1"], saju_b["l2"])
    return out


def build(t, saju=None, partner_type=None, partner_saju=None, mode="love"):
    identity = parse_identity(t)
    t = parse_type(t)
    card = {"type": t, "identity": identity, "stack": cognitive_stack(t), "tone": tone(t, identity), "note": NOTE}
    if saju:
        card["compare"] = compare(t, saju["l2"], saju["l1"])
        card["timing"] = timing(t, saju["l1"], saju["l2"])
    if partner_type:
        card["compat"] = compat(t, parse_type(partner_type), mode, saju, partner_saju)
    return card


def main(argv=None):
    ap = argparse.ArgumentParser(description="saju-standard MBTI 레이어")
    ap.add_argument("--type", required=True)
    ap.add_argument("--saju", help="interpret.py 출력 JSON 파일 ({l1, l2})")
    ap.add_argument("--partner-type")
    ap.add_argument("--partner-saju")
    ap.add_argument("--mode", default="love", choices=["love", "team"])
    a = ap.parse_args(argv)
    load = lambda p: json.load(open(p, encoding="utf-8")) if p else None  # noqa: E731
    try:
        card = build(a.type, load(a.saju), a.partner_type, load(a.partner_saju), a.mode)
    except ValueError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 2
    print(json.dumps(card, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
