import numpy as np
from . import FSM, state


class SISaModel(FSM):
    """
    Settings:
        neutral_discontent_spon_prob

        neutral_discontent_infected_prob

        neutral_content_spon_prob

        neutral_content_infected_prob

        discontent_neutral

        discontent_content

        variance_d_c

        content_discontent

        variance_c_d

        content_neutral

        standard_variance
    """

    def __init__(self, environment, unique_id=0, state=()):
        super().__init__(model=environment, unique_id=unique_id, state=state)

        random = np.random.default_rng(seed=self._seed)

        self.neutral_discontent_spon_prob = random.normal(
            self.env["neutral_discontent_spon_prob"], self.env["standard_variance"]
        )
        self.neutral_discontent_infected_prob = random.normal(
            self.env["neutral_discontent_infected_prob"], self.env["standard_variance"]
        )
        self.neutral_content_spon_prob = random.normal(
            self.env["neutral_content_spon_prob"], self.env["standard_variance"]
        )
        self.neutral_content_infected_prob = random.normal(
            self.env["neutral_content_infected_prob"], self.env["standard_variance"]
        )

        self.discontent_neutral = random.normal(
            self.env["discontent_neutral"], self.env["standard_variance"]
        )
        self.discontent_content = random.normal(
            self.env["discontent_content"], self.env["variance_d_c"]
        )

        self.content_discontent = random.normal(
            self.env["content_discontent"], self.env["variance_c_d"]
        )
        self.content_neutral = random.normal(
            self.env["content_neutral"], self.env["standard_variance"]
        )

    @state
    def neutral(self):
        # Spontaneous effects
        if self.prob(self.neutral_discontent_spon_prob):
            return self.discontent
        if self.prob(self.neutral_content_spon_prob):
            return self.content

        # Infected
        discontent_neighbors = self.count_neighbors(state_id=self.discontent)
        if self.prob(scontent_neighbors * self.neutral_discontent_infected_prob):
            return self.discontent
        content_neighbors = self.count_neighbors(state_id=self.content.id)
        if self.prob(s * self.neutral_content_infected_prob):
            return self.content
        return self.neutral

    @state
    def discontent(self):
        # Healing
        if self.prob(self.discontent_neutral):
            return self.neutral

        # Superinfected
        content_neighbors = self.count_neighbors(state_id=self.content.id)
        if self.prob(s * self.discontent_content):
            return self.content
        return self.discontent

    @state
    def content(self):
        # Healing
        if self.prob(self.content_neutral):
            return self.neutral

        # Superinfected
        discontent_neighbors = self.count_neighbors(state_id=self.discontent.id)
        if self.prob(scontent_neighbors * self.content_discontent):
            self.discontent
        return self.content
