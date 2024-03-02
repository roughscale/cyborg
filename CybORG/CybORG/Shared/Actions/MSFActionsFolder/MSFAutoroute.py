# Copyright DST Group. Licensed under the MIT license.
from ipaddress import IPv4Network

from CybORG.Shared.Actions.MSFActionsFolder.MSFAction import MSFAction
from CybORG.Shared.Enums import SessionType
from CybORG.Shared.Observation import Observation
from CybORG.Simulator.State import State


class MSFAutoroute(MSFAction):
    def __init__(self, agent, session, ip_address):
        super().__init__(session, agent)
        self.ip_address = ip_address

    def sim_execute(self, state: State):
        obs = Observation()
        # check server session
        server_sessions = [ s for s in state.sessions['Red'] if s.ident == self.session and s.session_type == SessionType.MSF_SERVER and s.active ]
        if len(server_sessions) == 0:
            # invalid server session
            obs.set_success(False)
            return obs
        # choose first server session
        msf_session = server_sessions[0]
        # NEED TO FIX
        # we need a session handler for the Simulated case.
        # at the moment we retrieve this directly from the State object
        # we need to identify the sessions on the host
        # check target session
        interfaces = []
        print(state.sessions[self.agent])
        hostname = state.ip_addresses[self.ip_address]
        print(hostname)
        # breakdown list comp
        session_hosts = [ s.host for s in state.sessions[self.agent] ]
        # Documentation claims Autoroute can also work on SSH-type sessions.
        host_sessions = [ s for s in state.sessions[self.agent] if s.host == hostname and s.session_type == SessionType.METERPRETER ]
        print(host_sessions)
        if len(host_sessions) == 0:
            obs.set_success(False)
            return obs
        # choose first target session if more than one
        meterpreter_session = host_sessions[0]
        print(meterpreter_session)
        # not sure about session children at the moment
        #if meterpreter_session in msf_session.children.values() and meterpreter_session.session_type == SessionType.METERPRETER:
        obs.set_success(True)
        routes = []
        # for autoroute, we don't add interface observations.  We add the routes to the existing session object
        for interface in state.hosts[meterpreter_session.host].interfaces:
                if str(interface.ip_address) != '127.0.0.1':
                    #    interfaces.append(interface)
                    #    obs.add_interface_info(hostid=str(self.ip_address), subnet=interface.subnet)
                    print(interface.subnet)
                    routes.append(IPv4Network(interface.subnet))

        if len(routes) > 0:
                # update simulator state change
                print("update host session routes in state")
                sess = meterpreter_session
                sess.add_routes(routes)
                # add session observation
                print("updated host session state")
                print(sess.get_state())
                obs.add_session_info(hostid=sess.host, session_id=sess.ident, session_type=sess.session_type, agent=sess.agent, routes=sess.routes, username=sess.username, pid=sess.pid, active=sess.active)
                #msf_session.routes[self.ip_address] = interfaces
        else:
            obs.set_success(False)
        return obs

    def emu_execute(self, session_handler) -> Observation:
        obs = Observation()
        from CybORG.Emulator.Session import MSFSessionHandler
        if type(session_handler) is not MSFSessionHandler:
            obs.set_success(False)
            return obs

        sessions = session_handler.get_session_by_remote_ip(str(self.ip_address), session_type="meterpreter")
        print(sessions)
        if len(sessions) == 0:
            print("no meterpreter session for host {}".format(str(self.ip_address)))
            obs.set_success(False)
            return obs

        session = list(sessions.keys())[0]
        output = session_handler.execute_module(mtype='post', mname='multi/manage/autoroute',
                                         opts={'SESSION': session})
        obs.add_raw_obs(output)
        """Example:
        [!] SESSION may not be compatible with this module.
        [*] Running module against 10.0.2.164
        [*] Searching for subnets to autoroute.
        [+] Route added to subnet 10.0.2.0/255.255.254.0 from host's routing table.
        [*] Post module execution completed
        """
        obs.set_success(False)
        routes = []
        for line in output.split('\n'):
            if '[+] Route added' in line:
                obs.set_success(True)
                subnet = line.split(' ')[5]
                # for autoroute, we don't add interface observations.  We add the routes to the existing session object
                #obs.add_interface_info(hostid=str(self.ip_address), subnet=IPv4Network(subnet))
                routes.append(IPv4Network(subnet))
        
        if len(routes) > 0:
            # get existing session
            sess = sessions[session]
            print(sess)
            #obs.add_session_info(hostid=self.ip_address, session_id=session, session_type=sess.session_type, agent=sess.agent, routes=routes, username=sess.username, pid=sess.pid, active=sess.active)
            obs.add_session_info(hostid=str(self.ip_address), session_id=session, routes=routes, session_type=sess["type"], username=sess["username"],agent=self.agent)
            #obs.add_session_info(routes=routes, **sessions[session].get_state())

        return obs

    def __str__(self):
        return super(MSFAutoroute, self).__str__() + f", Meterpreter Session: {self.ip_address}"
