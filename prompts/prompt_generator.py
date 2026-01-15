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

    include_h2h: bool = True
    include_recent_matches: bool = False
    include_league_table: bool = True
    use_all_bookmakers: bool = True
    handicap_bookmakers: List[str] = field(default_factory=list)
    odds_bookmakers: List[str] = field(default_factory=list)
    primary_bookmaker: str = "macau"


class GameTheoryPromptGenerator:
    """博弈论分析Prompt生成器"""

    SYSTEM_PROMPT = """你是一位精通博弈论（Game Theory）与动态赔率逻辑的足彩战略顾问。你不仅擅长拆解机构的心理陷阱，更能识别出哪些变化是由于"资金对冲需求"，哪些是由于"真实战力倾斜"。

## 核心分析框架

### 第一步：战力离散度评估（The Power Gap）
- 比较双方"主场进攻/客场防守"的真实效率差
- 预警信号：如果一方近3场进球数 > 2且另一方进球数 < 0.5，此时任何"升水"都必须首选怀疑为"阻盘（阻碍资金流入）"而非"诱多"

### 第二步：初始定位与赔付压力（Initial Positioning）
- 初始盘口是否完全贴合战力？（深开、浅开、还是平开？）
- 初始回报是否处于机构的"舒适防御区"？

### 第三步：动态博弈假设（Game Theory Hypothesis）
针对盘口与水位的波动，必须进行"双向验证"：
- **假设1（诱多策略）**：机构利用题材制造高回报，吸引散户接盘
- **假设2（阻碍策略）**：机构通过拉高赔率，增加博取难度，利用散户"恐高"心理降低赔付压力

### 第四步：交叉逻辑检验（Cross-Verification）
- **量价背离检查**：如果水位持续拉升但盘口坚挺不动（如半球维持到临场），判断这是否为机构在"高位派发"还是在"关门谢客"
- **欧亚同步性**：欧赔的主胜拉升是否伴随着平赔的剧烈下调？（若是，则是真实防平；若否，则是诱导资金去下盘）

### 第五步：确定性结论
- **博弈结论**：谁是真正的利益既得方？
- **实战建议**：给出首选选项及对应的风险对冲方案
- **陷阱揭露**：明确指出当前盘面最容易让普通玩家产生的"视觉错觉"

## 分析要求

1. **宏观结构分析**：判断初始定位是否足以支撑市场需求平衡
2. **建立博弈假设**：针对数据的变动（如升盘、降水等），假设机构的意图
3. **证据推导**：观察后期数据变化，验证假设是否成立
4. **给出最终倾向**：明确给出谁是"更好的选择"，并指出市场陷阱所在

请严格按以上框架进行分析。"""

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

        self.default_handicap_bookmakers = ["macau", "bet365", "easybet"]
        self.default_odds_bookmakers = ["bet365", "william", "betfair", "easybet"]

    def _extract_float(self, text: str) -> Optional[float]:
        match = re.search(r"[\d.]+", text)
        return float(match.group()) if match else None

    def _convert_handicap_to_decimal(self, handicap: str) -> str:
        handicap = handicap.strip()
        # return handicap
        mapping = {
            "半球": "-0.5",
            "半球/一球": "-0.75",
            "一球": "-1.0",
            "一球/球半": "-1.25",
            "球半": "-1.5",
            "球半/两球": "-1.75",
            "两球": "-2.0",
            "两球/两球半": "-2.25",
            "两球半": "-2.5",
            "两球半/三球": "-2.75",
            "三球": "-3.0",
            "平手": "0",
            "平手/半球": "-0.25",
            "受让平手/半球": "+0.25",
            "受让半球": "+0.5",
            "受让半球/一球": "+0.75",
            "受让一球": "+1.0",
            "受让一球/球半": "+1.25",
            "受让球半": "+1.5",
            "受让球半/两球": "+1.75",
            "受让两球": "+2.0",
            "受让两球/两球半": "+2.25",
            "受让两球半": "+2.5",
            "受让两球半/三球": "+2.75",
            "受让三球": "+3.0",
        }
        if handicap in mapping:
            return mapping[handicap]
        if handicap.startswith("受让"):
            real_handicap = handicap[2:]
            if real_handicap in mapping:
                return mapping[real_handicap]
        if handicap.startswith("客让"):
            real_handicap = handicap[2:]
            if real_handicap in mapping:
                return mapping[real_handicap]
        if handicap.startswith("主让"):
            real_handicap = handicap[2:]
            if real_handicap in mapping:
                return mapping[real_handicap]
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
        with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
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
                status = cols[6].get_text(strip=True)
                if status != "即":
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
        with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
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

    def _get_all_available_bookmakers(self, match_id: str) -> Dict[str, List[str]]:
        handicap_files = list(self.handicap_path.glob(f"{match_id}_*_*.html"))
        odds_files = list(self.odds_path.glob(f"{match_id}_*_*.html"))

        handicap_bms = set()
        odds_bms = set()

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

        return {"handicap": sorted(list(handicap_bms)), "odds": sorted(list(odds_bms))}

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
                converted_handicap = self._convert_handicap_to_decimal(odds["handicap"])
                if odds["handicap"] == "平手":
                    handicap_label = ""
                else:
                    handicap_label = (
                        "主队受让"
                        if odds["handicap"].startswith("受让")
                        else "主队让球"
                    )

                handicap_display = f"{converted_handicap} {handicap_label}".strip()
                lines.append(
                    f"  {odds['home_odds']} | {handicap_display} | {odds['away_odds']} | {odds['time']}"
                )
        else:
            latest = odds_list[-1] if odds_list else None
            if latest:
                converted_handicap = self._convert_handicap_to_decimal(
                    latest["handicap"]
                )
                if latest["handicap"] == "平手":
                    handicap_label = ""
                else:
                    handicap_label = (
                        "主队受让"
                        if latest["handicap"].startswith("受让")
                        else "主队让球"
                    )

                handicap_display = f"{converted_handicap} {handicap_label}".strip()
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

    def _compare_bookmakers(self, handicap_data: List[dict]) -> str:
        if not handicap_data or len(handicap_data) < 2:
            return ""

        lines = ["\n### 庄家对比分析"]

        latest_odds = []
        for data in handicap_data:
            if data.get("odds"):
                latest = data["odds"][-1]
                latest_odds.append(
                    {
                        "name": data["name"],
                        "home": latest["home_odds"],
                        "handicap": latest["handicap"],
                        "away": latest["away_odds"],
                    }
                )

        if not latest_odds:
            return ""

        home_odds = [(o["name"], o["home"]) for o in latest_odds]
        max_home = max(home_odds, key=lambda x: x[1])
        min_home = min(home_odds, key=lambda x: x[1])

        away_odds = [(o["name"], o["away"]) for o in latest_odds]
        max_away = max(away_odds, key=lambda x: x[1])
        min_away = min(away_odds, key=lambda x: x[1])

        lines.append(
            f"- 主胜分歧: 最高 {max_home[0]}@{max_home[1]}, 最低 {min_home[0]}@{min_home[1]}"
        )
        lines.append(
            f"- 客胜分歧: 最高 {max_away[0]}@{max_away[1]}, 最低 {min_away[0]}@{min_away[1]}"
        )

        converted_handicaps = []
        for o in latest_odds:
            converted = self._convert_handicap_to_decimal(o["handicap"])
            converted_handicaps.append((o["name"], converted))
        unique_handicaps = list(set(h[1] for h in converted_handicaps))
        if len(unique_handicaps) > 1:
            lines.append(f"- 盘口分歧: {', '.join(unique_handicaps)}")

        return "\n".join(lines)

    def _compare_european_odds(self, odds_data: List[dict]) -> str:
        if not odds_data or len(odds_data) < 2:
            return ""

        lines = ["\n### 欧赔庄家对比"]

        latest_odds = []
        for data in odds_data:
            if data.get("odds"):
                latest = data["odds"][-1]
                latest_odds.append(
                    {
                        "name": data["name"],
                        "home": latest["home"],
                        "draw": latest["draw"],
                        "away": latest["away"],
                    }
                )

        if not latest_odds:
            return ""

        avg_home = sum(o["home"] for o in latest_odds) / len(latest_odds)
        avg_draw = sum(o["draw"] for o in latest_odds) / len(latest_odds)
        avg_away = sum(o["away"] for o in latest_odds) / len(latest_odds)

        lines.append(f"- 平均赔率: {avg_home:.2f} | {avg_draw:.2f} | {avg_away:.2f}")

        min_home = min(latest_odds, key=lambda x: x["home"])
        min_draw = min(latest_odds, key=lambda x: x["draw"])
        min_away = min(latest_odds, key=lambda x: x["away"])

        lines.append(f"- 主胜最低: {min_home['name']}@{min_home['home']}")
        lines.append(f"- 平局最低: {min_draw['name']}@{min_draw['draw']}")
        lines.append(f"- 客胜最低: {min_away['name']}@{min_away['away']}")

        return "\n".join(lines)

    def generate(self, match_id: str, config: Optional[PromptConfig] = None) -> str:
        if config is None:
            config = PromptConfig()

        data = self._load_match_data(match_id)
        if not data:
            return f"错误: 找不到比赛 {match_id} 的基本面数据"

        info = data.get("match_info", {})
        home_stats = data.get("home_team_full_stats", {})
        away_stats = data.get("away_team_full_stats", {})
        home_home = data.get("home_team_home_stats", {})
        away_away = data.get("away_team_away_stats", {})
        h2h = data.get("h2h_records", []) if config.include_h2h else []
        league_table = (
            data.get("league_table", []) if config.include_league_table else []
        )

        available = self._get_all_available_bookmakers(match_id)

        if config.use_all_bookmakers:
            handicap_bms = available.get("handicap", self.default_handicap_bookmakers)
            odds_bms = available.get("odds", self.default_odds_bookmakers)
        else:
            handicap_bms = config.handicap_bookmakers or [config.primary_bookmaker]
            odds_bms = config.odds_bookmakers or [config.primary_bookmaker]

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

        home_team = info.get("home_team", "N/A")
        away_team = info.get("away_team", "N/A")

        prompt_parts = []

        prompt_parts.append(self.SYSTEM_PROMPT)
        prompt_parts.append("\n" + "=" * 60 + "\n")

        prompt_parts.append("## 待分析比赛")
        prompt_parts.append(f"**对阵双方**: {home_team} VS {away_team}")
        prompt_parts.append(f"**比赛时间**: {info.get('match_time', 'N/A')}")
        prompt_parts.append(
            f"**联赛**: {info.get('league', 'N/A')} {info.get('round_num', 'N/A')}"
        )
        prompt_parts.append(f"**场地**: {info.get('venue', 'N/A')}")
        prompt_parts.append(
            f"**天气**: {info.get('weather', 'N/A')} {info.get('temperature', 'N/A')}"
        )

        prompt_parts.append("\n## 联赛定位")
        for entry in league_table:
            if entry.get("team_name") == home_team:
                prompt_parts.append(
                    f"主队 {home_team}: 第{entry.get('position', 'N/A')}名 {entry.get('points', 0)}分"
                )
            if entry.get("team_name") == away_team:
                prompt_parts.append(
                    f"客队 {away_team}: 第{entry.get('position', 'N/A')}名 {entry.get('points', 0)}分"
                )

        prompt_parts.append("\n## 基本面信息")

        prompt_parts.append(f"### 主队 ({home_team})")
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
        prompt_parts.append(f"- 近10场评分: {info.get('home_recent_ratings', [])}")

        prompt_parts.append(f"\n### 客队 ({away_team})")
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
        prompt_parts.append(f"- 近10场评分: {info.get('away_recent_ratings', [])}")

        if h2h:
            prompt_parts.append(f"\n## 历史交锋 (近5场)")
            h2h.reverse()
            for match in h2h[:5]:
                result_map = {"1": "主胜", "0": "平", "-1": "客胜"}
                result = result_map.get(str(match.get("result", "")), "N/A")
                prompt_parts.append(
                    f"{match.get('date', 'N/A')} | {match.get('league', 'N/A')} | "
                    f"{match.get('home_team', 'N/A')} {match.get('home_goals', 0)} - {match.get('away_goals', 0)} {match.get('away_team', 'N/A')} | {result}"
                )

        prompt_parts.append("\n## 亚盘数据 ( 主队水位 | 盘口 | 客队水位 )")
        if handicap_data:
            prompt_parts.append(
                f"共{len(handicap_data)}家庄家: {', '.join(d['name'] for d in handicap_data)}"
            )

            for data in handicap_data:
                prompt_parts.append(self._format_handicap_for_prompt(data))

            prompt_parts.append(self._compare_bookmakers(handicap_data))
        else:
            prompt_parts.append("暂无亚盘数据")

        prompt_parts.append("\n## 欧赔数据 ( 主胜 | 平局 | 客胜 )")
        if odds_data:
            prompt_parts.append(
                f"共{len(odds_data)}家庄家: {', '.join(d['name'] for d in odds_data)}"
            )

            for data in odds_data:
                prompt_parts.append(self._format_european_for_prompt(data))

            prompt_parts.append(self._compare_european_odds(odds_data))
        else:
            prompt_parts.append("暂无欧赔数据")

        prompt_parts.append("\n" + "=" * 60)
        prompt_parts.append("## 机构共识分析")

        if handicap_data:
            handicaps = []
            for data in handicap_data:
                if data.get("odds"):
                    latest = data["odds"][-1]
                    converted = self._convert_handicap_to_decimal(latest["handicap"])
                    handicaps.append(converted)
            if handicaps:
                from collections import Counter

                most_common = Counter(handicaps).most_common(1)[0]
                prompt_parts.append(
                    f"- 主流盘口: {most_common[0]} ({most_common[1]}家一致)"
                )
        else:
            prompt_parts.append("- 亚盘数据不足，无法判断共识")

        if odds_data:
            avg_home = sum(
                d["odds"][-1]["home"] for d in odds_data if d.get("odds")
            ) / len(odds_data)
            avg_draw = sum(
                d["odds"][-1]["draw"] for d in odds_data if d.get("odds")
            ) / len(odds_data)
            avg_away = sum(
                d["odds"][-1]["away"] for d in odds_data if d.get("odds")
            ) / len(odds_data)
            prompt_parts.append(
                f"- 平均赔率: {avg_home:.2f} | {avg_draw:.2f} | {avg_away:.2f}"
            )
        else:
            prompt_parts.append("- 欧赔数据不足，无法计算平均值")

        prompt_parts.append("\n" + "=" * 60)
        prompt_parts.append("## 分析任务")

        prompt_parts.append("""
请按以下步骤进行分析:

### 步骤1: 宏观定位判断
- 基于联赛排名和积分，主客队的定位差距是多少？
- 初始亚盘定位是否合理反映了这一差距？
- 欧赔的平均赔率是否支持这一判断？

### 步骤2: 庄家共识分析
- 多家庄家的亚盘盘口是否一致？分歧点在哪里？
- 欧赔的平均值与各庄家赔率的差异说明了什么？
- 哪家/哪些庄家的初始定位最值得关注？

### 步骤3: 博弈假设建立
观察赔率变化，假设机构的真实意图是什么？
- **亚盘分析**: 观察澳门、易胜博、Bet365等主要庄家的盘口变化趋势
  - 如果多数庄家降盘: 可能是在降低赔付风险还是诱下盘？
  - 如果多数庄家降水: 是在保护热门方还是诱导投注？
- **欧赔分析**: 观察主胜/平局/客胜的赔率变化方向
  - 哪一方被持续降低赔付？
  - 机构在分散哪一方的风险？

### 步骤4: 交叉验证
结合亚盘和欧赔进行交叉验证:
- 亚盘的降水/升盘与欧赔的对应变化是否一致？
- 是否存在"亚盘诱多但欧赔真实看好"的分歧？
- 各庄家的操作是否形成合力还是各有打算？

### 步骤5: 结论
给出明确的分析结论:
- **推荐选项**: 主胜 / 客胜 / 不让球平局
- **盘口建议**: 对应的亚盘选择
- **市场陷阱**: 指出机构可能设置的诱盘陷阱
- **置信度**: 高 / 中 / 低

请开始分析，重点关注亚盘变化趋势的同时，参考欧赔数据进行交叉验证。
""")

        return "\n".join(prompt_parts)

    def save_to_file(
        self, match_id: str, output_path: str, config: Optional[PromptConfig] = None
    ) -> str:
        prompt = self.generate(match_id, config)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(prompt)
        return prompt


def main():
    generator = GameTheoryPromptGenerator("./data")

    config = PromptConfig(
        include_h2h=True, include_league_table=True, use_all_bookmakers=True
    )

    match_id = "2789331"

    print(f"为比赛 {match_id} 生成Prompt (使用全部庄家)...")
    prompt = generator.generate(match_id, config)

    output_path = f"prompts/{match_id}_multi_bookmaker_prompt.txt"
    Path(output_path).parent.mkdir(exist_ok=True)
    generator.save_to_file(match_id, output_path, config)
    print(f"已保存到: {output_path}")

    print("\n" + "=" * 60)
    print("Prompt预览 (前80行):")
    print("=" * 60)
    for i, line in enumerate(prompt.split("\n")[:80]):
        print(line)


if __name__ == "__main__":
    main()
