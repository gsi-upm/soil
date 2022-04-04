from mesa import DataCollector as MDC

class SoilDataCollector(MDC):


    def __init__(self, environment, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate model and env reporters so they have a key per 
        # So they can be shown in the web interface
        self.environment = environment
        raise NotImplementedError()

    @property
    def model_vars(self):
        raise NotImplementedError()

    @model_vars.setter
    def model_vars(self, value):
        raise NotImplementedError()

    @property
    def agent_reporters(self):
        raise NotImplementedError()

