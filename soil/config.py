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
    dir_path: str = None
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
    state: Dict[str, Any]


class Edge(BaseModel):
    source: nodeId
    target: nodeId
    value: float = 1


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
    agent_class: Union[Type, str] = 'soil.Agent'
    agent_id: Optional[Union[str, int]] = None
    params: Dict[str, Any] = {}
    state: Dict[str, Any] = {}


class AgentDistro(SingleAgentConfig):
    weight: Optional[float] = None
    n: Optional[int] = None

    @root_validator
    def validate_all(cls,  values):
        if 'weight' in values and 'count' in values:
            raise ValueError("You may either specify a weight in the distribution or an agent count")
        return values


class AgentConfig(SingleAgentConfig):
    n: Optional[int] = None
    distribution: Optional[List[AgentDistro]] = None
    fixed: Optional[List[SingleAgentConfig]] = None

    @staticmethod
    def default():
        return AgentConfig()


class Config(BaseModel, extra=Extra.forbid):
    general: General = General.default()
    network: Optional[NetConfig] = None
    environment: EnvConfig = EnvConfig.default()
    agents: Dict[str, AgentConfig] = {}


def convert_old(old):
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

    network = {'group': 'network'}


    if 'network_params' in old and old['network_params']:
        for (k, v) in old['network_params'].items():
            if k == 'path':
                network['path'] = v
            else:
                network.setdefault('params', {})[k] = v

    if 'topology' in old:
        network['topology'] = old['topology']

    agents = {
        'environment': {
            'fixed': []
        },
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
        agents['environment']['fixed'].append(updated_agent(agent))

    for agent in old.get('network_agents', []):
        agents['network'].setdefault('distribution', []).append(updated_agent(agent))

    environment = {'params': {}}
    if 'environment_class' in old:
        environment['environment_class'] = old['environment_class']

    for (k, v) in old.get('environment_params', {}).items():
        environment['params'][k] = v


    return Config(general=general,
                  network=network,
                  environment=environment,
                  agents=agents)
