import type { FieldSpec } from '../../api/hooks';

interface FieldRendererProps {
  field: FieldSpec;
  value: unknown;
  onChange: (name: string, value: unknown) => void;
  error?: string;
  showErrors: boolean;
  disabled?: boolean;
  hint?: string;
}

const baseInputClass = 'w-full border rounded px-2 py-1.5 text-xs focus:ring-2 focus:ring-[var(--color-info)] focus:outline-none';
const errorInputClass = 'border-red-500 focus:ring-red-500';

function RadioCardGroup({
  choices,
  value,
  onChange,
  disabled,
}: {
  choices: string[];
  value: unknown;
  onChange: (val: string) => void;
  disabled?: boolean;
}) {
  const isBinaryTakNie = choices.length === 2 &&
    choices.every((c) => c.toUpperCase() === 'TAK' || c.toUpperCase() === 'NIE');

  return (
    <div className={`grid gap-1.5 ${isBinaryTakNie ? 'grid-cols-2' : 'grid-cols-1'} ${disabled ? 'pointer-events-none opacity-70' : ''}`}>
      {choices.map((choice) => {
        const selected = String(value ?? '') === choice;
        return (
          <button
            key={choice}
            type="button"
            onClick={() => onChange(selected ? '' : choice)}
            className={`flex items-center gap-2 px-3 py-2.5 rounded border text-xs text-left transition-all cursor-pointer
              ${selected
                ? 'border-[var(--color-info)] bg-[var(--color-info)]/10'
                : 'border-gray-200 bg-white hover:border-gray-400 hover:bg-gray-50'
              }`}
          >
            <span className={`w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center flex-shrink-0
              ${selected ? 'border-[var(--color-info)]' : 'border-gray-400'}`}
            >
              {selected && <span className="w-2 h-2 rounded-full bg-[var(--color-info)]" />}
            </span>
            <span className={selected ? 'font-medium' : ''}>{choice}</span>
          </button>
        );
      })}
    </div>
  );
}

export default function FieldRenderer({ field, value, onChange, error, showErrors, disabled = false, hint }: FieldRendererProps) {
  const inputClass = `${baseInputClass} ${showErrors && error ? errorInputClass : 'border-gray-300'}`;

  const handleChange = (val: string) => {
    onChange(field.name, val);
  };

  if (field.kind === 'radio') {
    return (
      <div className="mb-2.5">
        <label className="block text-xs font-medium text-gray-700 mb-1.5">
          {field.label}
        </label>
        <RadioCardGroup
          choices={field.choices ?? []}
          value={value}
          onChange={handleChange}
          disabled={disabled}
        />
        {showErrors && error && (
          <p className="text-red-600 text-xs mt-0.5">{error}</p>
        )}
      </div>
    );
  }

  const renderInput = () => {
    switch (field.kind) {
      case 'number':
        return (
          <input
            type="number"
            value={String(value ?? '')}
            onChange={(e) => handleChange(e.target.value)}
            min={field.min ?? undefined}
            max={field.max ?? undefined}
            step={1}
            disabled={disabled}
            className={`${inputClass} ${field.name === 'p2_wiek' ? 'max-w-[100px]' : ''}`}
          />
        );
      case 'text':
        return (
          <textarea
            rows={2}
            value={String(value ?? '')}
            onChange={(e) => handleChange(e.target.value)}
            disabled={disabled}
            className={inputClass}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="mb-2.5">
      <label className="block text-xs font-medium text-gray-700 mb-1.5">
        {field.label}
      </label>
      {renderInput()}
      {hint && <p className="text-amber-700 text-xs mt-0.5">{hint}</p>}
      {showErrors && error && (
        <p className="text-red-600 text-sm mt-0.5">{error}</p>
      )}
    </div>
  );
}
