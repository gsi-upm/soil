from soil import Simulation
from social_wealth import MoneyEnv, graph_generator

sim = Simulation(name="mesa_sim", dump=False, max_steps=10, interval=2, model=MoneyEnv, model_params=dict(generator=graph_generator, N=10, width=50, height=50))

if __name__ == "__main__":
    sim.run()
