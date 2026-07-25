import type { FieldSpec } from '../../api/hooks';

const MFIS_LABEL_MAP: Record<string, string> = {
  "0": "Nigdy",
  "1": "Rzadko",
  "2": "Czasami",
  "3": "Często",
  "4": "Prawie zawsze",
};

interface ScaleTableGridProps {
  fields: FieldSpec[];
  values: Record<string, unknown>;
  onChange: (name: string, value: unknown) => void;
}

export default function ScaleTableGrid({ fields, values, onChange }: ScaleTableGridProps) {
  if (fields.length === 0) return null;

  const choices = fields[0].choices ?? [];
  const isMfisScale = choices.length === 5 && choices.every((c) => /^[0-4]$/.test(c));

  const colLabels = isMfisScale
    ? choices.map((c) => MFIS_LABEL_MAP[c] ?? c)
    : choices;

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-xs">
        <thead>
          <tr>
            <th className="text-left font-medium text-gray-600 p-1.5 border-b border-gray-200 min-w-[180px]">
              Pytanie
            </th>
            {colLabels.map((label, i) => (
              <th
                key={i}
                className="text-center font-medium text-gray-600 p-1.5 border-b border-gray-200 min-w-[80px] leading-tight"
              >
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {fields.map((field) => {
            const currentValue = String(values[field.name] ?? '');
            return (
              <tr key={field.name} className="hover:bg-gray-50">
                <td className="p-1.5 border-b border-gray-100 text-gray-700">
                  {field.label}
                </td>
                {choices.map((choice) => {
                  const selected = currentValue === choice;
                  return (
                    <td key={choice} className="p-0 border-b border-gray-100 text-center">
                      <button
                        type="button"
                        onClick={() => onChange(field.name, choice)}
                        className={`w-full h-full min-h-[32px] flex items-center justify-center transition-colors cursor-pointer
                          ${selected
                            ? 'bg-[var(--color-info)] text-white font-medium'
                            : 'hover:bg-gray-100 text-gray-500'
                          }`}
                      >
                        {selected ? '●' : '○'}
                      </button>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
