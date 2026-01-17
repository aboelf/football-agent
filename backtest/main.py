"""
回测脚本 - 测试模型预测准确率

功能:
1. 读取 prompts/save/ 下所有赛事的 prompt 文件
2. 使用指定模型进行预测
3. 根据 bet365 终盘赔率计算收入
4. 输出回测报表

使用方式:
    python backtest/main.py --model gemini-3.0-flash    # 使用 Gemini 3.0 Flash
    python backtest/main.py --model gemini-3.0-pro      # 使用 Gemini 3.0 Pro
    python backtest/main.py --model minimax-m2.1        # 使用 MiniMax M2.1
"""

import argparse
import json
import os
import re
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
import httpx

# 设置默认环境变量 (如果未设置)
# 请替换为你的实际 API Key
os.environ.setdefault(
    "MINIMAX_API_KEY",
    "sk-cp-aQTgjmdyS0RmLEBBd_yy6TPDo8mfsi-e23MqbYx2e5f6D6X6a0S3jNjPLYoyPFTpyqlNGAOCsn1ySEneA6eoTuGOSLJt5DApUVUCtE__0zXONlpal-zY0r8",
)

os.environ.setdefault(
    "LOCAL_GEMINI_API_KEY",
    "sk-geminixxxxx",
)
# 默认配置
DEFAULT_MODEL = "gemini-3.0-flash"
BET_AMOUNT = 100

# 支持的模型列表
AVAILABLE_MODELS = {
    "gemini-3.0-flash": ("local-gemini", "Gemini 3.0 Flash"),
    "gemini-3.0-pro": ("local-gemini", "Gemini 3.0 Pro"),
    "minimax-m2.1": ("minimax", "MiniMax M2.1"),
}

# API 配置
AI_PROVIDERS = {
    "minimax": {
        "name": "MiniMax",
        "models": {
            "minimax-m2.1": {
                "name": "MiniMax-M2.1",
                "api_key_env": "MINIMAX_API_KEY",
                "endpoint": "https://api.minimaxi.com/anthropic/v1/messages",
                "temperature": 0.7,
                "max_tokens": 4096,
                "thinking": True,
                "request_format": "anthropic",  # 使用 Anthropic 格式
            }
        },
    },
    "local-gemini": {
        "name": "本地 Gemini (兼容OpenAI)",
        "models": {
            "gemini-3.0-flash": {
                "name": "Gemini 3.0 Flash",
                "api_key_env": "LOCAL_GEMINI_API_KEY",
                "endpoint": "http://localhost:8000/v1/chat/completions",
                "temperature": 0.3,
                "max_tokens": 4096,
                "thinking": False,
                "request_format": "openai",  # 使用 OpenAI 格式
            },
            "gemini-3.0-pro": {
                "name": "Gemini 3.0 Pro",
                "api_key_env": "LOCAL_GEMINI_API_KEY",
                "endpoint": "http://localhost:8000/v1/chat/completions",
                "temperature": 0.3,
                "max_tokens": 4096,
                "thinking": False,
                "request_format": "openai",  # 使用 OpenAI 格式
            },
        },
    },
}

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="回测脚本 - 测试模型预测准确率",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
可用模型:
  gemini-3.0-flash   Gemini 3.0 Flash (默认)
  gemini-3.0-pro     Gemini 3.0 Pro
  minimax-m2.1       MiniMax M2.1
        """
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=DEFAULT_MODEL,
        choices=list(AVAILABLE_MODELS.keys()),
        help=f"选择AI模型 (默认: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--bet", "-b",
        type=int,
        default=BET_AMOUNT,
        help=f"单场投注金额 (默认: {BET_AMOUNT})"
    )
    return parser.parse_args()


def init_config(args):
    """初始化配置"""
    global PROVIDER, MODEL, BET_AMOUNT

    # 根据模型查找对应的提供商
    if args.model in AVAILABLE_MODELS:
        PROVIDER, model_display_name = AVAILABLE_MODELS[args.model]
        MODEL = args.model
    else:
        raise ValueError(f"不支持的模型: {args.model}")

    BET_AMOUNT = args.bet
    return MODEL, PROVIDER, BET_AMOUNT

# 比赛信息缓存
MATCH_INFO_CACHE = {}

# AI 分析结果保存目录
SCRIPT_DIR = Path(__file__).parent.resolve()
AI_ANALYZE_DIR = SCRIPT_DIR / "ai_analyze"
AI_ANALYZE_DIR.mkdir(exist_ok=True)


def save_ai_result(match_id, model, ai_response):
    """保存AI分析结果到文件"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_model_name = model.replace("/", "_").replace(":", "_")
        filename = f"{timestamp}_{match_id}_{safe_model_name}.md"
        filepath = AI_ANALYZE_DIR / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(ai_response)

        print(f"  [保存] AI结果已保存到: {filepath}")
        return True
    except Exception as e:
        print(f"  [警告] 保存AI结果失败: {e}")
        return False


def load_api_config():
    """加载API配置"""
    provider_config = AI_PROVIDERS.get(PROVIDER)
    if not provider_config:
        raise ValueError(f"不支持的AI提供商: {PROVIDER}")

    model_config = provider_config["models"].get(MODEL)
    if not model_config:
        raise ValueError(f"不支持的模型: {MODEL}")

    api_key = os.environ.get(model_config["api_key_env"])
    if not api_key:
        raise ValueError(f"未配置 {model_config['api_key_env']} 环境变量")

    return model_config, api_key


def call_ai_analyze(prompt, match_id):
    """调用AI进行预测"""
    model_config, api_key = load_api_config()

    system_prompt = "你是一位精通博弈论的足彩分析专家，请根据提供的比赛数据和赔率信息进行专业的博弈论分析。分析要逻辑清晰，有理有据。"

    client = httpx.Client(timeout=300.0)

    # 根据 API 格式选择不同的请求方式
    request_format = model_config.get("request_format", "openai")

    if request_format == "anthropic":
        # MiniMax 使用 Anthropic 格式
        response = client.post(
            model_config["endpoint"],
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "Anthropic-Version": "2023-06-01",
            },
            json={
                "model": "MiniMax-M2.1",
                "max_tokens": model_config["max_tokens"],
                "temperature": model_config["temperature"],
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            },
            timeout=300.0,
        )

        result = response.json()

        if response.status_code != 200:
            raise Exception(f"MiniMax API错误 (状态码 {response.status_code})")

        if "content" in result:
            ai_response = ""
            for block in result["content"]:
                if block.get("type") == "text":
                    ai_response += block.get("text", "")
                elif block.get("type") == "thinking":
                    ai_response += (
                        f"\n\n[思考过程]\n{block.get('thinking', '')}"
                        if block.get("thinking")
                        else ""
                    )
            return ai_response
        else:
            raise Exception("AI返回格式未知")

    else:
        # OpenAI/Gemini 格式
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        response = client.post(
            model_config["endpoint"],
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": messages,
                "temperature": model_config["temperature"],
                "max_tokens": model_config["max_tokens"],
            },
            timeout=300.0,
        )

        result = response.json()

        if "choices" in result:
            ai_response = result["choices"][0]["message"]["content"]
            return ai_response
        else:
            raise Exception(f"AI调用失败: {result.get('error', '未知错误')}")


def get_prompt_files():
    """获取所有prompt文件"""
    # 使用绝对路径，基于脚本文件位置
    script_dir = Path(__file__).parent.resolve()
    prompts_dir = script_dir.parent / "prompts" / "save"
    if not prompts_dir.exists():
        return []
    return list(prompts_dir.glob("*_prompt.txt"))


def load_match_info(match_id):
    """加载比赛信息（包含实际比分）"""
    if match_id in MATCH_INFO_CACHE:
        return MATCH_INFO_CACHE[match_id]

    # 使用绝对路径
    script_dir = Path(__file__).parent.resolve()
    analysis_dir = script_dir.parent / "data" / "analysis"
    for f in analysis_dir.glob(f"{match_id}_*.json"):
        with open(f, "r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, list):
                data = data[0]

            match_info = {
                "match_id": match_id,
                "home_team": data.get("match_info", {}).get("home_team", ""),
                "away_team": data.get("match_info", {}).get("away_team", ""),
                "final_score": data.get("match_info", {}).get("final_score", ""),
            }
            MATCH_INFO_CACHE[match_id] = match_info
            return match_info

    return None


def get_bet365_final_odds(match_id):
    """获取bet365终盘赔率"""
    # 使用绝对路径
    script_dir = Path(__file__).parent.resolve()
    handicap_dir = script_dir.parent / "data" / "odds" / "handicap"
    html_files = list(handicap_dir.glob(f"{match_id}_bet365_*.html"))

    if not html_files:
        print(f"[警告] 未找到 {match_id} 的 bet365 赔率文件")
        return None

    # 取最新的文件
    html_file = max(html_files, key=lambda f: f.stat().st_mtime)

    with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", attrs={"cellspacing": "1"})
    if not table:
        print(f"[警告] {match_id} 的 bet365 文件无法解析表格")
        return None

    rows = table.find_all("tr", align="center")
    final_odds = None

    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) < 7:
            continue

        status = cols[6].get_text(strip=True)
        if status != "即":  # 只取即时刻数据
            continue

        home_odds_text = cols[2].get_text(strip=True)
        handicap = cols[3].get_text(strip=True)
        away_odds_text = cols[4].get_text(strip=True)

        # 提取数值
        home_match = re.search(r"[\d.]+", home_odds_text)
        away_match = re.search(r"[\d.]+", away_odds_text)

        if home_match and away_match:
            final_odds = {
                "home_odds": float(home_match.group()),
                "away_odds": float(away_match.group()),
                "handicap": handicap,
                "source_file": html_file.name,
            }

    if final_odds is None:
        print(f"[警告] {match_id} 的 bet365 文件没有即时刻赔率记录")

    return final_odds


def analyze_prediction(ai_response, match_id):
    """调用AI对预测结果进行二次分析，确认购买建议

    Args:
        ai_response: 第一次AI分析的完整返回
        match_id: 比赛ID

    Returns:
        prediction: "主胜" 或 "客胜"
    """
    # 二次分析的系统提示词
    system_prompt = """你是一位专业的足彩分析师，负责从AI分析结果中提取明确的亚盘购买建议。

你的任务是：
1. 仔细阅读提供的分析内容
2. 提取最关键的亚盘购买建议
3. 只能返回一个结果：要么"主胜"（主队获胜/上盘），要么"客胜"（客队获胜/下盘）

输出格式：
直接输出"主胜"或"客胜"，不要有任何其他内容。"""

    # 构造用户提示词
    user_prompt = f"""请从以下亚盘分析中提取最明确的购买建议：

=== 分析内容 ===
{ai_response}
=== 分析结束 ===

请直接输出：主胜 或 客胜"""

    model_config, api_key = load_api_config()

    client = httpx.Client(timeout=300.0)

    request_format = model_config.get("request_format", "openai")

    if request_format == "anthropic":
        # MiniMax 格式
        response = client.post(
            model_config["endpoint"],
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "Anthropic-Version": "2023-06-01",
            },
            json={
                "model": "MiniMax-M2.1",
                "max_tokens": 512,
                "temperature": 0.1,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=300.0,
        )

        result = response.json()

        if response.status_code != 200:
            raise Exception(f"MiniMax API错误 (状态码 {response.status_code})")

        if "content" in result:
            prediction = ""
            for block in result["content"]:
                if block.get("type") == "text":
                    prediction = block.get("text", "").strip()
                    break
            return prediction if prediction in ["主胜", "客胜"] else None
        else:
            raise Exception("AI返回格式未知")

    else:
        # OpenAI/Gemini 格式
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = client.post(
            model_config["endpoint"],
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 512,
            },
            timeout=300.0,
        )

        result = response.json()

        if "choices" in result:
            prediction = result["choices"][0]["message"]["content"].strip()
            # 只接受主胜或客胜
            if prediction in ["主胜", "客胜"]:
                return prediction
            return None
        else:
            raise Exception(f"AI调用失败: {result.get('error', '未知错误')}")


def extract_prediction(ai_response):
    """从AI返回中提取预测结果

    期望从"实战建议"或"最终倾向"段落提取
    返回: "主胜", "客胜", 或 None
    """
    if not ai_response:
        return None

    # 转换为小写便于匹配
    response_lower = ai_response.lower()

    # 关键词模式
    patterns = [
        # 首选/推荐模式
        r"(?:首选|推荐|倾向|选择)[^\n]*?(主队|客队|主胜|客胜|主让|客让|上盘|下盘)",
        r"(?:最终|实战)[^\n]*?(主队|客队|主胜|客胜|主让|客让|上盘|下盘)",
        # 结论模式
        r"结论[^\n]*?(主队|客队|主胜|客胜|主让|客让|上盘|下盘)",
        r"预测[^\n]*?(主队|客队|主胜|客胜|主让|客让|上盘|下盘)",
        # 直接给出结果
        r"(?:主队|主胜|上盘)[^\n\d]{0,10}胜",
        r"(?:客队|客胜|下盘)[^\n\d]{0,10}胜",
    ]

    for pattern in patterns:
        match = re.search(pattern, response_lower)
        if match:
            result = match.group(1)
            # 判断结果
            if any(kw in result for kw in ["主队", "主胜", "上盘", "主让"]):
                return "主胜"
            elif any(kw in result for kw in ["客队", "客胜", "下盘", "客让"]):
                return "客胜"

    # 备选：检查是否明确提到"主队获胜"或"客队获胜"
    if "主队获胜" in ai_response or "主胜" in ai_response:
        return "主胜"
    if "客队获胜" in ai_response or "客胜" in ai_response:
        return "客胜"

    # 尝试从完整文本中寻找更明确的结论
    # 检查"实战建议"部分
    practical_pattern = r"(?:实战建议|最终建议)[:：]?\s*(.+?)(?:\n\n|\n[A-Z]|$)"
    practical_match = re.search(practical_pattern, ai_response, re.IGNORECASE | re.DOTALL)
    if practical_match:
        suggestion = practical_match.group(1)
        suggestion_lower = suggestion.lower()
        if any(kw in suggestion_lower for kw in ["主队", "主胜", "上盘", "主让"]):
            return "主胜"
        if any(kw in suggestion_lower for kw in ["客队", "客胜", "下盘", "客让"]):
            return "客胜"

    print(f"[警告] 无法从AI返回中提取预测结果")
    return None


def parse_score(score_str):
    """解析比分字符串，返回主队进球和客队进球"""
    if not score_str:
        return None, None

    parts = score_str.split("-")
    if len(parts) != 2:
        return None, None

    try:
        home_goals = int(parts[0])
        away_goals = int(parts[1])
        return home_goals, away_goals
    except (ValueError, IndexError):
        return None, None


def determine_winner(home_goals, away_goals, handicap):
    """根据比分和盘口判断亚盘输赢

    handicap 格式示例: "平手", "半球", "一球", "-0.25" 等
    """
    if home_goals is None or away_goals is None:
        return None

    # 计算实际比分差
    goal_diff = home_goals - away_goals

    # 解析盘口
    handicap_str = handicap.strip()

    # 处理各种盘口格式
    if "平手" in handicap_str or handicap_str == "0":
        # 平手盘：进球多者赢
        if goal_diff > 0:
            return "主胜"
        elif goal_diff < 0:
            return "客胜"
        else:
            return "走盘"

    # 半球盘 (0.5)
    half_patterns = ["半球", "0.5", "半/一"]
    if "半球" in handicap_str or "0.5" in handicap_str or "半/一" in handicap_str:
        if goal_diff > 0.5:
            return "主胜"
        elif goal_diff < 0.5:
            return "客胜"
        else:
            return "客胜"  # 半球盘刚好0.5算输

    # 一球盘 (1.0)
    if "一球" in handicap_str or "1.0" in handicap_str:
        if goal_diff > 1:
            return "主胜"
        elif goal_diff < 1:
            return "客胜"
        else:
            return "走盘"

    # 一球/球半 (1.25)
    if "一球/球半" in handicap_str or "1/1.5" in handicap_str or "1.25" in handicap_str:
        if goal_diff > 1.25:
            return "主胜"
        elif goal_diff < 1.25:
            return "客胜"
        else:
            return "客赢半"  # 刚好赢1球输半

    # 球半 (1.5)
    if "球半" in handicap_str or "1.5" in handicap_str:
        if goal_diff > 1.5:
            return "主胜"
        elif goal_diff < 1.5:
            return "客胜"
        else:
            return "客胜"

    # 球半/两球 (1.75)
    if "球半/两球" in handicap_str or "1.5/2" in handicap_str or "1.75" in handicap_str:
        if goal_diff > 1.75:
            return "主胜"
        elif goal_diff < 1.75:
            return "客胜"
        else:
            return "客赢半"

    # 两球 (2.0)
    if "两球" in handicap_str or "2.0" in handicap_str:
        if goal_diff > 2:
            return "主胜"
        elif goal_diff < 2:
            return "客胜"
        else:
            return "走盘"

    # 默认：简单比较进球数
    if goal_diff > 0:
        return "主胜"
    elif goal_diff < 0:
        return "客胜"
    else:
        return "走盘"


def calculate_profit(prediction, actual_result, odds, handicap):
    """计算盈亏

    Args:
        prediction: 预测结果 ("主胜" 或 "客胜")
        actual_result: 实际比分 ("2-1")
        odds: 赔率字典 {"home_odds": x.xx, "away_odds": x.xx}
        handicap: 盘口 ("平手", "半球" 等)

    Returns:
        profit: 盈亏金额
    """
    if not prediction or not actual_result or not odds:
        return None

    # 解析比分
    home_goals, away_goals = parse_score(actual_result)
    if home_goals is None:
        return None

    # 判断实际亚盘结果
    actual = determine_winner(home_goals, away_goals, handicap)
    if not actual:
        return None

    # 计算盈亏
    if actual == "走盘":
        profit = 0
    elif prediction == actual:
        # 预测正确：根据预测方向选择赔率
        if prediction == "主胜":
            profit = BET_AMOUNT * odds["home_odds"] - BET_AMOUNT
        else:
            profit = BET_AMOUNT * odds["away_odds"] - BET_AMOUNT
    else:
        # 预测错误
        profit = -BET_AMOUNT

    return profit, actual


def generate_report(results):
    """生成回测报表"""
    # 过滤有效结果
    valid_results = [r for r in results if r["profit"] is not None]

    if not valid_results:
        print("[错误] 没有有效的回测结果")
        return

    # 统计
    total_matches = len(valid_results)
    correct_predictions = sum(1 for r in valid_results if r["profit"] > 0)
    push_predictions = sum(1 for r in valid_results if r["profit"] == 0)
    wrong_predictions = sum(1 for r in valid_results if r["profit"] < 0)

    total_investment = total_matches * BET_AMOUNT
    total_profit = sum(r["profit"] for r in valid_results)
    roi = (total_profit / total_investment) * 100 if total_investment > 0 else 0
    accuracy = (correct_predictions / (total_matches - push_predictions)) * 100 if (total_matches - push_predictions) > 0 else 0

    # 生成报表
    report = f"""# 回测报表

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**使用模型**: {MODEL}
**投注金额**: {BET_AMOUNT}元/场

## 统计概览

| 指标 | 数值 |
|------|------|
| 测试样本 | {total_matches} 场 |
| 正确预测 | {correct_predictions} 场 |
| 走盘 | {push_predictions} 场 |
| 错误预测 | {wrong_predictions} 场 |
| 准确率 | {accuracy:.1f}% |
| 总投入 | {total_investment} 元 |
| 总收入 | {total_investment + total_profit:.2f} 元 |
| 净收益 | {total_profit:.2f} 元 |
| 收益率 | {roi:.2f}% |

## 详细明细

| 比赛ID | 对阵 | 预测 | 实际比分 | 盘口 | 主赔 | 客赔 | 结果 | 盈亏 |
|--------|------|------|----------|------|------|------|------|------|
"""

    for r in valid_results:
        match_info = r["match_info"]
        odds = r["odds"]
        handicap = odds.get("handicap", "-") if odds else "-"
        home_odds = f"{odds['home_odds']:.2f}" if odds and "home_odds" in odds else "-"
        away_odds = f"{odds['away_odds']:.2f}" if odds and "away_odds" in odds else "-"
        result = r.get("actual_result", "-")
        profit = f"{r['profit']:.2f}" if r["profit"] is not None else "-"

        teams = f"{match_info['home_team']} vs {match_info['away_team']}"
        match_id = r["match_id"]

        report += f"| {match_id} | {teams} | {r['prediction']} | {r['actual_score']} | {handicap} | {home_odds} | {away_odds} | {result} | {profit} |\n"

    # 保存报表
    report_path = SCRIPT_DIR / "backtest_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n[完成] 回测报表已保存到: {report_path}")
    print(f"\n统计概览:")
    print(f"  - 测试样本: {total_matches} 场")
    print(f"  - 正确: {correct_predictions} 场 | 走盘: {push_predictions} 场 | 错误: {wrong_predictions} 场")
    print(f"  - 准确率: {accuracy:.1f}%")
    print(f"  - 净收益: {total_profit:.2f} 元 | 收益率: {roi:.2f}%")


def run_backtest():
    """运行回测"""
    print("=" * 60)
    print("回测脚本启动")
    print(f"模型: {MODEL} | 投注金额: {BET_AMOUNT}元/场")
    print("=" * 60)

    # 获取所有prompt文件
    prompt_files = get_prompt_files()
    if not prompt_files:
        print("[错误] 未找到任何 prompt 文件")
        return

    print(f"\n找到 {len(prompt_files)} 个待测试的 prompt 文件\n")

    results = []
    errors = []

    for i, prompt_file in enumerate(prompt_files, 1):
        # 从文件名提取 match_id
        filename = prompt_file.stem
        parts = filename.split("_")
        if len(parts) < 1:
            print(f"[跳过] 文件名格式错误: {filename}")
            continue

        match_id = parts[0]

        print(f"[{i}/{len(prompt_files)}] 处理比赛 {match_id}...")

        # 1. 读取prompt
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt = f.read()
        except Exception as e:
            print(f"  [错误] 读取prompt失败: {e}")
            errors.append({"match_id": match_id, "error": f"读取prompt失败: {e}"})
            continue

        # 2. 加载比赛信息
        match_info = load_match_info(match_id)
        if not match_info:
            print(f"  [警告] 未找到比赛 {match_id} 的分析数据")
            errors.append({"match_id": match_id, "error": "未找到分析数据"})
            continue

        # 3. AI预测 (第一次分析)
        try:
            ai_response = call_ai_analyze(prompt, match_id)
            # 保存AI分析结果
            save_ai_result(match_id, MODEL, ai_response)
        except Exception as e:
            print(f"  [错误] AI预测失败: {e}")
            errors.append({"match_id": match_id, "error": f"AI预测失败: {e}"})
            continue

        # 4. 二次分析 - 确认购买建议
        try:
            print(f"  [二次分析] 正在确认购买建议...")
            prediction = analyze_prediction(ai_response, match_id)
            if prediction:
                print(f"  [二次分析] 购买建议: {prediction}")
            else:
                print(f"  [警告] 二次分析未能提取有效预测")
                errors.append({"match_id": match_id, "error": "二次分析未能提取有效预测"})
                continue
        except Exception as e:
            print(f"  [错误] 二次分析失败: {e}")
            errors.append({"match_id": match_id, "error": f"二次分析失败: {e}"})
            continue

        # 5. 获取赔率
        odds = get_bet365_final_odds(match_id)
        if not odds:
            print(f"  [警告] 无法获取赔率")
            errors.append({"match_id": match_id, "error": "无法获取赔率"})
            continue

        # 6. 计算盈亏
        handicap = odds.get("handicap", "平手")
        calc_result = calculate_profit(prediction, match_info["final_score"], odds, handicap)

        if calc_result is None:
            print(f"  [警告] 无法计算盈亏")
            errors.append({"match_id": match_id, "error": "无法计算盈亏"})
            continue

        profit, actual_result = calc_result

        result = {
            "match_id": match_id,
            "match_info": match_info,
            "prediction": prediction,
            "actual_score": match_info["final_score"],
            "odds": odds,
            "profit": profit,
            "actual_result": actual_result,
        }
        results.append(result)

        profit_str = f"+{profit:.2f}" if profit >= 0 else f"{profit:.2f}"
        print(f"  预测: {prediction} | 实际: {match_info['final_score']} ({actual_result}) | 盈亏: {profit_str}")

    # 7. 生成报表
    print("\n" + "=" * 60)
    generate_report(results)

    # 输出错误统计
    if errors:
        print(f"\n错误统计 ({len(errors)} 个):")
        for e in errors:
            print(f"  - {e['match_id']}: {e['error']}")


if __name__ == "__main__":
    # 解析命令行参数
    args = parse_args()
    init_config(args)

    # 运行回测
    run_backtest()
