#!/usr/bin/env bash
# ============================================================
# 引路人 Lumora — VPS 一鍵部署腳本
# 在 VPS 上執行：bash deploy-vps.sh
# ============================================================
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="lumora"
SERVICE_DEST="/etc/systemd/system/${SERVICE_NAME}.service"
PORT="${LUMORA_PORT:-8000}"
WORKERS="${LUMORA_WORKERS:-2}"

# 偵測 Python / uvicorn 路徑
PYTHON_BIN="$(which python3 || which python)"
UVICORN_BIN="$(which uvicorn 2>/dev/null || echo "${PYTHON_BIN%/*}/uvicorn")"

echo "========================================"
echo "  引路人 Lumora — VPS 部署"
echo "  目錄：$REPO_DIR"
echo "  埠號：$PORT   Workers：$WORKERS"
echo "========================================"

# ── 1. 拉最新代碼 ──
echo ""
echo "▶ [1/5] 拉取最新代碼..."
git -C "$REPO_DIR" fetch --all
git -C "$REPO_DIR" reset --hard origin/"$(git -C "$REPO_DIR" branch --show-current)"

# ── 2. 安裝依賴 ──
echo ""
echo "▶ [2/5] 安裝 / 更新 Python 依賴..."
pip install -q -r "$REPO_DIR/requirements.txt"

# ── 3. 確認 .env 存在 ──
echo ""
echo "▶ [3/5] 檢查 .env..."
if [ ! -f "$REPO_DIR/.env" ]; then
  echo "⚠️  找不到 $REPO_DIR/.env，請確認 .env 已建立且含有 OPENAI_API_KEY 等設定。"
  echo "   可參考：cp $REPO_DIR/.env.example $REPO_DIR/.env  再填入真實 key"
  exit 1
fi
echo "   ✓ .env 存在"

# ── 4. 安裝 / 更新 systemd 服務 ──
echo ""
echo "▶ [4/5] 設定 systemd 服務（開機自啟 + 自動重啟）..."

cat > "$SERVICE_DEST" <<EOF
[Unit]
Description=引路人 Lumora — FastAPI Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${REPO_DIR}
EnvironmentFile=${REPO_DIR}/.env
ExecStart=${UVICORN_BIN} yinluren.main:app --host 0.0.0.0 --port ${PORT} --workers ${WORKERS}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=lumora

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
echo "   ✓ systemd 服務已更新並設為開機啟動"

# ── 5. 重啟並驗證 ──
echo ""
echo "▶ [5/5] 重啟 Lumora 後端並驗證..."
systemctl restart "$SERVICE_NAME"
sleep 3

if curl -sf "http://localhost:${PORT}/api/v1/ping" > /dev/null 2>&1; then
  echo ""
  echo "✅ 部署成功！後端已在背景持久運行。"
  echo ""
  echo "  服務狀態：  systemctl status lumora"
  echo "  即時 log：  journalctl -u lumora -f"
  echo "  重啟：      systemctl restart lumora"
  echo "  停止：      systemctl stop lumora"
else
  echo ""
  echo "❌ 後端啟動後 ping 失敗，請查看 log："
  journalctl -u "$SERVICE_NAME" -n 40 --no-pager
  exit 1
fi
