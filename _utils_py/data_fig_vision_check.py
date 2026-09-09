'''数据图视觉自检 — 调 vision LLM 检查 matplotlib 数据图（柱状/折线/散点/热力/箱线等）
是否有坐标轴标签截断、图例压数据、刻度重叠等【影响阅读的硬伤】。

⛔ 与 tikz_vision_check.py（查流程/架构图布局）的区别：数据图关心的是坐标系可读性
   （轴标签/刻度/图例/子图挤压），而非节点连线布局。PROMPT 专为数据图定制，且刻意
   宽容——只报明确影响阅读的硬伤，不挑审美、不对 Sankey/3D/热力图等非常规图型苛求，
   把误报压到最低（数据图形态千奇百怪，误报会白烧额度、逼出无谓的重跑）。

用法:
  python _utils/data_fig_vision_check.py <image.png>

环境变量（按优先级）:
  EDITOR_AI_API_KEY + EDITOR_AI_BASE_URL  (editor_ai 配置)
  OPENAI_API_KEY + OPENAI_BASE_URL        (reviewer 配置)

退出码:
  0 = 通过（PASS）
  1 = 有问题（输出具体问题描述）
  2 = API 不可用（未配置 key 或调用失败）
'''
from __future__ import annotations
import base64
import http.client as http
import json
import os
import ssl
import sys
from pathlib import Path
from urllib.parse import urlparse

PROMPT = '这是一张学术论文里的【数据图】（柱状图/折线图/散点图/热力图/箱线图/子图组合等，由 matplotlib/seaborn 生成）。请只检查【明确影响阅读的硬伤】，不要挑审美，也不要对 Sankey/3D/网络图/自定义布局等非常规图型苛求。逐项核对：\n1. 坐标轴标签、刻度数字是否被截断、超出画布、或被裁掉一半？\n2. 图例（legend）是否压住了数据（曲线/柱子/散点）导致看不清，或跑到画布外被截断？\n3. x/y 轴刻度标签是否互相重叠、叠成一团看不清（尤其长文字或日期）？\n4. 多子图之间是否严重挤压、子图标题与相邻子图内容重叠？\n5. 数据在灰度打印下是否完全无法区分（多条同色系曲线且无不同线型/marker）？\n6. 是否是空图、纯白图、或明显的渲染异常（大片乱码/黑块/报错文字）？\n\n⛔ 判定从宽：只要图能正常读懂、上述硬伤都没有，就判通过。轻微留白、配色偏好、刻度密度等【不影响读懂】的都不算问题。不确定算不算硬伤时，一律判通过。\n\n如果没有上述硬伤，第一行只回答一个词：PASS\n如果确有硬伤，逐条列出，每条以 ISSUE 开头，给出具体位置和该怎么改：\nISSUE 1: [位置] [问题描述] [修复建议]\nISSUE 2: [位置] [问题描述] [修复建议]\n'


def _load_image_b64(img_path: Path):
    '''读取图片→(base64, mime)。超过阈值时用 PIL 等比压缩，避免超 vision API 单图限制；
    PIL 缺失或压缩失败则回退原图。返回 None 表示无法读取（调用方据此跳过）。'''
    _MAX_IMG_BYTES = 3500000
    try:
        data = img_path.read_bytes()
    except Exception:
        return None
    ext = img_path.suffix.lower().lstrip('.')
    mime = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg' }.get(ext, 'image/png')
    if len(data) > _MAX_IMG_BYTES:
        try:
            import io
            from PIL import Image
            with Image.open(io.BytesIO(data)) as im:
                if im.mode not in ('RGB', 'L'):
                    im = im.convert('RGB')
                max_side = max(im.size)
                if max_side > 2200:
                    ratio = 2200.0 / max_side
                    im = im.resize((max(1, int(im.size[0] * ratio)), max(1, int(im.size[1] * ratio))))
                buf = io.BytesIO()
                q = 85
                while q >= 50:
                    buf.seek(0)
                    buf.truncate()
                    im.save(buf, format='JPEG', quality=q, optimize=True)
                    if buf.tell() <= _MAX_IMG_BYTES:
                        break
                    q -= 10
                data = buf.getvalue()
                mime = 'image/jpeg'
        except Exception:
            pass
    return (base64.b64encode(data).decode('ascii'), mime)


def _call_vision(api_base: str, api_key: str, model: str, image_b64: str, mime: str, timeout: int = 60) -> str:
    parsed = urlparse(api_base)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    if not host:
        raise ValueError(f'Bad API base URL: {api_base}')
    path = (parsed.path or '').rstrip('/')
    if '/v1/chat/completions' not in path:
        path = path + '/v1/chat/completions'
    payload = json.dumps({
        'model': model or 'gpt-4o',
        'messages': [
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': PROMPT},
                    {'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{image_b64}'}},
                ],
            },
        ],
        'max_tokens': 2000,
        'stream': False,
    })
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Content-Length': str(len(payload)) }
    conn = None
    try:
        if parsed.scheme == 'https':
            ctx = ssl.create_default_context()
            conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=ctx)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request('POST', path, payload, headers)
        res = conn.getresponse()
        data = res.read()
        if res.status != 200:
            raise Exception(f'HTTP {res.status}: {data.decode("utf-8", errors="replace")[:300]}')
        result = json.loads(data.decode('utf-8'))
        if 'choices' in result and len(result['choices']) > 0:
            if conn:
                conn.close()
            return result['choices'][0]['message']['content']
        raise Exception('No choices in response')
    except Exception:
        if conn:
            conn.close()
        raise


def _is_pass(result: str) -> bool:
    '''判定是否通过。数据图判定刻意宽容：
    - 第一行含 PASS → 通过（与 tikz 口径一致）
    - 或全文没有任何 ISSUE 行 → 也判通过（防 vision 啰嗦地把客套话写第一行、
      实际没列出任何硬伤时被误判为 FAIL 白白触发重跑）。'''
    up = result.upper()
    first = up.split('\n', 1)[0]
    if 'PASS' in first:
        return True
    for line in up.splitlines():
        if line.strip().startswith('ISSUE'):
            return False
    return True


def main():
    if len(sys.argv) < 2:
        print('Usage: python data_fig_vision_check.py <image.png>')
        sys.exit(2)
    img_path = Path(sys.argv[1])
    if not img_path.exists():
        print(f'File not found: {img_path}')
        sys.exit(2)
    loaded = _load_image_b64(img_path)
    if loaded is None:
        print('READ_FAIL: cannot read image — skip')
        sys.exit(2)
    img_b64, mime = loaded
    configs = [
        (os.environ.get('EDITOR_AI_API_KEY', ''),
         os.environ.get('EDITOR_AI_BASE_URL', ''),
         os.environ.get('EDITOR_AI_MODEL_ID', 'gpt-4o')),
        (os.environ.get('OPENAI_API_KEY', ''),
         os.environ.get('OPENAI_BASE_URL', ''),
         os.environ.get('REVIEWER_MODEL_ID', 'gpt-4o')), ]
    for api_key, api_base, model in configs:
        if not (api_key and api_base):
            continue
        try:
            result = _call_vision(api_base, api_key, model, img_b64, mime)
            print(result)
            sys.exit(0 if _is_pass(result) else 1)
        except Exception as e:
            print(f'Vision API error: {e}', file=sys.stderr)
    print('NO_VISION_API: No vision-capable LLM configured (need EDITOR_AI_API_KEY or OPENAI_API_KEY)')
    sys.exit(2)


if __name__ == '__main__':
    main()