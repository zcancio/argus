/**
 * Default values for Dataset configurations
 */

export const DEFAULT_DATASET_SETTINGS = {
  num_problems: 5,
  num_backdoor_ideas: 3,
  max_difficulty: 7,
};

export const DEFAULT_DATASET_MODELS = {
  human_model: "gpt-4o",
  trusted_model: "gpt-4o",
  untrusted_model: "gpt-4o",
};

export const MODEL_OPTIONS = [
  { value: "simulated", label: "Simulated (No API calls)" },
  { value: "gpt-4o", label: "GPT-4o (OpenAI)" },
  { value: "gpt-4o-mini", label: "GPT-4o Mini (OpenAI)" },
  { value: "gpt-3.5-turbo", label: "GPT-3.5 Turbo (OpenAI)" },
  { value: "claude-3-opus-20240229", label: "Claude 3 Opus (Anthropic)" },
  { value: "claude-3-sonnet-20240229", label: "Claude 3 Sonnet (Anthropic)" },
  { value: "claude-3-haiku-20240307", label: "Claude 3 Haiku (Anthropic)" },
];

/**
 * Create a new dataset object with default values
 */
export function createDefaultDataset(name = "New Dataset") {
  return {
    name,
    settings: { ...DEFAULT_DATASET_SETTINGS },
    models: { ...DEFAULT_DATASET_MODELS },
    prompts: {},
  };
}

/**
 * Dataset status badges
 */
export const STATUS_BADGES = {
  draft: {
    label: "Draft",
    className: "bg-yellow-100 text-yellow-800",
  },
  published: {
    label: "Published",
    className: "bg-green-100 text-green-800",
  },
};

/**
 * Test run status badges
 */
export const TEST_STATUS_BADGES = {
  running: {
    label: "Running",
    className: "bg-blue-100 text-blue-800",
  },
  completed: {
    label: "Passed",
    className: "bg-green-100 text-green-800",
  },
  failed: {
    label: "Failed",
    className: "bg-red-100 text-red-800",
  },
};
