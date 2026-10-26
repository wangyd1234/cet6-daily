# -*- coding: utf-8 -*-
"""推送模块：Server酱 / PushPlus / 企业微信群机器人。纯标准库，无第三方依赖。"""
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "cet6-daily/1.0 (+local script)"


def _deep_merge(base: dict, extra: dict) -> dict:
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def load_config() -> dict:
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    local = ROOT / "config.local.json"
    if local.exists():
        _deep_merge(cfg, json.loads(local.read_text(encoding="utf-8")))
    # 环境变量优先（云端 GitHub Actions 用 Secrets 注入）
    env_key = os.environ.get("SCT_SENDKEY") or os.environ.get("SERVERCHAN_SENDKEY")
    if env_key:
        cfg.setdefault("serverchan", {})["sendkey"] = env_key.strip()
    env_pp = os.environ.get("PUSHPLUS_TOKEN")
    if env_pp:
        cfg.setdefault("pushplus", {})["token"] = env_pp.strip()
    env_wc = os.environ.get("WECOM_WEBHOOK")
    if env_wc:
        cfg.setdefault("wecom", {})["url"] = env_wc.strip()
    return cfg


def _post(url: str, data: dict, timeout: int = 25, as_json: bool = False) -> dict:
    if as_json:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        ctype = "application/json; charset=utf-8"
    else:
        body = urllib.parse.urlencode(data).encode("utf-8")
        ctype = "application/x-www-form-urlencoded; charset=utf-8"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": ctype, "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", "replace")
    try:
        return json.loads(raw)
    except Exception:
        return {"_raw": raw}


def send_serverchan(title: str, desp: str, key: str) -> tuple:
    if not key:
        return False, "未配置 serverchan.sendkey"
    if len(title) > 60:
        title = title[:60]
    try:
        r = _post(f"https://sctapi.ftqq.com/{key}.send", {"title": title, "desp": desp})
    except Exception as e:
        return False, f"网络错误: {e}"
    code = r.get("code")
    if code == 0:
        return True, r.get("data", {}).get("pushid", "ok")
    return False, str(r)


def send_pushplus(title: str, desp: str, token: str) -> tuple:
    if not token:
        return False, "未配置 pushplus.token"
    try:
        r = _post("https://www.pushplus.plus/send",
                  {"token": token, "title": title, "content": desp, "template": "markdown"})
    except Exception as e:
        return False, f"网络错误: {e}"
    if r.get("code") == 200:
        return True, str(r.get("data", ""))
    return False, str(r)


def send_wecom(title: str, desp: str, url: str) -> tuple:
    if not url:
        return False, "未配置 wecom.url"
    try:
        r = _post(url, {"msgtype": "markdown",
                        "markdown": {"content": f"**{title}**\n{desp}"}}, as_json=True)
    except Exception as e:
        return False, f"网络错误: {e}"
    if r.get("errcode") == 0:
        return True, "ok"
    return False, str(r)


def send(title: str, desp: str, cfg: dict | None = None) -> list:
    """按配置顺序推送，返回 [(channel, ok, detail), ...]"""
    cfg = cfg or load_config()
    results = []
    sc = cfg.get("serverchan") or {}
    if sc.get("enabled"):
        results.append(("serverchan", *send_serverchan(title, desp, sc.get("sendkey", ""))))
    pp = cfg.get("pushplus") or {}
    if pp.get("enabled"):
        results.append(("pushplus", *send_pushplus(title, desp, pp.get("token", ""))))
    wc = cfg.get("wecom") or {}
    if wc.get("enabled"):
        results.append(("wecom", *send_wecom(title, desp, wc.get("url", ""))))
    if not results:
        results.append(("none", False, "没有任何启用的推送通道"))
    return results


if __name__ == "__main__":
    if "--test" in sys.argv:
        cfg = load_config()
        msg = (
            "## 通道测试成功\n\n"
            "如果你在微信里看到这条消息，说明推送链路已打通。\n\n"
            "> 正式内容每天 09:00 自动发送：30 个六级考纲单词（音标 / 释义 / 搭配 / 例句）+ 1 条作文好句。"
        )
        for ch, ok, detail in send("【测试】六级每日词汇推送已配置", msg, cfg):
            print(("OK  " if ok else "FAIL"), ch, detail)
    else:
        print("用法: python push.py --test")
