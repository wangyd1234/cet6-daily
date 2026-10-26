# 每日 09:00 六级词汇（微信推送）

## 一句话说明

每天北京时间 **09:00**，把 **30 个六级考纲单词**（英/美音标 + 词性释义 + 2 个搭配 + 1 个例句带译文 + 1 句记忆提示）和 **1 条作文好句**（原句 + 译文 + 用法 + 适用话题）推送到你的**微信**。

词库是六级考纲 **2345 词**，按 **30 词/天** 排成 **79 天**（第 79 天为复习日：5 个新词 + 25 个回顾词），学完自动进入第二轮循环。

## 目录结构

```
├─ .github/workflows/daily.yml   # 云端定时（GitHub Actions）★ 不开电脑也能推
├─ config.json                   # 主配置（推送时间、起始日期、通道开关）
├─ config.local.json             # 私密配置：Server酱 SendKey（已 gitignore，不会上传）
├─ data/
│  ├─ words.json                 # 清洗后的考纲词库（2345 词）
│  ├─ days/day_001..079.json     # 每天的词包（学习顺序）
│  ├─ authored/day_001..079.json # 每天的词卡内容（搭配/例句/提示）
│  ├─ essays.json                # 78 条作文好句
│  └─ content.json               # 上面数据合并后的运行时文件（推送时只读它）
├─ scripts/
│  ├─ daily.py                   # 主程序：选词 → 渲染 → 归档 → 推送
│  ├─ push.py                    # 推送通道（Server酱 / PushPlus / 企业微信）
│  ├─ build_words.py             # 词库清洗
│  └─ build_content.py           # 内容合并 + 质量校验
└─ out/                          # 每天渲染出的 Markdown 归档
```

## 本地怎么用

- 双击 **`立即推送一次.bat`** → 立刻按今天的日期推一条（也可用于补发）。
- 只预览不发送：

```bat
python scripts\daily.py --dry-run
python scripts\daily.py --day 12 --dry-run      :: 预览第 12 天
python scripts\daily.py --day 12                :: 补发第 12 天
python scripts\daily.py --date 2026-11-01       :: 按指定日期推算该推第几天
```

## 云端（不开电脑也能推）配置步骤

1. 在 GitHub 新建一个仓库（Private 也可以），把整个文件夹上传（网页 Upload files 拖文件夹即可）。
2. 仓库 → **Settings → Secrets and variables → Actions → New repository secret**
   - Name：`SCT_SENDKEY`
   - Secret：你的 Server酱 SendKey（`SCT` 开头）
3. 仓库 → **Actions** 标签页 → 若提示工作流被禁用，点 **I understand my workflows, go ahead and enable them**。
4. 手动验证一次：Actions → 六级词汇每日推送 → **Run workflow** → Run。

之后每天 UTC 01:00（北京时间 09:00）自动运行。GitHub 免费额度的定时任务通常有 5~20 分钟排队延迟，属正常现象。

> 定时任务在仓库连续 60 天没有任何活动时会被自动停用。本项目每次运行都会把当天归档提交回仓库，从而保持活跃；若某次推送失败导致长期无提交，去 Actions 页手动 Run 一次即可恢复。

## 想改点什么

| 想改 | 改哪里 |
|---|---|
| 开学日期 / 第 1 天 | `config.json` → `start_date` |
| 推送时间 | `.github/workflows/daily.yml` 的 `cron`（UTC；北京时间 09:00 = `0 1 * * *`） |
| 每次推送的词数 | 改 `scripts/build_words.py` 的 `PER_DAY` 后重跑 `build_words.py`（会重排词包） |
| 换推送通道 | `config.json` 里把 `pushplus` / `wecom` 的 `enabled` 设为 true 并填 token |
| 作文好句 | 直接编辑 `data/essays.json`，按天循环使用 |

改完 `data/` 下的内容后，记得重跑：

```bat
python scripts\build_content.py    :: 合并 + 校验，生成 data/content.json
```

## 常见问题

- **没收到**：先在微信「方糖」服务号里看是否被折叠；Server酱 免费版每天限 5 条（本项目每天 1 条，足够）。若 Actions 显示失败，看日志里 `FAIL serverchan ...` 的原因。
- **推送时间不准**：GitHub 定时任务排队延迟，一般 5~20 分钟；想更准就把 cron 提前 10 分钟试试。
- **SendKey 泄露**：去 sct.ftqq.com 重置 SendKey，然后同时更新 `config.local.json` 与仓库 Secret。
- **词库来源**：qwerty-learner 的 CET6 词库（音标 + 释义），例句/搭配/提示为人工撰写内容，已做机器校验（词序、字段完整性、例句含目标词）。
