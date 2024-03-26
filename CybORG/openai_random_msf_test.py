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

# set max params for observation vector sizei
# other than MAX_HOSTS, they are max per host
env_config = {
   "fully_obs": True
}

path = str(inspect.getfile(CybORG))
curr_dir = os.getcwd()

# TestScenario is Scenario1b with only a Red RedMeanderAgent config
# seems that Scenarios MUST have agents declared ??
# seems that the actions listed in an Agent spec are actually Agent classes??
# this is going to cause some difficulties in generalising actions!
path = path[:-10] + "/Shared/Scenarios/TestMSFSessionRandomScenario.yaml"
#print(path)

cyborg = CybORG(path,'sim', env_config=env_config)

# print env controller network/environment state (ie not agent state!)
#environment=cyborg.environment_controller.state
#print()
# the following returns the AgentInterface
agent=cyborg.environment_controller.agent_interfaces["Red"]
#unwrapped_action_space=agent.action_space.get_action_space()
#action_env=EnumActionWrapper(cyborg)
#print("action env get action space")
#print(action_env.get_action_space(agent="Red"))
#wrapped_env = FixedFlatStateWrapper(action_env, max_params=env_config["max_params"])
#print("wrapped env get action space")
#print(wrapped_env.get_action_space(agent="Red"))
wrapped_env = FixedFlatStateWrapper(EnumActionWrapper(cyborg))
env = OpenAIGymWrapper(env=wrapped_env, agent_name="Red")
# wraps env in DummyVecEnv VecEnv environment
#env = make_vec_env(lambda: OpenAIGymWrapper(env=wrapped_env, agent_name="Red"),n_envs=n_envs)

# print openaigym action and observation spaces

print(env.action_space) # Discrete
print(type(env.action_space))
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
    #action=env.env.possible_actions[action_num]
    #print("Action: {0}".format(action))
    # wrapped step method needs an action_num (possible_actions index)
    observation, reward, done, _, info = env.step(action_num)
    print("Reward: {0}".format(reward))
    print("Done: {0}".format(done))
    print()
    step += 1
    if done:
      print("Goal succeeded in {0} steps".format(step))
end=time.time()
print("Episodes end: {}".format(time.ctime(end)))

