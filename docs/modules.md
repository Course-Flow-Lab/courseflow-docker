# 平台模块下载与安装

模块下载页：**[Courseflow 模块下载](https://course-flow-lab.github.io/courseflow-docker/)**。页面列出版本、源码提交、SHA-256 校验值、框架要求和对应 `.tgz` 文件。包内使用 `package/` 根目录，可直接交给框架安装，无需解压或在服务器上编译。

| 模块 | 编号 | 运行环境 | Docker 发行版 |
| --- | --- | --- | --- |
| 智慧树 | `zhs` | Linux amd64，glibc ≥ 2.36，Chromium | 已预装，通常无需重复安装 |
| 超星学习通 | `cx` | Python ≥ 3.11、包内 `requirements.txt` 的依赖 | 已预装，Python 为 `/opt/cx-venv/bin/python` |
| U校园 | `unipus` | Node.js ≥ 24，Chromium；作答功能需要配置模型 | 可选模块，默认不预装 |

智慧树预编译包适用于当前 Docker 发行版、Debian 12 或更新版本等兼容系统；ARM、Alpine 等环境需自行从页面关联的固定源码编译。超星与 U校园包本身不绑定 CPU 架构，但依赖的 Python、Node 和浏览器需要匹配服务器。统一题库已内置在框架中，不另装为平台模块。

## 下载并校验

在服务器上选择下载页的 `.tgz` 和同名 `.tgz.sha256`，保存到同一目录。可复制页面链接后使用 `curl -fLO '完整下载地址'`，或者从本机通过 SSH 传输下载文件。

```sh
# 把文件名替换为实际下载的版本；校验文件中的文件名应与 tgz 相同。
sha256sum -c courseflow-uai-版本-node24-提交.tgz.sha256
```

只安装来源可信且校验通过的包。模块是运行在服务器上的程序；下载包不包含账号、Cookie、站点密钥或个人题库。

## Docker 安装

在已初始化的 `courseflow-docker` 目录运行：

```sh
git pull --ff-only
./scripts/courseflow module install /绝对路径/模块包.tgz
./scripts/courseflow status
```

框架版本低于下载页所列要求时，先运行 `./scripts/courseflow update latest`。使用旧版 Release 解压包而非 Git 仓库时，可重新克隆当前部署工具并沿用原有 `.env`，或使用下文的管理员本地路径安装方式；旧包没有新增的 `module install` 命令。

该命令先停止 API，保存并验证备份，再通过临时容器安装包、验证模块握手并恢复服务；不会同时运行两个使用相同数据目录的后端。失败时回退到配对的原有数据快照。安装文件通过标准输入传入容器，不需要把文件改成公开可读或手动修改数据目录属主。普通宿主不需要安装 Node、Python、Rust 或 npm。

使用自定义配置文件的实例，应保持原有 `CF_CONFIG` 或 `.env` 配置。运行中的任务会随 API 停止而暂停，安装后先核对任务详情。模块版本变化时，旧任务可能需要重新创建；账号、主密钥与其他模块配置保留。

安装后在「站点管理 → 平台模块」查看版本与状态，再到「平台连接」登录。U校园可使用 `{ "source": "live" }`，课程会按账号自动读取，无需填写课程、教材或单元编号。Docker 中手动配置超星时使用 `{ "source": "live", "python": "/opt/cx-venv/bin/python" }`。智慧树使用 `{ "source": "live" }`。

也可把包放到 `STATE_DIR/data` 下的可读目录，再在管理员模块页面填写对应的 `/data/...tgz` 路径。网页当前支持服务器本地路径，不支持直接粘贴下载 URL 或从浏览器上传文件。

Docker 镜像更新会保留额外安装的模块；内置的智慧树和超星在镜像所固定的源码提交改变时，仍会按发行版升级内置版本。安装前可先执行 `./scripts/courseflow export-backup /私有离机目录` 保留站点备份。

## 独立 Framework 安装

安装前停止使用同一数据目录的服务，设置原有 `CF_DATA_DIR`，不要创建新的主密钥：

```sh
export CF_DATA_DIR=/原有数据目录
npm run cli -- module add /绝对路径/模块包.tgz
npm run cli -- module list
```

智慧树与 U校园已经包含运行产物，无需 Rust 或 npm 构建依赖。超星需要 Python 依赖环境；可先把包解压到临时目录，按照其中的 `requirements.txt` 创建 venv，再把该环境的 Python 绝对路径写入模块设置。Python 环境应位于源码和模块安装目录之外。智慧树见面课及 U校园登录等浏览器功能需要宿主配置 `CF_CHROMIUM=/浏览器绝对路径`。

恢复服务后检查模块状态，使用自己的账号小范围验收。本项目的打包发布检查只使用合成账号与离线 fixture，不使用真实平台账号。

## 发布维护

`module-sources.lock.json` 固定可发布模块的源码提交。维护者更新对应提交并推送 main 后，`Publish module downloads` 工作流会重新构建智慧树、打包 U校园、收集超星源码及依赖清单，生成版本化包和 SHA-256，并在禁用网络的 API 容器中实际安装、握手、登录和读取合成课程，全部通过后部署 GitHub Pages。也可手动触发工作流。

文件名包含模块版本、目标环境和源码提交，页面的 `catalog.json` 提供机器可读目录。Pages 展示锁文件中当前推荐版本；需要长期保留某个版本时，应保存下载包及校验文件。
