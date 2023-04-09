from soil import Environment, Simulation, CounterModel

class TorvaldsEnv(Environment):

  def init(self):
    self.create_network(path='torvalds.edgelist')
    self.populate_network(CounterModel, skill_level='beginner')
    print("Agentes: ", list(self.network_agents))
    self.find_one(node_id="Torvalds").skill_level = 'God'
    self.find_one(node_id="balkian").skill_level = 'developer'


sim = Simulation(name='torvalds_example',
                 max_steps=10,
                 interval=2,
                 model=TorvaldsEnv)