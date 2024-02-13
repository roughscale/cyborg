from CybORG import CybORG
from CybORG.Agents.Wrappers.EnumActionWrapper import EnumActionWrapper
from CybORG.Agents.Wrappers.FixedFlatWrapper import FixedFlatWrapper
from CybORG.Agents.Wrappers.FixedFlatStateWrapper import FixedFlatStateWrapper
from CybORG.Agents.Wrappers.OpenAIGymWrapper import OpenAIGymWrapper
#from CybORG.Agents.SimpleAgents.RedRandomAgent import RedRandomAgent
from CybORG.Shared.Results import Results
from CybORG.Shared.State import State
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.evaluation import evaluate_policy
import inspect
import sys
import time
import copy
import os

# number of evaulation episodes
n_eval_eps=1

env_config = {
   "fully_obs": True,
   "max_params": {
        "MAX_HOSTS": 5,
        "MAX_PROCESSES": 5,
        "MAX_CONNECTIONS": 2,
        "MAX_VULNERABILITIES": 1,
        "MAX_INTERFACES": 2,
        "MAX_SESSIONS": 5,
        "MAX_USERS": 5,
        "MAX_FILES": 0,
        "MAX_GROUPS": 0,
        "MAX_PATCHES": 0
   }
}

path = str(inspect.getfile(CybORG))
n_envs=1

# TestScenario is Scenario1b with only a Red RedMeanderAgent config
# seems that Scenarios MUST have agents declared ??
# seems that the actions listed in an Agent spec are actually Agent classes??
# this is going to cause some difficulties in generalising actions!
scenario_path = path[:-10] + "/Shared/Scenarios/TestMSFSessionDQNScenario.yaml"
model_path=path[:-17] + "/exports/dqn_20231223_2000"
#print(path)

cyborg = CybORG(scenario_path,'qemu', env_config=env_config)

# print env controller network/environment state (ie not agent state!)
#environment=cyborg.environment_controller.state
#print()
# the following returns the AgentInterface
agent=cyborg.environment_controller.agent_interfaces["Red"]
#unwrapped_action_space=agent.action_space.get_action_space()
wrapped_env = FixedFlatStateWrapper(EnumActionWrapper(cyborg),max_params=env_config["max_params"])
#env = OpenAIGymWrapper(env=wrapped_env, agent_name="Red")
# wraps env in DummyVecEnv VecEnv environment
env = make_vec_env(lambda: OpenAIGymWrapper(env=wrapped_env, agent_name="Red"),n_envs=n_envs)

# print openaigym action and observation spaces
print(env.action_space) # Discrete

# load agent from export file
model=agent.agent.load("DuelingDQN",model_path)

# initialise agent learning
#agent.agent.initialise(env,gamma,initial_epsilon,final_epsilon,total_steps,double,dueling)
#callback=agent.agent.learn_callback

start=time.time()
print("Evaluation start: {}".format(time.ctime(start)))
print()
#agent.agent.dqn.learn(total_timesteps=total_steps,log_interval=1,callback=callback)
print(dir(model))
print(type(model))
mean_reward, std_reward = evaluate_policy(model.dqn.policy, env, n_eval_episodes=n_eval_eps, deterministic=True)
end=time.time()
print(mean_reward)
print(std_reward)
print("Evaluation end: {}".format(time.ctime(end)))

# save model to file
#agent.agent.dqn.save(curr_dir+"/exports/dqn.zip")

