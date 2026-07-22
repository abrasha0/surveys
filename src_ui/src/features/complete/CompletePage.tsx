import { useExportCsv } from '../../api/hooks';

export default function CompletePage() {
  const exportCsv = useExportCsv();

  const handleNewSession = () => {
    window.location.href = '/app';
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-50 gap-6">
      <div className="w-16 h-16 rounded-full bg-[var(--color-success)] flex items-center justify-center">
        <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      </div>

      <h1 className="text-2xl font-bold text-gray-800">Wszystkie ankiety zweryfikowane</h1>
      <p className="text-gray-500">Możesz pobrać wyniki lub rozpocząć nową sesję.</p>

      <div className="flex gap-4 mt-2">
        <button
          onClick={() => exportCsv.mutate()}
          disabled={exportCsv.isPending}
          className="px-6 py-2.5 text-sm font-medium text-white bg-[var(--color-info)] rounded-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
        >
          {exportCsv.isPending ? 'Pobieranie...' : 'Pobierz CSV'}
        </button>
        <button
          onClick={handleNewSession}
          className="px-6 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          Nowa sesja
        </button>
      </div>
    </div>
  );
}
