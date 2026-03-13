from datetime import timedelta

from temporalio import workflow

from ..activities.be_deployer import deploy_backend_artifacts


@workflow.defn(sandboxed=False)
class BeWorkspaceDeployWorkflow:
    """
    Workflow chuyên trách việc đưa backend artifacts vào workspace/repo đích.

    Workflow này được tách riêng khỏi `BeCodeGenerationWorkflow` để đảm bảo:
    - workflow sinh code luôn có thể hoàn tất và trả về ZIP export,
    - lỗi ở bước triển khai vào workspace không làm fail toàn bộ quy trình sinh mã,
    - trạng thái deploy có thể được theo dõi độc lập bằng workflow ID riêng.
    """

    @workflow.run
    async def run(self, artifacts, kw=None):
        """
        Chạy activity deploy duy nhất cho toàn bộ batch artifact backend.

        - `artifacts`: danh sách artifact đã sinh từ workflow backend chính.
        - `kw`: cấu hình phụ truyền xuyên suốt từ request gốc.

        Trả về trực tiếp kết quả của activity `deploy_backend_artifacts`.
        """
        return await workflow.execute_activity(
            deploy_backend_artifacts,
            args=[artifacts, kw or {}],
            start_to_close_timeout=timedelta(minutes=5),
        )
