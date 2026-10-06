# 엔진 교차검증 하네스

결과 해설은 `docs/engine-comparison-2026-10.md`를 참고하세요.

## 준비 (이 폴더 기준)

```bash
mkdir ext && cd ext
for r in adminhelper/saju-engine yuling170916/jeomsin-fortune-reader \
         RichardHojunJang/hermes-manseyeok-skill xodn348/destiny davidchoi0313/samsin-saju; do
  git clone --depth 1 https://github.com/$r.git $(echo $r | tr / _)
done
(cd RichardHojunJang_hermes-manseyeok-skill/skills/hermes-saju/scripts && npm ci --ignore-scripts)
cd .. && git clone --depth 1 https://github.com/be-realdeveloper/saju.git saju-src
python3 -m venv venv && venv/bin/pip install lunar-python
```

## 실행

```bash
node harness/compare.mjs pure  > results/pure.json   # 경도 135°, 보정 없음
node harness/compare.mjs seoul > results/seoul.json  # 서울 경도 보정
node harness/terms.mjs          # adminhelper 천문 계산 절입 시각
python3 harness/lunar_terms.py  # lunar-python 절입 시각(UTC+8)
```
