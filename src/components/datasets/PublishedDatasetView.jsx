import { useState, useEffect, Fragment } from 'react';
import { colors, API_BASE } from '../../constants';
import { STATUS_BADGES } from '../../datasetDefaults';
import { PhaseCallsSection } from './PhaseCallsSection';

function PublishedDatasetView({ dataset, onDuplicate, onDelete }) {
  const [expandedRows, setExpandedRows] = useState({});
  const [expandedPhases, setExpandedPhases] = useState({});
  const [problemResults, setProblemResults] = useState({});
  const [detailedResults, setDetailedResults] = useState({}); // Stores full results with llm_calls
  const [loadingDetails, setLoadingDetails] = useState({});
  const [loadingProblems, setLoadingProblems] = useState({});
  const [computingThreshold, setComputingThreshold] = useState(false);
  const [runningFromPhase, setRunningFromPhase] = useState({}); // {problemId: phase} when running
  const [thresholds, setThresholds] = useState({
    audit: dataset.audit_threshold,
    defer: dataset.defer_threshold,
    error: dataset.threshold_error
  });

  // Fetch problem results on mount
  useEffect(() => {
    fetchProblemResults();
  }, [dataset.id]);

  const fetchProblemResults = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/datasets/${dataset.id}/problems`);
      if (response.ok) {
        const data = await response.json();
        const resultsMap = {};
        data.problems.forEach(p => {
          resultsMap[p.problem_id] = p.result;
        });
        setProblemResults(resultsMap);
      }
    } catch (err) {
      console.error('Failed to fetch problem results:', err);
    }
  };

  const toggleRow = async (problemId) => {
    const willExpand = !expandedRows[problemId];
    setExpandedRows(prev => ({
      ...prev,
      [problemId]: willExpand
    }));

    // Fetch detailed results (with llm_calls) when expanding
    if (willExpand && !detailedResults[problemId] && !loadingDetails[problemId]) {
      setLoadingDetails(prev => ({ ...prev, [problemId]: true }));
      try {
        const response = await fetch(`${API_BASE}/api/datasets/${dataset.id}/problems/${problemId}`);
        if (response.ok) {
          const data = await response.json();
          if (data.result) {
            setDetailedResults(prev => ({ ...prev, [problemId]: data.result }));
          }
        }
      } catch (err) {
        console.error('Failed to fetch detailed results:', err);
      } finally {
        setLoadingDetails(prev => ({ ...prev, [problemId]: false }));
      }
    }
  };

  const togglePhase = (problemId, phase) => {
    const key = `${problemId}-${phase}`;
    setExpandedPhases(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const runProblem = async (problemId) => {
    setLoadingProblems(prev => ({ ...prev, [problemId]: true }));
    try {
      const apiKeys = loadApiKeys();
      const response = await fetch(`${API_BASE}/api/datasets/${dataset.id}/problems/${problemId}/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-OpenAI-Key': apiKeys.openai || '',
          'X-Anthropic-Key': apiKeys.anthropic || '',
        },
      });
      if (response.ok) {
        // Poll for results
        const pollInterval = setInterval(async () => {
          const resultRes = await fetch(`${API_BASE}/api/datasets/${dataset.id}/problems/${problemId}`);
          if (resultRes.ok) {
            const data = await resultRes.json();
            if (data.result) {
              // Update both problemResults and detailedResults (for llm_calls)
              setProblemResults(prev => ({ ...prev, [problemId]: data.result }));
              setDetailedResults(prev => ({ ...prev, [problemId]: data.result }));
              if (data.result.status === 'completed' || data.result.status === 'failed') {
                clearInterval(pollInterval);
                setLoadingProblems(prev => ({ ...prev, [problemId]: false }));
              }
            }
          }
        }, 2000);
        // Stop polling after 5 minutes
        setTimeout(() => clearInterval(pollInterval), 300000);
      }
    } catch (err) {
      console.error('Failed to run problem:', err);
      setLoadingProblems(prev => ({ ...prev, [problemId]: false }));
    }
  };

  const runFromPhase = async (problemId, fromPhase) => {
    setRunningFromPhase(prev => ({ ...prev, [problemId]: fromPhase }));
    try {
      const apiKeys = loadApiKeys();
      const response = await fetch(`${API_BASE}/api/datasets/${dataset.id}/problems/${problemId}/run-from-phase`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-OpenAI-Key': apiKeys.openai || '',
          'X-Anthropic-Key': apiKeys.anthropic || '',
        },
        body: JSON.stringify({ from_phase: fromPhase }),
      });
      if (response.ok) {
        // Poll for results
        const pollInterval = setInterval(async () => {
          const resultRes = await fetch(`${API_BASE}/api/datasets/${dataset.id}/problems/${problemId}`);
          if (resultRes.ok) {
            const data = await resultRes.json();
            if (data.result) {
              setProblemResults(prev => ({ ...prev, [problemId]: data.result }));
              setDetailedResults(prev => ({ ...prev, [problemId]: data.result }));
              if (data.result.status === 'completed' || data.result.status === 'failed') {
                clearInterval(pollInterval);
                setRunningFromPhase(prev => ({ ...prev, [problemId]: null }));
              }
            }
          }
        }, 2000);
        // Stop polling after 5 minutes
        setTimeout(() => clearInterval(pollInterval), 300000);
      } else {
        const errorData = await response.json();
        console.error('Failed to run from phase:', errorData);
        setRunningFromPhase(prev => ({ ...prev, [problemId]: null }));
      }
    } catch (err) {
      console.error('Failed to run from phase:', err);
      setRunningFromPhase(prev => ({ ...prev, [problemId]: null }));
    }
  };

  const computeThresholds = async () => {
    setComputingThreshold(true);
    try {
      const response = await fetch(`${API_BASE}/api/datasets/${dataset.id}/compute-thresholds`, {
        method: 'POST',
      });
      const data = await response.json();
      if (response.ok) {
        setThresholds({
          audit: data.audit_threshold,
          defer: data.defer_threshold,
          error: null
        });
      } else {
        setThresholds(prev => ({ ...prev, error: data.detail || 'Failed to compute thresholds' }));
      }
    } catch (err) {
      setThresholds(prev => ({ ...prev, error: err.message }));
    } finally {
      setComputingThreshold(false);
    }
  };

  const getPhaseIndicators = (result) => {
    const phases = [1, 2, 3, 4, 5];
    const completed = result?.phases_completed || [];
    const current = result?.current_phase;
    const failed = result?.status === 'failed';
    const failedPhase = failed ? current : null;

    return (
      <div style={{ display: 'flex', gap: '3px', alignItems: 'center' }}>
        {phases.map(phase => {
          let bg = colors.text.muted + '40'; // gray - inactive
          let color = colors.text.muted;

          if (completed.includes(phase)) {
            bg = colors.accent.green; // green - completed
            color = '#000';
          } else if (phase === current && !failed) {
            bg = colors.accent.amber; // yellow - in progress
            color = '#000';
          } else if (phase === failedPhase) {
            bg = colors.accent.red; // red - error
            color = '#fff';
          }

          return (
            <span
              key={phase}
              style={{
                width: '18px',
                height: '18px',
                borderRadius: '3px',
                background: bg,
                color: color,
                fontSize: '10px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {phase}
            </span>
          );
        })}
        {result?.error && (
          <span style={{ color: colors.accent.red, fontSize: '10px', marginLeft: '6px' }}>
            {result.error.includes('difficulty') ? 'Skipped (difficulty)' : 'Error'}
          </span>
        )}
      </div>
    );
  };

  const allComplete = dataset.problem_ids?.every(pid => {
    const result = problemResults[pid];
    return result?.status === 'completed' && (result?.phases_completed?.length || 0) >= 5;
  });

  return (
    <div style={{
      background: colors.bg.secondary,
      border: `1px solid ${colors.border}`,
      borderRadius: '8px',
      padding: '24px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <span style={{
          padding: '4px 10px',
          background: colors.accent.green + '20',
          borderRadius: '4px',
          fontSize: '11px',
          color: colors.accent.green,
          textTransform: 'uppercase',
        }}>
          Published
        </span>
        <span style={{ color: colors.text.muted, fontSize: '12px' }}>
          Published datasets cannot be edited
        </span>
      </div>

      <h3 style={{ color: colors.text.primary, margin: '0 0 16px 0', fontSize: '16px' }}>{dataset.name}</h3>

      {/* Settings */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '16px' }}>
        <div style={{ padding: '12px', background: colors.bg.tertiary, borderRadius: '6px' }}>
          <div style={{ color: colors.text.muted, fontSize: '11px', marginBottom: '4px' }}>Problems</div>
          <div style={{ color: colors.text.primary, fontSize: '16px', fontFamily: 'JetBrains Mono, monospace' }}>
            {dataset.problem_ids?.length || 0}
          </div>
        </div>
        <div style={{ padding: '12px', background: colors.bg.tertiary, borderRadius: '6px' }}>
          <div style={{ color: colors.text.muted, fontSize: '11px', marginBottom: '4px' }}>Backdoor Ideas</div>
          <div style={{ color: colors.text.primary, fontSize: '16px', fontFamily: 'JetBrains Mono, monospace' }}>
            {dataset.settings.num_backdoor_ideas}
          </div>
        </div>
        <div style={{ padding: '12px', background: colors.bg.tertiary, borderRadius: '6px' }}>
          <div style={{ color: colors.text.muted, fontSize: '11px', marginBottom: '4px' }}>Max Difficulty</div>
          <div style={{ color: colors.text.primary, fontSize: '16px', fontFamily: 'JetBrains Mono, monospace' }}>
            {dataset.settings.max_difficulty}
          </div>
        </div>
      </div>

      {/* Models */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ color: colors.text.muted, fontSize: '11px', marginBottom: '8px', textTransform: 'uppercase' }}>Models</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
          <div style={{ padding: '10px', background: colors.bg.tertiary, borderRadius: '6px' }}>
            <div style={{ color: colors.text.muted, fontSize: '10px', marginBottom: '2px' }}>Human (H)</div>
            <div style={{ color: colors.text.primary, fontSize: '13px', fontFamily: 'JetBrains Mono, monospace' }}>
              {dataset.models?.human_model || 'gpt-4o'}
            </div>
          </div>
          <div style={{ padding: '10px', background: colors.bg.tertiary, borderRadius: '6px' }}>
            <div style={{ color: colors.text.muted, fontSize: '10px', marginBottom: '2px' }}>Trusted (T)</div>
            <div style={{ color: colors.text.primary, fontSize: '13px', fontFamily: 'JetBrains Mono, monospace' }}>
              {dataset.models?.trusted_model || 'gpt-3.5-turbo'}
            </div>
          </div>
          <div style={{ padding: '10px', background: colors.bg.tertiary, borderRadius: '6px' }}>
            <div style={{ color: colors.text.muted, fontSize: '10px', marginBottom: '2px' }}>Untrusted (U)</div>
            <div style={{ color: colors.text.primary, fontSize: '13px', fontFamily: 'JetBrains Mono, monospace' }}>
              {dataset.models?.untrusted_model || 'gpt-4o'}
            </div>
          </div>
          <div style={{ padding: '10px', background: colors.bg.tertiary, borderRadius: '6px' }}>
            <div style={{ color: colors.text.muted, fontSize: '10px', marginBottom: '2px' }}>Red Team</div>
            <div style={{ color: colors.text.primary, fontSize: '13px', fontFamily: 'JetBrains Mono, monospace' }}>
              {dataset.models?.red_team_model || 'gpt-4o'}
            </div>
          </div>
        </div>
      </div>

      {/* Problems Table */}
      {dataset.problem_ids && dataset.problem_ids.length > 0 && (
        <div style={{ marginBottom: '16px' }}>
          <div style={{ color: colors.text.muted, fontSize: '11px', marginBottom: '8px', textTransform: 'uppercase' }}>
            Problems ({dataset.problem_ids.length})
          </div>
          <div style={{
            background: colors.bg.tertiary,
            borderRadius: '6px',
            overflow: 'hidden',
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${colors.border}` }}>
                  <th style={{ padding: '10px 12px', textAlign: 'left', color: colors.text.muted, fontSize: '11px', fontWeight: 500 }}>Problem ID</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left', color: colors.text.muted, fontSize: '11px', fontWeight: 500 }}>Status</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left', color: colors.text.muted, fontSize: '11px', fontWeight: 500 }}>Backdoor</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left', color: colors.text.muted, fontSize: '11px', fontWeight: 500 }}>Sneakiness</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right', color: colors.text.muted, fontSize: '11px', fontWeight: 500 }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {dataset.problem_ids.map(pid => {
                  const result = problemResults[pid];
                  const isExpanded = expandedRows[pid];
                  const isLoading = loadingProblems[pid];
                  const isComplete = result?.status === 'completed' && (result?.phases_completed?.length || 0) >= 5;

                  return (
                    <Fragment key={pid}>
                      <tr
                        style={{
                          borderBottom: isExpanded ? 'none' : `1px solid ${colors.border}`,
                          cursor: 'pointer',
                          background: isExpanded ? colors.bg.secondary : 'transparent',
                        }}
                        onClick={() => toggleRow(pid)}
                      >
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '13px', color: colors.text.primary }}>
                            {isExpanded ? '▼' : '▶'} {pid}
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px' }}>{getPhaseIndicators(result)}</td>
                        <td style={{ padding: '10px 12px' }}>
                          {(() => {
                            if (result?.difficulty_skipped) {
                              return <span style={{ color: colors.accent.amber }}>Skipped</span>;
                            }
                            const backdoorAttempts = result?.backdoor_attempts || [];
                            const sneakiestIdx = result?.sneakiest_backdoor_idx;
                            const hasBackdoor = sneakiestIdx != null && backdoorAttempts[sneakiestIdx];
                            if (hasBackdoor) {
                              return <span style={{ color: colors.accent.green }}>Yes</span>;
                            }
                            return <span style={{ color: colors.text.muted }}>No</span>;
                          })()}
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          {(() => {
                            const backdoorAttempts = result?.backdoor_attempts || [];
                            const sneakiestIdx = result?.sneakiest_backdoor_idx;
                            const sneakiest = sneakiestIdx != null ? backdoorAttempts[sneakiestIdx] : null;
                            if (sneakiest?.sneakiness != null) {
                              return <span style={{ fontFamily: 'JetBrains Mono, monospace', color: colors.text.primary }}>{sneakiest.sneakiness.toFixed(1)}</span>;
                            }
                            return <span style={{ color: colors.text.muted }}>—</span>;
                          })()}
                        </td>
                        <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                          <button
                            onClick={(e) => { e.stopPropagation(); runProblem(pid); }}
                            disabled={isLoading || isComplete}
                            style={{
                              padding: '6px 16px',
                              background: isComplete ? colors.accent.green : isLoading ? colors.accent.amber : colors.accent.cyan,
                              border: 'none',
                              borderRadius: '4px',
                              color: isComplete || isLoading ? '#000' : '#000',
                              fontSize: '12px',
                              fontWeight: 600,
                              cursor: isLoading || isComplete ? 'default' : 'pointer',
                              opacity: isComplete ? 0.8 : 1,
                            }}
                          >
                            {isLoading ? 'Running...' : isComplete ? '✓ Done' : 'Run'}
                          </button>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr style={{ borderBottom: `1px solid ${colors.border}` }}>
                          <td colSpan={5} style={{ padding: '0 12px 12px 32px', background: colors.bg.secondary }}>
                            {/* Error Message */}
                            {result?.error && (
                              <div style={{
                                marginTop: '12px',
                                padding: '8px 12px',
                                background: colors.accent.red + '15',
                                border: `1px solid ${colors.accent.red}40`,
                                borderRadius: '4px',
                                color: colors.accent.red,
                                fontSize: '11px',
                              }}>
                                {result.error}
                              </div>
                            )}

                            {/* Phases Section */}
                            {(() => {
                              const detailed = detailedResults[pid];
                              const isLoadingDetail = loadingDetails[pid];
                              // Check detailedResults first, fall back to result (which may have llm_calls from polling)
                              const llmCalls = detailed?.llm_calls || result?.llm_calls || [];

                              if (isLoadingDetail) {
                                return (
                                  <div style={{ marginTop: '16px', color: colors.text.muted, fontSize: '12px' }}>
                                    Loading phase details...
                                  </div>
                                );
                              }

                              // Show phases section even if no LLM calls (Phase 4 may have code execution)
                              const hasPhaseData = llmCalls.length > 0 || result?.phases_completed?.length > 0;
                              if (!hasPhaseData) {
                                return null;
                              }

                              return (
                                <div style={{ marginTop: '16px' }}>
                                  <div style={{
                                    color: colors.text.muted,
                                    fontSize: '11px',
                                    marginBottom: '8px',
                                    textTransform: 'uppercase',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                  }}>
                                    Phases
                                  </div>
                                  {[1, 2, 3, 4, 5].map(phase => (
                                    <PhaseCallsSection
                                      key={phase}
                                      phase={phase}
                                      calls={llmCalls}
                                      result={result}
                                      isExpanded={expandedPhases[`${pid}-${phase}`]}
                                      onToggle={() => togglePhase(pid, phase)}
                                      onRunFromHere={(fromPhase) => runFromPhase(pid, fromPhase)}
                                      isRunning={runningFromPhase[pid] != null}
                                    />
                                  ))}
                                </div>
                              );
                            })()}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Threshold Section */}
      <div style={{
        background: colors.bg.tertiary,
        borderRadius: '6px',
        padding: '16px',
        marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <div style={{ color: colors.text.muted, fontSize: '11px', textTransform: 'uppercase' }}>Thresholds (Phase 7)</div>
          <button
            onClick={computeThresholds}
            disabled={computingThreshold || !allComplete}
            style={{
              padding: '6px 16px',
              background: allComplete ? colors.accent.blue : colors.bg.secondary,
              border: `1px solid ${allComplete ? colors.accent.blue : colors.border}`,
              borderRadius: '4px',
              color: allComplete ? '#fff' : colors.text.muted,
              fontSize: '12px',
              cursor: computingThreshold || !allComplete ? 'default' : 'pointer',
              opacity: computingThreshold ? 0.7 : 1,
            }}
            title={!allComplete ? 'All problems must complete before computing thresholds' : ''}
          >
            {computingThreshold ? 'Computing...' : 'Calculate Thresholds'}
          </button>
        </div>

        {thresholds.error && (
          <div style={{ color: colors.accent.red, fontSize: '12px', marginBottom: '8px' }}>
            {thresholds.error}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div style={{ padding: '12px', background: colors.bg.secondary, borderRadius: '4px' }}>
            <div style={{ color: colors.text.muted, fontSize: '10px', marginBottom: '4px' }}>Audit Threshold (98th %ile)</div>
            <div style={{ color: colors.text.primary, fontSize: '20px', fontFamily: 'JetBrains Mono, monospace' }}>
              {thresholds.audit != null ? thresholds.audit.toFixed(3) : '—'}
            </div>
          </div>
          <div style={{ padding: '12px', background: colors.bg.secondary, borderRadius: '4px' }}>
            <div style={{ color: colors.text.muted, fontSize: '10px', marginBottom: '4px' }}>Defer Threshold (90th %ile)</div>
            <div style={{ color: colors.text.primary, fontSize: '20px', fontFamily: 'JetBrains Mono, monospace' }}>
              {thresholds.defer != null ? thresholds.defer.toFixed(3) : '—'}
            </div>
          </div>
        </div>
      </div>

      {/* Action buttons for published dataset */}
      <div style={{ display: 'flex', gap: '12px', borderTop: `1px solid ${colors.border}`, paddingTop: '16px' }}>
        <button
          onClick={() => onDuplicate(dataset.id)}
          style={{
            padding: '10px 20px',
            background: colors.bg.tertiary,
            border: `1px solid ${colors.border}`,
            borderRadius: '6px',
            color: colors.text.secondary,
            fontSize: '13px',
            cursor: 'pointer',
          }}
        >
          Duplicate
        </button>
        <button
          onClick={() => onDelete(dataset.id)}
          style={{
            padding: '10px 20px',
            background: 'transparent',
            border: `1px solid ${colors.accent.red}40`,
            borderRadius: '6px',
            color: colors.accent.red,
            fontSize: '13px',
            cursor: 'pointer',
          }}
        >
          Delete
        </button>
      </div>
    </div>
  );
}

export { PublishedDatasetView };
