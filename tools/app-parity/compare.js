// JS 엔진(app/saju-engine.js) ↔ Python 엔진 결과 대조.
// 사용: node compare.js expected.json
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..", "..");
const SajuEngine = require(path.join(ROOT, "app", "saju-engine.js"));
const cal = JSON.parse(fs.readFileSync(path.join(ROOT, "app", "data", "calendar.json"), "utf8"));
const E = SajuEngine.create(cal);
const cases = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));

const round = (v) => (typeof v === "number" ? Math.round(v * 100) / 100 : v);
function norm(x) {
  if (Array.isArray(x)) return x.map(norm);
  if (x && typeof x === "object") { const o = {}; for (const k of Object.keys(x).sort()) if (!k.startsWith("_")) o[k] = norm(x[k]); return o; }
  return round(x);
}
function diff(a, b, p, out) {
  if (out.length > 4) return;
  if (Array.isArray(a) || Array.isArray(b)) {
    if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) { out.push(`${p}: ${JSON.stringify(a)} ≠ ${JSON.stringify(b)}`); return; }
    a.forEach((v, i) => diff(v, b[i], `${p}[${i}]`, out)); return;
  }
  if (a && b && typeof a === "object" && typeof b === "object") {
    for (const k of new Set([...Object.keys(a), ...Object.keys(b)])) diff(a[k], b[k], `${p}.${k}`, out); return;
  }
  if (JSON.stringify(a) !== JSON.stringify(b)) out.push(`${p}: ${JSON.stringify(a)} ≠ ${JSON.stringify(b)}`);
}
const SKIP_L1 = new Set(["engine"]);
let ok = 0; const fails = [];
for (const c of cases) {
  const i = c.input;
  const r = E.reading({ date: i.date, time: i.time, calendar: i.calendar, leap: i.leap, sex: i.sex, zishi: i.zishi, place: i.place,
    eot: i.eot, seunYears: i.seun_years, mbti: i.mbti });
  const got = { l1: Object.fromEntries(Object.entries(r.l1).filter(([k]) => !SKIP_L1.has(k))), l2: r.l2,
    mbti: { stack: r.mbti.stack, compare: r.mbti.compare,
      timing: r.mbti.timing.map((t) => ({ kind: t.kind, when: t.when, pillar: t.pillar, group: t.group, theme: t.theme, function: t.function, role: t.role })) } };
  const e = c.expected;
  const expL1 = Object.fromEntries(Object.entries(e.l1).filter(([k]) => !SKIP_L1.has(k)));
  delete expL1.input.time; delete got.l1.input.time;
  const exp = { l1: expL1, l2: e.l2, mbti: { stack: e.mbti.stack, compare: e.mbti.compare.map((a) => ({ axis: a.axis, saju_lean: a.saju_lean, saju_score: a.saju_score, self: a.self, match: a.match })),
    timing: e.mbti.timing.map((t) => ({ kind: t.kind, when: t.when, pillar: t.pillar, group: t.group, theme: t.theme, function: t.function, role: t.role })) } };
  const out = []; diff(norm(got), norm(exp), "", out);
  if (out.length === 0) ok++; else if (fails.length < 8) fails.push({ input: i, diffs: out });
}
console.log(`parity ${ok}/${cases.length}`);
for (const f of fails) console.log(JSON.stringify(f.input), "\n   " + f.diffs.join("\n   "));
process.exit(ok === cases.length ? 0 : 1);
