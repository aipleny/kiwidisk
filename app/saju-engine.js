/* saju-standard 브라우저 엔진 (Python engine/saju_std.py · interpret.py · mbti_layer.py 의 포팅)
 * 데이터: data/calendar.json (tools/build_app_data.py 로 생성)
 * 사용: const E = SajuEngine.create(calendarJson);
 *       const r = E.reading({date:"1990-05-10", time:"14:30", calendar:"solar", sex:"male", place:"서울", mbti:"ENFP-T", seunYears:[2026,2027]});
 * 패리티: tools/app-parity/ 에서 Python 결과와 대량 비교.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.SajuEngine = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const STEMS = "甲乙丙丁戊己庚辛壬癸", STEMS_KO = "갑을병정무기경신임계";
  const BRANCHES = "子丑寅卯辰巳午未申酉戌亥", BRANCHES_KO = "자축인묘진사오미신유술해";
  const EL_KO = ["목", "화", "토", "금", "수"];
  const STEM_EL = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4];
  const BRANCH_EL = [4, 2, 0, 0, 2, 1, 1, 2, 3, 3, 2, 4];
  const HIDDEN = { 0: [8, null, 9], 1: [9, 7, 5], 2: [4, 2, 0], 3: [0, null, 1], 4: [1, 9, 4], 5: [4, 6, 2],
    6: [2, 5, 3], 7: [3, 1, 5], 8: [4, 8, 6], 9: [6, null, 7], 10: [7, 3, 4], 11: [4, 0, 8] };
  const TEN_GODS = ["비견", "겁재", "식신", "상관", "편재", "정재", "편관", "정관", "편인", "정인"];
  const LIFE_STAGES = ["장생", "목욕", "관대", "건록", "제왕", "쇠", "병", "사", "묘", "절", "태", "양"];
  const LIFE_START = [11, 6, 2, 9, 2, 9, 5, 0, 8, 3];
  const ZISHI_MODES = ["yaja", "jeongja", "midnight"];
  const SEOUL_LON = 126.978;
  const CITY_LON = { "서울": 126.978, "인천": 126.705, "수원": 127.029, "경기": 127.029, "춘천": 127.730, "강원": 128.168,
    "강릉": 128.876, "대전": 127.385, "세종": 127.289, "청주": 127.489, "충북": 127.489, "천안": 127.114,
    "충남": 126.800, "전주": 127.148, "전북": 127.148, "광주": 126.852, "전남": 126.463, "목포": 126.392,
    "대구": 128.601, "경북": 128.889, "포항": 129.343, "부산": 129.075, "울산": 129.311, "창원": 128.681,
    "경남": 128.681, "제주": 126.531, "평양": 125.754 };
  const POS = ["연", "월", "일", "시"];
  const mod = (a, n) => ((a % n) + n) % n;
  // Python round()/format(.0f) 와 같은 은행가 반올림
  const roundHalfEven = (x) => { const f = Math.floor(x), d = x - f; if (Math.abs(d - 0.5) < 1e-9) return f % 2 === 0 ? f : f + 1; return Math.round(x); };
  const fs = (arr) => arr.slice().sort((a, b) => a - b).join(",");
  const pairSet = (pairs) => new Set(pairs.map((p) => fs(p)));
  const STEM_HAP = new Map([[fs([0, 5]), 2], [fs([1, 6]), 3], [fs([2, 7]), 4], [fs([3, 8]), 0], [fs([4, 9]), 1]]);
  const STEM_CHUNG = pairSet([[0, 6], [1, 7], [2, 8], [3, 9]]);
  const YUKHAP = new Map([[fs([0, 1]), 2], [fs([2, 11]), 0], [fs([3, 10]), 1], [fs([4, 9]), 3], [fs([5, 8]), 4], [fs([6, 7]), 1]]);
  const PA = pairSet([[0, 9], [6, 3], [2, 11], [5, 8], [4, 1], [10, 7]]);
  const HAE = pairSet([[0, 7], [1, 6], [2, 5], [3, 4], [8, 11], [9, 10]]);
  const SAMHAP = [[8, 0, 4, 4], [2, 6, 10, 1], [5, 9, 1, 3], [11, 3, 7, 0]];
  const BANGHAP = [[2, 3, 4, 0], [5, 6, 7, 1], [8, 9, 10, 3], [11, 0, 1, 4]];
  const HYEONG_SETS = [[[2, 5, 8], "인사신 삼형"], [[1, 10, 7], "축술미 삼형"]];

  const gzName = (i) => STEMS[i % 10] + BRANCHES[i % 12];
  const gzKo = (i) => STEMS_KO[i % 10] + BRANCHES_KO[i % 12];
  const gzIndex = (s, b) => mod(6 * s - 5 * b, 60);
  const parseGz = (t) => gzIndex(STEMS.indexOf(t[0]), BRANCHES.indexOf(t[1]));
  const mainHidden = (b) => HIDDEN[b][2];
  const yearPillarOf = (y) => mod(y - 4, 60);

  function tenGod(ds, os) {
    const rel = mod(STEM_EL[os] - STEM_EL[ds], 5);
    return TEN_GODS[[0, 2, 4, 6, 8][rel] + ((ds % 2) === (os % 2) ? 0 : 1)];
  }
  function lifeStage(ds, b) {
    const st = LIFE_START[ds];
    return LIFE_STAGES[ds % 2 === 0 ? mod(b - st, 12) : mod(st - b, 12)];
  }
  function gongmang(di) { const s = mod(di % 12 - di % 10, 12); return [(s + 10) % 12, (s + 11) % 12]; }

  // ── 날짜 유틸 (UTC 기반 순수 계산) ─────────────────────────────────
  const DAY = 86400;
  function daysFromCivil(y, m, d) { return Math.floor(Date.UTC(y, m - 1, d) / 864e5); }
  function civilFromDays(n) { const t = new Date(n * 864e5); return [t.getUTCFullYear(), t.getUTCMonth() + 1, t.getUTCDate()]; }
  function fmt(sec) { // UTC 초 → "YYYY-MM-DD HH:MM"
    const t = new Date(sec * 1000), p = (x) => String(x).padStart(2, "0");
    return `${t.getUTCFullYear()}-${p(t.getUTCMonth() + 1)}-${p(t.getUTCDate())} ${p(t.getUTCHours())}:${p(t.getUTCMinutes())}`;
  }
  const iso = (y, m, d) => `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  const dayIndexFromDays = (n) => mod(n - daysFromCivil(2000, 1, 1) + 54, 60);
  const hourBranch = (minutes) => Math.floor((minutes + 60) / 120) % 12;
  const hourStem = (di, br) => ((di % 10) % 5 * 2 + br) % 10;

  function equationOfTimeMin(utcSec) {
    const t = new Date(utcSec * 1000);
    const start = Date.UTC(t.getUTCFullYear(), 0, 1);
    const n = Math.floor((t.getTime() - start) / 864e5) + 1;
    const g = 2 * Math.PI / 365 * (n - 1 + (t.getUTCHours() - 12) / 24);
    return 229.18 * (0.000075 + 0.001868 * Math.cos(g) - 0.032077 * Math.sin(g) - 0.014615 * Math.cos(2 * g) - 0.040849 * Math.sin(2 * g));
  }

  function create(cal) {
    const JIE_T = cal.jie.map((x) => x[0]), JIE_B = cal.jie.map((x) => x[1]);
    const TZ = cal.tz; // [[utc, offset]] 오름차순
    const LUN = cal.lunar; // [[startDays, y, m, leap, days]]
    const JOHU = cal.johu;

    function bisectRight(arr, x) { let lo = 0, hi = arr.length; while (lo < hi) { const m = (lo + hi) >> 1; if (x < arr[m]) hi = m; else lo = m + 1; } return lo; }
    function offsetAt(utc) { let off = TZ[0][1]; for (const [t, o] of TZ) { if (utc >= t) off = o; else break; } return off; }

    // 법정 시각(local 초, 즉 그 날짜·시각을 UTC로 읽은 값) → UTC. Python zoneinfo fold=0 과 같은 규칙.
    function localToUtc(local) {
      const warnings = [];
      for (let i = 1; i < TZ.length; i++) {
        const [t, o2] = TZ[i], o1 = TZ[i - 1][1];
        if (o2 > o1 && local >= t + o1 && local < t + o2) {
          warnings.push("입력 시각이 서머타임 전환으로 존재하지 않는 시각이라 전환 후 시각으로 계산했습니다.");
          return { utc: local - o1, offset: o1, warnings };
        }
        if (o2 < o1 && local >= t + o2 && local < t + o1) {
          warnings.push("입력 시각이 서머타임 종료로 두 번 존재하는 시각이라 앞선 시각으로 계산했습니다.");
          return { utc: local - o1, offset: o1, warnings };
        }
      }
      // 일반 구간: 자기일관 오프셋
      let off = offsetAt(local - 9 * 3600);
      for (let k = 0; k < 3; k++) { const o = offsetAt(local - off); if (o === off) break; off = o; }
      return { utc: local - off, offset: off, warnings };
    }
    // 표준 오프셋은 LMT(30472)·+8:30(30600)·+9(32400). +9:30(34200)·+10(36000)은 서머타임.
    const isDst = (offset) => offset === 34200 || offset === 36000;

    function lunarToSolar(y, m, d, leap) {
      const row = LUN.find((r) => r[1] === y && r[2] === m && r[3] === (leap ? 1 : 0));
      if (!row) throw new Error(leap ? `${y}년에는 윤${m}월이 없습니다.` : "존재하지 않는 음력 날짜입니다.");
      if (d < 1 || d > row[4]) throw new Error(`존재하지 않는 음력 날짜입니다: 음력 ${y}년 ${leap ? "윤" : ""}${m}월은 ${row[4]}일까지입니다.`);
      return civilFromDays(row[0] + d - 1);
    }
    function solarToLunar(days) {
      let lo = 0, hi = LUN.length - 1;
      while (lo < hi) { const m = (lo + hi + 1) >> 1; if (LUN[m][0] <= days) lo = m; else hi = m - 1; }
      const r = LUN[lo]; return { year: r[1], month: r[2], leap: !!r[3], day: days - r[0] + 1 };
    }

    function yearMonthPillars(utc) {
      const i = bisectRight(JIE_T, utc) - 1;
      const branch = JIE_B[i];
      let j = i; while (JIE_B[j] !== 2) j--;
      const y = new Date((JIE_T[j] + 9 * 3600) * 1000).getUTCFullYear();
      const yi = yearPillarOf(y);
      const first = ((yi % 10) % 5 * 2 + 2) % 10;
      return [yi, gzIndex((first + mod(branch - 2, 12)) % 10, branch)];
    }
    const JIE_NAMES = { 1: "小寒", 2: "立春", 3: "惊蛰", 4: "清明", 5: "立夏", 6: "芒种", 7: "小暑", 8: "立秋", 9: "白露", 10: "寒露", 11: "立冬", 0: "大雪" };
    function surroundingJie(utc) {
      const i = bisectRight(JIE_T, utc) - 1;
      return [[JIE_NAMES[JIE_B[i]], JIE_T[i]], [JIE_NAMES[JIE_B[i + 1]], JIE_T[i + 1]]];
    }

    function dayHourPillars(lmtSec, mode) {
      const days = Math.floor(lmtSec / DAY);
      const minutes = Math.floor((lmtSec - days * DAY) / 60);
      const br = hourBranch(minutes);
      let dayD = days, baseD = days;
      if (minutes >= 23 * 60) {
        if (mode === "yaja") baseD = days + 1;
        else if (mode === "jeongja") { dayD = days + 1; baseD = days + 1; }
      }
      const di = dayIndexFromDays(dayD);
      return [di, gzIndex(hourStem(dayIndexFromDays(baseD), br), br)];
    }

    function interactions(stems, branches) {
      const out = [], idx = [0, 1, 2, 3].filter((i) => stems[i] !== null);
      for (const a of idx) for (const b of idx) {
        if (a >= b) continue;
        const sa = stems[a], sb = stems[b], ba = branches[a], bb = branches[b], pair = `${POS[a]}-${POS[b]}`;
        const k = fs([sa, sb]), kb = fs([ba, bb]);
        if (STEM_HAP.has(k)) out.push({ type: "천간합", at: pair, chars: STEMS[sa] + STEMS[sb], element: EL_KO[STEM_HAP.get(k)] });
        if (STEM_CHUNG.has(k)) out.push({ type: "천간충", at: pair, chars: STEMS[sa] + STEMS[sb] });
        if (YUKHAP.has(kb)) out.push({ type: "육합", at: pair, chars: BRANCHES[ba] + BRANCHES[bb], element: EL_KO[YUKHAP.get(kb)] });
        if (mod(ba - bb, 12) === 6) out.push({ type: "충", at: pair, chars: BRANCHES[ba] + BRANCHES[bb] });
        if (PA.has(kb)) out.push({ type: "파", at: pair, chars: BRANCHES[ba] + BRANCHES[bb] });
        if (HAE.has(kb)) out.push({ type: "해", at: pair, chars: BRANCHES[ba] + BRANCHES[bb] });
        if (kb === fs([0, 3])) out.push({ type: "형", at: pair, chars: BRANCHES[ba] + BRANCHES[bb], name: "자묘 상형" });
        if (ba === bb && [4, 6, 9, 11].includes(ba)) out.push({ type: "형", at: pair, chars: BRANCHES[ba] + BRANCHES[ba], name: "자형" });
      }
      const present = new Set(idx.map((i) => branches[i]));
      for (const [sang, wang, go, el] of SAMHAP) {
        const have = [sang, wang, go].filter((x) => present.has(x));
        if (have.length === 3) out.push({ type: "삼합", chars: [sang, wang, go].map((x) => BRANCHES[x]).join(""), element: EL_KO[el] });
        else if (have.length === 2 && have.includes(wang)) out.push({ type: "반합", chars: have.slice().sort((a, b) => a - b).map((x) => BRANCHES[x]).join(""), element: EL_KO[el] });
      }
      for (const [a, b, c, el] of BANGHAP) if ([a, b, c].every((x) => present.has(x))) out.push({ type: "방합", chars: BRANCHES[a] + BRANCHES[b] + BRANCHES[c], element: EL_KO[el] });
      for (const [members, name] of HYEONG_SETS) {
        const have = members.filter((x) => present.has(x));
        if (have.length >= 2) out.push({ type: "형", chars: have.map((x) => BRANCHES[x]).join(""), name: name + (have.length === 3 ? "" : "(부분)") });
      }
      return out;
    }

    function sinsal(stems, branches, p60) {
      const ds = stems[2], known = [0, 1, 2, 3].filter((i) => branches[i] !== null), found = [];
      const mark = (name, targets, basis) => { for (const i of known) if (targets.includes(branches[i])) found.push({ name, at: POS[i], char: BRANCHES[branches[i]], basis }); };
      for (const bp of [0, 2]) {
        const b = branches[bp];
        for (const [sang, wang, go] of SAMHAP) if ([sang, wang, go].includes(b)) {
          mark("도화살", [{ 8: 9, 2: 3, 5: 6, 11: 0 }[sang]], POS[bp] + "지");
          mark("역마살", [{ 8: 2, 2: 8, 5: 11, 11: 5 }[sang]], POS[bp] + "지");
          mark("화개살", [go], POS[bp] + "지");
        }
      }
      const cheoneul = { 0: [1, 7], 4: [1, 7], 6: [1, 7], 1: [0, 8], 5: [0, 8], 2: [11, 9], 3: [11, 9], 7: [2, 6], 8: [5, 3], 9: [5, 3] };
      mark("천을귀인", cheoneul[ds], "일간");
      mark("문창귀인", [{ 0: 5, 1: 6, 2: 8, 3: 9, 4: 8, 5: 9, 6: 11, 7: 0, 8: 2, 9: 3 }[ds]], "일간");
      if (ds % 2 === 0) mark("양인살", [{ 0: 3, 2: 6, 4: 6, 6: 9, 8: 0 }[ds]], "일간");
      if (["庚辰", "庚戌", "壬辰", "壬戌", "戊戌"].map(parseGz).includes(p60[2])) found.push({ name: "괴강살", at: "일", char: gzName(p60[2]), basis: "일주" });
      const baekho = ["甲辰", "乙未", "丙戌", "丁丑", "戊辰", "壬戌", "癸丑"].map(parseGz);
      p60.forEach((p, i) => { if (p !== null && baekho.includes(p)) found.push({ name: "백호살", at: POS[i], char: gzName(p), basis: "주" }); });
      const seen = new Set();
      return found.filter((f) => { const k = f.name + "|" + f.at; if (seen.has(k)) return false; seen.add(k); return true; });
    }

    function elementCounts(stems, branches, hidden) {
      const c = [0, 0, 0, 0, 0];
      for (const s of stems) if (s !== null) c[STEM_EL[s]] += 1;
      for (const b of branches) {
        if (b === null) continue;
        if (hidden) {
          const parts = HIDDEN[b].filter((h) => h !== null), ws = parts.length === 2 ? [0.3, 0.7] : [0.2, 0.2, 0.6];
          parts.forEach((h, i) => { c[STEM_EL[h]] += ws[i]; });
        } else c[BRANCH_EL[b]] += 1;
      }
      const o = {}; EL_KO.forEach((k, i) => { o[k] = Math.round(c[i] * 100) / 100; }); return o;
    }

    function daewoon(utc, birthLocal, yearStem, month60, sex) {
      const forward = (yearStem % 2 === 0) === (sex === "male");
      const [[pn, p], [nn, n]] = surroundingJie(utc);
      const days = (forward ? n - utc : utc - p) / DAY;
      const totalMonths = Math.round(days * 4);
      const sy = Math.floor(totalMonths / 12), sm = totalMonths % 12;
      const startSec = birthLocal + Math.round(days * 365.2422 / 3) * DAY;
      const startY = new Date(startSec * 1000).getUTCFullYear();
      const list = [];
      for (let k = 1; k <= 10; k++) {
        const idx = mod(month60 + (forward ? k : -k), 60);
        list.push({ order: k, pillar: gzName(idx), ko: gzKo(idx), age_from: sy + 10 * (k - 1), year_from: startY + 10 * (k - 1) });
      }
      return { direction: forward ? "순행" : "역행", basis_jie: forward ? nn : pn, start_age: { years: sy, months: sm },
        start_date: fmt(startSec).slice(0, 10), list };
    }

    function compute(inp) {
      const warnings = [];
      let [y, m, d] = inp.date.split("-").map(Number);
      const calType = inp.calendar || "solar";
      if (calType === "lunar") [y, m, d] = lunarToSolar(y, m, d, !!inp.leap);
      else if (isNaN(Date.UTC(y, m - 1, d)) || civilFromDays(daysFromCivil(y, m, d)).join() !== [y, m, d].join()) throw new Error("존재하지 않는 날짜입니다.");
      const timeKnown = !!inp.time;
      const [hh, mm] = timeKnown ? inp.time.split(":").map(Number) : [12, 0];
      if (!timeKnown) warnings.push("태어난 시각 미상: 시주를 비우고 정오 기준으로 연·월·일주를 계산했습니다.");
      let lon, lonSrc;
      if (inp.longitude !== undefined && inp.longitude !== null && inp.longitude !== "") { lon = Number(inp.longitude); lonSrc = "직접 입력"; }
      else if (inp.place) { if (!(inp.place in CITY_LON)) throw new Error(`알 수 없는 출생지: ${inp.place}`); lon = CITY_LON[inp.place]; lonSrc = inp.place; }
      else { lon = SEOUL_LON; lonSrc = "서울(기본값)"; }
      const useEot = !!inp.eot, mode = inp.zishi || "yaja";
      const local = daysFromCivil(y, m, d) * DAY + hh * 3600 + mm * 60;
      const lt = localToUtc(local); warnings.push(...lt.warnings);
      const utc = lt.utc;
      const eot = equationOfTimeMin(utc);
      // Python timedelta 와 같게: 마이크로초로 반올림한 뒤 초 미만은 버림
      const lmt = utc + Math.floor(Math.round((lon * 4 + (useEot ? eot : 0)) * 60 * 1e6) / 1e6);
      const lmtFloor = Math.floor(lmt / 60) * 60;
      const [yi, mi] = yearMonthPillars(utc);
      let di, hi = null;
      if (timeKnown) [di, hi] = dayHourPillars(lmtFloor, mode); else di = dayIndexFromDays(daysFromCivil(y, m, d));
      const pillars = [yi, mi, di, hi];
      const stems = pillars.map((p) => (p === null ? null : p % 10)), branches = pillars.map((p) => (p === null ? null : p % 12));
      const ds = stems[2];
      const alternatives = {};
      const [[pn, pu], [nn, nu]] = surroundingJie(utc);
      for (const [name, t] of [[pn, pu], [nn, nu]]) {
        const gap = Math.abs(utc - t) / 60;
        if (gap <= 30) {
          const before = yearMonthPillars(t - 60), after = yearMonthPillars(t + 60);
          warnings.push(`절입(${name}) ${roundHalfEven(gap)}분 거리: 출생 시각 오차에 따라 연·월주가 바뀔 수 있습니다.`);
          alternatives.jie = { name, at_kst: fmt(t + offsetAt(t)), before: before.map(gzName), after: after.map(gzName) };
        }
      }
      if (timeKnown) {
        const minutes = ((lmt / 60) % 1440 + 1440) % 1440;
        const toEdge = Math.min(mod(minutes - 60, 120), 120 - mod(minutes - 60, 120));
        if (toEdge <= 15) {
          warnings.push(`시 경계 ${roundHalfEven(toEdge)}분 거리: 출생 시각·경도 오차에 따라 시주가 바뀔 수 있습니다.`);
          const alt = [];
          for (const sh of [-16, 16]) { const h2 = dayHourPillars(lmtFloor + sh * 60, mode)[1]; if (h2 !== hi) alt.push(gzName(h2)); }
          alternatives.hour = alt;
        }
        const lh = Math.floor(mod(lmtFloor, DAY) / 3600);
        if (lh === 23 || lh === 0) {
          alternatives.zishi = {};
          for (const md of ZISHI_MODES) { const [a, b] = dayHourPillars(lmtFloor, md); alternatives.zishi[md] = { day: gzName(a), hour: gzName(b) }; }
          warnings.push(`자시 구간: 학파에 따라 일주·시주가 달라집니다(적용: ${mode}).`);
        }
      }
      const pillarInfo = (i) => {
        const p = pillars[i]; if (p === null) return null;
        const s = p % 10, b = p % 12;
        return { pillar: gzName(p), ko: gzKo(p),
          stem: { char: STEMS[s], ko: STEMS_KO[s], element: EL_KO[STEM_EL[s]], yin: s % 2 === 1, ten_god: i === 2 ? "일간" : tenGod(ds, s) },
          branch: { char: BRANCHES[b], ko: BRANCHES_KO[b], element: EL_KO[BRANCH_EL[b]], ten_god: tenGod(ds, mainHidden(b)),
            hidden: HIDDEN[b].filter((h) => h !== null).map((h) => STEMS[h]), life_stage: lifeStage(ds, b) } };
      };
      const r = {
        engine: { name: "saju-standard-js", version: "0.1.0" },
        input: { date: inp.date, calendar: calType, leap: !!inp.leap, time: inp.time || null, sex: inp.sex || null, zishi: mode },
        time: { solar_date: iso(y, m, d), utc_offset_hours: lt.offset / 3600, dst: isDst(lt.offset), utc: fmt(utc),
          longitude: lon, longitude_source: lonSrc, equation_of_time_min: Math.round(eot * 10) / 10, eot_applied: useEot,
          local_solar_time: fmt(lmtFloor), prev_jie: { name: pn, kst: fmt(pu + offsetAt(pu)) }, next_jie: { name: nn, kst: fmt(nu + offsetAt(nu)) } },
        pillars: { year: pillarInfo(0), month: pillarInfo(1), day: pillarInfo(2), hour: pillarInfo(3) },
        day_master: { char: STEMS[ds], ko: STEMS_KO[ds], element: EL_KO[STEM_EL[ds]], yin: ds % 2 === 1 },
        elements: { visible: elementCounts(stems, branches, false), with_hidden: elementCounts(stems, branches, true) },
        gongmang: gongmang(di).map((x) => BRANCHES[x]),
        interactions: interactions(stems, branches),
        sinsal: sinsal(stems, branches, pillars),
        alternatives, warnings,
      };
      if (inp.sex === "male" || inp.sex === "female") r.daewoon = daewoon(utc, local, stems[0], mi, inp.sex);
      else warnings.push("성별 미상: 대운(순행/역행)을 계산하지 않았습니다.");
      r.seun = (inp.seunYears || []).map((yy) => { const p = yearPillarOf(yy);
        return { year: yy, pillar: gzName(p), ko: gzKo(p), stem_ten_god: tenGod(ds, p % 10), branch_ten_god: tenGod(ds, mainHidden(p % 12)) }; });
      r._stems = stems; r._branches = branches;
      return r;
    }

    // ── L2 해석 ─────────────────────────────────────────────────────
    const produces = (e) => (e + 1) % 5, controls = (e) => (e + 2) % 5, mother = (e) => mod(e - 1, 5), controller = (e) => mod(e - 2, 5);
    const GROUPS = ["비겁", "식상", "재성", "관성", "인성"];
    const groupOf = (dm, el) => GROUPS[mod(el - dm, 5)];
    const groupEl = (dm, g) => (dm + GROUPS.indexOf(g)) % 5;
    const WEIGHTS = { ys: 10, yb: 10, ms: 10, mb: 30, db: 15, hs: 10, hb: 15 };
    const ROK = [2, 3, 5, 6, 5, 6, 8, 9, 11, 0];
    const YANGIN = { 0: 3, 2: 6, 4: 6, 6: 9, 8: 0 };
    const SANGSIN = { "정관격": ["재성", "인성"], "편관격": ["식상", "인성"], "정재격": ["식상", "관성"], "편재격": ["식상", "관성"],
      "정인격": ["관성", "비겁"], "편인격": ["관성", "비겁"], "식신격": ["재성", "비겁"], "상관격": ["재성", "인성"],
      "건록격": ["관성", "재성", "식상"], "양인격": ["관성"], "월겁격": ["관성", "재성", "식상"] };

    function chartItems(stems, branches) {
      const ds = stems[2], dm = STEM_EL[ds];
      const pos = [["ys", stems[0], true], ["yb", branches[0], false], ["ms", stems[1], true], ["mb", branches[1], false],
        ["db", branches[2], false], ["hs", stems[3], true], ["hb", branches[3], false]];
      const items = pos.filter(([, v]) => v !== null).map(([k, v, isS]) => [k, v, isS, isS ? STEM_EL[v] : STEM_EL[mainHidden(v)]]);
      return [ds, dm, items];
    }
    function weightedElements(stems, branches) {
      const c = [0, 0, 0, 0, 0];
      for (const s of stems) if (s !== null) c[STEM_EL[s]] += 1;
      for (const b of branches) { if (b === null) continue; const parts = HIDDEN[b].filter((h) => h !== null), ws = parts.length === 2 ? [0.3, 0.7] : [0.2, 0.2, 0.6]; parts.forEach((h, i) => { c[STEM_EL[h]] += ws[i]; }); }
      return c;
    }
    function strength(stems, branches) {
      const [, dm, items] = chartItems(stems, branches);
      const sup = (el) => el === dm || el === mother(dm);
      const total = items.reduce((a, [k]) => a + WEIGHTS[k], 0);
      const score = items.reduce((a, [k, , , el]) => a + (sup(el) ? WEIGHTS[k] : 0), 0) * 100 / total;
      const monthEl = items.find(([k]) => k === "mb")[3], dayEl = items.find(([k]) => k === "db")[3];
      const others = items.filter(([k]) => k !== "mb" && k !== "db").map((x) => x[3]);
      const rooted = branches.some((b) => b !== null && HIDDEN[b].some((h) => h !== null && (STEM_EL[h] === dm || STEM_EL[h] === mother(dm))));
      const grade = score >= 80 ? "극신강" : score >= 60 ? "신강" : score >= 40 ? "중화" : score >= 20 ? "신약" : "극신약";
      return { score: Math.round(score * 10) / 10, grade, strong: score >= 50, deuk_ryeong: sup(monthEl), deuk_ji: sup(dayEl),
        deuk_se: others.filter(sup).length * 2 >= others.length, rooted };
    }
    function johu(stems, branches) {
      const ds = stems[2], mb = branches[1];
      const cell = JOHU[STEMS[ds] + BRANCHES[mb]];
      const need = cell.stems, firstEl = STEM_EL[STEMS.indexOf(need[0])];
      const c = weightedElements(stems, branches);
      const climate = [11, 0, 1].includes(mb) ? "한" : [5, 6, 7].includes(mb) ? "난" : "온";
      const needEl = climate === "한" ? 1 : climate === "난" ? 4 : null;
      const priority = [0, 1, 6, 7].includes(mb) && needEl !== null && c[needEl] < 1.0;
      const visS = stems.filter((s) => s !== null);
      const present = [...need].filter((ch) => { const si = STEMS.indexOf(ch); return visS.includes(si) || branches.some((b) => b !== null && HIDDEN[b].includes(si)); });
      return { climate, table_stems: [...need], conditional_stems: [...cell.conditional], evidence: cell.evidence, first_element: EL_KO[firstEl],
        first_element_idx: firstEl, present, priority, basis: `[궁통보감] ${STEMS[ds]}일간 ${BRANCHES[mb]}월 → ${[...need].join("·")}` };
    }

    function gyeokguk(stems, branches, st) {
      const [ds, dm] = chartItems(stems, branches);
      const mb = branches[1];
      const vis = []; stems.forEach((s, i) => { if (s !== null && i !== 2) vis.push([i, s]); });
      const visStems = vis.map((x) => x[1]);
      const merged = (i, s) => vis.some(([j, t]) => j !== i && STEM_HAP.has(fs([s, t])));
      const godFree = (n) => vis.some(([i, s]) => tenGod(ds, s) === n && !merged(i, s));
      const godAny = (n) => vis.some(([, s]) => tenGod(ds, s) === n);
      const grp = (n, free = true) => vis.some(([i, s]) => groupOf(dm, STEM_EL[s]) === n && (!free || !merged(i, s)));
      const grpCount = (n) => vis.filter(([, s]) => groupOf(dm, STEM_EL[s]) === n).length;
      const present = branches.filter((b) => b !== null);
      let name = null, basis = "", also = [];
      if (mb === ROK[ds]) { name = "건록격"; basis = `월지 ${BRANCHES[mb]} = 일간 건록`; }
      else if (ds in YANGIN && mb === YANGIN[ds]) { name = "양인격"; basis = `월지 ${BRANCHES[mb]} = 일간 양인`; }
      else {
        for (const [sang, wang, go, el] of SAMHAP) {
          if ([sang, wang, go].includes(mb) && [sang, wang, go].every((x) => present.includes(x)) && el !== dm) {
            name = tenGod(ds, mainHidden(wang)) + "격";
            basis = `월지 ${BRANCHES[mb]} 포함 ${[sang, wang, go].map((x) => BRANCHES[x]).join("")} 삼합 ${EL_KO[el]}국으로 변격`; break;
          }
        }
        if (name === null) {
          const order = [HIDDEN[mb][2], HIDDEN[mb][1], HIDDEN[mb][0]].filter((h) => h !== null);
          const out = order.filter((h) => visStems.includes(h));
          const pick = out.length ? out[0] : HIDDEN[mb][2];
          name = STEM_EL[pick] === dm ? "월겁격" : tenGod(ds, pick) + "격";
          basis = `월지 ${BRANCHES[mb]} 지장간 ${STEMS[pick]}` + (out.length ? " 투출" : " 정기(미투출)");
          also = out.slice(1).filter((h) => STEM_EL[h] !== dm).map((h) => tenGod(ds, h) + "격");
        }
      }
      let status = "성격", reason = [];
      const set = (s, r) => { status = s; reason = r; };
      if (name === "정관격") {
        if (godFree("편관")) set("파격", ["관살혼잡"]);
        else if (godFree("상관")) {
          if (grp("인성")) grp("재성") ? set("파격", ["상관견관, 인성으로 구했으나 재가 인을 깨뜨림"]) : set("성격", ["상관견관을 인성이 구함(官逢伤而透印以解之)"]);
          else set("파격", ["상관견관"]);
        } else if (vis.some(([i, s]) => tenGod(ds, s) === "정관" && merged(i, s))) set("대기", ["정관이 합으로 묶임"]);
        else if (grp("재성") || grp("인성")) reason = ["재·인이 관을 돕고 지킴(官喜透财以相生, 生印以护官)"];
        else set("성격(하)", ["고관(孤官): 재·인 보좌 없음"]);
        if (godAny("편관") && !godFree("편관")) reason.push("편관이 합으로 제거됨(合杀留官)");
      } else if (name === "편관격") {
        const yb = ds in YANGIN && present.includes(YANGIN[ds]);
        if (godFree("정관")) set("대기", ["관살혼잡: 관이나 살 중 하나를 걸러야 맑아짐(取清)"]);
        else if (grp("식상")) { if (grp("인성") && !grp("재성")) set("대기", ["식신제살 위에 인성이 식신을 누름(七煞逢食制而又逢印)"]); else reason = ["식신제살"]; }
        else if (grp("인성")) grp("재성") ? set("파격", ["살인상생인데 재가 인을 깨뜨림"]) : set("성격", ["살인상생"]);
        else if (yb) reason = ["양인이 칠살을 대적(用刃当煞)"];
        else if (grp("재성")) set("파격", ["칠살이 재를 만나 제어 없음(七煞逢财无制)"]);
        else set("미정", ["제화 없음"]);
      } else if (name === "정재격" || name === "편재격") {
        if (godFree("편관")) grp("식상") ? set("성격", ["재투칠살을 식신이 제어"]) : set("파격", ["재투칠살(财透七煞)"]);
        else if (grpCount("비겁") >= 2) {
          if (grp("식상")) reason = ["재봉겁을 식상이 화함(财逢劫而透食以化之)"];
          else if (grp("관성")) reason = ["재봉겁을 관이 제어(生官以制之)"];
          else set("파격", ["군겁쟁재(财轻比重)"]);
        } else if (grp("관성") && grp("식상")) set("대기", ["재왕생관에 식상이 섞임(露食则杂)"]);
        else reason = [grp("식상") ? "식상생재" : grp("관성") ? "재왕생관" : "재 단독"];
      } else if (name === "정인격" || name === "편인격") {
        if (st && st.strong && godFree("편관")) set("파격", ["신강 인중에 칠살 투출(身强印重而透煞)"]);
        else if (grp("재성")) {
          if (grp("비겁") || !grp("재성", true) || grpCount("인성") > grpCount("재성")) reason = ["재가 인을 치나 겁재·합·인다로 구함(印逢财而劫财以解之)"];
          else if (grp("관성")) set("성격(하)", ["재극인을 관이 통관"]);
          else set("파격", ["재극인"]);
        } else if (grp("관성")) reason = ["관인상생(印喜官煞以相生)"];
        else if (grp("비겁")) reason = ["겁재가 인을 보호(劫才以护印)"];
        else set("성격(하)", ["인 단독"]);
      } else if (name === "식신격") {
        if (grp("인성")) {
          if (grp("재성")) reason = ["재가 인을 제어해 식신을 보호(生财以护食)"];
          else if (godFree("편관")) reason = ["효신을 만났으나 칠살을 취해 격을 이룸(就煞以成格)"];
          else set("파격", ["효신탈식(정인·편인 모두 夺食)"]);
        } else if (grp("재성") && godFree("편관")) set("파격", ["식신생재에 칠살 투출(生财露煞)"]);
        else if (godFree("편관")) reason = ["식신제살"];
        else if (grp("재성")) reason = ["식신생재"];
        else set("성격(하)", ["식신 단독"]);
      } else if (name === "상관격") {
        const jinsu = (ds === 6 || ds === 7) && (mb === 11 || mb === 0);
        if (godFree("정관")) {
          if (jinsu) reason = ["금수상관은 관을 기뻐함(金水独宜)"];
          else if (grp("인성")) set("성격(하)", ["상관견관을 인성이 구함"]);
          else set("파격", ["상관견관(伤官非金水而见官)"]);
        } else if (grp("재성") && godFree("편관")) set("파격", ["상관생재에 칠살 투출"]);
        else if (grp("인성") && grp("재성")) set("대기", ["상관패인에 재가 섞임"]);
        else if (grp("재성")) reason = ["상관생재(生财以化伤)"];
        else if (grp("인성")) reason = ["상관패인(佩印以制伏)"];
        else if (godFree("편관")) reason = ["상관가살"];
        else set("미정", ["재·인 없음"]);
      } else if (name === "양인격") {
        if (!grp("관성")) (grp("재성") && grp("식상")) ? set("성격(하)", ["관살 없이 재와 식상으로 씀(财根深而用伤食)"]) : set("파격", ["양인무관살(阳刃无官煞, 刃格败也)"]);
        else if (grp("식상") && !grp("인성")) set("파격", ["관살을 식상이 제거"]);
        else reason = ["관살이 양인을 제어(阳刃喜官煞以制伏)"];
      } else {
        if (godFree("정관") && godFree("편관")) set("대기", ["관살혼잡: 取清 필요"]);
        else if (godFree("정관")) { if (godFree("상관")) set("파격", ["용관에 상관 투출"]); else if (grp("재성") || grp("인성")) reason = ["용관에 재·인 보좌(透官而逢财印)"]; else set("성격(하)", ["고관"]); }
        else if (godFree("편관")) { if (grp("식상")) reason = ["용살에 제복(透煞而遇制伏)"]; else if (grp("재성")) set("파격", ["용살에 재가 살을 생함"]); else set("미정", ["칠살 제복 필요"]); }
        else if (grp("재성")) grp("식상") ? set("성격", ["용재에 식상(禄劫用财, 须带食伤)"]) : set("성격(하)", ["용재에 식상 없음"]);
        else if (grp("식상")) reason = ["식상 설기(亦为秀气)"];
        else if (grp("인성")) set("파격", ["재관 없이 인만 투출"]);
        else set("미정", ["재·관·식상 없음"]);
      }
      const clash = [0, 2, 3].filter((i) => branches[i] !== null && mod(branches[i] - mb, 12) === 6);
      if (clash.length && ![fs([4, 10]), fs([1, 7])].includes(fs([mb, branches[clash[0]]]))) {
        const others = branches.filter((b, i) => b !== null && i !== 1);
        const pool = new Set([mb, ...others]);
        const rescued = others.some((b) => YUKHAP.has(fs([mb, b]))) || SAMHAP.some(([sg, wg, gg]) =>
          [sg, wg, gg].includes(mb) && pool.has(wg) && [sg, wg, gg].filter((x) => pool.has(x)).length >= 2 && others.some((b) => [sg, wg, gg].includes(b)));
        const cb = BRANCHES[branches[clash[0]]] + BRANCHES[mb];
        if (rescued) reason.push(`월령 충(${cb})을 합이 풀어 줌(三合六合可以解之)`);
        else if (["성격", "성격(하)", "대기"].includes(status)) { status = "파격"; reason.push(`월령 충(${cb})으로 파격(刑冲用神, 尤为破格)`); }
      }
      const sangsin = SANGSIN[name];
      return { name, basis, also, status, reason, sangsin_groups: sangsin, sangsin_elements: sangsin.map((g) => EL_KO[groupEl(dm, g)]), tag: "[자평진전]" };
    }

    function eokbuYongsin(stems, branches, st) {
      const dm = STEM_EL[stems[2]], c = weightedElements(stems, branches);
      const grpW = {}; GROUPS.forEach((g) => { grpW[g] = c[groupEl(dm, g)]; });
      if (st.strong) {
        if (grpW["인성"] > grpW["비겁"]) return ["재성", "인성 과다 → 재성으로 인성 제어"];
        if (grpW["관성"] < 0.8) return grpW["재성"] >= 0.8 ? ["관성", "비겁 과다 → 관성으로 제어"] : ["식상", "비겁 과다 → 식상으로 설기"];
        return ["관성", "비겁 과다 → 관성으로 제어"];
      }
      let heavy = "식상"; for (const k of ["식상", "재성", "관성"]) if (grpW[k] > grpW[heavy]) heavy = k;
      if (heavy === "재성") return ["비겁", "재성 과다 → 비겁으로 감당"];
      return ["인성", `${heavy} 과다 → 인성으로 ${heavy === "식상" ? "설기 차단" : "살인상생"}`];
    }
    function yongsin(stems, branches, st, jh, gk) {
      const dm = STEM_EL[stems[2]], c = weightedElements(stems, branches);
      const [ebGroup, ebWhy] = eokbuYongsin(stems, branches, st), ebEl = groupEl(dm, ebGroup);
      let jong = null;
      if (st.score >= 85 && !stems.some((s) => s !== null && groupOf(dm, STEM_EL[s]) === "관성")) jong = ["종왕격", dm, "일간 세력 극단·관살 무투 → 비겁 순종"];
      else if (st.score <= 15 && !st.rooted) {
        let top = "식상"; for (const g of ["식상", "재성", "관성"]) if (c[groupEl(dm, g)] > c[groupEl(dm, top)]) top = g;
        jong = [{ "식상": "종아격", "재성": "종재격", "관성": "종살격" }[top], groupEl(dm, top), `무근·극약 → ${top} 순종`];
      }
      let chosen, method, why;
      if (jong) [chosen, method, why] = [jong[1], "종격", jong[2]];
      else if (jh.priority) [chosen, method, why] = [jh.first_element_idx, "조후", "한난 극단 + 조후 오행 부족 → 조후 우선"];
      else [chosen, method, why] = [ebEl, "억부", ebWhy];
      const sangsinEls = gk.sangsin_groups.map((g) => groupEl(dm, g));
      const agree = [chosen === ebEl, chosen === jh.first_element_idx, sangsinEls.includes(chosen)].filter(Boolean).length;
      let huisin = mother(chosen); const supportive = [dm, mother(dm)];
      if (method === "억부" && !st.strong && !supportive.includes(huisin)) huisin = chosen === mother(dm) ? dm : mother(dm);
      else if (method === "억부" && st.strong && supportive.includes(huisin)) huisin = produces(chosen);
      return { element: EL_KO[chosen], element_idx: chosen, group: groupOf(dm, chosen), method, reason: why,
        confidence: agree >= 2 ? "높음" : agree === 1 ? "보통" : "낮음",
        huisin: EL_KO[huisin], huisin_idx: huisin, gisin: EL_KO[controller(chosen)], gisin_idx: controller(chosen), strong: st.strong,
        jong: jong ? jong[0] : null,
        candidates: { "억부": { element: EL_KO[ebEl], group: ebGroup, reason: ebWhy, tag: "[적천수]" },
          "조후": { element: jh.first_element, stems: jh.table_stems, tag: "[궁통보감]" },
          "격국상신": { elements: sangsinEls.map((e) => EL_KO[e]), groups: gk.sangsin_groups, tag: "[자평진전]" } } };
    }
    function luckRating(dm, ysd, p60) {
      const ys = ysd.element_idx, hs = ysd.huisin_idx, gs = ysd.gisin_idx, supportive = [dm, mother(dm)];
      const val = (el) => el === ys ? 2 : el === hs ? 1 : el === gs ? -2 : (ysd.method === "억부" && supportive.includes(el) === ysd.strong) ? -1 : 0;
      const v = 0.4 * val(STEM_EL[p60 % 10]) + 0.6 * val(STEM_EL[mainHidden(p60 % 12)]);
      return [Math.round(v * 100) / 100, v >= 0.8 ? "길" : v <= -0.8 ? "흉" : "평"];
    }
    function natalRelations(stems, branches, p60) {
      const ls = p60 % 10, lb = p60 % 12, out = [];
      for (let i = 0; i < 4; i++) {
        const s = stems[i], b = branches[i]; if (s === null) continue;
        const pos = POS[i] + "주", k = fs([ls, s]), kb = fs([lb, b]);
        if (STEM_HAP.has(k)) out.push(`${pos} 천간합(${STEMS[ls]}${STEMS[s]})`);
        if (STEM_CHUNG.has(k)) out.push(`${pos} 천간충(${STEMS[ls]}${STEMS[s]})`);
        if (YUKHAP.has(kb)) out.push(`${pos} 육합(${BRANCHES[lb]}${BRANCHES[b]})`);
        if (mod(lb - b, 12) === 6) out.push(`${pos} 충(${BRANCHES[lb]}${BRANCHES[b]})`);
        if (PA.has(kb)) out.push(`${pos} 파(${BRANCHES[lb]}${BRANCHES[b]})`);
        if (HAE.has(kb)) out.push(`${pos} 해(${BRANCHES[lb]}${BRANCHES[b]})`);
        if (kb === fs([0, 3]) || (lb !== b && HYEONG_SETS.some(([m]) => m.includes(lb) && m.includes(b)))) out.push(`${pos} 형(${BRANCHES[lb]}${BRANCHES[b]})`);
        for (const [sang, wang, go, el] of SAMHAP) if (lb !== b && [sang, wang, go].includes(lb) && [sang, wang, go].includes(b) && (wang === lb || wang === b)) out.push(`${pos} 반합(${BRANCHES[lb]}${BRANCHES[b]}→${EL_KO[el]})`);
      }
      return out;
    }
    function interpretCore(stems, branches) {
      const st = strength(stems, branches), jh = johu(stems, branches), gk = gyeokguk(stems, branches, st);
      return { strength: st, johu: jh, gyeokguk: gk, yongsin: yongsin(stems, branches, st, jh, gk) };
    }
    function interpret(l1) {
      const stems = l1._stems, branches = l1._branches;
      const core = interpretCore(stems, branches), dm = STEM_EL[stems[2]], ys = core.yongsin;
      const tgd = {};
      stems.forEach((s, i) => { if (s !== null && i !== 2) { const g = tenGod(stems[2], s); tgd[g] = (tgd[g] || 0) + 1; } });
      branches.forEach((b) => { if (b !== null) { const g = tenGod(stems[2], mainHidden(b)); tgd[g] = (tgd[g] || 0) + 1; } });
      core.ten_god_distribution = tgd;
      core.palace = { "연주": "조상·초년(~19세)", "월주": "부모·형제·사회(20~39세)", "일주": "본인·배우자(40~59세)", "시주": "자녀·말년(60세~)" };
      if (l1.daewoon) core.daewoon_rating = l1.daewoon.list.map((d) => { const idx = parseGz(d.pillar), [v, label] = luckRating(dm, ys, idx);
        return { pillar: d.pillar, age_from: d.age_from, score: v, rating: label, natal: natalRelations(stems, branches, idx) }; });
      core.seun_rating = (l1.seun || []).map((s) => { const idx = parseGz(s.pillar), [v, label] = luckRating(dm, ys, idx);
        return { year: s.year, pillar: s.pillar, score: v, rating: label, natal: natalRelations(stems, branches, idx) }; });
      return core;
    }

    // ── L3 MBTI ─────────────────────────────────────────────────────
    const TYPES = new Set(); for (const a of "EI") for (const b of "SN") for (const c of "TF") for (const d of "JP") TYPES.add(a + b + c + d);
    const NOTE = "이론적 매핑(가설)입니다. 사주에서 MBTI를 판정하지 않으며, 검증된 상관관계가 아닙니다.";
    function parseType(t) { const raw = String(t || "").trim().toUpperCase(), core = raw.split("-")[0];
      if (!TYPES.has(core) || (raw !== core && !["A", "T"].includes(raw.slice(5)))) throw new Error("MBTI 유형 4글자를 입력하세요 (예: INFP, ENFP-T)."); return core; }
    function parseIdentity(t) { const raw = String(t || "").trim().toUpperCase(); return raw.length === 6 && raw[4] === "-" ? raw[5] : null; }
    function cognitiveStack(t) {
      const [ei, sn, tf, jp] = t, opp = { N: "S", S: "N", T: "F", F: "T" }, flip = (a) => (a === "e" ? "i" : "e");
      const dom = ei === "E" ? [jp === "J" ? tf : sn, "e"] : [jp === "J" ? sn : tf, "i"];
      const aux = [dom[0] === tf ? sn : tf, flip(dom[1])], tert = [opp[aux[0]], dom[1]], inf = [opp[dom[0]], flip(dom[1])];
      return [dom, aux, tert, inf].map(([f, a]) => f + a);
    }
    const TONE = { E: "대화하듯 주고받고, 바로 해볼 수 있는 행동을 제안", I: "생각을 정리할 성찰 질문을 남기고, 혼자 소화할 여지를 둠",
      S: "구체적 사례·시기·숫자로 말함", N: "큰 흐름·의미·가능성부터 말함", T: "근거와 구조를 먼저, 결론을 분명하게",
      F: "마음과 관계의 맥락을 먼저 짚고 공감하며 전달", J: "단계별 계획·우선순위·기한으로 정리", P: "여러 선택지와 작은 실험으로 열어 둠" };
    const IDENTITY_TONE = { T: "주의할 대목은 불안을 키우지 않게 '대비하면 되는 것'으로 말하고, 바로 할 수 있는 작은 다음 걸음과 함께 전달",
      A: "돌려 말하지 않고 핵심부터 직설적으로, 대신 놓치기 쉬운 위험 신호는 분명히 짚음" };
    const GROUP_OF_GOD = { 비견: "비겁", 겁재: "비겁", 식신: "식상", 상관: "식상", 편재: "재성", 정재: "재성", 편관: "관성", 정관: "관성", 편인: "인성", 정인: "인성" };
    const AXIS_SIGNALS = { EI: [{ 식상: 1.0, 비겁: 0.5, 목: 0.3, 화: 0.5 }, { 인성: 1.0, 수: 0.5, 금: 0.3 }],
      SN: [{ 재성: 1.0, 토: 0.5 }, { 인성: 0.7, 상관: 0.6, 수: 0.3 }],
      TF: [{ 관성: 0.6, 재성: 0.5, 금: 0.5 }, { 식신: 0.6, 정인: 0.5, 화: 0.3, 목: 0.3 }],
      JP: [{ 관성: 1.0, 정인: 0.4 }, { 식상: 0.8, 편재: 0.3, 편인: 0.3 }] };
    const THEME = { 비겁: ["자기주도·독립·경쟁", ["Ti", "Fi", "Se"]], 식상: ["표현·창작·말하기", ["Ne", "Se", "Fe"]],
      재성: ["실행·성과·현실 관리", ["Te", "Se", "Si"]], 관성: ["책임·규범·조직 안의 역할", ["Te", "Si", "Fe"]], 인성: ["배움·성찰·내면 정리", ["Ni", "Si", "Ti", "Fi"]] };
    const POSITION_KO = ["주기능", "부기능", "3차 기능", "열등 기능"];
    function mbtiCompare(t, l2, l1) {
      const sig = {};
      for (const [god, n] of Object.entries(l2.ten_god_distribution)) { sig[god] = (sig[god] || 0) + n; const g = GROUP_OF_GOD[god]; sig[g] = (sig[g] || 0) + n; }
      for (const [el, v] of Object.entries(l1.elements.with_hidden)) sig[el] = (sig[el] || 0) + v;
      return Object.entries(AXIS_SIGNALS).map(([axis, [plus, minus]]) => {
        const p = Object.entries(plus).reduce((a, [k, w]) => a + (sig[k] || 0) * w, 0);
        const m = Object.entries(minus).reduce((a, [k, w]) => a + (sig[k] || 0) * w, 0);
        const diff = Math.round((p - m) * 1e6) / 1e6, lean = diff > 0.5 ? axis[0] : diff < -0.5 ? axis[1] : "균형";
        const self = t["EISNTFJP".indexOf(axis[0]) / 2];
        return { axis, saju_lean: lean, saju_score: Math.round(diff * 100) / 100, self, match: lean === "균형" || lean === self };
      });
    }
    function mbtiTiming(t, l1, l2) {
      const stack = cognitiveStack(t), ds = l1._stems[2], dm = STEM_EL[ds];
      const periods = (l1.seun || []).map((s) => ["세운", s.year, s.pillar]).concat((l1.daewoon ? l1.daewoon.list.slice(0, 8) : []).map((d) => ["대운", d.age_from + "세~", d.pillar]));
      return periods.map(([kind, when, pillar]) => {
        const g = groupOf(dm, STEM_EL[mainHidden(BRANCHES.indexOf(pillar[1]))]);
        const [theme, funcs] = THEME[g];
        let best = null; funcs.forEach((f) => { const i = stack.indexOf(f); if (i >= 0 && (best === null || i < best[0])) best = [i, f]; });
        const fn = best ? best[1] : funcs[0], role = best ? POSITION_KO[best[0]] : "새로운 기능";
        return { kind, when, pillar, group: g, theme, function: fn, role, strength: best ? best[0] <= 1 : false };
      });
    }

    function reading(inp) {
      const l1 = compute(inp), l2 = interpret(l1);
      const out = { l1, l2 };
      if (inp.mbti) {
        const t = parseType(inp.mbti), identity = parseIdentity(inp.mbti);
        const rules = [...t].map((c) => TONE[c]); if (identity) rules.push(IDENTITY_TONE[identity]);
        out.mbti = { type: t, identity, stack: cognitiveStack(t), tone: rules, compare: mbtiCompare(t, l2, l1), timing: mbtiTiming(t, l1, l2), note: NOTE };
      }
      return out;
    }

    // 시각 범위(예: 10:00~12:00) 안에서 시주가 달라지는 후보를 모두 찾는다
    function hourCandidates(inp, from, to) {
      const toMin = (s) => { const [h, m] = s.split(":").map(Number); return h * 60 + m; };
      const a = toMin(from), b = toMin(to), seen = new Map();
      for (let t = a; t <= b; t += 1) {
        const hhmm = `${String(Math.floor(t / 60) % 24).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;
        const r = compute(Object.assign({}, inp, { time: hhmm }));
        const key = r.pillars.hour.pillar + "|" + r.pillars.day.pillar;
        if (!seen.has(key)) seen.set(key, { from: hhmm, to: hhmm, hour: r.pillars.hour.pillar, day: r.pillars.day.pillar, minutes: 0 });
        const e = seen.get(key); e.to = hhmm; e.minutes += 1;
      }
      const list = [...seen.values()], total = list.reduce((x, e) => x + e.minutes, 0);
      list.forEach((e) => { e.share = Math.round(e.minutes / total * 100); });
      return list;
    }

    return { compute, interpret, interpretCore, reading, hourCandidates, lunarToSolar, solarToLunar, cognitiveStack, parseType, parseIdentity,
      CITY_LON, consts: { STEMS, STEMS_KO, BRANCHES, BRANCHES_KO, EL_KO, STEM_EL, BRANCH_EL } };
  }
  return { create };
});
