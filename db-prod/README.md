# 数据库初始化与升级指南

本目录包含云枢 AI Agent 平台生产环境的数据库初始化脚本 (Migrations) 以及部署脚本。
为了防止误触或破坏已有数据，**初始化脚本中不再包含 `CREATE DATABASE` 与自动切换库的逻辑**。在运行初始化或迁移之前，您需要先手动创建数据库。

## 📁 文件结构

| 文件名/目录 | 用途 |
| :--- | :--- |
| `V0` - `V*.sql` | 版本化的数据库迁移脚本（按序号从小到大执行），涵盖建表、配置初始化等。 |
| `INIT-USER-ADMIN.sql` | 默认管理员账号初始化脚本（含预置的 API Key）。 |
| `apply-sql.sh` | 引导式的数据库部署 Shell 脚本（交互式输入连接配置，防误操作）。 |
| `apply_sql.py` | 实际执行 SQL 导入的核心 Python 脚本。 |

---

## 🚀 数据库部署步骤

### 第一步：手动创建数据库

登录您的 MySQL 服务，手动创建一个干净的数据库。
为了良好地支持中文字符与 Emoji，请确保使用 `utf8mb4` 字符集。

```sql
CREATE DATABASE IF NOT EXISTS `yunshu_ai_agent_platform` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

### 第二步：运行结构初始化脚本

平台提供了交互式的 Shell 脚本，能够自动扫描并按顺序应用所有 `V*.sql` 脚本。

1. **进入项目根目录**。
2. 确保已激活 Python 虚拟环境，并安装了 `requirements.txt`（脚本依赖 `aiomysql`）。
3. 运行以下命令（若提示权限不足，请先执行 `chmod +x db-prod/apply-sql.sh`）：

```bash
./db-prod/apply-sql.sh
```

4. **根据交互提示，依次输入**：
   - **MySQL host**: 数据库主机地址（例如 `127.0.0.1`）
   - **MySQL port**: 端口号（直接回车默认为 `3306`）
   - **MySQL user**: 用户名（例如 `root`）
   - **MySQL password**: 密码（输入时不会显示）
   - **Target database**: 输入第一步创建的数据库名称（例如 `yunshu_ai_agent_platform`）

5. **二次确认**：
   脚本会打印上述连接信息，请仔细检查，确认无误后输入 **`YES`** 即可开始执行。

> 💡 **幂等性说明**：脚本具备幂等性（Idempotency），如果某些表或字段已经存在，脚本会自动跳过，因此可以在后续版本升级时安全地重复运行。

---

### 第三步：配置默认管理员账号（可选）

如果您是首次部署，需要生成默认的 `admin` 账号和默认 API Key，可以运行以下命令来导入管理员数据：

```bash
./db-prod/apply-sql.sh db-prod/INIT-USER-ADMIN.sql
```
（同样需要输入上述的 MySQL 连接信息，并输入 `YES` 确认执行）

**💡 默认管理员账号信息说明**：
- **默认用户名**：`admin`
- **默认 API Key**：`5BYfsKWhU_Cfx83cuo8E0kd4AtEhlUHDVlKwwR2kN-c`
- **初始登录说明**：该脚本未设置初始密码。默认情况下，系统在第一次生成后**仅支持通过 API Key 进行登录和接口调用**。用户成功登录系统后，可前往用户管理或个人中心页面**自行修改并设置初始登录密码**。

---

## ⚠️ 常见问题

### Q1: 运行脚本时报错 `ModuleNotFoundError: No module named 'aiomysql'`
**原因**：未在虚拟环境中安装依赖。
**解决**：
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Q2: 提示 `Skipping (already applied): ...` 报错
**原因**：这是因为迁移脚本具有幂等性设计。由于数据库中已经存在对应的表或字段，系统为了避免覆盖已有数据，主动跳过了该执行步骤。这是**正常现象**，无需处理。

### Q3: 如何自定义创建新的管理员？
如果不希望使用默认 the `INIT-USER-ADMIN.sql` 配置，可在系统部署完成后通过命令行直接生成：
```bash
export PYTHONPATH=$PYTHONPATH:.
./venv/bin/python scripts/create_admin_key.py <username>
```

---
⚠️ **安全提示**：在任何生产环境执行数据库结构变更前，请务必提前备份您的数据！
