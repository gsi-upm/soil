from mesa import DataCollector as MDC


class SoilCollector(MDC):
    def __init__(self, model_reporters=None, agent_reporters=None, tables=None, **kwargs):
        model_reporters = model_reporters or {}
        agent_reporters = agent_reporters or {}
        tables = tables or {}
        if 'agent_count' not in model_reporters:
            model_reporters['agent_count'] = lambda m: m.schedule.get_agent_count()
        if 'time' not in model_reporters:
            model_reporters['time'] = lambda m: m.schedule.time
        # if 'state_id' not in agent_reporters:
        #     agent_reporters['state_id'] = lambda agent: getattr(agent, 'state_id', None)

        super().__init__(model_reporters=model_reporters,
                         agent_reporters=agent_reporters,
                         tables=tables,
                         **kwargs)
