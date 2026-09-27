# HyperFit 部署教程

[中文](deployment.zh.md) · [English](deployment.en.md) · [日本語](deployment.ja.md)

## 获取代码

本教程部署完整 Python API 与三语网页。Python 3.12 推荐，项目最低 3.11；无 Node/npm 构建要求。先安装 Git 与 Python。服务器端计算需要普通 CPU，不依赖 Abaqus 或 GPU。

```text
git clone https://github.com/ywytrew/hyperfit.git
cd hyperfit
```

## Windows

在仓库根目录运行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m uvicorn hyperfit.api:app --host 127.0.0.1 --port 8765 --workers 1
```

打开 http://127.0.0.1:8765，中文默认，也可用 ?lang=en 或 ?lang=ja。以后可双击 start.cmd；停止服务按 Ctrl+C。PowerShell 脚本被执行策略限制时可直接运行上述 Python 命令，无需更改系统策略。端口占用时将 8765 改为 8766，或运行 ./start.ps1 -Port 8766。

## Linux / macOS

先准备 Python 3.12 和 venv 支持，然后在仓库根目录运行：

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m uvicorn hyperfit.api:app --host 127.0.0.1 --port 8765 --workers 1
```

同样访问 127.0.0.1:8765，Ctrl+C 停止。启动命令只使用一个 worker：任务状态与取消机制目前在单进程内管理，不能通过增加 Uvicorn worker 来安全扩容。

## Docker Compose

安装并启动 Docker Engine 28+ 或相应 Docker Desktop（Linux 容器），以及 Compose 插件。当前 PC 的 Docker daemon 未运行，因此本地没有完成容器实机验证；仓库 CI 包含容器构建与 HTTP 冒烟检查。

```sh
docker compose up --build -d
docker compose ps
docker compose logs --tail=50 hyperfit
# Stop without removing saved runs:
docker compose down
```

容器内部监听 0.0.0.0:8765，Compose 仅映射到主机 127.0.0.1:8765。使用非 root 用户、单 worker，并把运行数据持久化到 hyperfit-runs 命名卷。镜像只复制应用与锁文件，不包含本机实验或 runs。健康检查访问 /api/models。不要使用 down -v，除非明确希望删除运行卷。

如果本机 8765 已被其他实例占用，把 compose.yaml 中主机端口改成 127.0.0.1:8766:8765，再访问 8766。不能只改浏览器地址。

## 远程服务器：SSH 隧道

在自己的服务器克隆仓库并按上面的原生或 Docker 方法启动。保持服务器只监听回环地址，不开放 8765 防火墙端口。在使用者电脑运行以下命令，替换服务器账号和主机名：

```sh
ssh -N -L 8765:127.0.0.1:8765 your-user@your-server
```

保持 SSH 窗口开启，再在本机访问 http://127.0.0.1:8765。若本地已有服务，可将隧道左侧 8765 改为 8766。数据会在远程服务器处理和存储。该应用没有内置用户鉴权、隔离或配额，因此此教程采用 SSH 访问；公网多用户服务还需要身份验证、HTTPS、访问控制与计算队列设计，不能仅把监听地址改为 0.0.0.0。

## 前后端与运行记录

默认由同一服务提供静态前端和 /api/*，Python 科学核心不依赖网页。独立前端可在 app.js 载入前设置 window.HYPERFIT_API 为 API 地址；开发 CORS 仅允许 localhost:5173 和 127.0.0.1:5173。跨机器部署优先使用同源反向代理，不要依靠关闭 CORS 解决访问问题。GitHub Pages 只能承载静态内容，不能执行此 Python/FEM 后端。

原生运行默认保存到仓库 runs/；可在启动前设置 HYPERFIT_RUNS 为专用可写目录。Docker 保存到 /data 命名卷。备份完整目录或卷，并保管包含实验输入的导出 JSON。重启中断的任务不会自动续算。更新前导出记录、备份运行目录并记下 git rev-parse HEAD；停止服务后 git pull --ff-only、安装锁文件（或 Compose 重新构建）再启动。回滚时使用单独目录检出旧提交并创建其环境，不覆盖未提交工作。

## 验证与维护

使用虚拟环境对应的 Python 执行（Windows 为 .venv/Scripts/python.exe，Linux/macOS 为 .venv/bin/python）：

```sh
python -m pytest -q
python -m hyperfit.verify --output validation-results/fem-verification.json
python tools/build_manuals.py
python tools/package_source.py
```

浏览器验收：合成示例 → 拟合 → 切换三语 → 选择候选 → 立方体检验 → 导出 JSON。/docs 提供 API 交互文档。科学验证边界见[使用手册](manual.zh.md)和 [VALIDATION](VALIDATION.md)。Windows 原生已在本机测试；其他平台及 Docker 的状态以仓库 Actions 的实际结果为准。

网络行为参考官方文档：[Docker port publishing](https://docs.docker.com/engine/network/port-publishing/) · [Uvicorn deployment](https://uvicorn.dev/deployment/)
