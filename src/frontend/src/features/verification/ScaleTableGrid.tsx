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
  rowHeight?: number;
}

export default function ScaleTableGrid({ fields, values, onChange, rowHeight = 40 }: ScaleTableGridProps) {
  if (fields.length === 0) return null;

  const choices = fields[0].choices ?? [];
  const isMfisScale = choices.length === 5 && choices.every((c) => /^[0-4]$/.test(c));

  const colLabels = isMfisScale
    ? choices.map((c) => MFIS_LABEL_MAP[c] ?? c)
    : choices;

  return (
    <div>
      <table className="w-full border-collapse text-xs" style={{ tableLayout: 'fixed' }}>
        <thead>
          <tr>
            <th className="text-left font-medium text-gray-600 p-1.5 border-b border-gray-200 w-[30%]" style={{ height: rowHeight }}>
              Pytanie
            </th>
            {colLabels.map((label, i) => (
              <th
                key={i}
                className="text-center font-medium text-gray-600 p-1.5 border-b border-gray-200 leading-tight"
              >
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {fields.map((field, idx) => {
            const currentValue = String(values[field.name] ?? '');
            return (
              <tr key={field.name} className={`${idx % 2 === 0 ? 'bg-gray-50/50' : ''} hover:bg-blue-50/60 transition-colors`}>
                <td className="p-1.5 border-b border-gray-100 text-gray-700" style={{ height: rowHeight }}>
                  {field.label}
                </td>
                {choices.map((choice) => {
                  const selected = currentValue === choice;
                  return (
                    <td key={choice} className="p-0 border-b border-gray-100 text-center" style={{ height: rowHeight }}>
                      <button
                        type="button"
                        onClick={() => onChange(field.name, choice)}
                        className={`w-full h-full flex items-center justify-center transition-colors cursor-pointer
                          ${selected
                            ? 'bg-[var(--color-info)] text-white font-medium'
                            : 'hover:bg-blue-100/70 text-gray-500'
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
