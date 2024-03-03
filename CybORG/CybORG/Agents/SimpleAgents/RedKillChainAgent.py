from CybORG.Agents.SimpleAgents.BaseAgent import BaseAgent
import random
import math

from ipaddress import IPv4Network, IPv4Address

from CybORG.Shared.Actions import UpgradeToMeterpreter, MSFAutoroute, MSFPingsweep, SSHLoginExploit, Sleep, MS17_010_PSExec, MSFPortscan, MSFSubUidShell, MSFJuicyPotato, MeterpreterIPConfig

class RedKillChainAgent(BaseAgent):

    def __init__(self, action_size=None, state_size=None):

        host_external0 = "192.168.254.35"
        host_internal0 = "192.168.254.90"
        host_internal1 = "192.168.254.108"
        host_internal2 = "192.168.254.79"
        net_external = "192.168.254.0/26"
        net_internal = "192.168.254.64/26"

        self.killchains = {
          "internal1_juicy":  [
                [ MSFPingsweep, { "subnet":  IPv4Network(net_external) } ],
                [ MSFPortscan, { "ip_address":  IPv4Address(host_external0) } ],
                [ SSHLoginExploit, { "ip_address" : IPv4Address(host_external0), "port": 22 } ],
                [ MSFSubUidShell, { "ip_address": IPv4Address(host_external0) } ],
                [ MeterpreterIPConfig, { "ip_address":  IPv4Address(host_external0) } ],
                [ MSFAutoroute, { "ip_address": IPv4Address(host_external0) } ],
                [ MSFPingsweep, { "subnet": IPv4Network(net_internal) } ],
                [ MSFPortscan, { "ip_address": IPv4Address(host_internal1) } ],
                [ SSHLoginExploit, { "ip_address": IPv4Address(host_internal1), "port": 22 } ],
                [ UpgradeToMeterpreter, { "ip_address": IPv4Address(host_internal1) } ],
                [ MSFJuicyPotato, { "ip_address": IPv4Address(host_internal1) } ]
          ],           
          "internal1_pexec":  [
                [ MSFPingsweep, { "subnet":  IPv4Network("10.46.64.0/24") } ],
                [ MSFPortscan, { "ip_address":  IPv4Address("10.46.64.100") } ],
                [ SSHLoginExploit, { "ip_address" : IPv4Address("10.46.64.100"), "port": 22 } ],
                [ MSFSubUidShell, { "ip_address": IPv4Address("10.46.64.100") } ],
                [ MeterpreterIPConfig, { "ip_address":  IPv4Address("10.46.64.100") } ],
                [ MSFAutoroute, { "ip_address": IPv4Address("10.46.64.100") } ],
                [ MSFPingsweep, { "subnet": IPv4Network("10.58.85.0/24") } ],
                [ MSFPortscan, { "ip_address": IPv4Address("10.58.85.101") } ],
                [ SSHLoginExploit, { "ip_address": IPv4Address("10.58.85.101"), "port": 22 } ],
                [ MS17_010_PSExec, { "ip_address": IPv4Address("10.58.85.101") } ]
          ],
          "exploit_all":  [
                [ MSFPingsweep, { "subnet":  IPv4Network(net_external) } ],
                [ MSFPortscan, { "ip_address":  IPv4Address(host_external0) } ],
                [ SSHLoginExploit, { "ip_address" : IPv4Address(host_external0), "port": 22 } ],
                [ MSFSubUidShell, { "ip_address": IPv4Address(host_external0) } ],
                [ MeterpreterIPConfig, { "ip_address":  IPv4Address(host_external0) } ],
                [ MSFAutoroute, { "ip_address": IPv4Address(host_external0) } ],
                [ MSFPingsweep, { "subnet": IPv4Network(net_internal) } ],
                [ MSFPortscan, { "ip_address": IPv4Address(host_internal1) } ],
                [ SSHLoginExploit, { "ip_address": IPv4Address(host_internal1), "port": 22 } ],
                [ UpgradeToMeterpreter, { "ip_address": IPv4Address(host_internal1) } ],
                [ MSFJuicyPotato, { "ip_address": IPv4Address(host_internal1) } ],
                [ MSFPortscan, { "ip_address": IPv4Address(host_internal0) } ],
                [ SSHLoginExploit, { "ip_address": IPv4Address(host_internal0), "port": 22 } ],
                [ MSFSubUidShell, { "ip_address": IPv4Address(host_internal0) } ],
                [ MSFPortscan, { "ip_address": IPv4Address(host_internal2) } ],
                [ SSHLoginExploit, { "ip_address": IPv4Address(host_internal2), "port": 22 } ],
                [ MSFSubUidShell, { "ip_address": IPv4Address(host_internal2) } ]
          ]           
        }

        self.killchain = None
        self.count = 0

    def train(self, results):
        pass

    def get_action(self, observation, action_space, egreedy):
        #self.killchain = self.killchains["internal1_juicy"]
        self.killchain = self.killchains["exploit_all"]
        position = self.count % len(self.killchain)
        action_class = self.killchain[position][0]
        action_params = { "agent": "Red", "session": 0 }
        action_params.update(self.killchain[position][1])
        self.count += 1
        return action_class(**action_params)

    def end_episode(self):
        pass

    def set_initial_values(self, action_space, observation):
        pass

