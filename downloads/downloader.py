"""
足球比赛赔率分析系统 - 数据下载模块
使用 Playwright 处理动态加载的数据
"""
import requests
from datetime import datetime
import os
import re
import json
import time


class DataDownloader:
    """数据下载器类"""

    def __init__(self, base_path="./data"):
        self.base_path = base_path
        self.session = requests.Session()

        # 请求头，模拟浏览器访问
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        self.session.headers.update(self.headers)

        # 确保数据目录存在
        os.makedirs(base_path, exist_ok=True)
        os.makedirs(f"{base_path}/analysis", exist_ok=True)
        os.makedirs(f"{base_path}/odds", exist_ok=True)

    def download_analysis_data(self, match_id, use_browser=True):
        """
        下载比赛分析数据
        URL: https://zq.titan007.com/analysis/[比赛编号]sb.htm
        use_browser: 是否使用 Playwright 浏览器获取动态内容
        """
        url = f"https://zq.titan007.com/analysis/{match_id}sb.htm"

        try:
            print(f"正在下载比赛分析数据: {url}")

            if use_browser:
                # 使用 Playwright 获取动态内容
                from playwright.sync_api import sync_playwright

                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()

                    # 访问页面
                    page.goto(url, wait_until='networkidle')

                    # 等待动态内容加载完成
                    # 尝试等待包含比分的元素出现
                    try:
                        # 等待最多 10 秒让动态内容加载
                        page.wait_for_timeout(5000)

                        # 检查是否有特定的选择器需要等待
                        # 常见的动态内容容器
                        possible_selectors = [
                            'div[id*="score"]',
                            'span[id*="score"]',
                            '.score-box',
                            '#比分',
                            '[class*="score"]'
                        ]

                        for selector in possible_selectors:
                            try:
                                page.wait_for_selector(selector, timeout=3000)
                                break
                            except:
                                continue

                    except Exception as e:
                        print(f"  等待元素超时: {e}")

                    # 获取完整页面内容（包括动态加载的）
                    html_content = page.content()

                    browser.close()

            else:
                # 使用 requests 获取静态内容
                response = self.session.get(url, timeout=30)
                response.encoding = 'utf-8'
                html_content = response.text

            if html_content:
                # 保存原始HTML
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{self.base_path}/analysis/{match_id}_{timestamp}.html"

                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                # 提取关键信息
                data = {
                    'match_id': match_id,
                    'url': url,
                    'download_time': timestamp,
                    'raw_file': filename,
                    'status': 'success',
                    'content_length': len(html_content),
                    'use_browser': use_browser
                }

                # 保存JSON元数据
                meta_file = f"{self.base_path}/analysis/{match_id}_{timestamp}.json"
                with open(meta_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print(f"✓ 分析数据下载成功: {filename}")
                return data
            else:
                print(f"✗ 下载失败，未获取到内容")
                return {'status': 'failed', 'error': 'No content retrieved'}

        except ImportError:
            print("⚠ Playwright 未安装，使用 requests 降级获取")
            return self._download_analysis_requests(match_id)
        except Exception as e:
            print(f"✗ 下载出错: {str(e)}")
            return {'status': 'failed', 'error': str(e)}

    def _download_analysis_requests(self, match_id):
        """使用 requests 降级获取分析数据"""
        url = f"https://zq.titan007.com/analysis/{match_id}sb.htm"

        try:
            response = self.session.get(url, timeout=30)
            response.encoding = 'utf-8'

            if response.status_code == 200:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{self.base_path}/analysis/{match_id}_{timestamp}.html"

                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)

                data = {
                    'match_id': match_id,
                    'url': url,
                    'download_time': timestamp,
                    'raw_file': filename,
                    'status': 'success',
                    'content_length': len(response.text),
                    'use_browser': False,
                    'warning': '使用静态请求获取，动态内容可能不完整'
                }

                meta_file = f"{self.base_path}/analysis/{match_id}_{timestamp}.json"
                with open(meta_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print(f"✓ 分析数据下载成功 (静态): {filename}")
                return data
            else:
                return {'status': 'failed', 'error': f'HTTP {response.status_code}'}

        except Exception as e:
            return {'status': 'failed', 'error': str(e)}

    def download_odds_data(self, match_id, use_browser=True):
        """
        下载赔率数据
        URL: https://vip.titan007.com/changeDetail/handicap.aspx?id=[比赛编号]&companyID=1&l=0
        """
        url = f"https://vip.titan007.com/changeDetail/handicap.aspx?id={match_id}&companyID=1&l=0"

        try:
            print(f"正在下载赔率数据: {url}")

            if use_browser:
                # 使用 Playwright 获取动态内容
                from playwright.sync_api import sync_playwright

                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()

                    # 访问页面
                    page.goto(url, wait_until='networkidle')

                    # 等待赔率数据加载
                    page.wait_for_timeout(3000)

                    # 获取完整页面内容
                    html_content = page.content()

                    browser.close()

            else:
                response = self.session.get(url, timeout=30)
                response.encoding = 'utf-8'
                html_content = response.text

            if html_content:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{self.base_path}/odds/{match_id}_{timestamp}.html"

                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                data = {
                    'match_id': match_id,
                    'url': url,
                    'download_time': timestamp,
                    'raw_file': filename,
                    'status': 'success',
                    'content_length': len(html_content),
                    'use_browser': use_browser
                }

                meta_file = f"{self.base_path}/odds/{match_id}_{timestamp}.json"
                with open(meta_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print(f"✓ 赔率数据下载成功: {filename}")
                return data
            else:
                return {'status': 'failed', 'error': 'No content retrieved'}

        except ImportError:
            print("⚠ Playwright 未安装，使用 requests 降级获取")
            return self._download_odds_requests(match_id)
        except Exception as e:
            print(f"✗ 下载出错: {str(e)}")
            return {'status': 'failed', 'error': str(e)}

    def _download_odds_requests(self, match_id):
        """使用 requests 降级获取赔率数据"""
        url = f"https://vip.titan007.com/changeDetail/handicap.aspx?id={match_id}&companyID=1&l=0"

        try:
            response = self.session.get(url, timeout=30)
            response.encoding = 'utf-8'

            if response.status_code == 200:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{self.base_path}/odds/{match_id}_{timestamp}.html"

                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)

                data = {
                    'match_id': match_id,
                    'url': url,
                    'download_time': timestamp,
                    'raw_file': filename,
                    'status': 'success',
                    'content_length': len(response.text),
                    'use_browser': False
                }

                meta_file = f"{self.base_path}/odds/{match_id}_{timestamp}.json"
                with open(meta_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print(f"✓ 赔率数据下载成功 (静态): {filename}")
                return data
            else:
                return {'status': 'failed', 'error': f'HTTP {response.status_code}'}

        except Exception as e:
            return {'status': 'failed', 'error': str(e)}

    def download_both(self, match_id, use_browser=True):
        """同时下载分析数据和赔率数据"""
        print(f"\n{'='*50}")
        print(f"开始下载比赛 {match_id} 的数据")
        print(f"{'='*50}\n")

        analysis_result = self.download_analysis_data(match_id, use_browser)
        time.sleep(1)
        odds_result = self.download_odds_data(match_id, use_browser)

        return {
            'match_id': match_id,
            'analysis': analysis_result,
            'odds': odds_result,
            'total_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_downloaded_files(self, data_type='all'):
        """获取已下载的文件列表"""
        files = {'analysis': [], 'odds': []}

        if data_type in ['all', 'analysis']:
            analysis_dir = f"{self.base_path}/analysis"
            if os.path.exists(analysis_dir):
                for f in os.listdir(analysis_dir):
                    if f.endswith('.html'):
                        files['analysis'].append(f)

        if data_type in ['all', 'odds']:
            odds_dir = f"{self.base_path}/odds"
            if os.path.exists(odds_dir):
                for f in os.listdir(odds_dir):
                    if f.endswith('.html'):
                        files['odds'].append(f)

        return files


if __name__ == "__main__":
    # 测试下载
    downloader = DataDownloader()

    test_id = input("请输入比赛编号 (直接回车跳过测试): ").strip()

    if test_id:
        result = downloader.download_both(test_id, use_browser=True)
        print("\n下载结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
