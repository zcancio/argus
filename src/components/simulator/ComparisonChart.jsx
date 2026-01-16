import { ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, Customized } from 'recharts';
import { colors } from '../../constants';

export function ComparisonChart({ paperData, simData }) {
  // Create paired data for connecting lines
  const connectionLines = simData?.map(sim => {
    const paper = paperData.find(p => p.protocol === sim.protocol);
    if (paper) {
      return {
        protocol: sim.protocol,
        paperSafety: paper.safety,
        paperUsefulness: paper.usefulness,
        simSafety: sim.safety,
        simUsefulness: sim.usefulness,
      };
    }
    return null;
  }).filter(Boolean) || [];

  // Custom component to render dashed connection lines
  const ConnectionLines = ({ xAxisMap, yAxisMap }) => {
    if (!connectionLines.length || !xAxisMap || !yAxisMap) return null;

    const xAxis = xAxisMap[0];
    const yAxis = yAxisMap[0];

    if (!xAxis || !yAxis) return null;

    return (
      <g>
        {connectionLines.map((line) => {
          const x1 = xAxis.scale(line.paperUsefulness);
          const y1 = yAxis.scale(line.paperSafety);
          const x2 = xAxis.scale(line.simUsefulness);
          const y2 = yAxis.scale(line.simSafety);

          return (
            <line
              key={line.protocol}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke={colors.text.muted}
              strokeWidth={1.5}
              strokeDasharray="4 3"
              opacity={0.6}
            />
          );
        })}
      </g>
    );
  };

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const data = payload[0].payload;

    return (
      <div style={{
        background: colors.bg.elevated,
        border: `1px solid ${colors.border}`,
        borderRadius: '6px',
        padding: '12px',
        fontSize: '12px',
      }}>
        <div style={{ fontWeight: '600', color: colors.text.primary, marginBottom: '8px' }}>
          {data.name}
        </div>
        <div style={{ color: colors.text.secondary }}>
          Safety: {(data.safety * 100).toFixed(1)}%
          {data.safety_se && ` \u00B1${(data.safety_se * 100).toFixed(1)}%`}
        </div>
        <div style={{ color: colors.text.secondary }}>
          Usefulness: {(data.usefulness * 100).toFixed(1)}%
          {data.usefulness_se && ` \u00B1${(data.usefulness_se * 100).toFixed(1)}%`}
        </div>
      </div>
    );
  };

  const hasSimData = simData && simData.length > 0;

  // Custom legend
  const renderLegend = () => (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      gap: '24px',
      marginTop: '16px',
      flexWrap: 'wrap',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <svg width="16" height="16">
          <circle cx="8" cy="8" r="6" fill={colors.accent.cyan} />
        </svg>
        <span style={{ color: colors.text.secondary, fontSize: '12px' }}>Paper Results</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <svg width="16" height="16">
          <rect x="2" y="2" width="12" height="12" fill={colors.accent.magenta} transform="rotate(45 8 8)" />
        </svg>
        <span style={{ color: colors.text.secondary, fontSize: '12px' }}>Simulation Results</span>
      </div>
      {hasSimData && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <svg width="24" height="16">
            <line x1="2" y1="8" x2="22" y2="8" stroke={colors.text.muted} strokeWidth="1.5" strokeDasharray="4 3" opacity="0.6" />
          </svg>
          <span style={{ color: colors.text.secondary, fontSize: '12px' }}>Same Protocol</span>
        </div>
      )}
    </div>
  );

  return (
    <div style={{
      background: colors.bg.secondary,
      border: `1px solid ${colors.border}`,
      borderRadius: '8px',
      padding: '24px',
    }}>
      <h3 style={{
        color: colors.text.primary,
        margin: '0 0 20px 0',
        fontSize: '14px',
        textTransform: 'uppercase',
        letterSpacing: '1px',
      }}>
        Safety vs Usefulness Comparison
      </h3>

      <ResponsiveContainer width="100%" height={400}>
        <ScatterChart margin={{ top: 20, right: 30, bottom: 40, left: 50 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
          <XAxis
            type="number"
            dataKey="usefulness"
            name="Usefulness"
            domain={[0.75, 1.0]}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            stroke={colors.text.muted}
            tick={{ fill: colors.text.muted, fontSize: 11 }}
            label={{
              value: 'Usefulness Rate',
              position: 'bottom',
              fill: colors.text.secondary,
              fontSize: 12,
              offset: 0,
            }}
          />
          <YAxis
            type="number"
            dataKey="safety"
            name="Safety"
            domain={[0.55, 1.0]}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            stroke={colors.text.muted}
            tick={{ fill: colors.text.muted, fontSize: 11 }}
            label={{
              value: 'Safety Rate',
              angle: -90,
              position: 'insideLeft',
              fill: colors.text.secondary,
              fontSize: 12,
            }}
          />
          <Tooltip content={<CustomTooltip />} />

          {/* Dashed lines connecting paper to simulation for same protocol */}
          {hasSimData && <Customized component={ConnectionLines} />}

          {/* Paper results - circles */}
          <Scatter
            name="Paper Results"
            data={paperData}
            fill={colors.accent.cyan}
            stroke={colors.accent.cyan}
            strokeWidth={2}
            shape="circle"
            r={8}
          />

          {/* Simulation results - diamonds */}
          {hasSimData && (
            <Scatter
              name="Simulation Results"
              data={simData}
              fill={colors.accent.magenta}
              stroke={colors.accent.magenta}
              strokeWidth={2}
              shape="diamond"
              r={8}
            />
          )}
        </ScatterChart>
      </ResponsiveContainer>

      {renderLegend()}

      {!hasSimData && (
        <div style={{
          textAlign: 'center',
          color: colors.text.muted,
          fontSize: '12px',
          marginTop: '8px',
        }}>
          Run simulations to compare with paper results
        </div>
      )}
    </div>
  );
}
