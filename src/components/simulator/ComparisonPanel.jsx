import { useState, useEffect } from 'react';
import { colors, API_BASE } from '../../constants';
import { PAPER_RESULTS, PROTOCOL_CONFIGS, PROTOCOL_ORDER } from '../../paperResults';
import { ComparisonTable } from './ComparisonTable';
import { ComparisonChart } from './ComparisonChart';

export function ComparisonPanel({ selectedDatasetId, baseConfig }) {
  const [results, setResults] = useState({});
  const [isRunning, setIsRunning] = useState(false);
  const [currentProtocol, setCurrentProtocol] = useState(null);
  const [progress, setProgress] = useState({ completed: 0, total: 0 });
  const [error, setError] = useState(null);
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [simulationParams, setSimulationParams] = useState(null);
  const [problems, setProblems] = useState([]);

  // Fetch dataset info and problems when dataset changes and reset results
  useEffect(() => {
    if (!selectedDatasetId) {
      setDatasetInfo(null);
      setSimulationParams(null);
      setResults({});
      setProblems([]);
      return;
    }

    // Reset state for new dataset
    setSimulationParams(null);
    setResults({});
    setProblems([]);

    const fetchDatasetInfo = async () => {
      try {
        const [infoRes, problemsRes] = await Promise.all([
          fetch(`${API_BASE}/api/local-datasets/${selectedDatasetId}`),
          fetch(`${API_BASE}/api/local-datasets/${selectedDatasetId}/problems`),
        ]);
        if (infoRes.ok) {
          const data = await infoRes.json();
          setDatasetInfo(data);
        }
        if (problemsRes.ok) {
          const data = await problemsRes.json();
          setProblems(data.problems || []);
        }
      } catch (err) {
        console.error('Failed to fetch dataset info:', err);
      }
    };

    fetchDatasetInfo();
  }, [selectedDatasetId]);

  const runAllProtocols = async () => {
    if (!selectedDatasetId) {
      setError('Please select a dataset first');
      return;
    }

    setIsRunning(true);
    setError(null);
    setProgress({ completed: 0, total: PROTOCOL_ORDER.length });

    // Initialize all protocols as pending
    const initialResults = {};
    PROTOCOL_ORDER.forEach(key => {
      initialResults[key] = { status: 'pending' };
    });
    setResults(initialResults);

    for (const protocolKey of PROTOCOL_ORDER) {
      setCurrentProtocol(protocolKey);

      try {
        const protocolConfig = PROTOCOL_CONFIGS[protocolKey];

        const simulationRequest = {
          dataset_id: selectedDatasetId,
          backdoor_rate: baseConfig.backdoor_rate,
          max_fail_rate: baseConfig.max_fail_rate,
          num_trials: baseConfig.num_trials,
          num_problems: baseConfig.num_problems,
          coup_subsample_rate: baseConfig.coup_subsample_rate,
          filter_inverted: true,  // Always filter inverted T monitoring problems
          // Protocol-specific config
          monitor_type: protocolConfig.monitor_type,
          audit_budget_rate: protocolConfig.audit_budget_rate,
          free_start_rate: baseConfig.free_start_rate || 0.002,
          defer_enabled: protocolConfig.defer_enabled,
          defer_rate: protocolConfig.defer_rate,
          defer_action: protocolConfig.defer_action,
        };

        const response = await fetch(`${API_BASE}/api/simulate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(simulationRequest),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Simulation failed');
        }

        const result = await response.json();

        // Store simulation parameters from first successful result
        if (!simulationParams && result.config) {
          setSimulationParams({
            num_trials: result.config.num_trials,
            num_problems: result.config.num_problems,
            num_problems_requested: result.config.num_problems_requested,
            audit_budget_rate: result.config.blue_team?.audit_budget_rate,
            free_start_rate: result.config.blue_team?.free_start_rate,
            free_start_actual: result.config.blue_team?.free_start_actual,
            defer_rate: result.config.blue_team?.defer_rate,
            coup_subsample_rate: result.config.coup_subsample_rate,
            backdoor_rate: result.config.red_team?.backdoor_rate,
          });
        }

        setResults(prev => ({
          ...prev,
          [protocolKey]: {
            safety: result.results.safety,
            safety_se: result.results.safety_se,
            usefulness: result.results.usefulness,
            usefulness_se: result.results.usefulness_se,
            status: 'complete',
            timestamp: new Date().toISOString(),
          }
        }));
      } catch (err) {
        setResults(prev => ({
          ...prev,
          [protocolKey]: {
            status: 'error',
            error: err.message,
          }
        }));
      }

      setProgress(prev => ({ ...prev, completed: prev.completed + 1 }));
    }

    setCurrentProtocol(null);
    setIsRunning(false);
  };

  // Prepare chart data
  const paperData = PROTOCOL_ORDER.map(key => ({
    protocol: key,
    name: PROTOCOL_CONFIGS[key].name,
    shortName: PROTOCOL_CONFIGS[key].shortName,
    safety: PAPER_RESULTS[key].safety,
    usefulness: PAPER_RESULTS[key].usefulness,
  }));

  const simData = PROTOCOL_ORDER
    .filter(key => results[key]?.status === 'complete')
    .map(key => ({
      protocol: key,
      name: PROTOCOL_CONFIGS[key].name,
      shortName: PROTOCOL_CONFIGS[key].shortName,
      safety: results[key].safety,
      usefulness: results[key].usefulness,
      safety_se: results[key].safety_se,
      usefulness_se: results[key].usefulness_se,
    }));

  const completedCount = Object.values(results).filter(r => r.status === 'complete').length;

  return (
    <div>
      {/* Header with Run All button */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '24px',
      }}>
        <div>
          <h2 style={{
            color: colors.text.primary,
            margin: 0,
            fontSize: '18px',
            fontWeight: '600',
          }}>
            Paper vs Simulation Comparison
          </h2>
          {completedCount > 0 && (
            <p style={{
              color: colors.text.secondary,
              margin: '4px 0 0 0',
              fontSize: '12px',
            }}>
              {completedCount} of {PROTOCOL_ORDER.length} protocols completed
            </p>
          )}
        </div>

        <button
          onClick={runAllProtocols}
          disabled={isRunning || !selectedDatasetId}
          style={{
            padding: '12px 24px',
            background: isRunning ? colors.bg.tertiary : colors.accent.cyan,
            border: 'none',
            borderRadius: '6px',
            color: isRunning ? colors.text.muted : colors.bg.primary,
            fontWeight: '600',
            fontSize: '14px',
            cursor: isRunning || !selectedDatasetId ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          {isRunning ? (
            <>
              <span style={{
                display: 'inline-block',
                width: '12px',
                height: '12px',
                border: `2px solid ${colors.text.muted}`,
                borderTopColor: 'transparent',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
              }} />
              Running {progress.completed}/{progress.total}...
            </>
          ) : (
            'Run All Protocols'
          )}
        </button>
      </div>

      {/* Error display */}
      {error && (
        <div style={{
          background: colors.accent.red + '20',
          border: `1px solid ${colors.accent.red}`,
          borderRadius: '6px',
          padding: '12px 16px',
          marginBottom: '16px',
          color: colors.accent.red,
          fontSize: '13px',
        }}>
          {error}
        </div>
      )}

      {/* No dataset selected message */}
      {!selectedDatasetId && (
        <div style={{
          background: colors.bg.secondary,
          border: `1px solid ${colors.border}`,
          borderRadius: '8px',
          padding: '48px',
          textAlign: 'center',
          color: colors.text.muted,
        }}>
          Select a dataset to run comparison simulations
        </div>
      )}

      {/* Dataset Info Panel - Shows when dataset selected */}
      {selectedDatasetId && datasetInfo && (
        <div style={{
          background: colors.bg.secondary,
          border: `1px solid ${colors.border}`,
          borderRadius: '8px',
          padding: '24px',
          marginBottom: '16px',
        }}>
          <h3 style={{
            color: colors.text.primary,
            margin: '0 0 16px 0',
            fontSize: '14px',
            textTransform: 'uppercase',
            letterSpacing: '1px',
          }}>
            Dataset Info
          </h3>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: '24px',
          }}>
            {/* Dataset Info */}
            {datasetInfo && (
              <div>
                <div style={{
                  fontSize: '11px',
                  color: colors.text.muted,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  marginBottom: '12px',
                  paddingBottom: '8px',
                  borderBottom: `1px solid ${colors.border}`,
                }}>
                  Dataset
                </div>
                <div style={{ display: 'grid', gap: '8px', fontSize: '13px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: colors.text.muted }}>Name</span>
                    <span style={{ color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace' }}>
                      {datasetInfo.name || selectedDatasetId}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: colors.text.muted }}>Total Problems</span>
                    <span style={{ color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace' }}>
                      {datasetInfo.stats?.completed ?? '-'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: colors.text.muted }}>Inverted (T_bd {'<'} T_norm)</span>
                    <span style={{ color: colors.text.secondary, fontFamily: 'JetBrains Mono, monospace' }}>
                      {datasetInfo.stats?.inverted_t_monitoring ?? 0}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: colors.text.muted }}>Viable Problems</span>
                    <span style={{ color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace' }}>
                      {datasetInfo.stats?.viable_problems ?? (datasetInfo.stats?.completed - (datasetInfo.stats?.inverted_t_monitoring || 0)) ?? '-'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: colors.text.muted }}>Problems w/ Backdoors</span>
                    <span style={{ color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace' }}>
                      {(datasetInfo.stats?.completed || 0) - (datasetInfo.stats?.no_backdoor || 0)}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: colors.text.muted }}>Usable Backdoors</span>
                    <span style={{ color: colors.accent.green, fontFamily: 'JetBrains Mono, monospace' }}>
                      {(datasetInfo.stats?.successful_coups || 0) + (datasetInfo.stats?.failed_coup_attempts || 0)}
                      <span style={{ color: colors.text.muted, fontSize: '11px' }}>
                        {' '}({datasetInfo.stats?.successful_coups || 0} coup + {datasetInfo.stats?.failed_coup_attempts || 0} failed)
                      </span>
                    </span>
                  </div>
                </div>

                {/* Models sub-section */}
                {datasetInfo.models && (
                  <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: `1px solid ${colors.border}` }}>
                    <div style={{ fontSize: '11px', color: colors.text.muted, marginBottom: '8px' }}>
                      Models
                    </div>
                    <div style={{ display: 'grid', gap: '6px', fontSize: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: colors.text.muted }}>Trusted (T)</span>
                        <span style={{ color: colors.accent.cyan, fontFamily: 'JetBrains Mono, monospace' }}>
                          {datasetInfo.models.trusted_model}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: colors.text.muted }}>Untrusted (U)</span>
                        <span style={{ color: colors.accent.magenta, fontFamily: 'JetBrains Mono, monospace' }}>
                          {datasetInfo.models.untrusted_model}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: colors.text.muted }}>Red Team</span>
                        <span style={{ color: colors.accent.red, fontFamily: 'JetBrains Mono, monospace' }}>
                          {datasetInfo.models.red_team_model}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Backdoor Details */}
            {datasetInfo && (
              <div>
                <div style={{
                  fontSize: '11px',
                  color: colors.text.muted,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  marginBottom: '12px',
                  paddingBottom: '8px',
                  borderBottom: `1px solid ${colors.border}`,
                }}>
                  Backdoor Details
                </div>
                <div style={{ display: 'grid', gap: '8px', fontSize: '13px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: colors.text.muted }}>Successful Coups</span>
                    <span style={{ color: colors.accent.green, fontFamily: 'JetBrains Mono, monospace' }}>
                      {datasetInfo.stats?.successful_coups || 0}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: colors.text.muted }}>Failed Coup Attempts</span>
                    <span style={{ color: colors.accent.red, fontFamily: 'JetBrains Mono, monospace' }}>
                      {datasetInfo.stats?.failed_coup_attempts || 0}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: colors.text.muted }}>No Backdoor</span>
                    <span style={{ color: colors.text.secondary, fontFamily: 'JetBrains Mono, monospace' }}>
                      {datasetInfo.stats?.no_backdoor || 0}
                    </span>
                  </div>
                </div>

                {/* Suspicion Score Distribution */}
                {datasetInfo.summary?.suspicion_stats && (
                  <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: `1px solid ${colors.border}` }}>
                    <div style={{ fontSize: '11px', color: colors.text.muted, marginBottom: '8px' }}>
                      T Suspicion Scores
                    </div>
                    <div style={{ display: 'grid', gap: '6px', fontSize: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ color: colors.text.muted }}>Normal Solutions</span>
                        <span style={{ color: colors.accent.cyan, fontFamily: 'JetBrains Mono, monospace' }}>
                          avg: {datasetInfo.summary.suspicion_stats.avg_t_normal?.toFixed(2) || '-'}
                          <span style={{ color: colors.text.muted, fontSize: '11px' }}> (n={datasetInfo.summary.suspicion_stats.t_normal_count || 0})</span>
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ color: colors.text.muted }}>Backdoor Solutions</span>
                        <span style={{ color: colors.accent.red, fontFamily: 'JetBrains Mono, monospace' }}>
                          avg: {datasetInfo.summary.suspicion_stats.avg_t_backdoor?.toFixed(2) || '-'}
                          <span style={{ color: colors.text.muted, fontSize: '11px' }}> (n={datasetInfo.summary.suspicion_stats.t_backdoor_count || 0})</span>
                        </span>
                      </div>
                      {datasetInfo.summary.suspicion_stats.avg_t_backdoor && datasetInfo.summary.suspicion_stats.avg_t_normal && (
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ color: colors.text.muted }}>Difference (bd - norm)</span>
                          <span style={{
                            color: (datasetInfo.summary.suspicion_stats.avg_t_backdoor - datasetInfo.summary.suspicion_stats.avg_t_normal) > 0
                              ? colors.accent.amber
                              : colors.accent.green,
                            fontFamily: 'JetBrains Mono, monospace',
                          }}>
                            {(datasetInfo.summary.suspicion_stats.avg_t_backdoor - datasetInfo.summary.suspicion_stats.avg_t_normal) > 0 ? '+' : ''}
                            {(datasetInfo.summary.suspicion_stats.avg_t_backdoor - datasetInfo.summary.suspicion_stats.avg_t_normal).toFixed(2)}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Sneakiness Stats */}
                {datasetInfo.summary?.backdoor_stats && (
                  <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: `1px solid ${colors.border}` }}>
                    <div style={{ fontSize: '11px', color: colors.text.muted, marginBottom: '8px' }}>
                      Sneakiness Scores
                    </div>
                    <div style={{ display: 'grid', gap: '6px', fontSize: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: colors.text.muted }}>Total Generated</span>
                        <span style={{ color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace' }}>
                          {datasetInfo.summary.backdoor_stats.total_generated || 0}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: colors.text.muted }}>Above Threshold (≥20)</span>
                        <span style={{ color: colors.accent.green, fontFamily: 'JetBrains Mono, monospace' }}>
                          {datasetInfo.summary.backdoor_stats.above_threshold || 0}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: colors.text.muted }}>Avg Sneakiness</span>
                        <span style={{ color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace' }}>
                          {datasetInfo.summary.backdoor_stats.avg_sneakiness?.toFixed(1) || '-'}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: colors.text.muted }}>Max Sneakiness</span>
                        <span style={{ color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace' }}>
                          {datasetInfo.summary.backdoor_stats.max_sneakiness?.toFixed(1) || '-'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Backdoor Suspicion Score Distribution */}
                {problems.length > 0 && (() => {
                  const backdoorScores = problems
                    .filter(p => p.T_suspicion_backdoor !== null && p.T_suspicion_backdoor !== undefined)
                    .map(p => ({
                      problemId: p.problem_id,
                      score: p.T_suspicion_backdoor,
                      normalScore: p.T_suspicion_normal,
                      status: p.status,
                      sneakiness: p.sneakiness,
                    }))
                    .sort((a, b) => a.score - b.score);

                  if (backdoorScores.length === 0) return null;

                  return (
                    <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: `1px solid ${colors.border}` }}>
                      <div style={{ fontSize: '11px', color: colors.text.muted, marginBottom: '8px' }}>
                        Backdoor T Suspicion Distribution ({backdoorScores.length} scores)
                      </div>
                      <div style={{
                        maxHeight: '200px',
                        overflowY: 'auto',
                        background: colors.bg.tertiary,
                        borderRadius: '4px',
                        padding: '8px',
                      }}>
                        <div style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
                          gap: '4px',
                          fontSize: '11px',
                          fontFamily: 'JetBrains Mono, monospace',
                        }}>
                          {backdoorScores.map((item, idx) => (
                            <div
                              key={item.problemId}
                              style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                padding: '2px 6px',
                                borderRadius: '3px',
                                background: item.status === 'successful_coup'
                                  ? colors.accent.green + '20'
                                  : item.status === 'failed_coup_attempt'
                                  ? colors.accent.red + '20'
                                  : 'transparent',
                              }}
                              title={`Problem ${item.problemId}\nStatus: ${item.status}\nBackdoor: ${item.score.toFixed(2)}, Normal: ${item.normalScore?.toFixed(2) || '-'}${item.sneakiness ? `\nSneakiness: ${item.sneakiness.toFixed(1)}` : ''}`}
                            >
                              <span style={{ color: colors.text.muted }}>{idx + 1}.</span>
                              <span style={{
                                color: item.status === 'successful_coup'
                                  ? colors.accent.green
                                  : item.status === 'failed_coup_attempt'
                                  ? colors.accent.red
                                  : colors.text.secondary,
                              }}>
                                {item.score.toFixed(2)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div style={{ fontSize: '10px', color: colors.text.muted, marginTop: '6px' }}>
                        <span style={{ color: colors.accent.green }}>■</span> successful coup{' '}
                        <span style={{ color: colors.accent.red }}>■</span> failed attempt
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Simulation Settings Panel - Shows after simulations complete */}
      {selectedDatasetId && completedCount > 0 && simulationParams && (
        <div style={{
          background: colors.bg.secondary,
          border: `1px solid ${colors.border}`,
          borderRadius: '8px',
          padding: '24px',
          marginBottom: '16px',
        }}>
          <h3 style={{
            color: colors.text.primary,
            margin: '0 0 16px 0',
            fontSize: '14px',
            textTransform: 'uppercase',
            letterSpacing: '1px',
          }}>
            Simulation Settings
          </h3>

          <div style={{ display: 'grid', gap: '8px', fontSize: '13px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: colors.text.muted }}>Num Trials</span>
              <span style={{ color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace' }}>
                {simulationParams.num_trials?.toLocaleString()}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: colors.text.muted }}>Problems per Trial</span>
              <span style={{ color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace' }}>
                {simulationParams.num_problems}
                {simulationParams.num_problems_requested === null && (
                  <span style={{ color: colors.text.muted, fontSize: '11px' }}> (auto)</span>
                )}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: colors.text.muted }}>Audit Budget</span>
              <span style={{ color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace' }}>
                {((simulationParams.audit_budget_rate || 0.02) * 100).toFixed(0)}%
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: colors.text.muted }}>Free Start Audits</span>
              <span style={{ color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace' }}>
                {simulationParams.free_start_actual || Math.ceil((simulationParams.num_problems || 0) * (simulationParams.free_start_rate || 0.002))}
                <span style={{ color: colors.text.muted, fontSize: '11px' }}> ({((simulationParams.free_start_rate || 0.002) * 100).toFixed(1)}%)</span>
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: colors.text.muted }}>Coup Subsample</span>
              <span style={{ color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace' }}>
                {(() => {
                  const rate = simulationParams.coup_subsample_rate || 1/12;
                  const categories = [
                    { name: 'Common', rate: 1/3 },
                    { name: 'Sometimes', rate: 1/6 },
                    { name: 'Rarely', rate: 1/12 },
                    { name: 'Very Rarely', rate: 1/50 },
                    { name: 'Very Very Rarely', rate: 1/300 },
                  ];
                  const match = categories.find(c => Math.abs(c.rate - rate) < 0.01);
                  const pct = (rate * 100).toFixed(1);
                  return match ? `${match.name} (${pct}%)` : `${pct}%`;
                })()}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: colors.text.muted }}>Backdoor Rate</span>
              <span style={{ color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace' }}>
                {((simulationParams.backdoor_rate || 0.20) * 100).toFixed(0)}%
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: colors.text.muted }}>Expected Backdoors/Trial</span>
              <span style={{ color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace' }}>
                {((simulationParams.num_problems || 0) * (simulationParams.backdoor_rate || 0.20)).toFixed(1)}
              </span>
            </div>
          </div>

          {/* Frequency Distribution Table */}
          <div style={{
            marginTop: '16px',
            paddingTop: '12px',
            borderTop: `1px solid ${colors.border}`,
          }}>
            <div style={{
              fontSize: '11px',
              color: colors.text.muted,
              marginBottom: '8px',
            }}>
              Paper Frequency Categories
            </div>
            <div style={{ display: 'grid', gap: '4px', fontSize: '12px' }}>
              {[
                { name: 'Common', rate: 1/3 },
                { name: 'Sometimes', rate: 1/6 },
                { name: 'Rarely', rate: 1/12 },
                { name: 'Very Rarely', rate: 1/50 },
                { name: 'Very Very Rarely', rate: 1/300 },
              ].map(({ name, rate }) => {
                const numProblems = simulationParams.num_problems || 0;
                const expected = numProblems * rate;
                const currentRate = simulationParams.backdoor_rate || 0.20;
                const isActive = Math.abs(rate - currentRate) < 0.01;
                return (
                  <div key={name} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    background: isActive ? colors.accent.cyan + '20' : 'transparent',
                    border: isActive ? `1px solid ${colors.accent.cyan}40` : '1px solid transparent',
                  }}>
                    <span style={{ color: isActive ? colors.accent.cyan : colors.text.muted }}>
                      {name} (1/{Math.round(1/rate)})
                    </span>
                    <span style={{
                      color: isActive ? colors.accent.cyan : colors.text.secondary,
                      fontFamily: 'JetBrains Mono, monospace',
                    }}>
                      {(rate * 100).toFixed(1)}% → {expected.toFixed(1)} bd/trial
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Chart and Table */}
      {selectedDatasetId && (
        <>
          <ComparisonChart paperData={paperData} simData={simData} />
          <ComparisonTable results={results} runningProtocol={currentProtocol} />
        </>
      )}

      {/* CSS for spinner animation */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
