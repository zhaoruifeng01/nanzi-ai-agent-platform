## Git 协作：用户说「代码已合」

用户表示 PR/代码已合并后，**必须立即执行本地同步与重启**，不要只口头确认或列部署提醒：

1. `git fetch origin`
2. `git checkout main && git pull origin main`
3. `git checkout dev-agentscope && git merge main`（或 `git rebase main`，以 `DEVELOPMENT.md` 为准）
4. `git push origin dev-agentscope`（若本地领先远程）
5. `./dev.sh`（编译前端并重启本地服务）
6. 汇报：`main` / `dev-agentscope` 最新 commit、是否与远程一致

**不要**在用户未要求时擅自创建 PR 或 force push。

## 开发环境服务启停

在完成任何前端/后端代码修改后，**严禁主动或自动运行 `./dev.sh` 等编译、部署与启动脚本**。所有的服务编译、启停和重启测试均需交由用户在控制台手动操作。修改完毕后，Agent 仅负责通知用户代码修改已就绪，保持静默并等待测试。
