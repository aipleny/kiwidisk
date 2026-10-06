// Print solar-term instants (KST) from adminhelper's astronomy module.
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const a = await import(pathToFileURL(path.join(ROOT, 'ext/adminhelper_saju-engine/mcp/lib/astronomy.mjs')));
const want = [[2024, 315, '입춘'], [2023, 345, '경칩'], [2025, 285, '소한']];
for (const [y, lon, name] of want) {
  const jdUT = a.findSolarTermJD(y, lon);
  const ms = (jdUT - 2440587.5) * 86400000 + 9 * 3600000;
  console.log(name, y, new Date(ms).toISOString().replace('T', ' ').slice(0, 19), 'KST');
}
