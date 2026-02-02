#!/usr/bin/env python3
"""
Game Theory Betting Analysis Prompt Generator
结合基本面数据和赔率数据，生成完整的足彩博弈论分析prompt
支持综合多家博彩公司数据
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from bs4 import BeautifulSoup
from datetime import datetime


@dataclass
class PromptConfig:
    """Prompt配置选项"""

    include_h2h: bool = False
    include_recent_matches: bool = False
    include_league_table: bool = True
    use_all_bookmakers: bool = True
    handicap_bookmakers: List[str] = field(default_factory=list)
    odds_bookmakers: List[str] = field(default_factory=list)
    primary_bookmaker: str = "macau"


class GameTheoryPromptGenerator:
    """博弈论分析Prompt生成器"""

    # SYSTEM_PROMPT = """你是一位精通博弈论（Game Theory）与动态赔率逻辑的顶级战略顾问。你的核心任务是识别机构在盘面上的**"财务对冲"与"真实防御"**。"""
    SYSTEM_PROMPT = """
# Role
你是一个精通「机构博弈派」理论的足球赛事高级分析师。你的核心逻辑不再局限于球队技战术，而是专注于分析博彩公司（庄家/市场）如何通过数据（赔率/盘口）调控注码流向。你的目标是利用“假-验证”方法论，穿透市场的诱导，找到真实的获利方向。

# Core Philosophy (理论基石)
请严格遵循以下分析体系进行推理，禁止单纯依赖基本面：
1. 市场均衡与供需：庄家的目标是掌控资金流向。若盘口看似完美均衡，往往是掩盖真实意图的陷阱。
2. 底蕴 vs 定位：
* 深层逻辑：“便宜莫贪”与“便宜不敢贪”。若强队浅开但水位极低（<0.85），是“降赔付”；若强队浅开且水位高企（>1.00），是“诱入”。
3. 矛盾分析法（核心）：
* 洗盘逻辑（新增）：若强队方向热度过高，机构可能通过“退盘+升水”或“欧赔主胜大幅上调”制造不稳假象，试图将资金赶往对家。判断洗盘还是诱导的关键在于大小球。
* 维度共振（大小球定性）：
* 正向共振：让球盘示强（升盘）+ 大小球示强（升盘/降水）= 真实看好，正路穿盘。
* 以退为进（本案关键）：让球盘示弱（退盘/升水）+ 大小球坚挺（不降盘或逆势升盘）= 机构在利用让球盘的“便宜”制造恐慌，实则看好强队火力，此为洗盘，正路打出。
* 诱上背离：让球盘示强（升盘）+ 大小球示弱（降盘/升水）= 虚假繁荣，诱上。
4. 时间维度：重点观察临场 2 小时内，大小球与让球盘是否出现“反向走势”。

# Analysis Workflow (严格执行步骤)

Step 1: 建立基准 (Qualitative Analysis)
* 分析双方底蕴差距与大众心理倾向。明确谁是“天然受热方”。

Step 2: 初始意图假设 (Hypothesis)
* 判断初盘定位。若偏浅，结合初盘大小球（如 2.5 球低水）判断机构对进球的基本预期。

Step 3: 后期验证与矛盾捕捉 (Verification)
* 核心博弈逻辑验证（必须执行）：
* 交叉比对：观察让球盘退盘时，大小球是否同步缩减？
* 洗盘识别：如果让球盘从 0.75 退到 0.5，且欧赔主胜升高，但大小球盘口却从 2.5 升至 2.5/3 或水位极度压缩。结论：机构在利用让球盘“赶客”，真实意图是主队大胜。
* 赔付压力测试：观察临场水位。若热门方退盘后水位维持在 0.90-0.95（中水），且大小球走强，这通常是“洗掉散户，收割中线资金”的洗盘行为。

Step 4: 临界判定 (Threshold Check)
* 最终决策优先级：
1. 大小球与让球盘背离时，优先相信大小球释放的火力信号。
2. 当“让球退盘/欧赔升水”+“大小球升盘/坚挺”同时出现，坚定看好强队（正路）。

# Output Format (输出格式)

🎯 核心逻辑推演
1. 市场底蕴画像：(明确受热方)
2. 初始定位与协同：(分析初盘意图)
3. 后期资金博弈（关键）：(重点分析让球盘与大小球的背离关系，识别是“诱上”还是“洗盘”)
4. 破局点 (The Key)：(指出机构利用哪种数据制造了恐慌或贪婪)

🔮 最终结论
* 亚盘/方向预测：
* 进球数趋势：
* 信心指数：
* 风险剧本：

---
现在，请接收我的比赛及赔率数据（包含让球与大小球），开始分析：

    """
    BOOKMAKER_NAMES = {
        "macau": "澳门",
        "bet365": "Bet365",
        "easybet": "易胜博",
        "betfair": "Betfair",
        "william": "威廉希尔",
    }

    def __init__(self, base_path: str = "./data"):
        self.base_path = Path(base_path)
        self.basic_data_path = self.base_path / "basic_data.json"
        self.handicap_path = self.base_path / "odds" / "handicap"
        self.odds_path = self.base_path / "odds" / "odds"
        self.overunder_path = self.base_path / "odds" / "overunder"

        self.default_handicap_bookmakers = ["macau", "bet365", "easybet"]
        self.default_odds_bookmakers = ["bet365", "william", "betfair", "easybet"]

    def _extract_float(self, text: str) -> Optional[float]:
        match = re.search(r"[\d.]+", text)
        return float(match.group()) if match else None

    def _convert_handicap_to_readable(self, handicap: str) -> str:
        handicap = handicap.strip()
        if handicap == "平手":
            return "平手"

        is_received = handicap.startswith("受让")
        raw_handicap = handicap[2:] if is_received else handicap

        name_map = {
            "半球": "半球",
            "半球/一球": "半球/一球",
            "一球": "一球",
            "一球/球半": "一球/球半",
            "球半": "球半",
            "球半/两球": "球半/两球",
            "两球": "两球",
            "两球/两球半": "两球/两球半",
            "两球半": "两球半",
            "两球半/三球": "两球半/三球",
            "三球": "三球",
            "平手/半球": "平手/半球",
        }

        if raw_handicap in name_map:
            readable = name_map[raw_handicap]
            if is_received:
                return f"主队受让{readable}"
            else:
                return f"主队让{readable}"

        return handicap

    def _load_basic_data(self) -> dict:
        """加载基本面数据（第一场比赛）"""
        if not self.basic_data_path.exists():
            return {}
        with open(self.basic_data_path, "r", encoding="utf-8") as f:
            content = json.load(f)
            return content[0] if isinstance(content, list) else content

    def _load_match_data(self, match_id: str) -> Optional[dict]:
        """根据match_id加载指定的比赛数据"""
        if not self.basic_data_path.exists():
            return None
        with open(self.basic_data_path, "r", encoding="utf-8") as f:
            content = json.load(f)
            if isinstance(content, list):
                for match in content:
                    if match.get("match_info", {}).get("match_id") == match_id:
                        return match
            elif isinstance(content, dict):
                if content.get("match_info", {}).get("match_id") == match_id:
                    return content
        return None

    def _parse_handicap_odds(self, match_id: str, bookmaker: str) -> Optional[dict]:
        pattern = f"{match_id}_{bookmaker}_*.html"
        files = list(self.handicap_path.glob(pattern))
        if not files:
            return None

        html_file = files[0]
        with open(html_file, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")
        odds_list = []

        table = soup.find("table", attrs={"cellspacing": "1"})
        if not table:
            return None

        rows = table.find_all("tr", align="center")
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) < 7:
                continue

            try:
                status_td = cols[6]
                td_class = status_td.get("class") or []
                if "hg_blue" in td_class:
                    continue

                home_odds_text = cols[2].get_text(strip=True)
                home_odds = self._extract_float(home_odds_text)

                handicap = cols[3].get_text(strip=True)

                away_odds_text = cols[4].get_text(strip=True)
                away_odds = self._extract_float(away_odds_text)

                change_time = cols[5].get_text(strip=True)

                if home_odds and away_odds:
                    odds_list.append(
                        {
                            "home_odds": home_odds,
                            "handicap": handicap,
                            "away_odds": away_odds,
                            "time": change_time,
                        }
                    )
            except (IndexError, ValueError):
                continue

        return {
            "bookmaker": bookmaker,
            "name": self.BOOKMAKER_NAMES.get(bookmaker, bookmaker),
            "odds": odds_list,
        }

    def _parse_european_odds(self, match_id: str, bookmaker: str) -> Optional[dict]:
        pattern = f"{match_id}_{bookmaker}_*.html"
        files = list(self.odds_path.glob(pattern))
        if not files:
            return None

        html_file = files[0]
        with open(html_file, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")
        odds_list = []

        table = soup.find("table", width="860")
        if not table:
            return None

        rows = table.find_all("tr", align="center")
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) < 11:
                continue

            try:
                home_odds = self._extract_float(cols[0].get_text(strip=True))
                draw_odds = self._extract_float(cols[1].get_text(strip=True))
                away_odds = self._extract_float(cols[2].get_text(strip=True))
                change_time = cols[10].get_text(strip=True)

                if home_odds and draw_odds and away_odds:
                    odds_list.append(
                        {
                            "home": home_odds,
                            "draw": draw_odds,
                            "away": away_odds,
                            "time": change_time,
                        }
                    )
            except (IndexError, ValueError):
                continue

        return {
            "bookmaker": bookmaker,
            "name": self.BOOKMAKER_NAMES.get(bookmaker, bookmaker),
            "odds": odds_list,
        }

    def _parse_overunder_odds(self, match_id: str, bookmaker: str) -> Optional[dict]:
        pattern = f"{match_id}_{bookmaker}_*.html"
        files = list(self.overunder_path.glob(pattern))
        if not files:
            return None

        html_file = files[0]
        with open(html_file, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")
        odds_list = []

        table = soup.find("table", attrs={"cellspacing": "1"})
        if not table:
            return None

        rows = table.find_all("tr", align="center")
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) < 6:
                continue

            try:
                if len(cols) < 7:
                    continue

                status_td = cols[6]
                td_class = status_td.get("class") or []
                if "hg_blue" in td_class:
                    continue

                over_odds_text = cols[2].get_text(strip=True)
                over_odds = self._extract_float(over_odds_text)

                handicap = cols[3].get_text(strip=True)

                under_odds_text = cols[4].get_text(strip=True)
                under_odds = self._extract_float(under_odds_text)

                change_time = cols[5].get_text(strip=True) if len(cols) > 5 else ""

                if over_odds and under_odds:
                    odds_list.append(
                        {
                            "over_odds": over_odds,
                            "handicap": handicap,
                            "under_odds": under_odds,
                            "time": change_time,
                        }
                    )
            except (IndexError, ValueError):
                continue

        return {
            "bookmaker": bookmaker,
            "name": self.BOOKMAKER_NAMES.get(bookmaker, bookmaker),
            "odds": odds_list,
        }

    def _get_all_available_bookmakers(self, match_id: str) -> Dict[str, List[str]]:
        handicap_files = list(self.handicap_path.glob(f"{match_id}_*_*.html"))
        odds_files = list(self.odds_path.glob(f"{match_id}_*_*.html"))
        overunder_files = list(self.overunder_path.glob(f"{match_id}_*_*.html"))

        handicap_bms = set()
        odds_bms = set()
        overunder_bms = set()

        for f in handicap_files:
            name = f.stem
            parts = name.split("_")
            if len(parts) >= 2:
                handicap_bms.add(parts[1])

        for f in odds_files:
            name = f.stem
            parts = name.split("_")
            if len(parts) >= 2:
                odds_bms.add(parts[1])

        for f in overunder_files:
            name = f.stem
            parts = name.split("_")
            if len(parts) >= 2:
                overunder_bms.add(parts[1])

        return {
            "handicap": sorted(list(handicap_bms)),
            "odds": sorted(list(odds_bms)),
            "overunder": sorted(list(overunder_bms)),
        }

    def _format_handicap_for_prompt(
        self, odds_data: dict, show_details: bool = True
    ) -> str:
        odds_list = odds_data.get("odds", [])
        if not odds_list:
            return f"{odds_data['name']}: 暂无数据"

        lines = []
        name = odds_data["name"]

        if show_details and len(odds_list) > 0:
            lines.append(f"**{name} 亚盘变化** (共{len(odds_list)}条记录)")
            for odds in reversed(odds_list):
                readable_handicap = self._convert_handicap_to_readable(odds["handicap"])
                if odds["handicap"] == "平手":
                    handicap_label = ""
                else:
                    handicap_label = ""

                handicap_display = f"{readable_handicap} {handicap_label}".strip()
                lines.append(
                    f"  {odds['home_odds']} | {handicap_display} | {odds['away_odds']} | {odds['time']}"
                )
        else:
            latest = odds_list[-1] if odds_list else None
            if latest:
                readable_handicap = self._convert_handicap_to_readable(
                    latest["handicap"]
                )
                if latest["handicap"] == "平手":
                    handicap_label = ""
                else:
                    handicap_label = ""

                handicap_display = f"{readable_handicap} {handicap_label}".strip()
                lines.append(
                    f"**{name}**: {latest['home_odds']} | {handicap_display} | {latest['away_odds']}"
                )

        return "\n".join(lines)

    def _format_european_for_prompt(
        self, odds_data: dict, show_details: bool = True
    ) -> str:
        odds_list = odds_data.get("odds", [])
        if not odds_list:
            return f"{odds_data['name']}: 暂无数据"

        lines = []
        name = odds_data["name"]

        if show_details and len(odds_list) > 0:
            lines.append(f"**{name} 欧赔变化** (共{len(odds_list)}条记录)")
            for odds in reversed(odds_list):
                lines.append(
                    f"  {odds['home']} | {odds['draw']} | {odds['away']} | {odds['time']}"
                )
        else:
            latest = odds_list[-1] if odds_list else None
            if latest:
                lines.append(
                    f"**{name}**: {latest['home']} | {latest['draw']} | {latest['away']}"
                )

        return "\n".join(lines)

    def _format_overunder_for_prompt(
        self, odds_data: dict, show_details: bool = True
    ) -> str:
        odds_list = odds_data.get("odds", [])
        if not odds_list:
            return f"{odds_data['name']}: 暂无数据"

        lines = []
        name = odds_data["name"]

        if show_details and len(odds_list) > 0:
            lines.append(f"**{name} 大小球变化** (共{len(odds_list)}条记录)")
            for odds in reversed(odds_list):
                lines.append(
                    f"  {odds['over_odds']} | {odds['handicap']} | {odds['under_odds']} | {odds['time']}"
                )
        else:
            latest = odds_list[-1] if odds_list else None
            if latest:
                lines.append(
                    f"**{name}**: {latest['over_odds']} | {latest['handicap']} | {latest['under_odds']}"
                )

        return "\n".join(lines)

    def _format_goal_timing_for_prompt(self, goal_timing: dict) -> str:
        """将进球时间数据格式化为prompt文本"""
        lines = ["\n## 进球时间统计"]

        # 进球时间分布
        goals_for = goal_timing.get("goals_for", {})
        if goals_for and goals_for.get("total"):
            lines.append("### 进球时间分布")
            periods = goals_for.get("time_periods", [])
            lines.append(f"**时间段**: {', '.join(periods)}")
            lines.append(
                f"**总进球**: {', '.join(map(str, goals_for.get('total', [])))}"
            )
            lines.append(
                f"**主队进球**: {', '.join(map(str, goals_for.get('home', [])))}"
            )
            lines.append(
                f"**客队进球**: {', '.join(map(str, goals_for.get('away', [])))}"
            )

        # 首个进球时间
        first_goal = goal_timing.get("first_goal_for", {})
        if first_goal and first_goal.get("total"):
            lines.append("\n### 首个进球时间分布")
            lines.append(
                f"**总进球**: {', '.join(map(str, first_goal.get('total', [])))}"
            )
            lines.append(f"**主队**: {', '.join(map(str, first_goal.get('home', [])))}")
            lines.append(f"**客队**: {', '.join(map(str, first_goal.get('away', [])))}")

        # 失球时间分布
        goals_against = goal_timing.get("goals_against", {})
        if goals_against and goals_against.get("total"):
            lines.append("\n### 失球时间分布")
            lines.append(
                f"**总失球**: {', '.join(map(str, goals_against.get('total', [])))}"
            )
            lines.append(
                f"**主队失球**: {', '.join(map(str, goals_against.get('home', [])))}"
            )
            lines.append(
                f"**客队失球**: {', '.join(map(str, goals_against.get('away', [])))}"
            )

        # 首个失球时间
        first_against = goal_timing.get("first_goal_against", {})
        if first_against and first_against.get("total"):
            lines.append("\n### 首个失球时间分布")
            lines.append(
                f"**总失球**: {', '.join(map(str, first_against.get('total', [])))}"
            )
            lines.append(
                f"**主队**: {', '.join(map(str, first_against.get('home', [])))}"
            )
            lines.append(
                f"**客队**: {', '.join(map(str, first_against.get('away', [])))}"
            )

        return "\n".join(lines)

    # def _compare_bookmakers(self, handicap_data: List[dict]) -> str:
    #     if not handicap_data or len(handicap_data) < 2:
    #         return ""
    #
    #     lines = ["\n### 庄家对比分析"]
    #
    #     latest_odds = []
    #     for data in handicap_data:
    #         if data.get("odds"):
    #             latest = data["odds"][-1]
    #             latest_odds.append(
    #                 {
    #                     "name": data["name"],
    #                     "home": latest["home_odds"],
    #                     "handicap": latest["handicap"],
    #                     "away": latest["away_odds"],
    #                 }
    #             )
    #
    #     if not latest_odds:
    #         return ""
    #
    #     home_odds = [(o["name"], o["home"]) for o in latest_odds]
    #     max_home = max(home_odds, key=lambda x: x[1])
    #     min_home = min(home_odds, key=lambda x: x[1])
    #
    #     away_odds = [(o["name"], o["away"]) for o in latest_odds]
    #     max_away = max(away_odds, key=lambda x: x[1])
    #     min_away = min(away_odds, key=lambda x: x[1])
    #
    #     lines.append(
    #         f"- 主胜分歧: 最高 {max_home[0]}@{max_home[1]}, 最低 {min_home[0]}@{min_home[1]}"
    #     )
    #     lines.append(
    #         f"- 客胜分歧: 最高 {max_away[0]}@{max_away[1]}, 最低 {min_away[0]}@{min_away[1]}"
    #     )
    #
    #     converted_handicaps = []
    #     for o in latest_odds:
    #         converted = self._convert_handicap_to_readable(o["handicap"])
    #         converted_handicaps.append((o["name"], converted))
    #     unique_handicaps = list(set(h[1] for h in converted_handicaps))
    #     if len(unique_handicaps) > 1:
    #         lines.append(f"- 盘口分歧: {', '.join(unique_handicaps)}")
    #
    #     return "\n".join(lines)
    #
    # def _compare_european_odds(self, odds_data: List[dict]) -> str:
    #     if not odds_data or len(odds_data) < 2:
    #         return ""
    #
    #     lines = ["\n### 欧赔庄家对比"]
    #
    #     latest_odds = []
    #     for data in odds_data:
    #         if data.get("odds"):
    #             latest = data["odds"][-1]
    #             latest_odds.append(
    #                 {
    #                     "name": data["name"],
    #                     "home": latest["home"],
    #                     "draw": latest["draw"],
    #                     "away": latest["away"],
    #                 }
    #             )
    #
    #     if not latest_odds:
    #         return ""
    #
    #     avg_home = sum(o["home"] for o in latest_odds) / len(latest_odds)
    #     avg_draw = sum(o["draw"] for o in latest_odds) / len(latest_odds)
    #     avg_away = sum(o["away"] for o in latest_odds) / len(latest_odds)
    #
    #     lines.append(f"- 平均赔率: {avg_home:.2f} | {avg_draw:.2f} | {avg_away:.2f}")
    #
    #     min_home = min(latest_odds, key=lambda x: x["home"])
    #     min_draw = min(latest_odds, key=lambda x: x["draw"])
    #     min_away = min(latest_odds, key=lambda x: x["away"])
    #
    #     lines.append(f"- 主胜最低: {min_home['name']}@{min_home['home']}")
    #     lines.append(f"- 平局最低: {min_draw['name']}@{min_draw['draw']}")
    #     lines.append(f"- 客胜最低: {min_away['name']}@{min_away['away']}")
    #
    #     return "\n".join(lines)

    def _format_recent_6(self, recent_record: dict) -> str:
        """格式化近6场战绩（使用新解析的数据格式）"""
        if not recent_record:
            return "N/A"

        wins = recent_record.get("wins", 0)
        draws = recent_record.get("draws", 0)
        losses = recent_record.get("losses", 0)
        goals_for = recent_record.get("goals_for", 0)
        goals_against = recent_record.get("goals_against", 0)

        return f"{wins}胜{draws}平{losses}负 (进{goals_for}失{goals_against})"

    def _format_h2h_for_prompt(
        self, h2h_records: list, home_team: str, away_team: str
    ) -> str:
        """格式化历史交锋数据"""
        if not h2h_records:
            return "\n## 历史交锋\n暂无历史交锋数据"

        lines = ["\n## 历史交锋 (近3年)"]
        lines.append(f"共 {len(h2h_records)} 场历史交锋")

        for record in h2h_records[:8]:  # 最多显示8场
            date = record.get("date", "N/A")
            home = record.get("home_team", "N/A")
            away = record.get("away_team", "N/A")
            home_goals = record.get("home_goals", 0)
            away_goals = record.get("away_goals", 0)
            score = f"{home_goals}-{away_goals}"

            # # 判断结果
            # if home_goals > away_goals:
            #     result = "主胜"
            # elif home_goals < away_goals:
            #     result = "客胜"
            # else:
            #     result = "平"

            lines.append(f"  {date}: {home} {score} {away} ")

        return "\n".join(lines)

    def _format_recent_matches_for_prompt(
        self, matches: list, team_name: str, label: str
    ) -> str:
        """格式化近期比赛数据"""
        if not matches:
            return f"\n{label}\n暂无近期比赛数据"

        lines = [f"\n{label}"]
        lines.append(f"共 {len(matches)} 场近期比赛")

        for record in matches[:6]:  # 最多显示6场
            date = record.get("date", "N/A")
            home = record.get("home_team", "N/A")
            away = record.get("away_team", "N/A")
            home_goals = record.get("home_goals", 0)
            away_goals = record.get("away_goals", 0)
            score = f"{home_goals}-{away_goals}"

            # 判断结果
            if home_goals > away_goals:
                result = "胜"
            elif home_goals < away_goals:
                result = "负"
            else:
                result = "平"

            lines.append(f"  {date}: {home} {score} {away} ({result})")

        return "\n".join(lines)

    def generate(
        self, match_id: str, config: Optional[PromptConfig] = None
    ) -> tuple[str, str]:
        """
        Generate system prompt and user prompt separately.

        Returns:
            tuple: (system_prompt, user_prompt)
                - system_prompt: The role definition and analysis steps (JSON format)
                - user_prompt: The match data and analysis instructions
        """
        if config is None:
            config = PromptConfig()

        data = self._load_match_data(match_id)
        if not data:
            return "ERROR", f"错误: 找不到比赛 {match_id} 的基本面数据"

        # System prompt is separate from match data
        system_prompt = self.SYSTEM_PROMPT.strip()

        # Build user prompt with match data only
        info = data.get("match_info", {})
        home_stats = data.get("home_team_full_stats", {})
        away_stats = data.get("away_team_full_stats", {})
        home_home = data.get("home_team_home_stats", {})
        away_away = data.get("away_team_away_stats", {})
        league_table = (
            data.get("league_table", []) if config.include_league_table else []
        )

        # 只使用bet365的数据（暂时注释掉多家庄家）
        handicap_bms = ["bet365"]
        odds_bms = ["bet365"]
        overunder_bms = ["bet365"]

        # 原有逻辑（已注释）
        # available = self._get_all_available_bookmakers(match_id)
        # if config.use_all_bookmakers:
        #     handicap_bms = available.get("handicap", self.default_handicap_bookmakers)
        #     odds_bms = available.get("odds", self.default_odds_bookmakers)
        #     overunder_bms = available.get("overunder", self.default_handicap_bookmakers)
        # else:
        #     handicap_bms = config.handicap_bookmakers or [config.primary_bookmaker]
        #     odds_bms = config.odds_bookmakers or [config.primary_bookmaker]
        #     overunder_bms = config.handicap_bookmakers or [config.primary_bookmaker]

        handicap_data = []
        for bm in handicap_bms:
            result = self._parse_handicap_odds(match_id, bm)
            if result:
                handicap_data.append(result)

        odds_data = []
        for bm in odds_bms:
            result = self._parse_european_odds(match_id, bm)
            if result:
                odds_data.append(result)

        overunder_data = []
        for bm in overunder_bms:
            result = self._parse_overunder_odds(match_id, bm)
            if result:
                overunder_data.append(result)

        home_team = info.get("home_team", "N/A")
        away_team = info.get("away_team", "N/A")

        prompt_parts = []

        prompt_parts.append("## 待分析比赛")
        # prompt_parts.append(f"**对阵双方**: {home_team} VS {away_team}")
        prompt_parts.append(f"**比赛时间**: {info.get('match_time', 'N/A')}")
        prompt_parts.append(
            f"**联赛**: {info.get('league', 'N/A')} {info.get('round_num', 'N/A')}"
        )
        prompt_parts.append(
            f"**天气**: {info.get('weather', 'N/A')} {info.get('temperature', 'N/A')}"
        )

        prompt_parts.append("\n## 联赛定位")
        for entry in league_table:
            if entry.get("team_name") == home_team:
                prompt_parts.append(
                    f"主队: 第{entry.get('position', 'N/A')}名 {entry.get('points', 0)}分"
                )
            if entry.get("team_name") == away_team:
                prompt_parts.append(
                    f"客队: 第{entry.get('position', 'N/A')}名 {entry.get('points', 0)}分"
                )

        prompt_parts.append("\n## 基本面信息")

        prompt_parts.append("### 主队")
        prompt_parts.append(
            f"- 联赛排名: {home_stats.get('rank', 'N/A')} | 积分: {home_stats.get('points', 'N/A')}"
        )
        prompt_parts.append(
            f"- 总战绩: {home_stats.get('wins', 0)}胜 {home_stats.get('draws', 0)}平 {home_stats.get('losses', 0)}负 "
            f"(进{home_stats.get('goals_for', 0)}失{home_stats.get('goals_against', 0)})"
        )
        prompt_parts.append(
            f"- 主场战绩: {home_home.get('wins', 0)}胜 {home_home.get('draws', 0)}平 {home_home.get('losses', 0)}负 "
            f"(进{home_home.get('goals_for', 0)}失{home_home.get('goals_against', 0)})"
        )
        home_recent_6 = data.get("home_recent_6")
        if home_recent_6:
            prompt_parts.append(f"- 近6场: {self._format_recent_6(home_recent_6)}")
        # prompt_parts.append(f"主队 近10场评分: {info.get('home_recent_ratings', [])}")

        prompt_parts.append("\n### 客队")
        prompt_parts.append(
            f"- 联赛排名: {away_stats.get('rank', 'N/A')} | 积分: {away_stats.get('points', 'N/A')}"
        )
        prompt_parts.append(
            f"- 总战绩: {away_stats.get('wins', 0)}胜 {away_stats.get('draws', 0)}平 {away_stats.get('losses', 0)}负 "
            f"(进{away_stats.get('goals_for', 0)}失{away_stats.get('goals_against', 0)})"
        )
        prompt_parts.append(
            f"- 客场战绩: {away_away.get('wins', 0)}胜 {away_away.get('draws', 0)}平 {away_away.get('losses', 0)}负 "
            f"(进{away_away.get('goals_for', 0)}失{away_away.get('goals_against', 0)})"
        )
        away_recent_6 = data.get("away_recent_6")
        if away_recent_6:
            prompt_parts.append(f"- 近6场: {self._format_recent_6(away_recent_6)}")
        # prompt_parts.append(f"客队 近10场评分: {info.get('away_recent_ratings', [])}")

        # 添加历史交锋和近期比赛数据
        # h2h_records = data.get("h2h_records", [])
        # recent_matches_home = data.get("recent_matches_home", [])
        # recent_matches_away = data.get("recent_matches_away", [])

        # # 历史交锋
        # if config.include_h2h and h2h_records:
        #     prompt_parts.append(
        #         self._format_h2h_for_prompt(h2h_records, home_team, away_team)
        #     )

        # 主队近期比赛
        if config.include_recent_matches and recent_matches_home:
            prompt_parts.append(
                self._format_recent_matches_for_prompt(
                    recent_matches_home, home_team, f"### {home_team}近期比赛 (近1个月)"
                )
            )

        # 客队近期比赛
        if config.include_recent_matches and recent_matches_away:
            prompt_parts.append(
                self._format_recent_matches_for_prompt(
                    recent_matches_away, away_team, f"### {away_team}近期比赛 (近1个月)"
                )
            )

        prompt_parts.append("\n## 亚盘数据 ( 主队水位 | 盘口 | 客队水位 )")
        if handicap_data:
            for entry in handicap_data:
                prompt_parts.append(self._format_handicap_for_prompt(entry))
        else:
            prompt_parts.append("暂无亚盘数据")

        prompt_parts.append("\n## 欧赔数据 ( 主胜 | 平局 | 客胜 )")
        if odds_data:
            for entry in odds_data:
                prompt_parts.append(self._format_european_for_prompt(entry))
        else:
            prompt_parts.append("暂无欧赔数据")

        prompt_parts.append("\n## 大小球数据 ( 大球水位 | 进球数盘口 | 小球水位 )")
        if overunder_data:
            for odds_entry in overunder_data:
                prompt_parts.append(self._format_overunder_for_prompt(odds_entry))
        else:
            prompt_parts.append("暂无大小球数据")

        # 添加进球时间统计
        # goal_timing = data.get("goal_timing")
        # if goal_timing:
        #     prompt_parts.append(self._format_goal_timing_for_prompt(goal_timing))

        user_prompt = "\n".join(prompt_parts)
        return system_prompt, user_prompt

    def save_to_file(
        self, match_id: str, output_path: str, config: Optional[PromptConfig] = None
    ) -> tuple[str, str]:
        system_prompt, user_prompt = self.generate(match_id, config)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(user_prompt)
        return system_prompt, user_prompt


def main():
    generator = GameTheoryPromptGenerator("./data")

    config = PromptConfig(
        include_h2h=True,
        include_recent_matches=True,
        include_league_table=True,
        use_all_bookmakers=True,
    )

    match_id = "2789331"

    print(f"为比赛 {match_id} 生成Prompt (使用全部庄家)...")
    system_prompt, user_prompt = generator.generate(match_id, config)

    output_path = f"prompts/{match_id}_multi_bookmaker_prompt.txt"
    Path(output_path).parent.mkdir(exist_ok=True)
    generator.save_to_file(match_id, output_path, config)
    print(f"已保存到: {output_path}")

    print("\n" + "=" * 60)
    print("User Prompt预览 (前80行):")
    print("=" * 60)
    for i, line in enumerate(user_prompt.split("\n")[:80]):
        print(line)


if __name__ == "__main__":
    main()
