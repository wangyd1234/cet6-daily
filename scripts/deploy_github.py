# -*- coding: utf-8 -*-
"""一键部署到 GitHub：建私有仓库 -> 推送 -> 配置 SCT_SENDKEY 密钥 -> 触发一次试运行。

用法：
    python scripts/deploy_github.py <github_token> [--repo cet6-daily] [--no-dispatch]
"""
import base64
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GIT = ROOT / ".tools" / "PortableGit" / "bin" / "git.exe"
API = "https://api.github.com"


def api(method: str, path: str, token: str, payload=None):
    import urllib.request
    url = path if path.startswith("http") else API + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "cet6-deploy",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8")
            return r.status, (json.loads(body) if body.strip() else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw}
    except Exception as e:
        return 0, {"error": str(e)}


def sh(args, cwd=ROOT, check=True):
    p = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    print(f"  $ {' '.join(a if 'x-access-token' not in a and 'ghp_' not in a else '<redacted>' for a in args)}")
    if out.strip():
        print("   ", out.strip().replace("\n", "\n    "))
    if check and p.returncode != 0:
        raise SystemExit(f"git 失败: {args}")
    return p


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    token = sys.argv[1].strip()
    repo = "cet6-daily"
    if "--repo" in sys.argv:
        repo = sys.argv[sys.argv.index("--repo") + 1]

    st, me = api("GET", "/user", token)
    if st != 200:
        print("令牌无效:", me)
        return 1
    login = me["login"]
    print(f"账号: {login}")

    st, data = api("POST", "/user/repos", token, {
        "name": repo, "private": True, "auto_init": False,
        "description": "每天 09:00 推送 30 个六级考纲单词 + 1 条作文好句到微信",
    })
    if st == 201:
        print(f"已创建私有仓库: {data['full_name']}")
    elif st == 422:
        print(f"仓库已存在，直接使用: {login}/{repo}")
    else:
        print("创建仓库失败:", st, data)
        return 1

    # 本地提交
    if not (ROOT / ".git").exists():
        sh([str(GIT), "init", "-b", "main"])
    sh([str(GIT), "config", "user.name", login])
    sh([str(GIT), "config", "user.email", f"{login}@users.noreply.github.com"])
    sh([str(GIT), "add", "-A"])
    sh([str(GIT), "commit", "-m", "init: 六级考纲词汇每日微信推送"], check=False)
    remote = f"https://github.com/{login}/{repo}.git"
    remotes = sh([str(GIT), "remote"], check=False).stdout.split()
    sh([str(GIT), "remote", "add", "origin", remote] if "origin" not in remotes
       else [str(GIT), "remote", "set-url", "origin", remote], check=False)
    auth_url = f"https://x-access-token:{token}@github.com/{login}/{repo}.git"
    sh([str(GIT), "push", "-u", auth_url, "main"])
    sh([str(GIT), "remote", "set-url", "origin", remote], check=False)
    print(f"已推送: {remote}")

    # 配置 Actions 密钥
    try:
        from nacl import public, encoding
        st, key = api("GET", f"/repos/{login}/{repo}/actions/secrets/public-key", token)
        if st == 200:
            cfg = json.loads((ROOT / "config.local.json").read_text(encoding="utf-8"))
            sendkey = (cfg.get("serverchan") or {}).get("sendkey", "").strip()
            if sendkey:
                pk = public.PublicKey(key["key"].encode(), encoding.Base64Encoder())
                sealed = public.SealedBox(pk).encrypt(sendkey.encode())
                enc = base64.b64encode(sealed).decode()
                st2, r2 = api("PUT", f"/repos/{login}/{repo}/actions/secrets/SCT_SENDKEY", token,
                              {"encrypted_value": enc, "key_id": key["key_id"]})
                print("Actions 密钥 SCT_SENDKEY:", "已写入" if st2 in (201, 204) else f"失败 {st2} {r2}")
            else:
                print("config.local.json 里没有 sendkey，跳过密钥配置")
        else:
            print("读取仓库公钥失败:", st, key)
    except Exception as e:
        print("配置密钥异常:", e)

    if "--no-dispatch" in sys.argv:
        return 0

    # 触发一次只渲染不发送的试运行，验证云端链路
    st, r = api("POST", f"/repos/{login}/{repo}/actions/workflows/daily.yml/dispatches", token,
                {"ref": "main", "inputs": {"dry_run": "true"}})
    print("触发试运行:", "已排队" if st in (204, 201) else f"失败 {st} {r}")

    for _ in range(30):
        time.sleep(8)
        st, runs = api("GET", f"/repos/{login}/{repo}/actions/runs?per_page=1", token)
        if st == 200 and runs.get("workflow_runs"):
            run = runs["workflow_runs"][0]
            print(f"  运行状态: {run['status']} / {run.get('conclusion')}")
            if run["status"] == "completed":
                print(f"  详情: {run['html_url']}")
                print("  结果:", "成功 ✅" if run.get("conclusion") == "success" else "失败 ❌")
                break
    print(f"\n仓库地址: https://github.com/{login}/{repo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
