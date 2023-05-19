from collections.abc import Mapping, Set
from itertools import islice
from mesa import Agent


class AgentView(Mapping, Set):
    """A lazy-loaded list of agents."""

    __slots__ = ("_agents", "agents_by_type")

    def __init__(self, agents, agents_by_type):
        self._agents = agents
        self.agents_by_type = agents_by_type

    def __getstate__(self):
        return {"_agents": self._agents}

    def __setstate__(self, state):
        self._agents = state["_agents"]

    # Mapping methods
    def __len__(self):
        return len(self._agents)

    def __iter__(self):
        yield from self._agents.values()

    def __getitem__(self, agent_id):
        if isinstance(agent_id, slice):
            raise ValueError(f"Slicing is not supported")
        if agent_id in self._agents:
            return self._agents[agent_id]
        raise ValueError(f"Agent {agent_id} not found")

    def filter(self, agent_class=None, include_subclasses=True, **kwargs):
        if agent_class and self.agents_by_type:
            if not include_subclasses:
                return filter_agents(self.agents_by_type[agent_class],
                                    **kwargs)
            else:
                d = {}
                for k, v in self.agents_by_type.items():
                    if (k == agent_class) or issubclass(k, agent_class):
                        d.update(v)
                return filter_agents(d, **kwargs)
        return filter_agents(self._agents, agent_class=agent_class, **kwargs)


    def one(self, *args, **kwargs):
        try:
            return next(self.filter(*args, **kwargs))
        except StopIteration:
            return None

    def __call__(self, *args, **kwargs):
        return list(self.filter(*args, **kwargs))

    def __contains__(self, agent_id):
        if isinstance(agent_id, Agent):
            agent_id = agent_id.unique_id
        return agent_id in self._agents

    def __str__(self):
        return str(list(unique_id for unique_id in self.keys()))

    def __repr__(self):
        return f"{self.__class__.__name__}({self})"


def filter_agents(
    agents: dict,
    *id_args,
    unique_id=None,
    state_id=None,
    agent_class=None,
    ignore=None,
    state=None,
    limit=None,
    **kwargs,
):
    """
    Filter agents given as a dict, by the criteria given as arguments (e.g., certain type or state id).
    """
    assert isinstance(agents, dict)

    ids = []

    if unique_id is not None:
        if isinstance(unique_id, list):
            ids += unique_id
        else:
            ids.append(unique_id)

    if id_args:
        ids += id_args

    if ids:
        f = list(agents[aid] for aid in ids if aid in agents)
    else:
        f = agents.values()

    if state_id is not None and not isinstance(state_id, (tuple, list)):
        state_id = tuple([state_id])

    if ignore:
        f = filter(lambda x: x not in ignore, f)

    if state_id is not None:
        f = filter(lambda agent: agent.get("state_id", None) in state_id, f)

    if agent_class is not None:
        f = filter(lambda agent: isinstance(agent, agent_class), f)

    state = state or dict()
    state.update(kwargs)

    for k, vs in state.items():
        if not isinstance(vs, list):
            vs = [vs]
        f = filter(lambda agent: any(getattr(agent, k, None) == v for v in vs), f)

    if limit is not None:
        f = islice(f, limit)

    return AgentResult(f)

class AgentResult:
    def __init__(self, iterator):
        self.iterator = iterator
    
    def limit(self, limit):
        self.iterator = islice(self.iterator, limit)
        return self

    def __iter__(self):
        return iter(self.iterator)

    def __next__(self):
        return next(self.iterator)