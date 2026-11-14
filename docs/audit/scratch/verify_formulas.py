"""Verificación de WACC y dilución."""

from __future__ import annotations

# WACC vector
rf = 0.0425
beta = 1.1
erp = 0.05
ke = rf + beta * erp
kd = 0.05
tax = 0.21
kd_after = kd * (1 - tax)
equity = 3000.0
debt = 1000.0
wacc = (equity / (equity + debt)) * ke + (debt / (equity + debt)) * kd_after
print(f"Ke = {ke:.4f} (expected 0.0975)")
print(f"Kd after tax = {kd_after:.4f} (expected 0.0395)")
print(f"WACC = {wacc:.4f} (expected 0.0830)")

# Treasury stock
basic = 100.0
options = 10.0
exercise = 20.0
rsus = 4.0
price = 50.0
option_dilution = options * (1 - exercise / price) if exercise < price else 0.0
diluted = basic + option_dilution + rsus
print(f"\nDiluted shares = {diluted} (expected 110.0)")

# With price 15 (out of the money)
price2 = 15.0
option_dilution2 = options * (1 - exercise / price2) if exercise < price2 else 0.0
diluted2 = basic + option_dilution2 + rsus
print(f"Diluted shares (price 15) = {diluted2} (expected 104.0)")

# Beneish identical years
dsri = 1.0
gmi = 1.0
aqi = 1.0
sgi = 1.0
depi = 1.0
sgai = 1.0
lvgi = 1.0
tata = 0.0
m = -4.84 + 0.920*dsri + 0.528*gmi + 0.404*aqi + 0.892*sgi + 0.115*depi - 0.172*sgai + 4.679*tata - 0.327*lvgi
print(f"\nBeneish M (identical) = {m:.4f} (expected -2.48)")

# Altman Z'
x1, x2, x3, x4, x5 = 0.2, 0.3, 0.1, 0.5, 1.0
z_prime = 0.717*x1 + 0.847*x2 + 3.107*x3 + 0.420*x4 + 0.998*x5
print(f"Altman Z' = {z_prime:.4f} (expected 1.916)")

# Altman Z''
z_double = 6.56*0.2 + 3.26*0.3 + 6.72*0.1 + 1.05*0.5
print(f"Altman Z'' = {z_double:.4f} (expected 3.487)")

# Piotroski all improving
print("\nPiotroski: all improving -> 9, all declining -> 0")