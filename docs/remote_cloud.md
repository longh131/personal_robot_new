# 云端接入教程（pi.zwic.cn）

链路：`浏览器 HTTPS → Nginx(443) → 本机 9080 → FRP → 树莓派 127.0.0.1:5000`

树莓派上的 Web **不要**对公网监听。先在 Pi 上能 `curl 127.0.0.1:5000` 再配隧道。

## 1. 云服务器防火墙

- 公网只开 **80、443**。
- **7000**（frps 控制口）建议只允许你家宽带 IP，或至少不要和 9080 一起暴露给全世界。
- **9080** 只监听 `127.0.0.1`（给本机 Nginx），不要映射到公网。

## 2. 云服务器 frps

安装 [frp](https://github.com/fatedier/frp/releases) 后，`/etc/frp/frps.toml`：

```toml
bindAddr = "0.0.0.0"
bindPort = 7000
auth.method = "token"
auth.token = "换成足够长的随机串"

webServer.addr = "127.0.0.1"
webServer.port = 7500

# HTTP 虚拟主机，仅本机 Nginx 来连
vhostHTTPPort = 9080
```

`systemctl enable --now frps`

把 **同一 token** 配到树莓派 `frpc`，不要提交到 git。

## 3. 云服务器 Nginx + HTTPS

证书用 Let's Encrypt（`certbot --nginx -d pi.zwic.cn`）。站点：

```nginx
server {
    listen 80;
    server_name pi.zwic.cn;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name pi.zwic.cn;
    # ssl_certificate / ssl_certificate_key 由 certbot 填写

    add_header Strict-Transport-Security "max-age=31536000" always;

    location / {
        proxy_pass http://127.0.0.1:9080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 60s;
    }
}
```

DNS：`pi.zwic.cn` A 记录指向云服务器公网 IP。

## 4. 树莓派 frpc

`/opt/personal_robot/config/frpc.toml`（自行创建，勿提交 token）：

```toml
serverAddr = "你的云服务器IP或域名"
serverPort = 7000
auth.method = "token"
auth.token = "与 frps 相同"

[[proxies]]
name = "pi-web"
type = "http"
localIP = "127.0.0.1"
localPort = 5000
customDomains = ["pi.zwic.cn"]
```

日常一条命令（frpc + `main.py`，Ctrl+C 一起停）：

```bash
/opt/personal_robot/scripts/start.sh
```

只起隧道：`/opt/personal_robot/tools/frp/frpc -c /opt/personal_robot/config/frpc.toml`

## 5. 树莓派 Web

首次设密码：`python3 /opt/personal_robot/scripts/set_remote_password.py --user andylong`

之后用 `scripts/start.sh`。不要同时再开一份 `main.py`（端口 5000 会冲突）。

本机检查：`curl -s http://127.0.0.1:5000/api/state`

然后手机浏览器打开 `https://pi.zwic.cn` 登录。

## 6. 注意

- 第一刀没有视频、没有走轮。
- 心跳约 8 秒无请求会退出 REMOTE。
- 软件急停不是工业急停。
