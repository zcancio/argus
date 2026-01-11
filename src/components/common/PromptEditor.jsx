import { useState } from 'react';
import { colors } from '../../constants';

export function PromptEditor({
  promptKey,
  label,
  description,
  variables,
  defaultValue,
  value,
  isModified,
  onChange,
  onReset
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div style={{
      background: colors.bg.tertiary,
      border: `1px solid ${isModified ? colors.accent.amber + '60' : colors.border}`,
      borderRadius: '6px',
    }}>
      {/* Header */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          padding: '12px 16px',
          cursor: 'pointer',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              color: colors.text.primary,
              fontSize: '13px',
              fontWeight: '500'
            }}>
              {label}
            </span>
            {isModified && (
              <span style={{
                padding: '1px 6px',
                background: colors.accent.amber + '20',
                borderRadius: '3px',
                fontSize: '10px',
                color: colors.accent.amber,
              }}>
                modified
              </span>
            )}
          </div>
          <p style={{
            color: colors.text.muted,
            fontSize: '11px',
            margin: '4px 0 0 0',
            whiteSpace: 'normal',
            wordWrap: 'break-word',
          }}>
            {description}
          </p>
        </div>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke={colors.text.muted}
          strokeWidth="2"
          style={{
            transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.2s',
          }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </div>

      {/* Editor */}
      {isExpanded && (
        <div style={{
          padding: '0 16px 16px 16px',
          borderTop: `1px solid ${colors.border}`,
        }}>
          {/* Variables */}
          <div style={{
            padding: '12px 0',
            display: 'flex',
            flexWrap: 'wrap',
            gap: '6px',
          }}>
            <span style={{
              color: colors.text.muted,
              fontSize: '11px',
              marginRight: '4px'
            }}>
              Variables:
            </span>
            {variables.map(v => (
              <code
                key={v}
                style={{
                  padding: '2px 6px',
                  background: colors.bg.primary,
                  borderRadius: '3px',
                  fontSize: '11px',
                  color: colors.accent.cyan,
                  fontFamily: 'JetBrains Mono, monospace',
                }}
              >
                {v}
              </code>
            ))}
          </div>

          {/* Textarea */}
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            style={{
              width: '100%',
              minHeight: '150px',
              padding: '12px',
              background: colors.bg.primary,
              border: `1px solid ${colors.border}`,
              borderRadius: '4px',
              color: colors.text.primary,
              fontSize: '12px',
              fontFamily: 'JetBrains Mono, monospace',
              lineHeight: '1.5',
              resize: 'vertical',
              boxSizing: 'border-box',
            }}
          />

          {/* Actions */}
          {isModified && (
            <button
              onClick={(e) => { e.stopPropagation(); onReset(); }}
              style={{
                marginTop: '8px',
                padding: '6px 12px',
                background: 'transparent',
                border: `1px solid ${colors.border}`,
                borderRadius: '4px',
                color: colors.text.secondary,
                fontSize: '11px',
                cursor: 'pointer',
              }}
            >
              Reset to Default
            </button>
          )}
        </div>
      )}
    </div>
  );
}
