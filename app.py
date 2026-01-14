"""
足球比赛赔率分析系统 - Flask 主应用
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from downloads.downloader import DataDownloader, OddsType, Bookmaker
import os
import json
from pathlib import Path

os.environ.setdefault(
    "MINIMAX_API_KEY",
    "sk-cp-aQTgjmdyS0RmLEBBd_yy6TPDo8mfsi-e23MqbYx2e5f6D6X6a0S3jNjPLYoyPFTpyqlNGAOCsn1ySEneA6eoTuGOSLJt5DApUVUCtE__0zXONlpal-zY0r8",
)

app = Flask(__name__, template_folder="templates", static_folder="static")

# 初始化下载器
downloader = DataDownloader(base_path="./data")

AI_PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek",
        "models": {
            "deepseek-chat": {
                "name": "DeepSeek Chat",
                "api_key_env": "DEEPSEEK_API_KEY",
                "endpoint": "https://api.deepseek.com/chat/completions",
                "temperature": 0.3,
                "max_tokens": 4096,
            }
        },
    },
    "minimax": {
        "name": "MiniMax",
        "models": {
            "minimax-m2.1": {
                "name": "MiniMax-M2.1",
                "api_key_env": "MINIMAX_API_KEY",
                "endpoint": "https://api.minimaxi.com/anthropic/v1/messages",
                "temperature": 0.3,
                "max_tokens": 4096,
                "thinking": True,
            }
        },
    },
    "gemini": {
        "name": "Gemini",
        "models": {
            "gemini-3-flash-preview": {
                "name": "Gemini 3.0 Flash (Thinking)",
                "api_key_env": "GOOGLE_API_KEY",
                "temperature": 0.3,
                "max_tokens": 4096,
                "thinking": True,
            }
        },
    },
}


@app.route("/")
def index():
    """主页"""
    return render_template("index.html")


@app.route("/api/download", methods=["POST"])
def download_data():
    """下载比赛数据API"""
    data = request.get_json()

    if not data or "match_id" not in data:
        return jsonify({"success": False, "error": "缺少比赛编号"})

    match_id = data["match_id"].strip()

    if not match_id:
        return jsonify({"success": False, "error": "比赛编号不能为空"})

    try:
        result = downloader.download_both(match_id)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/download/analysis", methods=["POST"])
def download_analysis():
    """只下载分析数据"""
    data = request.get_json()

    if not data or "match_id" not in data:
        return jsonify({"success": False, "error": "缺少比赛编号"})

    match_id = data["match_id"].strip()

    try:
        result = downloader.download_analysis_data(match_id)

        if result.get("status") == "success":
            import subprocess

            subprocess.run(["python", "parsers/analysis_parser.py"], check=True)

        return jsonify({"success": result.get("status") == "success", "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/download/odds", methods=["POST"])
def download_odds():
    """下载赔率数据"""
    data = request.get_json()

    if not data or "match_id" not in data:
        return jsonify({"success": False, "error": "缺少比赛编号"})

    match_id = data["match_id"].strip()
    odds_type = data.get("odds_type", "handicap")
    bookmaker = data.get("bookmaker")

    if not match_id:
        return jsonify({"success": False, "error": "比赛编号不能为空"})

    try:
        ot = OddsType(odds_type)
        bm = None
        if bookmaker:
            bm = Bookmaker(bookmaker)

        result = downloader.download_odds_data(match_id, odds_type=ot, bookmaker=bm)
        return jsonify({"success": result.get("status") == "success", "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/download/odds/handicap", methods=["POST"])
def download_handicap():
    """下载亚盘所有庄家赔率"""
    data = request.get_json()

    if not data or "match_id" not in data:
        return jsonify({"success": False, "error": "缺少比赛编号"})

    match_id = data["match_id"].strip()

    try:
        result = downloader.download_all_handicap(match_id)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/download/odds/handicap/<bookmaker>", methods=["POST"])
def download_handicap_bookmaker(bookmaker):
    """下载亚盘指定庄家赔率"""
    data = request.get_json()

    if not data or "match_id" not in data:
        return jsonify({"success": False, "error": "缺少比赛编号"})

    match_id = data["match_id"].strip()

    try:
        bm = Bookmaker(bookmaker)
        result = downloader.download_odds_data(
            match_id, odds_type=OddsType.HANDICAP, bookmaker=bm
        )
        return jsonify({"success": result.get("status") == "success", "data": result})
    except ValueError:
        return jsonify({"success": False, "error": f"未知的庄家: {bookmaker}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/download/odds/odds", methods=["POST"])
def download_odds_all():
    """下载欧赔所有庄家赔率 (威廉/bet365/易胜博/betfair)"""
    data = request.get_json()

    if not data or "match_id" not in data:
        return jsonify({"success": False, "error": "缺少比赛编号"})

    match_id = data["match_id"].strip()

    try:
        result = downloader.download_all_odds(match_id)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/download/odds/overunder", methods=["POST"])
def download_overunder_all():
    """下载大小球所有庄家赔率"""
    data = request.get_json()

    if not data or "match_id" not in data:
        return jsonify({"success": False, "error": "缺少比赛编号"})

    match_id = data["match_id"].strip()

    try:
        result = downloader.download_all_overunder(match_id)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/download/odds/all", methods=["POST"])
def download_all_odds():
    """下载所有类型赔率数据"""
    data = request.get_json()

    if not data or "match_id" not in data:
        return jsonify({"success": False, "error": "缺少比赛编号"})

    match_id = data["match_id"].strip()
    include_handicap = data.get("include_handicap", True)
    include_odds = data.get("include_odds", True)
    include_overunder = data.get("include_overunder", True)

    try:
        result = downloader.download_all_odds_data(
            match_id,
            include_handicap=include_handicap,
            include_odds=include_odds,
            include_overunder=include_overunder,
        )
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/files")
def list_files():
    """获取已下载文件列表"""
    files = downloader.get_downloaded_files()
    return jsonify({"success": True, "data": files})


@app.route("/api/files/analysis/<filename>")
def view_analysis_file(filename):
    """查看分析文件内容"""
    return send_from_directory("./data/analysis", filename)


@app.route("/api/files/odds/<filename>")
def view_odds_file(filename):
    """查看赔率文件内容"""
    return send_from_directory("./data/odds", filename)


@app.route("/api/files/odds/handicap/<filename>")
def view_handicap_file(filename):
    """查看亚盘赔率文件内容"""
    return send_from_directory("./data/odds/handicap", filename)


@app.route("/api/files/odds/odds/<filename>")
def view_odds_odds_file(filename):
    """查看欧赔文件内容"""
    return send_from_directory("./data/odds/odds", filename)


@app.route("/api/files/odds/overunder/<filename>")
def view_overunder_file(filename):
    """查看大小球赔率文件内容"""
    return send_from_directory("./data/odds/overunder", filename)


@app.route("/api/check/<match_id>")
def check_downloaded(match_id):
    """检查比赛数据是否已下载"""
    files = downloader.get_downloaded_files()

    analysis_files = [f for f in files["analysis"] if f.startswith(match_id + "_")]
    handicap_files = [f for f in files["handicap"] if f.startswith(match_id + "_")]
    odds_files = [f for f in files["odds"] if f.startswith(match_id + "_")]
    overunder_files = [f for f in files["overunder"] if f.startswith(match_id + "_")]

    return jsonify(
        {
            "success": True,
            "data": {
                "match_id": match_id,
                "has_analysis": len(analysis_files) > 0,
                "has_handicap": len(handicap_files) > 0,
                "has_odds": len(odds_files) > 0,
                "has_overunder": len(overunder_files) > 0,
                "analysis_files": analysis_files,
                "handicap_files": handicap_files,
                "odds_files": odds_files,
                "overunder_files": overunder_files,
            },
        }
    )


@app.route("/api/delete/<match_id>", methods=["POST"])
def delete_downloaded(match_id):
    """删除指定比赛的已下载数据"""
    try:
        files = downloader.get_downloaded_files()
        deleted = []

        for f in files["analysis"]:
            if f.startswith(match_id + "_"):
                path = f"./data/analysis/{f}"
                if os.path.exists(path):
                    os.remove(path)
                    deleted.append(f)

        for f in files["handicap"]:
            if f.startswith(match_id + "_"):
                path = f"./data/odds/handicap/{f}"
                if os.path.exists(path):
                    os.remove(path)
                    deleted.append(f)

        for f in files["odds"]:
            if f.startswith(match_id + "_"):
                path = f"./data/odds/odds/{f}"
                if os.path.exists(path):
                    os.remove(path)
                    deleted.append(f)

        for f in files["overunder"]:
            if f.startswith(match_id + "_"):
                path = f"./data/odds/overunder/{f}"
                if os.path.exists(path):
                    os.remove(path)
                    deleted.append(f)

        return jsonify(
            {"success": True, "data": {"deleted_files": deleted, "count": len(deleted)}}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/analysis/list")
def list_analysis_data():
    """获取已分析的数据列表"""
    try:
        basic_data_path = "./data/basic_data.json"
        if os.path.exists(basic_data_path):
            with open(basic_data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify({"success": True, "data": data})
        return jsonify({"success": True, "data": []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/analysis/<match_id>")
def get_analysis_data(match_id):
    """获取指定比赛的详细分析数据"""
    try:
        basic_data_path = "./data/basic_data.json"
        if os.path.exists(basic_data_path):
            with open(basic_data_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for match in data:
                if match["match_info"]["match_id"] == match_id:
                    return jsonify({"success": True, "data": match})

        return jsonify({"success": False, "error": "未找到该比赛的分析数据"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/analysis/<match_id>", methods=["DELETE"])
def delete_analysis_data(match_id):
    """删除指定比赛的分析数据"""
    try:
        basic_data_path = "./data/basic_data.json"
        deleted_files = []

        if os.path.exists(basic_data_path):
            with open(basic_data_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            original_len = len(data)
            data = [
                match for match in data if match["match_info"]["match_id"] != match_id
            ]

            if len(data) < original_len:
                with open(basic_data_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                for filename in os.listdir("./data/analysis"):
                    if filename.startswith(match_id + "_"):
                        path = f"./data/analysis/{filename}"
                        if os.path.exists(path):
                            os.remove(path)
                            deleted_files.append(filename)

                for filename in os.listdir("./data/odds/handicap"):
                    if filename.startswith(match_id + "_"):
                        path = f"./data/odds/handicap/{filename}"
                        if os.path.exists(path):
                            os.remove(path)
                            deleted_files.append(filename)

                for filename in os.listdir("./data/odds/odds"):
                    if filename.startswith(match_id + "_"):
                        path = f"./data/odds/odds/{filename}"
                        if os.path.exists(path):
                            os.remove(path)
                            deleted_files.append(filename)

                for filename in os.listdir("./data/odds/overunder"):
                    if filename.startswith(match_id + "_"):
                        path = f"./data/odds/overunder/{filename}"
                        if os.path.exists(path):
                            os.remove(path)
                            deleted_files.append(filename)

                return jsonify(
                    {
                        "success": True,
                        "data": {
                            "deleted_match_id": match_id,
                            "count": original_len - len(data),
                            "deleted_files": deleted_files,
                        },
                    }
                )
            else:
                return jsonify({"success": False, "error": "未找到该比赛的分析数据"})
        else:
            return jsonify({"success": False, "error": "分析数据文件不存在"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/prompt/generate", methods=["POST"])
def generate_prompt():
    """生成博弈论分析Prompt"""
    try:
        from prompts.prompt_generator import GameTheoryPromptGenerator, PromptConfig

        data = request.get_json()
        match_id = data.get("match_id")
        bookmaker = data.get("bookmaker", "all")
        use_all = data.get("use_all_bookmakers", True)
        include_h2h = data.get("include_h2h", True)
        include_league_table = data.get("include_league_table", True)

        if not match_id:
            return jsonify({"success": False, "error": "缺少比赛编号"})

        config = PromptConfig(
            include_h2h=include_h2h,
            include_league_table=include_league_table,
            use_all_bookmakers=use_all,
            primary_bookmaker=bookmaker if bookmaker != "all" else "macau",
        )

        generator = GameTheoryPromptGenerator("./data")
        prompt = generator.generate(match_id, config)

        if "No basic data found" in prompt:
            return jsonify(
                {
                    "success": False,
                    "error": "未找到该比赛的基本面数据，请先下载分析数据",
                }
            )

        source_type = "all_bookmakers" if use_all else bookmaker
        output_path = f"prompts/{match_id}_{source_type}_prompt.txt"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(prompt)

        return jsonify(
            {"success": True, "data": {"prompt": prompt, "saved_to": output_path}}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/ai/analyze", methods=["POST"])
def ai_analyze():
    """调用AI进行博弈论分析"""
    try:
        import httpx

        data = request.get_json()
        prompt = data.get("prompt")
        provider = data.get("provider", "deepseek")
        model = data.get("model", "deepseek-chat")

        if not prompt:
            return jsonify({"success": False, "error": "缺少分析内容"})

        if provider not in AI_PROVIDERS:
            return jsonify({"success": False, "error": f"不支持的AI提供商: {provider}"})

        provider_config = AI_PROVIDERS[provider]
        if model not in provider_config["models"]:
            return jsonify({"success": False, "error": f"不支持的模型: {model}"})

        model_config = provider_config["models"][model]
        api_key = os.environ.get(model_config["api_key_env"])

        if not api_key:
            return jsonify(
                {
                    "success": False,
                    "error": f"未配置{model_config['api_key_env']}环境变量",
                }
            )

        system_prompt = "你是一位精通博弈论的足彩分析专家，请根据提供的比赛数据和赔率信息进行专业的博弈论分析。分析要逻辑清晰，有理有据。"

        client = httpx.Client(timeout=300.0)

        if provider == "minimax":
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

            if response.status_code != 200:
                return jsonify(
                    {
                        "success": False,
                        "error": f"MiniMax API错误 (状态码 {response.status_code})",
                    }
                )

            result = response.json()

            if "content" in result:
                ai_response = ""
                for block in result["content"]:
                    if block.get("type") == "text":
                        ai_response += block.get("text", "")
                    elif block.get("type") == "thinking":
                        ai_response += (
                            f"\n[思考过程]\n{block.get('thinking', '')}\n[/思考过程]\n"
                        )
                return jsonify({"success": True, "data": {"response": ai_response}})
            else:
                return jsonify(
                    {
                        "success": False,
                        "error": "AI返回格式未知",
                    }
                )

        elif provider == "gemini":
            from google import genai

            client_gemini = genai.Client(api_key=api_key)

            full_content = f"{system_prompt}\n\n{prompt}"

            response = client_gemini.models.generate_content(
                model=model,
                contents=full_content,
                config={
                    "temperature": model_config["temperature"],
                    "max_output_tokens": model_config["max_tokens"],
                    "thinking_config": {"type": "thinking"}
                    if model_config.get("thinking")
                    else None,
                },
            )

            if response.text:
                return jsonify({"success": True, "data": {"response": response.text}})
            else:
                return jsonify(
                    {
                        "success": False,
                        "error": "AI调用失败，未返回内容",
                    }
                )

        else:
            response = client.post(
                model_config["endpoint"],
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": model_config["temperature"],
                    "max_tokens": model_config["max_tokens"],
                },
                timeout=300.0,
            )

            result = response.json()

            if "choices" in result:
                ai_response = result["choices"][0]["message"]["content"]
                return jsonify({"success": True, "data": {"response": ai_response}})
            else:
                return jsonify(
                    {
                        "success": False,
                        "error": result.get("error", {}).get("message", "AI调用失败"),
                    }
                )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/ai/providers", methods=["GET"])
def get_ai_providers():
    """获取支持的AI提供商列表"""
    try:
        providers = []
        for provider_id, provider_config in AI_PROVIDERS.items():
            models = []
            for model_id, model_config in provider_config["models"].items():
                models.append(
                    {
                        "id": model_id,
                        "name": model_config["name"],
                    }
                )
            providers.append(
                {
                    "id": provider_id,
                    "name": provider_config["name"],
                    "models": models,
                }
            )
        return jsonify({"success": True, "data": providers})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/odds/<match_id>")
def get_odds_data(match_id):
    """获取比赛的赔率数据（已过滤滚球数据）"""
    try:
        bookmaker_filter = request.args.get("bookmaker")

        handicap_path = Path("./data/odds/handicap")
        odds_path = Path("./data/odds/odds")

        handicap_files = list(handicap_path.glob(f"{match_id}_*_*.html"))
        odds_files = list(odds_path.glob(f"{match_id}_*_*.html"))

        from bs4 import BeautifulSoup
        import re

        def extract_float(text):
            match = re.search(r"[\d.]+", text)
            return float(match.group()) if match else None

        handicap_data = {}
        odds_data = {}

        for f in handicap_files:
            name = f.stem
            parts = name.split("_")
            if len(parts) < 2:
                continue
            bookmaker = parts[1]

            if (
                bookmaker_filter
                and bookmaker != "all"
                and bookmaker != bookmaker_filter
            ):
                continue

            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                html = fp.read()

            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table", attrs={"cellspacing": "1"})
            if not table:
                continue

            odds_list = []
            rows = table.find_all("tr", align="center")
            for row in rows[1:]:
                cols = row.find_all("td")
                if len(cols) < 7:
                    continue

                status = cols[6].get_text(strip=True)
                if status != "即":
                    continue

                home_odds = extract_float(cols[2].get_text(strip=True))
                handicap = cols[3].get_text(strip=True)
                away_odds = extract_float(cols[4].get_text(strip=True))
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

            if odds_list:
                handicap_data[bookmaker] = {
                    "bookmaker": bookmaker,
                    "name": {
                        "macau": "澳门",
                        "bet365": "Bet365",
                        "easybet": "易胜博",
                        "betfair": "Betfair",
                        "william": "威廉希尔",
                    }.get(bookmaker, bookmaker),
                    "odds": odds_list,
                }

        for f in odds_files:
            name = f.stem
            parts = name.split("_")
            if len(parts) < 2:
                continue
            bookmaker = parts[1]

            if (
                bookmaker_filter
                and bookmaker != "all"
                and bookmaker != bookmaker_filter
            ):
                continue

            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                html = fp.read()

            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table", width="860")
            if not table:
                continue

            odds_list = []
            rows = table.find_all("tr", align="center")
            for row in rows[1:]:
                cols = row.find_all("td")
                if len(cols) < 11:
                    continue

                home_odds = extract_float(cols[0].get_text(strip=True))
                draw_odds = extract_float(cols[1].get_text(strip=True))
                away_odds = extract_float(cols[2].get_text(strip=True))
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

            if odds_list:
                odds_data[bookmaker] = {
                    "bookmaker": bookmaker,
                    "name": {
                        "macau": "澳门",
                        "bet365": "Bet365",
                        "easybet": "易胜博",
                        "betfair": "Betfair",
                        "william": "威廉希尔",
                    }.get(bookmaker, bookmaker),
                    "odds": odds_list,
                }

        return jsonify(
            {"success": True, "data": {"handicap": handicap_data, "odds": odds_data}}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    print("=" * 60)
    print("⚽ 足球比赛赔率分析系统")
    print("=" * 60)
    print("系统启动中...")
    print("访问 http://localhost:8080 使用系统")
    print("=" * 60)

    app.run(debug=True, host="0.0.0.0", port=8080)
