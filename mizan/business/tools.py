"""Permissioned tools used by the Ramadan retail AUT in explicit Sandbox mode."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from mizan.business.repository import SandboxRepository
from mizan.core.contracts import ErrorCode, ErrorRecord, ToolRequest, ToolResponse
from mizan.services.pii_engine import PIIEngine
from mizan.services.vector_store import VectorStore


class ToolPermissionDenied(PermissionError):
    """Raised when an agent tries to exceed its explicitly allowed tool set."""


class TypedToolFailure(Exception):
    """Expected, observable tool failure that preserves its error classification."""

    def __init__(self, error: ErrorRecord):
        self.error = error
        super().__init__(error.message)


class ToolGateway:
    """Audited tool gateway; agents never receive repository access directly."""

    _PERMISSIONS: dict[str, set[str]] = {
        "CampaignCommander": {"create_tasks", "request_approval", "campaign_state"},
        "ContentArchitect": {"product_search", "content_compliance_check"},
        "ComplianceGuardian": {"pii_redaction", "consent_check", "content_compliance_check"},
        "ChannelDeployer": {"channel_deployment"},
        "CustomerEngagement": {"customer_memory"},
        "AnalyticsEngine": {"campaign_analytics"},
    }

    def __init__(self, repository: SandboxRepository):
        self.repository = repository

    def _authorize(self, request: ToolRequest) -> None:
        allowed = self._PERMISSIONS.get(request.agent_id, set())
        if request.tool_name not in allowed:
            raise ToolPermissionDenied(f"{request.agent_id} cannot invoke {request.tool_name}")

    @staticmethod
    def _sanitize(value: Any) -> Any:
        if isinstance(value, str):
            return PIIEngine.redact(value)[0]
        if isinstance(value, dict):
            return {str(key): ToolGateway._sanitize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [ToolGateway._sanitize(item) for item in value]
        return value

    def _execute(self, request: ToolRequest, operation: Callable[[], dict[str, Any]]) -> ToolResponse:
        started = time.perf_counter()
        try:
            self._authorize(request)
            result = operation()
            response = ToolResponse(
                request_id=request.request_id,
                success=True,
                result=result,
                duration_ms=(time.perf_counter() - started) * 1_000,
            )
        except TypedToolFailure as exc:
            response = ToolResponse(
                request_id=request.request_id,
                success=False,
                error=exc.error,
                duration_ms=(time.perf_counter() - started) * 1_000,
            )
        except ToolPermissionDenied as exc:
            response = ToolResponse(
                request_id=request.request_id,
                success=False,
                error=ErrorRecord(code=ErrorCode.PERMISSION_DENIED, message=str(exc)),
                duration_ms=(time.perf_counter() - started) * 1_000,
            )
        except LookupError:
            response = ToolResponse(
                request_id=request.request_id,
                success=False,
                error=ErrorRecord(code=ErrorCode.VALIDATION_ERROR, message="Scoped business record was not found"),
                duration_ms=(time.perf_counter() - started) * 1_000,
            )
        except ValueError as exc:
            response = ToolResponse(
                request_id=request.request_id,
                success=False,
                error=ErrorRecord(code=ErrorCode.VALIDATION_ERROR, message=str(exc)),
                duration_ms=(time.perf_counter() - started) * 1_000,
            )

        self.repository.record_tool_call(
            run_id=str(request.run_id),
            company_id=request.tenant.company_id,
            campaign_id=request.campaign_id,
            task_id=request.task_id,
            agent_id=request.agent_id,
            tool_name=request.tool_name,
            success=response.success,
            duration_ms=response.duration_ms,
            error_code=response.error.code.value if response.error else None,
            input_payload=self._sanitize(request.arguments),
            output_payload=self._sanitize(response.result if response.success else response.error.model_dump()),
        )
        return response

    def create_tasks(self, request: ToolRequest) -> ToolResponse:
        def operation() -> dict[str, Any]:
            tasks = request.arguments["tasks"]
            for task in tasks:
                self.repository.create_task(
                    request.tenant.company_id,
                    request.campaign_id,
                    str(task["task_id"]),
                    str(task["agent_id"]),
                    dict(task.get("payload", {})),
                )
            return {"task_count": len(tasks)}

        return self._execute(request, operation)

    def product_search(self, request: ToolRequest) -> ToolResponse:
        def operation() -> dict[str, Any]:
            query = str(request.arguments["query"])
            products = self.repository.list_products(request.tenant.company_id)
            if not products:
                raise LookupError("No company catalog exists")
            store = VectorStore()
            store.index_products(products)
            matches = store.search(query, top_k=int(request.arguments.get("top_k", 3)))
            return {"products": matches}

        return self._execute(request, operation)

    def redact_pii(self, request: ToolRequest) -> ToolResponse:
        def operation() -> dict[str, Any]:
            redacted, audit = PIIEngine.redact(str(request.arguments["text"]), jurisdiction=str(request.arguments["jurisdiction"]))
            return {"redacted_text": redacted, "pii_counts": audit["pii_counts"], "total_redactions": audit["total_redactions"]}

        return self._execute(request, operation)

    def check_consent(self, request: ToolRequest) -> ToolResponse:
        def operation() -> dict[str, Any]:
            customer_id = str(request.arguments["customer_id"])
            market, consent_status = self.repository.get_customer_consent(request.tenant.company_id, customer_id)
            allowed = consent_status == "opted_in"
            jurisdiction = "KSA_PDPL" if market == "KSA" else "EG_LAW_151"
            self.repository.append_consent_audit(
                request.tenant.company_id,
                request.campaign_id,
                customer_id,
                "communication_authorized" if allowed else "communication_blocked_no_consent",
                jurisdiction,
                {"channel": request.arguments["channel"], "consent_status": consent_status},
            )
            return {"customer_id": customer_id, "allowed": allowed, "jurisdiction": jurisdiction}

        return self._execute(request, operation)

    def request_approval(self, request: ToolRequest) -> ToolResponse:
        def operation() -> dict[str, Any]:
            approval_id = self.repository.create_approval(
                request.tenant.company_id,
                request.campaign_id,
                request.task_id,
                str(request.arguments["requested_action"]),
                str(request.arguments["risk"]),
                str(request.arguments["required_role"]),
                request.agent_id,
                str(request.arguments["reason"]),
            )
            return {"approval_id": approval_id, "status": "pending"}

        return self._execute(request, operation)

    def deploy_channel(self, request: ToolRequest) -> ToolResponse:
        """Explicit sandbox adapter; no external provider API is called here."""

        def operation() -> dict[str, Any]:
            if request.tenant.execution_mode.value != "sandbox":
                raise ValueError("This adapter is available only in sandbox mode")
            channel = str(request.arguments["channel"])
            attempt = int(request.arguments["attempt"])
            fallback_from = request.arguments.get("fallback_from")
            key = f"{request.idempotency_key}:{channel}:{attempt}"

            if channel == "snapchat" and attempt == 1:
                self.repository.record_deployment(
                    request.tenant.company_id, request.campaign_id, channel, attempt, "sandbox_rate_limited", key,
                    error_code=ErrorCode.RATE_LIMIT.value,
                )
                raise TypedToolFailure(
                    ErrorRecord(
                        code=ErrorCode.RATE_LIMIT,
                        message="Sandbox channel adapter injected a rate-limit response",
                        retryable=True,
                        retry_after_seconds=1,
                    )
                )
            if channel == "whatsapp":
                self.repository.record_deployment(
                    request.tenant.company_id, request.campaign_id, channel, attempt, "sandbox_template_rejected", key,
                    error_code=ErrorCode.TOOL_ERROR.value,
                )
                raise TypedToolFailure(
                    ErrorRecord(
                        code=ErrorCode.TOOL_ERROR,
                        message="Sandbox channel adapter injected a template rejection",
                        retryable=False,
                    )
                )

            self.repository.record_deployment(
                request.tenant.company_id, request.campaign_id, channel, attempt, "sandbox_accepted", key,
                fallback_from=str(fallback_from) if fallback_from else None,
            )
            return {"channel": channel, "attempt": attempt, "status": "sandbox_accepted", "external_dispatch": False}

        return self._execute(request, operation)

    def campaign_analytics(self, request: ToolRequest) -> ToolResponse:
        def operation() -> dict[str, Any]:
            spend = float(request.arguments["spend"])
            revenue = float(request.arguments["revenue"])
            clicks = float(request.arguments["clicks"])
            impressions = float(request.arguments["impressions"])
            conversions = float(request.arguments["conversions"])
            if spend <= 0 or impressions <= 0 or conversions <= 0:
                raise ValueError("Spend, impressions, and conversions must be positive")
            metrics = {
                "roas": revenue / spend,
                "cpa": spend / conversions,
                "ctr": clicks / impressions,
                "conversion_rate": conversions / clicks if clicks else 0.0,
                "cost": spend,
                "revenue": revenue,
            }
            self.repository.record_metrics(request.tenant.company_id, request.campaign_id, metrics)
            return {"metrics": metrics}

        return self._execute(request, operation)

    def customer_memory(self, request: ToolRequest) -> ToolResponse:
        def operation() -> dict[str, Any]:
            customer_id = str(request.arguments["customer_id"])
            key = str(request.arguments["key"])
            value = request.arguments.get("value")
            if value is not None:
                self.repository.save_customer_memory(request.tenant.company_id, customer_id, key, str(value))
            memory = self.repository.get_customer_memory(request.tenant.company_id, customer_id)
            return {"customer_id": customer_id, "memory": memory}

        return self._execute(request, operation)
