# OVOS-EnMS Documentation

This index points to the maintained documentation for the HumanEnerDIA OVOS
integration.

## Start Here

| Need | Read |
|---|---|
| Use the assistant as an operator or energy user | [User Guide](./USER_GUIDE.md) |
| Install and configure the Docker deployment | [Installation and Configuration](./INSTALLATION_AND_CONFIGURATION.md) |
| Understand the system architecture | [Technical Architecture Guide](./TECHNICAL_ARCHITECTURE_GUIDE.md) |
| Operate and troubleshoot the runtime | [Operations Runbook](./OPERATIONS_RUNBOOK.md) |
| Integrate through HTTP | [REST Bridge API Reference](./REST_BRIDGE_API_REFERENCE.md) |
| Understand supported query types | [Query Capabilities](./QUERY_CAPABILITIES.md) |
| Configure the optional local model fallback | [LLM Fallback Model Guide](./LLM_FALLBACK_MODEL_GUIDE.md) |

## Repository Components

- `enms-ovos-skill/`: OVOS skill package and runtime configuration.
- `enms-ovos-skill/bridge/`: REST, Windows, and WSL2 bridge utilities.
- `Dockerfile`: headless OVOS image with messagebus, skills service, and REST bridge.
- `docker-compose.yml`: single-container OVOS deployment that joins the
  HumanEnerDIA Docker network.
- `supervisord.conf`: process supervisor for messagebus, OVOS core, and REST bridge.

## Important Notes

- The HumanEnerDIA backend is required for live energy answers.
- The local LLM fallback is optional and is not bundled with this repository.
- The Docker deployment expects access to the HumanEnerDIA network named
  `enms-network` by default.
- The REST bridge is a proxy into OVOS; it does not implement energy logic by
  itself.

## Screenshot Placeholder Paths

Use these folders for future screenshots:

```text
docs/images/user-guide/
docs/images/architecture/
docs/images/operations/
```
