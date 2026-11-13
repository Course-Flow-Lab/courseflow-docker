# 配置

数据目录需要支持 Unix 属主和权限的 Linux 文件系统（例如 ext4 或 Btrfs）。不要把 STATE_DIR 放到忽略 chmod 的 NTFS/FAT 共享目录中。仓库本身可以放在其他位置。

`.env` 使用不带引号的 `KEY=value`，支持以下变量。部署脚本解析值，不执行文件中的 shell 命令。

| 变量 | 默认值 | 用途 |
|---|---|---|
| PUBLIC_URL | 示例为 http://127.0.0.1:8100 | 必填，浏览器实际访问的源地址，不含路径 |
| WEB_PORT | 8100 | 宿主回环网关端口 |
| PROJECT_NAME | courseflow-docker | 本实例的 Compose 名称 |
| STATE_DIR | ~/.local/share/courseflow-docker | 私有状态目录；自定义时填写绝对路径 |

修改 URL 或端口后，执行 `update images.lock.env`，会先备份再应用配置。每个实例使用独立的 STATE_DIR、PROJECT_NAME 和端口。不要把多个项目指向同一 SQLite 目录。

API 使用 Node 24、Python `/opt/cx-venv/bin/python`、Chromium `/usr/bin/chromium`，以 UID 1000 运行。初始化工具创建匹配属主的 0700 数据目录及 0600 密钥。Chromium 依赖宿主允许容器内非特权用户 namespace；部署不使用 privileged、SYS_ADMIN 或 `--no-sandbox`。

首次安装默认启用智慧树与超星的 live 模式。额外模块可上传到 STATE_DIR/data 下，再在管理员“平台模块”页面填写容器内 `/data/...` 路径安装，后续容器更新会保留该模块。

U校园等可选模块可从 [模块下载页](https://course-flow-lab.github.io/courseflow-docker/) 获取可直接安装的 `.tgz`，详见 [模块安装手册](modules.md)。U校园的 ID 是 `unipus`，使用 `source=live` 后按当前账号读取课程，不需要填写全局课程、教材或单元编号。它不是本发行版默认预装组件。

日志有大小上限；不要将含设置码、Cookie 或令牌的日志上传到公开 issue。设置码只在管理员创建前有效。
