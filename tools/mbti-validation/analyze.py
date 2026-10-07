#!/usr/bin/env python3
"""MBTI 이론 매핑(설계서 §4.3) 실사용자 검증 분석기.

입력 CSV (동의받은 응답만, 개인 식별정보 없음):
  consent,birth_date,calendar,leap,birth_time,place,mbti
  yes,1990-05-10,solar,false,14:30,서울,ENFP-T
  - consent 가 yes 가 아닌 행은 읽지 않는다.
  - birth_time 은 비워도 된다(시주 없이 계산).

출력: 축(E/I, S/N, T/F, J/P)마다
  - 사주 쪽 매핑 점수(mbti_layer.compare 의 saju_score)와 자기보고 글자의 점이연 상관(r)
  - 순열검정 p값(5,000회)
  - 매핑 방향 일치율과 50% 기준 이항 비교
결과는 집계값만 출력하고 개별 행은 출력하지 않는다.

사용: python3 analyze.py responses.csv [--min-n 200] [--json out.json]
"""
import argparse
import csv
import json
import math
import os
import random
import sys

ENGINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".claude", "skills", "saju-standard", "engine")
sys.path.insert(0, ENGINE)
import interpret  # noqa: E402
import mbti_layer as M  # noqa: E402
import saju_std as S  # noqa: E402


def point_biserial(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sxy / (sx * sy) if sx and sy else 0.0


def perm_p(x, y, r_obs, iters=5000, seed=7):
    rng = random.Random(seed)
    yy = list(y)
    hits = 0
    for _ in range(iters):
        rng.shuffle(yy)
        if abs(point_biserial(x, yy)) >= abs(r_obs):
            hits += 1
    return (hits + 1) / (iters + 1)


def binom_p_two_sided(k, n):
    """정규근사 이항검정 (p=0.5)."""
    if n == 0:
        return 1.0
    z = (k - n / 2) / math.sqrt(n / 4)
    return math.erfc(abs(z) / math.sqrt(2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--min-n", type=int, default=200, help="축별 결과를 보고할 최소 표본 수")
    ap.add_argument("--json")
    a = ap.parse_args()

    rows, skipped = [], 0
    with open(a.csv, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("consent") or "").strip().lower() != "yes":
                skipped += 1
                continue
            try:
                t = M.parse_type(r["mbti"])
                l1 = S.compute({"date": r["birth_date"], "calendar": r.get("calendar") or "solar",
                                "leap": (r.get("leap") or "").lower() == "true",
                                "time": r.get("birth_time") or None, "place": r.get("place") or None})
                l2 = interpret.interpret(l1)
                axes = M.compare(t, l2, l1)["axes"]
                rows.append((t, axes))
            except (ValueError, KeyError):
                skipped += 1
    n = len(rows)
    report = {"n": n, "skipped": skipped, "axes": {}}
    for i, axis in enumerate(("EI", "SN", "TF", "JP")):
        x = [ax[i]["saju_score"] for _, ax in rows]
        y = [1 if t[i] == axis[0] else 0 for t, _ in rows]
        leaned = [(ax[i]["saju_lean"], t[i]) for t, ax in rows if ax[i]["saju_lean"] != "균형"]
        agree = sum(1 for lean, s in leaned if lean == s)
        entry = {"n": n, "share_first_letter": round(sum(y) / n, 3) if n else None,
                 "leaned_n": len(leaned), "agreement": round(agree / len(leaned), 3) if leaned else None,
                 "agreement_p": round(binom_p_two_sided(agree, len(leaned)), 4)}
        if n >= a.min_n:
            r = point_biserial(x, y)
            entry.update({"r": round(r, 4), "perm_p": round(perm_p(x, y, r), 4)})
        else:
            entry["r"] = None
            entry["note"] = f"표본 {n} < {a.min_n}: 상관은 보고하지 않음"
        report["axes"][axis] = entry
    report["interpretation"] = ("|r| < 0.1 이거나 p ≥ 0.05 이면 매핑을 근거로 성향을 말하지 말 것. "
                                "여러 축을 함께 보므로 유의수준은 0.05/4 = 0.0125(본페로니)로 판단.")
    out = json.dumps(report, ensure_ascii=False, indent=1)
    print(out)
    if a.json:
        open(a.json, "w", encoding="utf-8").write(out)


if __name__ == "__main__":
    main()
