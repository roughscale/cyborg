# ObsHistoryWrapper: Refactoring AgentState

## Overview

`ObsHistoryWrapper` replaces the `fully_obs=True` / `AgentState` mechanism built into the CybORG environment controller. It accumulates partial observations into a full running state at the wrapper level, with no changes required to core CybORG classes.

**Parity verification**: 10,000-step random-policy run against the original `AgentState` path confirmed identical state accumulation across all action types (pingsweep, port scan, SSH exploit, MS17-010, meterpreter upgrade, JuicyPotato, SubUidShell).

## Files Changed

| File | Change |
|---|---|
| `CybORG/CybORG/Agents/Wrappers/ObsHistoryWrapper.py` | New — `AccumulatedState` + `ObsHistoryWrapper` classes |
| `CybORG/CybORG/Agents/Wrappers/__init__.py` | Export `ObsHistoryWrapper` |
| `CybORG/CybORG/CybORG.py` | `env_config` default changed from `None` to `{}` |
| `CybORG/CybORG/Shared/Actions/MSFActionsFolder/MSFPrivilegeEscalationFolder/MSFJuicyPotato.py` | Session filter: require active METERPRETER/MSF_SHELL/SSH |
| `CybORG/CybORG/Shared/Actions/MSFActionsFolder/MSFPrivilegeEscalationFolder/MSFSubUidShell.py` | Same session filter |
| `CybORG/CybORG/Shared/Actions/MSFActionsFolder/UpgradeToMeterpreter.py` | Only MSF_SHELL sessions can be upgraded |
| `CybORG/openai_dqn_msf_test.py` | Wrapper chain updated (see below) |

## Migration

### Before

```python
env_config = {"fully_obs": True}
cyborg = CybORG(scenario_path, 'sim', env_config=env_config)
wrapped = FixedFlatWrapper(EnumActionWrapper(cyborg), max_params=env_config["max_params"])
```

### After

```python
cyborg = CybORG(scenario_path, 'sim')
wrapped = FixedFlatWrapper(EnumActionWrapper(ObsHistoryWrapper(cyborg, agents=['Red'])))
```

`ObsHistoryWrapper` **must** wrap CybORG directly, before `FixedFlatWrapper`. It operates on dict observations; `FixedFlatWrapper` converts dicts to vectors and must come after.

## Wrapper Chain

```
CybORG → ObsHistoryWrapper → EnumActionWrapper → FixedFlatWrapper → OpenAIGymWrapper
```

## Usage

```python
from CybORG import CybORG
from CybORG.Agents.Wrappers import ObsHistoryWrapper

cyborg = CybORG(scenario_path, 'sim')
wrapped = ObsHistoryWrapper(cyborg, agents=['Red'])

result = wrapped.reset(agent='Red')
# result.observation — accumulated state dict, same as original AgentState.data
# result.state      — same (kept for compatibility)

result = wrapped.step(agent='Red', action=action)
# result.observation updated with merged observation
```

### Multi-agent

Each agent maintains an independent `AccumulatedState`. Discoveries made by Red are not visible in Blue's state.

```python
wrapped = ObsHistoryWrapper(cyborg, agents=['Red', 'Blue'])
red_result = wrapped.step(agent='Red', action=red_action)
blue_result = wrapped.step(agent='Blue', action=blue_action)
```

### Max elements (for FixedFlatWrapper sizing)

```python
max_elements = wrapped.get_max_elements()
# {"hosts": N, "processes": N, "sessions": N, "connections": N, "interfaces": N, "subnets": N}
```

## Design Notes

`AccumulatedState` (internal class in `ObsHistoryWrapper.py`) mirrors `AgentState` behaviour exactly:

- Composition over inheritance — does not extend `Observation`
- `initialise_state(scenario)` — pre-populates host keys for consistent observation space
- `update(observation, agent)` — merges new observation into accumulated state
- `merge_session_info` / `merge_process` — faithful copies of `AgentState` merge logic
- `add_session_info` matches `Observation.add_session_info` exactly: PID is only stored when passed as the `pid` positional parameter, not looked up from kwargs (key behavioural parity point verified in testing)

## Tests

| Script | Location | Purpose |
|---|---|---|
| `test_full_obs_wrapper.py` | `CybORG/` | Smoke test — reset/step/get_max_elements |
| `test_obs_parity.py` | `CybORG/` | Step-by-step parity against original `AgentState` |

Run parity test:

```bash
python test_obs_parity.py --steps 10000 --seed 42
```
