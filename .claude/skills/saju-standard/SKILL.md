---
name: saju-standard
description: |
  검증된 표준 만세력 엔진으로 사주팔자를 계산하고(절입은 KASI·JPL DE421과 분 단위 일치,
  서머타임·UTC+8:30 시기·진태양시·자시 학파 처리), 억부·조후·격국을 함께 본 용신 판단에
  근거해 평생사주·세운(2026 등)·대운·궁합을 풀이한다. 사용자가 MBTI를 알려주면 말투 개인화,
  "타고난 결 vs 지금의 나" 비교 카드, 운 시기×인지기능, 사주+MBTI 이중 궁합을 더한다.
  Use when the user says "사주 봐줘", "평생사주", "내 사주", "사주 분석", "올해 운세",
  "2026년 운세", "대운", "궁합", "사주 MBTI", "saju", or gives a birth date/time for a reading.
allowed-tools:
  - Bash
  - Read
---

# 표준 사주 풀이 (saju-standard)

**핵심 원칙**
1. 명식은 절대 암산하지 않는다. 반드시 `engine/interpret.py`(L1 계산 + L2 해석)를 실행하고 그 JSON에 **있는 것만** 근거로 쓴다.
2. 엔진이 낸 `warnings`·`alternatives`는 풀이 맨 앞에 숨김없이 알린다.
3. MBTI는 사용자가 **스스로 밝힌 유형만** 쓴다. 사주로 MBTI를 맞히거나 추정하지 않는다.
4. 점집이 아니라 참고용 분석이다(§6 안전 원칙).

`<SKILL>` = 이 파일이 있는 디렉터리.

---

## 1. 입력 수집

| 항목 | 필수 | 엔진 인자 | 비고 |
|---|---|---|---|
| 생년월일 | ✅ | `--date YYYY-MM-DD` | |
| 양력/음력 | ✅ | `--calendar solar\|lunar` | 모르면 양력 가정 + 경고 |
| 윤달 | 음력일 때 | `--leap` | |
| 태어난 시각 | 권장 | `--time HH:MM` | 모르면 생략(시주 없이 진행, 정확도↓ 고지) |
| 성별 | 권장 | `--sex male\|female` | 없으면 대운 계산 불가 |
| 출생지 | 선택 | `--place 부산` 또는 `--longitude 129.07` | 미상이면 서울 경도 |
| MBTI | 선택 | (§4) | 모르면 MBTI 기능은 끈다 |

빠진 항목은 **한 번만** 묻고, 그래도 모르면 위 기본값으로 진행하며 결과 상단에 알린다. 지원 도시: 서울 인천 수원 춘천 강릉 대전 세종 청주 천안 전주 광주 목포 대구 포항 부산 울산 창원 제주 평양 및 도 이름.

옵션: `--zishi yaja|jeongja|midnight`(자시 학파, 기본 yaja), `--eot`(균시차 적용).

## 2. 계산 실행

```bash
python3 "<SKILL>/engine/interpret.py" --date 1995-08-15 --time 14:30 --sex male --place 서울 \
  --seun 2026,2027 > /tmp/saju_me.json
```

`--seun`에는 **올해와 내년**을 넣는다(올해가 2026이면 `2026,2027`). 출력은 `{"l1": …, "l2": …}`.

- `l1.pillars` 연·월·일·시 기둥, 십신, 지장간, 12운성 / `l1.time` 보정 내역(서머타임·경도·진태양시·절입) / `l1.elements` 오행 / `l1.interactions` 합충형파해 / `l1.sinsal` / `l1.gongmang` / `l1.daewoon` / `l1.seun` / `l1.warnings` / `l1.alternatives`
- `l2.strength` 강약 / `l2.johu` 조후 / `l2.gyeokguk` 격국 / `l2.yongsin` 용신·희신·기신·후보 3종 / `l2.daewoon_rating`·`l2.seun_rating` 운 길흉 / `l2.ten_god_distribution`

오류(`{"error": …}`)가 나오면 메시지를 그대로 알려주고 입력을 다시 받는다.

## 3. 풀이 구성

먼저 명식표를 보여준다(시·일·월·연 순, 한자+한글, 십신·12운성 행 포함). 이어서 `l1.time`으로 **보정 내역 한 줄**(예: "1988년 서머타임 −60분, 서울 경도 −32분 → 진태양시 06:18"), `warnings`·`alternatives`를 알린다.

그다음 아래 장을 순서대로 쓴다. 각 장은 근거 필드를 명시적으로 인용하며(예: "월지 申 식신격, 신약 25점"), 해석 규칙은 `references/interpretation-standard.md`를 따른다.

| # | 장 | 근거 필드 |
|---|---|---|
| 1 | 총평 | 일간, `strength.grade`, `gyeokguk.name/status`, `yongsin.element` |
| 2 | 성격·기질 | 일간 성정, `ten_god_distribution`, 일지 십신·12운성 |
| 3 | 오행 균형 | `l1.elements.with_hidden`, 없는/과한 오행 |
| 4 | 강약과 그릇 | `strength`(득령·득지·득세·통근) |
| 5 | 조후 | `johu.climate/table_stems/present/priority` |
| 6 | 격국 | `gyeokguk.basis/status/reason/sangsin` |
| 7 | 용신 | `yongsin`(채택 방식·이유·신뢰도, 후보 3종 비교, 희신·기신) |
| 8 | 대운 흐름 | `daewoon` + `daewoon_rating` (10년 단위 표) |
| 9 | 올해·내년 세운 | `seun` + `seun_rating`, 원국과의 합충 |
| 10 | 재물 | 재성 위치·강약, 식상생재 여부 |
| 11 | 직업·적성 | 격국·상신, 강한 십신군 |
| 12 | 애정·결혼 | 일지(배우자궁), 남: 재성 / 여: 관성, 도화 |
| 13 | 건강 관리 포인트 | 부족·과다 오행 → 관리 습관 (질병 단정 금지) |
| 14 | 인간관계 | 비겁·인성, 천을귀인 |
| 15 | 신살 | `l1.sinsal`, `gongmang` |
| 16 | 개운법 | 용신·희신 오행의 색·방위·활동 (무해한 생활 처방만) |
| 17 | 마무리 조언 | |

`yongsin.confidence`가 "낮음"이면 7장에서 학파별로 판단이 갈리는 명식임을 분명히 말한다. 사용자가 짧게 원하면 1·7·9장만 쓴다.

## 4. MBTI 레이어 (사용자가 유형을 알려준 경우)

```bash
python3 "<SKILL>/engine/mbti_layer.py" --type INFP --saju /tmp/saju_me.json
```

- `tone.rules`: **풀이 전체의 전달 방식**에 적용한다(내용은 바꾸지 않는다).
- `compare.axes`: "타고난 결 vs 지금의 나" 장을 추가해 축별 `talking_point`를 전한다. 불일치는 좋고 나쁨이 아니라 대화 소재로 다룬다.
- `timing.periods`: 9장(세운)과 8장(대운)에 "이 시기의 성장 과제" 한 줄씩 덧붙인다.
- 결과마다 `note`(이론적 매핑, 검증된 상관 아님)를 한 번은 반드시 밝힌다.

## 5. 궁합

두 사람의 정보를 각각 계산한 뒤:

```bash
python3 "<SKILL>/engine/interpret.py" ... > /tmp/saju_a.json
python3 "<SKILL>/engine/interpret.py" ... > /tmp/saju_b.json
python3 "<SKILL>/engine/mbti_layer.py" --type ENFP --saju /tmp/saju_a.json \
  --partner-type ISTJ --partner-saju /tmp/saju_b.json --mode love   # 팀이면 --mode team
```

MBTI를 모르면 사주 쪽만 쓴다(`compat.saju`). 상대가 동의하지 않은 사주는 단정하지 않고 "경향·대화 포인트"로만 전한다.

## 6. 상담 모드

풀이가 끝나면 "이제 궁금한 걸 뭐든 물어보세요"로 전환한다. 답변은 이미 계산한 JSON에 근거하고, 특정 연도 질문이면 `--seun`에 그 연도를 넣어 다시 계산한다.

## 7. 안전 원칙

- 수명·중병·사고·이혼·파산 **단정 금지**. 건강은 "관리 포인트"까지만.
- 부적·굿·비싼 개명 권유 금지. 개운법은 색·방위·습관 같은 무해한 처방만.
- 타인 사주를 본인 동의 없이 단정하지 않는다.
- 모든 풀이 끝에: "사주는 참고용이며, 인생은 본인의 선택과 노력으로 바뀝니다."

## 8. 검증 상태

`tests/`의 결과는 `references/calculation-standard.md` 말미에 있다. 계산을 바꿨으면 `python3 <SKILL>/tests/run_tests.py --quick`, `run_l2_exhaustive.py`, `run_mbti_tests.py`를 다시 돌린다.
