# OVOS-EnMS Query Capabilities

This document describes the main query families supported by the HumanEnerDIA
OVOS skill.

The actual answer quality depends on backend data availability, machine names,
configured API URL, and whether optional model fallback is installed.

## Fast-Path Query Families

These are handled primarily by heuristic and Adapt routing:

| Query family | Example |
|---|---|
| Machine status | "What is the status of Compressor-1?" |
| Power | "What is the power of Compressor-1?" |
| Energy | "How much energy did Boiler-1 use yesterday?" |
| Factory overview | "Give me a factory overview." |
| Ranking | "Show the top three energy consumers." |
| Comparison | "Compare Compressor-1 and Boiler-1." |
| Cost | "What is the energy cost today?" |
| Anomalies | "Are there anomalies for Compressor-1?" |
| Forecast | "Forecast energy for tomorrow." |
| KPI | "Show KPIs for Compressor-1." |
| Production | "How many units did Conveyor-A produce?" |
| Reports | "Generate an energy performance report." |
| SEUs | "List significant energy uses." |
| Help | "What can I ask?" |

## Baseline and Advanced Analysis

Supported where backend data and models exist:

- baseline prediction
- baseline model list
- baseline explanation
- driver analysis
- performance analysis
- ISO 50001 EnPI-oriented reporting
- action-plan related report flows

## Query Writing Guidance

Use this structure when possible:

```text
<question> + <machine/factory> + <time period>
```

Examples:

```text
What is the power of Compressor-1?
How much energy did Boiler-1 use yesterday?
Show anomalies for HVAC-Main today.
Compare Compressor-1 and Boiler-1 for last week.
```

## Machine Names

The skill can fuzzy-match common spoken forms, but exact names are still best.
Default fallback examples include:

- `Compressor-1`
- `Boiler-1`
- `HVAC-Main`
- `Conveyor-A`
- `Injection-Molding-1`
- `Pump-1`

When connected to HumanEnerDIA, the skill can discover machines from the API.

## Limitations

- The REST bridge does not answer questions by itself; OVOS and the skill must
  be running.
- The HumanEnerDIA backend must have relevant data for live answers.
- Local LLM fallback is optional and slower than heuristic/Adapt routing.
- Very broad or multi-part questions may need to be split into shorter queries.
- Anomaly and forecast answers depend on model/data availability in the backend.

## Screenshot Placeholder

- `docs/images/user-guide/query-examples.png`
