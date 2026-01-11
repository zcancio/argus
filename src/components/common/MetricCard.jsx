import { colors } from '../../constants';

export function MetricCard({ label, value, subvalue, color = colors.accent.cyan }) {
  return (
    <div style={{
      background: colors.bg.secondary,
      border: `1px solid ${colors.border}`,
      borderRadius: '8px',
      padding: '20px',
      position: 'relative',
      overflow: 'hidden',
    }}>
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        height: '2px',
        background: `linear-gradient(90deg, ${color}, transparent)`,
      }} />
      <div style={{ color: colors.text.secondary, fontSize: '12px', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '8px' }}>
        {label}
      </div>
      <div style={{ color: colors.text.primary, fontSize: '32px', fontWeight: '600', fontFamily: 'JetBrains Mono, monospace' }}>
        {value}
      </div>
      {subvalue && (
        <div style={{ color: colors.text.muted, fontSize: '12px', marginTop: '4px' }}>
          {subvalue}
        </div>
      )}
    </div>
  );
}
