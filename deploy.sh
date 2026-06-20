#!/usr/bin/env bash
# 引路人 Lumora — VPS 一鍵部署 / 重啟腳本
# 用法：bash deploy.sh
# 第一次執行會安裝 systemd 服務；之後執行只更新代碼並重啟。

set -e
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="lumora"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "▶ 拉取最新代碼..."
git -C "$REPO_DIR" pull origin "$(git -C "$REPO_DIR" branch --show-current)"

echo "▶ 安裝 / 更新 Python 依賴..."
pip install -q -r "$REPO_DIR/requirements.txt"

# 安裝 systemd 服務（第一次）
if [ ! -f "$SERVICE_FILE" ]; then
  echo "▶ 首次安裝 systemd 服務..."
  # 將服務檔中的路徑替換為實際路徑
  sed "s|/root/Lumora-vps|$REPO_DIR|g" "$REPO_DIR/lumora.service" > "$SERVICE_FILE"
  systemctl daemon-reload
  systemctl enable "$SERVICE_NAME"
  echo "✓ 服務已安裝並設為開機啟動"
else
  systemctl daemon-reload
fi

echo "▶ 重啟 Lumora 後端..."
systemctl restart "$SERVICE_NAME"
sleep 2
systemctl status "$SERVICE_NAME" --no-pager -l
echo ""
echo "✓ 完成！後端已在背景持久運行，桌機關機後仍會繼續跑。"
echo "  查看即時 log：journalctl -u lumora -f"
echo "  手動停止：    systemctl stop lumora"
echo "  手動啟動：    systemctl start lumora"
