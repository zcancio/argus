import { colors } from '../../constants';

export function DatasetPanel({ datasets, selectedDatasetId, onDatasetChange, onRun, isRunning }) {
  const selectStyle = {
    width: '100%',
    padding: '10px 12px',
    background: colors.bg.tertiary,
    border: `1px solid ${colors.border}`,
    borderRadius: '6px',
    color: colors.text.primary,
    fontSize: '14px',
  };

  return (
    <div style={{
      background: colors.bg.secondary,
      border: `1px solid ${colors.border}`,
      borderRadius: '8px',
      padding: '24px',
    }}>
      <div style={{ fontSize: '11px', color: colors.text.muted, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '16px' }}>
        Dataset
      </div>

      <select
        value={selectedDatasetId || ''}
        onChange={(e) => onDatasetChange(e.target.value || null)}
        style={selectStyle}
      >
        <option value="">Select a dataset...</option>
        {datasets.map(d => (
          <option key={d.id} value={d.id}>
            {d.name} ({d.stats?.completed || 0} problems)
          </option>
        ))}
      </select>

      <button
        onClick={onRun}
        disabled={isRunning || !selectedDatasetId}
        style={{
          width: '100%',
          padding: '14px 20px',
          marginTop: '16px',
          background: (isRunning || !selectedDatasetId) ? colors.bg.tertiary : `linear-gradient(135deg, ${colors.accent.cyan}, ${colors.accent.magenta})`,
          border: 'none',
          borderRadius: '6px',
          color: colors.text.primary,
          fontSize: '14px',
          fontWeight: '600',
          cursor: (isRunning || !selectedDatasetId) ? 'not-allowed' : 'pointer',
          textTransform: 'uppercase',
          letterSpacing: '1px',
        }}
      >
        {isRunning ? 'Running...' : 'Run Simulation'}
      </button>
    </div>
  );
}
