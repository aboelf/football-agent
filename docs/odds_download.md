# 赔率下载功能说明

## 概述

赔率下载功能已重构，支持下载三种类型的赔率数据：
- **亚盘 (Handicap)** - 让球/受让
- **欧赔 (Odds)** - 胜平负概率
- **大小球 (OverUnder)** - 总进球数

## 赔率类型与URL结构

### 亚盘 (Handicap)
- 基础URL: `https://vip.titan007.com/changeDetail/handicap.aspx`
- 参数: `id={match_id}&companyID={company_id}&l=0`
- 庄家:
  - 澳门: companyID=1
  - bet365: companyID=8
  - 易胜博: companyID=12

### 欧赔 (Odds)
- 基础URL: `https://1x2.titan007.com/OddsHistory.aspx`
- 参数: `sid={match_id}&cid={company_id}`
- 庄家:
  - 威廉: cid=115
  - bet365: cid=281
  - 易胜博: cid=90
  - betfair: cid=2

### 大小球 (OverUnder)
- 基础URL: `https://vip.titan007.com/changeDetail/overunder.aspx`
- 参数: `id={match_id}&companyID={company_id}&l=0`
- 庄家:
  - 澳门: companyID=1
  - bet365: companyID=8
  - 易胜博: companyID=12

## 数据目录结构

```
data/
├── analysis/           # 分析数据
└── odds/
    ├── handicap/      # 亚盘赔率
    │   ├── {match_id}_{bookmaker}_{timestamp}.html
    │   └── {match_id}_{bookmaker}_{timestamp}.json
    ├── odds/          # 欧赔
    │   ├── {match_id}_{bookmaker}_{timestamp}.html
    │   └── {match_id}_{bookmaker}_{timestamp}.json
    └── overunder/     # 大小球
        ├── {match_id}_{bookmaker}_{timestamp}.html
        └── {match_id}_{bookmaker}_{timestamp}.json
```

## API 接口

### 1. 下载亚盘所有庄家
```bash
POST /api/download/odds/handicap
{
  "match_id": "2789338"
}
```

### 2. 下载亚盘指定庄家
```bash
POST /api/download/odds/handicap/<bookmaker>
# bookmaker: macau, bet365, easybet
{
  "match_id": "2789338"
}
```

### 3. 下载欧赔所有庄家
```bash
POST /api/download/odds/odds
{
  "match_id": "2789338"
}
```

### 4. 下载大小球所有庄家
```bash
POST /api/download/odds/overunder
{
  "match_id": "2789338"
}
```

### 5. 下载单类型赔率
```bash
POST /api/download/odds
{
  "match_id": "2789338",
  "odds_type": "handicap|odds|overunder",
  "bookmaker": "macau|bet365|easybet|william|betfair"  // 可选
}
```

### 6. 下载所有赔率
```bash
POST /api/download/odds/all
{
  "match_id": "2789338",
  "include_handicap": true,
  "include_odds": true,
  "include_overunder": true
}
```

### 7. 检查已下载文件
```bash
GET /api/check/{match_id}
```

## 使用示例

```python
from downloads.downloader import DataDownloader, OddsType, Bookmaker

downloader = DataDownloader()

# 下载亚盘所有庄家 (澳门/bet365/易胜博)
result = downloader.download_all_handicap("2789338")

# 下载欧赔所有庄家 (威廉/bet365/易胜博/betfair)
result = downloader.download_all_odds("2789338")

# 下载大小球所有庄家 (澳门/bet365/易胜博)
result = downloader.download_all_overunder("2789338")

# 下载所有赔率
result = downloader.download_all_odds_data("2789338")

# 下载指定庄家
result = downloader.download_odds_data(
    "2789338",
    odds_type=OddsType.ODDS,
    bookmaker=Bookmaker.WILLIAM
)
```

## 返回格式示例

```json
{
  "status": "success",
  "results": [
    {
      "match_id": "2789338",
      "odds_type": "odds",
      "bookmaker": "william",
      "bookmaker_name": "威廉",
      "company_id": 115,
      "url": "https://1x2.titan007.com/OddsHistory.aspx?sid=2789338&cid=115",
      "download_time": "20260111_120000",
      "raw_file": "./data/odds/odds/2789338_william_20260111_120000.html",
      "status": "success",
      "content_length": 12345,
      "use_browser": true
    }
  ],
  "total": 4,
  "success_count": 4
}
```

## 庄家配置表

| 庄家 | code | 亚盘companyID | 欧赔cid |
|------|------|---------------|---------|
| 澳门 | macau | 1 | - |
| bet365 | bet365 | 8 | 281 |
| 易胜博 | easybet | 12 | 90 |
| 威廉 | william | - | 115 |
| Betfair | betfair | - | 2 |

## 欧赔数据获取流程

欧赔需要从oddslist页面动态获取庄家的`id`参数：

1. 访问 `https://1x2.titan007.com/oddslist/{match_id}.htm`
2. 页面加载JS文件 `https://1x2d.titan007.com/{match_id}.js`
3. 解析JS中的`game`数组获取庄家数据
4. 构建完整URL: `https://1x2.titan007.com/OddsHistory.aspx?id={id}&sid={match_id}&cid={company_id}`

```python
# 示例：获取欧赔庄家信息
downloader = DataDownloader()
company_ids = downloader.get_odds_company_ids("2591272")
# 返回格式: {115: {"id": "xxx", "name": "威廉", "initial_odds": "x/x/x"}, ...}
```

## 文件命名规则

| 赔率类型 | 文件路径 | 命名格式 |
|----------|----------|----------|
| 亚盘 | `data/odds/handicap/` | `{match_id}_{bookmaker}_{timestamp}.html` |
| 欧赔 | `data/odds/odds/` | `{match_id}_{bookmaker}_{timestamp}.html` |
| 大小球 | `data/odds/overunder/` | `{match_id}_{bookmaker}_{timestamp}.html` |
