import numpy as np
from hashlib import sha512
from . import Agent, state, default_state


class SISaModel(Agent):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        seed = self.model._seed
        if isinstance(seed, (str, bytes, bytearray)):
            if isinstance(seed, str):
                seed = seed.encode()
            seed = int.from_bytes(seed + sha512(seed).digest(), 'big')

        random = np.random.default_rng(seed=seed)

        self.neutral_discontent_spon_prob = random.normal(
            self.model.neutral_discontent_spon_prob, self.model.standard_variance
        )
        self.neutral_discontent_infected_prob = random.normal(
            self.model.neutral_discontent_infected_prob, self.model.standard_variance
        )
        self.neutral_content_spon_prob = random.normal(
            self.model.neutral_content_spon_prob, self.model.standard_variance
        )
        self.neutral_content_infected_prob = random.normal(
            self.model.neutral_content_infected_prob, self.model.standard_variance
        )

        self.discontent_neutral = random.normal(
            self.model.discontent_neutral, self.model.standard_variance
        )
        self.discontent_content = random.normal(
            self.model.discontent_content, self.model.variance_d_c
        )

        self.content_discontent = random.normal(
            self.model.content_discontent, self.model.variance_c_d
        )
        self.content_neutral = random.normal(
            self.model.discontent_neutral, self.model.standard_variance
        )

    @default_state
    @state
    def neutral(self):
        # Spontaneous effects
        if self.prob(self.neutral_discontent_spon_prob):
            return self.discontent
        if self.prob(self.neutral_content_spon_prob):
            return self.content

        # Infected
        discontent_neighbors = self.count_neighbors(state_id=self.discontent)
        if self.prob(discontent_neighbors * self.neutral_discontent_infected_prob):
            return self.discontent
        content_neighbors = self.count_neighbors(state_id=self.content.id)
        if self.prob(content_neighbors * self.neutral_content_infected_prob):
            return self.content
        return self.neutral

    @state
    def discontent(self):
        # Healing
        if self.prob(self.discontent_neutral):
            return self.neutral

        # Superinfected
        content_neighbors = self.count_neighbors(state_id=self.content.id)
        if self.prob(content_neighbors * self.discontent_content):
            return self.content
        return self.discontent

    @state
    def content(self):
        # Healing
        if self.prob(self.content_neutral):
            return self.neutral

        # Superinfected
        discontent_neighbors = self.count_neighbors(state_id=self.discontent.id)
        if self.prob(discontent_neighbors * self.content_discontent):
            self.discontent
        return self.content
