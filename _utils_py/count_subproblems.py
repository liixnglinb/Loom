# -*- coding: utf-8 -*-
"""count_subproblems.py —— 统一"子问题数量"计数器（count_subproblems.sh 的 Python 等价版）。
仅数 Markdown 顶层标题行里的子问题声明，按编号去重。
用法：python count_subproblems.py <file.md>
输出：一个整数（去重后的子问题数），文件不存在/无法解析输出 0。
"""
import re
import sys
from pathlib import Path


def count_subproblems(text: str) -> int:
    seen = set()
    # 只处理标题行：以一个或多个 # 开头
    for line in text.splitlines():
        if not re.match(r'^#{1,4}\s', line):
            continue
        # 中文「问题X」：问题 后跟中文数字 或 阿拉伯数字
        m = re.search(r'问题[一二三四五六七八九十0-9]+', line)
        if m:
            seen.add(m.group(0))
            continue
        # 英文 Problem N / Question N（去空格、小写归一）
        m = re.search(r'(?:problem|question)\s*[0-9]+', line, re.IGNORECASE)
        if m:
            seen.add(re.sub(r'\s+', '', m.group(0).lower()))
    return len(seen)


def main():
    if len(sys.argv) < 2:
        print(0)
        return 0
    p = Path(sys.argv[1])
    if not p.is_file():
        print(0)
        return 0
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        print(0)
        return 0
    print(count_subproblems(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())