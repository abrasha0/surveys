import { useMemo, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import {
  useClearSession,
  useExportCsv,
  useProcessingStatus,
  useStartProcessing,
  useSurveys,
} from '../../api/hooks';
import { useVerificationStore } from '../../store/verificationStore';

function formatEta(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '-';
  if (seconds <= 0) return 'Zakończono';
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return mins > 0 ? `~${mins} min ${secs} s` : `~${secs} s`;
}

export default function WelcomePage() {
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const { data: surveys } = useSurveys();
  const { data: processingStatus } = useProcessingStatus();
  const startProcessing = useStartProcessing();
  const clearSession = useClearSession();
  const exportCsv = useExportCsv();
  const clearCache = useVerificationStore((s) => s.clearAllCache);

  const isRunning = processingStatus?.is_running ?? false;

  const stats = useMemo(() => {
    const list = surveys ?? [];
    const status = processingStatus;
    const done = list.filter(
      (s) => s.status === 'ready' || s.status === 'error' || s.status === 'verified'
    );
    return {
      total: list.length,
      processed: done.length,
      verified: list.filter((s) => s.status === 'verified').length,
      processedPages:
        status?.processed_pages ??
        done.reduce((acc, s) => acc + s.files.length, 0),
      errors: status?.errors ?? 0,
    };
  }, [surveys, processingStatus]);

  if (processingStatus === undefined || surveys === undefined) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-info)]" />
      </div>
    );
  }

  if (isRunning) {
    return <Navigate to="/app" replace />;
  }

  const readyCount = surveys.filter((s) => s.status === 'ready').length;
  const isCovered = stats.total > 0 && stats.processed === stats.total;
  const allVerified = isCovered && stats.verified === stats.total;
  const showEta = stats.total > 0;
  const etaText = formatEta(processingStatus?.eta_seconds);
  const etaLabel = 'Czas przetwarzania';
  const remainingPages = (processingStatus?.total_pages ?? stats.processedPages) - stats.processedPages;

  const handleStart = () => {
    setError('');
    startProcessing.mutate(undefined, {
      onSuccess: () => navigate('/app'),
      onError: (err) => {
        if (err instanceof Error) setError(err.message);
      },
    });
  };

  const handleRestart = () => {
    setError('');
    clearCache();
    clearSession.mutate(undefined, {
      onSuccess: () => {
        startProcessing.mutate(undefined, {
          onSuccess: () => navigate('/app'),
          onError: (err) => {
            if (err instanceof Error) setError(err.message);
          },
        });
      },
      onError: (err) => {
        if (err instanceof Error) setError(err.message);
      },
    });
  };

  const handleCsv = () => {
    setError('');
    exportCsv.mutate(undefined, {
      onError: (err) => {
        if (err instanceof Error) setError(err.message);
      },
    });
  };

  const busy = startProcessing.isPending || clearSession.isPending;

  const statsBlock = (
    <div className="space-y-2 text-sm mb-2">
      <div className="flex justify-between">
        <span className="text-gray-500">Wszystkie ankiety</span>
        <span className="font-medium">{stats.total}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-gray-500">Przeprocesowane</span>
        <span className="font-medium">
          {stats.processed} ({stats.processedPages} zdjęć)
        </span>
      </div>
      {remainingPages > 0 && (
        <div className="flex justify-between">
          <span className="text-gray-500">Pozostało do przeprocesowania</span>
          <span className="font-medium">{remainingPages} zdjęć</span>
        </div>
      )}
      <div className="flex justify-between">
        <span className="text-gray-500">Zweryfikowane</span>
        <span className="font-medium">{stats.verified}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-gray-500">Błędy</span>
        <span className="font-medium">{stats.errors}</span>
      </div>
    </div>
  );

  const etaBlock = showEta && (
    <div className="flex justify-between text-sm mb-2">
      <span className="text-gray-500">{etaLabel}</span>
      <span className="font-medium">{etaText}</span>
    </div>
  );

  const primaryButtonClass =
    'w-full py-3 px-6 text-base bg-[var(--color-info)] text-white ' +
    'rounded-md hover:opacity-90 disabled:opacity-50 font-medium transition-opacity mt-6';

  return (
    <div className="flex items-center justify-center h-screen bg-gray-50">
      <div className="w-full max-w-sm bg-white rounded-lg shadow-md p-8">
        <h1 className="text-2xl font-bold text-center mb-1">AnkieterAI</h1>
        <p className="text-gray-500 text-center text-sm mb-6">
          System wprowadzania ankiet papierowych
        </p>

        {stats.total === 0 && (
          <p className="text-center text-gray-500">Brak ankiet w katalogu.</p>
        )}

        {stats.total > 0 && stats.processed === 0 && (
          <>
            <p className="text-center text-gray-600 mb-6">
              Znaleziono {stats.total} ankiet. Rozpocznij analizę, aby wygenerować wyniki.
            </p>
            {statsBlock}
            <button onClick={handleStart} disabled={busy} className={primaryButtonClass}>
              {startProcessing.isPending ? 'Rozpoczynanie...' : 'Rozpocznij analizę'}
            </button>
          </>
        )}

        {stats.total > 0 && stats.processed > 0 && !isCovered && (
          <>
            {statsBlock}
            {etaBlock}
            <button onClick={handleStart} disabled={busy} className={primaryButtonClass}>
              {startProcessing.isPending ? 'Kontynuowanie...' : 'Kontynuuj analizę'}
            </button>
          </>
        )}

        {isCovered && (
          <>
            <h2 className="text-lg font-semibold text-center mb-4">
              Wszystkie ankiety przeprocesowane
            </h2>
            {statsBlock}
            {etaBlock}
            <div className="flex flex-col gap-3 mt-6">
              {allVerified || readyCount === 0 ? (
                <button
                  onClick={() => navigate('/complete')}
                  className="w-full py-3 px-6 text-base bg-[var(--color-info)] text-white
                             rounded-md hover:opacity-90 font-medium transition-opacity"
                >
                  Pobierz wyniki
                </button>
              ) : (
                <button
                  onClick={() => navigate('/app')}
                  className="w-full py-3 px-6 text-base bg-[var(--color-info)] text-white
                             rounded-md hover:opacity-90 font-medium transition-opacity"
                >
                  Przejdź do weryfikacji
                </button>
              )}
              <div className="flex gap-3">
                <button
                  onClick={handleCsv}
                  disabled={exportCsv.isPending}
                  className="flex-1 py-2 px-4 text-sm text-gray-700 bg-white border border-gray-300
                             rounded-md hover:bg-gray-50 font-medium transition-colors
                             disabled:opacity-50"
                >
                  {exportCsv.isPending ? 'Pobieranie...' : 'Pobierz CSV'}
                </button>
                <button
                  onClick={handleRestart}
                  disabled={busy}
                  className="flex-1 py-2 px-4 text-sm text-gray-700 bg-white border border-gray-300
                             rounded-md hover:bg-gray-50 font-medium transition-colors
                             disabled:opacity-50"
                >
                  {busy ? 'Uruchamianie...' : 'Rozpocznij od nowa'}
                </button>
              </div>
            </div>
          </>
        )}

        {error && (
          <div className="mt-4 text-sm text-[var(--color-error)] bg-red-50 p-2 rounded">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
