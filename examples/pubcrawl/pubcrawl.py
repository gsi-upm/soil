from soil.agents import FSM, NetworkAgent, state, default_state
from soil import Environment
from itertools import islice
import logging


class CityPubs(Environment):
    """Environment with Pubs"""

    level = logging.INFO

    def __init__(self, *args, number_of_pubs=3, pub_capacity=10, **kwargs):
        super(CityPubs, self).__init__(*args, **kwargs)
        pubs = {}
        for i in range(number_of_pubs):
            newpub = {
                "name": "The awesome pub #{}".format(i),
                "open": True,
                "capacity": pub_capacity,
                "occupancy": 0,
            }
            pubs[newpub["name"]] = newpub
        self["pubs"] = pubs

    def enter(self, pub_id, *nodes):
        """Agents will try to enter. The pub checks if it is possible"""
        try:
            pub = self["pubs"][pub_id]
        except KeyError:
            raise ValueError("Pub {} is not available".format(pub_id))
        if not pub["open"] or (pub["capacity"] < (len(nodes) + pub["occupancy"])):
            return False
        pub["occupancy"] += len(nodes)
        for node in nodes:
            node["pub"] = pub_id
        return True

    def available_pubs(self):
        for pub in self["pubs"].values():
            if pub["open"] and (pub["occupancy"] < pub["capacity"]):
                yield pub["name"]

    def exit(self, pub_id, *node_ids):
        """Agents will notify the pub they want to leave"""
        try:
            pub = self["pubs"][pub_id]
        except KeyError:
            raise ValueError("Pub {} is not available".format(pub_id))
        for node_id in node_ids:
            node = self.get_agent(node_id)
            if pub_id == node["pub"]:
                del node["pub"]
                pub["occupancy"] -= 1


class Patron(FSM, NetworkAgent):
    """Agent that looks for friends to drink with. It will do three things:
    1) Look for other patrons to drink with
    2) Look for a bar where the agent and other agents in the same group can get in.
    3) While in the bar, patrons only drink, until they get drunk and taken home.
    """

    level = logging.DEBUG

    pub = None
    drunk = False
    pints = 0
    max_pints = 3
    kicked_out = False

    @default_state
    @state
    def looking_for_friends(self):
        """Look for friends to drink with"""
        self.info("I am looking for friends")
        available_friends = list(
            self.get_agents(drunk=False, pub=None, state_id=self.looking_for_friends.id)
        )
        if not available_friends:
            self.info("Life sucks and I'm alone!")
            return self.at_home
        befriended = self.try_friends(available_friends)
        if befriended:
            return self.looking_for_pub

    @state
    def looking_for_pub(self):
        """Look for a pub that accepts me and my friends"""
        if self["pub"] != None:
            return self.sober_in_pub
        self.debug("I am looking for a pub")
        group = list(self.get_neighbors())
        for pub in self.model.available_pubs():
            self.debug("We're trying to get into {}: total: {}".format(pub, len(group)))
            if self.model.enter(pub, self, *group):
                self.info("We're all {} getting in {}!".format(len(group), pub))
                return self.sober_in_pub

    @state
    def sober_in_pub(self):
        """Drink up."""
        self.drink()
        if self["pints"] > self["max_pints"]:
            return self.drunk_in_pub

    @state
    def drunk_in_pub(self):
        """I'm out. Take me home!"""
        self.info("I'm so drunk. Take me home!")
        self["drunk"] = True
        if self.kicked_out:
            return self.at_home
        pass  # out drun

    @state
    def at_home(self):
        """The end"""
        others = self.get_agents(state_id=Patron.at_home.id, limit_neighbors=True)
        self.debug("I'm home. Just like {} of my friends".format(len(others)))

    def drink(self):
        self["pints"] += 1
        self.debug("Cheers to that")

    def kick_out(self):
        self.kicked_out = True

    def befriend(self, other_agent, force=False):
        """
        Try to become friends with another agent. The chances of
        success depend on both agents' openness.
        """
        if force or self["openness"] > self.random.random():
            self.add_edge(self, other_agent)
            self.info("Made some friend {}".format(other_agent))
            return True
        return False

    def try_friends(self, others):
        """Look for random agents around me and try to befriend them"""
        befriended = False
        k = int(10 * self["openness"])
        self.random.shuffle(others)
        for friend in islice(others, k):  # random.choice >= 3.7
            if friend == self:
                continue
            if friend.befriend(self):
                self.befriend(friend, force=True)
                self.debug("Hooray! new friend: {}".format(friend.id))
                befriended = True
            else:
                self.debug("{} does not want to be friends".format(friend.id))
        return befriended


class Police(FSM):
    """Simple agent to take drunk people out of pubs."""

    level = logging.INFO

    @default_state
    @state
    def patrol(self):
        drunksters = list(self.get_agents(drunk=True, state_id=Patron.drunk_in_pub.id))
        for drunk in drunksters:
            self.info("Kicking out the trash: {}".format(drunk.id))
            drunk.kick_out()
        else:
            self.info("No trash to take out. Too bad.")


if __name__ == "__main__":
    from soil import run_from_config

    run_from_config("pubcrawl.yml", dry_run=True, dump=None, parallel=False)
