// Cross-engine saju comparison harness.
// Usage: node compare.mjs [pure|seoul] > out.json
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const EXT = path.join(ROOT, 'ext');
const VENV_PY = path.join(ROOT, 'venv/bin/python');
const MODE = process.argv[2] || 'pure';
const LON = MODE === 'pure' ? 135 : 126.978;

const STEMS = '甲乙丙丁戊己庚辛壬癸';
const BRANCHES = '子丑寅卯辰巳午未申酉戌亥';
function gz(s) {
  if (s == null) return null;
  const t = typeof s === 'string' ? s : JSON.stringify(s);
  const st = [...t].find(c => STEMS.includes(c));
  const br = [...t].find(c => BRANCHES.includes(c));
  return st && br ? st + br : t;
}

const CASES = [
  ['normal',          '1995-08-15 14:30'],
  ['ipchun-before',   '2024-02-04 17:20'],
  ['ipchun-after',    '2024-02-04 17:35'],
  ['gyeongchip-bef',  '2023-03-06 05:30'],
  ['gyeongchip-aft',  '2023-03-06 05:45'],
  ['sohan-before',    '2025-01-05 11:25'],
  ['sohan-after',     '2025-01-05 11:40'],
  ['jasi-2330',       '1990-05-10 23:30'],
  ['jasi-0030',       '1990-05-11 00:30'],
  ['dst-1988',        '1988-07-15 07:50'],
  ['utc830-1958',     '1958-06-15 06:50'],
  ['utc830-1955-jan', '1955-01-15 07:10'],
  ['midnight-2000',   '2000-01-01 00:10'],
  ['hour-boundary',   '1979-11-03 09:05'],
];

function run(cmd, args, input) {
  return execFileSync(cmd, args, { input, encoding: 'utf8', timeout: 60000, stdio: ['pipe', 'pipe', 'pipe'] });
}
const pick = (o) => [o.year, o.month, o.day, o.hour].map(gz).join(' ');

const sajuMod = await import(pathToFileURL(path.join(EXT, 'adminhelper_saju-engine/mcp/lib/saju.mjs')));

const ENGINES = {
  realdev(d, t) {
    const args = [path.join(ROOT, 'saju-src/.claude/skills/saju/engine/manse.cjs'), `${d} ${t} 남`, '--json'];
    if (MODE === 'pure') args.push('표준시'); else args.push(`--lon=${LON}`);
    const r = JSON.parse(run('node', args)).result.palja;
    return pick({ year: r.yearPillar, month: r.monthPillar, day: r.dayPillar, hour: r.hourPillar });
  },
  adminhelper(d, t) {
    const [y, m, dd] = d.split('-').map(Number); const [h, mi] = t.split(':').map(Number);
    const r = sajuMod.computeSaju({ gender: 'male', year: y, month: m, day: dd, hour: h, minute: mi, longitude: LON });
    const g = r.원국.간지; return pick({ year: g.년주, month: g.월주, day: g.일주, hour: g.시주 });
  },
  hermes(d, t) {
    const [y, m, dd] = d.split('-').map(Number); const [h, mi] = t.split(':').map(Number);
    const inp = { calendar: 'solar', leapMonth: false, year: y, month: m, day: dd, timeKnown: true, hour: h, minute: mi,
      sex: 'male', trueSolarTime: MODE !== 'pure', yajaSi: 'standard' };
    if (MODE !== 'pure') inp.longitude = LON;
    const out = JSON.parse(run('node', [path.join(EXT, 'RichardHojunJang_hermes-manseyeok-skill/skills/hermes-saju/scripts/calculate.mjs')], JSON.stringify(inp)));
    if (out.status !== 'ok') return 'ERR:' + (out.message || out.status);
    const p = Object.fromEntries(out.pillars.map(x => [x.label, x.stem + x.branch]));
    return pick(p);
  },
  jeomsin(d, t) {
    if (MODE !== 'pure') return 'n/a(no lon)';
    const out = JSON.parse(run('python3', [path.join(EXT, 'yuling170916_jeomsin-fortune-reader/skills/jeomsin-fortune-reader/scripts/chart_from_gregorian.py'), '--datetime', `${d}T${t}`]));
    return pick(out.pillars);
  },
  destiny(d, t) {
    const out = JSON.parse(run(VENV_PY, [path.join(EXT, 'xodn348_destiny/skills/destiny/scripts/reading.py'), '--birth', `${d}T${t}`, '--lon', String(LON)]));
    const find = (o) => o && typeof o === 'object' ? (o.pillars?.day?.gz ? o.pillars : Object.values(o).map(find).find(Boolean)) : null;
    const p = find(out.personal); return pick({ year: p.year.gz, month: p.month.gz, day: p.day.gz, hour: p.hour.gz });
  },
  samsin(d, t) {
    const out = JSON.parse(run('python3', [path.join(EXT, 'davidchoi0313_samsin-saju/plugins/samsin-saju/skills/saju-reading/scripts/saju_engine.py'),
      '--gender', 'male', '--date', d, '--time-hm', t, '--longitude', String(LON)]));
    const p = out.pillars; const f = x => x ? x.gan + x.zhi : null;
    return pick({ year: f(p.year), month: f(p.month), day: f(p.day), hour: f(p.hour) });
  },
};

const rows = [];
for (const [name, dt] of CASES) {
  const [d, t] = dt.split(' ');
  const row = { case: name, input: dt };
  for (const [en, fn] of Object.entries(ENGINES)) {
    try { row[en] = fn(d, t); } catch (e) { row[en] = 'ERR:' + String(e.message).split('\n')[0].slice(0, 80); }
  }
  rows.push(row);
}
console.log(JSON.stringify({ mode: MODE, longitude: LON, rows }, null, 1));
