import { useMemo, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import {
  useClearSession,
  useProcessingStatus,
  useStartProcessing,
  useSurveys,
} from '../../api/hooks';
import { useVerificationStore } from '../../store/verificationStore';

export default function WelcomePage() {
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const { data: surveys } = useSurveys();
  const { data: processingStatus } = useProcessingStatus();
  const startProcessing = useStartProcessing();
  const clearSession = useClearSession();
  const clearCache = useVerificationStore((s) => s.clearAllCache);

  const isRunning = processingStatus?.is_running ?? false;

  const { total, processed, verified, processedPages } = useMemo(() => {
    const list = surveys ?? [];
    const done = list.filter(
      (s) => s.status === 'ready' || s.status === 'error' || s.status === 'verified'
    );
    return {
      total: list.length,
      processed: done.length,
      verified: list.filter((s) => s.status === 'verified').length,
      processedPages: done.reduce((acc, s) => acc + s.files.length, 0),
    };
  }, [surveys]);

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
  const isCovered = total > 0 && processed === total;
  const allVerified = isCovered && verified === total;

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

  const busy = startProcessing.isPending || clearSession.isPending;

  return (
    <div className="flex items-center justify-center h-screen bg-gray-50">
      <div className="w-full max-w-md bg-white rounded-lg shadow-md p-8">
        <h1 className="text-2xl font-bold text-center mb-1">AnkieterAI</h1>
        <p className="text-gray-500 text-center text-sm mb-6">
          System wprowadzania ankiet papierowych
        </p>

        {total === 0 && (
          <p className="text-center text-gray-500">Brak ankiet w katalogu.</p>
        )}

        {total > 0 && processed === 0 && (
          <>
            <p className="text-center text-gray-600 mb-6">
              Znaleziono {total} ankiet. Rozpocznij analizę, aby wygenerować wyniki.
            </p>
            <button
              onClick={handleStart}
              disabled={busy}
              className="w-full py-2 px-4 bg-[var(--color-info)] text-white
                         rounded-md hover:opacity-90 disabled:opacity-50
                         font-medium transition-opacity"
            >
              {startProcessing.isPending ? 'Rozpoczynanie...' : 'Rozpocznij analizę'}
            </button>
          </>
        )}

        {total > 0 && processed > 0 && !isCovered && (
          <>
            <p className="text-center text-gray-600 mb-2">
              Kontynuacja od ostatniego stanu: przeprocesowano {processed} z {total} ankiet
              ({processedPages} zdjęć).
            </p>
            <button
              onClick={handleStart}
              disabled={busy}
              className="w-full py-2 px-4 bg-[var(--color-info)] text-white
                         rounded-md hover:opacity-90 disabled:opacity-50
                         font-medium transition-opacity"
            >
              {startProcessing.isPending ? 'Kontynuowanie...' : 'Kontynuuj analizę'}
            </button>
          </>
        )}

        {isCovered && (
          <>
            <p className="text-center text-gray-600 mb-2">
              Ten batch jest w 100% przeprocesowany — ponowne rozpoczęcie rozpocznie od nowa.
            </p>
            <div className="flex gap-3">
              {allVerified || readyCount === 0 ? (
                <button
                  onClick={() => navigate('/complete')}
                  className="flex-1 py-2 px-4 bg-[var(--color-info)] text-white
                             rounded-md hover:opacity-90 font-medium transition-opacity"
                >
                  Pobierz wyniki
                </button>
              ) : (
                <button
                  onClick={() => navigate('/app')}
                  className="flex-1 py-2 px-4 bg-[var(--color-info)] text-white
                             rounded-md hover:opacity-90 font-medium transition-opacity"
                >
                  Przejdź do weryfikacji
                </button>
              )}
              <button
                onClick={handleRestart}
                disabled={busy}
                className="flex-1 py-2 px-4 text-gray-700 bg-white border border-gray-300
                           rounded-md hover:bg-gray-50 font-medium transition-colors
                           disabled:opacity-50"
              >
                {busy ? 'Uruchamianie...' : 'Rozpocznij od nowa'}
              </button>
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
