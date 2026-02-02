"""
批量运行Prompt脚本 (v2 - 支持自定义System Prompt - Google GenAI SDK)

功能：读取prompts目录下的prompt文件，使用Google GenAI SDK进行分析，
     将结果保存到backtest/result目录

使用方式：
    export GEMINI_API_KEY="your_api_key"
    python backtest/run_prompts_v2.py --system-prompt-file prompts/prompt5.6
"""

import argparse
import json
import os
import re
import sys
import requests
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("错误: 未找到 google-genai 库。请运行: pip install google-genai")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent))

DEFAULT_PROMPT_DIR = "backtest/prompts"
DEFAULT_RESULT_DIR = "backtest/result"
DEFAULT_MODEL = "gemini-3.0-flash-preview"
DEFAULT_API_KEY = "123456"

# HTTP API 配置 (用于兼容自定义 API 服务)
DEFAULT_API_BASE = "http://localhost:3000"
DEFAULT_API_PATH = "/gemini-cli-oauth/v1/chat/completions"
DEFAULT_API_TOKEN = "123456"

# Default system prompt
SYSTEM_PROMPT_CONTENT = """
✦ 核心定位
    Role: Elite Football Odds Game Theory Engine (v3.4 - Economy Mode Patch)
    版本更新：v3.4 (Economy Mode Patch)
    更新日志：
    1. 继承 v3.3 的“纸老虎（Paper Tiger）”逻辑，继续精准识别中游伪强队。
    2. 新增“经济适用模式（Economy Mode）”协议：修正超级豪门深盘退盘时的误判，不再盲目搏冷门下盘。

    本质：通过亚盘、欧赔、大小球的全链路数据，结合基本面实力锚点（Class Anchor）、市场热度对冲（Flow Hedging）与特定场景协议，输出高置信度的博弈结论。

    核心分析原则 (Updated v3.4)

    1. 实力锚点阶级化（Class Hierarchy）：
        * 超级霸主（Super Hegemon）：联赛 Top 3 或 统治力极强的卫冕冠军（如曼城、皇马）。此类球队具备“控盘赢球”能力，即赢球输盘或刚好卡盘。
        * 真强队（True Class）：Top 6 球队，实力稳健。
        * 伪强队（Pseudo Favorite）：排名中游（如第8-10名），却因主场/名气强行让球给上游球队。
        * 鱼腩部队（Bottom Feeder）：联赛倒数 3 名，缺乏反击能力。

    2. 纸老虎协议（Paper Tiger Protocol）—— *针对伪强队*：
        * 触发条件：低排名主队让球给高排名客队（倒挂盘）。
        * 逻辑判定：若临场退盘（如 -0.5 退 -0.25）或主胜赔率飘升，这是庄家在“戳破泡沫/正向修正”。
        * 策略：坚决打击伪强队，支持高排名受让方（真强队）。

    3. 经济适用模式（Economy Mode Protocol）—— *针对超级霸主*：
        * 触发条件：超级霸主（主） vs 鱼腩部队（客）。
        * 现象：初盘极深（如 -2.5/-2.25），临场大幅退盘（如退至 -1.5），且大小球同步下调（如 3.5 降至 3.0）。
        * 修正逻辑（The Fix）：这 **不是** 庄家看衰霸主不胜，而是预判霸主将“收着踢”或“破密集防守效率低”。庄家将门槛降至 2-0/1-0 的精准赔付点。
        * 策略：首选 **小球 (Under)**，次选霸主赢盘。**严禁** 仅仅因为“盘口便宜”而盲目去下盘（+1.5），因为鱼腩部队极大概率被零封，无法守住门槛。

    4. 免费午餐悖论（The Free Lunch Paradox）—— *一般性原则*：
        * 除上述“经济模式”外，若普通强队面对弱队，门槛异常低且水位舒适，视为诱上陷阱，去下盘。

    分析流程（逻辑重构版 v3.4）

    第一阶段：场景定性（Scenario Definition）
        - 判定对阵双方阶级。
        - 场景 A [纸老虎局]：伪强队 vs 真强队（应用 Paper Tiger 协议）。
        - 场景 B [大卫与其利亚局]：超级霸主 vs 鱼腩部队（应用 Economy Mode 协议）。
        - 场景 C [常规博弈]：普通强弱对话（应用 Free Lunch / 散热逻辑）。

    第二阶段：盘口动态博弈（Handicap Dynamics）
        - 观察亚盘与大小球的 **联动性**：
            - 深盘退盘 + 大小球暴跌 = 豪门小胜（2-0/1-0），走小球逻辑。
            - 伪强队退盘 + 大小球坚挺 = 主队无胜，走客队不败逻辑。
            - 强队升盘 + 水位极低 = 真实看好，正路打出。

    第三阶段：避坑自查（Self-Correction）
        - 只有当客队具备极强反击能力（进球预期 > 1）时，深盘退盘才是诱上。
        - 若客队是“零进球能力”的弱旅，霸主退盘只是在降低“赢球成本”，不可博冷。

    输出项规范（终端输出版）

     - Match_Scenario: 比赛场景定义（如：豪门经济局 / 伪强队现形局）
     - Core_Protocol: 激活的协议 (Economy Mode / Paper Tiger / Standard)
     - Market_Intent: 庄家意图解读 (精准风控 / 诱导散热 / 实力修正)
     - Recommended_Outcome: 推荐赛果 (含亚盘及大小球)
     - Logic_Chain: 核心推理链条
     - Risk_Alert: 特殊风险提示（如：勿博强队穿盘，勿信弱队守盘）
     - Confidence: 置信度

    避坑指南（Directives v3.4）
      1. Don't Fight the Hegemon:
         面对超级霸主打弱队，如果盘口退得很浅（-1.5），不要觉得是陷阱去买弱队。霸主大概率 2-0 让你输掉下盘，同时收割大球盘。此时最优解是 **小球**。
      2. Respect the Anchor:
         积分榜是物理定律。第9名让第3名永远是异常，除非第3名主力全伤。否则一律按“纸老虎”处理。
      3. Volume over Handicap:
         在深盘局中，大小球的变动权重高于亚盘变动。大小球崩塌往往直接剧透了比分（如从4球降至3球，暗示比分封顶 2-0 或 3-0）。
"""


def call_llm(prompt: str, match_id: str, model: str) -> dict:
    """使用Google GenAI SDK调用模型"""
    api_key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or DEFAULT_API_KEY
    )
    if not api_key:
        return {
            "success": False,
            "error": "API Key 未设置。请设置 GEMINI_API_KEY 或 GOOGLE_API_KEY。",
        }

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model=model,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT_CONTENT,
                temperature=0.3,
                max_output_tokens=4096,
            ),
            contents=[prompt],
        )

        if response.text:
            return {"success": True, "data": {"response": response.text}}
        else:
            return {"success": False, "error": "Empty response from model"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def call_llm_http(
    prompt: str,
    match_id: str,
    model: str,
    api_base: str,
    api_path: str,
    api_token: str,
    max_tokens: int = 8192,
) -> dict:
    """使用 HTTP API 调用模型 (兼容自定义 API 服务)

    参考 curl 命令格式:
    curl http://localhost:3000/gemini-cli-oauth/v1/chat/completions \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer 123456" \
      -d '{"model": "gemini-3.0-flash-preview", "messages": [...], "max_tokens": 1000}'
    """
    if not api_base:
        return {"success": False, "error": "API Base URL 未设置"}

    if not api_token:
        return {"success": False, "error": "API Token 未设置"}

    url = f"{api_base.rstrip('/')}{api_path}"

    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT_CONTENT}, {"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)

        if response.status_code == 200:
            data = response.json()

            # 兼容 OpenAI/Gemini CLI 格式的响应
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                content = choice["message"]["content"]
                finish_reason = choice.get("finish_reason", "")

                # 检查是否因达到 max_tokens 而截断
                if finish_reason == "length":
                    print(f"    ⚠️ 警告: 响应达到 max_tokens 限制，内容可能被截断")

                return {"success": True, "data": {"response": content}}
            else:
                return {"success": False, "error": f"响应格式异常: {data}"}
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
            }

    except requests.exceptions.ConnectionError:
        return {"success": False, "error": f"连接失败: 无法连接到 {url}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@dataclass
class RunStats:
    """运行统计"""

    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0


def extract_match_id(filename: str) -> Optional[str]:
    """从文件名提取match_id"""
    match = re.match(r"(\d+)_prompt\.txt", filename)
    return match.group(1) if match else None


def save_result(
    match_id: str,
    response: str,
    result_dir: str = DEFAULT_RESULT_DIR,
) -> str:
    """保存分析结果到文件"""
    Path(result_dir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{match_id}_{timestamp}.md"
    filepath = Path(result_dir) / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(response)

    return str(filepath)


def batch_run(
    prompt_dir: str,
    result_dir: str,
    model: str,
    limit: Optional[int] = None,
    use_http: bool = False,
    api_base: str = DEFAULT_API_BASE,
    api_path: str = DEFAULT_API_PATH,
    api_token: str = DEFAULT_API_TOKEN,
    max_tokens: int = 4096,
) -> RunStats:
    """批量运行prompts"""
    stats = RunStats()

    prompt_path = Path(prompt_dir)
    print(f"[初始化] 检查Prompt目录: {prompt_path}")

    # Ensure result directory exists
    Path(result_dir).mkdir(parents=True, exist_ok=True)

    if not prompt_path.exists():
        print(f"[错误] Prompt目录不存在: {prompt_path}")
        return stats

    prompt_files = list(prompt_path.glob("*_prompt.txt"))
    print(f"[初始化] 找到 {len(prompt_files)} 个prompt文件")

    if not prompt_files:
        print(f"[警告] 目录中无prompt文件: {prompt_path}")
        return stats

    if limit:
        prompt_files = prompt_files[:limit]
        print(f"[初始化] 限制处理前 {limit} 个")

    stats.total = len(prompt_files)
    print(f"[开始] 共 {stats.total} 个文件待处理\n")

    for i, prompt_file in enumerate(prompt_files, 1):
        print(f"-" * 60)
        print(f"[{i}/{stats.total}] 文件: {prompt_file.name}")

        match_id = extract_match_id(prompt_file.name)
        if not match_id:
            print(
                f"[{i}/{stats.total}] {prompt_file.name} - ✗ 跳过（无法提取match_id）"
            )
            stats.skipped += 1
            continue

        print(f"[{i}/{stats.total}] 比赛ID: {match_id}")

        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt_content = f.read()
            print(f"[{i}/{stats.total}] 已读取Prompt文件 ({len(prompt_content)} 字符)")
        except Exception as e:
            print(f"[{i}/{stats.total}] ✗ 读取文件失败: {e}")
            stats.failed += 1
            continue

        # 根据模式调用不同的 API
        if use_http:
            result = call_llm_http(
                prompt_content,
                match_id,
                model,
                api_base,
                api_path,
                api_token,
                max_tokens,
            )
        else:
            result = call_llm(prompt_content, match_id, model)

        if result.get("success"):
            response = result["data"]["response"]
            filepath = save_result(match_id, response, result_dir)
            print(f"[{i}/{stats.total}] ✓ 成功保存到: {filepath}")
            stats.success += 1
        else:
            print(f"[{i}/{stats.total}] ✗ 失败: {result.get('error', '未知错误')}")
            stats.failed += 1

    print(f"-" * 60)
    return stats


def save_stats(stats: RunStats, result_dir: str):
    """保存运行统计"""
    stats_file = Path(result_dir) / "run_stats.json"
    stats_dict = {
        "total": stats.total,
        "success": stats.success,
        "failed": stats.failed,
        "skipped": stats.skipped,
    }
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats_dict, f, ensure_ascii=False, indent=2)
    print(f"\n统计已保存到: {stats_file}")


def print_summary(stats: RunStats):
    """打印摘要"""
    print(f"\n{'=' * 60}")
    print("运行完成 - 统计摘要")
    print(f"{'=' * 60}")
    print(f"  总数: {stats.total}")
    print(f"  成功: {stats.success}")
    print(f"  失败: {stats.failed}")
    print(f"  跳过: {stats.skipped}")


def main():
    global SYSTEM_PROMPT_CONTENT
    parser = argparse.ArgumentParser(
        description="批量运行Prompts并使用Google GenAI SDK进行分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--prompt-dir",
        "-p",
        type=str,
        default=DEFAULT_PROMPT_DIR,
        help=f"Prompt文件目录 (默认: {DEFAULT_PROMPT_DIR})",
    )

    parser.add_argument(
        "--result-dir",
        "-o",
        type=str,
        default=DEFAULT_RESULT_DIR,
        help=f"结果保存目录 (默认: {DEFAULT_RESULT_DIR})",
    )

    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=DEFAULT_MODEL,
        help=f"使用的模型 (默认: {DEFAULT_MODEL})",
    )

    parser.add_argument("--limit", "-l", type=int, help="限制处理数量")

    parser.add_argument(
        "--system-prompt-file",
        type=str,
        help="Path to the system prompt file",
    )

    # HTTP API 模式参数
    parser.add_argument(
        "--http",
        action="store_true",
        default=False,
        help="使用 HTTP API 模式调用模型 (替代 Google GenAI SDK)",
    )

    parser.add_argument(
        "--api-base",
        type=str,
        default=DEFAULT_API_BASE,
        help=f"API Base URL (默认: {DEFAULT_API_BASE})",
    )

    parser.add_argument(
        "--api-path",
        type=str,
        default=DEFAULT_API_PATH,
        help=f"API Path (默认: {DEFAULT_API_PATH})",
    )

    parser.add_argument(
        "--api-token",
        type=str,
        default=DEFAULT_API_TOKEN,
        help=f"API Token (默认: {DEFAULT_API_TOKEN})",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=8192,
        help=f"最大输出 token 数 (默认: 8192)",
    )

    args = parser.parse_args()

    print(f"{'=' * 60}")
    print(f"[配置]")
    print(f"  Prompt目录: {args.prompt_dir}")
    print(f"  结果目录: {args.result_dir}")
    print(f"  模型: {args.model}")
    print(f"  调用模式: {'HTTP API' if args.http else 'Google GenAI SDK'}")
    if args.http:
        print(f"  API Base: {args.api_base}")
        print(f"  API Path: {args.api_path}")
        print(
            f"  API Token: {'***' + args.api_token[-4:] if len(args.api_token) > 4 else '***'}"
        )
        print(f"  Max Tokens: {args.max_tokens}")
    if args.system_prompt_file:
        print(f"  System Prompt: {args.system_prompt_file}")
    print(f"{'=' * 60}\n")

    if args.system_prompt_file:
        try:
            with open(args.system_prompt_file, "r", encoding="utf-8") as f:
                SYSTEM_PROMPT_CONTENT = f.read()
            print(f"[配置] System Prompt loaded from: {args.system_prompt_file}")
        except Exception as e:
            print(f"[错误] Failed to load system prompt: {e}")
            return 1

    prompt_path = Path(args.prompt_dir)
    if not prompt_path.exists():
        print(f"[错误] Prompt目录不存在: {prompt_path}")
        print(f"[提示] 请先运行: python backtest/generate_prompts.py")
        return 1

    prompt_files = list(prompt_path.glob("*_prompt.txt"))
    if not prompt_files:
        print(f"[错误] 目录中无prompt文件: {prompt_path}")
        print(f"[提示] 请先运行: python backtest/generate_prompts.py")
        return 1

    print(f"[检查] 找到 {len(prompt_files)} 个prompt文件\n")

    stats = batch_run(
        prompt_dir=args.prompt_dir,
        result_dir=args.result_dir,
        model=args.model,
        limit=args.limit,
        use_http=args.http,
        api_base=args.api_base,
        api_path=args.api_path,
        api_token=args.api_token,
        max_tokens=args.max_tokens,
    )

    save_stats(stats, args.result_dir)
    print_summary(stats)

    return 0


if __name__ == "__main__":
    sys.exit(main())
