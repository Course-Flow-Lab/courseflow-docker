# 离线安装

下载 Release 中 `linux-amd64-offline.tar.gz` 与外层 SHA256SUMS，验证后解压。包内包含 Docker 镜像、完整部署文件和镜像标签索引。`load` 会在目标 Docker 引擎中取得不可变镜像 ID。

```sh
tar -xzf courseflow-docker-v0.1.2-linux-amd64-offline.tar.gz
cd courseflow-docker
cp .env.example .env
# 修改 PUBLIC_URL 和实例目录
./scripts/courseflow load "$PWD"
CF_IMAGES_LOCK="$HOME/.local/share/courseflow-docker/images.local.env" ./scripts/courseflow init
./scripts/courseflow up
```

`load` 会验证包内所有摘要再执行 docker load，并在实例 `STATE_DIR` 写入 `images.local.env`。不同 Docker 镜像存储后端可能给导入的镜像分配不同 ID，因此不要把发布机器的 ID 当成目标机器的锁。若 `.env` 设置了 `STATE_DIR`，把上述 `CF_IMAGES_LOCK` 路径改为该目录下的 `images.local.env`；离线更新同样传入这个锁文件。

首次初始化不访问真实学习平台；后续登录、学习、模型和官方浏览器仍需要网络。
