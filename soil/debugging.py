from __future__ import annotations

import pdb
import sys
import os

from textwrap import indent
from functools import wraps

from .agents import FSM, MetaFSM
from mesa import Model, Agent


def wrapcmd(func):
    @wraps(func)
    def wrapper(self, arg: str, temporary=False):
        sys.settrace(self.trace_dispatch)

        lastself = self
        known = globals()
        known.update(self.curframe.f_globals)
        known.update(self.curframe.f_locals)
        known["attrs"] = arg.strip().split()

        this = known.get("self", None)

        if isinstance(this, Model):
            known["model"] = this
        elif isinstance(this, Agent):
            known["agent"] = this
            known["model"] = this.model

        known["self"] = lastself
        return exec(func.__code__, known, known)

    return wrapper


class Debug(pdb.Pdb):
    def __init__(self, *args, skip_soil=False, **kwargs):
        skip = kwargs.get("skip", [])
        if skip_soil:
            skip.append("soil")
            skip.append("contextlib")
            skip.append("soil.*")
            skip.append("mesa.*")
        super(Debug, self).__init__(*args, skip=skip, **kwargs)
        self.prompt = "[soil-pdb] "

    @staticmethod
    def _soil_agents(model, attrs=None, pretty=True, **kwargs):
        for agent in model.get_agents(**kwargs):
            d = agent
            print(" - " + indent(agent.to_str(keys=attrs, pretty=pretty), "  "))

    @wrapcmd
    def do_soil_agents():
        return Debug._soil_agents(model, attrs=attrs or None)

    do_sa = do_soil_agents

    @wrapcmd
    def do_soil_list():
        return Debug._soil_agents(model, attrs=["state_id"], pretty=False)

    do_sl = do_soil_list

    def do_continue_state(self, arg):
        """Continue until next time this state is reached"""
        self.do_break_state(arg, temporary=True)
        return self.do_continue("")

    do_cs = do_continue_state

    @wrapcmd
    def do_soil_agent():
        if not agent:
            print("No agent available")
            return

        keys = None
        if attrs:
            keys = []
            for k in attrs:
                for key in agent.keys():
                    if key.startswith(k):
                        keys.append(key)

        print(agent.to_str(pretty=True, keys=keys))

    do_aa = do_soil_agent

    def do_break_step(self, arg: str):
        """
        Break before the next step.
        """
        try:
            known = globals()
            known.update(self.curframe.f_globals)
            known.update(self.curframe.f_locals)
            func = getattr(known["model"], "step")
        except AttributeError as ex:
            self.error(f"The model does not have a step function: {ex}")
            return
        if hasattr(func, "__func__"):
            func = func.__func__

        code = func.__code__
        # use co_name to identify the bkpt (function names
        # could be aliased, but co_name is invariant)
        funcname = code.co_name
        lineno = code.co_firstlineno
        filename = code.co_filename

        # Check for reasonable breakpoint
        line = self.checkline(filename, lineno)
        if not line:
            raise ValueError("no line found")
            # now set the break point

        existing = self.get_breaks(filename, line)
        if existing:
            self.message("Breakpoint already exists at %s:%d" % (filename, line))
            return
        cond = f"self.schedule.steps > {model.schedule.steps}"
        err = self.set_break(filename, line, True, cond, funcname)
        if err:
            self.error(err)
        else:
            bp = self.get_breaks(filename, line)[-1]
            self.message("Breakpoint %d at %s:%d" % (bp.number, bp.file, bp.line))
            return self.do_continue("")
    
    do_bstep = do_break_step

    def do_break_state(self, arg: str, instances=None, temporary=False):
        """
        Break before a specified state is stepped into.
        """

        klass = None
        state = arg
        if not state:
            self.error("Specify at least a state name")
            return

        state, *tokens = state.lstrip().split()
        if tokens:
            instances = list(eval(token) for token in tokens)

        colon = state.find(":")

        if colon > 0:
            klass = state[:colon].rstrip()
            state = state[colon + 1 :].strip()

            print(klass, state, tokens)
            klass = eval(klass, self.curframe.f_globals, self.curframe_locals)

        if klass:
            klasses = [klass]
        else:
            klasses = [
                k
                for k in self.curframe.f_globals.values()
                if isinstance(k, type) and issubclass(k, FSM)
            ]

        if not klasses:
            self.error("No agent classes found")

        for klass in klasses:
            try:
                func = getattr(klass, state)
            except AttributeError:
                self.error(f"State {state} not found in class {klass}")
                continue
            if hasattr(func, "__func__"):
                func = func.__func__

            code = func.__code__
            # use co_name to identify the bkpt (function names
            # could be aliased, but co_name is invariant)
            funcname = code.co_name
            lineno = code.co_firstlineno
            filename = code.co_filename

            # Check for reasonable breakpoint
            line = self.checkline(filename, lineno)
            if not line:
                raise ValueError("no line found")
                # now set the break point
            cond = None
            if instances:
                cond = f"self.unique_id in { repr(instances) }"

            existing = self.get_breaks(filename, line)
            if existing:
                self.message("Breakpoint already exists at %s:%d" % (filename, line))
                continue
            err = self.set_break(filename, line, temporary, cond, funcname)
            if err:
                self.error(err)
            else:
                bp = self.get_breaks(filename, line)[-1]
                self.message("Breakpoint %d at %s:%d" % (bp.number, bp.file, bp.line))

    do_bs = do_break_state

    def do_break_state_self(self, arg: str, temporary=False):
        """
        Break before a specified state is stepped into, for the current agent
        """
        agent = self.curframe.f_locals.get("self")
        if not agent:
            self.error("No current agent.")
            self.error("Try this again when the debugger is stopped inside an agent")
            return

        arg = f"{agent.__class__.__name__}:{ arg } {agent.unique_id}"
        return self.do_break_state(arg)

    do_bss = do_break_state_self


debugger = None


def set_trace(frame=None, **kwargs):
    global debugger
    if debugger is None:
        debugger = Debug(**kwargs)
    frame = frame or sys._getframe().f_back
    debugger.set_trace(frame)


def post_mortem(traceback=None, **kwargs):
    global debugger
    if debugger is None:
        debugger = Debug(**kwargs)
    t = sys.exc_info()[2]
    debugger.reset()
    debugger.interaction(None, t)
