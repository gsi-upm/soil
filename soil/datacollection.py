from mesa import DataCollector as MDC


class SoilCollector(MDC):
    def __init__(self, model_reporters=None, agent_reporters=None, tables=None, **kwargs):
        model_reporters = model_reporters or {}
        agent_reporters = agent_reporters or {}
        tables = tables or {}
        if 'agent_count' not in model_reporters:
            model_reporters['agent_count'] = lambda m: m.schedule.get_agent_count()
        if 'state_id' not in agent_reporters:
            agent_reporters['agent_id'] = lambda agent: agent.get('state_id', None)

        super().__init__(model_reporters=model_reporters,
                         agent_reporters=agent_reporters,
                         tables=tables,
                         **kwargs)
