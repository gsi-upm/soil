import solara

@solara.component
def MainPage(clicks):
    color = "green"
    if clicks.value >= 5:
        color = "red"

    def increment():
        clicks.value += 1
        print("clicks", clicks)  # noqa

    solara.Button(label=f"Clicked: {clicks}", on_click=increment, color=color)

@solara.component
def Page():
    v = Visualization()
    v.viz()

class Visualization:
    def __init__(self):
        self.clicks = solara.reactive(0)

    def viz(self):
        from sol_lib import MainPage
        return MainPage(self.clicks)
