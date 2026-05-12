# AGENTS.md

## Cursor Cloud specific instructions

This is a greenfield repository ("equibets" — a personal eventing results calculator and data storage system). As of now, the repository contains only a `README.md` with no application code, dependencies, or configuration.

### Current state

- **No application code, build system, or dependency files exist yet.**
- No lint, test, or build commands are available.
- No services to start or ports to expose.

### When code is added

Once the project is bootstrapped with a framework and dependency files, future agents should:

1. Update the VM environment update script (via `SetupVmEnvironment`) to install dependencies (e.g., `npm install`, `pip install -r requirements.txt`).
2. Update this section with lint/test/build/run commands and any non-obvious caveats.
