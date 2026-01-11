import { useState, useEffect } from 'react';
import { colors, API_BASE } from '../../constants';
import { DEFAULT_DATASET_SETTINGS, DEFAULT_DATASET_MODELS, MODEL_OPTIONS } from '../../datasetDefaults';
import { PromptEditor } from '../common';

function DatasetEditorPanel({ dataset, onSave, onTest, onPublish, onDelete, onDuplicate, defaultPrompts }) {
  const [localDataset, setLocalDataset] = useState(null);
  const [activeTab, setActiveTab] = useState('settings');
  const [hasChanges, setHasChanges] = useState(false);
  const [promptPhase, setPromptPhase] = useState('phase1');
  const [validProblemIds, setValidProblemIds] = useState(new Set());
  const [mandatoryError, setMandatoryError] = useState('');

  // Fetch valid problem IDs on mount
  useEffect(() => {
    const fetchValidIds = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/apps/problems?limit=10000`);
        if (res.ok) {
          const data = await res.json();
          setValidProblemIds(new Set(data.problems.map(p => p.problem_id)));
        }
      } catch (e) {
        console.error('Failed to fetch valid problem IDs:', e);
      }
    };
    fetchValidIds();
  }, []);

  useEffect(() => {
    if (dataset) {
      setLocalDataset({
        name: dataset.name,
        settings: {
          ...DEFAULT_DATASET_SETTINGS,
          ...dataset.settings,
          // Ensure mandatory_problems is always an array
          mandatory_problems: dataset.settings?.mandatory_problems || []
        },
        models: { ...DEFAULT_DATASET_MODELS, ...dataset.models },
        prompts: { ...dataset.prompts },
      });
      setHasChanges(false);
    }
  }, [dataset?.id]);

  if (!dataset || !localDataset) {
    return (
      <div style={{
        background: colors.bg.secondary,
        border: `1px solid ${colors.border}`,
        borderRadius: '8px',
        padding: '48px',
        textAlign: 'center',
      }}>
        <div style={{ fontSize: '32px', marginBottom: '12px' }}>📝</div>
        <p style={{ color: colors.text.muted, margin: 0, fontSize: '13px' }}>Select a dataset to edit</p>
      </div>
    );
  }

  if (dataset.status === 'published') {
    return <PublishedDatasetView dataset={dataset} onDuplicate={onDuplicate} onDelete={onDelete} />;
  }

  const handleChange = (field, value) => {
    setLocalDataset(prev => ({ ...prev, [field]: value }));
    setHasChanges(true);
  };

  const handleSettingsChange = (key, value) => {
    setLocalDataset(prev => ({
      ...prev,
      settings: { ...prev.settings, [key]: value }
    }));
    setHasChanges(true);
  };

  const handleModelsChange = (key, value) => {
    setLocalDataset(prev => ({
      ...prev,
      models: { ...prev.models, [key]: value }
    }));
    setHasChanges(true);
  };

  const handlePromptChange = (key, value) => {
    setLocalDataset(prev => ({
      ...prev,
      prompts: { ...prev.prompts, [key]: value }
    }));
    setHasChanges(true);
  };

  const handlePromptReset = (key) => {
    setLocalDataset(prev => {
      const newPrompts = { ...prev.prompts };
      delete newPrompts[key];
      return { ...prev, prompts: newPrompts };
    });
    setHasChanges(true);
  };

  const handleSave = () => {
    onSave(dataset.id, localDataset);
    setHasChanges(false);
  };

  const sliderStyle = {
    width: '100%',
    height: '4px',
    background: 'rgb(36, 36, 46)',
    borderRadius: '2px',
    appearance: 'none',
    cursor: 'pointer',
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

  const phases = [
    { key: 'phase1', label: 'Phase 1', count: 2 },
    { key: 'phase2', label: 'Phase 2', count: 6 },
    { key: 'phase3', label: 'Phase 3', count: 7 },
    { key: 'phase5', label: 'Phase 5', count: 2 },
  ];

  const getPromptValue = (key, defaultValue) => {
    return localDataset.prompts[key] !== undefined ? localDataset.prompts[key] : defaultValue;
  };

  const isPromptModified = (key) => localDataset.prompts[key] !== undefined;

  return (
    <div style={{
      background: colors.bg.secondary,
      border: `1px solid ${colors.border}`,
      borderRadius: '8px',
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 24px',
        borderBottom: `1px solid ${colors.border}`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div>
          <input
            type="text"
            value={localDataset.name}
            onChange={(e) => handleChange('name', e.target.value)}
            style={{
              background: 'transparent',
              border: 'none',
              color: colors.text.primary,
              fontSize: '16px',
              fontWeight: '500',
              padding: 0,
              outline: 'none',
            }}
          />
          <span style={{
            marginLeft: '12px',
            padding: '2px 8px',
            background: colors.accent.amber + '20',
            borderRadius: '4px',
            fontSize: '10px',
            color: colors.accent.amber,
            textTransform: 'uppercase',
          }}>
            Draft
          </span>
        </div>
        <button
          onClick={handleSave}
          disabled={!hasChanges}
          style={{
            padding: '8px 20px',
            background: hasChanges ? `linear-gradient(135deg, ${colors.accent.cyan}, ${colors.accent.magenta})` : colors.bg.tertiary,
            border: 'none',
            borderRadius: '6px',
            color: hasChanges ? colors.text.primary : colors.text.muted,
            fontSize: '12px',
            fontWeight: '600',
            cursor: hasChanges ? 'pointer' : 'not-allowed',
          }}
        >
          {hasChanges ? 'Save Changes' : 'Saved'}
        </button>
      </div>

      {/* Tabs */}
      <div style={{
        display: 'flex',
        gap: '4px',
        padding: '16px 24px',
        borderBottom: `1px solid ${colors.border}`,
      }}>
        {['settings', 'models', 'prompts'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 16px',
              background: activeTab === tab ? colors.bg.tertiary : 'transparent',
              border: `1px solid ${activeTab === tab ? colors.accent.cyan : colors.border}`,
              borderRadius: '4px',
              color: activeTab === tab ? colors.accent.cyan : colors.text.secondary,
              fontSize: '12px',
              cursor: 'pointer',
              textTransform: 'capitalize',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div style={{ padding: '24px' }}>
        {activeTab === 'settings' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ color: colors.text.secondary, fontSize: '13px', display: 'flex', alignItems: 'center' }}>
                  Number of Problems
                  <InfoIcon tooltip="How many APPS problems to randomly select when publishing. Each problem runs through all 6 phases independently." />
                </span>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={localDataset.settings.num_problems}
                  onChange={(e) => {
                    const val = Math.min(100, Math.max(1, parseInt(e.target.value) || 1));
                    handleSettingsChange('num_problems', val);
                  }}
                  style={{
                    width: '60px',
                    padding: '4px 8px',
                    background: colors.bg.tertiary,
                    border: `1px solid ${colors.border}`,
                    borderRadius: '4px',
                    color: colors.accent.cyan,
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '13px',
                    textAlign: 'center',
                  }}
                />
              </div>
              <input
                type="range"
                min="1"
                max="100"
                value={localDataset.settings.num_problems}
                onChange={(e) => handleSettingsChange('num_problems', parseInt(e.target.value))}
                style={sliderStyle}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ color: colors.text.secondary, fontSize: '13px', display: 'flex', alignItems: 'center' }}>
                  Backdoor Ideas per Problem
                  <InfoIcon tooltip="Number of different backdoor strategies U will attempt per problem. Higher = more likely to find a sneaky backdoor, but costs more API calls." />
                </span>
                <input
                  type="number"
                  min="1"
                  max="5"
                  value={localDataset.settings.num_backdoor_ideas}
                  onChange={(e) => {
                    const val = Math.min(5, Math.max(1, parseInt(e.target.value) || 1));
                    handleSettingsChange('num_backdoor_ideas', val);
                  }}
                  style={{
                    width: '60px',
                    padding: '4px 8px',
                    background: colors.bg.tertiary,
                    border: `1px solid ${colors.border}`,
                    borderRadius: '4px',
                    color: colors.accent.magenta,
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '13px',
                    textAlign: 'center',
                  }}
                />
              </div>
              <input
                type="range"
                min="1"
                max="5"
                value={localDataset.settings.num_backdoor_ideas}
                onChange={(e) => handleSettingsChange('num_backdoor_ideas', parseInt(e.target.value))}
                style={sliderStyle}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ color: colors.text.secondary, fontSize: '13px', display: 'flex', alignItems: 'center' }}>
                  Max Difficulty
                  <InfoIcon tooltip="Maximum problem difficulty (1-10). Higher difficulty problems are harder to backdoor but also harder to detect. Used for filtering APPS problems." />
                </span>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={localDataset.settings.max_difficulty}
                  onChange={(e) => {
                    const val = Math.min(10, Math.max(1, parseInt(e.target.value) || 1));
                    handleSettingsChange('max_difficulty', val);
                  }}
                  style={{
                    width: '60px',
                    padding: '4px 8px',
                    background: colors.bg.tertiary,
                    border: `1px solid ${colors.border}`,
                    borderRadius: '4px',
                    color: colors.accent.amber,
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '13px',
                    textAlign: 'center',
                  }}
                />
              </div>
              <input
                type="range"
                min="1"
                max="10"
                value={localDataset.settings.max_difficulty}
                onChange={(e) => handleSettingsChange('max_difficulty', parseInt(e.target.value))}
                style={sliderStyle}
              />
            </div>

            {/* Mandatory Problems */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ color: colors.text.secondary, fontSize: '13px', display: 'flex', alignItems: 'center' }}>
                  Mandatory Problems
                  <InfoIcon tooltip="Problem IDs that must be included when publishing. These are added first (in order), then random problems fill remaining slots up to 'Number of Problems'." />
                </span>
                <span style={{ color: colors.text.muted, fontSize: '11px' }}>
                  {(localDataset.settings.mandatory_problems || []).length} added
                </span>
              </div>
              <div style={{
                background: colors.bg.tertiary,
                borderRadius: '6px',
                padding: '12px',
                border: `1px solid ${colors.border}`,
              }}>
                {/* Add problem input */}
                <div style={{ display: 'flex', gap: '8px', marginBottom: mandatoryError || (localDataset.settings.mandatory_problems || []).length > 0 ? '8px' : 0 }}>
                  <input
                    type="text"
                    placeholder="Enter problem ID (e.g., 0001)"
                    id="mandatory-problem-input"
                    onChange={() => setMandatoryError('')}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        const input = e.target;
                        const value = input.value.trim();
                        if (!value) return;
                        if ((localDataset.settings.mandatory_problems || []).includes(value)) {
                          setMandatoryError(`Problem ${value} is already in the list`);
                          return;
                        }
                        if (validProblemIds.size > 0 && !validProblemIds.has(value)) {
                          setMandatoryError(`Problem ${value} not found in filtered APPS dataset`);
                          return;
                        }
                        handleSettingsChange('mandatory_problems', [...(localDataset.settings.mandatory_problems || []), value]);
                        input.value = '';
                        setMandatoryError('');
                      }
                    }}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      background: colors.bg.primary,
                      border: `1px solid ${mandatoryError ? colors.accent.red : colors.border}`,
                      borderRadius: '4px',
                      color: colors.text.primary,
                      fontSize: '13px',
                      fontFamily: 'JetBrains Mono, monospace',
                    }}
                  />
                  <button
                    onClick={() => {
                      const input = document.getElementById('mandatory-problem-input');
                      const value = input.value.trim();
                      if (!value) return;
                      if ((localDataset.settings.mandatory_problems || []).includes(value)) {
                        setMandatoryError(`Problem ${value} is already in the list`);
                        return;
                      }
                      if (validProblemIds.size > 0 && !validProblemIds.has(value)) {
                        setMandatoryError(`Problem ${value} not found in filtered APPS dataset`);
                        return;
                      }
                      handleSettingsChange('mandatory_problems', [...(localDataset.settings.mandatory_problems || []), value]);
                      input.value = '';
                      setMandatoryError('');
                    }}
                    style={{
                      padding: '8px 16px',
                      background: colors.accent.cyan + '20',
                      border: `1px solid ${colors.accent.cyan}40`,
                      borderRadius: '4px',
                      color: colors.accent.cyan,
                      fontSize: '12px',
                      fontWeight: 500,
                      cursor: 'pointer',
                    }}
                  >
                    + Add
                  </button>
                </div>
                {/* Error message */}
                {mandatoryError && (
                  <div style={{
                    padding: '6px 10px',
                    background: colors.accent.red + '15',
                    border: `1px solid ${colors.accent.red}40`,
                    borderRadius: '4px',
                    color: colors.accent.red,
                    fontSize: '12px',
                    marginBottom: (localDataset.settings.mandatory_problems || []).length > 0 ? '8px' : 0,
                  }}>
                    {mandatoryError}
                  </div>
                )}
                {/* List of mandatory problems */}
                {(localDataset.settings.mandatory_problems || []).length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {(localDataset.settings.mandatory_problems || []).map((pid, idx) => (
                      <div
                        key={pid}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          padding: '6px 10px',
                          background: colors.bg.primary,
                          borderRadius: '4px',
                          border: `1px solid ${colors.border}`,
                        }}
                      >
                        <span style={{
                          color: colors.text.muted,
                          fontSize: '11px',
                          minWidth: '20px',
                        }}>
                          {idx + 1}.
                        </span>
                        <span style={{
                          flex: 1,
                          color: colors.text.primary,
                          fontSize: '13px',
                          fontFamily: 'JetBrains Mono, monospace',
                        }}>
                          {pid}
                        </span>
                        <button
                          onClick={() => {
                            const updated = (localDataset.settings.mandatory_problems || []).filter((_, i) => i !== idx);
                            handleSettingsChange('mandatory_problems', updated);
                          }}
                          style={{
                            padding: '2px 6px',
                            background: 'transparent',
                            border: 'none',
                            color: colors.text.muted,
                            fontSize: '14px',
                            cursor: 'pointer',
                            opacity: 0.6,
                          }}
                          onMouseOver={(e) => e.target.style.opacity = 1}
                          onMouseOut={(e) => e.target.style.opacity = 0.6}
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'models' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <label style={{ display: 'block', color: colors.text.secondary, fontSize: '13px', marginBottom: '8px' }}>
                <span style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '20px',
                  height: '20px',
                  borderRadius: '4px',
                  background: colors.accent.amber + '30',
                  color: colors.accent.amber,
                  fontSize: '11px',
                  fontWeight: '600',
                  marginRight: '8px',
                }}>H</span>
                Human Auditor
              </label>
              <select
                value={localDataset.models.human_model}
                onChange={(e) => handleModelsChange('human_model', e.target.value)}
                style={selectStyle}
              >
                {MODEL_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: 'block', color: colors.text.secondary, fontSize: '13px', marginBottom: '8px' }}>
                <span style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '20px',
                  height: '20px',
                  borderRadius: '4px',
                  background: colors.accent.green + '30',
                  color: colors.accent.green,
                  fontSize: '11px',
                  fontWeight: '600',
                  marginRight: '8px',
                }}>T</span>
                Trusted Model
              </label>
              <select
                value={localDataset.models.trusted_model}
                onChange={(e) => handleModelsChange('trusted_model', e.target.value)}
                style={selectStyle}
              >
                {MODEL_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: 'block', color: colors.text.secondary, fontSize: '13px', marginBottom: '8px' }}>
                <span style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '20px',
                  height: '20px',
                  borderRadius: '4px',
                  background: colors.accent.magenta + '30',
                  color: colors.accent.magenta,
                  fontSize: '11px',
                  fontWeight: '600',
                  marginRight: '8px',
                }}>U</span>
                Untrusted Model
              </label>
              <select
                value={localDataset.models.untrusted_model}
                onChange={(e) => handleModelsChange('untrusted_model', e.target.value)}
                style={selectStyle}
              >
                {MODEL_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ display: 'flex', alignItems: 'center', color: colors.text.muted, fontSize: '11px', marginBottom: '6px' }}>
                <span style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '20px',
                  height: '20px',
                  borderRadius: '4px',
                  background: colors.accent.red + '30',
                  color: colors.accent.red,
                  fontSize: '11px',
                  fontWeight: '600',
                  marginRight: '8px',
                }}>R</span>
                Red Team Model
              </label>
              <select
                value={localDataset.models.red_team_model}
                onChange={(e) => handleModelsChange('red_team_model', e.target.value)}
                style={selectStyle}
              >
                {MODEL_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>
        )}

        {activeTab === 'prompts' && (
          <div>
            {/* Phase tabs */}
            <div style={{ display: 'flex', gap: '4px', marginBottom: '16px' }}>
              {phases.map(phase => (
                <button
                  key={phase.key}
                  onClick={() => setPromptPhase(phase.key)}
                  style={{
                    padding: '6px 12px',
                    background: promptPhase === phase.key ? colors.bg.tertiary : 'transparent',
                    border: `1px solid ${promptPhase === phase.key ? colors.accent.cyan : colors.border}`,
                    borderRadius: '4px',
                    color: promptPhase === phase.key ? colors.accent.cyan : colors.text.secondary,
                    fontSize: '11px',
                    cursor: 'pointer',
                  }}
                >
                  {phase.label} ({phase.count})
                </button>
              ))}
            </div>

            {/* Prompt editors */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '600px', overflowY: 'auto' }}>
              {Object.entries(defaultPrompts[promptPhase] || {}).map(([key, promptDef]) => (
                <PromptEditor
                  key={key}
                  promptKey={key}
                  label={promptDef.label}
                  description={promptDef.description}
                  variables={promptDef.variables}
                  defaultValue={promptDef.default}
                  value={getPromptValue(key, promptDef.default)}
                  isModified={isPromptModified(key)}
                  onChange={(value) => handlePromptChange(key, value)}
                  onReset={() => handlePromptReset(key)}
                />
              ))}
            </div>
          </div>
        )}

      </div>

      {/* Action buttons for draft dataset */}
      <div style={{
        display: 'flex',
        gap: '12px',
        padding: '16px 24px',
        borderTop: `1px solid ${colors.border}`,
        background: colors.bg.tertiary,
        borderRadius: '0 0 8px 8px',
      }}>
        <button
          onClick={() => onTest(dataset.id)}
          style={{
            padding: '10px 20px',
            background: colors.accent.cyan + '20',
            border: `1px solid ${colors.accent.cyan}`,
            borderRadius: '6px',
            color: colors.accent.cyan,
            fontSize: '13px',
            fontWeight: '500',
            cursor: 'pointer',
          }}
        >
          Test Dataset
        </button>
        <button
          onClick={() => onPublish(dataset.id)}
          style={{
            padding: '10px 20px',
            background: colors.accent.green + '20',
            border: `1px solid ${colors.accent.green}`,
            borderRadius: '6px',
            color: colors.accent.green,
            fontSize: '13px',
            fontWeight: '500',
            cursor: 'pointer',
          }}
        >
          Publish
        </button>
        <div style={{ flex: 1 }} />
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


// MAIN APP

export { DatasetEditorPanel };
