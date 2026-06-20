# INFRA-NOTES — Lumora live VPS 實際架構

給協作的 Claude 看：以下是 `lumora.139.59.228.58.sslip.io` 這台 VPS 的真實狀況。寫部署 / 修復指令前先讀這份。

## 1. 檔案 / 進程位置

| 項目 | 值 |
|---|---|
| 專案根目錄 | `/home/claude/lumora` |
| 執行使用者 | `claude`（不是 root） |
| Python | `/home/claude/lumora/.venv/bin/python`（venv，不要用系統 pip） |
| systemd unit | `/etc/systemd/system/lumora.service` |
| Service 啟動 | `.venv/bin/uvicorn yinluren.main:app --host 127.0.0.1 --port 8000` |
| Git remote 名稱 | `github`（指向 `hpwwly-ops/Lumora-`，不是 `origin`） |
| 當前部署分支 | `feature/7-ui-fixes` |

## 2. 反向代理架構

```
[使用者瀏覽器]
   ↓ HTTPS
[Cloudflare proxy, 104.28.x.x]   ← TLS 在這裡終止
   ↓ HTTP :80
[nginx — /etc/nginx/sites-available/lumora]
   ↓ Basic Auth gate（auth_basic_user_file /etc/nginx/.lumora_htpasswd）
   ↓ proxy_pass http://127.0.0.1:8000
[uvicorn / Lumora FastAPI]
```

### 從 VPS 內 curl 看到的東西

- `curl http://127.0.0.1:8000/` → 200（uvicorn 直連，跳過 nginx）
- `curl https://lumora.139.59.228.58.sslip.io/` → 401（被 nginx Basic Auth 擋）

**401 不是壞掉，是 feature。** 真實使用者瀏覽器會被跳出登入框、輸入帳密後快取 Authorization header，後續請求就會穿過。journal 看到的 200 OK 真實流量都是這樣來的。

## 3. 部署 = 跑這支腳本

```bash
GITHUB_TOKEN=<pat> bash /home/claude/lumora/deploy-vps.sh
```

`deploy-vps.sh` 已經處理 fetch / venv pip / sudo systemctl restart / 健康檢查。**不要再叫 VPS 跑下列指令**：

| 指令 | 為什麼不行 |
|---|---|
| `bash deploy.sh` | 那是 fresh-install 範本：假設 root / `/root/Lumora-vps` / 系統 pip / `0.0.0.0` / `origin` remote，全跟這台不相容 |
| `pkill -f uvicorn` | 殺掉的是 systemd 管的進程，systemd 會 race 自動拉起，可能跟接下來的 nohup 撞 port |
| `nohup uvicorn ... &` | 跟 systemd 雙跑、競爭 port 8000、無 sudoer 也會失敗 |
| `pip install ...`（系統） | 裝錯 Python interpreter，systemd 啟動時用的是 venv 那支，新依賴看不到 |
| 把 `nginx-lumora.conf` 套用到 `/etc/nginx/sites-available/lumora` | 範本只 listen 80、無 auth_basic，套了會拆掉 Basic Auth 保護 |

## 4. 已知狀態 / 歷史伏筆

### Rate limit（commit `06de956` 後修復鏈）

`06de956` 的 security 修復裡 rate limiter 因三層 bug 連鎖從未生效。已修：

- `9b5076d` — `raise JSONResponse` 改 `raise HTTPException`（前者不是 BaseException subclass，會丟 TypeError）
- `da2ca17` — `_rate_limit_divine` wrapper 改成先 `except HTTPException: raise`（原本 `except Exception: pass` 把它也吞掉）
- `51d4bb6` — 補 `routes.py` 缺失的 `import os`（NameError 也被 except 吞掉）

burst test 確認 `200×20 → 429×4`。

教訓：寫 `except Exception: pass` 之前先想清楚會吞掉哪些「應該炸出來的東西」。最少 `logging.exception(...)` 不要靜默 swallow。

### 環境變數狀態

`.env` 已設：
- `ANTHROPIC_API_KEY` ✓
- `OPENAI_API_KEY` ✓
- `OPENAI_MODEL_INSTANT`、`OPENAI_MODEL_THINKING` ✓

未設（M20 對應功能會自動跳過）：
- `PERPLEXITY_API_KEY`（外網搜尋）
- `GEMINI_API_KEY`（多 AI 交叉的 Gemini 鏈）

### 不存在的模型

M14 模型鏈裡 `claude-opus-4-8`、`claude-fable-5`、`gemini-3-pro` 都還沒對外開放。第一次調用會 404，code 會標記不可用、6 小時後重探。功能正常，第一次回應慢 1–2 秒。

## 5. 可信的 ground truth 來源

- 服務即時狀態：`systemctl status lumora.service`
- 即時 log：`sudo journalctl -u lumora.service -f`
- 當前部署 commit：`git -C /home/claude/lumora rev-parse HEAD`
- VPS-side Claude 部署紀錄：repo 上的 `deployed-2026-06-20-*` tag（每次部署都打一顆）
