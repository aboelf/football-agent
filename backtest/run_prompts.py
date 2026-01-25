"""
批量运行Prompt脚本

功能：读取prompts目录下的prompt文件，使用local-gemini模型进行分析，
     将结果保存到backtest/result目录

使用方式：
    python backtest/run_prompts.py                           # 处理所有prompts
    python backtest/run_prompts.py --limit 5                 # 限制数量
    python backtest/run_prompts.py --prompt-dir ./custom_prompts  # 指定prompt目录
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))

DEFAULT_PROMPT_DIR = "backtest/prompts"
DEFAULT_RESULT_DIR = "backtest/result"
DEFAULT_MODEL = "gemini-3.0-flash"

# OpenAI客户端配置（用于本地Gemini）
OPENAI_CLIENT = OpenAI(
    base_url="http://127.0.0.1:8045/v1",
    api_key="sk-ce335b5133fb4daf8a6dfa35311e93dd",
)

OPENAI_MODEL = "gemini-3-flash"


def call_llm(prompt: str, match_id: str) -> dict:
    """使用OpenAI客户端调用本地Gemini模型"""
    try:
        response = OPENAI_CLIENT.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "你是一位精通博弈论的足彩分析专家，请根据提供的比赛数据和赔率信息进行专业的博弈论分析。分析要逻辑清晰，有理有据。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        ai_response = response.choices[0].message.content
        return {"success": True, "data": {"response": ai_response}}
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
) -> RunStats:
    """批量运行prompts"""
    stats = RunStats()

    prompt_path = Path(prompt_dir)
    print(f"[初始化] 检查Prompt目录: {prompt_path}")

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

        result = call_llm(prompt_content, match_id)

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
    parser = argparse.ArgumentParser(
        description="批量运行Prompts并使用local-gemini模型分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 处理所有prompts
    python backtest/run_prompts.py

    # 只处理前5个
    python backtest/run_prompts.py --limit 5

    # 指定prompt目录
    python backtest/run_prompts.py --prompt-dir ./my_prompts

    # 指定结果目录
    python backtest/run_prompts.py --result-dir ./my_results

    # 使用其他模型
    python backtest/run_prompts.py --model gemini-3.0-pro
        """,
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

    args = parser.parse_args()

    print(f"{'=' * 60}")
    print(f"[配置]")
    print(f"  Prompt目录: {args.prompt_dir}")
    print(f"  结果目录: {args.result_dir}")
    print(f"  模型: {args.model}")
    print(f"{'=' * 60}\n")

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
    )

    save_stats(stats, args.result_dir)
    print_summary(stats)

    return 0


if __name__ == "__main__":
    sys.exit(main())
