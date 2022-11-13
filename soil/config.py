from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, ValidationError, validator, root_validator

import yaml
import os
import sys


from typing import Any, Callable, Dict, List, Optional, Union, Type
from pydantic import BaseModel, Extra

from . import environment, utils

import networkx as nx


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


class NetConfig(BaseModel):
    params: Optional[Dict[str, Any]]
    fixed: Optional[Union[Topology, nx.Graph]]
    path: Optional[str]

    class Config:
        arbitrary_types_allowed = True

    @staticmethod
    def default():
        return NetConfig(topology=None, params=None)

    @root_validator
    def validate_all(cls, values):
        if "params" not in values and "topology" not in values:
            raise ValueError(
                "You must specify either a topology or the parameters to generate a graph"
            )
        return values


class EnvConfig(BaseModel):
    @staticmethod
    def default():
        return EnvConfig()


class SingleAgentConfig(BaseModel):
    agent_class: Optional[Union[Type, str]] = None
    unique_id: Optional[int] = None
    topology: Optional[bool] = False
    node_id: Optional[Union[int, str]] = None
    state: Optional[Dict[str, Any]] = {}


class FixedAgentConfig(SingleAgentConfig):
    n: Optional[int] = 1
    hidden: Optional[bool] = False  # Do not count this agent towards total agent count

    @root_validator
    def validate_all(cls, values):
        if values.get("unique_id", None) is not None and values.get("n", 1) > 1:
            raise ValueError(
                f"An unique_id can only be provided when there is only one agent ({values.get('n')} given)"
            )
        return values


class OverrideAgentConfig(FixedAgentConfig):
    filter: Optional[Dict[str, Any]] = None


class Strategy(Enum):
    topology = "topology"
    total = "total"


class AgentDistro(SingleAgentConfig):
    weight: Optional[float] = 1
    strategy: Strategy = Strategy.topology


class AgentConfig(SingleAgentConfig):
    n: Optional[int] = None
    distribution: Optional[List[AgentDistro]] = None
    fixed: Optional[List[FixedAgentConfig]] = None
    override: Optional[List[OverrideAgentConfig]] = None

    @staticmethod
    def default():
        return AgentConfig()

    @root_validator
    def validate_all(cls, values):
        if "distribution" in values and (
            "n" not in values and "topology" not in values
        ):
            raise ValueError(
                "You need to provide the number of agents or a topology to extract the value from."
            )
        return values


class Config(BaseModel, extra=Extra.allow):
    version: Optional[str] = "1"

    name: str = "Unnamed Simulation"
    description: Optional[str] = None
    group: str = None
    dir_path: Optional[str] = None
    num_trials: int = 1
    max_time: float = 100
    max_steps: int = -1
    num_processes: int = 1
    interval: float = 1
    seed: str = ""
    dry_run: bool = False
    skip_test: bool = False

    model_class: Union[Type, str] = environment.Environment
    model_params: Optional[Dict[str, Any]] = {}

    visualization_params: Optional[Dict[str, Any]] = {}

    @classmethod
    def from_raw(cls, cfg):
        if isinstance(cfg, Config):
            return cfg
        if cfg.get("version", "1") == "1" and any(
            k in cfg for k in ["agents", "agent_class", "topology", "environment_class"]
        ):
            return convert_old(cfg)
        return Config(**cfg)


def convert_old(old, strict=True):
    """
    Try to convert old style configs into the new format.

    This is still a work in progress and might not work in many cases.
    """

    utils.logger.warning(
        "The old configuration format is deprecated. The converted file MAY NOT yield the right results"
    )

    new = old.copy()

    network = {}

    if "topology" in old:
        del new["topology"]
        network["topology"] = old["topology"]

    if "network_params" in old and old["network_params"]:
        del new["network_params"]
        for (k, v) in old["network_params"].items():
            if k == "path":
                network["path"] = v
            else:
                network.setdefault("params", {})[k] = v

    topology = None
    if network:
        topology = network

    agents = {"fixed": [], "distribution": []}

    def updated_agent(agent):
        """Convert an agent definition"""
        newagent = dict(agent)
        return newagent

    by_weight = []
    fixed = []
    override = []

    if "environment_agents" in new:

        for agent in new["environment_agents"]:
            agent.setdefault("state", {})["group"] = "environment"
            if "agent_id" in agent:
                agent["state"]["name"] = agent["agent_id"]
                del agent["agent_id"]
            agent["hidden"] = True
            agent["topology"] = False
            fixed.append(updated_agent(agent))
        del new["environment_agents"]

    if "agent_class" in old:
        del new["agent_class"]
        agents["agent_class"] = old["agent_class"]

    if "default_state" in old:
        del new["default_state"]
        agents["state"] = old["default_state"]

    if "network_agents" in old:
        agents["topology"] = True

        agents.setdefault("state", {})["group"] = "network"

        for agent in new["network_agents"]:
            agent = updated_agent(agent)
            if "agent_id" in agent:
                agent["state"]["name"] = agent["agent_id"]
                del agent["agent_id"]
                fixed.append(agent)
            else:
                by_weight.append(agent)
        del new["network_agents"]

    if "agent_class" in old and (not fixed and not by_weight):
        agents["topology"] = True
        by_weight = [{"agent_class": old["agent_class"], "weight": 1}]

    # TODO: translate states properly
    if "states" in old:
        del new["states"]
        states = old["states"]
        if isinstance(states, dict):
            states = states.items()
        else:
            states = enumerate(states)
        for (k, v) in states:
            override.append({"filter": {"node_id": k}, "state": v})

    agents["override"] = override
    agents["fixed"] = fixed
    agents["distribution"] = by_weight

    model_params = {}
    if "environment_params" in new:
        del new["environment_params"]
        model_params = dict(old["environment_params"])

    if "environment_class" in old:
        del new["environment_class"]
        new["model_class"] = old["environment_class"]

    if "dump" in old:
        del new["dump"]
        new["dry_run"] = not old["dump"]

    model_params["topology"] = topology
    model_params["agents"] = agents

    return Config(version="2", model_params=model_params, **new)
