import { useState } from 'react';
import { colors } from '../../constants';
import { LLMCallCard } from '../common';

export function TestProgressModal({ isOpen, testResult, onClose }) {
  const [expandedPhases, setExpandedPhases] = useState({});

  if (!isOpen) return null;

  const phases = [
    { num: 1, name: 'Baseline Solutions' },
    { num: 2, name: 'Generate Backdoors' },
    { num: 3, name: 'Find Exploits' },
    { num: 4, name: 'Verify Exploits' },
    { num: 5, name: 'Monitoring Scores' },
    { num: 6, name: 'Select Best' },
    { num: 7, name: 'Compute Thresholds' },
  ];

  // Group LLM calls by phase
  const callsByPhase = {};
  (testResult?.llm_calls || []).forEach(call => {
    if (!callsByPhase[call.phase]) {
      callsByPhase[call.phase] = [];
    }
    callsByPhase[call.phase].push(call);
  });

  const togglePhase = (phaseNum) => {
    setExpandedPhases(prev => ({
      ...prev,
      [phaseNum]: !prev[phaseNum]
    }));
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0,0,0,0.8)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
    }}>
      <div style={{
        background: colors.bg.secondary,
        border: `1px solid ${colors.border}`,
        borderRadius: '12px',
        padding: '32px',
        width: '700px',
        maxWidth: '90vw',
        maxHeight: '85vh',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <h3 style={{ color: colors.text.primary, margin: 0, fontSize: '16px' }}>
            Test Run {testResult?.status === 'running' ? 'In Progress' : testResult?.status === 'completed' ? 'Complete' : 'Failed'}
          </h3>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: colors.text.muted,
              fontSize: '20px',
              cursor: 'pointer',
            }}
          >
            ×
          </button>
        </div>

        {/* Progress bar */}
        <div style={{
          height: '4px',
          background: colors.bg.primary,
          borderRadius: '2px',
          overflow: 'hidden',
          marginBottom: '24px',
          flexShrink: 0,
        }}>
          <div style={{
            height: '100%',
            width: `${testResult?.progress_percent || 0}%`,
            background: testResult?.status === 'failed' ? colors.accent.red :
                       testResult?.status === 'completed' ? colors.accent.green :
                       `linear-gradient(90deg, ${colors.accent.cyan}, ${colors.accent.magenta})`,
            transition: 'width 0.3s ease',
          }} />
        </div>

        {/* Scrollable content */}
        <div style={{ flex: 1, overflow: 'auto', marginBottom: '16px' }}>
          {/* Phase list with LLM calls */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {phases.map(phase => {
              const isComplete = testResult?.phases_completed?.includes(phase.num);
              const isCurrent = testResult?.current_phase?.includes(`Phase ${phase.num}`);
              const phaseCalls = callsByPhase[phase.num] || [];
              const isExpanded = expandedPhases[phase.num];
              const hasRunningCall = phaseCalls.some(c => c.status === 'running');

              return (
                <div key={phase.num}>
                  <div
                    onClick={() => phaseCalls.length > 0 && togglePhase(phase.num)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      padding: '10px 12px',
                      background: isCurrent ? colors.bg.tertiary : 'transparent',
                      borderRadius: '6px',
                      cursor: phaseCalls.length > 0 ? 'pointer' : 'default',
                    }}
                  >
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: '20px',
                      height: '20px',
                      borderRadius: '50%',
                      background: isComplete ? colors.accent.green + '30' :
                                 isCurrent ? colors.accent.cyan + '30' :
                                 colors.bg.primary,
                      color: isComplete ? colors.accent.green :
                             isCurrent ? colors.accent.cyan :
                             colors.text.muted,
                      fontSize: '10px',
                      fontWeight: '600',
                    }}>
                      {isComplete ? '✓' : hasRunningCall ? '⟳' : phase.num}
                    </span>
                    <span style={{
                      flex: 1,
                      color: isComplete ? colors.text.primary :
                             isCurrent ? colors.accent.cyan :
                             colors.text.muted,
                      fontSize: '13px',
                    }}>
                      {phase.name}
                    </span>
                    {phaseCalls.length > 0 && (
                      <>
                        <span style={{
                          padding: '2px 8px',
                          background: colors.bg.primary,
                          borderRadius: '10px',
                          fontSize: '10px',
                          color: colors.text.muted,
                        }}>
                          {phaseCalls.filter(c => c.status === 'completed').length}/{phaseCalls.length} calls
                        </span>
                        <span style={{ color: colors.text.muted, fontSize: '10px' }}>
                          {isExpanded ? '▼' : '▶'}
                        </span>
                      </>
                    )}
                  </div>

                  {/* LLM calls for this phase */}
                  {isExpanded && phaseCalls.length > 0 && (
                    <div style={{ padding: '8px 0 8px 32px' }}>
                      {phaseCalls.map(call => (
                        <LLMCallCard key={call.call_id} call={call} />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Results summary */}
        {testResult?.status === 'completed' && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '12px',
            marginBottom: '16px',
            flexShrink: 0,
          }}>
            <div style={{ padding: '12px', background: colors.bg.tertiary, borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ color: colors.accent.cyan, fontSize: '20px', fontWeight: '600' }}>
                {testResult.problems_generated}
              </div>
              <div style={{ color: colors.text.muted, fontSize: '11px' }}>Problems</div>
            </div>
            <div style={{ padding: '12px', background: colors.bg.tertiary, borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ color: colors.accent.magenta, fontSize: '20px', fontWeight: '600' }}>
                {testResult.backdoors_generated}
              </div>
              <div style={{ color: colors.text.muted, fontSize: '11px' }}>Backdoors</div>
            </div>
            <div style={{ padding: '12px', background: colors.bg.tertiary, borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ color: colors.accent.amber, fontSize: '20px', fontWeight: '600' }}>
                {testResult.exploits_found}
              </div>
              <div style={{ color: colors.text.muted, fontSize: '11px' }}>Exploits</div>
            </div>
          </div>
        )}

        {/* Error message */}
        {testResult?.error && (
          <div style={{
            padding: '12px 16px',
            background: colors.accent.red + '20',
            border: `1px solid ${colors.accent.red}`,
            borderRadius: '6px',
            marginBottom: '16px',
            fontSize: '13px',
            color: colors.accent.red,
            flexShrink: 0,
          }}>
            {testResult.error}
          </div>
        )}

        {/* Close button */}
        {testResult?.status !== 'running' && (
          <button
            onClick={onClose}
            style={{
              width: '100%',
              padding: '12px',
              background: colors.bg.tertiary,
              border: `1px solid ${colors.border}`,
              borderRadius: '6px',
              color: colors.text.primary,
              fontSize: '13px',
              cursor: 'pointer',
              flexShrink: 0,
            }}
          >
            Close
          </button>
        )}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}
