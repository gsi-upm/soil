from __future__ import annotations

import pdb
import sys
import os

from textwrap import indent
from functools import wraps

from .agents import FSM, MetaFSM


def wrapcmd(func):
    @wraps(func)
    def wrapper(self, arg: str, temporary=False):
        sys.settrace(self.trace_dispatch)

        known = globals()
        known.update(self.curframe.f_globals)
        known.update(self.curframe.f_locals)
        known['agent'] = known.get('self', None)
        known['model'] = known.get('self', {}).get('model')
        known['attrs'] = arg.strip().split()

        exec(func.__code__, known, known)

    return wrapper


class Debug(pdb.Pdb):
    def __init__(self, *args, skip_soil=False, **kwargs):
        skip = kwargs.get('skip', [])
        if skip_soil:
            skip.append('soil.*')
            skip.append('mesa.*')
        super(Debug, self).__init__(*args, skip=skip, **kwargs)
        self.prompt = "[soil-pdb] "

    @staticmethod
    def _soil_agents(model, attrs=None, pretty=True, **kwargs):
        for agent in model.agents(**kwargs):
            d = agent
            print(' - ' + indent(agent.to_str(keys=attrs, pretty=pretty), '  '))

    @wrapcmd
    def do_soil_agents():
        return Debug._soil_agents(model, attrs=attrs or None)

    do_sa = do_soil_agents

    @wrapcmd
    def do_soil_list():
        return Debug._soil_agents(model, attrs=['state_id'], pretty=False)

    do_sl = do_soil_list

    @wrapcmd
    def do_soil_self():
        if not agent:
            print('No agent available')
            return

        keys = None
        if attrs:
            keys = []
            for k in attrs:
                for key in agent.keys():
                    if key.startswith(k):
                        keys.append(key)

        print(agent.to_str(pretty=True, keys=keys))

    do_ss = do_soil_self

    def do_break_state(self, arg: str, temporary=False):
        '''
        Break before a specified state is stepped into.
        '''

        klass = None
        state = arg.strip()
        if not state:
            self.error("Specify at least a state name")
            return

        comma = arg.find(':')
        if comma > 0:
            state = arg[comma+1:].lstrip()
            klass = arg[:comma].rstrip()
            klass = eval(klass,
                         self.curframe.f_globals,
                         self.curframe_locals)

        if klass:
            klasses = [klass]
        else:
            klasses = [k for k in self.curframe.f_globals.values() if isinstance(k, type) and issubclass(k, FSM)]
            print(klasses)
            if not klasses:
                self.error('No agent classes found')
        
        for klass in klasses:
            try:
                func = getattr(klass, state)
            except AttributeError:
                continue
            if hasattr(func, '__func__'):
                func = func.__func__

            code = func.__code__
            #use co_name to identify the bkpt (function names
            #could be aliased, but co_name is invariant)
            funcname = code.co_name
            lineno = code.co_firstlineno
            filename = code.co_filename

            # Check for reasonable breakpoint
            line = self.checkline(filename, lineno)
            if not line:
                raise ValueError('no line found')
                # now set the break point
            cond = None
            existing = self.get_breaks(filename, line)
            if existing:
                self.message("Breakpoint already exists at %s:%d" %
                              (filename, line))
                continue
            err = self.set_break(filename, line, temporary, cond, funcname)
            if err:
                self.error(err)
            else:
                bp = self.get_breaks(filename, line)[-1]
                self.message("Breakpoint %d at %s:%d" %
                              (bp.number, bp.file, bp.line))
    do_bs = do_break_state


def setup(frame=None):
    debugger = Debug()
    frame = frame or sys._getframe().f_back
    debugger.set_trace(frame)

def debug_env():
    if os.environ.get('SOIL_DEBUG'):
        return setup(frame=sys._getframe().f_back)

def post_mortem(traceback=None):
    p = Debug()
    t = sys.exc_info()[2]
    p.reset()
    p.interaction(None, t)
