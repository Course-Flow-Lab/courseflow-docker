# Courseflow Docker

[![CI](https://github.com/Course-Flow-Lab/courseflow-docker/actions/workflows/check.yml/badge.svg)](https://github.com/Course-Flow-Lab/courseflow-docker/actions/workflows/check.yml)

Courseflow 的即用部署入口：API + Web 两个容器，内置智慧树与超星模块、Chromium 和 Python 环境。使用者只需 **Linux amd64、Docker Engine、Docker Compose v2、Bash 与 flock（util-linux）**，无需安装 Node、Rust 或 Python。

## 快速开始

```sh
git clone https://github.com/Course-Flow-Lab/courseflow-docker.git
cd courseflow-docker
cp .env.example .env
# 编辑 PUBLIC_URL：正式部署填写 https://你的域名
./scripts/courseflow doctor
./scripts/courseflow init
./scripts/courseflow up
./scripts/courseflow setup-code
```

默认本机试用地址为 `http://127.0.0.1:8100`。在该页面输入最后一条命令显示的设置码创建管理员。首次创建后设置码不再用于注册；后续注册默认需要邀请码。

远端部署时，将现有 HTTPS 反向代理指向 `127.0.0.1:8100`，并把 `.env` 的 `PUBLIC_URL` 设置为浏览器实际使用的 HTTPS 源地址。参考 [Nginx 示例](examples/nginx.conf)。网关默认仅绑定回环；API 不发布宿主端口。

`images.lock.env` 固定已发布镜像 digest，来源为 [GitHub Packages](https://github.com/orgs/Course-Flow-Lab/packages?repo_name=courseflow-docker)。也可从 [Releases](https://github.com/Course-Flow-Lab/courseflow-docker/releases) 下载带锁文件的部署包或完整离线包。

## 日常使用

```sh
./scripts/courseflow status
./scripts/courseflow backup
./scripts/courseflow export-backup /你的私有离机目录
./scripts/courseflow update latest
./scripts/courseflow update /新发布/images.lock.env
./scripts/courseflow restore
./scripts/courseflow down
```

运行数据默认位于 `~/.local/share/courseflow-docker`，独立于仓库。设置 `STATE_DIR` 可选择其他绝对路径。`down` 只移除本实例的容器和网络，数据保留。初始化可重复执行；遇到已有但无法识别的数据目录会停止，不会重新生成密钥。

每次正式发布都会更新 `ghcr.io/course-flow-lab/courseflow-api:latest` 和 `ghcr.io/course-flow-lab/courseflow-webui:latest`。`update latest` 主动拉取两个镜像，核对属于同一版本，再解析为固定 digest，执行备份、模块更新和健康检查；失败时回退。执行前先 `git pull --ff-only` 更新本部署仓库。固定版本升级仍可传入 Release 的 `images.lock.env`。

每个实例只保留 **一份** 已验证备份 `backups/latest`；离机导出使用固定文件名 `courseflow-backup.tgz`，校验成功后替换上一份。备份会短暂停止 API；运行中的任务会暂停，恢复后需人工确认再继续。请阅读 [备份与恢复](docs/backup.md)。

## 文档

- [配置与平台模块](docs/configuration.md)
- [模块下载与安装](docs/modules.md)（[直接下载 .tgz](https://course-flow-lab.github.io/courseflow-docker/)）
- [更新和失败回退](docs/upgrade.md)
- [备份、离机副本和迁移](docs/backup.md)
- [离线安装](docs/offline.md)
- [维护者构建与发布](docs/releasing.md)

CI 使用合成账号和离线 fixture 验证框架、智慧树、超星及 HTTP 权限边界，并演练 Chromium 沙箱、更新失败回退和离机恢复。真实账号登录、课程目录和任务结果需要部署者自行验收。首版仅支持 Linux amd64。

部署工具使用 MIT 许可。组件许可与来源见 [licenses](licenses/)，Chromium seccomp 来源及 Apache-2.0 许可见 [security/NOTICE.md](security/NOTICE.md)。系统软件保留镜像中的上游许可文件。
