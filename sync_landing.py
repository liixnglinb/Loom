# -*- coding: utf-8 -*-
"""同步下载页里写死的兜底版本号。体积单独传，一样带计数断言。

用法：python sync_landing.py <旧版本> <新版本> [新体积MB]
不带第三个参数就不动体积（两版体积常常一样）。
"""
import pathlib
import re
import sys

old_v, new_v = sys.argv[1], sys.argv[2]
size_mb = sys.argv[3] if len(sys.argv) > 3 else None

p = pathlib.Path(r"D:\Voyra 个人网站\public\modelflow\index.html")
s = p.read_text(encoding="utf-8")

n = len(re.findall(re.escape(old_v), s))
assert n == 6, f"预期 6 处 {old_v}，实际 {n}"
s = s.replace(f"Loom-{old_v}-setup.exe", f"Loom-{new_v}-setup.exe")
s = s.replace(f">{old_v}<", f">{new_v}<")
s = s.replace(f"更新至 {old_v}", f"更新至 {new_v}")
assert old_v not in s, f"还剩 {old_v} 没换掉"

if size_mb:
    # 只认这三处安装包体积。页里还有"2.4 MB"（mock 日志与产物文件名）和
    # "约 200 MB 磁盘"（另一件事），按"约 N MB"这种宽匹配会把它们一起改掉。
    anchors = [f'id="heroSize">{{V}} MB<', f'id="btnSize">{{V}} MB<', f"安装包约 {{V}} MB，"]
    cur = None
    for a in anchors:
        pat = a.replace("{V}", r"([\d.]+)")
        found = re.findall(pat, s)
        assert len(found) == 1, f"锚点没命中或命中多处：{a} -> {found}"
        cur = cur or found[0]
        s = re.sub(a.replace("{V}", r"[\d.]+"), a.replace("{V}", size_mb), s)
    print(f"体积 {cur} MB -> {size_mb} MB" if cur != size_mb else f"体积仍是 {cur} MB")

p.write_text(s, encoding="utf-8")
print(f"index.html -> {new_v}（6 处版本号已换）")
