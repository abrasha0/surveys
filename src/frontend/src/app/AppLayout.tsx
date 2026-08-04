import { useProcessingStatus } from '../api/hooks';
import ProcessingProgressBar from '../features/verification/ProcessingProgressBar';
import VerificationPanel from '../features/verification/VerificationPanel';

export default function AppLayout() {
  const { data: processingStatus, isLoading: statusLoading } = useProcessingStatus();

  return (
    <div className="flex flex-col h-screen">
      <ProcessingProgressBar
        status={processingStatus}
        isLoading={statusLoading}
      />
      <main className="flex-1 flex overflow-hidden">
        <VerificationPanel />
      </main>
    </div>
  );
}