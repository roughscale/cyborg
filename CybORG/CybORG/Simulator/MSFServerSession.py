# Copyright DST Group. Licensed under the MIT license.
from CybORG.Simulator.Session import Session
from CybORG.Simulator.Process import Process


class MSFServerSession(Session):

    def __init__(self, ident: str, host: str, user: str, agent: str,
                 process: Process, timeout: int = 0, session_type: str = 'msf server', name=None, routes={}):
        super().__init__(ident, host, user, agent,
                 process, timeout, session_type, name=name)
        self.routes = routes  # routes have the structure sessionid: list of subnets
          

    def dead_child(self, child_id: int):
        super().dead_child(child_id)
        if child_id in self.routes:
            self.routes.pop(child_id)

    def add_route(self, route: dict):
        for nk,nv in route.items():
            for ek,ev in self.routes.items():
                if nk == ek:
                    # matching session
                    for nr in route.values():
                      for er in self.routes.values():
                          if nr == er:
                              # matching route
                              pass
                          else:
                              self.routes[ek].append(nr)
                    return
        # no matching session
        self.routes.update(route)

