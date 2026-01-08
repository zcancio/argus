/**
 * Secure Browser Storage for API Keys
 *
 * Uses localStorage with base64 encoding for basic obfuscation.
 * Note: This is NOT encryption - keys can still be retrieved by
 * anyone with access to the browser's developer tools.
 */

const STORAGE_KEY = 'argus_api_keys';
const VALIDATION_KEY = 'argus_api_validation';

/**
 * Simple obfuscation using base64 + reversal
 * This prevents casual snooping but is NOT secure encryption
 */
function obfuscate(value) {
  if (!value) return '';
  try {
    const reversed = value.split('').reverse().join('');
    return btoa(reversed);
  } catch {
    return '';
  }
}

function deobfuscate(value) {
  if (!value) return '';
  try {
    const decoded = atob(value);
    return decoded.split('').reverse().join('');
  } catch {
    return '';
  }
}

/**
 * Save API keys to browser storage
 */
export function saveApiKeys(keys) {
  try {
    const obfuscated = {
      anthropic: obfuscate(keys.anthropic || ''),
      openai: obfuscate(keys.openai || ''),
      savedAt: Date.now(),
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(obfuscated));
    return true;
  } catch (err) {
    console.error('Failed to save API keys:', err);
    return false;
  }
}

/**
 * Load API keys from browser storage
 */
export function loadApiKeys() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return { anthropic: '', openai: '' };

    const parsed = JSON.parse(stored);
    return {
      anthropic: deobfuscate(parsed.anthropic || ''),
      openai: deobfuscate(parsed.openai || ''),
    };
  } catch (err) {
    console.error('Failed to load API keys:', err);
    return { anthropic: '', openai: '' };
  }
}

/**
 * Clear all stored API keys
 */
export function clearApiKeys() {
  try {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(VALIDATION_KEY);
    return true;
  } catch (err) {
    console.error('Failed to clear API keys:', err);
    return false;
  }
}

/**
 * Save validation status for API keys
 */
export function saveValidationStatus(status) {
  try {
    localStorage.setItem(VALIDATION_KEY, JSON.stringify({
      ...status,
      savedAt: Date.now(),
    }));
    return true;
  } catch (err) {
    console.error('Failed to save validation status:', err);
    return false;
  }
}

/**
 * Load validation status for API keys
 * Expires after 24 hours
 */
export function loadValidationStatus() {
  try {
    const stored = localStorage.getItem(VALIDATION_KEY);
    if (!stored) return { anthropic: null, openai: null };

    const parsed = JSON.parse(stored);

    // Expire after 24 hours
    const ONE_DAY = 24 * 60 * 60 * 1000;
    if (parsed.savedAt && Date.now() - parsed.savedAt > ONE_DAY) {
      localStorage.removeItem(VALIDATION_KEY);
      return { anthropic: null, openai: null };
    }

    return {
      anthropic: parsed.anthropic || null,
      openai: parsed.openai || null,
    };
  } catch (err) {
    console.error('Failed to load validation status:', err);
    return { anthropic: null, openai: null };
  }
}

/**
 * Check if any API keys are stored
 */
export function hasStoredKeys() {
  const keys = loadApiKeys();
  return !!(keys.anthropic || keys.openai);
}
