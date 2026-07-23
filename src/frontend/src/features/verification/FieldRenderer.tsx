import type { FieldSpec } from '../../api/hooks';

interface FieldRendererProps {
  field: FieldSpec;
  value: unknown;
  onChange: (name: string, value: unknown) => void;
  error?: string;
  showErrors: boolean;
}

const baseInputClass = 'w-full border rounded px-2 py-1.5 text-xs focus:ring-2 focus:ring-[var(--color-info)] focus:outline-none';
const errorInputClass = 'border-red-500 focus:ring-red-500';

export default function FieldRenderer({ field, value, onChange, error, showErrors }: FieldRendererProps) {
  const inputClass = `${baseInputClass} ${showErrors && error ? errorInputClass : 'border-gray-300'}`;

  const handleChange = (val: string) => {
    onChange(field.name, val);
  };

  const renderInput = () => {
    switch (field.kind) {
      case 'select':
        return (
          <select
            value={String(value ?? '')}
            onChange={(e) => handleChange(e.target.value)}
            className={inputClass}
          >
            <option value="">Wybierz...</option>
            {field.choices?.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        );
      case 'number':
        return (
          <input
            type="number"
            value={String(value ?? '')}
            onChange={(e) => handleChange(e.target.value)}
            min={field.min ?? undefined}
            max={field.max ?? undefined}
            step={1}
            className={inputClass}
          />
        );
      case 'text':
        return (
          <textarea
            rows={2}
            value={String(value ?? '')}
            onChange={(e) => handleChange(e.target.value)}
            className={inputClass}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="mb-1.5">
      <label className="block text-xs font-medium text-gray-700 mb-0.5">
        {field.label}
      </label>
      {renderInput()}
      {showErrors && error && (
        <p className="text-red-600 text-xs mt-0.5">{error}</p>
      )}
    </div>
  );
}
