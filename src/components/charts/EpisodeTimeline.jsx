import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { colors } from '../../constants';

export function EpisodeTimeline({ episodes }) {
  if (!episodes || episodes.length === 0) return null;

  const timelineData = episodes.map((ep, idx) => ({
    index: idx,
    suspicion: ep.suspicion_score || 0,
    wasAttack: ep.was_attack,
    caught: ep.was_attack && ep.safety_preserved,
    missed: ep.was_attack && !ep.safety_preserved,
    falsePositive: !ep.was_attack && ep.action_taken !== 'allow',
  }));

  return (
    <div style={{
      background: colors.bg.secondary,
      border: `1px solid ${colors.border}`,
      borderRadius: '8px',
      padding: '24px',
    }}>
      <h3 style={{ color: colors.text.primary, margin: '0 0 20px 0', fontSize: '14px', textTransform: 'uppercase', letterSpacing: '1px' }}>
        Episode Timeline
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={timelineData} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
          <XAxis dataKey="index" stroke={colors.text.muted} />
          <YAxis domain={[0, 1]} stroke={colors.text.muted} tickFormatter={(v) => v.toFixed(1)} />
          <Tooltip
            contentStyle={{
              background: colors.bg.elevated,
              border: `1px solid ${colors.border}`,
              borderRadius: '6px',
              fontSize: '12px',
            }}
          />
          <Line type="monotone" dataKey="suspicion" stroke={colors.accent.cyan} dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2px', marginTop: '16px' }}>
        {timelineData.map((ep, idx) => (
          <div
            key={idx}
            title={`Episode ${idx}: ${ep.wasAttack ? 'Attack' : 'Benign'} - ${ep.caught ? 'Caught' : ep.missed ? 'Missed!' : ep.falsePositive ? 'False Positive' : 'Correct'}`}
            style={{
              width: '8px',
              height: '24px',
              borderRadius: '2px',
              background: ep.missed ? colors.accent.red :
                         ep.caught ? colors.accent.green :
                         ep.falsePositive ? colors.accent.amber :
                         colors.bg.tertiary,
            }}
          />
        ))}
      </div>

      <div style={{ display: 'flex', gap: '20px', marginTop: '12px', fontSize: '11px' }}>
        <span style={{ color: colors.accent.green }}>■ Attack Caught</span>
        <span style={{ color: colors.accent.red }}>■ Attack Missed</span>
        <span style={{ color: colors.accent.amber }}>■ False Positive</span>
        <span style={{ color: colors.text.muted }}>■ Correct Allow</span>
      </div>
    </div>
  );
}
