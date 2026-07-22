import { useState } from 'react';
import { surveyImageUrl } from '../api/hooks';
import Spinner from './ui/Spinner';

interface ImageViewerProps {
  surveyId: number;
  page: number;
}

const PAGE_DESCRIPTIONS: Record<number, string> = {
  0: 'Dane demograficzne, praca, styl życia',
  1: 'Skala CES-D (odczucia w minionym tygodniu)',
  2: 'Ateńska skala bezsenności',
  3: 'MFIS (część 1, pozycje 1-15)',
  4: 'MFIS (część 2, pozycje 16-21) oraz pytania o zdrowie',
};

export default function ImageViewer({ surveyId, page }: ImageViewerProps) {
  const [isLoading, setLoading] = useState(true);
  const [hasError, setError] = useState(false);

  return (
    <div className="relative w-full h-full overflow-hidden bg-gray-100">
      {isLoading && !hasError && <Spinner className="absolute inset-0" />}
      {hasError && (
        <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-500 p-4 text-center">
          <p className="font-medium">Brak obrazu dla tej strony</p>
          <p className="text-sm mt-1">{PAGE_DESCRIPTIONS[page] ?? ''}</p>
        </div>
      )}
      {!hasError && (
        <img
          src={surveyImageUrl(surveyId, page)}
          alt={`Strona ${page + 1}`}
          className="w-full h-full object-contain"
          onLoad={() => setLoading(false)}
          onError={() => { setLoading(false); setError(true); }}
        />
      )}
    </div>
  );
}
