# 离线安装

下载 Release 中 `linux-amd64-offline.tar.gz` 与外层 SHA256SUMS，验证后解压。包内包含 Docker 镜像、完整部署文件及固定的本地镜像 ID。

```sh
tar -xzf courseflow-docker-v0.1.0-linux-amd64-offline.tar.gz
cd courseflow-docker
cp .env.example .env
# 修改 PUBLIC_URL 和实例目录
./scripts/courseflow load "$PWD"
CF_IMAGES_LOCK="$PWD/images.offline.env" ./scripts/courseflow init
./scripts/courseflow up
```

`load` 会验证包内所有摘要再执行 docker load。离线锁文件按不可变镜像 ID 引用镜像；Docker save/load 不保证保留 registry RepoDigests，因此离线模式使用单独的 images.offline.env。离线更新同样传入该锁文件。

首次初始化不访问真实学习平台；后续登录、学习、模型和官方浏览器仍需要网络。
