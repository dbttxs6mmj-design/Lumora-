#!/usr/bin/env bash
# 引路人 Lumora — 既有 VPS 部署腳本（user=claude / venv / 127.0.0.1）
# 用法：bash deploy-vps.sh [remote] [branch]
#   預設 remote = github，branch = 當前分支
# 跟 deploy.sh 的差異：
#   - 用本機 .venv 的 pip，不污染系統 Python
#   - 走 `github` remote（live VPS 沒有 origin）
#   - 不覆寫 /etc/systemd/system/lumora.service（live 配置跟 repo 範本不同）
#   - 健康檢查打 127.0.0.1:8000（live 服務不暴露 0.0.0.0）

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
REMOTE="${1:-github}"
BRANCH="${2:-$(git -C "$REPO_DIR" branch --show-current)}"
VENV_PIP="$REPO_DIR/.venv/bin/pip"
SERVICE_NAME="lumora"
HEALTH_URL="http://127.0.0.1:8000/"

cd "$REPO_DIR"

echo "▶ Repo:    $REPO_DIR"
echo "▶ Remote:  $REMOTE"
echo "▶ Branch:  $BRANCH"

if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
  echo "✗ remote '$REMOTE' 不存在。可用 remote：" >&2
  git remote -v >&2
  exit 1
fi

REMOTE_URL=$(git remote get-url "$REMOTE")
if [ -n "${GITHUB_TOKEN:-}" ] && [[ "$REMOTE_URL" == https://* ]]; then
  # 將 token 注入 URL 用於這次 fetch；不寫進 git config
  HOST_PATH="${REMOTE_URL#https://}"
  AUTH_URL="https://x-access-token:${GITHUB_TOKEN}@${HOST_PATH}"
  FETCH_TARGET="$AUTH_URL"
else
  FETCH_TARGET="$REMOTE"
  if [[ "$REMOTE_URL" == https://* ]]; then
    echo "  (提示：private repo 請先 export GITHUB_TOKEN=...，否則 fetch 會卡在認證)"
  fi
fi

echo "▶ 拉取最新代碼..."
git fetch "$FETCH_TARGET" "$BRANCH" 2>&1 | sed 's/ghp_[A-Za-z0-9_]*/[REDACTED]/g'
BEFORE=$(git rev-parse HEAD)
git merge --ff-only FETCH_HEAD
AFTER=$(git rev-parse HEAD)

if [ "$BEFORE" = "$AFTER" ]; then
  echo "  (已是最新：$AFTER，無需重啟)"
  echo "▶ 健康檢查 $HEALTH_URL"
  curl -s -o /dev/null -w "  HTTP %{http_code}\n" "$HEALTH_URL"
  exit 0
fi
echo "  $BEFORE → $AFTER"

if [ ! -x "$VENV_PIP" ]; then
  echo "✗ 找不到 venv pip：$VENV_PIP" >&2
  exit 1
fi

echo "▶ 更新依賴（venv pip）..."
"$VENV_PIP" install -q -r "$REPO_DIR/requirements.txt"

echo "▶ 重啟 uvicorn 服務 (需要 sudo)..."
sudo systemctl restart "$SERVICE_NAME"

# ── 重啟反向代理（nginx / caddy；whoever is active）──
_restart_proxy() {
  for PROXY in nginx caddy apache2 httpd; do
    if systemctl is-active --quiet "$PROXY" 2>/dev/null; then
      echo "▶ 重啟反向代理：$PROXY"
      sudo systemctl restart "$PROXY"
      return 0
    fi
    # 若代理存在但非 active（可能就是它沒在跑導致外部 502）
    if systemctl list-units --type=service --all 2>/dev/null | grep -q "^  $PROXY.service"; then
      echo "▶ $PROXY 存在但未 active，嘗試啟動..."
      sudo systemctl start "$PROXY" && return 0
    fi
  done
  echo "  (未偵測到 nginx/caddy/apache，跳過反向代理重啟)"
}
_restart_proxy
sleep 3

ACTIVE=$(systemctl is-active "$SERVICE_NAME")
echo "▶ lumora 服務狀態：$ACTIVE"

echo "▶ 內部健康檢查 $HEALTH_URL"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL")
echo "  HTTP $HTTP_CODE"

if [ "$ACTIVE" = "active" ] && [ "$HTTP_CODE" = "200" ]; then
  echo "✓ 部署完成 ($AFTER)"
  echo ""
  echo "若瀏覽器仍顯示錯誤，請執行："
  echo "  sudo nginx -t && sudo systemctl status nginx"
  echo "  或：sudo systemctl status caddy"
else
  echo "✗ 健康檢查失敗，查 log：" >&2
  echo "  sudo journalctl -u $SERVICE_NAME -n 30 --no-pager" >&2
  exit 1
fi
