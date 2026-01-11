import { colors } from '../../constants';
import { STATUS_BADGES, TEST_STATUS_BADGES } from '../../datasetDefaults';

function DatasetCard({ dataset, isSelected, onSelect }) {
  const statusBadge = STATUS_BADGES[dataset.status] || STATUS_BADGES.draft;
  const testBadge = dataset.last_test ? TEST_STATUS_BADGES[dataset.last_test.status] : null;

  return (
    <div
      onClick={() => onSelect(dataset.id)}
      style={{
        padding: '16px',
        background: isSelected ? colors.bg.tertiary : colors.bg.secondary,
        borderRadius: '8px',
        border: `1px solid ${isSelected ? colors.accent.cyan : colors.border}`,
        cursor: 'pointer',
        transition: 'all 0.2s',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
        <div>
          <h4 style={{ margin: 0, color: colors.text.primary, fontSize: '14px', fontWeight: '500' }}>
            {dataset.name}
          </h4>
          <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
            <span style={{
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '10px',
              textTransform: 'uppercase',
              background: statusBadge.className.includes('green') ? colors.accent.green + '20' : colors.accent.amber + '20',
              color: statusBadge.className.includes('green') ? colors.accent.green : colors.accent.amber,
            }}>
              {statusBadge.label}
            </span>
            {testBadge && (
              <span style={{
                padding: '2px 8px',
                borderRadius: '4px',
                fontSize: '10px',
                textTransform: 'uppercase',
                background: testBadge.className.includes('green') ? colors.accent.green + '20' :
                           testBadge.className.includes('red') ? colors.accent.red + '20' :
                           colors.accent.cyan + '20',
                color: testBadge.className.includes('green') ? colors.accent.green :
                       testBadge.className.includes('red') ? colors.accent.red :
                       colors.accent.cyan,
              }}>
                Test: {testBadge.label}
              </span>
            )}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '8px', fontSize: '11px', color: colors.text.muted }}>
        <span>{dataset.settings.num_problems} problems</span>
        <span>•</span>
        <span>{dataset.settings.num_backdoor_ideas} ideas</span>
        <span>•</span>
        <span>max diff: {dataset.settings.max_difficulty}</span>
      </div>
    </div>
  );
}

export { DatasetCard };
