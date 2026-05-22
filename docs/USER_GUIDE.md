# OVOS-EnMS User Guide

This guide is for operators, energy managers, and reviewers who use the
HumanEnerDIA OVOS assistant through text, voice, or the REST bridge.

## What the Assistant Does

The assistant answers natural-language questions about industrial energy
management data from a HumanEnerDIA-compatible backend.

It can help with:

- machine status
- current power and energy consumption
- factory summaries
- top energy consumers
- machine comparisons
- anomalies and alerts
- forecasts
- KPIs and ISO 50001-oriented questions
- baseline and driver-analysis questions where backend data is available

The assistant does not replace engineering review. Treat its answers as
decision support and confirm important findings in dashboards or source data.

## Access Methods

Common access paths:

- REST query endpoint: `http://localhost:5000/query`
- REST bridge docs: `http://localhost:5000/docs`
- Portal or widget integration when connected through HumanEnerDIA
- Optional Windows/WSL2 audio bridge for local microphone workflows

Screenshot to add:

```text
docs/images/user-guide/assistant-query.png
```

## Example Questions

Machine status:

- "What is the status of Compressor-1?"
- "Is HVAC-Main running?"
- "Check all machines."

Energy and power:

- "What is the power consumption of Compressor-1?"
- "How much energy did Boiler-1 use yesterday?"
- "Total factory energy consumption."

Analysis:

- "Top three energy consumers."
- "Compare Compressor-1 and Boiler-1."
- "Detect anomalies for Compressor-1 today."

Forecasting and reporting:

- "Forecast energy for tomorrow."
- "Show KPIs for Compressor-1 today."
- "Generate an energy performance report."

## Writing Good Queries

For best results:

- include the machine name when asking about one machine
- include a time period when asking historical questions
- use one request at a time
- use known machine names from the backend when possible
- ask shorter questions if the assistant asks for clarification

Examples:

```text
Good: "How much energy did Compressor-1 use yesterday?"
Less clear: "What happened before?"
```

## What to Do When an Answer Looks Wrong

1. Repeat the question with the machine name and time period.
2. Check whether HumanEnerDIA backend health is green.
3. Confirm the machine exists in the backend.
4. Compare with Grafana or the HumanEnerDIA portal.
5. Escalate to a technical maintainer if the issue repeats.

Include the query text, time, session ID if available, and screenshot.

## Screenshot Placeholders

- `docs/images/user-guide/assistant-query.png`
- `docs/images/user-guide/assistant-response.png`
- `docs/images/user-guide/voice-widget.png`
