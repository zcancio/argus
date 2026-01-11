import { useState } from 'react';
import { colors } from '../../constants';

export function LLMCallCard({ call }) {
  const [expanded, setExpanded] = useState(false);

  const statusColors = {
    pending: colors.text.muted,
    running: colors.accent.amber,
    completed: colors.accent.green,
    failed: colors.accent.red,
  };

  return (
    <div style={{
      background: colors.bg.primary,
      border: `1px solid ${colors.border}`,
      borderRadius: '6px',
      marginBottom: '8px',
      overflow: 'hidden',
    }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '10px 12px',
          cursor: 'pointer',
        }}
      >
        {/* Status indicator */}
        <div style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: statusColors[call.status] || colors.text.muted,
          animation: call.status === 'running' ? 'pulse 1.5s infinite' : 'none',
        }} />

        {/* Step name */}
        <span style={{
          flex: 1,
          color: colors.text.primary,
          fontSize: '12px',
          fontFamily: 'JetBrains Mono, monospace',
        }}>
          {call.step}
        </span>

        {/* Model */}
        <span style={{
          padding: '2px 6px',
          background: colors.bg.tertiary,
          borderRadius: '4px',
          fontSize: '10px',
          color: colors.text.muted,
        }}>
          {call.model}
        </span>

        {/* Expand indicator */}
        <span style={{ color: colors.text.muted, fontSize: '12px' }}>
          {expanded ? '▼' : '▶'}
        </span>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div style={{ padding: '12px', borderTop: `1px solid ${colors.border}` }}>
          {/* Prompt */}
          <div style={{ marginBottom: '12px' }}>
            <div style={{ color: colors.text.muted, fontSize: '10px', marginBottom: '4px', textTransform: 'uppercase' }}>
              Prompt
            </div>
            <pre style={{
              background: colors.bg.tertiary,
              padding: '8px',
              borderRadius: '4px',
              fontSize: '11px',
              color: colors.text.secondary,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              maxHeight: '150px',
              overflow: 'auto',
              margin: 0,
            }}>
              {call.prompt}
            </pre>
          </div>

          {/* Response */}
          {call.response && (
            <div>
              <div style={{ color: colors.text.muted, fontSize: '10px', marginBottom: '4px', textTransform: 'uppercase' }}>
                Response
              </div>
              <pre style={{
                background: colors.bg.tertiary,
                padding: '8px',
                borderRadius: '4px',
                fontSize: '11px',
                color: colors.accent.green,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                maxHeight: '150px',
                overflow: 'auto',
                margin: 0,
              }}>
                {call.response}
              </pre>
            </div>
          )}

          {/* Error */}
          {call.error && (
            <div>
              <div style={{ color: colors.accent.red, fontSize: '10px', marginBottom: '4px', textTransform: 'uppercase' }}>
                Error
              </div>
              <pre style={{
                background: colors.accent.red + '20',
                padding: '8px',
                borderRadius: '4px',
                fontSize: '11px',
                color: colors.accent.red,
                whiteSpace: 'pre-wrap',
                margin: 0,
              }}>
                {call.error}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
