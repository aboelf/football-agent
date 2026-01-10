"""
足球比赛赔率分析系统 - Flask 主应用
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from downloads.downloader import DataDownloader
import os
import json

app = Flask(__name__, template_folder="templates", static_folder="static")

# 初始化下载器
downloader = DataDownloader(base_path="./data")


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
    """只下载赔率数据"""
    data = request.get_json()

    if not data or "match_id" not in data:
        return jsonify({"success": False, "error": "缺少比赛编号"})

    match_id = data["match_id"].strip()

    try:
        result = downloader.download_odds_data(match_id)
        return jsonify({"success": result.get("status") == "success", "data": result})
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


@app.route("/api/check/<match_id>")
def check_downloaded(match_id):
    """检查比赛数据是否已下载"""
    files = downloader.get_downloaded_files()

    analysis_files = [f for f in files["analysis"] if f.startswith(match_id + "_")]
    odds_files = [f for f in files["odds"] if f.startswith(match_id + "_")]

    return jsonify(
        {
            "success": True,
            "data": {
                "match_id": match_id,
                "has_analysis": len(analysis_files) > 0,
                "has_odds": len(odds_files) > 0,
                "analysis_files": analysis_files,
                "odds_files": odds_files,
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

        for f in files["odds"]:
            if f.startswith(match_id + "_"):
                path = f"./data/odds/{f}"
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

                for filename in os.listdir("./data/odds"):
                    if filename.startswith(match_id + "_"):
                        path = f"./data/odds/{filename}"
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


@app.route("/api/stats")
def get_stats():
    """获取统计信息"""
    files = downloader.get_downloaded_files()
    return jsonify(
        {
            "success": True,
            "data": {
                "analysis_count": len(files["analysis"]),
                "odds_count": len(files["odds"]),
                "total_count": len(files["analysis"]) + len(files["odds"]),
            },
        }
    )


if __name__ == "__main__":
    print("=" * 60)
    print("⚽ 足球比赛赔率分析系统")
    print("=" * 60)
    print("系统启动中...")
    print("访问 http://localhost:8080 使用系统")
    print("=" * 60)

    app.run(debug=True, host="0.0.0.0", port=8080)
