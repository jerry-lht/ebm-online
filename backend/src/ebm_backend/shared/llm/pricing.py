"""Model pricing configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    input_per_1m: float
    output_per_1m: float
    batch_discount: float = 1.0


PRICING: dict[str, ModelPricing] = {
    "gpt-5.2": ModelPricing(input_per_1m=2.0, output_per_1m=8.0, batch_discount=0.5),
    "gpt-5.2-mini": ModelPricing(input_per_1m=0.4, output_per_1m=1.6, batch_discount=0.5),
    "gpt-4o": ModelPricing(input_per_1m=5.0, output_per_1m=15.0, batch_discount=0.5),
}


def calculate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    is_batch: bool = False,
) -> float:
    pricing = PRICING.get(model, PRICING["gpt-5.2"])
    discount = pricing.batch_discount if is_batch else 1.0
    cost = (
        prompt_tokens / 1_000_000 * pricing.input_per_1m
        + completion_tokens / 1_000_000 * pricing.output_per_1m
    )
    return round(cost * discount, 8)
