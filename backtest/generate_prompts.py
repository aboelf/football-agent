"""
批量生成Prompt脚本

功能：读取backtest/data目录下的分析数据，生成博弈论分析prompt

使用方式：
    python backtest/generate_prompts.py --regen                          # 处理所有比赛
    python backtest/generate_prompts.py --match-id 2789305        # 处理指定比赛
    python backtest/generate_prompts.py --rounds 18               # 处理第18轮
    python backtest/generate_prompts.py --limit 5                 # 限制数量
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from prompts.prompt_generator import GameTheoryPromptGenerator


@dataclass
class GenerationStats:
    """生成统计"""

    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0


def extract_match_id(filename: str) -> Optional[str]:
    """从文件名提取match_id"""
    match = re.match(r"(\d+)_\d+\.html", filename)
    return match.group(1) if match else None


def get_match_ids_from_rounds(rounds_str: str) -> set:
    """根据轮次获取比赛ID列表"""
    from backtest.batch_download import fetch_match_list, parse_matches

    round_nums = set()
    if "-" in rounds_str:
        parts = rounds_str.split("-")
        start = int(parts[0])
        end = int(parts[1])
        round_nums.update(range(start, end + 1))
    elif "," in rounds_str:
        for r in rounds_str.split(","):
            round_nums.add(int(r.strip()))
    else:
        round_nums.add(int(rounds_str))

    url = (
        "https://zq.titan007.com/jsData/matchResult/2025-2026/s36.js?version=2026011816"
    )
    js_content = fetch_match_list(url)
    if not js_content:
        return set()

    matches_by_round = parse_matches(js_content, target_rounds=round_nums)
    match_ids = set()
    for round_matches in matches_by_round.values():
        for match in round_matches:
            match_ids.add(match["match_id"])

    return match_ids


def load_existing_basic_data(data_dir: str) -> Dict[str, Dict]:
    """直接读取已有的basic_data.json文件"""
    basic_data_file = Path(data_dir) / "basic_data.json"
    if not basic_data_file.exists():
        return {}

    with open(basic_data_file, "r", encoding="utf-8") as f:
        content = json.load(f)

    basic_data_dict = {}
    if isinstance(content, list):
        for match in content:
            match_id = match.get("match_info", {}).get("match_id")
            if match_id:
                basic_data_dict[match_id] = match
    elif isinstance(content, dict):
        match_id = content.get("match_info", {}).get("match_id")
        if match_id:
            basic_data_dict[match_id] = content

    return basic_data_dict


def generate_basic_data(data_dir: str) -> Dict[str, Dict]:
    """从analysis目录解析HTML文件，生成basic_data.json"""
    from parsers.analysis_parser import process_all_analyses

    basic_data_file = Path(data_dir) / "basic_data.json"
    analysis_dir = Path(data_dir) / "analysis"

    if not analysis_dir.exists():
        print(f"警告: 分析数据目录不存在: {analysis_dir}")
        return {}

    basic_data_dict = load_existing_basic_data(data_dir)
    existing_count = len(basic_data_dict)

    html_files = list(analysis_dir.glob("*.html"))
    if not html_files:
        print(f"警告: 目录中无HTML文件: {analysis_dir}")
        return {}

    print(f"检测到 {len(html_files)} 个分析文件...")
    if existing_count > 0:
        print(f"现有basic_data.json包含 {existing_count} 场比赛数据")

    process_all_analyses(str(analysis_dir), str(basic_data_file))

    basic_data_dict = load_existing_basic_data(data_dir)
    print(f"生成/更新后共 {len(basic_data_dict)} 场比赛的基本面数据")

    return basic_data_dict


def generate_single_prompt(
    match_id: str,
    generator: GameTheoryPromptGenerator,
) -> Optional[str]:
    """为单个比赛生成prompt"""
    try:
        prompt = generator.generate(match_id)
        return prompt
    except Exception as e:
        print(f"  错误: {e}")
        import traceback

        traceback.print_exc()
        return None


def batch_generate(
    data_dir: str,
    output_dir: str,
    match_ids: Optional[List[str]] = None,
    limit: Optional[int] = None,
    force_regen: bool = False,
) -> GenerationStats:
    """批量生成prompt"""
    stats = GenerationStats()

    basic_data_dict = load_existing_basic_data(data_dir)
    if not basic_data_dict or force_regen:
        print("正在从analysis目录生成/更新basic_data.json...")
        basic_data_file = Path(data_dir) / "basic_data.json"
        if basic_data_file.exists():
            basic_data_file.unlink()
            print(f"已删除现有文件: {basic_data_file}")
        basic_data_dict = generate_basic_data(data_dir)

    if not basic_data_dict:
        print("错误: 无法获取基本面数据")
        return stats

    if match_ids:
        target_match_ids = [mid for mid in match_ids if mid in basic_data_dict]
    else:
        target_match_ids = list(basic_data_dict.keys())

    if limit:
        target_match_ids = target_match_ids[:limit]

    stats.total = len(target_match_ids)
    print(f"开始生成Prompt，共 {stats.total} 场比赛\n")

    generator = GameTheoryPromptGenerator(data_dir)

    for i, match_id in enumerate(target_match_ids, 1):
        match_info = basic_data_dict.get(match_id, {}).get("match_info", {})
        home_team = match_info.get("home_team", "N/A")
        away_team = match_info.get("away_team", "N/A")

        print(
            f"[{i}/{stats.total}] {home_team} vs {away_team} ({match_id})...", end=" "
        )

        prompt = generate_single_prompt(match_id, generator)

        if prompt:
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"{match_id}_prompt.txt")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(prompt)
            print(f"✓")
            stats.success += 1
        else:
            print("✗ 跳过")
            stats.skipped += 1

    return stats


def save_stats(stats: GenerationStats, output_dir: str):
    """保存生成统计"""
    stats_file = os.path.join(output_dir, "generation_stats.json")
    stats_dict = {
        "total": stats.total,
        "success": stats.success,
        "failed": stats.failed,
        "skipped": stats.skipped,
    }
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats_dict, f, ensure_ascii=False, indent=2)
    print(f"\n统计已保存到: {stats_file}")


def print_summary(stats: GenerationStats):
    """打印摘要"""
    print(f"\n{'=' * 60}")
    print("生成完成 - 统计摘要")
    print(f"{'=' * 60}")
    print(f"  总数: {stats.total}")
    print(f"  成功: {stats.success}")
    print(f"  跳过: {stats.skipped}")
    print(f"  失败: {stats.failed}")


def main():
    parser = argparse.ArgumentParser(
        description="批量生成博弈论分析Prompt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 处理所有比赛
    python backtest/generate_prompts.py

    # 强制重新生成basic_data.json后再生成prompts
    python backtest/generate_prompts.py --regen

    # 处理指定比赛
    python backtest/generate_prompts.py --match-id 2789305

    # 处理多个指定比赛
    python backtest/generate_prompts.py --match-id 2789305 2789306 2789307

    # 处理第18轮比赛
    python backtest/generate_prompts.py --rounds 18

    # 处理前5场比赛
    python backtest/generate_prompts.py --limit 5

    # 指定输出目录
    python backtest/generate_prompts.py --output /path/to/prompts
        """,
    )

    parser.add_argument(
        "--data-dir",
        "-d",
        type=str,
        default="backtest/data",
        help="数据根目录 (默认: backtest/data)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="backtest/prompts",
        help="输出目录 (默认: backtest/prompts)",
    )

    parser.add_argument(
        "--match-id", "-m", type=str, nargs="+", help="指定比赛ID (可多个)"
    )

    parser.add_argument(
        "--rounds", "-r", type=str, help="指定轮次，如 '18' 或 '1-5' 或 '1,3,5'"
    )

    parser.add_argument("--limit", "-l", type=int, help="限制处理数量")

    parser.add_argument(
        "--regen",
        "-R",
        action="store_true",
        help="强制重新生成basic_data.json（删除后从HTML重新解析）",
    )

    args = parser.parse_args()

    match_ids = None

    if args.match_id:
        match_ids = args.match_id
    elif args.rounds:
        match_ids = list(get_match_ids_from_rounds(args.rounds))
        if not match_ids:
            print("未找到指定轮次的比赛")
            return 1
        print(f"从第{args.rounds}轮获取到 {len(match_ids)} 场比赛")

    stats = batch_generate(
        data_dir=args.data_dir,
        output_dir=args.output,
        match_ids=match_ids,
        limit=args.limit,
        force_regen=args.regen,
    )

    save_stats(stats, args.output)
    print_summary(stats)

    return 0


if __name__ == "__main__":
    sys.exit(main())
