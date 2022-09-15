from __future__ import annotations
from pydantic import BaseModel, ValidationError, validator, root_validator

import yaml
import os
import sys

from typing import Any, Callable, Dict, List, Optional, Union, Type
from pydantic import BaseModel, Extra

class General(BaseModel):
    id: str = 'Unnamed Simulation'
    group: str = None
    dir_path: Optional[str] = None
    num_trials: int = 1
    max_time: float = 100
    interval: float = 1
    seed: str = ""

    @staticmethod
    def default():
        return General()


# Could use TypeAlias in python >= 3.10
nodeId = int

class Node(BaseModel):
    id: nodeId
    state: Optional[Dict[str, Any]] = {}


class Edge(BaseModel):
    source: nodeId
    target: nodeId
    value: Optional[float] = 1


class Topology(BaseModel):
    nodes: List[Node]
    directed: bool
    links: List[Edge]


class NetParams(BaseModel, extra=Extra.allow):
    generator: Union[Callable, str]
    n: int 


class NetConfig(BaseModel):
    group: str = 'network'
    params: Optional[NetParams]
    topology: Optional[Topology]
    path: Optional[str]

    @staticmethod
    def default():
        return NetConfig(topology=None, params=None)

    @root_validator
    def validate_all(cls,  values):
        if 'params' not in values and 'topology' not in values:
            raise ValueError('You must specify either a topology or the parameters to generate a graph')
        return values


class EnvConfig(BaseModel):
    environment_class: Union[Type, str] = 'soil.Environment'
    params: Dict[str, Any] = {}
    schedule: Union[Type, str] = 'soil.time.TimedActivation'

    @staticmethod
    def default():
        return EnvConfig()


class SingleAgentConfig(BaseModel):
    agent_class: Optional[Union[Type, str]] = None
    agent_id: Optional[int] = None
    topology: Optional[str] = 'default'
    name: Optional[str] = None
    state: Optional[Dict[str, Any]] = {}

class FixedAgentConfig(SingleAgentConfig):
    n: Optional[int] = 1

    @root_validator
    def validate_all(cls,  values):
        if values.get('agent_id', None) is not None and values.get('n', 1) > 1:
            print(values)
            raise ValueError(f"An agent_id can only be provided when there is only one agent ({values.get('n')} given)")
        return values


class OverrideAgentConfig(FixedAgentConfig):
    filter: Optional[Dict[str, Any]] = None


class AgentDistro(SingleAgentConfig):
    weight: Optional[float] = 1


class AgentConfig(SingleAgentConfig):
    n: Optional[int] = None
    topology: Optional[str] = None
    distribution: Optional[List[AgentDistro]] = None
    fixed: Optional[List[FixedAgentConfig]] = None
    override: Optional[List[OverrideAgentConfig]] = None

    @staticmethod
    def default():
        return AgentConfig()

    @root_validator
    def validate_all(cls,  values):
        if 'distribution' in values and ('n' not in values and 'topology' not in values):
            raise ValueError("You need to provide the number of agents or a topology to extract the value from.")
        return values


class Config(BaseModel, extra=Extra.forbid):
    version: Optional[str] = '1'
    general: General = General.default()
    topologies: Optional[Dict[str, NetConfig]] = {}
    environment: EnvConfig = EnvConfig.default()
    agents: Optional[Dict[str, AgentConfig]] = {}

def convert_old(old, strict=True):
    '''
    Try to convert old style configs into the new format.

    This is still a work in progress and might not work in many cases.
    '''


    new = {}


    general = {}
    for k in ['id', 
              'group',
              'dir_path',
              'num_trials',
              'max_time',
              'interval',
              'seed']:
        if k in old:
            general[k] = old[k]

    if 'name' in old:
        general['id'] = old['name']

    network = {}


    if 'network_params' in old and old['network_params']:
        for (k, v) in old['network_params'].items():
            if k == 'path':
                network['path'] = v
            else:
                network.setdefault('params', {})[k] = v

    if 'topology' in old:
        network['topology'] = old['topology']

    agents = {
        'network': {},
        'default': {},
    }

    if 'agent_type' in old:
        agents['default']['agent_class'] = old['agent_type']

    if 'default_state' in old:
        agents['default']['state'] = old['default_state']


    def updated_agent(agent):
        newagent = dict(agent)
        newagent['agent_class'] = newagent['agent_type']
        del newagent['agent_type']
        return newagent

    for agent in old.get('environment_agents', []):
        agents['environment'] = {'distribution': [], 'fixed': []}
        if 'agent_id' in agent:
            agent['name'] = agent['agent_id']
            del agent['agent_id']
            agents['environment']['fixed'].append(updated_agent(agent))
        else:
            agents['environment']['distribution'].append(updated_agent(agent))

    by_weight = []
    fixed = []
    override = []

    if 'network_agents' in old:
        agents['network']['topology'] = 'default'

        for agent in old['network_agents']:
            agent = updated_agent(agent)
            if 'agent_id' in agent:
                fixed.append(agent)
            else:
                by_weight.append(agent)

    if 'agent_type' in old and (not fixed and not by_weight):
        agents['network']['topology'] = 'default'
        by_weight = [{'agent_type': old['agent_type']}]

    
    # TODO: translate states
    if 'states' in old:
        states = old['states']
        if isinstance(states, dict):
            states = states.items()
        else:
            states = enumerate(states)
        for (k, v) in states:
            override.append({'filter': {'id': k},
                             'state': v
            })

    agents['network']['override'] = override
    agents['network']['fixed'] = fixed
    agents['network']['distribution'] = by_weight

    environment = {'params': {}}
    if 'environment_class' in old:
        environment['environment_class'] = old['environment_class']

    for (k, v) in old.get('environment_params', {}).items():
        environment['params'][k] = v

    return Config(version='2',
                  general=general,
                  topologies={'default': network},
                  environment=environment,
                  agents=agents)
