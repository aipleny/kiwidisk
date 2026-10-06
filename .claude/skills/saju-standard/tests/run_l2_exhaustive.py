#!/usr/bin/env python3
"""L2 해석 모듈 전수 테스트 (설계서 §5.2).

가능한 모든 명식 60(연) × 12(월) × 60(일) × 12(시) = 518,400개 + 시주 미상 43,200개에 대해
interpret_core 를 실행하고 불변식 위반·예외를 센다. 분포는 '조합 수' 기준이며 실제 출생 빈도가 아니다.
결과 요약은 tests/data/l2_exhaustive_summary.json 에 저장.
"""
import json
import os
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))
import interpret as I  # noqa: E402
import saju_std as S  # noqa: E402

STRONG_GROUPS = {"식상", "재성", "관성"}
WEAK_GROUPS = {"인성", "비겁"}


def charts(with_hour=True):
    for y in range(60):
        ys = y % 10
        first = (ys % 5 * 2 + 2) % 10
        for mb in range(12):
            ms = (first + (mb - 2) % 12) % 10
            for d in range(60):
                ds, db = d % 10, d % 12
                if not with_hour:
                    yield [ys, ms, ds, None], [y % 12, mb, db, None]
                    continue
                for hb in range(12):
                    yield [ys, ms, ds, S.hour_stem(d, hb)], [y % 12, mb, db, hb]


def check(stems, branches, r):
    errs = []
    st, jh, gk, ys = r["strength"], r["johu"], r["gyeokguk"], r["yongsin"]
    if not 0 <= st["score"] <= 100:
        errs.append("score 범위")
    if gk["name"] not in I.SANGSIN:
        errs.append("격 이름")
    if (gk["name"] == "건록격") != (branches[1] == I.ROK[stems[2]]):
        errs.append("건록격 판정")
    if jh["priority"] and branches[1] not in (0, 1, 6, 7):
        errs.append("조후 우선 월")
    if ys["method"] == "억부":
        if st["strong"] and ys["group"] not in STRONG_GROUPS:
            errs.append("신강인데 생부 용신")
        if not st["strong"] and ys["group"] not in WEAK_GROUPS:
            errs.append("신약인데 극설 용신")
    if ys["jong"] == "종왕격" and st["score"] < 85:
        errs.append("종왕 점수")
    if ys["jong"] in ("종재격", "종살격", "종아격") and (st["score"] > 15 or st["rooted"]):
        errs.append("종격 조건")
    if ys["element"] not in S.ELEMENTS_KO or ys["confidence"] not in ("높음", "보통", "낮음"):
        errs.append("용신 필드")
    return errs


def run(with_hour):
    stats = {k: Counter() for k in ("grade", "gyeok", "status", "method", "confidence", "jong", "errors")}
    n = bad = 0
    examples = []
    for stems, branches in charts(with_hour):
        n += 1
        try:
            r = I.interpret_core(stems, branches)
        except Exception as e:  # noqa: BLE001
            bad += 1
            stats["errors"]["exception:" + type(e).__name__] += 1
            if len(examples) < 5:
                examples.append({"stems": stems, "branches": branches, "error": repr(e)})
            continue
        errs = check(stems, branches, r)
        if errs:
            bad += 1
            for e in errs:
                stats["errors"][e] += 1
            if len(examples) < 5:
                examples.append({"chart": [S.gz_name(S.gz_index(s, b)) if s is not None else None for s, b in zip(stems, branches)], "errors": errs})
        stats["grade"][r["strength"]["grade"]] += 1
        stats["gyeok"][r["gyeokguk"]["name"]] += 1
        stats["status"][r["gyeokguk"]["status"]] += 1
        stats["method"][r["yongsin"]["method"]] += 1
        stats["confidence"][r["yongsin"]["confidence"]] += 1
        stats["jong"][r["yongsin"]["jong"] or "-"] += 1
    return n, bad, {k: dict(v.most_common()) for k, v in stats.items()}, examples


if __name__ == "__main__":
    t0 = time.time()
    summary = {}
    for label, wh in (("시주 포함 518,400", True), ("시주 미상 43,200", False)):
        n, bad, stats, ex = run(wh)
        print(f"[{'PASS' if bad == 0 else 'FAIL'}] L2 전수 {label}: {n - bad}/{n} 불변식 통과", flush=True)
        for k, v in stats.items():
            if v:
                print(f"   {k}: {v}")
        summary[label] = {"total": n, "violations": bad, "stats": stats, "examples": ex}
    # 결정론: 같은 입력 → 같은 출력
    same = all(I.interpret_core(s, b) == I.interpret_core(s, b) for s, b in list(charts())[:: 5000])
    print(f"[{'PASS' if same else 'FAIL'}] 결정론(재실행 동일)")
    with open(os.path.join(HERE, "data", "l2_exhaustive_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print(f"{time.time() - t0:.0f}s")
    sys.exit(0 if all(v["violations"] == 0 for v in summary.values()) and same else 1)
