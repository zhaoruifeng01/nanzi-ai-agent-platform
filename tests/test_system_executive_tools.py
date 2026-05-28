import os
import pytest
import asyncio
from app.services.ai.tools.system_executive_tools import (
    validate_safe_path, read_local_file, write_local_file,
    execute_system_command, manage_system_process
)
from app.services.ai.tools.advanced_auxiliary_tools import (
    sqlite_scratchpad, directory_tree_navigator, code_syntax_linter
)

def test_safe_path_validation():
    # 验证合法路径正常返回
    valid_path = os.path.abspath("data/uploads/test.txt")
    assert validate_safe_path(valid_path) == valid_path

    # 验证路径穿越攻击被安全拦截
    with pytest.raises(ValueError, match="安全拦截：路径越界"):
        validate_safe_path("data/uploads/../../../etc/passwd")

def test_read_write_local_file():
    test_file = "data/uploads/test_junit.txt"
    test_content = "Hello Yunshu Agent Executive Tools!\nLine 2\nLine 3"
    
    # 写入测试
    res_write = write_local_file.invoke({"path": test_file, "content": test_content})
    assert "物理写入成功" in res_write

    # 分页读取测试
    res_read = read_local_file.invoke({"path": test_file, "offset": 0, "limit": 10})
    assert "[分页读取成功" in res_read
    assert "Hello Yuns" in res_read

    # Tail 读取测试
    res_tail = read_local_file.invoke({"path": test_file, "tail": True, "limit": 20})
    assert "[Tail 读取成功" in res_tail
    
    # 清理
    if os.path.exists(test_file):
        os.remove(test_file)

@pytest.mark.asyncio
async def test_execute_system_command():
    # 测试常规命令
    res = await execute_system_command.ainvoke({"command": "echo 'Yunshu'"})
    assert "Yunshu" in res
    assert "ExitCode=0" in res

    # 测试超时拦截
    res_timeout = await execute_system_command.ainvoke({"command": "sleep 40"})
    assert "已强制终止命令进程" in res_timeout

    # 测试高危命令拦截
    res_forbidden = await execute_system_command.ainvoke({"command": "rm -rf /"})
    assert "安全拦截：该命令包含高危操作" in res_forbidden

def test_manage_system_process():
    # 测试列出进程
    res_list = manage_system_process.invoke({"action": "list"})
    assert "PID" in res_list
    assert "进程名" in res_list

    # 测试核心主进程误杀拦截
    current_pid = os.getpid()
    res_kill = manage_system_process.invoke({"action": "kill", "pid": current_pid})
    assert "受到强制保护，禁止终止" in res_kill

def test_sqlite_scratchpad():
    session_id = "test_sess_99"
    # 测试建表与查询
    import_data = '{"users": [{"id": 1, "name": "Alice", "role": "admin"}, {"id": 2, "name": "Bob", "role": "user"}]}'
    sql = "SELECT name FROM users WHERE role = 'admin'"
    res = sqlite_scratchpad.invoke({"sql": sql, "session_id": session_id, "import_data": import_data})
    
    assert "Alice" in res
    assert "Bob" not in res
    
    # 清理沙箱临时文件
    db_path = f"data/sandbox/sess_{session_id}.db"
    if os.path.exists(db_path):
        os.remove(db_path)

def test_code_syntax_linter():
    # 正确代码
    res_ok = code_syntax_linter.invoke({"code": "def hello():\n    print('hi')"})
    assert "静态语法检测通过" in res_ok

    # 语法错误代码
    res_err = code_syntax_linter.invoke({"code": "def hello()\n    print('hi')"})
    assert "发现 Python 语法错误" in res_err
    assert "第 1 行" in res_err

@pytest.mark.asyncio
async def test_fetch_static_web_url_flow():
    from unittest.mock import patch, MagicMock, AsyncMock
    from app.services.ai.tools.advanced_auxiliary_tools import fetch_static_web_url
    
    mock_response = MagicMock()
    mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}
    mock_response.text = """
    <html>
      <head><style>body { color: red; }</style></head>
      <body>
        <header><h1>Header Navigation</h1></header>
        <div class="content">
          <p>Hello Yunshu Light Weight Web Content!</p>
          <script>console.log("noisy script");</script>
        </div>
        <footer>Footer Info</footer>
      </body>
    </html>
    """
    
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    
    with patch("httpx.AsyncClient") as mock_class:
        mock_class.return_value.__aenter__.return_value = mock_client
        res = await fetch_static_web_url.ainvoke({"url": "https://example.com/news"})
        
    assert "静态网页拉取成功" in res
    assert "Hello Yunshu Light Weight Web Content!" in res
    assert "Header Navigation" not in res
    assert "Footer Info" not in res
    assert "noisy script" not in res

@pytest.mark.asyncio
async def test_fetch_static_web_url_ssrf():
    from app.services.ai.tools.advanced_auxiliary_tools import fetch_static_web_url
    
    res = await fetch_static_web_url.ainvoke({"url": "http://127.0.0.1:8080/admin"})
    assert "安全拦截：URL 校验未通过" in res


def test_create_skills_tool(tmp_path):
    from app.services.ai.tools.system_executive_tools import create_skills
    from unittest.mock import patch, PropertyMock

    # 将 settings.SKILLS_DIR mock 成 pytest 的 tmp_path 隔离真实环境
    with patch("app.core.config.Settings.SKILLS_DIR", new_callable=PropertyMock) as mock_skills_dir:
        mock_skills_dir.return_value = str(tmp_path)
        
        skill_id = "test-ai-write"
        name = "AI自动写作技能"
        description = "自动生成文章"
        content = "---\nname: AI自动写作技能\ndescription: 自动生成文章\n---\n\n# 守则\n1. Imperatives"
        
        # 1. 成功创建技能
        res = create_skills.invoke({
            "skill_id": skill_id,
            "name": name,
            "description": description,
            "skill_md_content": content
        })
        assert "创建成功" in res
        
        # 验证物理文件写入
        skill_file = tmp_path / skill_id / "SKILL.md"
        assert skill_file.exists()
        assert skill_file.read_text(encoding="utf-8") == content

        # 2. 测试非法ID拦截
        res_bad_id = create_skills.invoke({
            "skill_id": "../bad-path",
            "name": name,
            "description": description,
            "skill_md_content": content
        })
        assert "非法技能 ID 格式" in res_bad_id


