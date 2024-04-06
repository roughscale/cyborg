from CybORG import CybORG
from CybORG.Agents.Wrappers.EnumActionWrapper import EnumActionWrapper
from CybORG.Agents.Wrappers.FixedFlatWrapper import FixedFlatWrapper
from CybORG.Agents.Wrappers.FixedFlatStateWrapper import FixedFlatStateWrapper
from CybORG.Agents.Wrappers.OpenAIGymWrapper import OpenAIGymWrapper
#from CybORG.Agents.SimpleAgents.RedRandomAgent import RedRandomAgent
from CybORG.Shared.Results import Results
from CybORG.Shared.State import State
from stable_baselines3.common.env_util import make_vec_env
import inspect
import sys
import time
import copy
import os

num_episodes=1
total_steps=200000

# set n_envs to 1 initially. No parallelisation
n_envs=1

# set max params for observation vector size
# other than MAX_HOSTS, they are max per host
env_config = {
   "fully_obs": True
}

path = str(inspect.getfile(CybORG))
curr_dir = os.getcwd()

path = path[:-10] + "/Shared/Scenarios/TestMSFSessionRandomScenario.yaml"

cyborg = CybORG(path,'sim', env_config=env_config)

# the following returns the AgentInterface
agent=cyborg.environment_controller.agent_interfaces["Red"]
wrapped_env = FixedFlatStateWrapper(EnumActionWrapper(cyborg))
env = OpenAIGymWrapper(env=wrapped_env, agent_name="Red")

observation=env.reset()
start=time.time()
print("Episodes start: {}".format(time.ctime(start)))
print()
done=False
step = 0
for ep in range(num_episodes):
  while not done:
    action_space=env.action_space
    action_num=agent.get_action(observation, action_space)
    print("Action Number: {0}".format(action_num))
    observation, reward, done, _, info = env.step(action_num)
    print("Reward: {0}".format(reward))
    print("Done: {0}".format(done))
    print()
    step += 1
    if done:
      print("Goal succeeded in {0} steps".format(step))
end=time.time()
print("Episodes end: {}".format(time.ctime(end)))
