# FastAPI 启动说明

## 1. 本地开发

```bash
cd fksapi
pip install -r requirements.txt
python fastapi_server.py
```

默认监听：

- `http://0.0.0.0:5000`

接口文档：

- `http://127.0.0.1:5000/docs`

## 2. 生产部署

推荐使用新的 `fks-fastapi.service`：

```bash
sudo cp fks-fastapi.service /etc/systemd/system/fks.service
sudo systemctl daemon-reload
sudo systemctl restart fks
sudo systemctl status fks
```

## 3. 兼容策略

- 当前保留旧入口 `recharge_verify_server.py` 作为回滚备份
- 新入口为 `fastapi_server.py`
- 对外接口路径保持不变，方便小程序和后台平滑切换

## 4. 后续建议

- 下一阶段继续把 `recharge_verify_server.py` 里的共享工具函数迁移到独立模块
- 再按业务拆成 `routers/ services/ repositories`
- 最终再移除旧的 `BaseHTTPRequestHandler` 入口
