
# -*- coding: utf-8 -*-
import requests, json
B = "http://127.0.0.1:8765"

# 1. 创建自定义两步模板
r = requests.post(B+"/api/pipelines", json={
    "name": "My Quick Test",
    "label": "我的极简流水线",
    "emoji": "TEST",
    "steps": [
        {"key":"step1","label":"第一步分析","skill":"comp-prob-analysis","out":"OUT1.md","checkpoint":False,"role":"executor","check":""},
        {"key":"step2","label":"第二步复核","skill":"comp-review","out":"OUT2.md","checkpoint":False,"role":"reviewer","check":""},
    ],
})
print("1.创建模板:", r.status_code, r.json())

# 2. 非法模板校验（重复 key 应被拒）
r2 = requests.post(B+"/api/pipelines", json={
    "name": "bad-template",
    "steps": [{"key":"a","label":"A","skill":"comp-review","out":"X.md"},
              {"key":"a","label":"A2","skill":"comp-review","out":"Y.md"}],
})
print("2.重复key校验(应400):", r2.status_code, r2.json())

# 3. 基于自定义模板创建工作流实例
r3 = requests.post(B+"/api/workflows", json={
    "title": "冒烟测试工作流",
    "template": "my-quick-test",
    "config": {"question": "测试赛题正文"},
})
print("3.创建实例:", r3.status_code, r3.json())

wid = r3.json().get("id")
# 4. 验证实例快照
r4 = requests.get(B+f"/api/workflows/{wid}")
d = r4.json()
print("4.实例快照:", d["template"], [s["key"] for s in d["steps_snapshot"]])

# 5. 编辑模板 → 不影响已建实例
r5 = requests.put(B+"/api/pipelines/my-quick-test", json={
    "steps": [{"key":"only1","label":"只剩一步","skill":"comp-review","out":"Z.md"}]})
print("5.编辑模板:", r5.status_code, r5.json())
r6 = requests.get(B+f"/api/workflows/{wid}").json()
print("6.实例快照不变:", [s["key"] for s in r6["steps_snapshot"]], "(应仍是 step1,step2)")
r7 = requests.get(B+"/api/pipelines").json()
tpl = next(p for p in r7["pipelines"] if p["name"]=="my-quick-test")
print("7.模板已变:", [s["key"] for s in tpl["steps"]], "(应只有 only1)")

# 8. 内置模板保护：删除应被拒
r8 = requests.delete(B+"/api/pipelines/competition")
print("8.删内置(应400):", r8.status_code, r8.json())

# 9. 列表与工作流清单
r9 = requests.get(B+"/api/workflows").json()
print("9.工作流列表:", [(w["id"], w["title"], w["template"]) for w in r9])
print("=== 冒烟完成 ===")
