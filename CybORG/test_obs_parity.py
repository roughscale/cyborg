"""
Parity test: AgentState (fully_obs=True) vs AccumulatedState (ObsHistoryWrapper).

Uses a seeded random policy via EnumActionWrapper to drive a short episode,
exercising pingsweep, port scan, exploit, meterpreter upgrade, and privesc paths.

Compares AgentState.data vs AccumulatedState.data after every step.
First divergence and its field path are reported immediately.

Usage:
    python test_obs_parity.py [--steps N] [--seed S]
"""

import argparse
import copy
import inspect
import os
import random
import sys

import numpy as np

from CybORG import CybORG
from CybORG.Agents.Wrappers.EnumActionWrapper import EnumActionWrapper
from CybORG.Agents.Wrappers.ObsHistoryWrapper import ObsHistoryWrapper

SCENARIO = 'TestMSFSessionDQNScenario.yaml'
AGENT = 'Red'


def seed_all(seed: int):
    random.seed(seed)
    np.random.seed(seed)


def deep_diff(a, b, path=""):
    """Return list of (path, original_val, wrapper_val) for every differing leaf."""
    diffs = []
    if type(a) != type(b):
        diffs.append((path, a, b))
        return diffs
    if isinstance(a, dict):
        for k in set(list(a.keys()) + list(b.keys())):
            child = f"{path}.{k}" if path else str(k)
            if k not in a:
                diffs.append((child, "<missing>", b[k]))
            elif k not in b:
                diffs.append((child, a[k], "<missing>"))
            else:
                diffs.extend(deep_diff(a[k], b[k], child))
    elif isinstance(a, list):
        for i in range(max(len(a), len(b))):
            child = f"{path}[{i}]"
            if i >= len(a):
                diffs.append((child, "<missing>", b[i]))
            elif i >= len(b):
                diffs.append((child, a[i], "<missing>"))
            else:
                diffs.extend(deep_diff(a[i], b[i], child))
    else:
        if a != b:
            diffs.append((path, a, b))
    return diffs


def build_envs(scenario_path: str, seed: int):
    # Save PRNG state so both envs are initialised from the same seed.
    # State.__init__ uses random.sample / random.choice to assign subnet CIDRs
    # and IP addresses — both envs must see the same draws.
    seed_all(seed)
    init_rng_state = random.getstate()
    init_np_rng_state = np.random.get_state()

    # Original: fully_obs=True inside the controller
    orig_cyborg = CybORG(scenario_path, 'sim', env_config={"fully_obs": True})
    orig_env = EnumActionWrapper(orig_cyborg)
    orig_env.reset(agent=AGENT)
    orig_iface = orig_cyborg.environment_controller.agent_interfaces[AGENT]

    # Restore so new env sees identical PRNG draws during initialisation
    random.setstate(init_rng_state)
    np.random.set_state(init_np_rng_state)

    # New: ObsHistoryWrapper accumulates state outside the controller
    new_cyborg = CybORG(scenario_path, 'sim')
    new_wrapper = ObsHistoryWrapper(new_cyborg, agents=[AGENT])
    new_env = EnumActionWrapper(new_wrapper)
    sys.stdout = open(os.devnull, 'w')
    new_env.reset(agent=AGENT)
    sys.stdout = sys.__stdout__

    return orig_env, orig_iface, new_env, new_wrapper


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--steps', type=int, default=100)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    scenario_path = str(inspect.getfile(CybORG))
    scenario_path = scenario_path[:-10] + f"/Shared/Scenarios/{SCENARIO}"

    if not os.path.exists(scenario_path):
        print(f"Scenario not found: {scenario_path}")
        sys.exit(1)

    orig_env, orig_iface, new_env, new_wrapper = build_envs(scenario_path, args.seed)

    # Separate RNG for action selection — identical sequence for both runs
    action_rng = np.random.RandomState(args.seed)

    devnull = open(os.devnull, 'w')

    print(f"Scenario : {SCENARIO}")
    print(f"Agent    : {AGENT}")
    print(f"Steps    : {args.steps}  Seed: {args.seed}")
    print()
    print(f"{'Step':<6} {'Action':<30} {'Result'}")
    print("-" * 65)

    action_types_seen = set()
    total_diffs = 0
    first_divergence = None

    for step in range(args.steps):
        n_actions = len(orig_env.possible_actions)
        action_idx = int(action_rng.randint(0, n_actions))
        action_name = orig_env.possible_actions[action_idx].__class__.__name__
        action_types_seen.add(action_name)

        # Save PRNG state before stepping so both envs see identical random draws
        # (e.g. UpgradeToMeterpreter calls random.randint for port numbers)
        rng_state = random.getstate()
        np_rng_state = np.random.get_state()

        # Step original
        orig_env.step(agent=AGENT, action=action_idx)
        orig_state = copy.deepcopy(orig_iface.state_space.data)

        # Restore PRNG state so new env sees the same draws
        random.setstate(rng_state)
        np.random.set_state(np_rng_state)

        # Step new (suppress ObsHistoryWrapper debug prints)
        sys.stdout = devnull
        new_env.step(agent=AGENT, action=action_idx)
        sys.stdout = sys.__stdout__
        new_state = copy.deepcopy(new_wrapper.agent_states[AGENT].data)

        diffs = deep_diff(orig_state, new_state)

        if diffs:
            total_diffs += len(diffs)
            if first_divergence is None:
                first_divergence = step
            print(f"{step:<6} {action_name:<30} DIVERGED  ({len(diffs)} field(s))")
            for path, orig_val, wrap_val in diffs[:5]:
                print(f"         path     : {path}")
                print(f"         original : {orig_val!r}")
                print(f"         wrapper  : {wrap_val!r}")
            if len(diffs) > 5:
                print(f"         ... and {len(diffs) - 5} more")
        else:
            print(f"{step:<6} {action_name:<30} OK")

    devnull.close()

    print()
    print("Action types exercised:")
    for name in sorted(action_types_seen):
        print(f"  {name}")

    # Flag any key paths not hit — test may need more steps or a different seed
    key_paths = {'MSFPingsweep', 'MSFPortscan', 'SSHLoginExploit',
                 'MS17_010_PSExec', 'UpgradeToMeterpreter',
                 'MSFJuicyPotato', 'MSFSubUidShell'}
    missing = key_paths - action_types_seen
    if missing:
        print(f"\nWARNING: key action types not exercised: {missing}")
        print("         Try a larger --steps value or a different --seed.")

    print()
    if total_diffs == 0:
        print("RESULT: IDENTICAL — ObsHistoryWrapper is a like-for-like replacement.")
    else:
        print(f"RESULT: DIVERGED  — first divergence at step {first_divergence}, "
              f"{total_diffs} total field difference(s).")


if __name__ == '__main__':
    main()
