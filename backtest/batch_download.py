"""
批量下载比赛数据脚本

功能：根据联赛URL下载完场比赛的赛事分析、亚盘、欧赔、大小球数据

使用方式：
    python backtest/batch_download.py --url "https://zq.titan007.com/jsData/matchResult/2025-2026/s36.js?version=2026011816" --rounds 1-10
    python backtest/batch_download.py --league epl --rounds 1-5
    python backtest/batch_download.py --league seria --rounds 1-3
"""

import argparse
import re
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from downloads.downloader import DataDownloader, OddsType

LEAGUE_CODES = {
    "epl": {"code": "s36", "name": "英超"},
    "premier": {"code": "s36", "name": "英超"},
    "england": {"code": "s36", "name": "英超"},
    "seriea": {"code": "s34_2948", "name": "意甲"},
    "italy": {"code": "s34_2948", "name": "意甲"},
    "la_liga": {"code": "s31", "name": "西甲"},
    "spain": {"code": "s31", "name": "西甲"},
    "bundesliga": {"code": "s8", "name": "德甲"},
    "germany": {"code": "s8", "name": "德甲"},
    "ligue1": {"code": "s11", "name": "法甲"},
    "france": {"code": "s11", "name": "法甲"},
}

SEASON_PATTERN = re.compile(r"matchResult/(\d{4}-\d{4})/")
CODE_PATTERN = re.compile(r"/(s\d+(?:_\d+)?)\.js")


def parse_league_url(url):
    """解析联赛URL，提取赛季和联赛代码"""
    season_match = SEASON_PATTERN.search(url)
    code_match = CODE_PATTERN.search(url)

    if not code_match:
        raise ValueError(f"无法从URL中提取联赛代码: {url}")

    season = season_match.group(1) if season_match else "2025-2026"
    code = code_match.group(1)

    league_info = None
    for name, info in LEAGUE_CODES.items():
        if info["code"] == code:
            league_info = info.copy()
            league_info["code"] = code
            league_info["season"] = season
            break

    if not league_info:
        league_info = {"code": code, "name": code, "season": season}

    return league_info


def parse_round_range(round_str):
    """解析轮次范围字符串，如 '1-10' 或 '1,3,5' 或 '5'"""
    rounds = set()
    round_str = round_str.strip()

    if "-" in round_str:
        parts = round_str.split("-")
        start = int(parts[0])
        end = int(parts[1])
        rounds.update(range(start, end + 1))
    elif "," in round_str:
        for r in round_str.split(","):
            rounds.add(int(r.strip()))
    else:
        rounds.add(int(round_str))

    return sorted(rounds)


def fetch_match_list(url):
    """从URL获取比赛列表"""
    import requests

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://zq.titan007.com/",
    }

    try:
        response = requests.get(url, timeout=30, headers=headers)
        response.encoding = "utf-8"

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")

        return response.text
    except Exception as e:
        print(f"获取比赛列表失败: {e}")
        return None


def parse_matches(js_content, target_rounds=None):
    """解析JS内容，提取比赛ID列表

    Args:
        js_content: JS文件内容
        target_rounds: 目标轮次列表，如果为None则下载所有已完成的比赛

    Returns:
        字典: {round_number: [match_id, ...]}
    """
    matches_by_round = {}

    if target_rounds is None:
        target_rounds = set()

    pattern = r'jh\["R_(\d+)"\]\s*=\s*(\[.*?\]);'
    matches = re.findall(pattern, js_content, re.DOTALL)

    for round_num_str, matches_array in matches:
        round_num = int(round_num_str)

        if target_rounds and round_num not in target_rounds:
            continue

        match_pattern = (
            r"\[(\d+),36,-1,\'[^\']*\',(\d+),(\d+),\'([^\']*)\',\'([^\']*)\'"
        )
        round_matches = re.findall(match_pattern, matches_array)

        for match_id, home_id, away_id, score, half_score in round_matches:
            if not score or score == "":
                continue

            if round_num not in matches_by_round:
                matches_by_round[round_num] = []

            matches_by_round[round_num].append(
                {
                    "match_id": match_id,
                    "home_team_id": int(home_id),
                    "away_team_id": int(away_id),
                    "score": score,
                    "half_score": half_score,
                    "datetime": "",
                }
            )

    return matches_by_round


def download_matches(
    matches_by_round,
    base_path,
    use_browser=True,
    download_analysis=True,
    download_handicap=True,
    download_odds=True,
    download_overunder=True,
    delay_between_matches=1,
    delay_between_types=2,
):
    """批量下载比赛数据"""
    downloader = DataDownloader(base_path=base_path)

    total_matches = sum(len(matches) for matches in matches_by_round.values())
    current = 0

    results = {
        "success": [],
        "failed": [],
        "skipped": [],
    }

    for round_num in sorted(matches_by_round.keys()):
        round_matches = matches_by_round[round_num]
        print(f"\n{'=' * 60}")
        print(f"开始下载第 {round_num} 轮，共 {len(round_matches)} 场比赛")
        print(f"{'=' * 60}\n")

        for match in round_matches:
            match_id = match["match_id"]
            current += 1

            print(f"[{current}/{total_matches}] 比赛 {match_id} ({match['score']})")

            match_result = {
                "match_id": match_id,
                "round": round_num,
                "score": match["score"],
                "datetime": match["datetime"],
            }

            try:
                if download_analysis:
                    print(f"  下载分析数据...")
                    result = downloader.download_analysis_data(
                        match_id, use_browser=use_browser
                    )
                    match_result["analysis"] = result.get("status", "unknown")
                    time.sleep(delay_between_matches)

                if download_handicap:
                    print(f"  下载亚盘数据...")
                    result = downloader.download_all_handicap(
                        match_id, use_browser=use_browser
                    )
                    match_result["handicap"] = {
                        "status": result.get("status", "unknown"),
                        "count": sum(
                            1
                            for r in result.get("results", [])
                            if r.get("status") == "success"
                        ),
                    }
                    time.sleep(delay_between_types)

                if download_odds:
                    print(f"  下载欧赔数据...")
                    result = downloader.download_all_odds(
                        match_id, use_browser=use_browser
                    )
                    match_result["odds"] = {
                        "status": result.get("status", "unknown"),
                        "count": sum(
                            1
                            for r in result.get("results", [])
                            if r.get("status") == "success"
                        ),
                    }
                    time.sleep(delay_between_types)

                if download_overunder:
                    print(f"  下载大小球数据...")
                    result = downloader.download_all_overunder(
                        match_id, use_browser=use_browser
                    )
                    match_result["overunder"] = {
                        "status": result.get("status", "unknown"),
                        "count": sum(
                            1
                            for r in result.get("results", [])
                            if r.get("status") == "success"
                        ),
                    }
                    time.sleep(delay_between_types)

                results["success"].append(match_result)
                print(f"  ✓ 下载完成\n")

            except Exception as e:
                print(f"  ✗ 下载失败: {e}\n")
                match_result["error"] = str(e)
                results["failed"].append(match_result)

    return results


def save_download_log(results, base_path):
    """保存下载日志"""
    log_file = Path(base_path) / "download_log.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n下载日志已保存到: {log_file}")


def print_summary(results):
    """打印下载摘要"""
    print(f"\n{'=' * 60}")
    print("下载完成 - 统计摘要")
    print(f"{'=' * 60}")
    print(f"  成功: {len(results['success'])} 场")
    print(f"  失败: {len(results['failed'])} 场")

    if results["success"]:
        print(f"\n成功的比赛ID列表:")
        for r in results["success"]:
            print(f"  - {r['match_id']} (第{r['round']}轮)")

    if results["failed"]:
        print(f"\n失败的场比赛:")
        for r in results["failed"]:
            print(f"  - {r['match_id']}: {r.get('error', '未知错误')}")


def main():
    parser = argparse.ArgumentParser(
        description="批量下载比赛数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 使用URL下载英超1-10轮
    python backtest/batch_download.py --url "https://zq.titan007.com/jsData/matchResult/2025-2026/s36.js?version=2026011816" --rounds 1-10

    # 使用联赛代码下载意甲全部已完比赛
    python backtest/batch_download.py --league seriea

    # 下载西甲特定轮次
    python backtest/batch_download.py --league la_liga --rounds 1,5,10

    # 只下载亚盘数据
    python backtest/batch_download.py --league epl --rounds 1-5 --no-analysis --no-odds --no-overunder

支持的联赛代码:
    epl/premier/england     - 英超 (s36)
    seriea/italy            - 意甲 (s34_2948)
    la_liga/spain           - 西甲 (s31)
    bundesliga/germany      - 德甲 (s8)
    ligue1/france           - 法甲 (s11)
        """,
    )

    parser.add_argument(
        "--url",
        "-u",
        type=str,
        help="联赛数据URL，如 https://zq.titan007.com/jsData/matchResult/2025-2026/s36.js?version=2026011816",
    )

    parser.add_argument(
        "--league",
        "-l",
        type=str,
        choices=list(LEAGUE_CODES.keys()),
        help="联赛代码 (epl, seriea, la_liga, bundesliga, ligue1)",
    )

    parser.add_argument(
        "--rounds",
        "-r",
        type=str,
        default="all",
        help="轮次范围，如 '1-10'、'1,3,5' 或 '5' (默认: all 全部已完比赛)",
    )

    parser.add_argument(
        "--season",
        "-s",
        type=str,
        default="2025-2026",
        help="赛季，格式为YYYY-YYYY (默认: 2025-2026)",
    )

    parser.add_argument(
        "--output", "-o", type=str, help="输出目录 (默认: backtest/data)"
    )

    parser.add_argument(
        "--no-browser", action="store_true", help="不使用Playwright，使用requests请求"
    )

    parser.add_argument("--no-analysis", action="store_true", help="不下载分析数据")

    parser.add_argument("--no-handicap", action="store_true", help="不下载亚盘数据")

    parser.add_argument("--no-odds", action="store_true", help="不下载欧赔数据")

    parser.add_argument("--no-overunder", action="store_true", help="不下载大小球数据")

    parser.add_argument(
        "--delay-match", type=float, default=2, help="场比赛之间的延迟秒数 (默认: 2)"
    )

    parser.add_argument(
        "--delay-type",
        type=float,
        default=3,
        help="不同数据类型之间的延迟秒数 (默认: 3)",
    )

    args = parser.parse_args()

    if not args.url and not args.league:
        parser.error("必须指定 --url 或 --league 参数")

    use_browser = not args.no_browser
    target_rounds = None if args.rounds == "all" else parse_round_range(args.rounds)

    if args.url:
        league_info = parse_league_url(args.url)
        url = args.url
    else:
        league_code = LEAGUE_CODES[args.league]["code"]
        league_name = LEAGUE_CODES[args.league]["name"]
        league_info = {"code": league_code, "name": league_name, "season": args.season}
        url = (
            f"https://zq.titan007.com/jsData/matchResult/{args.season}/{league_code}.js"
        )

    base_path = args.output if args.output else str(Path(__file__).parent / "data")

    print(f"{'=' * 60}")
    print("批量下载比赛数据")
    print(f"{'=' * 60}")
    print(f"联赛: {league_info['name']} ({league_info['code']})")
    print(f"赛季: {league_info['season']}")
    print(f"轮次: {'全部已完比赛' if target_rounds is None else f'第{args.rounds}轮'}")
    print(f"输出目录: {base_path}")
    print(f"使用浏览器: {'是' if use_browser else '否'}")
    print(f"{'=' * 60}\n")

    print("正在获取比赛列表...")

    js_content = fetch_match_list(url)
    if not js_content:
        print("获取比赛列表失败")
        return 1

    matches_by_round = parse_matches(js_content, target_rounds)

    if not matches_by_round:
        print("未找到符合条件的比赛")
        return 0

    total_matches = sum(len(matches) for matches in matches_by_round.values())
    print(f"找到 {total_matches} 场比赛分布在 {len(matches_by_round)} 轮")

    if target_rounds:
        print(f"目标轮次: {sorted(target_rounds)}")
    else:
        print(f"涵盖轮次: {sorted(matches_by_round.keys())}")

    print()

    results = download_matches(
        matches_by_round=matches_by_round,
        base_path=base_path,
        use_browser=use_browser,
        download_analysis=not args.no_analysis,
        download_handicap=not args.no_handicap,
        download_odds=not args.no_odds,
        download_overunder=not args.no_overunder,
        delay_between_matches=args.delay_match,
        delay_between_types=args.delay_type,
    )

    save_download_log(results, base_path)
    print_summary(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
