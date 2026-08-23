# Mochi - AI宠物养成 + 业主群

SQLite版本，可部署到Railway/Render等免费云平台。

## 部署到Railway

1. 在Railway创建新项目
2. 连接GitHub仓库，或直接上传这些文件：
   - `app.py`
   - `init_db.py`
   - `requirements.txt`
   - `Procfile`
   - `templates/index.html`（如果有前端）

3. 设置环境变量：
   ```
   MOCHI_ADMIN_KEY=你的管理员密钥
   PORT=5000
   MCP_PORT=5003
   ```

4. Railway会自动：
   - 安装依赖（requirements.txt）
   - 初始化SQLite数据库
   - 启动Flask + MCP Server

5. 部署完成后：
   - Web API: `https://你的域名/api/...`
   - MCP Server: `https://你的域名:5003/mcp/sse?token=你的token`

## 本地测试

```bash
# 初始化数据库
python3 init_db.py

# 启动服务
python3 app.py

# 生成邀请码
curl "http://localhost:5000/api/admin/invite?key=你的密钥"

# 注册用户
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{"invite_code":"邀请码","username":"test","password":"123456"}'
```

## 数据持久化

Railway提供5GB免费存储空间，SQLite数据库文件保存在 `/root/mochi/mochi.db`。

状态文件保存在 `/root/mochi/states/`。

部署后数据会持久化，不会丢失。

## 端口说明

- Flask API: `PORT` 环境变量（默认5000）
- MCP Server: `MCP_PORT` 环境变量（默认5003）

Railway会自动分配 `PORT`，MCP端口可手动设置。

## 管理员功能

生成邀请码：
```
GET /api/admin/invite?key=你的MOCHI_ADMIN_KEY
```

返回：
```json
{"ok": true, "code": "ABC12345"}
```