# Copyright DST Group. Licensed under the MIT license.
from ipaddress import IPv4Address, IPv4Network
from typing import List
import re

from CybORG.Shared.Actions.SessionAction import SessionAction
from CybORG.Simulator.Host import Host
from CybORG.Simulator.Interface import Interface
from CybORG.Simulator.MSFServerSession import MSFServerSession
from CybORG.Simulator.Session import Session
from CybORG.Simulator.State import State
from CybORG.Simulator.Subnet import Subnet

lo_subnet = IPv4Network('127.0.0.0/8')
lo = IPv4Address('127.0.0.1')

class MSFAction(SessionAction):
    def __init__(self, session, agent):
        super().__init__(session)
        self.agent = agent


    def get_lhost(self, ltunnel):
        tunnel_conn = re.match("(.*):(.*)",ltunnel)
        tunnel = re.match("(.*)-(.*)",tunnel_conn[1])
        if tunnel:
            lhost = tunnel[1]
        else:
            lhost = tunnel_conn[1]
        return lhost

    def get_local_source_interface(self, local_session, remote_address: IPv4Address, state: State) -> (Session, Interface):
        # ignore local_session parameter. This is to ensure backward compatbility
        # this identifies the whether there is session that contains a route to the remote_address
        #
        # first, check if there is a match of an existing session route
        # breakdown list comp
        sessions = [s for s in state.sessions[self.agent] ]
        routes = [ r for s in sessions for r in s.routes]
        session_routes = [ s for s in state.sessions[self.agent] for r in s.routes if remote_address in r]
        if len(session_routes)== 0:
            return None, None
        target_session = session_routes[0]
        # the following checks for a subnet on the session host that contains the remote_addr
        # this isn't always the case, as there may be a route via a gateway
        for interface in state.hosts[target_session.host].interfaces:
            if remote_address in interface.subnet:
               return local_session, interface
        # is there an edge case where there is no route in the session but there is a route on the interface?
        # yes. if a shell exists on target, but autoroute hasn't been executed.
        # or there is a route in the session but not on any interface?
        # yes, if target is accessible via gateway
        # assuming valid session route implies network routability
        # if no matching interface, return first non-local interface
        for interface in state.hosts[target_session.host].interfaces:
            if interface.name != 'lo':
               return local_session, interface

        return None,None

    def get_local_source_interface_original(self, local_session: Session, remote_address: IPv4Address, state: State) -> (Session, Interface):
        # discovers the local session and interface from routing through existing sessions
        remote_subnet = state.get_subnet_containing_ip_address(remote_address)
        # if MSF server then attempt to use the routes generated by autoroute
        if type(local_session) is MSFServerSession:
            for session, interfaces in local_session.routes.items():
                for interface in interfaces:
                    # find if remote address is in the sessions subnet
                    if remote_address in interface.subnet:
                        return local_session.children[session], interface
                    # find if the remote address is in a routable subnet
                    if interface.name in remote_subnet.nacls:
                        return local_session, interface
        for interface in state.hosts[local_session.host].interfaces:
            # find if remote address is in the sessions subnet
            if remote_address in interface.subnet:
                return local_session, interface

            # find if the remote address is in a routable subnet
            if interface.name != 'lo':
              # this doesn't determine routeability.  Only if there is network filtering
              # removing this for the moment.
              # this would require a bit more complexity. as the nacls are expressed as in/out
              # also not sure if there is any intention for allow/deny functionality.
              return local_session, interface

        return None, None

    def test_nacl(self, port, target_subnet: Subnet, originating_subnet: Subnet) -> bool:
        # return true if target subnet can receive traffic from originating subnet over specified port
        if originating_subnet == target_subnet:
            #no nacl block inside subnet
            return True

        if originating_subnet.name not in target_subnet.nacls:
            return False
        if 'all' in [i for i in target_subnet.nacls[originating_subnet.name]['in']]:
            return True
        if port in [i['PortRange'] for i in target_subnet.nacls[originating_subnet.name]['in'] if
                    type(i['PortRange']) is int]:
            return True
        return False

    def check_routable(self, from_subnets: List[Subnet], to_subnets: List[Subnet]) -> dict:
        """
        Checks which ports in from_subnets can be accessed by hosts in to_subnets.

        Checks NACL data to see if any ports are blocked.
        """
        # check what ports from subnets allow to any to subnets
        ports = {} # port: (to_subnet, from_subnet)
        for from_subnet in from_subnets:
            for to_subnet in to_subnets:
                # check if traffic from subnet is stopped by to subnet nacl
                if from_subnet.name in to_subnet.nacls:
                    if 'ICMP' not in ports:
                       ports['ICMP'] = (from_subnet.cidr, to_subnet.cidr)
                    if 'all' in to_subnet.nacls[from_subnet.name]['in']:
                        # if all ports accepted in then set ports to all and we are done
                        return {'all': (from_subnet.cidr, to_subnet.cidr)}
                    elif 'None' in to_subnet.nacls[from_subnet.name]['in']:
                        # If you don't have access to Enteprise network, you can't act on Operational Host
                        # TODO refactor this hacky fix
                        permission = self.check_for_enterprise_sessions()
                        ports = {'all': (from_subnet.cidr, to_subnet.cidr)} if permission else {}
                        return ports

                    else:
                        # we only add the ports in rules to our accepted ports
                        for rule in to_subnet.nacls[from_subnet.name]['in']:
                            if rule['PortRange'] is int and rule['PortRange'] not in ports:
                                ports[rule["PortRange"]] = (from_subnet.cidr, to_subnet.cidr)
                            else:
                                for p in range(rule["PortRange"][0], rule["PortRange"][1]):
                                    if p not in ports:
                                        ports[p] = (from_subnet.cidr, to_subnet.cidr)
                elif 'all' in to_subnet.nacls:
                    if 'ICMP' not in ports:
                        ports['ICMP'] = (from_subnet.cidr, to_subnet.cidr)
                    # if all ports accepted out then use inbound rules only
                    if 'all' in to_subnet.nacls['all']['in']:
                        # if all ports accepted in then set ports to all and we are done
                        return {'all': (from_subnet.cidr, to_subnet.cidr)}
                    else:
                        # we only add the ports in rules to our accepted ports
                        for rule in to_subnet.nacls['all']['in']:
                            if rule['PortRange'] is int and rule['PortRange'] not in ports:
                                ports[rule["PortRange"]] = (from_subnet.cidr, to_subnet.cidr)
                            else:
                                for p in range(rule["PortRange"][0], rule["PortRange"][1]):
                                    if p not in ports:
                                        ports[p] = (from_subnet.cidr, to_subnet.cidr)
                else:
                    # this means that traffic cannot reach move between these 2 subnets
                    continue

        return ports

    def __str__(self):
        return f"{self.__class__.__name__}: MSF Session: {self.session}"
