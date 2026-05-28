import pytest
from app.services.ai.rewriters.sql_rewriter import SQLRewriter

def test_basic_rewrite():
    rewriter = SQLRewriter(dialect="clickhouse")
    sql = "SELECT * FROM sys_server_assets"
    filters = [{"condition": "region_code = {user.region}"}]
    context = {"region": "SH"}
    
    rewritten = rewriter.rewrite(sql, filters, context)
    assert "WHERE" in rewritten
    assert "region_code = 'SH'" in rewritten

def test_multiple_filters():
    rewriter = SQLRewriter(dialect="clickhouse")
    sql = "SELECT * FROM sys_server_assets WHERE cpu > 80"
    filters = [
        {"condition": "region_code = {user.region}"},
        {"condition": "status = 1"}
    ]
    context = {"region": "BJ"}
    
    rewritten = rewriter.rewrite(sql, filters, context)
    assert "cpu > 80" in rewritten
    assert "region_code = 'BJ'" in rewritten
    assert "status = 1" in rewritten
    assert rewritten.count("AND") >= 2

def test_subquery_rewrite():
    rewriter = SQLRewriter(dialect="clickhouse")
    sql = "SELECT name FROM (SELECT * FROM assets) t"
    filters = [{"condition": "dept_id = {user.dept}"}]
    context = {"dept": 101}
    
    rewritten = rewriter.rewrite(sql, filters, context)
    # The filter should be injected into the subquery as well
    assert "dept_id = 101" in rewritten

def test_union_rewrite():
    rewriter = SQLRewriter(dialect="clickhouse")
    sql = "SELECT id FROM table1 UNION ALL SELECT id FROM table2"
    filters = [{"condition": "org_id = 5"}]
    context = {} # No placeholders needed here
    
    rewritten = rewriter.rewrite(sql, filters, context)
    assert rewritten.count("WHERE org_id = 5") == 2

def test_strategy_resolution():
    config = {
        "user_overrides": {
            "1": [{"condition": "1=1"}]
        },
        "role_policies": {
            "manager": [{"condition": "dept_id = {user.dept}"}],
            "viewer": [{"condition": "id = {user.id}"}]
        },
        "default_policy": [{"condition": "1=0"}]
    }
    
    # User override test
    filters = SQLRewriter.resolve_strategy(1, ["manager"], config)
    assert filters == [{"condition": "1=1"}]
    
    # Role merge test
    filters = SQLRewriter.resolve_strategy(2, ["manager", "viewer"], config)
    assert len(filters) == 2
    
    # Default policy test
    filters = SQLRewriter.resolve_strategy(3, ["guest"], config)
    assert filters == [{"condition": "1=0"}]

def test_placeholder_replacer():
    rewriter = SQLRewriter()
    # Recommended way: use placeholder directly, rewriter handles quotes
    filters = [{"condition": "path LIKE {user.path}"}]
    context = {"path": "yovole/sh%"}
    
    prepared = rewriter._prepare_conditions(filters, context)
    assert len(prepared) > 0
    sql_cond = prepared[0].sql()
    assert "yovole/sh%" in sql_cond

def test_oracle_rewrite():
    # Oracle often uses double quotes for identifiers and has distinct syntax
    rewriter = SQLRewriter(dialect="oracle")
    sql = 'SELECT * FROM "USERS" WHERE "STATUS" = 1'
    filters = [{"condition": 'DEPT_ID = {user.dept}'}]
    context = {"dept": 500}
    
    rewritten = rewriter.rewrite(sql, filters, context)
    # sqlglot might normalize output, but it should contain the injected condition
    assert "DEPT_ID = 500" in rewritten
    assert "WHERE" in rewritten
