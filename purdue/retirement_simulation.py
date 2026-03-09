#!/usr/bin/env python3
"""Retirement balance simulator for Purdue faculty contribution structures."""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass


@dataclass
class Inputs:
    age: int
    retirement_age: int
    salary: float
    current_balance: float
    salary_growth: float
    expected_return: float
    volatility: float
    mandatory_401a: float
    employer_base: float
    voluntary_rates: list[float]
    simulations: int
    seed: int


def simulate_deterministic(inputs: Inputs, voluntary_rate: float) -> float:
    years = inputs.retirement_age - inputs.age
    salary = inputs.salary
    balance = inputs.current_balance
    total_rate = inputs.employer_base + inputs.mandatory_401a + voluntary_rate

    for _ in range(years):
        balance *= 1.0 + inputs.expected_return
        balance += salary * total_rate
        salary *= 1.0 + inputs.salary_growth

    return balance


def simulate_monte_carlo(inputs: Inputs, voluntary_rate: float) -> tuple[float, float, float]:
    years = inputs.retirement_age - inputs.age
    total_rate = inputs.employer_base + inputs.mandatory_401a + voluntary_rate
    outcomes = []

    for _ in range(inputs.simulations):
        salary = inputs.salary
        balance = inputs.current_balance

        for _ in range(years):
            annual_return = random.gauss(inputs.expected_return, inputs.volatility)
            annual_return = max(-0.95, annual_return)
            balance *= 1.0 + annual_return
            balance += salary * total_rate
            salary *= 1.0 + inputs.salary_growth

        outcomes.append(balance)

    outcomes.sort()
    return (
        percentile(outcomes, 10),
        percentile(outcomes, 50),
        percentile(outcomes, 90),
    )


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return math.nan
    idx = (len(sorted_values) - 1) * p / 100.0
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return sorted_values[lo]
    weight = idx - lo
    return sorted_values[lo] * (1.0 - weight) + sorted_values[hi] * weight


def fmt_money(value: float) -> str:
    return f"${value:,.0f}"


def parse_args() -> Inputs:
    parser = argparse.ArgumentParser(
        description=(
            "Project retirement balances for Purdue faculty-style contributions "
            "(10% employer base + 4% mandatory 401(a) + voluntary savings)."
        )
    )
    parser.add_argument("--age", type=int, default=40)
    parser.add_argument("--retirement-age", type=int, default=67)
    parser.add_argument("--salary", type=float, default=120000)
    parser.add_argument("--current-balance", type=float, default=0)
    parser.add_argument("--salary-growth", type=float, default=0.03)
    parser.add_argument("--expected-return", type=float, default=0.065)
    parser.add_argument("--volatility", type=float, default=0.15)
    parser.add_argument("--mandatory-401a", type=float, default=0.04)
    parser.add_argument("--employer-base", type=float, default=0.10)
    parser.add_argument("--voluntary-rates", default="0.04,0.06")
    parser.add_argument("--simulations", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    voluntary_rates = [float(x.strip()) for x in args.voluntary_rates.split(",") if x.strip()]
    if args.retirement_age <= args.age:
        raise ValueError("--retirement-age must be greater than --age")
    if not voluntary_rates:
        raise ValueError("--voluntary-rates must contain at least one rate")

    return Inputs(
        age=args.age,
        retirement_age=args.retirement_age,
        salary=args.salary,
        current_balance=args.current_balance,
        salary_growth=args.salary_growth,
        expected_return=args.expected_return,
        volatility=args.volatility,
        mandatory_401a=args.mandatory_401a,
        employer_base=args.employer_base,
        voluntary_rates=voluntary_rates,
        simulations=args.simulations,
        seed=args.seed,
    )


def main() -> None:
    inputs = parse_args()
    random.seed(inputs.seed)
    years = inputs.retirement_age - inputs.age

    print("Retirement Simulation")
    print(
        f"Assumptions: age {inputs.age} -> {inputs.retirement_age} ({years} years), "
        f"salary {fmt_money(inputs.salary)}, salary growth {inputs.salary_growth:.1%}, "
        f"return mean {inputs.expected_return:.1%}, volatility {inputs.volatility:.1%}, "
        f"current balance {fmt_money(inputs.current_balance)}"
    )
    print(
        f"Fixed rates: employer {inputs.employer_base:.1%} + mandatory 401(a) {inputs.mandatory_401a:.1%}"
    )
    print("")
    print(
        "Voluntary  Total Save  Deterministic Balance  MC P10         MC P50         MC P90         4% Income (P50)"
    )

    for voluntary_rate in inputs.voluntary_rates:
        deterministic = simulate_deterministic(inputs, voluntary_rate)
        p10, p50, p90 = simulate_monte_carlo(inputs, voluntary_rate)
        total_rate = inputs.employer_base + inputs.mandatory_401a + voluntary_rate
        income_p50 = p50 * 0.04
        print(
            f"{voluntary_rate:8.1%}  {total_rate:10.1%}  "
            f"{fmt_money(deterministic):21}  {fmt_money(p10):12}  "
            f"{fmt_money(p50):12}  {fmt_money(p90):12}  {fmt_money(income_p50):>15}/yr"
        )


if __name__ == "__main__":
    main()
