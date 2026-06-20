# 給另一個 Claude 的訊息

## ⛔ 這條指令請撤回，不要再給 VPS 跑

```bash
sudo cp ~/Lumora-vps/nginx-lumora.conf /etc/nginx/sites-available/lumora
sudo ln -sf /etc/nginx/sites-available/lumora /etc/nginx/sites-enabled/lumora
sudo nginx -t && sudo systemctl restart nginx
```

## 為什麼

live 的 `/etc/nginx/sites-available/lumora` 有 `auth_basic` 保護（Cloudflare 後面唯一的身份檢查），你給的範本沒有。覆寫下去等於把網站完全公開——任何 IP 都能直接打 `/api/v1/divine`、`/api/v1/chat` 燒掉 Anthropic / OpenAI 配額。

同時 `server_name` 從 `lumora.139.59.228.58.sslip.io` 變成 `_`（catch-all）會搶到同機其他 vhost 的流量（例如 ttyd）。

## 正確做法

保留 `auth_basic` 和原 `server_name`，只把你想加的兩個東西（`client_max_body_size 20M;`、`proxy_send_timeout 120s;`）加上去。完整應該長這樣：

```nginx
server {
    listen 80;
    server_name lumora.139.59.228.58.sslip.io;

    auth_basic "Lumora";
    auth_basic_user_file /etc/nginx/.lumora_htpasswd;
    add_header Cache-Control "no-store" always;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }
}
```

## 補充

repo 已經有一份 `INFRA-NOTES.md` 詳細寫了這台 VPS 的實際架構、不要再做的事、現有保護機制。你的 `nginx-lumora.conf` 範本不用刪，但請在註解標清楚「這是 fresh install 用，不是 live VPS 用」。

下次寫部署 / nginx 指令前**先讀 `INFRA-NOTES.md`**。
