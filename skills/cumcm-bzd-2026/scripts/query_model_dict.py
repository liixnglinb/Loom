#!/usr/bin/env python3
"""数模模型字典查询适配器（Stage 3 模型选型用）。

本脚本**不复制、不内嵌**字典数据。它通过路径或环境变量指向用户本地的
`model-dictionary.json`，只读查询，并在每次输出中携带原始许可声明。

字典来源：BZD 数模社《数模模型字典—学习交流版》(5713 条)
获取方式：https://github.com/BZDmathclub/bzd-math-modeling-skills
          skills/论文自查类/bzd-model-dictionary/assets/model-dictionary.json

许可：仅限个人学习、数学建模竞赛研究及非商业交流使用；禁止商用、倒卖、
      二次包装销售或用于商业引流。详见字典文件内的「使用许可」字段。

用法:
    # 按模型名查询
    python query_model_dict.py --model 灰色预测

    # 按大类 / 分组 / 类别浏览
    python query_model_dict.py --category 优化模型 --limit 15
    python query_model_dict.py --category "元启发式与群智能算法"

    # 按适用场景关键词检索
    python query_model_dict.py --scene 小样本 贫信息

    # 输出精简字段（只看判定所需的六维）
    python query_model_dict.py --model Cox --brief

    # 机器可读
    python query_model_dict.py --model ARIMA --json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# 工作流的六维判定框架 -> 字典字段
FIT_FIELDS = {
    "适用场景": "适用场景",
    "数据要求": "数据要求",
    "关键假设": "关键假设",
    "模型输入": "输入",
    "模型输出": "输出",
    "禁忌点": "禁忌点",
    "模型缺陷": "缺陷",
    "检验方法": "检验方法",
}

ALL_FIELDS = [
    "序号", "模型名称", "模型大类", "具体分组", "模型类别",
    "适用场景", "数据要求", "原理讲解", "模型输入", "模型输出",
    "关键假设", "禁忌点", "模型缺陷", "检验方法", "资料使用声明",
]

CANDIDATE_PATHS = [
    "bzd-math-modeling-skills/skills/论文自查类/bzd-model-dictionary/assets/model-dictionary.json",
    "bzd-model-dictionary/assets/model-dictionary.json",
    "assets/model-dictionary.json",
]


class DictNotFound(Exception):
    pass


def resolve_dict(cli_value):
    if cli_value:
        p = Path(cli_value)
        if p.exists():
            return p
        raise DictNotFound(f"指定的字典文件不存在: {p}")

    env = os.environ.get("BZD_MODEL_DICT")
    if env and Path(env).exists():
        return Path(env)

    # 从当前目录向上查找
    here = Path.cwd()
    for base in [here, *here.parents[:4]]:
        for rel in CANDIDATE_PATHS:
            p = base / rel
            if p.exists():
                return p
    raise DictNotFound("未找到 model-dictionary.json")


def normalize(value):
    text = str(value or "").casefold().replace("（", "(").replace("）", ")")
    return re.sub(r"[\s_\-—–·/]+", "", text)


def clean_html(text):
    """字典中部分字段含 <br/> 与标记符号，转为可读文本。"""
    text = str(text or "").replace("<br/>", "\n  ").replace("<br>", "\n  ")
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def score_by_name(record, query):
    q = normalize(query)
    name = normalize(record.get("模型名称"))
    if not q:
        return (0, 0)
    if name == q:
        return (4, 0)
    if q in name:
        return (3, len(name) - len(q))
    if name in q:
        return (2, len(q) - len(name))
    searchable = normalize(" ".join(
        str(record.get(k, "")) for k in ("模型类别", "具体分组", "模型名称")
    ))
    if q in searchable:
        return (1, len(searchable) - len(q))
    return (0, 0)


def score_by_scene(record, query):
    q = normalize(query)
    scene = normalize(record.get("适用场景"))
    if q and q in scene:
        return (2, -len(scene))
    return (0, 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", help="模型名称或别名")
    ap.add_argument("--category", help="模型大类 / 具体分组 / 模型类别")
    ap.add_argument("--scene", help="适用场景关键词")
    ap.add_argument("--dict", dest="dict_path", help="字典文件路径")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--brief", action="store_true", help="只输出六维判定字段")
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    args = ap.parse_args()

    if not any([args.model, args.category, args.scene]):
        print("[FAIL] 至少指定 --model / --category / --scene 之一")
        return 1

    try:
        dict_path = resolve_dict(args.dict_path)
    except DictNotFound as exc:
        print(f"[FAIL] {exc}")
        print()
        print("获取方式：")
        print("  git clone https://github.com/BZDmathclub/bzd-math-modeling-skills.git")
        print("  然后设置环境变量指向字典文件：")
        print("  export BZD_MODEL_DICT=<仓库>/skills/论文自查类/bzd-model-dictionary/assets/model-dictionary.json")
        return 1

    try:
        root = json.loads(dict_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(f"[FAIL] 字典解析失败: {exc}")
        return 1

    data = root.get("数据")
    if not isinstance(data, list):
        print("[FAIL] 字典结构异常：缺少「数据」数组")
        return 1

    # 检索
    ranked = []
    for rec in data:
        rank = 0
        if args.model:
            rank = score_by_name(rec, args.model)[0]
        elif args.category:
            q = normalize(args.category)
            for f in ("模型大类", "具体分组", "模型类别"):
                if q and q in normalize(rec.get(f)):
                    rank = 2 if f == "模型大类" else 3
                    break
        elif args.scene:
            rank = score_by_scene(rec, args.scene)[0]
        if rank:
            ranked.append((rank, -int(rec.get("序号", 0)), rec))

    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    hits = [r for _, _, r in ranked[: max(1, args.limit)]]

    if not hits:
        print(f"[OK] 无匹配（共检索 {len(data)} 条）")
        return 0

    fields = ALL_FIELDS
    if args.brief:
        fields = ["序号", "模型名称", "模型大类", "具体分组", "模型类别"] + list(FIT_FIELDS.keys())

    out_records = []
    for rec in hits:
        item = {}
        for k in fields:
            if k in rec:
                item[k] = clean_html(rec[k]) if k != "序号" else rec[k]
        out_records.append(item)

    payload = {
        "_source": {
            "数据集名称": root.get("数据集名称"),
            "制作方": root.get("制作方"),
            "记录数": root.get("记录数"),
            "字典路径": str(dict_path),
        },
        "_license": {
            "使用许可": root.get("使用许可"),
            "版权与传播声明": str(root.get("版权与传播声明"))[:200] + "…",
        },
        "查询": args.model or args.category or args.scene,
        "匹配总数": len(ranked),
        "返回记录数": len(out_records),
        "数据": out_records,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"字典：{payload['_source']['数据集名称']}（{payload['_source']['记录数']} 条）")
    print(f"查询「{payload['查询']}」→ 匹配 {payload['匹配总数']} 条，返回 {len(out_records)} 条")
    print("=" * 66)
    for rec in out_records:
        print(f"\n[{rec['序号']}] {rec['模型名称']}  （{rec.get('模型类别','-')}）")
        print(f"    大类/分组：{rec.get('模型大类','-')} / {rec.get('具体分组','-')}")
        if not args.brief:
            print(f"    原理：{rec.get('原理讲解','-')}")
        for k in FIT_FIELDS:
            if k in rec:
                label = FIT_FIELDS[k]
                print(f"    {label}：{rec[k]}")
        if rec.get("资料使用声明"):
            print(f"    ⚠ {rec['资料使用声明']}")

    print("\n" + "=" * 66)
    print(f"许可：{payload['_license']['使用许可']}")
    print(f"来源：{payload['_source']['字典路径']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
