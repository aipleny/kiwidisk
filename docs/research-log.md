# 연구 루틴 로그

자동 연구 루틴(하루 2회, KST 03:52·15:52)이 실행될 때마다 맨 아래에 한 줄씩 남긴다. 루틴은 아래 순환표에서 다음 작업 하나를 고른다.

| 순서 | 작업 | 산출물 |
|---|---|---|
| A | 만족도·연구 동의 응답 집계 (`responses` 컬렉션) | `docs/research/feedback-YYYY-MM-DD.md` (집계값만) |
| B | 콘텐츠 DB 확장·다듬기 (`app/data/content-ko.json`) | 콘텐츠 커밋 + 페이지 재배포 |
| C | 고전 원문 대조로 규칙 검수 (신살·12운성·대운수·합충 등) | `references/*.json` 근거 인용 + 규칙 수정 |

원칙: 개인정보(생년월일 등)는 저장소에 커밋하지 않는다. 규칙을 바꾸면 테스트 4종(run_tests --quick, run_l2_exhaustive, run_mbti_tests, app-parity)을 모두 통과시킨 뒤에만 커밋한다.

## 기록

- 2026-10-07 · 초기 구축: 엔진·조후표(궁통보감 120칸)·격국 규칙(자평진전)·JS 엔진·콘텐츠 DB·페이지 v1 배포 (https://claude.ai/artifact/2CHWyZyKbTYsE66PqNQLFT)
