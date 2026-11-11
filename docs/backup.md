# 备份与恢复

`backup` 在持有实例锁时停止 API，将数据库/WAL、原 master key、模块、模块配置及记录一起归档，附带 Compose、seccomp 和镜像锁文件。临时浏览器 profiles 不归档。它会解压新归档，检查 SHA-256、SQLite quick_check、32 字节原密钥和模块目录，然后才替换 `backups/latest` 并删除旧备份。失败时旧备份保留，API 恢复运行。

```sh
./scripts/courseflow backup
./scripts/courseflow export-backup /私有目录
```

每个实例只有一份正式备份；每个导出目录只有一个由本工具管理的 `courseflow-backup.tgz`。生成和验证期间会临时同时存在新旧快照。归档包含私密数据，使用私有目录并通过 SSH 等可信传输方式复制到其他主机；复制后校验摘要再替换离机旧副本。

当前本机与远端分别运行实例时，可在一个私有离机备份包中分别使用 `localhost/`、`remote/` 存放各自的唯一快照，清楚记录来源，不能交叉混用密钥和数据库。工具不自动登录其他主机，也不读取宿主 Nginx 配置；宿主配置由运维另行管理。

恢复当前实例的最近快照：

```sh
./scripts/courseflow restore
```

恢复先验证归档，再停止 API，整体恢复数据与当时部署配置。原数据暂存在 `.failed-data`；恢复健康检查通过后才删除。失败时保留诊断现场和快照，不重复执行覆盖；先检查容器日志、镜像可用性与磁盘空间。

迁移到新机器：准备同版本部署仓库、Docker 和 `.env`，导入镜像或确保能拉取，再执行：

```sh
./scripts/courseflow import-backup /私有目录/courseflow-backup.tgz
./scripts/courseflow restore
```

导入仅接受没有现有备份的新恢复目录。恢复使用快照中的 PUBLIC_URL 和 WEB_PORT；更改域名或端口可在恢复完成后修改 `.env`，再执行 update。STATE_DIR 使用新机器的配置。

只保留一份快照意味着下一次备份会替换上一份可恢复状态；镜像与上一版镜像不自动删除。禁止 `docker compose down -v` 或全局 volume prune 作为本应用的清理方式。
