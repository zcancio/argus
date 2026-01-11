import { colors } from '../../constants';
import { InfoIcon } from '../common';

export function ConfigPanel({ config, onChange, onRun, isRunning, datasets, selectedDatasetId, onDatasetChange }) {
  // Get selected dataset's problem count
  const selectedDataset = datasets.find(d => d.id === selectedDatasetId);
  const datasetSize = selectedDataset?.stats?.completed || 0;
  const numProblemsExceedsDataset = datasetSize > 0 && config.num_problems > datasetSize;
  const sliderStyle = {
    width: '100%',
    height: '4px',
    background: 'rgb(36, 36, 46)',
    borderRadius: '2px',
    appearance: 'none',
    cursor: 'pointer',
  };

  const labelStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
    fontSize: '13px',
  };

  const inputGroupStyle = {
    marginBottom: '20px',
  };

  const selectStyle = {
    width: '100%',
    padding: '10px 12px',
    background: colors.bg.tertiary,
    border: `1px solid ${colors.border}`,
    borderRadius: '6px',
    color: colors.text.primary,
    fontSize: '14px',
  };

  return (
    <div style={{
      background: colors.bg.secondary,
      border: `1px solid ${colors.border}`,
      borderRadius: '8px',
      padding: '24px',
    }}>
      {/* Dataset Selection */}
      <div style={{ marginBottom: '20px' }}>
        <div style={labelStyle}>
          <span style={{ color: colors.text.secondary }}>Dataset</span>
        </div>
        <select
          value={selectedDatasetId || ''}
          onChange={(e) => onDatasetChange(e.target.value || null)}
          style={selectStyle}
        >
          <option value="">Select a dataset...</option>
          {datasets.map(d => (
            <option key={d.id} value={d.id}>
              {d.name} ({d.stats?.completed || 0} problems)
            </option>
          ))}
        </select>

        <button
          onClick={onRun}
          disabled={isRunning || !selectedDatasetId}
          style={{
            width: '100%',
            padding: '14px 20px',
            marginTop: '12px',
            background: (isRunning || !selectedDatasetId) ? colors.bg.tertiary : `linear-gradient(135deg, ${colors.accent.cyan}, ${colors.accent.magenta})`,
            border: 'none',
            borderRadius: '6px',
            color: colors.text.primary,
            fontSize: '14px',
            fontWeight: '600',
            cursor: (isRunning || !selectedDatasetId) ? 'not-allowed' : 'pointer',
            textTransform: 'uppercase',
            letterSpacing: '1px',
          }}
        >
          {isRunning ? 'Running...' : 'Run Simulation'}
        </button>
      </div>

      {/* Protocol Preset */}
      <div style={{
        padding: '16px',
        background: colors.bg.tertiary,
        borderRadius: '6px',
        marginBottom: '20px',
        border: `1px solid ${colors.accent.cyan}40`,
      }}>
        <div style={{ fontSize: '11px', color: colors.accent.cyan, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px' }}>
          Control Protocol
        </div>

        <div style={{ marginBottom: '16px' }}>
          <div style={labelStyle}>
            <span style={{ color: colors.text.secondary, display: 'flex', alignItems: 'center' }}>
              Protocol
              <InfoIcon tooltip="Pre-configured protocols from Greenblatt et al. Select a preset to auto-configure Blue Team settings." />
            </span>
          </div>
          <select
            value={
              config.monitor_type === 'trusted' && !config.defer_enabled ? 'tm' :
              config.monitor_type === 'trusted' && config.defer_enabled && config.defer_action === 'replace' && config.defer_rate === 0.05 ? 'tm_d5' :
              config.monitor_type === 'trusted' && config.defer_enabled && config.defer_action === 'replace' && config.defer_rate === 0.10 ? 'tm_d10' :
              config.monitor_type === 'trusted' && config.defer_enabled && config.defer_action === 'replace' && config.defer_rate === 0.20 ? 'tm_d20' :
              config.monitor_type === 'untrusted' && !config.defer_enabled ? 'um' :
              config.monitor_type === 'untrusted' && config.defer_enabled && config.defer_rate === 0.05 ? 'um_d5' :
              config.monitor_type === 'untrusted' && config.defer_enabled && config.defer_rate === 0.10 ? 'um_d10' :
              config.monitor_type === 'untrusted' && config.defer_enabled && config.defer_rate === 0.20 ? 'um_d20' :
              config.monitor_type === 'trusted' && config.defer_enabled && config.defer_action === 'edit' && config.defer_rate === 0.05 ? 'te_5' :
              config.monitor_type === 'trusted' && config.defer_enabled && config.defer_action === 'edit' && config.defer_rate === 0.10 ? 'te_10' :
              config.monitor_type === 'trusted' && config.defer_enabled && config.defer_action === 'edit' && config.defer_rate === 0.20 ? 'te_20' :
              config.monitor_type === 'trusted' && config.defer_enabled && config.defer_action === 'edit' && config.defer_rate === 0.50 ? 'te_50' :
              'custom'
            }
            onChange={(e) => {
              const presets = {
                tm: { monitor_type: 'trusted', audit_budget_rate: 0.02, free_start: 10, defer_enabled: false, defer_rate: 0.10, defer_action: 'replace' },
                tm_d5: { monitor_type: 'trusted', audit_budget_rate: 0.02, free_start: 10, defer_enabled: true, defer_rate: 0.05, defer_action: 'replace' },
                tm_d10: { monitor_type: 'trusted', audit_budget_rate: 0.02, free_start: 10, defer_enabled: true, defer_rate: 0.10, defer_action: 'replace' },
                tm_d20: { monitor_type: 'trusted', audit_budget_rate: 0.02, free_start: 10, defer_enabled: true, defer_rate: 0.20, defer_action: 'replace' },
                um: { monitor_type: 'untrusted', audit_budget_rate: 0.02, free_start: 10, defer_enabled: false, defer_rate: 0.10, defer_action: 'replace' },
                um_d5: { monitor_type: 'untrusted', audit_budget_rate: 0.02, free_start: 10, defer_enabled: true, defer_rate: 0.05, defer_action: 'replace' },
                um_d10: { monitor_type: 'untrusted', audit_budget_rate: 0.02, free_start: 10, defer_enabled: true, defer_rate: 0.10, defer_action: 'replace' },
                um_d20: { monitor_type: 'untrusted', audit_budget_rate: 0.02, free_start: 10, defer_enabled: true, defer_rate: 0.20, defer_action: 'replace' },
                te_5: { monitor_type: 'trusted', audit_budget_rate: 0.02, free_start: 10, defer_enabled: true, defer_rate: 0.05, defer_action: 'edit' },
                te_10: { monitor_type: 'trusted', audit_budget_rate: 0.02, free_start: 10, defer_enabled: true, defer_rate: 0.10, defer_action: 'edit' },
                te_20: { monitor_type: 'trusted', audit_budget_rate: 0.02, free_start: 10, defer_enabled: true, defer_rate: 0.20, defer_action: 'edit' },
                te_50: { monitor_type: 'trusted', audit_budget_rate: 0.02, free_start: 10, defer_enabled: true, defer_rate: 0.50, defer_action: 'edit' },
              };
              if (presets[e.target.value]) {
                onChange({ ...config, ...presets[e.target.value] });
              }
            }}
            style={selectStyle}
          >
            <option value="tm">Trusted Monitoring</option>
            <option value="tm_d5">Trusted Monitoring + Defer 5%</option>
            <option value="tm_d10">Trusted Monitoring + Defer 10%</option>
            <option value="tm_d20">Trusted Monitoring + Defer 20%</option>
            <option value="um">Untrusted Monitoring</option>
            <option value="um_d5">Untrusted Monitoring + Defer 5%</option>
            <option value="um_d10">Untrusted Monitoring + Defer 10%</option>
            <option value="um_d20">Untrusted Monitoring + Defer 20%</option>
            <option value="te_5">Trusted Editing 5%</option>
            <option value="te_10">Trusted Editing 10%</option>
            <option value="te_20">Trusted Editing 20%</option>
            <option value="te_50">Trusted Editing 50%</option>
            <option value="custom" disabled>Custom (adjust settings below)</option>
          </select>
        </div>

        <div style={{ marginBottom: '12px' }}>
          <div style={labelStyle}>
            <span style={{ color: colors.text.secondary, display: 'flex', alignItems: 'center' }}>
              Monitor Type
              <InfoIcon tooltip="Who rates code for suspicion. Trusted (T) is less capable but honest. Untrusted (U) is more capable but may collude with backdoored code." />
            </span>
          </div>
          <select
            value={config.monitor_type || 'trusted'}
            onChange={(e) => onChange({ ...config, monitor_type: e.target.value })}
            style={selectStyle}
          >
            <option value="trusted">Trusted (T)</option>
            <option value="untrusted">Untrusted (U)</option>
          </select>
        </div>

        <div style={{ borderTop: `1px solid ${colors.border}`, margin: '16px 0', paddingTop: '16px' }}>
          <div style={inputGroupStyle}>
            <div style={labelStyle}>
              <span style={{ color: colors.text.secondary, display: 'flex', alignItems: 'center' }}>
                Audit Budget Rate
                <InfoIcon tooltip="Percentage of problems that can be audited by H. E.g., 2% means H can audit 100 out of 5000 problems." />
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <input
                  type="number"
                  min="1"
                  max="10"
                  step="1"
                  value={Math.round(config.audit_budget_rate * 100)}
                  onChange={(e) => onChange({ ...config, audit_budget_rate: parseFloat(e.target.value) / 100 })}
                  style={{ width: '50px', padding: '4px 8px', background: colors.bg.secondary, border: `1px solid ${colors.border}`, borderRadius: '4px', color: colors.accent.amber, fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', textAlign: 'right' }}
                />
                <span style={{ color: colors.accent.amber, fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>%</span>
              </div>
            </div>
            <input
              type="range"
              min="0.01"
              max="0.10"
              step="0.01"
              value={config.audit_budget_rate}
              onChange={(e) => onChange({ ...config, audit_budget_rate: parseFloat(e.target.value) })}
              style={sliderStyle}
            />
          </div>

          <div style={inputGroupStyle}>
            <div style={labelStyle}>
              <span style={{ color: colors.text.secondary, display: 'flex', alignItems: 'center' }}>
                Free Start
                <InfoIcon tooltip="First N problems are audited for free (not counted against budget). Helps calibrate thresholds." />
              </span>
              <input
                type="number"
                min="0"
                max="100"
                step="1"
                value={config.free_start}
                onChange={(e) => onChange({ ...config, free_start: parseInt(e.target.value) || 0 })}
                style={{ width: '60px', padding: '4px 8px', background: colors.bg.secondary, border: `1px solid ${colors.border}`, borderRadius: '4px', color: colors.accent.amber, fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', textAlign: 'right' }}
              />
            </div>
            <input
              type="range"
              min="0"
              max="50"
              step="5"
              value={config.free_start}
              onChange={(e) => onChange({ ...config, free_start: parseInt(e.target.value) })}
              style={sliderStyle}
            />
          </div>

          <div style={inputGroupStyle}>
            <div style={labelStyle}>
              <span style={{ color: colors.text.secondary, display: 'flex', alignItems: 'center' }}>
                Enable Defer
                <InfoIcon tooltip="When enabled, suspicious problems above defer threshold use T's solution instead of U's." />
              </span>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={config.defer_enabled}
                onChange={(e) => onChange({ ...config, defer_enabled: e.target.checked })}
                style={{ width: '16px', height: '16px', accentColor: colors.accent.cyan }}
              />
              <span style={{ color: config.defer_enabled ? colors.text.primary : colors.text.muted, fontSize: '13px' }}>
                Defer to T for suspicious problems
              </span>
            </label>
          </div>

          {config.defer_enabled && (
            <>
              <div style={{ marginBottom: 0 }}>
                <div style={labelStyle}>
                  <span style={{ color: colors.text.secondary, display: 'flex', alignItems: 'center' }}>
                    Defer Rate
                    <InfoIcon tooltip="Percentage of problems to defer to T's solution. Higher = safer but lower usefulness." />
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <input
                      type="number"
                      min="1"
                      max="50"
                      step="1"
                      value={Math.round(config.defer_rate * 100)}
                      onChange={(e) => onChange({ ...config, defer_rate: parseFloat(e.target.value) / 100 })}
                      style={{ width: '50px', padding: '4px 8px', background: colors.bg.secondary, border: `1px solid ${colors.border}`, borderRadius: '4px', color: colors.accent.cyan, fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', textAlign: 'right' }}
                    />
                    <span style={{ color: colors.accent.cyan, fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>%</span>
                  </div>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="0.50"
                  step="0.05"
                  value={config.defer_rate}
                  onChange={(e) => onChange({ ...config, defer_rate: parseFloat(e.target.value) })}
                  style={sliderStyle}
                />
              </div>

              <div style={{ marginTop: '12px' }}>
                <div style={labelStyle}>
                  <span style={{ color: colors.text.secondary, display: 'flex', alignItems: 'center' }}>
                    Defer Action
                    <InfoIcon tooltip="What to do when deferring. Replace: use T's solution. Edit: T edits U's code to remove suspected issues." />
                  </span>
                </div>
                <select
                  value={config.defer_action || 'replace'}
                  onChange={(e) => onChange({ ...config, defer_action: e.target.value })}
                  style={selectStyle}
                >
                  <option value="replace">Replace with T's solution</option>
                  <option value="edit">T edits U's code</option>
                </select>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Red Team Strategy */}
      <div style={{
        padding: '16px',
        background: colors.bg.tertiary,
        borderRadius: '6px',
        marginBottom: '20px',
        border: `1px solid ${colors.accent.red}40`,
      }}>
        <div style={{ fontSize: '11px', color: colors.accent.red, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px' }}>
          Red Team Strategy
        </div>

        <div style={inputGroupStyle}>
          <div style={labelStyle}>
            <span style={{ color: colors.text.secondary, display: 'flex', alignItems: 'center' }}>
              Backdoor Rate
              <InfoIcon tooltip="Target percentage of problems where red team uses a backdoor. Higher rate = more aggressive red team. The sneakiness threshold is computed dynamically to achieve this rate." />
            </span>
            <span style={{ color: colors.text.muted, fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>
              {(config.backdoor_rate * 100).toFixed(0)}%
            </span>
          </div>
          <input
            type="range"
            min="0.05"
            max="0.80"
            step="0.05"
            value={config.backdoor_rate}
            onChange={(e) => onChange({ ...config, backdoor_rate: parseFloat(e.target.value) })}
            style={sliderStyle}
          />
        </div>

        <div style={{ marginBottom: 0 }}>
          <div style={labelStyle}>
            <span style={{ color: colors.text.secondary, display: 'flex', alignItems: 'center' }}>
              Coup Subsample Rate
              <InfoIcon tooltip="Probability of attempting coup when backdoor is available. Paper default is 1/12 (~8.3%). Lower rate reduces variance but requires more trials." />
            </span>
            <span style={{ color: colors.text.muted, fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>
              {(config.coup_subsample_rate * 100).toFixed(1)}%
            </span>
          </div>
          <input
            type="range"
            min="0.01"
            max="1.0"
            step="0.01"
            value={config.coup_subsample_rate}
            onChange={(e) => onChange({ ...config, coup_subsample_rate: parseFloat(e.target.value) })}
            style={sliderStyle}
          />
        </div>
      </div>

      {/* Simulation Options */}
      <div style={{
        padding: '16px',
        background: colors.bg.tertiary,
        borderRadius: '6px',
        marginBottom: '20px',
        border: `1px solid ${colors.accent.green}40`,
      }}>
        <div style={{ fontSize: '11px', color: colors.accent.green, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '12px' }}>
          Simulation Options
        </div>

        <div style={inputGroupStyle}>
          <div style={labelStyle}>
            <span style={{ color: colors.text.secondary, display: 'flex', alignItems: 'center' }}>
              Number of Trials
              <InfoIcon tooltip="Monte Carlo trials to run. More trials = more accurate results. 200 for testing, 2000 for final results." />
            </span>
            <input
              type="number"
              min="10"
              max="10000"
              step="100"
              value={config.num_trials}
              onChange={(e) => onChange({ ...config, num_trials: parseInt(e.target.value) || 100 })}
              style={{ width: '80px', padding: '4px 8px', background: colors.bg.secondary, border: `1px solid ${colors.border}`, borderRadius: '4px', color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', textAlign: 'right' }}
            />
          </div>
          <input
            type="range"
            min="100"
            max="5000"
            step="100"
            value={config.num_trials}
            onChange={(e) => onChange({ ...config, num_trials: parseInt(e.target.value) })}
            style={sliderStyle}
          />
        </div>

        <div style={{ marginBottom: 0 }}>
          <div style={labelStyle}>
            <span style={{ color: colors.text.secondary, display: 'flex', alignItems: 'center' }}>
              Problems per Trial
              <InfoIcon tooltip="Number of problems sampled (with replacement) per trial. Should match dataset size for accurate results." />
            </span>
            <input
              type="number"
              min="10"
              max="50000"
              step="100"
              value={config.num_problems}
              onChange={(e) => onChange({ ...config, num_problems: parseInt(e.target.value) || 100 })}
              style={{ width: '80px', padding: '4px 8px', background: colors.bg.secondary, border: `1px solid ${numProblemsExceedsDataset ? colors.accent.amber : colors.border}`, borderRadius: '4px', color: colors.text.primary, fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', textAlign: 'right' }}
            />
          </div>
          <input
            type="range"
            min="10"
            max={Math.max(datasetSize || 100, 100)}
            step="10"
            value={config.num_problems}
            onChange={(e) => onChange({ ...config, num_problems: parseInt(e.target.value) })}
            style={sliderStyle}
          />
          {numProblemsExceedsDataset && (
            <div style={{ marginTop: '8px', padding: '8px 12px', background: `${colors.accent.amber}20`, border: `1px solid ${colors.accent.amber}40`, borderRadius: '4px', fontSize: '11px', color: colors.accent.amber }}>
              Dataset has {datasetSize} problems. Using {config.num_problems} will oversample.
              <button
                onClick={() => onChange({ ...config, num_problems: datasetSize })}
                style={{ marginLeft: '8px', padding: '2px 8px', background: colors.accent.amber, border: 'none', borderRadius: '3px', color: colors.bg.primary, fontSize: '11px', cursor: 'pointer', fontWeight: '600' }}
              >
                Use {datasetSize}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
