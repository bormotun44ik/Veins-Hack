#!/usr/bin/env bash
# demo_replay.sh — Interactive demo replay script for Veins-Hack.
#
# Pushes 4 events with pauses so the frontend polling (10s dashboard, 5s graph)
# can show each update individually — maximum WOW effect for judges.
#
# Usage: bash scripts/demo_replay.sh
# Optional: BASE=http://localhost:8000 bash scripts/demo_replay.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUSH="python3 ${SCRIPT_DIR}/push_event.py"

# Colors
GREEN="\033[32m"
YELLOW="\033[33m"
BOLD="\033[1m"
RESET="\033[0m"

POLL_WAIT=12  # >= dashboard polling interval (10s) + buffer

echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  Veins Demo Replay — Live Event Injection  ${RESET}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo "This script pushes events one by one."
echo "Each pause lets frontend polling show the update."
echo ""

# ── Event 1: Ivan night commit ──────────────────────────────────────────────
echo -e "${YELLOW}[Event 1/4]${RESET} Ivan — night commit (fix: revert broke prod again)"
echo -e "${GREEN}Press Enter to push, or wait 30s for auto-continue...${RESET}"
read -t 30 || true
$PUSH ivan commit "fix: revert broke prod again" --night

echo ""
echo -e "${YELLOW}⏳ Waiting ${POLL_WAIT}s for frontend to poll update...${RESET}"
sleep $POLL_WAIT

# ── Event 2: Ivan slack message ──────────────────────────────────────────────
echo -e "${YELLOW}[Event 2/4]${RESET} Ivan — slack message (не успею, всё ломается)"
echo -e "${GREEN}Press Enter to push, or wait 30s for auto-continue...${RESET}"
read -t 30 || true
$PUSH ivan slack_msg "не успею, всё ломается"

echo ""
echo -e "${YELLOW}⏳ Waiting ${POLL_WAIT}s for frontend to poll update...${RESET}"
sleep $POLL_WAIT

# ── Event 3: Ivan weekend commit ──────────────────────────────────────────────
echo -e "${YELLOW}[Event 3/4]${RESET} Ivan — weekend commit (chore: hotfix deploy)"
echo -e "${GREEN}Press Enter to push, or wait 30s for auto-continue...${RESET}"
read -t 30 || true
$PUSH ivan commit "chore: hotfix deploy" --weekend

echo ""
echo -e "${YELLOW}⏳ Waiting ${POLL_WAIT}s for frontend to poll update...${RESET}"
sleep $POLL_WAIT

# ── Event 4: Maria — healthy commit ──────────────────────────────────────────
echo -e "${YELLOW}[Event 4/4]${RESET} Maria — normal commit (feat: new dashboard component)"
echo -e "${GREEN}Press Enter to push, or wait 30s for auto-continue...${RESET}"
read -t 30 || true
$PUSH maria commit "feat: new dashboard component"

echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  Demo replay complete! ✅${RESET}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo "Check frontend dashboard — Ivan's overload should have increased."
echo "Graph view shows Ivan's node highlighted in RED."
