# MBTI 매핑 실사용자 검증 (설계서 §5.3)

`saju-standard`의 사주↔MBTI 대응표(`references/mbti-layer.md`)는 **가설**입니다. 실제로 맞는지는 동의를 받은 사람들의 (출생정보, 자기보고 MBTI)로만 확인할 수 있어요. 이 폴더는 그 수집 양식과 분석기입니다.

## 수집 원칙
- 이름·연락처·이메일·주소는 **받지 않습니다.** 생년월일·출생시각·출생지(시/도)·MBTI만 받습니다.
- 동의 문구(`consent-ko.md`)에 "예"라고 답한 응답만 분석합니다.
- 분석 결과는 축별 **집계값만** 공개합니다. 개별 응답은 공유하지 않습니다.
- 원자료 CSV는 저장소에 커밋하지 않습니다(`.gitignore`에 `tools/mbti-validation/data/` 포함).

## 필요한 표본 수
축마다 상관 r ≈ 0.1(약한 효과)을 유의수준 0.0125, 검정력 80%로 잡으려면 대략 **1,000명** 이상이 필요합니다. 200명 미만이면 분석기는 상관을 보고하지 않습니다.

## 실행
```bash
python3 tools/mbti-validation/analyze.py tools/mbti-validation/data/responses.csv --json result.json
```
양식은 `sample.csv`(가상의 예시 3행)를 보세요.

## 판단 기준
- 축별 |r| < 0.1 이거나 순열검정 p ≥ 0.0125 → 그 축의 매핑으로 성향을 말하지 않음. 비교 카드는 "대화 소재"로만 유지
- 의미 있는 축이 나오면 가중치를 데이터로 다시 맞추고(교차검증), 결과와 표본 수를 `references/mbti-layer.md`에 기록
