"""Print lunar-python solar-term instants (library time, i.e. UTC+8) and the same instant in KST."""
import glob
import os
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
vendor = glob.glob(os.path.join(ROOT, "ext/davidchoi0313_samsin-saju/plugins/samsin-saju/skills/saju-reading/scripts/vendor/lunar-python-*"))[0]
sys.path.insert(0, vendor)
from lunar_python import Solar  # noqa: E402

for y, name in [(2024, "立春"), (2023, "惊蛰"), (2025, "小寒"), (2024, "惊蛰"), (1988, "小暑")]:
    table = Solar.fromYmd(y, 6, 1).getLunar().getJieQiTable()
    # table keys may hold the term for the lunar year; pick the one in calendar year y
    for k, s in table.items():
        if k.upper() == name.upper() or k == name:
            if s.getYear() == y:
                cst = datetime(s.getYear(), s.getMonth(), s.getDay(), s.getHour(), s.getMinute(), s.getSecond())
                print(name, y, "lib:", cst, "-> KST:", cst + timedelta(hours=1))
    if y == 2025:
        s = Solar.fromYmd(2025, 1, 10).getLunar().getJieQiTable().get("小寒")
        print("小寒 2025 (alt)", s.toYmdHms() if s else None)
