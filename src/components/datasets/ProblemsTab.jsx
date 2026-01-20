import { useState, useEffect } from 'react';
import { colors, API_BASE } from '../../constants';
import { PhaseCallsSection } from './PhaseCallsSection';

function ProblemsTab({ datasetId }) {
  const [problems, setProblems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [appsBrowser, setAppsBrowser] = useState({ open: false, problems: [], total: 0, difficulties: {} });
  const [manualId, setManualId] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState('interview');
  const [computingThresholds, setComputingThresholds] = useState(false);
  const [thresholdResult, setThresholdResult] = useState(null);

  const fetchProblems = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/datasets/${datasetId}/problems`);
      if (res.ok) {
        const data = await res.json();
        setProblems(data.problems || []);
      }
    } catch (e) {
      console.error('Failed to fetch problems:', e);
    }
  };

  useEffect(() => {
    if (datasetId) {
      fetchProblems();
    }
  }, [datasetId]);

  const openAppsBrowser = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/apps/problems?difficulty=${difficultyFilter}&limit=50`);
      if (res.ok) {
        const data = await res.json();
        setAppsBrowser({
          open: true,
          problems: data.problems || [],
          total: data.total,
          difficulties: data.difficulties || {}
        });
      }
    } catch (e) {
      console.error('Failed to load APPS problems:', e);
    }
  };

  const addProblem = async (problemId) => {
    try {
      const res = await fetch(`${API_BASE}/api/datasets/${datasetId}/problems`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ problem_ids: [problemId] })
      });
      if (res.ok) {
        fetchProblems();
      }
    } catch (e) {
      console.error('Failed to add problem:', e);
    }
  };

  const removeProblem = async (problemId) => {
    try {
      const res = await fetch(`${API_BASE}/api/datasets/${datasetId}/problems/${problemId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchProblems();
      }
    } catch (e) {
      console.error('Failed to remove problem:', e);
    }
  };

  const runProblem = async (problemId) => {
    try {
      // Get API keys using the secure storage loader
      const apiKeys = loadApiKeys();

      const res = await fetch(`${API_BASE}/api/datasets/${datasetId}/problems/${problemId}/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(apiKeys.openai && { 'X-OpenAI-Key': apiKeys.openai }),
          ...(apiKeys.anthropic && { 'X-Anthropic-Key': apiKeys.anthropic }),
        }
      });
      if (res.ok) {
        // Start polling for updates
        const pollInterval = setInterval(async () => {
          await fetchProblems();
          const updated = problems.find(p => p.problem_id === problemId);
          if (updated?.result?.status === 'completed' || updated?.result?.status === 'failed') {
            clearInterval(pollInterval);
          }
        }, 2000);
      }
    } catch (e) {
      console.error('Failed to run problem:', e);
    }
  };

  const computeThresholds = async () => {
    setComputingThresholds(true);
    try {
      const res = await fetch(`${API_BASE}/api/datasets/${datasetId}/compute-thresholds`, {
        method: 'POST'
      });
      const data = await res.json();
      if (res.ok) {
        setThresholdResult({ success: true, ...data });
      } else {
        setThresholdResult({ success: false, error: data.detail || 'Failed to compute thresholds' });
      }
    } catch (e) {
      setThresholdResult({ success: false, error: e.message });
    }
    setComputingThresholds(false);
  };

  const handleAddManualId = () => {
    if (manualId.trim()) {
      addProblem(manualId.trim());
      setManualId('');
    }
  };

  const statusColors = {
    pending: colors.text.muted,
    running: colors.accent.amber,
    completed: colors.accent.green,
    failed: colors.accent.red,
  };

  const completedCount = problems.filter(p => p.result?.status === 'completed').length;
  const allComplete = problems.length > 0 && completedCount === problems.length;

  return (
    <div>
      {/* Add Problems Section */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
          <input
            type="text"
            value={manualId}
            onChange={(e) => setManualId(e.target.value)}
            placeholder="Enter problem ID (e.g., 0042)"
            style={{
              flex: 1,
              padding: '8px 12px',
              background: colors.bg.tertiary,
              border: `1px solid ${colors.border}`,
              borderRadius: '6px',
              color: colors.text.primary,
              fontSize: '13px',
            }}
          />
          <button
            onClick={handleAddManualId}
            style={{
              padding: '8px 16px',
              background: colors.accent.cyan + '20',
              border: `1px solid ${colors.accent.cyan}`,
              borderRadius: '6px',
              color: colors.accent.cyan,
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            Add
          </button>
          <button
            onClick={openAppsBrowser}
            style={{
              padding: '8px 16px',
              background: colors.bg.tertiary,
              border: `1px solid ${colors.border}`,
              borderRadius: '6px',
              color: colors.text.secondary,
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            Browse APPS
          </button>
        </div>
      </div>

      {/* Problem List */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <span style={{ color: colors.text.secondary, fontSize: '13px' }}>
            {problems.length} problems ({completedCount} completed)
          </span>
        </div>

        {problems.length === 0 ? (
          <div style={{
            padding: '24px',
            background: colors.bg.tertiary,
            borderRadius: '6px',
            textAlign: 'center',
            color: colors.text.muted,
            fontSize: '13px',
          }}>
            No problems added yet. Add problems using the ID field or browse APPS.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '300px', overflowY: 'auto' }}>
            {problems.map(p => (
              <div key={p.problem_id} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '10px 12px',
                background: colors.bg.tertiary,
                borderRadius: '6px',
                border: `1px solid ${colors.border}`,
              }}>
                {/* Status indicator */}
                <div style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: p.result ? statusColors[p.result.status] : colors.text.muted,
                }} />

                {/* Problem ID */}
                <span style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: '12px',
                  color: colors.text.primary,
                  width: '60px',
                }}>
                  {p.problem_id}
                </span>

                {/* Difficulty */}
                {p.difficulty && (
                  <span style={{
                    padding: '2px 6px',
                    background: p.difficulty === 'competition' ? colors.accent.red + '20' :
                               p.difficulty === 'interview' ? colors.accent.amber + '20' :
                               colors.accent.green + '20',
                    borderRadius: '4px',
                    fontSize: '10px',
                    color: p.difficulty === 'competition' ? colors.accent.red :
                           p.difficulty === 'interview' ? colors.accent.amber :
                           colors.accent.green,
                  }}>
                    {p.difficulty}
                  </span>
                )}

                {/* Status */}
                {p.result && (
                  <span style={{
                    fontSize: '11px',
                    color: statusColors[p.result.status],
                  }}>
                    {p.result.status === 'running' && p.result.current_phase && `Phase ${p.result.current_phase}`}
                    {p.result.status === 'completed' && (
                      <span style={{ display: 'flex', gap: '8px' }}>
                        <span style={{ color: colors.accent.cyan }}>
                          T={p.result.T_suspicion_normal?.toFixed(1) ?? '?'}
                        </span>
                        <span style={{ color: colors.accent.magenta }}>
                          U={p.result.U_suspicion_normal?.toFixed(1) ?? '?'}
                        </span>
                      </span>
                    )}
                    {p.result.status === 'failed' && 'Failed'}
                  </span>
                )}

                <div style={{ flex: 1 }} />

                {/* Actions */}
                {(!p.result || p.result.status === 'failed') && (
                  <button
                    onClick={() => runProblem(p.problem_id)}
                    style={{
                      padding: '4px 12px',
                      background: colors.accent.cyan + '20',
                      border: `1px solid ${colors.accent.cyan}`,
                      borderRadius: '4px',
                      color: colors.accent.cyan,
                      fontSize: '11px',
                      cursor: 'pointer',
                    }}
                  >
                    Run
                  </button>
                )}

                <button
                  onClick={() => removeProblem(p.problem_id)}
                  style={{
                    padding: '4px 8px',
                    background: 'transparent',
                    border: `1px solid ${colors.accent.red}40`,
                    borderRadius: '4px',
                    color: colors.accent.red,
                    fontSize: '11px',
                    cursor: 'pointer',
                  }}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Compute Thresholds */}
      <div style={{
        padding: '16px',
        background: colors.bg.tertiary,
        borderRadius: '6px',
        border: `1px solid ${colors.border}`,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: thresholdResult ? '12px' : 0 }}>
          <button
            onClick={computeThresholds}
            disabled={!allComplete || computingThresholds}
            style={{
              padding: '10px 20px',
              background: allComplete ? colors.accent.magenta + '20' : colors.bg.tertiary,
              border: `1px solid ${allComplete ? colors.accent.magenta : colors.border}`,
              borderRadius: '6px',
              color: allComplete ? colors.accent.magenta : colors.text.muted,
              fontSize: '13px',
              cursor: allComplete ? 'pointer' : 'not-allowed',
            }}
          >
            {computingThresholds ? 'Computing...' : 'Compute Thresholds'}
          </button>
          <span style={{ color: colors.text.muted, fontSize: '12px' }}>
            {allComplete ? 'All problems complete' : `${problems.length - completedCount} problems remaining`}
          </span>
        </div>

        {thresholdResult && (
          <div style={{
            padding: '12px',
            background: thresholdResult.success ? colors.accent.green + '10' : colors.accent.red + '10',
            borderRadius: '4px',
            border: `1px solid ${thresholdResult.success ? colors.accent.green + '40' : colors.accent.red + '40'}`,
          }}>
            {thresholdResult.success ? (
              <div style={{ display: 'flex', gap: '24px' }}>
                <div>
                  <span style={{ color: colors.text.muted, fontSize: '11px' }}>Audit Threshold</span>
                  <div style={{ color: colors.accent.green, fontFamily: 'JetBrains Mono', fontSize: '16px' }}>
                    {thresholdResult.audit_threshold?.toFixed(2)}
                  </div>
                </div>
                <div>
                  <span style={{ color: colors.text.muted, fontSize: '11px' }}>Defer Threshold</span>
                  <div style={{ color: colors.accent.amber, fontFamily: 'JetBrains Mono', fontSize: '16px' }}>
                    {thresholdResult.defer_threshold?.toFixed(2)}
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ color: colors.accent.red, fontSize: '12px' }}>
                {thresholdResult.error}
              </div>
            )}
          </div>
        )}
      </div>

      {/* APPS Browser Modal */}
      {appsBrowser.open && (
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
            borderRadius: '12px',
            width: '600px',
            maxHeight: '80vh',
            overflow: 'hidden',
            border: `1px solid ${colors.border}`,
          }}>
            <div style={{
              padding: '16px 20px',
              borderBottom: `1px solid ${colors.border}`,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <span style={{ color: colors.text.primary, fontSize: '16px', fontWeight: '500' }}>
                APPS Problems ({appsBrowser.total} total)
              </span>
              <button
                onClick={() => setAppsBrowser({ ...appsBrowser, open: false })}
                style={{
                  background: 'none',
                  border: 'none',
                  color: colors.text.muted,
                  fontSize: '20px',
                  cursor: 'pointer',
                }}
              >
                ×
              </button>
            </div>

            <div style={{ padding: '16px 20px', borderBottom: `1px solid ${colors.border}` }}>
              <div style={{ display: 'flex', gap: '8px' }}>
                {['introductory', 'interview', 'competition'].map(diff => (
                  <button
                    key={diff}
                    onClick={async () => {
                      setDifficultyFilter(diff);
                      const res = await fetch(`${API_BASE}/api/apps/problems?difficulty=${diff}&limit=50`);
                      if (res.ok) {
                        const data = await res.json();
                        setAppsBrowser({ ...appsBrowser, problems: data.problems });
                      }
                    }}
                    style={{
                      padding: '6px 12px',
                      background: difficultyFilter === diff ? colors.bg.tertiary : 'transparent',
                      border: `1px solid ${difficultyFilter === diff ? colors.accent.cyan : colors.border}`,
                      borderRadius: '4px',
                      color: difficultyFilter === diff ? colors.accent.cyan : colors.text.secondary,
                      fontSize: '11px',
                      cursor: 'pointer',
                    }}
                  >
                    {diff} ({appsBrowser.difficulties[diff] || 0})
                  </button>
                ))}
              </div>
            </div>

            <div style={{ maxHeight: '400px', overflowY: 'auto', padding: '16px 20px' }}>
              {appsBrowser.problems.map(p => (
                <div key={p.problem_id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '10px 12px',
                  background: colors.bg.tertiary,
                  borderRadius: '6px',
                  marginBottom: '8px',
                  border: `1px solid ${colors.border}`,
                }}>
                  <span style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '12px',
                    color: colors.text.primary,
                  }}>
                    {p.problem_id}
                  </span>
                  <span style={{
                    padding: '2px 6px',
                    background: p.difficulty === 'competition' ? colors.accent.red + '20' :
                               p.difficulty === 'interview' ? colors.accent.amber + '20' :
                               colors.accent.green + '20',
                    borderRadius: '4px',
                    fontSize: '10px',
                    color: p.difficulty === 'competition' ? colors.accent.red :
                           p.difficulty === 'interview' ? colors.accent.amber :
                           colors.accent.green,
                  }}>
                    {p.difficulty}
                  </span>
                  <div style={{ flex: 1 }} />
                  <button
                    onClick={() => {
                      addProblem(p.problem_id);
                    }}
                    disabled={problems.some(existing => existing.problem_id === p.problem_id)}
                    style={{
                      padding: '4px 12px',
                      background: problems.some(existing => existing.problem_id === p.problem_id) ? colors.bg.tertiary : colors.accent.cyan + '20',
                      border: `1px solid ${problems.some(existing => existing.problem_id === p.problem_id) ? colors.border : colors.accent.cyan}`,
                      borderRadius: '4px',
                      color: problems.some(existing => existing.problem_id === p.problem_id) ? colors.text.muted : colors.accent.cyan,
                      fontSize: '11px',
                      cursor: problems.some(existing => existing.problem_id === p.problem_id) ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {problems.some(existing => existing.problem_id === p.problem_id) ? 'Added' : 'Add'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export { ProblemsTab };
