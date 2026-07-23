import { useVerificationStore } from '../store/verificationStore';

interface PageTabsProps {
  surveyId: number;
  currentPage: number;
  onChange: (page: number) => void;
}

const TOTAL_PAGES = 5;

export default function PageTabs({ surveyId, currentPage, onChange }: PageTabsProps) {
  const setSelectedPage = useVerificationStore((s) => s.setSelectedPage);

  const handleClick = (page: number) => {
    setSelectedPage(surveyId, page);
    onChange(page);
  };

  return (
    <div role="tablist" className="flex border-b border-gray-200 shrink-0">
      {Array.from({ length: TOTAL_PAGES }, (_, i) => (
        <button
          key={i}
          role="tab"
          aria-selected={currentPage === i}
          onClick={() => handleClick(i)}
          className={`flex-1 py-2 text-sm font-medium transition-colors focus:outline-none ${
            currentPage === i
              ? 'bg-[var(--color-info)] text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Strona {i + 1}
        </button>
      ))}
    </div>
  );
}
