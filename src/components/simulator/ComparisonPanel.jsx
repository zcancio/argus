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

  // Fetch dataset info when dataset changes and reset results
  useEffect(() => {
    if (!selectedDatasetId) {
      setDatasetInfo(null);
      setSimulationParams(null);
      setResults({});
      return;
    }

    // Reset state for new dataset
    setSimulationParams(null);
    setResults({});

    const fetchDatasetInfo = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/local-datasets/${selectedDatasetId}`);
        if (response.ok) {
          const data = await response.json();
          setDatasetInfo(data);
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
          // Protocol-specific config
          monitor_type: protocolConfig.monitor_type,
          audit_budget_rate: protocolConfig.audit_budget_rate,
          free_start: protocolConfig.free_start,
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
            free_start: result.config.blue_team?.free_start,
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

      {/* Summary Panel - Shows after simulations complete */}
      {selectedDatasetId && completedCount > 0 && (datasetInfo || simulationParams) && (
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
            Simulation Parameters
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
                    <span style={{ color: colors.text.muted }}>Viable Problems</span>
                    <span style={{ color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace' }}>
                      {datasetInfo.stats?.completed || '-'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: colors.text.muted }}>Successful Coups</span>
                    <span style={{ color: colors.accent.green, fontFamily: 'JetBrains Mono, monospace' }}>
                      {datasetInfo.stats?.successful_coups || 0}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: colors.text.muted }}>Failed Coup Attempts</span>
                    <span style={{ color: colors.text.secondary, fontFamily: 'JetBrains Mono, monospace' }}>
                      {datasetInfo.stats?.failed_coup_attempts || 0}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Models */}
            {datasetInfo?.models && (
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
                  Models
                </div>
                <div style={{ display: 'grid', gap: '8px', fontSize: '13px' }}>
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

            {/* Simulation Settings */}
            {simulationParams && (
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
                  Simulation Settings
                </div>
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
                      {simulationParams.free_start || 10}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: colors.text.muted }}>Coup Subsample</span>
                    <span style={{ color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace' }}>
                      {((simulationParams.coup_subsample_rate || 1/12) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            )}
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
