import { useState } from 'react';
import { colors } from '../../constants';

export function TrialsTable({ trials }) {
  const [currentPage, setCurrentPage] = useState(0);
  const pageSize = 50;

  if (!trials || trials.length === 0) return null;

  const totalPages = Math.ceil(trials.length / pageSize);
  const startIdx = currentPage * pageSize;
  const displayedTrials = trials.slice(startIdx, startIdx + pageSize);

  const redWins = trials.filter(t => t.winner === 'RED').length;
  const blueWins = trials.filter(t => t.winner === 'BLUE').length;

  return (
    <div style={{
      background: colors.bg.secondary,
      border: `1px solid ${colors.border}`,
      borderRadius: '8px',
      padding: '24px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ color: colors.text.primary, margin: 0, fontSize: '14px', textTransform: 'uppercase', letterSpacing: '1px' }}>
          Trial Results
        </h3>
        <div style={{ display: 'flex', gap: '16px', fontSize: '12px' }}>
          <span style={{ color: colors.accent.cyan }}>Blue Wins: {blueWins}</span>
          <span style={{ color: colors.accent.red }}>Red Wins: {redWins}</span>
        </div>
      </div>

      <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${colors.border}` }}>
              <th style={{ textAlign: 'left', padding: '8px 12px', color: colors.text.secondary, fontWeight: '500' }}>Trial</th>
              <th style={{ textAlign: 'left', padding: '8px 12px', color: colors.text.secondary, fontWeight: '500' }}>Winner</th>
              <th style={{ textAlign: 'left', padding: '8px 12px', color: colors.text.secondary, fontWeight: '500' }}>Problem Index</th>
              <th style={{ textAlign: 'left', padding: '8px 12px', color: colors.text.secondary, fontWeight: '500' }}>Correctness</th>
            </tr>
          </thead>
          <tbody>
            {displayedTrials.map((trial) => (
              <tr
                key={trial.trial}
                style={{
                  borderBottom: `1px solid ${colors.border}`,
                  background: trial.winner === 'RED' ? 'rgba(239, 68, 68, 0.1)' : 'transparent',
                }}
              >
                <td style={{ padding: '8px 12px', color: colors.text.muted, fontFamily: 'JetBrains Mono, monospace' }}>
                  {trial.trial}
                </td>
                <td style={{ padding: '8px 12px' }}>
                  <span style={{
                    color: trial.winner === 'BLUE' ? colors.accent.cyan : colors.accent.red,
                    fontWeight: '500',
                  }}>
                    {trial.winner}
                  </span>
                </td>
                <td style={{ padding: '8px 12px', color: colors.text.secondary, fontFamily: 'JetBrains Mono, monospace' }}>
                  {trial.problem_index !== null ? trial.problem_index : '-'}
                </td>
                <td style={{ padding: '8px 12px', color: colors.text.secondary }}>
                  {trial.correctness_rate !== null ? `${(trial.correctness_rate * 100).toFixed(1)}%` : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', marginTop: '16px' }}>
          <button
            onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
            disabled={currentPage === 0}
            style={{
              padding: '6px 12px',
              background: colors.bg.tertiary,
              border: `1px solid ${colors.border}`,
              borderRadius: '4px',
              color: currentPage === 0 ? colors.text.muted : colors.text.primary,
              cursor: currentPage === 0 ? 'default' : 'pointer',
              fontSize: '12px',
            }}
          >
            Previous
          </button>
          <span style={{ color: colors.text.secondary, fontSize: '12px' }}>
            Page {currentPage + 1} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage(p => Math.min(totalPages - 1, p + 1))}
            disabled={currentPage === totalPages - 1}
            style={{
              padding: '6px 12px',
              background: colors.bg.tertiary,
              border: `1px solid ${colors.border}`,
              borderRadius: '4px',
              color: currentPage === totalPages - 1 ? colors.text.muted : colors.text.primary,
              cursor: currentPage === totalPages - 1 ? 'default' : 'pointer',
              fontSize: '12px',
            }}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
