from core.ports.human_approval_port import (
    HumanApprovalPort,
    ApprovalRequest,
    ApprovalResponse,
)


class AutoApproveAdapter(HumanApprovalPort):

    async def request_approval(
        self, request: ApprovalRequest
    ) -> ApprovalResponse:
        print(f"[AUTO-APPROVE] Gate: {request.gate_name}")
        print(f"[AUTO-APPROVE] Description: {request.description}")
        print(f"[AUTO-APPROVE] ✅ Approved automatically")
        return ApprovalResponse(
            approved=True,
            reviewer="auto_approver",
            feedback="Auto-approved for testing",
        )
