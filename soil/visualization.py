from mesa.visualization.UserParam import UserSettableParameter

class UserSettableParameter(UserSettableParameter):
    def __str__(self):
        return self.value
