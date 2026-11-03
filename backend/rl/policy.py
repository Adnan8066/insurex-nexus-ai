"""Permutation-equivariant actor-critic policy for claim routing.

Every agent slot is scored by the same small network from the claim features
plus that agent's four features, and the scores are the action logits. This
matches the task's structure (the best employee does not depend on slot
order), so one model works for any team size up to ``MAX_AGENTS``.
"""

from __future__ import annotations

import torch
from stable_baselines3.common.policies import ActorCriticPolicy
from torch import nn

from .environment import MAX_AGENTS


CLAIM_FEATURES = 3
AGENT_FEATURES = 4
# Large enough that padded or unavailable slots are effectively never sampled.
UNAVAILABLE_LOGIT_PENALTY = 20.0


class AgentScorer(nn.Module):
    """SB3 ``mlp_extractor``: per-agent logits for the actor, pooled latent for the critic."""

    def __init__(self, hidden: int = 64) -> None:
        super().__init__()
        self.latent_dim_pi = MAX_AGENTS
        self.latent_dim_vf = hidden
        pair_features = CLAIM_FEATURES + AGENT_FEATURES
        self.actor = nn.Sequential(
            nn.Linear(pair_features, hidden), nn.Tanh(),
            nn.Linear(hidden, hidden), nn.Tanh(),
            nn.Linear(hidden, 1),
        )
        self.agent_encoder = nn.Sequential(nn.Linear(pair_features, hidden), nn.Tanh())
        self.critic = nn.Sequential(nn.Linear(hidden + CLAIM_FEATURES, hidden), nn.Tanh())

    @staticmethod
    def _split(features: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        claim = features[:, :CLAIM_FEATURES]
        agents = features[:, CLAIM_FEATURES:].reshape(-1, MAX_AGENTS, AGENT_FEATURES)
        pairs = torch.cat([claim.unsqueeze(1).expand(-1, MAX_AGENTS, -1), agents], dim=-1)
        return claim, agents, pairs

    def forward_actor(self, features: torch.Tensor) -> torch.Tensor:
        _claim, agents, pairs = self._split(features)
        available = agents[..., 3]
        return self.actor(pairs).squeeze(-1) - UNAVAILABLE_LOGIT_PENALTY * (1.0 - available)

    def forward_critic(self, features: torch.Tensor) -> torch.Tensor:
        claim, agents, pairs = self._split(features)
        available = agents[..., 3:4]
        encoded = self.agent_encoder(pairs) * available
        pooled = encoded.sum(dim=1) / available.sum(dim=1).clamp(min=1.0)
        return self.critic(torch.cat([pooled, claim], dim=-1))

    def forward(self, features: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        return self.forward_actor(features), self.forward_critic(features)


class AgentScoringPolicy(ActorCriticPolicy):
    """PPO policy whose action logits are the per-agent scores."""

    def _build_mlp_extractor(self) -> None:
        self.mlp_extractor = AgentScorer()

    def _build(self, lr_schedule) -> None:
        super()._build(lr_schedule)
        # A dense layer here would mix slots and break order independence.
        self.action_net = nn.Identity()
        self.optimizer = self.optimizer_class(
            self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs
        )
