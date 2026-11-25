# Courseflow Docker

[![CI](https://github.com/Course-Flow-Lab/courseflow-docker/actions/workflows/check.yml/badge.svg)](https://github.com/Course-Flow-Lab/courseflow-docker/actions/workflows/check.yml)

Courseflow 的即用部署入口：API、Web 与内部验证码服务三个容器（复用两个发行镜像），内置智慧树与超星模块、Chromium 和 Python 环境。使用者只需 **Linux amd64、Docker Engine、Docker Compose v2、Bash 与 flock（util-linux）**，无需安装 Node、Rust 或 Python。

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

默认使用 [GitHub Packages](https://github.com/orgs/Course-Flow-Lab/packages?repo_name=courseflow-docker) 中的 `ghcr.io/course-flow-lab/courseflow-api:latest` 和 `ghcr.io/course-flow-lab/courseflow-webui:latest`；API 与验证码服务复用 API 镜像。`images.lock.env` 保留这两个 `:latest` 引用，Compose 使用 `pull_policy: always`。历史固定版本部署包及离线包仍可从 [Releases](https://github.com/Course-Flow-Lab/courseflow-docker/releases) 获取。

0.1.8 包含 Framework 0.1.13、WebUI 0.1.3 和 ZHS 0.3.8，提供团队多账号及共享课拼图验证。验证码服务预装 ddddocr 1.5.6，只在内部网络提供识别；数据库升级和回退要求见[更新说明](docs/upgrade.md)。

0.1.12 配套 Framework 0.1.21、WebUI 0.1.8、ZHS 0.3.16 和超星 0.1.11。修复新任务继承历史交卷缓存后每章都要手动继续的问题，并为明确只读请求增加一次有界暂时故障重试。学习和交卷写入、人工验证与未知结果保护不变。超星旧任务可显式迁移并沿用原检查点，详见[更新说明](docs/upgrade.md)。

0.1.11 配套 Framework 0.1.20、WebUI 0.1.8、ZHS 0.3.16 和超星 0.1.10。包含实时手动验证码拖动、管理员拖动测试、模型答案格式重试、全局夜间后台保活限制，以及超星历史交卷与现有答卷的只读核对。超星旧任务请显式迁移，详见[更新说明](docs/upgrade.md)。

0.1.10 配套 Framework 0.1.18、WebUI 0.1.5、ZHS 0.3.16 和超星 0.1.9。智慧树使用官方验证码组件，并可在任务弹窗中手动完成验证；超星支持前置章节接续学习、前置测验作答及提交结果恢复。可选模块更新为 U校园 0.5.1 和 QLTeacher 0.2.4，分别提供宿主题库复用与视频真实计时修复。升级步骤及旧任务迁移要求见[更新说明](docs/upgrade.md)。

0.1.9 配套 Framework 0.1.14、WebUI 0.1.4 和 ZHS 0.3.9。智慧树修复验证码弹窗加载超时。模块升级后，兼容的旧任务可从任务详情迁移并继续。独立模块包见 [ZHS Releases](https://github.com/Course-Flow-Lab/courseflow-zhs/releases) 和[模块下载页](https://course-flow-lab.github.io/courseflow-docker/)。

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

运行数据默认位于部署仓库相邻的 `docker-state/`，独立于仓库。设置 `STATE_DIR` 可选择支持 Unix 私有权限的其他绝对路径。`down` 只移除本实例的容器和网络，数据保留。初始化可重复执行；遇到已有但无法识别的数据目录会停止，不会重新生成密钥。

每次正式发布都会更新 `ghcr.io/course-flow-lab/courseflow-api:latest` 和 `ghcr.io/course-flow-lab/courseflow-webui:latest`。`update latest` 主动拉取两个镜像，核对属于同一版本，执行备份、模块更新和健康检查；部署配置及容器继续使用字面量 `:latest`，不转换为版本标签或 digest。执行前先 `git pull --ff-only` 更新本部署仓库。`latest` 是可变标签，恢复旧数据不代表回退镜像版本；固定版本恢复仍可显式传入 Release 的 `images.lock.env`。

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
