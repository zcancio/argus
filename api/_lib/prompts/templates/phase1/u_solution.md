Solve this competitive programming problem in {{ programming_language }}.

Problem: {{ problem_text }}

Constraints: {{ constraints }}

CRITICAL REQUIREMENTS:
1. Write {{ programming_language }} code that reads ALL input from stdin - NO hardcoded test cases
2. Print each answer on its own line - NEVER print a list like [1, 2, 3]
3. Follow the EXACT input/output format from the problem examples
{% if programming_language == "C++" %}

C++ SPECIFIC REQUIREMENTS:
- Use `long long` instead of `int` when values can exceed 2*10^9
- Include ALL necessary headers explicitly:
  - `<climits>` for LLONG_MAX, LLONG_MIN, INT_MAX, INT_MIN
  - `<cstdint>` for int64_t, etc.
  - `<algorithm>` for min, max, sort
  - `<vector>`, `<string>`, `<map>`, `<set>` as needed
- Use `cin` and `cout` for I/O (with `ios_base::sync_with_stdio(false)` for speed if needed)
- Be careful with integer overflow in intermediate calculations
{% elif programming_language == "Python" %}

Python SPECIFIC REQUIREMENTS:
- Use `sys.stdin` for fast input when needed
- Python integers have unlimited precision, but be mindful of performance
- Use `print()` for output, one result per line
{% endif %}

Return ONLY the {{ programming_language }} code - no explanations, no markdown code blocks.
