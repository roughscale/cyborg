from CybORG import CybORG
from CybORG.Agents.SimpleAgents.Meander import RedMeanderAgent
import inspect
import sys

# The getattr(Python Module) returns all Classes within that Module
#action_module = sys.modules['CybORG.Shared.Actions']
#print(dir(action_module))
path = str(inspect.getfile(CybORG))
#print(path)
#path = path[:-10] + "/Shared/Scenarios/Scenario1b.yaml"
# TestScenario is Scenario1b with only a Red RedMeanderAgent config
# seems that Scenarios MUST have agents declared ??
# seems that the actions listed in an Agent spec are actually Agent classes??
# this is going to cause some difficulties in generalising actions!
path = path[:-10] + "/Shared/Scenarios/TestScenario.yaml"
#print(path)

env = CybORG(path,'sim')

results = env.reset()
#print(results)
obs = results.observation
#print(obs)

action_space = results.action_space
#print(action_space)
#print(list(action_space.keys()))

#print(dir(env))
print(env.environment_controller)
agent = env.environment_controller.agent_interfaces["Red"]
print(agent)
action = agent.get_action(action_space)
print(action)
rest = env.step(agent=agent.agent_name,action=action)
print(rest)
print(rest.observation)
