import re
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from bs4 import BeautifulSoup

# python -m parsers.analysis_parser  重新生成basic_data.json


@dataclass
class MatchBasicInfo:
    match_id: str = ""
    home_team: str = ""
    away_team: str = ""
    league: str = ""
    round_num: str = ""
    match_time: str = ""
    final_score: str = ""
    half_score: str = ""
    venue: str = ""
    weather: str = ""
    temperature: str = ""
    home_recent_ratings: List[float] = field(default_factory=list)
    away_recent_ratings: List[float] = field(default_factory=list)


@dataclass
class TeamStats:
    team_name: str  # e.g., "伯恩茅斯"
    rank: int  # e.g., 15
    matches: int  # total matches played
    wins: int  # of wins
    draws: int  # of draws
    losses: int  # of losses
    goals_for: int  # goals scored
    goals_against: int  # goals conceded
    goal_diff: int  # goal difference
    points: int  # total points
    win_rate: float  # win rate percentage


@dataclass
class MatchRecord:
    date: str
    league: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    score_line: str
    handicap: str
    result: int


@dataclass
class GoalTimeStats:
    """进球时间统计数据"""

    time_periods: List[str] = field(
        default_factory=lambda: [
            "1-10",
            "11-20",
            "21-30",
            "31-40",
            "41-45",
            "46-50",
            "51-60",
            "61-70",
            "71-80",
            "81-90+",
        ]
    )
    total: List[int] = field(default_factory=list)  # 10个时间段的总进球数
    home: List[int] = field(default_factory=list)  # 主队进球数
    away: List[int] = field(default_factory=list)  # 客队进球数


@dataclass
class GoalTimingData:
    """完整的进球时间数据"""

    goals_for: GoalTimeStats = field(default_factory=GoalTimeStats)  # 进球时间
    first_goal_for: GoalTimeStats = field(default_factory=GoalTimeStats)  # 首个进球
    goals_against: GoalTimeStats = field(default_factory=GoalTimeStats)  # 失球时间
    first_goal_against: GoalTimeStats = field(default_factory=GoalTimeStats)  # 首个失球


@dataclass
class RecentRecord:
    """近期战绩统计"""

    label: str  # 如 "近6"
    matches: int  # 场次
    wins: int  # 胜
    draws: int  # 平
    losses: int  # 负
    goals_for: int  # 进球
    goals_against: int  # 失球


@dataclass
class BasicData:
    match_info: MatchBasicInfo
    home_team_full_stats: TeamStats
    away_team_full_stats: TeamStats
    home_team_home_stats: TeamStats
    away_team_away_stats: TeamStats
    recent_matches_home: List[MatchRecord]
    recent_matches_away: List[MatchRecord]
    h2h_records: List[MatchRecord]
    league_table: List[Dict]
    home_recent_6: Optional[RecentRecord] = None  # 主队近6场统计
    away_recent_6: Optional[RecentRecord] = None  # 客队近6场统计
    goal_timing: Optional[GoalTimingData] = None  # 进球时间统计数据


def parse_js_array_manual(js_array: str) -> List[List]:
    result = []
    current = []
    in_string = False
    string_char = ""
    depth = 0
    last_was_bracket = False
    i = 0

    while i < len(js_array):
        char = js_array[i]

        if not in_string:
            if char in "\"'":
                in_string = True
                string_char = char
                current.append(char)
            elif char == "[":
                depth += 1
                current.append(char)
                last_was_bracket = True
            elif char == "]":
                depth -= 1
                current.append(char)
                last_was_bracket = True
                if depth == 1:
                    try:
                        item = "".join(current).strip()
                        if item:
                            result.append(item)
                    except:
                        pass
                    current = []
            elif char == "," and depth == 1 and not last_was_bracket:
                try:
                    item = "".join(current).strip()
                    if item:
                        result.append(item)
                except:
                    pass
                current = []
            else:
                current.append(char)
                last_was_bracket = False
        else:
            if char == string_char and js_array[i - 1] != "\\":
                in_string = False
            current.append(char)

        i += 1

    if current:
        item = "".join(current).strip()
        if item:
            result.append(item)

    parsed_items = []
    for item in result:
        item = item.strip().strip(",")
        if item and item != ",":
            try:
                if item.startswith("[") and item.endswith("]"):
                    item = item[1:-1]
                parts = []
                in_string = False
                string_char = ""
                current = ""
                depth = 0

                for j, char in enumerate(item):
                    if not in_string:
                        if char in "\"'":
                            in_string = True
                            string_char = char
                            current += char
                        elif char == "[":
                            depth += 1
                            current += char
                        elif char == "]":
                            depth -= 1
                            current += char
                        elif char == "," and depth == 0:
                            parts.append(current.strip())
                            current = ""
                        else:
                            current += char
                    else:
                        if char == string_char and (
                            j < len(item) - 1 and item[j + 1] != "\\"
                        ):
                            in_string = False
                        current += char

                if current.strip():
                    parts.append(current.strip())

                parsed_parts = []
                for p in parts:
                    p = p.strip()
                    if p:
                        if p.startswith('"') and p.endswith('"'):
                            parsed_parts.append(p[1:-1])
                        elif p.startswith("'") and p.endswith("'"):
                            parsed_parts.append(p[1:-1])
                        elif p.isdigit() or (p.startswith("-") and p[1:].isdigit()):
                            parsed_parts.append(int(p))
                        else:
                            parsed_parts.append(p)

                if parsed_parts:
                    parsed_items.append(parsed_parts)
            except:
                pass

    return parsed_items


def extract_js_data(html: str, var_name: str) -> Optional[List]:
    pattern = rf"var\s+{var_name}\s*=\s*(\[.*?\]);"
    match = re.search(pattern, html, re.DOTALL)
    if match:
        try:
            return parse_js_array_manual(match.group(1))
        except Exception as e:
            print(f"Parse error for {var_name}: {e}")
            return None
    return None


def clean_html_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<span[^>]*>\d+</span>", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.strip()
    return text


def parse_team_stats_from_table(
    table_html: str, team_name: str
) -> Dict[str, TeamStats]:
    stats = {}

    rank_pattern = r"\[([^\]-]+)-(\d+)\]" + re.escape(team_name)
    rank_match = re.search(rank_pattern, table_html)
    rank = int(rank_match.group(2)) if rank_match else 0

    team_start_pattern = r"\[[^\]]+\]" + re.escape(team_name)
    team_start_match = re.search(team_start_pattern, table_html)

    if not team_start_match:
        return stats

    team_start = team_start_match.start()

    team_section_pattern = (
        r"\[[^\]]+\]" + re.escape(team_name) + r".*?(?=</table>|<script|var\s)"
    )
    team_match = re.search(team_section_pattern, table_html[team_start:], re.DOTALL)

    if not team_match:
        return stats

    section = team_match.group(0)

    rows = re.findall(
        r'<tr[^>]*bgcolor=["\']?#FFECEC["\']?[^>]*>(.*?)</tr>', section, re.DOTALL
    )

    if len(rows) < 2:
        rows2 = re.findall(
            r'<tr[^>]*bgcolor=["\']?#CCCCFF["\']?[^>]*>(.*?)</tr>', section, re.DOTALL
        )
        rows = rows + rows2

    for row in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.DOTALL)
        cells = [clean_html_text(c) for c in cells]

        if len(cells) >= 9:
            label = cells[0]
            if "总" in label:
                stats["full"] = TeamStats(
                    team_name=team_name,
                    rank=rank,
                    matches=int(cells[1]) if cells[1].isdigit() else 0,
                    wins=int(cells[2]) if cells[2].isdigit() else 0,
                    draws=int(cells[3]) if cells[3].isdigit() else 0,
                    losses=int(cells[4]) if cells[4].isdigit() else 0,
                    goals_for=int(cells[5]) if cells[5].isdigit() else 0,
                    goals_against=int(cells[6]) if cells[6].isdigit() else 0,
                    goal_diff=int(cells[7]) if cells[7].lstrip("-").isdigit() else 0,
                    points=int(cells[8]) if cells[8].isdigit() else 0,
                    win_rate=0.0,
                )

    home_rows = re.findall(
        r'<tr[^>]*bgcolor=["\']?#FFECEC["\']?[^>]*>(.*?)</tr>', section, re.DOTALL
    )

    if len(home_rows) < 2:
        home_rows2 = re.findall(
            r'<tr[^>]*bgcolor=["\']?#CCCCFF["\']?[^>]*>(.*?)</tr>', section, re.DOTALL
        )
        home_rows = home_rows + home_rows2

    for row in home_rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.DOTALL)
        cells = [clean_html_text(c) for c in cells]

        if len(cells) >= 9:
            label = cells[0]
            if (
                "主" in label
                and "客" not in label
                and "总" not in label
                and "近" not in label
            ):
                stats["home"] = TeamStats(
                    team_name=team_name,
                    rank=0,
                    matches=int(cells[1]) if cells[1].isdigit() else 0,
                    wins=int(cells[2]) if cells[2].isdigit() else 0,
                    draws=int(cells[3]) if cells[3].isdigit() else 0,
                    losses=int(cells[4]) if cells[4].isdigit() else 0,
                    goals_for=int(cells[5]) if cells[5].isdigit() else 0,
                    goals_against=int(cells[6]) if cells[6].isdigit() else 0,
                    goal_diff=int(cells[7]) if cells[7].lstrip("-").isdigit() else 0,
                    points=int(cells[8]) if cells[8].isdigit() else 0,
                    win_rate=0.0,
                )
            elif "客" in label and "总" not in label:
                stats["away"] = TeamStats(
                    team_name=team_name,
                    rank=0,
                    matches=int(cells[1]) if cells[1].isdigit() else 0,
                    wins=int(cells[2]) if cells[2].isdigit() else 0,
                    draws=int(cells[3]) if cells[3].isdigit() else 0,
                    losses=int(cells[4]) if cells[4].isdigit() else 0,
                    goals_for=int(cells[5]) if cells[5].isdigit() else 0,
                    goals_against=int(cells[6]) if cells[6].isdigit() else 0,
                    goal_diff=int(cells[7]) if cells[7].lstrip("-").isdigit() else 0,
                    points=int(cells[8]) if cells[8].isdigit() else 0,
                    win_rate=0.0,
                )

    return stats


def parse_match_record(
    record_list: List, min_date: Optional[datetime] = None
) -> List[MatchRecord]:
    """
    解析比赛记录列表

    Args:
        record_list: 原始记录列表
        min_date: 最小日期筛选条件（可选），只保留 >= min_date 的记录
    """
    records = []
    for item in record_list:
        record = item
        parts = None

        if len(record) == 1 and isinstance(record[0], str):
            inner = record[0].strip()
            if inner.startswith("["):
                inner = inner[1:]
            if inner.endswith("]"):
                inner = inner[:-1]

            parts = []
            in_string = False
            string_char = ""
            current = ""
            depth = 0
            for j, char in enumerate(inner):
                if not in_string:
                    if char in "\"'":
                        in_string = True
                        string_char = char
                        current += char
                    elif char == "[":
                        depth += 1
                        current += char
                    elif char == "]":
                        depth -= 1
                        current += char
                    elif char == "," and depth == 0:
                        parts.append(current.strip())
                        current = ""
                    else:
                        current += char
                else:
                    if char == string_char and (
                        j < len(inner) - 1 and inner[j + 1] != "\\"
                    ):
                        in_string = False
                    current += char
            if current.strip():
                parts.append(current.strip())

            if parts:
                record = []
                for p in parts:
                    p = p.strip()
                    if p:
                        if p.startswith('"') and p.endswith('"'):
                            record.append(p[1:-1])
                        elif p.startswith("'") and p.endswith("'"):
                            record.append(p[1:-1])
                        elif p.isdigit() or (p.startswith("-") and p[1:].isdigit()):
                            record.append(int(p))
                        else:
                            record.append(p)

        if len(record) >= 10:
            home_team_raw = str(record[5]) if len(record) > 5 else ""
            away_team_raw = str(record[7]) if len(record) > 7 else ""

            home_team = clean_html_text(home_team_raw)
            away_team = clean_html_text(away_team_raw)

            try:
                home_goals = (
                    int(record[8])
                    if len(record) > 8 and str(record[8]).replace("-", "").isdigit()
                    else 0
                )
                away_goals = (
                    int(record[9])
                    if len(record) > 9 and str(record[9]).replace("-", "").isdigit()
                    else 0
                )
                result = (
                    int(record[12])
                    if len(record) > 12 and str(record[12]).replace("-", "").isdigit()
                    else 0
                )
            except:
                home_goals = 0
                away_goals = 0
                result = 0

            # 解析记录日期（格式：26-01-13 或 2026-01-13）
            record_date_str = str(record[0]) if len(record) > 0 else ""
            record_datetime = None
            if record_date_str:
                try:
                    # 尝试多种日期格式
                    for fmt in ["%y-%m-%d", "%Y-%m-%d", "%Y%m%d"]:
                        try:
                            record_datetime = datetime.strptime(record_date_str, fmt)
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass

            # 日期筛选：如果指定了 min_date，则只保留 >= min_date 的记录
            if min_date and record_datetime and record_datetime < min_date:
                continue

            records.append(
                MatchRecord(
                    date=record_date_str,
                    league=str(record[2]) if len(record) > 2 else "",
                    home_team=home_team,
                    away_team=away_team,
                    home_goals=home_goals,
                    away_goals=away_goals,
                    score_line=str(record[10]) if len(record) > 10 else "",
                    handicap=str(record[11]) if len(record) > 11 else "",
                    result=result,
                )
            )
    return records


def extract_recent_6_stats(html: str) -> tuple:
    """从HTML中提取主客队近6场统计（联赛数据）"""
    home_recent_6 = None
    away_recent_6 = None

    try:
        soup = BeautifulSoup(html, "html.parser")

        # 查找联赛积分排名区域 (porlet_5)
        league_div = soup.find("div", id="porlet_5")
        if not league_div:
            return None, None

        tables = league_div.find_all("table")

        home_found = False
        away_found = False

        for table in tables:
            rows = table.find_all("tr", align="middle")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 6:
                    label = cells[0].get_text(strip=True)
                    if label == "近6":
                        try:
                            matches = int(cells[1].get_text(strip=True))
                            wins = int(cells[2].get_text(strip=True))
                            draws = int(cells[3].get_text(strip=True))
                            losses = int(cells[4].get_text(strip=True))
                            goals_for = int(cells[5].get_text(strip=True))
                            goals_against = (
                                int(cells[6].get_text(strip=True))
                                if len(cells) > 6
                                else 0
                            )

                            recent_record = RecentRecord(
                                label=label,
                                matches=matches,
                                wins=wins,
                                draws=draws,
                                losses=losses,
                                goals_for=goals_for,
                                goals_against=goals_against,
                            )

                            # 根据bgcolor判断是主队还是客队，只取联赛数据（第一组）
                            bgcolor = row.get("bgcolor", "")
                            if bgcolor == "#FFECEC" and not home_found:
                                home_recent_6 = recent_record
                                home_found = True
                            elif bgcolor == "#CCCCFF" and not away_found:
                                away_recent_6 = recent_record
                                away_found = True

                            # 两队都找到后退出
                            if home_found and away_found:
                                return home_recent_6, away_recent_6
                        except (ValueError, IndexError):
                            continue
    except Exception as e:
        print(f"解析近6场统计失败: {e}")

    return home_recent_6, away_recent_6


def _parse_goal_time_row(row_text: str) -> List[int]:
    """解析进球时间表格的一行数据"""
    numbers = re.findall(r"<td[^>]*>(\d+)</td>", row_text)
    return [int(n) for n in numbers[:10]]  # 只取前10个时间段


def extract_goal_timing_data(html: str) -> Optional[GoalTimingData]:
    """从HTML中提取进球时间统计数据"""
    try:
        soup = BeautifulSoup(html, "html.parser")

        # 定位进球时间模块
        goal_timing_div = soup.find("div", id="porlet_19")
        if not goal_timing_div:
            return None

        # 查找所有表格
        tables = goal_timing_div.find_all("table")
        if len(tables) < 2:
            return None

        # 时间段
        time_periods = [
            "1-10",
            "11-20",
            "21-30",
            "31-40",
            "41-45",
            "46-50",
            "51-60",
            "61-70",
            "71-80",
            "81-90+",
        ]

        def parse_table_rows(table):
            """解析表格的所有数据行"""
            rows = table.find_all("tr")
            data = {}
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 11:
                    label = cells[0].get_text(strip=True)
                    if label in ["总", "主", "客"]:
                        numbers = [int(c.get_text(strip=True)) for c in cells[1:11]]
                        data[label] = numbers
            return data

        # 左侧第一张表：进球时间分布
        left_table1 = tables[0]
        left_data1 = parse_table_rows(left_table1)

        # 左侧第二张表：首个进球时间
        left_table2 = tables[1] if len(tables) > 1 else None
        left_data2 = parse_table_rows(left_table2) if left_table2 else {}

        # 右侧第一张表：失球时间分布
        right_table1 = tables[2] if len(tables) > 2 else None
        right_data1 = parse_table_rows(right_table1) if right_table1 else {}

        # 右侧第二张表：首个失球时间
        right_table2 = tables[3] if len(tables) > 3 else None
        right_data2 = parse_table_rows(right_table2) if right_table2 else {}

        # 验证数据完整性
        if not left_data1.get("总"):
            return None

        # 构建数据对象
        goal_timing = GoalTimingData(
            goals_for=GoalTimeStats(
                time_periods=time_periods,
                total=left_data1.get("总", []),
                home=left_data1.get("主", []),
                away=left_data1.get("客", []),
            ),
            first_goal_for=GoalTimeStats(
                time_periods=time_periods,
                total=left_data2.get("总", []),
                home=left_data2.get("主", []),
                away=left_data2.get("客", []),
            ),
            goals_against=GoalTimeStats(
                time_periods=time_periods,
                total=right_data1.get("总", []),
                home=right_data1.get("主", []),
                away=right_data1.get("客", []),
            ),
            first_goal_against=GoalTimeStats(
                time_periods=time_periods,
                total=right_data2.get("总", []),
                home=right_data2.get("主", []),
                away=right_data2.get("客", []),
            ),
        )

        return goal_timing

    except Exception as e:
        print(f"解析进球时间数据失败: {e}")
        import traceback

        traceback.print_exc()
        return None


def parse_html_basic_data(html_path: str) -> BasicData:
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    html_content = html_content.replace("\n", " ").replace("\r", " ")

    match_info = extract_match_info(html_content)

    home_team_name = match_info.home_team
    away_team_name = match_info.away_team

    home_stats = parse_team_stats_from_table(html_content, home_team_name)
    if not home_stats:
        home_stats = parse_team_stats_from_table(html_content, "伯恩茅斯")

    away_stats = parse_team_stats_from_table(html_content, away_team_name)
    if not away_stats:
        away_stats = parse_team_stats_from_table(html_content, "托特纳姆热刺")
    if not away_stats:
        away_stats = parse_team_stats_from_table(html_content, "诺丁汉森林")
    if not away_stats:
        away_stats = parse_team_stats_from_table(html_content, "西汉姆联")

    # 解析比赛日期用于时间筛选
    match_date = None
    if match_info.match_time:
        try:
            match_date = datetime.strptime(
                match_info.match_time.split(" ")[0], "%Y-%m-%d"
            )
        except ValueError:
            pass

    # 计算时间筛选边界
    # 近期战绩：取近1个月（30天）
    recent_min_date = match_date - timedelta(days=30) if match_date else None
    # 历史交锋：取近3年（1095天）
    h2h_min_date = match_date - timedelta(days=1095) if match_date else None

    h2h_data = extract_js_data(html_content, "v_data")
    h2h_records = (
        parse_match_record(h2h_data, min_date=h2h_min_date) if h2h_data else []
    )

    home_recent = extract_js_data(html_content, "h2_data")
    home_matches = (
        parse_match_record(home_recent, min_date=recent_min_date) if home_recent else []
    )

    away_recent = extract_js_data(html_content, "a2_data")
    away_matches = (
        parse_match_record(away_recent, min_date=recent_min_date) if away_recent else []
    )

    league_table_data = extract_js_data(html_content, "totalScoreStr")
    league_table = []
    if league_table_data:
        for item in league_table_data:
            if len(item) >= 5:
                league_table.append(
                    {
                        "rank_change": int(item[0])
                        if str(item[0]).replace("-", "").isdigit()
                        else 0,
                        "position": int(item[1]) if str(item[1]).isdigit() else 0,
                        "team_id": int(item[2]) if str(item[2]).isdigit() else 0,
                        "team_name": str(item[3]),
                        "points": int(item[4]) if str(item[4]).isdigit() else 0,
                    }
                )

    # 解析进球时间数据
    goal_timing_data = extract_goal_timing_data(html_content)

    # 解析近6场统计
    home_recent_6, away_recent_6 = extract_recent_6_stats(html_content)

    return BasicData(
        match_info=match_info,
        home_team_full_stats=home_stats.get(
            "full", TeamStats("", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0)
        ),
        away_team_full_stats=away_stats.get(
            "full", TeamStats("", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0)
        ),
        home_team_home_stats=home_stats.get(
            "home", TeamStats("", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0)
        ),
        away_team_away_stats=away_stats.get(
            "away", TeamStats("", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0)
        ),
        recent_matches_home=home_matches,
        recent_matches_away=away_matches,
        h2h_records=h2h_records,
        league_table=league_table,
        home_recent_6=home_recent_6,
        away_recent_6=away_recent_6,
        goal_timing=goal_timing_data,
    )


def extract_ratings(html: str) -> tuple:
    home_avg = 0.0
    away_avg = 0.0
    home_ratings = []
    away_ratings = []

    home_ratings_pattern = r'主队近10场平均评分:<ul[^>]*class="average"[^>]*>(.*?)</ul>'
    away_ratings_pattern = r'客队近10场平均评分:<ul[^>]*class="average"[^>]*>(.*?)</ul>'

    home_match = re.search(home_ratings_pattern, html, re.DOTALL)
    if home_match:
        home_list_html = home_match.group(1)
        home_ratings = [
            float(m) for m in re.findall(r"<li[^>]*>([^<]+)</li>", home_list_html)
        ]
        if home_ratings:
            home_avg = sum(home_ratings) / len(home_ratings)

    away_match = re.search(away_ratings_pattern, html, re.DOTALL)
    if away_match:
        away_list_html = away_match.group(1)
        away_ratings = [
            float(m) for m in re.findall(r"<li[^>]*>([^<]+)</li>", away_list_html)
        ]
        if away_ratings:
            away_avg = sum(away_ratings) / len(away_ratings)

    return home_avg, away_avg, home_ratings, away_ratings


def extract_match_info(html: str) -> MatchBasicInfo:
    match_id_match = re.search(r"scheduleID\s*=\s*(\d+)", html)
    home_match = re.search(r'var\s+hometeam\s*=\s*"([^"]+)"', html)
    away_match = re.search(r'var\s+guestteam\s*=\s*"([^"]+)"', html)
    time_match = re.search(r"var\s+strTime\s*=\s*'([^']+)'", html)
    league_match = re.search(r"class=['\"]LName['\"]>([^<]+)</a>", html)

    home_score_match = re.search(r'class="score">(\d+)</div>', html)
    away_score_match = re.search(r'class="score gt">(\d+)</div>', html)
    final_score = ""
    if home_score_match and away_score_match:
        final_score = f"{home_score_match.group(1)}-{away_score_match.group(1)}"

    half_score_match = re.search(r"\((\d+-\d+)\)", html)
    half_score = half_score_match.group(1) if half_score_match else ""

    venue_match = re.search(r"场地：([^<]+)", html)
    venue = venue_match.group(1).strip() if venue_match else ""

    weather_match = re.search(r"天气：([^<]+)", html)
    weather_full = weather_match.group(1).strip() if weather_match else ""

    temp_match = re.search(r"温度：([^\s℃]+)", weather_full)
    temperature = temp_match.group(1) + "℃" if temp_match else ""
    weather = weather_full
    if temperature:
        weather = weather.replace(f"温度：{temperature}", "").strip()

    league = league_match.group(1).split(" ")[0] if league_match else ""
    round_num = ""
    if league_match:
        parts = league_match.group(1).split(" ")
        if len(parts) > 1:
            round_num = " ".join(parts[1:])

    home_avg, away_avg, home_ratings, away_ratings = extract_ratings(html)

    return MatchBasicInfo(
        match_id=match_id_match.group(1) if match_id_match else "",
        home_team=home_match.group(1) if home_match else "",
        away_team=away_match.group(1) if away_match else "",
        league=league,
        round_num=round_num,
        match_time=time_match.group(1) if time_match else "",
        final_score=final_score,
        half_score=half_score,
        venue=venue,
        weather=weather,
        temperature=temperature,
        home_recent_ratings=home_ratings,
        away_recent_ratings=away_ratings,
    )


def process_all_analyses(
    data_dir: str = "./data/analysis", output_file: str = "./data/basic_data.json"
) -> List[Dict]:
    basic_data_dict = {}

    data_path = Path(data_dir)
    html_files = list(data_path.glob("*.html"))

    for html_file in sorted(html_files):
        print(f"Processing: {html_file.name}")
        try:
            basic_data = parse_html_basic_data(str(html_file))
            match_id = basic_data.match_info.match_id
            if match_id:
                basic_data_dict[match_id] = asdict(basic_data)
                print(f"  -> Match {match_id} added/updated")
            else:
                print(f"  -> Warning: No match_id found in {html_file.name}")
        except Exception as e:
            print(f"Error processing {html_file.name}: {e}")
            import traceback

            traceback.print_exc()

    basic_data_list = list(basic_data_dict.values())

    save_basic_data(basic_data_list, output_file)

    return basic_data_list


def save_basic_data(
    basic_data_list: List[Dict], output_file: str = "./data/basic_data.json"
):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(basic_data_list, f, ensure_ascii=False, indent=2)
    print(f"\nBasic data saved to {output_file}")
    print(f"Total matches processed: {len(basic_data_list)}")


def print_summary(data: Dict):
    print(
        f"\n=== {data['match_info']['home_team']} vs {data['match_info']['away_team']} ==="
    )
    print(f"Match ID: {data['match_info']['match_id']}")
    print(
        f"Score: {data['match_info']['final_score']} (Half: {data['match_info']['half_score']})"
    )
    print(f"Time: {data['match_info']['match_time']}")
    print(f"League: {data['match_info']['league']} {data['match_info']['round_num']}")
    print(f"Venue: {data['match_info']['venue']}")
    print(
        f"Weather: {data['match_info']['weather']} {data['match_info']['temperature']}"
    )

    print(
        f"\n--- {data['match_info']['home_team']} (Rank {data['home_team_full_stats']['rank']}) ---"
    )
    print(
        f"Overall: {data['home_team_full_stats']['matches']} games | {data['home_team_full_stats']['wins']}W {data['home_team_full_stats']['draws']}D {data['home_team_full_stats']['losses']}L"
    )
    print(
        f"Goals: {data['home_team_full_stats']['goals_for']}GF {data['home_team_full_stats']['goals_against']}GA | {data['home_team_full_stats']['points']}Pts"
    )
    print(
        f"Home: {data['home_team_home_stats']['matches']} games | {data['home_team_home_stats']['wins']}W {data['home_team_home_stats']['draws']}D {data['home_team_home_stats']['losses']}L | {data['home_team_home_stats']['goals_for']}GF {data['home_team_home_stats']['goals_against']}GA"
    )

    print(
        f"\n--- {data['match_info']['away_team']} (Rank {data['away_team_full_stats']['rank']}) ---"
    )
    print(
        f"Overall: {data['away_team_full_stats']['matches']} games | {data['away_team_full_stats']['wins']}W {data['away_team_full_stats']['draws']}D {data['away_team_full_stats']['losses']}L"
    )
    print(
        f"Goals: {data['away_team_full_stats']['goals_for']}GF {data['away_team_full_stats']['goals_against']}GA | {data['away_team_full_stats']['points']}Pts"
    )
    print(
        f"Away: {data['away_team_away_stats']['matches']} games | {data['away_team_away_stats']['wins']}W {data['away_team_away_stats']['draws']}D {data['away_team_away_stats']['losses']}L | {data['away_team_away_stats']['goals_for']}GF {data['away_team_away_stats']['goals_against']}GA"
    )

    print(f"\nH2H Records: {len(data['h2h_records'])} matches")
    for record in data["h2h_records"][:5]:
        print(
            f"  {record['date']}: {record['home_team']} {record['home_goals']}-{record['away_goals']} {record['away_team']}"
        )

    print(f"\nHome Team Recent (h2_data): {len(data['recent_matches_home'])} matches")
    for record in data["recent_matches_home"][:3]:
        print(
            f"  {record['date']}: {record['home_team']} {record['home_goals']}-{record['away_goals']} {record['away_team']}"
        )

    print(f"\nAway Team Recent (a2_data): {len(data['recent_matches_away'])} matches")
    for record in data["recent_matches_away"][:3]:
        print(
            f"  {record['date']}: {record['home_team']} {record['home_goals']}-{record['away_goals']} {record['away_team']}"
        )


if __name__ == "__main__":
    data_list = process_all_analyses()
    save_basic_data(data_list)

    for data in data_list:
        print_summary(data)
