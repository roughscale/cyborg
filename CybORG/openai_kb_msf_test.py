from CybORG import CybORG
import inspect
import sys
import time
import os

path = str(inspect.getfile(CybORG))
curr_dir = os.getcwd()

path = path[:-10] + "/Shared/Scenarios/TestMSFSessionKBScenario.yaml"

env_config = {
  "fully_obs": True
}

cyborg = CybORG(path, 'sim', env_config=env_config)

agent_interface = cyborg.environment_controller.agent_interfaces["Red"]

start = time.time()
print("Episodes start: {}".format(time.ctime(start)))
print()

result = cyborg.reset(agent="Red")
action_space = result.action_space

for step in range(0, 200):
    action = agent_interface.agent.get_action(result.observation, action_space)
    result = cyborg.step(agent=agent_interface.agent_name, action=action)
    print("Reward: {0}".format(result.reward))
    print("Done: {0}".format(result.done))
    action_space = result.action_space
    print()
    if result.done:
        print("Goal succeeded")
        sys.exit(0)

