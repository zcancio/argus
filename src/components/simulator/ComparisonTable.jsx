import { colors } from '../../constants';
import { PAPER_RESULTS, PROTOCOL_CONFIGS, PROTOCOL_ORDER } from '../../paperResults';

export function ComparisonTable({ results, runningProtocol }) {
  const getDeltaColor = (delta) => {
    if (delta === null || delta === undefined) return colors.text.muted;
    const absDelta = Math.abs(delta);
    if (absDelta <= 0.05) return colors.accent.green;
    if (absDelta <= 0.10) return colors.accent.amber;
    return colors.accent.red;
  };

  const formatPercent = (value, se) => {
    if (value === undefined || value === null) return '-';
    const seStr = se !== undefined ? ` \u00B1${(se * 100).toFixed(1)}` : '';
    return `${(value * 100).toFixed(1)}%${seStr}`;
  };

  const formatDelta = (simValue, paperValue) => {
    if (simValue === undefined || simValue === null) return '-';
    const delta = simValue - paperValue;
    const sign = delta >= 0 ? '+' : '';
    return `${sign}${(delta * 100).toFixed(1)}%`;
  };

  const getStatusBadge = (status, isRunning) => {
    if (isRunning) {
      return (
        <span style={{
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '10px',
          fontWeight: '500',
          background: colors.accent.cyan + '20',
          color: colors.accent.cyan,
        }}>
          Running...
        </span>
      );
    }

    const statusStyles = {
      complete: { bg: colors.accent.green + '20', color: colors.accent.green },
      error: { bg: colors.accent.red + '20', color: colors.accent.red },
      pending: { bg: colors.bg.tertiary, color: colors.text.muted },
    };

    const style = statusStyles[status] || statusStyles.pending;
    const label = status === 'complete' ? 'Done' : status === 'error' ? 'Error' : 'Pending';

    return (
      <span style={{
        padding: '2px 8px',
        borderRadius: '4px',
        fontSize: '10px',
        fontWeight: '500',
        background: style.bg,
        color: style.color,
      }}>
        {label}
      </span>
    );
  };

  const thStyle = {
    textAlign: 'left',
    padding: '10px 12px',
    color: colors.text.secondary,
    fontWeight: '500',
    fontSize: '11px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    whiteSpace: 'nowrap',
  };

  const tdStyle = {
    padding: '10px 12px',
    fontSize: '12px',
    fontFamily: 'JetBrains Mono, monospace',
  };

  return (
    <div style={{
      background: colors.bg.secondary,
      border: `1px solid ${colors.border}`,
      borderRadius: '8px',
      padding: '24px',
      marginTop: '16px',
    }}>
      <h3 style={{
        color: colors.text.primary,
        margin: '0 0 16px 0',
        fontSize: '14px',
        textTransform: 'uppercase',
        letterSpacing: '1px',
      }}>
        Protocol Comparison
      </h3>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '800px' }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${colors.border}` }}>
              <th style={thStyle}>Protocol</th>
              <th style={thStyle}>Paper Safety</th>
              <th style={thStyle}>Sim Safety</th>
              <th style={thStyle}>Delta</th>
              <th style={thStyle}>Paper Useful</th>
              <th style={thStyle}>Sim Useful</th>
              <th style={thStyle}>Delta</th>
              <th style={thStyle}>Status</th>
            </tr>
          </thead>
          <tbody>
            {PROTOCOL_ORDER.map((key) => {
              const paper = PAPER_RESULTS[key];
              const config = PROTOCOL_CONFIGS[key];
              const sim = results[key];
              const isRunning = runningProtocol === key;
              const safetyDelta = sim?.safety !== undefined ? sim.safety - paper.safety : null;
              const usefulDelta = sim?.usefulness !== undefined ? sim.usefulness - paper.usefulness : null;

              return (
                <tr
                  key={key}
                  style={{
                    borderBottom: `1px solid ${colors.border}`,
                    background: isRunning ? colors.accent.cyan + '10' : 'transparent',
                    transition: 'background 0.2s',
                  }}
                >
                  <td style={{ ...tdStyle, color: colors.text.primary, fontFamily: 'inherit', fontWeight: '500' }}>
                    {config.name}
                  </td>
                  <td style={{ ...tdStyle, color: colors.text.secondary }}>
                    {(paper.safety * 100).toFixed(0)}%
                  </td>
                  <td style={{ ...tdStyle, color: sim?.safety !== undefined ? colors.text.primary : colors.text.muted }}>
                    {formatPercent(sim?.safety, sim?.safety_se)}
                  </td>
                  <td style={{ ...tdStyle, color: getDeltaColor(safetyDelta) }}>
                    {formatDelta(sim?.safety, paper.safety)}
                  </td>
                  <td style={{ ...tdStyle, color: colors.text.secondary }}>
                    {(paper.usefulness * 100).toFixed(0)}%
                  </td>
                  <td style={{ ...tdStyle, color: sim?.usefulness !== undefined ? colors.text.primary : colors.text.muted }}>
                    {formatPercent(sim?.usefulness, sim?.usefulness_se)}
                  </td>
                  <td style={{ ...tdStyle, color: getDeltaColor(usefulDelta) }}>
                    {formatDelta(sim?.usefulness, paper.usefulness)}
                  </td>
                  <td style={tdStyle}>
                    {getStatusBadge(sim?.status, isRunning)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
