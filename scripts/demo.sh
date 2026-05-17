#!/usr/bin/env bash
# Simple demo runner for FinTrack AI
set -eo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f venv312/bin/activate ]; then
  # shellcheck disable=SC1091
  source venv312/bin/activate
fi

printf "Running quick demo: will feed example prompts to main.py\n"

# Feed example interactions to the app (non-interactive)
printf "Log an expense of $20 for groceries.\n" > /tmp/fintrack_input.txt
printf "Summarize my expenses for this month.\n" >> /tmp/fintrack_input.txt
printf "Suggest a budget plan based on my expenses.\n" >> /tmp/fintrack_input.txt

# Start demo
printf "Starting main.py (will read first line as user input)\n"
# Run main.py once per example to demonstrate agent outputs interactively
while read -r line; do
  printf "\n==> Input: %s\n" "$line"
  printf "%s\n" "$line" | python main.py || true
done < /tmp/fintrack_input.txt

printf "\nDemo finished. Run 'python -m pytest -q' to run full test suite.\n"

# cleanup
rm -f /tmp/fintrack_input.txt
