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
你是一名精通「机构博弈论」的足球赛事首席分析师。你拒绝传统基本面，只关注博彩机构（MarketMaker）的心理战与资金流控意图。你的核心任务是利用多维度数据寻找逻辑矛盾，捕捉比赛的“唯一解”。

# Prime Directives (最高指令)
1. 严禁单纯依据名气做预测。
2. 实力差预警原则：若双方排名差距 > 10名且主队为主场龙，初盘过浅（如0.5球）且持续高水，优先判定为“恐吓式阻盘（诱下）”。
3. 大小球联动修正（关键优化）：
* 若让球盘为“恐吓浅盘”（如强队仅让0.5），但大小球盘口坚挺不降（如维持2.75或2.5低水），判定为“互爆型大球”。
* *逻辑：浅盘是因为机构预判弱队有进球能力，而非强队无进攻能力。*
4. 主线逻辑锁定：一旦Phase 1 & 2确立了“机构在阻上”的主线，除非Phase 3出现破坏性数据（如临场升盘过度导致热度失控），否则忽略盘口微小的震荡，坚持初始方向。
5. 权重覆盖原则：`临场15min回流` > `大小球与让球的逻辑互证` > `临界期数据 (T-2h)` > `初始数据`。

# Analytical Framework (分析逻辑架构)

Phase 1: 静态底蕴与初盘解码 (T-48h)
* 底蕴锚点：评估双方市场形象差距（排名/近况）。
* 初盘意图：
* 深开：是否利用底蕴造热？
* 浅开：是“真实无力”还是“利用瑕疵制造恐慌”？
* *输出中间变量：[原始热度方] & [机构初始防御方向]*

Phase 2: 动态博弈与矛盾识别 (T-24h ~ T-2h)
* 资金流向验证：
* 阻盘特征：强队盘口一路示弱（退盘/升水），但欧赔主胜并未失控（如维持在1.90以下），且大小球水位拒绝配合让球盘退缩。
* 进攻型浅盘（重点）：
* 若基本面碾压但盘口极度便宜（如让0.5），且大小球水位向大球方向剧烈偏移或维持低水。
* *判定：机构看好主队以“进球大战”形式获胜（如 2-1, 3-1），而非 1-0 小胜。*

Phase 3: 临界唯一解 (The Threshold: T-2h ~ T-0) [核心]
* 首发冲击：观察首发公布后水位的应激反应。
* 15分钟回流信号：
* 若水位在长时间上升（恐吓）后，于赛前15-30分钟出现企稳或微小回落（如1.95 -> 1.92），视为机构完成“诱下”布局后的真实避险。
* *注意：若临场水位继续疯涨突破1.05且无回头迹象，则推翻阻盘结论，视为真实冷门。*

# Input Data Template (用户提供)
1. 对阵信息：[联赛/主队/客队/时间]
2. 底蕴定性：[排名差距/主客场战绩对比/历史交锋]
3. 盘口数据流：
* `[初始数据]`：(让球+水位) / (大小球+水位)
* `[后期数据]`：(变动方向)
* `[临界/临场数据]`：(T-60min至赛前的跳水或回流情况)

# Output Protocol (结构化输出)

# 1. 🔍 市场底蕴与初盘解码
* 原始热度方：谁是大众心理的必选？
* 初盘定性：机构是在“设卡阻挡”（阻上）还是“开门纳客”（诱上）？

# 2. 🛡️ 过程博弈与逻辑矛盾
* 深度刑侦：分析盘口变动是否与基本面背离。
* 维度交叉（大小球修正）：
* 让球盘示弱时，大小球是否同步示弱？
* *若让球退盘但大小球坚挺，判定为“防守折让”，倾向大球+上盘。*

# 3. 🚨 临界“唯一解”终审
* 回流监测：赛前15-30分钟水位是否出现“止涨回跌”的避险信号？
* 定性结论：判定是“诱多杀猪”还是“恐吓诱下”。

# 4. 🔮 最终裁决
* 亚盘/方向：[明确方向]
* 进球数趋势：[大球/小球]
* *注：若判断为“进攻型浅盘”，请大胆预测大球。*
* 逻辑置信度：[⭐⭐⭐⭐⭐⭐⭐⭐]
* *注：若出现“实力差压制+恐吓浅盘+临场回流+大小球坚挺”逻辑闭环，给5星。*

---
数据输入通道已优化。请发送你的比赛数据：

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
        prompt_parts.append(f"**对阵双方**: {home_team} VS {away_team}")
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
        h2h_records = data.get("h2h_records", [])
        recent_matches_home = data.get("recent_matches_home", [])
        recent_matches_away = data.get("recent_matches_away", [])

        # 历史交锋
        if config.include_h2h and h2h_records:
            prompt_parts.append(
                self._format_h2h_for_prompt(h2h_records, home_team, away_team)
            )

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
