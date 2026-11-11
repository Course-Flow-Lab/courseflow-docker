# 更新与回退

从一个明确的 GitHub Release 下载并核对 `images.lock.env` 和 SHA256SUMS；同时更新本部署仓库或使用该版本的部署包。

```sh
./scripts/courseflow update /发布包/images.lock.env
```

顺序为：拉取/检查新镜像 → 停止 API → 一致备份并验证 → 更新内置模块（仅源码提交改变时，保留设置和启用状态）→ 应用新部署配置 → 等待两容器健康。额外安装的平台模块保留。更新失败时使用旧镜像里的恢复工具，整体恢复配对快照，再启动旧服务。

不自动追踪 latest，不自动删除镜像。`sources.lock.json` 是组件组合的版本依据；框架包版本相同的两个提交也可能是不同发布。`release.json` 同时记录源提交、镜像 ID 与 GHCR digest。

已完成的更新若需人工回退，使用 `restore`。还原后核对账号、模块和课程任务状态，手动恢复需要继续的暂停任务。
