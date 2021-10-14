from mesa import DataCollector as MDC

class SoilDataCollector(MDC):


    def __init__(self, environment, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate model and env reporters so they have a key per 
        # So they can be shown in the web interface
        self.environment = environment


    @property
    def model_vars(self):
        pass

    @model_vars.setter
    def model_vars(self, value):
        pass

    @property
    def agent_reporters(self):
        self.model._history._

        pass

