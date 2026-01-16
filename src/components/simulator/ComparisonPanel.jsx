import { useState } from 'react';
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
