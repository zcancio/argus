import { ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine } from 'recharts';
import { colors } from '../../constants';

export function ParetoChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div style={{
        background: colors.bg.secondary,
        border: `1px solid ${colors.border}`,
        borderRadius: '8px',
        padding: '24px',
        aspectRatio: '1',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <span style={{ color: colors.text.muted }}>Run experiments to see Pareto frontier</span>
      </div>
    );
  }

  return (
    <div style={{
      background: colors.bg.secondary,
      border: `1px solid ${colors.border}`,
      borderRadius: '8px',
      padding: '24px',
    }}>
      <h3 style={{ color: colors.text.primary, margin: '0 0 20px 0', fontSize: '14px', textTransform: 'uppercase', letterSpacing: '1px' }}>
        Safety vs Usefulness Tradeoff
      </h3>
      <ResponsiveContainer width="100%" aspect={1}>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 40, left: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
          <XAxis
            type="number"
            dataKey="usefulness_rate"
            name="Usefulness"
            domain={[0, 1]}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            stroke={colors.text.muted}
            label={{ value: 'Usefulness Rate', position: 'bottom', fill: colors.text.secondary, fontSize: 12 }}
          />
          <YAxis
            type="number"
            dataKey="safety_rate"
            name="Safety"
            domain={[0, 1]}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            stroke={colors.text.muted}
            label={{ value: 'Safety Rate', angle: -90, position: 'left', fill: colors.text.secondary, fontSize: 12 }}
          />
          <Tooltip
            contentStyle={{
              background: colors.bg.elevated,
              border: `1px solid ${colors.border}`,
              borderRadius: '6px',
              fontSize: '12px',
            }}
            formatter={(value, name) => [`${(value * 100).toFixed(1)}%`, name]}
          />
          <ReferenceLine x={1} stroke={colors.accent.green} strokeDasharray="5 5" />
          <ReferenceLine y={1} stroke={colors.accent.green} strokeDasharray="5 5" />
          <Scatter
            data={data}
            fill={colors.accent.cyan}
            stroke={colors.accent.cyan}
            strokeWidth={2}
            r={8}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
