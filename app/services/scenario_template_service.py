from __future__ import annotations

from dataclasses import dataclass
import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AIAgent, AIAgentVersion
from app.models.knowledge import KnowledgeBaseMetadata
from app.models.mcp import McpToolCache
from app.models.metadata import MetaDataset
from app.models.scenario_template import ScenarioTemplateInstallRun, ScenarioTemplateInstance
from app.models.tool import SysApiTool
from app.schemas.agent import AIAgentBase, AIAgentVersionBase
from app.schemas.scenario_template import (
    ScenarioTemplateDetail,
    ScenarioTemplateInstallRequest,
    ScenarioTemplateInstallResponse,
    ScenarioTemplateInstanceSummary,
    ScenarioTemplatePrecheckItem,
    ScenarioTemplatePrecheckResponse,
    ScenarioTemplateResourceOption,
    ScenarioTemplateResourceOptionsResponse,
    ScenarioTemplateResourceRequirement,
    ScenarioTemplateSummary,
)
from app.services.ai.agent_manager import AgentManagerService


CHATBI_BUSINESS_ANALYSIS_MANIFEST: Dict[str, Any] = {
    "id": "chatbi-business-analysis",
    "name": "经营分析 ChatBI 助手",
    "category": "ChatBI",
    "description": "面向经营指标、销售趋势、区域排名和月报解读的可交付数据分析助手。",
    "tags": ["ChatBI", "数据门户", "黄金报表", "经营分析"],
    "recommended": True,
    "target_departments": ["经营管理", "销售管理", "财务分析"],
    "delivery_time": "0.5-1 天",
    "maturity": "标准版",
    "included_capabilities": ["Agent", "ChatBI", "工具调用", "知识检索", "验收样例"],
    "deliverables": [
        "Agent",
        "系统提示词",
        "工具配置",
        "推荐问题",
        "验收标准",
        "交付清单",
    ],
    "business_goals": [
        "让经营人员用自然语言查询销售、订单、客户和财务类指标。",
        "围绕趋势、排名、异常和原因假设生成结构化经营分析结论。",
        "把高频分析问题沉淀为可复用案例和黄金 SQL。",
    ],
    "install_steps": ["基础信息", "绑定资源", "预检", "安装发布"],
    "acceptance_criteria": [
        "经营指标类问题必须优先调用 SQL 查询工具获取真实数据。",
        "回答必须说明数据依据，并在缺少时间或指标口径时主动澄清。",
        "至少完成 3 条样例问题试跑，并将有效 SQL 沉淀到案例集。",
    ],
    "agent": {
        "name": "chatbi-business-analysis",
        "display_name": "经营分析 ChatBI 助手",
        "description": "通过自然语言查询经营数据，生成趋势、排名、异常和经营简报。",
        "capabilities": ["data_query", "knowledge_search"],
        "sort_order": 80,
        "engine_type": "LOCAL",
        "engine_config": {
            "scenario_template_id": "chatbi-business-analysis",
            "scenario_category": "ChatBI",
        },
    },
    "version": {
        "model_name": None,
        "temperature": 0.0,
        "system_prompt": (
            "你是经营分析 ChatBI 助手，负责围绕企业经营数据回答业务问题。"
            "优先使用数据查询能力获取真实数据，再给出趋势、排名、异常、原因假设和下一步建议。"
            "当问题缺少时间、指标或分析对象时，先提出澄清问题；不要编造不存在的数据。"
        ),
        "tools": ["get_dataset_schema", "execute_sql_query", "search_knowledge_base"],
        "skills_custom": False,
        "skills": [],
        "comment": "由场景模板一键交付生成",
    },
    "required_resources": [
        {
            "type": "metadata_dataset",
            "name": "经营数据集",
            "required": True,
            "description": "建议绑定销售、订单、客户或财务类元数据集。",
        },
        {
            "type": "knowledge_base",
            "name": "指标口径知识库",
            "required": False,
            "description": "建议绑定指标解释、经营制度、报表口径文档。",
        },
    ],
    "sample_questions": [
        "本月销售额同比和环比怎么样？",
        "哪些区域销售下滑最明显？",
        "帮我生成本周经营分析简报。",
    ],
    "next_steps": [
        "进入智能体中心检查系统提示词和工具配置。",
        "在元数据管理中绑定真实经营数据集并补充指标口径。",
        "用模板样例问题跑一次验收，再沉淀黄金 SQL 或案例集。",
    ],
}

KNOWLEDGE_QA_MANIFEST: Dict[str, Any] = {
    "id": "knowledge-qa-assistant",
    "name": "企业知识问答助手",
    "category": "知识库",
    "description": "面向制度、产品、交付文档和常见问题的企业知识检索问答助手。",
    "tags": ["知识库", "RAGFlow", "引用溯源", "反馈纠错"],
    "recommended": True,
    "target_departments": ["人力行政", "售前交付", "客服支持"],
    "delivery_time": "0.5 天",
    "maturity": "基础版",
    "included_capabilities": ["Agent", "知识检索", "引用溯源", "反馈入口"],
    "deliverables": ["Agent", "系统提示词", "知识库绑定建议", "推荐问题", "验收标准", "交付清单"],
    "business_goals": [
        "让员工直接询问制度、产品手册和交付规范，减少人工查文档成本。",
        "回答时带出知识来源，方便业务人员追溯原文和发现知识缺口。",
        "把高频问题沉淀为推荐问法，并把错误反馈流转到知识维护动作。",
    ],
    "install_steps": ["基础信息", "绑定资源", "预检", "安装发布"],
    "acceptance_criteria": [
        "知识类问题必须优先调用知识检索工具，并展示引用依据。",
        "找不到资料时要说明缺口，不允许编造制度或产品承诺。",
        "至少完成 3 条制度/产品/流程问题试跑，并记录缺失知识。",
    ],
    "agent": {
        "name": "knowledge-qa-assistant",
        "display_name": "企业知识问答助手",
        "description": "基于企业知识库回答制度、产品、流程和交付规范问题。",
        "capabilities": ["knowledge_search"],
        "sort_order": 70,
        "engine_type": "LOCAL",
        "engine_config": {
            "scenario_template_id": "knowledge-qa-assistant",
            "scenario_category": "knowledge",
        },
    },
    "version": {
        "model_name": None,
        "temperature": 0.0,
        "system_prompt": (
            "你是企业知识问答助手，负责基于已授权知识库回答制度、产品、流程和交付规范问题。"
            "必须优先检索知识库并引用依据；如果资料不足，要明确说明缺口并建议补充知识。"
            "不要编造政策、价格、服务承诺或合同条款。"
        ),
        "tools": ["search_knowledge_base"],
        "skills_custom": False,
        "skills": [],
        "comment": "由场景模板一键交付生成",
    },
    "required_resources": [
        {
            "type": "knowledge_base",
            "name": "业务知识库",
            "required": True,
            "description": "建议绑定制度、产品手册、交付规范、FAQ 文档。",
        },
        {
            "type": "feedback",
            "name": "反馈纠错入口",
            "required": False,
            "description": "建议开启点赞点踩和问题反馈，用于发现知识缺口。",
        },
    ],
    "sample_questions": [
        "请说明售后服务响应时效要求。",
        "这个产品支持哪些部署方式？",
        "新员工报销流程是什么？",
    ],
    "next_steps": [
        "进入知识库管理上传制度、产品和流程文档。",
        "进入智能体中心检查知识检索工具是否启用。",
        "用样例问题试跑并记录找不到答案的知识缺口。",
    ],
}

OPS_INSPECTION_MANIFEST: Dict[str, Any] = {
    "id": "ops-inspection-assistant",
    "name": "运维巡检助手",
    "category": "运维",
    "description": "面向告警排查、巡检汇总、变更审计和通知推送的运维助手。",
    "tags": ["MCP", "API 工具", "巡检", "通知"],
    "recommended": False,
    "target_departments": ["运维中心", "安全运维", "客户成功"],
    "delivery_time": "1-2 天",
    "maturity": "增强版",
    "included_capabilities": ["Agent", "MCP 工具", "API 工具", "通知", "任务调度"],
    "deliverables": ["Agent", "工具配置", "巡检问题", "通知建议", "验收标准", "交付清单"],
    "business_goals": [
        "把高频巡检、告警查询和变更审计问题变成可复用的运维助手入口。",
        "通过 MCP/API 工具连接监控、工单或资产系统，减少人工跨系统查询。",
        "巡检结果可继续沉淀为定时任务和通知规则。",
    ],
    "install_steps": ["基础信息", "绑定资源", "预检", "安装发布"],
    "acceptance_criteria": [
        "巡检类问题必须优先调用已发布 MCP/API 工具或数据查询工具。",
        "风险结论要区分事实、推断和建议动作。",
        "至少完成 3 条告警/巡检/审计问题试跑，并确认通知渠道可用。",
    ],
    "agent": {
        "name": "ops-inspection-assistant",
        "display_name": "运维巡检助手",
        "description": "连接监控、资产、工单和通知工具，辅助完成巡检与告警排查。",
        "capabilities": ["tool_use", "data_query"],
        "sort_order": 60,
        "engine_type": "LOCAL",
        "engine_config": {
            "scenario_template_id": "ops-inspection-assistant",
            "scenario_category": "ops",
        },
    },
    "version": {
        "model_name": None,
        "temperature": 0.0,
        "system_prompt": (
            "你是运维巡检助手，负责协助查询告警、巡检指标、变更记录和工单信息。"
            "涉及真实系统状态时，必须优先调用工具获取证据；结论要区分事实、风险推断和建议动作。"
            "对于高风险操作只给建议，不直接执行破坏性动作。"
        ),
        "tools": ["execute_sql_query", "send_dingtalk_message", "send_wechat_work_message"],
        "skills_custom": False,
        "skills": [],
        "comment": "由场景模板一键交付生成",
    },
    "required_resources": [
        {
            "type": "mcp_tool",
            "name": "监控或资产工具",
            "required": True,
            "description": "建议绑定监控、资产、工单或变更系统的 MCP/API 工具。",
        },
        {
            "type": "notification",
            "name": "通知渠道",
            "required": False,
            "description": "建议配置钉钉或企业微信，用于巡检摘要和风险提醒。",
        },
    ],
    "sample_questions": [
        "查看昨天高压告警并按机房汇总。",
        "统计本周巡检异常并给出风险等级。",
        "查询最近 7 天变更审批记录并生成摘要。",
    ],
    "next_steps": [
        "进入系统配置或 MCP 管理发布监控、资产、工单工具。",
        "进入智能体中心确认工具权限和确认策略。",
        "用巡检样例试跑，稳定后配置定时任务和通知渠道。",
    ],
}


@dataclass(frozen=True)
class ScenarioTemplate:
    manifest: Dict[str, Any]

    @property
    def id(self) -> str:
        return self.manifest["id"]

    def summary(self) -> ScenarioTemplateSummary:
        return ScenarioTemplateSummary(
            id=self.manifest["id"],
            name=self.manifest["name"],
            category=self.manifest["category"],
            description=self.manifest["description"],
            tags=list(self.manifest.get("tags") or []),
            recommended=bool(self.manifest.get("recommended")),
            target_departments=list(self.manifest.get("target_departments") or []),
            delivery_time=self.manifest.get("delivery_time"),
            maturity=self.manifest.get("maturity"),
            included_capabilities=list(self.manifest.get("included_capabilities") or []),
            deliverables=list(self.manifest.get("deliverables") or []),
            business_goals=list(self.manifest.get("business_goals") or []),
            install_steps=list(self.manifest.get("install_steps") or []),
            acceptance_criteria=list(self.manifest.get("acceptance_criteria") or []),
            required_resources=[
                ScenarioTemplateResourceRequirement(**item)
                for item in self.manifest.get("required_resources", [])
            ],
            sample_questions=list(self.manifest.get("sample_questions") or []),
        )

    def detail(self) -> ScenarioTemplateDetail:
        data = self.summary().model_dump()
        data["manifest"] = self.manifest
        return ScenarioTemplateDetail(**data)


class ScenarioTemplateService:
    _templates = {
        manifest["id"]: ScenarioTemplate(manifest)
        for manifest in (
            CHATBI_BUSINESS_ANALYSIS_MANIFEST,
            KNOWLEDGE_QA_MANIFEST,
            OPS_INSPECTION_MANIFEST,
        )
    }

    @classmethod
    def list_templates(cls) -> List[ScenarioTemplateSummary]:
        return [template.summary() for template in cls._templates.values()]

    @classmethod
    def get_template(cls, template_id: str) -> ScenarioTemplate:
        template = cls._templates.get(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="场景模板不存在")
        return template

    @classmethod
    def _target_agent_name(
        cls,
        template: ScenarioTemplate,
        request: ScenarioTemplateInstallRequest,
    ) -> str:
        return request.instance_name or template.manifest["agent"]["name"]

    @classmethod
    def _actor_name(cls, user: Optional[Dict[str, Any]]) -> Optional[str]:
        if not user:
            return None
        return str(user.get("user_name") or user.get("username") or user.get("name") or user.get("id") or "") or None

    @classmethod
    def _selected_values(cls, request: ScenarioTemplateInstallRequest, resource_type: str) -> List[str]:
        raw = request.resource_bindings.get(resource_type)
        if raw is None:
            return []
        if isinstance(raw, list):
            values = raw
        else:
            values = [raw]
        return [str(item).strip() for item in values if str(item).strip()]

    @classmethod
    def _missing_required_resources(
        cls,
        template: ScenarioTemplate,
        request: ScenarioTemplateInstallRequest,
    ) -> List[ScenarioTemplateResourceRequirement]:
        missing: List[ScenarioTemplateResourceRequirement] = []
        for item in template.manifest.get("required_resources", []):
            requirement = ScenarioTemplateResourceRequirement(**item)
            if requirement.required and not cls._selected_values(request, requirement.type):
                missing.append(requirement)
        return missing

    @classmethod
    def _resource_label(cls, resource_type: str) -> str:
        return {
            "metadata_dataset": "元数据集",
            "knowledge_base": "知识库",
            "mcp_tool": "MCP 工具",
            "api_tool": "API 工具",
            "notification": "通知渠道",
            "feedback": "反馈能力",
        }.get(resource_type, resource_type)

    @classmethod
    def _agent_template_id(cls, agent: AIAgent) -> Optional[str]:
        config = agent.engine_config if isinstance(agent.engine_config, dict) else {}
        return config.get("scenario_template_id")

    @classmethod
    def _precheck_payload(cls, result: ScenarioTemplatePrecheckResponse) -> Dict[str, Any]:
        return result.model_dump(mode="json")

    @classmethod
    def _version_tools_with_resource_bindings(
        cls,
        version_manifest: Dict[str, Any],
        request: ScenarioTemplateInstallRequest,
    ) -> List[Any]:
        tools: List[Any] = list(version_manifest.get("tools") or [])
        metadata_dataset_ids = cls._selected_values(request, "metadata_dataset")
        if not metadata_dataset_ids:
            return tools

        configured: List[Any] = []
        for tool in tools:
            name = tool.get("name") if isinstance(tool, dict) else str(tool)
            if name == "get_dataset_schema" and metadata_dataset_ids:
                base = dict(tool) if isinstance(tool, dict) else {"name": name}
                base["metadata_dataset_ids"] = metadata_dataset_ids
                configured.append(base)
                continue
            configured.append(tool)
        return configured

    @classmethod
    def _engine_config_with_resource_bindings(
        cls,
        template: ScenarioTemplate,
        engine_config: Dict[str, Any],
        request: ScenarioTemplateInstallRequest,
    ) -> Dict[str, Any]:
        updated = dict(engine_config or {})
        updated["resource_bindings"] = request.resource_bindings

        template_resource_types = {
            item.get("type")
            for item in template.manifest.get("required_resources", [])
        }
        if "knowledge_base" in template_resource_types:
            knowledge_base_ids = cls._selected_values(request, "knowledge_base")
            if knowledge_base_ids:
                updated["dataset_ids"] = knowledge_base_ids
            else:
                updated.pop("dataset_ids", None)

        return updated

    @classmethod
    def _tool_names(cls, tools: List[Any]) -> List[str]:
        names: List[str] = []
        for tool in tools:
            name = tool.get("name") if isinstance(tool, dict) else str(tool)
            if name:
                names.append(name)
        return names

    @classmethod
    async def _resource_names(
        cls,
        session: AsyncSession,
        resource_type: str,
        values: List[str],
    ) -> List[str]:
        if not values:
            return []

        names_by_id: Dict[str, str] = {}
        if resource_type == "metadata_dataset":
            numeric_ids = [int(item) for item in values if str(item).isdigit()]
            if numeric_ids:
                rows = (
                    await session.execute(select(MetaDataset).where(MetaDataset.id.in_(numeric_ids)))
                ).scalars().all()
                names_by_id = {
                    str(row.id): (row.display_name or row.name or str(row.id))
                    for row in rows
                }
        elif resource_type == "knowledge_base":
            rows = (
                await session.execute(
                    select(KnowledgeBaseMetadata).where(KnowledgeBaseMetadata.ragflow_dataset_id.in_(values))
                )
            ).scalars().all()
            names_by_id = {
                str(row.ragflow_dataset_id): (row.name or str(row.ragflow_dataset_id))
                for row in rows
            }

        return [names_by_id.get(str(item), str(item)) for item in values]

    @classmethod
    async def _resource_summary(
        cls,
        session: AsyncSession,
        resource_bindings: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        summary: List[Dict[str, Any]] = []
        request = ScenarioTemplateInstallRequest(resource_bindings=resource_bindings or {})
        for resource_type in (resource_bindings or {}).keys():
            if resource_type == "owner":
                continue
            values = cls._selected_values(request, resource_type)
            if not values:
                continue
            summary.append(
                {
                    "type": resource_type,
                    "label": cls._resource_label(resource_type),
                    "count": len(values),
                    "ids": values,
                    "names": await cls._resource_names(session, resource_type, values),
                }
            )
        return summary

    @classmethod
    async def resource_options(
        cls,
        session: AsyncSession,
        template_id: str,
    ) -> ScenarioTemplateResourceOptionsResponse:
        template = cls.get_template(template_id)
        needed_types = {item.get("type") for item in template.manifest.get("required_resources", [])}
        options: Dict[str, List[ScenarioTemplateResourceOption]] = {}

        if "metadata_dataset" in needed_types:
            rows = (
                await session.execute(
                    select(MetaDataset)
                    .where(MetaDataset.status == 1)
                    .order_by(MetaDataset.updated_at.desc())
                    .limit(50)
                )
            ).scalars().all()
            options["metadata_dataset"] = [
                ScenarioTemplateResourceOption(
                    id=str(row.id),
                    name=row.name,
                    label=row.display_name or row.name,
                    description=row.description,
                    status="enabled",
                    meta={"data_source": row.data_source},
                )
                for row in rows
            ]

        if "knowledge_base" in needed_types:
            rows = (
                await session.execute(
                    select(KnowledgeBaseMetadata)
                    .where(KnowledgeBaseMetadata.status != "deleted")
                    .order_by(KnowledgeBaseMetadata.updated_at.desc())
                    .limit(50)
                )
            ).scalars().all()
            options["knowledge_base"] = [
                ScenarioTemplateResourceOption(
                    id=row.ragflow_dataset_id,
                    name=row.name,
                    label=row.name,
                    description=row.description,
                    status=row.status,
                    meta={"owner": row.owner, "visibility": row.visibility},
                )
                for row in rows
            ]

        if "mcp_tool" in needed_types:
            rows = (
                await session.execute(
                    select(McpToolCache)
                    .where(McpToolCache.is_published == True)  # noqa: E712
                    .order_by(McpToolCache.updated_at.desc())
                    .limit(50)
                )
            ).scalars().all()
            options["mcp_tool"] = [
                ScenarioTemplateResourceOption(
                    id=row.id,
                    name=row.tool_name,
                    label=row.tool_name,
                    description=row.tool_description,
                    status="published",
                    meta={"server_id": row.server_id},
                )
                for row in rows
            ]

        if "api_tool" in needed_types:
            rows = (
                await session.execute(
                    select(SysApiTool)
                    .where(SysApiTool.is_active == True)  # noqa: E712
                    .order_by(SysApiTool.updated_at.desc())
                    .limit(50)
                )
            ).scalars().all()
            options["api_tool"] = [
                ScenarioTemplateResourceOption(
                    id=row.id,
                    name=row.name,
                    label=row.name,
                    description=row.description,
                    status="active",
                    meta={"method": row.method},
                )
                for row in rows
            ]

        if "notification" in needed_types:
            options["notification"] = [
                ScenarioTemplateResourceOption(
                    id="dingtalk",
                    name="dingtalk",
                    label="钉钉通知",
                    description="用于交付巡检摘要、风险提醒和待办。",
                    status="available",
                ),
                ScenarioTemplateResourceOption(
                    id="wechat_work",
                    name="wechat_work",
                    label="企业微信通知",
                    description="用于团队群消息和个人提醒。",
                    status="available",
                ),
            ]

        if "feedback" in needed_types:
            options["feedback"] = [
                ScenarioTemplateResourceOption(
                    id="chat_feedback",
                    name="chat_feedback",
                    label="对话点赞点踩与反馈",
                    description="使用平台内置反馈入口发现知识缺口。",
                    status="available",
                )
            ]

        return ScenarioTemplateResourceOptionsResponse(template_id=template.id, options=options)

    @classmethod
    async def list_instances(cls, session: AsyncSession) -> List[ScenarioTemplateInstanceSummary]:
        instances = (
            await session.execute(
                select(ScenarioTemplateInstance).order_by(ScenarioTemplateInstance.updated_at.desc())
            )
        ).scalars().all()
        if not instances:
            return []

        instance_ids = [item.id for item in instances]
        runs = (
            await session.execute(
                select(ScenarioTemplateInstallRun)
                .where(ScenarioTemplateInstallRun.instance_id.in_(instance_ids))
                .order_by(ScenarioTemplateInstallRun.created_at.desc())
            )
        ).scalars().all()
        latest_run_by_instance: Dict[str, ScenarioTemplateInstallRun] = {}
        for run in runs:
            if run.instance_id and run.instance_id not in latest_run_by_instance:
                latest_run_by_instance[run.instance_id] = run

        result: List[ScenarioTemplateInstanceSummary] = []
        for instance in instances:
            latest_run = latest_run_by_instance.get(instance.id)
            template = cls._templates.get(instance.template_id)
            result.append(
                ScenarioTemplateInstanceSummary(
                    id=instance.id,
                    template_id=instance.template_id,
                    template_name=instance.template_name,
                    status=instance.status,
                    owner=instance.owner,
                    agent={
                        "id": instance.agent_id,
                        "name": instance.agent_name,
                        "display_name": instance.display_name,
                    },
                    latest_run={
                        "id": latest_run.id,
                        "status": latest_run.status,
                        "version_id": (latest_run.install_result or {}).get("version_id"),
                    } if latest_run else None,
                    resource_summary=await cls._resource_summary(session, instance.resource_bindings or {}),
                    acceptance_criteria=list(instance.acceptance_criteria or []),
                    sample_questions=list(template.manifest.get("sample_questions") or []) if template else [],
                    next_steps=list(instance.next_steps or []),
                )
            )
        return result

    @classmethod
    async def get_instance_install_result(
        cls,
        session: AsyncSession,
        instance_id: str,
    ) -> ScenarioTemplateInstallResponse:
        instance = (
            await session.execute(
                select(ScenarioTemplateInstance).where(ScenarioTemplateInstance.id == instance_id)
            )
        ).scalar_one_or_none()
        if not instance:
            raise HTTPException(status_code=404, detail="场景交付实例不存在")

        latest_run = (
            await session.execute(
                select(ScenarioTemplateInstallRun)
                .where(ScenarioTemplateInstallRun.instance_id == instance.id)
                .order_by(ScenarioTemplateInstallRun.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        install_payload = latest_run.install_result if latest_run and isinstance(latest_run.install_result, dict) else {}
        version_id = install_payload.get("version_id")
        version = None
        if version_id:
            version = (
                await session.execute(
                    select(AIAgentVersion).where(AIAgentVersion.id == version_id)
                )
            ).scalar_one_or_none()

        template = cls._templates.get(instance.template_id)
        resource_bindings = instance.resource_bindings or {}
        return ScenarioTemplateInstallResponse(
            template_id=instance.template_id,
            created=bool(install_payload.get("created")),
            instance={
                "id": instance.id,
                "status": instance.status,
                "template_name": instance.template_name,
                "owner": instance.owner,
            },
            run={
                "id": latest_run.id if latest_run else "",
                "status": latest_run.status if latest_run else "unknown",
            },
            agent={
                "id": instance.agent_id,
                "name": instance.agent_name,
                "display_name": instance.display_name,
                "description": None,
            },
            version={
                "id": version.id if version else version_id,
                "version_number": version.version_number if version else 0,
                "status": version.status if version else "UNKNOWN",
            },
            resource_bindings=resource_bindings,
            missing_resources=list(instance.missing_resources or []),
            next_steps=list(instance.next_steps or []),
            enabled_tools=cls._tool_names(list(version.tools or [])) if version else [],
            sample_questions=list(template.manifest.get("sample_questions") or []) if template else [],
            resource_summary=await cls._resource_summary(session, resource_bindings),
        )

    @classmethod
    async def precheck(
        cls,
        session: AsyncSession,
        template_id: str,
        request: ScenarioTemplateInstallRequest,
    ) -> ScenarioTemplatePrecheckResponse:
        template = cls.get_template(template_id)
        target_name = cls._target_agent_name(template, request)

        existing = (
            await session.execute(select(AIAgent).where(AIAgent.name == target_name))
        ).scalar_one_or_none()
        checks: List[ScenarioTemplatePrecheckItem] = []
        can_install = True

        if existing:
            existing_template_id = cls._agent_template_id(existing)
            if existing_template_id != template.id:
                can_install = False
                checks.append(
                    ScenarioTemplatePrecheckItem(
                        key="agent_name",
                        label="智能体实例",
                        status="error",
                        message=(
                            f"实例标识 {target_name} 已被其他智能体占用，不能作为当前模板交付目标。"
                            "请更换实例标识，或先在智能体中心确认归属。"
                        ),
                    )
                )
            else:
                checks.append(
                    ScenarioTemplatePrecheckItem(
                        key="agent_name",
                        label="智能体实例",
                        status="warning",
                        message=f"将复用当前模板已安装的智能体 {target_name}。",
                    )
                )
        else:
            checks.append(
                ScenarioTemplatePrecheckItem(
                    key="agent_name",
                    label="智能体实例",
                    status="success",
                    message=f"将创建智能体 {target_name}。",
                )
            )

        checks.append(
            ScenarioTemplatePrecheckItem(
                key="tools",
                label="工具配置",
                status="success",
                message=f"将启用模板内置工具：{', '.join(template.manifest['version'].get('tools') or [])}。",
            )
        )

        missing = cls._missing_required_resources(template, request)
        if missing:
            can_install = False
            checks.append(
                ScenarioTemplatePrecheckItem(
                    key="resources",
                    label="资源绑定",
                    status="error",
                    message="缺少必选资源：" + "、".join(item.name for item in missing),
                )
            )
        else:
            bound_required = [
                cls._resource_label(item["type"])
                for item in template.manifest.get("required_resources", [])
                if item.get("required")
            ]
            checks.append(
                ScenarioTemplatePrecheckItem(
                    key="resources",
                    label="资源绑定",
                    status="success",
                    message=(
                        "必选资源已绑定：" + "、".join(bound_required)
                        if bound_required
                        else "当前模板没有必选资源。"
                    ),
                )
            )

        return ScenarioTemplatePrecheckResponse(
            template_id=template.id,
            target_agent_name=target_name,
            can_install=can_install,
            checks=checks,
        )

    @classmethod
    async def install(
        cls,
        session: AsyncSession,
        template_id: str,
        request: ScenarioTemplateInstallRequest,
        user: Optional[Dict[str, Any]] = None,
    ) -> ScenarioTemplateInstallResponse:
        template = cls.get_template(template_id)
        precheck = await cls.precheck(session, template_id, request)
        actor = cls._actor_name(user)
        if not precheck.can_install:
            run = ScenarioTemplateInstallRun(
                id=str(uuid.uuid4()),
                template_id=template.id,
                agent_id=None,
                status="blocked",
                precheck_result=cls._precheck_payload(precheck),
                error_message="场景模板预检未通过",
                created_by=actor,
            )
            session.add(run)
            await session.flush()
            await session.commit()
            raise HTTPException(status_code=400, detail="场景模板预检未通过，请先补齐必选资源或处理同名冲突")

        target_name = cls._target_agent_name(template, request)
        manifest = template.manifest
        agent_manifest = dict(manifest["agent"])
        version_manifest = dict(manifest["version"])
        version_manifest["tools"] = cls._version_tools_with_resource_bindings(version_manifest, request)

        existing = (
            await session.execute(select(AIAgent).where(AIAgent.name == target_name))
        ).scalar_one_or_none()
        created = existing is None

        if existing:
            agent = existing
            engine_config = dict(agent.engine_config or {})
            engine_config["scenario_template_id"] = template.id
            engine_config["scenario_category"] = agent_manifest.get("engine_config", {}).get("scenario_category")
            engine_config = cls._engine_config_with_resource_bindings(template, engine_config, request)
            agent.engine_config = engine_config
            agent.display_name = request.display_name or agent.display_name
            agent.description = request.description or agent.description
        else:
            engine_config = dict(agent_manifest.get("engine_config") or {})
            engine_config = cls._engine_config_with_resource_bindings(template, engine_config, request)
            agent = await AgentManagerService.create_agent(
                session,
                AIAgentBase(
                    name=target_name,
                    display_name=request.display_name or agent_manifest["display_name"],
                    description=request.description or agent_manifest.get("description"),
                    capabilities=list(agent_manifest.get("capabilities") or []),
                    is_system=False,
                    sort_order=agent_manifest.get("sort_order", 0),
                    is_enabled=True,
                    engine_type=agent_manifest.get("engine_type", "LOCAL"),
                    engine_config=engine_config,
                ),
                user=user,
            )

        version = await cls._ensure_published_version(
            session,
            agent,
            version_manifest,
            user=user,
            publish=request.publish,
        )
        missing_resources = cls._missing_required_resources(template, request)
        status = "installed" if not missing_resources else "needs_resources"
        instance = (
            await session.execute(
                select(ScenarioTemplateInstance).where(
                    ScenarioTemplateInstance.template_id == template.id,
                    ScenarioTemplateInstance.agent_id == agent.id,
                )
            )
        ).scalar_one_or_none()
        if instance:
            instance.agent_name = agent.name
            instance.display_name = agent.display_name
            instance.owner = request.resource_bindings.get("owner") if request.resource_bindings else None
            instance.status = status
            instance.resource_bindings = request.resource_bindings
            instance.missing_resources = [item.model_dump(mode="json") for item in missing_resources]
            instance.deliverables = list(manifest.get("deliverables") or [])
            instance.acceptance_criteria = list(manifest.get("acceptance_criteria") or [])
            instance.next_steps = list(manifest.get("next_steps") or [])
            instance.updated_by = actor
        else:
            instance = ScenarioTemplateInstance(
                id=str(uuid.uuid4()),
                template_id=template.id,
                template_name=template.manifest["name"],
                agent_id=agent.id,
                agent_name=agent.name,
                display_name=agent.display_name,
                owner=request.resource_bindings.get("owner") if request.resource_bindings else None,
                status=status,
                resource_bindings=request.resource_bindings,
                missing_resources=[item.model_dump(mode="json") for item in missing_resources],
                deliverables=list(manifest.get("deliverables") or []),
                acceptance_criteria=list(manifest.get("acceptance_criteria") or []),
                next_steps=list(manifest.get("next_steps") or []),
                created_by=actor,
                updated_by=actor,
            )
            session.add(instance)

        result_payload = {
            "agent_id": agent.id,
            "version_id": version.id,
            "created": created,
            "status": status,
        }
        run = ScenarioTemplateInstallRun(
            id=str(uuid.uuid4()),
            instance_id=instance.id,
            template_id=template.id,
            agent_id=agent.id,
            status="success",
            precheck_result=cls._precheck_payload(precheck),
            install_result=result_payload,
            created_by=actor,
        )
        session.add(run)
        await session.flush()

        return ScenarioTemplateInstallResponse(
            template_id=template.id,
            created=created,
            instance={
                "id": instance.id,
                "status": instance.status,
                "template_name": instance.template_name,
                "owner": instance.owner,
            },
            run={
                "id": run.id,
                "status": run.status,
            },
            agent={
                "id": agent.id,
                "name": agent.name,
                "display_name": agent.display_name,
                "description": agent.description,
            },
            version={
                "id": version.id,
                "version_number": version.version_number,
                "status": version.status,
            },
            resource_bindings=request.resource_bindings,
            missing_resources=missing_resources,
            next_steps=list(manifest.get("next_steps") or []),
            enabled_tools=cls._tool_names(version_manifest.get("tools") or []),
            sample_questions=list(manifest.get("sample_questions") or []),
            resource_summary=await cls._resource_summary(session, request.resource_bindings),
        )

    @classmethod
    async def _ensure_published_version(
        cls,
        session: AsyncSession,
        agent: AIAgent,
        version_manifest: Dict[str, Any],
        user: Optional[Dict[str, Any]],
        publish: bool,
    ) -> AIAgentVersion:
        existing = (
            await session.execute(
                select(AIAgentVersion)
                .where(
                    AIAgentVersion.agent_id == agent.id,
                    AIAgentVersion.status == "PUBLISHED",
                )
                .order_by(AIAgentVersion.version_number.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing:
            return existing

        version = await AgentManagerService.create_agent_version(
            session,
            agent.id,
            AIAgentVersionBase(
                model_name=version_manifest.get("model_name"),
                temperature=version_manifest.get("temperature", 0.0),
                synthesis_model_name=version_manifest.get("synthesis_model_name"),
                synthesis_temperature=version_manifest.get("synthesis_temperature"),
                system_prompt=version_manifest["system_prompt"],
                tools=list(version_manifest.get("tools") or []),
                skills_custom=bool(version_manifest.get("skills_custom", False)),
                skills=list(version_manifest.get("skills") or []),
                comment=version_manifest.get("comment"),
            ),
            user=user,
        )
        if not version:
            raise HTTPException(status_code=403, detail="无法为智能体创建模板版本")
        if publish:
            ok = await AgentManagerService.publish_version(session, agent.id, version.id, user=user)
            if not ok:
                raise HTTPException(status_code=403, detail="无法发布模板版本")
            refreshed = await session.get(AIAgentVersion, version.id)
            if refreshed:
                return refreshed
        return version
