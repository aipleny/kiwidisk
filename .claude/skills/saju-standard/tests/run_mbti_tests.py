#!/usr/bin/env python3
"""L3 MBTI 레이어 테스트: 16유형 인지기능 스택, 입력 검증, 사주 무접점, 전 유형 카드 생성."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "..", "engine")
sys.path.insert(0, ENGINE)
import mbti_layer as M  # noqa: E402

STACKS = {  # Beebe 모형 표준표
    "ISTJ": "Si Te Fi Ne", "ISFJ": "Si Fe Ti Ne", "INFJ": "Ni Fe Ti Se", "INTJ": "Ni Te Fi Se",
    "ISTP": "Ti Se Ni Fe", "ISFP": "Fi Se Ni Te", "INFP": "Fi Ne Si Te", "INTP": "Ti Ne Si Fe",
    "ESTP": "Se Ti Fe Ni", "ESFP": "Se Fi Te Ni", "ENFP": "Ne Fi Te Si", "ENTP": "Ne Ti Fe Si",
    "ESTJ": "Te Si Ne Fi", "ESFJ": "Fe Si Ne Ti", "ENFJ": "Fe Ni Se Ti", "ENTJ": "Te Ni Se Fi",
}
fails = []


def check(name, cond):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")
    if not cond:
        fails.append(name)


check("16유형 인지기능 스택", all(M.cognitive_stack(t) == s.split() for t, s in STACKS.items()))
bad_inputs = ["", "INFX", "ABCD", "INF", None]
rejected = 0
for b in bad_inputs:
    try:
        M.parse_type(b)
    except ValueError:
        rejected += 1
check("잘못된 유형 거부 5/5", rejected == len(bad_inputs))
check("소문자 허용", M.parse_type("infp") == "INFP")

src = open(os.path.join(ENGINE, "mbti_layer.py"), encoding="utf-8").read()
check("사주 엔진 import 없음(무접점)", "import saju_std" not in src and "import interpret" not in src)

saju = json.loads(subprocess.run([sys.executable, os.path.join(ENGINE, "interpret.py"), "--date", "2026-03-10",
                                  "--time", "09:30", "--sex", "female", "--seun", "2026,2027"],
                                 capture_output=True, text=True, check=True).stdout)
partner = json.loads(subprocess.run([sys.executable, os.path.join(ENGINE, "interpret.py"), "--date", "1994-11-20",
                                     "--time", "21:00", "--sex", "male"], capture_output=True, text=True, check=True).stdout)
ok = 0
for t in STACKS:
    card = M.build(t, saju, "ENTJ", partner, "team")
    good = (len(card["compare"]["axes"]) == 4 and card["timing"]["periods"] and card["compat"]["saju"]
            and all(M.NOTE == x for x in (card["note"], card["compare"]["note"], card["timing"]["note"], card["compat"]["note"])))
    ok += bool(good)
check(f"16유형 × 사주 카드 생성 {ok}/16", ok == 16)
card = M.build("INFP", saju)
check("비교 카드는 유형을 판정하지 않음(자기보고 유형 그대로)", card["compare"]["type"] == "INFP" and all(a["self"] in "EISNTFJP" for a in card["compare"]["axes"]))
check("세운 2026 포함", any(p["kind"] == "세운" and p["when"] == 2026 and p["pillar"] == "丙午" for p in card["timing"]["periods"]))

print(f"\n실패 {len(fails)}개")
sys.exit(1 if fails else 0)
