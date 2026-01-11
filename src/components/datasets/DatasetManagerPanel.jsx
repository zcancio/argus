import { colors } from '../../constants';

function DatasetManagerPanel({ datasets, selectedId, onSelect, onCreate }) {
  return (
    <div style={{
      background: colors.bg.secondary,
      border: `1px solid ${colors.border}`,
      borderRadius: '8px',
      padding: '24px',
      marginBottom: '24px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ color: colors.text.primary, margin: 0, fontSize: '14px', textTransform: 'uppercase', letterSpacing: '1px' }}>
          Datasets
        </h3>
        <button
          onClick={onCreate}
          style={{
            padding: '8px 16px',
            background: `linear-gradient(135deg, ${colors.accent.cyan}, ${colors.accent.magenta})`,
            border: 'none',
            borderRadius: '6px',
            color: colors.text.primary,
            fontSize: '12px',
            fontWeight: '600',
            cursor: 'pointer',
          }}
        >
          + New Dataset
        </button>
      </div>

      {datasets.length === 0 ? (
        <div style={{
          padding: '32px',
          textAlign: 'center',
          color: colors.text.muted,
        }}>
          <div style={{ fontSize: '32px', marginBottom: '12px' }}>📦</div>
          <p style={{ margin: 0, fontSize: '13px' }}>No datasets yet</p>
          <p style={{ margin: '8px 0 0 0', fontSize: '12px' }}>Create a dataset to configure pre-computation</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '400px', overflowY: 'auto' }}>
          {datasets.map(dataset => (
            <DatasetCard
              key={dataset.id}
              dataset={dataset}
              isSelected={dataset.id === selectedId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export { DatasetManagerPanel };
