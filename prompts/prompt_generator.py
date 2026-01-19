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
{
  "role": "expert_football_odds_game_theory_analyst",
  "analysis_goal": "通过亚盘与欧赔的静态与动态变化，反向推演博彩公司在不同阶段的风险管理策略与真实博弈意图，并给出可执行的投注判断。注意不要引入任何外部信息，只基于以下提供的数据进行分析。",
  "steps": [
    {
      "step_id": 1,
      "step_name": "宏观定位与机构初始定价逻辑判定",
      "tasks": [
        "基于双方排名、积分差距、近期状态、历史对阵等基本面信息，构建常规足球逻辑下的理论盘口区间。",
        "判断初始盘口是否贴合常规实力模型，或存在显著偏离。",
        "分析是否利用强队名气、连胜叙事、主场因素等市场情绪设置低准入门槛。",
        "提出关于机构初盘意图的初步假设（如风险防守、市场引导或信息领先）。"
      ],
      "output": {
        "theoretical_handicap_range": "",
        "initial_pricing_type": "实力定价 / 偏离定价",
        "initial_intent_hypothesis": ""
      }
    },
    {
      "step_id": 2,
      "step_name": "庄家共识强度与异常锚点扫描",
      "tasks": [
        "收集不少于三家主流博彩公司主胜 / 平局 / 客胜的欧赔数据。",
        "计算各结果项的离散度指标（标准差、变异系数）。",
        "比较不同结果项的共识强度，识别离散度显著最低的结果。",
        "扫描是否存在率先开出偏离均值低赔的机构，判断其是否构成市场锚点。",
        "分析该低离散度结果是否为机构重点防范的真实风险点。"
      ],
      "output": {
        "odds_dispersion": {
          "home": "",
          "draw": "",
          "away": ""
        },
        "lowest_dispersion_result": "",
        "anomalous_anchor_bookmaker": "",
        "defensive_risk_focus": ""
      }
    },
    {
      "step_id": 3,
      "step_name": "动态赔率博弈假设构建",
      "tasks": [
        "分析亚洲盘口在时间序列上的变化方向与机构一致性。",
        "判断盘口变化（如降盘、升盘、受让加深）是出于赔付风险控制还是投注引导。",
        "分析水位变化是否承担主要调节功能，或盘口结构发生实质性调整。",
        "观察欧赔中主胜 / 平局 / 客胜的变化趋势与同步程度。",
        "识别被持续压低赔率的结果项，判断其风险属性。",
        "结合亚盘与欧赔，构建一项或多项机构策略假设，并给出反向解释。"
      ],
      "output": {
        "asian_handicap_behavior": "",
        "european_odds_behavior": "",
        "strategy_hypotheses": [
          {
            "hypothesis": "",
            "supporting_evidence": "",
            "counter_explanation": ""
          }
        ]
      }
    },
    {
      "step_id": 4,
      "step_name": "亚欧逻辑交叉验证",
      "tasks": [
        "检验亚盘变化方向与欧赔调整是否一致。",
        "识别是否存在一方市场防守而另一方保持开放的分歧结构。",
        "判断不同机构行为是否形成合力，或存在明显博弈分歧。"
      ],
      "output": {
        "consistency_check": "一致 / 分歧",
        "market_divergence_description": "",
        "bookmaker_alignment": ""
      }
    },
    {
      "step_id": 5,
      "step_name": "临场财务对冲监控（开赛前30分钟）",
      "tasks": [
        "监控盘口不变情况下的水位剧烈波动（如超过10%）。",
        "判断水位波动是顺应市场热度的派发行为，还是逆市的财务防御。",
        "检查是否存在欧赔拉升而亚盘强行压低的量价背离现象。",
        "评估当前水位结构下，哪种赛果对机构的总体赔付压力最小。"
      ],
      "output": {
        "capital_reversion_signal": "",
        "price_volume_divergence": "",
        "minimum_payout_outcome": ""
      }
    },
    {
      "step_id": 6,
      "step_name": "对立观点辩论（反向验证）",
      "tasks": [
        "模拟分析师A，基于盘口与赔率支持主队观点。",
        "模拟分析师B，基于盘口与赔率支持客队观点。",
        "要求双方指出对方逻辑中的潜在漏洞。"
      ],
      "output": {
        "analyst_A_argument": "",
        "analyst_B_argument": "",
        "key_points_of_disagreement": ""
      }
    },
    {
      "step_id": 7,
      "step_name": "综合结论输出",
      "tasks": [
        "在综合所有分析后，给出最优赛果判断。",
        "提供对应的亚洲盘口建议。",
        "明确指出可能存在的市场诱导或陷阱。",
        "给出结论置信度并简要说明原因。"
      ],
      "output": {
        "recommended_outcome": "主胜 / 平局 / 客胜",
        "asian_handicap_recommendation": "",
        "market_trap_warning": "",
        "confidence_level": "高 / 中 / 低"
      }
    }
  ]
}

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
            converted = self._convert_handicap_to_readable(o["handicap"])
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
        # prompt_parts.append(
        #     f"- 主场战绩: {home_home.get('wins', 0)}胜 {home_home.get('draws', 0)}平 {home_home.get('losses', 0)}负 "
        #     f"(进{home_home.get('goals_for', 0)}失{home_home.get('goals_against', 0)})"
        # )
        # prompt_parts.append(f"- 近10场评分: {info.get('home_recent_ratings', [])}")

        prompt_parts.append("\n### 客队")
        prompt_parts.append(
            f"- 联赛排名: {away_stats.get('rank', 'N/A')} | 积分: {away_stats.get('points', 'N/A')}"
        )
        prompt_parts.append(
            f"- 总战绩: {away_stats.get('wins', 0)}胜 {away_stats.get('draws', 0)}平 {away_stats.get('losses', 0)}负 "
            f"(进{away_stats.get('goals_for', 0)}失{away_stats.get('goals_against', 0)})"
        )
        # prompt_parts.append(
        #     f"- 客场战绩: {away_away.get('wins', 0)}胜 {away_away.get('draws', 0)}平 {away_away.get('losses', 0)}负 "
        #     f"(进{away_away.get('goals_for', 0)}失{away_away.get('goals_against', 0)})"
        # )
        # prompt_parts.append(f"- 近10场评分: {info.get('away_recent_ratings', [])}")

        prompt_parts.append("\n## 亚盘数据 ( 主队水位 | 盘口 | 客队水位 )")
        if handicap_data:
            prompt_parts.append(
                f"共{len(handicap_data)}家庄家: {', '.join(d['name'] for d in handicap_data)}"
            )

            for data in handicap_data:
                prompt_parts.append(self._format_handicap_for_prompt(data))

            # prompt_parts.append(self._compare_bookmakers(handicap_data))
        else:
            prompt_parts.append("暂无亚盘数据")

        prompt_parts.append("\n## 欧赔数据 ( 主胜 | 平局 | 客胜 )")
        if odds_data:
            prompt_parts.append(
                f"共{len(odds_data)}家庄家: {', '.join(d['name'] for d in odds_data)}"
            )

            for data in odds_data:
                prompt_parts.append(self._format_european_for_prompt(data))

            # prompt_parts.append(self._compare_european_odds(odds_data))
        else:
            prompt_parts.append("暂无欧赔数据")

        # prompt_parts.append("\n" + "=" * 60)
        # prompt_parts.append("## 机构共识分析")

        # if handicap_data:
        #     handicaps = []
        #     for data in handicap_data:
        #         if data.get("odds"):
        #             latest = data["odds"][-1]
        #             converted = self._convert_handicap_to_readable(latest["handicap"])
        #             handicaps.append(converted)
        #     if handicaps:
        #         from collections import Counter

        #         most_common = Counter(handicaps).most_common(1)[0]
        #         prompt_parts.append(
        #             f"- 主流盘口: {most_common[0]} ({most_common[1]}家一致)"
        #         )
        # else:
        #     prompt_parts.append("- 亚盘数据不足，无法判断共识")

        # if odds_data:
        #     avg_home = sum(
        #         d["odds"][-1]["home"] for d in odds_data if d.get("odds")
        #     ) / len(odds_data)
        #     avg_draw = sum(
        #         d["odds"][-1]["draw"] for d in odds_data if d.get("odds")
        #     ) / len(odds_data)
        #     avg_away = sum(
        #         d["odds"][-1]["away"] for d in odds_data if d.get("odds")
        #     ) / len(odds_data)
        #     prompt_parts.append(
        #         f"- 平均赔率: {avg_home:.2f} | {avg_draw:.2f} | {avg_away:.2f}"
        #     )
        # else:
        #     prompt_parts.append("- 欧赔数据不足，无法计算平均值")

#         prompt_parts.append("\n" + "=" * 60)
#         prompt_parts.append("## 分析任务")

#         prompt_parts.append("""
# 请按以下步骤进行分析:

# ### 步骤1: 宏观定位与机构初衷判定
# - 基于排名、积分散差，计算客队在常规逻辑下应有的让步等级。
# - 初始亚盘定位是否合理反映了这一差距？
# - 判断初盘是属于**“实力盘”（真诚看好）还是“诱导盘”**（利用名气平衡资金）。

# ### 步骤2: 庄家共识与“异常锚点”扫描
# - 标准差深度解析:
#   1、统计多家博彩公司主胜 / 平局 / 客胜赔率的分布情况；
#   2、计算各结果的离散度指标（如标准差、变异系数）。
#   3、识别离散度显著最低的结果，结合足彩风险管理逻辑，判断该结果是否为博彩公司重点防守的风险节点，并说明其潜在投注含义。
# - 哪家/哪些庄家的初始定位最值得关注？

# ### 步骤3: 博弈假设建立
# 观察赔率变化，假设机构的真实意图是什么？
# - **亚盘分析**: 观察澳门、易胜博、Bet365等主要庄家的盘口变化趋势
#   - 如果多数庄家降盘: 可能是在降低赔付风险还是诱下盘？
#   - 如果多数庄家降水: 是在保护热门方还是诱导投注？
# - **欧赔分析**: 观察主胜/平局/客胜的赔率变化方向
#   - 哪一方被持续降低赔付？
#   - 机构在分散哪一方的风险？

# ### 步骤4: 交叉验证
# 结合亚盘和欧赔进行交叉验证:
# - 亚盘的降水/升盘与欧赔的对应变化是否一致？
# - 是否存在"亚盘诱多但欧赔真实看好"的分歧？
# - 各庄家的操作是否形成合力还是各有打算？

# ### 步骤5: 监控开赛前30分钟的即时水位异动，以捕捉最终的庄家财务对冲信号
# 现在进入博弈逻辑的最后环节：【临场财务对冲监控】。请分析开赛前30分钟的即时数据，重点回答以下三个核心问题：
# - 资金归位信号：在盘口不变的情况下，哪一方的水位出现了超过 10% 的剧烈波动？这种波动是属于'顺应市场热度'的派发，还是'逆市操作'的财务防御？
# - 末端欧亚一致性检查：是否存在欧赔（如主胜）在拉升，但亚盘（如主队水位）却在强行压低的现象？这种**'量价背离'**是否代表机构在利用最后的时间差诱骗筹码？
# - 终极利益既得方判定：基于最后5分钟的赔付压力分布，如果比赛以目前水位结束，哪种赛果对机构而言'赔付总额最小'？

# ### 步骤6: 辩论环节
# 请模拟两名分析师，分析师 A 倾向于主胜，分析师 B 倾向于客胜。请让他们进行辩论。

# ### 步骤7: 结论
# 给出明确的分析结论:
# - **推荐选项**: 主胜 / 客胜 / 不让球平局
# - **盘口建议**: 对应的亚盘选择
# - **市场陷阱**: 指出机构可能设置的诱盘陷阱
# - **置信度**: 高 / 中 / 低

# 请开始分析，重点关注亚盘变化趋势的同时，参考欧赔数据进行交叉验证。
# """)

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
