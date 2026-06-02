# GLaDOS Automatic Check-in Skill & Blueprint

This repository contains the complete Hermes Agent skill and runnable blueprint for automating GLaDOS daily check-ins, tracking remaining days, retrieving total points, and exchanging points for active packages.

## What is a Hermes Agent Skill?
Hermes Agent is an advanced AI agent framework. A "Skill" is a reusable capability that teaches Hermes Agent how to perform complex workflows. The `SKILL.md` in this repository teaches Hermes Agent how to autonomously set up, maintain, and systematically debug the GLaDOS automatic daily check-in automation.

## Repository Contents
- **`SKILL.md`**: The primary declarative capability metadata and SOP blueprint file. Copy this file into your `~/.hermes/skills/productivity/` directory to instantly load the skill into your Hermes Agent.
- **`scripts/checkin.py`**: Production-grade automation core Python script (multi-domain failover, PushDeer notifications, multi-account support).
- **`scripts/checkin.sh`**: Wrapper daemon script with 3x retry logging logic designed for cron environments.
- **`scripts/logging_config.py`**: Local time standardization config formatter (Beijing time standard).

## Getting Started
To learn how to configure your cookies, deploy the scheduler, and set up fail-safes, read [SKILL.md](./SKILL.md).

---
Created and published by **程序员Devil & Hermes Agent**.
