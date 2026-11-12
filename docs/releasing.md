# 维护者构建与发布

`sources.lock.json` 固定四个应用仓库的完整提交和三个基础镜像 digest。构建仅下载这些公开提交的归档，不读取开发者相邻工作树、运行数据或账号。首版为 Linux amd64，运行镜像与部署版本一起发布。

本机构建需要 Docker、Python 3.12+ 及网络：

```sh
python3 build/build.py --version v0.1.2
python3 tests/smoke.py
```

源码归档 SHA-256 记录在 `.build/context/source-archives.json`。固定源码和基础镜像不等于逐字节可重现：Debian 安全更新和 Python 间接依赖仍由构建时的软件源提供；最终发布的镜像 digest 才是部署使用的准确产物标识。

CI 的 `check.yml` 在 main、Pull Request 和手动触发时运行完整构建及验收。后端测试入口先断言智慧树二进制和超星 Python 依赖存在，再执行全部 `.test.ts` 和 `.test.mjs`，并拒绝跳过测试；同时运行 WebUI 检查、测试和构建、Rust locked 测试以及超星 unittest。容器验收覆盖登录、Cookie、CSRF、编码路径、下载、模块 fixture、Chromium 沙箱、幂等初始化、备份损坏、更新失败回退和离机恢复。它只使用临时合成数据。

发布步骤：

1. 修改源码锁文件、版本与文档；等待 CI 通过。
2. 创建并推送 `vX.Y.Z` 标签，或手动运行 `Release containers` 并填写版本。已经公开的版本不可覆盖，应使用新版本。
3. 工作流重新验收，使用最小范围的 `GITHUB_TOKEN` 写入 GHCR 和 Release，无需存储个人 token。
4. 首次创建 GHCR 包时，组织管理员需要在两个包的 Package settings 中把 visibility 设为 Public。GitHub 的新包默认私有，即使关联仓库已经公开。如果 Public 不可选，先由组织管理员在 Settings → Packages → Package creation 允许 Public。若因此匿名拉取失败，先改为公开，再重跑该发布工作流；未完成的 Release 保持草稿。
5. 匿名拉取通过后，工作流公开 Release，包含在线部署包、离线镜像包、digest 锁文件、离线镜像标签索引、来源清单及 SHA-256。离线本地镜像 ID 由目标机的 `load` 命令生成。
6. 从已发布 Release 下载 `images.lock.env`，提交到 main，供新克隆的用户直接启动。不要手工猜测 digest，也不要让默认配置追踪 `latest`。

镜像分别为 `ghcr.io/course-flow-lab/courseflow-api` 与 `ghcr.io/course-flow-lab/courseflow-webui`，镜像 source 标签关联此部署仓库。工作流中使用固定提交的 Actions；更新这些提交时仍应先通过完整验收。

发布依赖 GitHub Actions 可用、仓库允许 Actions 写入 Packages，以及组织允许公开包。开启公开包的操作只需首次执行，后续版本沿用包可见性。[GitHub 官方说明](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility)
