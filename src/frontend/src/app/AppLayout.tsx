import { useProcessingStatus, useStartProcessing } from '../api/hooks';
import ProcessingProgressBar from '../features/verification/ProcessingProgressBar';
import VerificationPanel from '../features/verification/VerificationPanel';

export default function AppLayout() {
  const { data: processingStatus, isLoading: statusLoading } = useProcessingStatus();
  const startMutation = useStartProcessing();

  return (
    <div className="flex flex-col h-screen">
      <ProcessingProgressBar
        status={processingStatus}
        isLoading={statusLoading}
        onStart={() => startMutation.mutate()}
        isStarting={startMutation.isPending}
      />
      <main className="flex-1 flex overflow-hidden">
        <VerificationPanel />
      </main>
    </div>
  );
}
