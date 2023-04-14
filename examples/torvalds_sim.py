from soil import Environment, Simulation, CounterModel, report


# Get directory path for current file
import os, sys, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

class TorvaldsEnv(Environment):

  def init(self):
    self.create_network(path=os.path.join(currentdir, 'torvalds.edgelist'))
    self.populate_network(CounterModel, skill_level='beginner')
    self.agent(node_id="Torvalds").skill_level = 'God'
    self.agent(node_id="balkian").skill_level = 'developer'
    self.add_agent_reporter("times")

  @report
  def god_developers(self):
    return self.count_agents(skill_level='God')
  

sim = Simulation(name='torvalds_example',
                 max_steps=10,
                 interval=2,
                 model=TorvaldsEnv)