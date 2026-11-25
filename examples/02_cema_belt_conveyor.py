"""Deterministic CEMA 7th Edition / DIN 22101 belt conveyor & drive pulley shaft sizing.

Adapted from Chapter 11 of *Everyday Agentic Engineering with Google Antigravity*.
Computes effective tension (Te), tight/slack tensions (T1/T2) via Euler-Eytelwein,
motor shaft power, minimum pulley diameter, and shaft sizing per ASME B106.1M.
Educational/prototyping reference only; verify independently with a licensed engineer before production use.
"""
from __future__ import annotations

import math


def size_cema_belt_conveyor(
    capacity_tph: float,
    length_m: float,
    lift_m: float,
    speed_m_s: float = 2.5,
    wrap_angle_deg: float = 210.0,
    mu_pulley: float = 0.38,
    ambient_temp_c: float = 25.0,
    drive_efficiency: float = 0.92,
) -> dict[str, float]:
    """Size effective tension Te, T1/T2 belt tensions, motor kW, and drum diameter."""
    g = 9.80665
    if capacity_tph <= 0 or length_m <= 0 or speed_m_s <= 0:
        raise ValueError("capacity_tph, length_m, and speed_m_s must be positive.")

    # 1. Material linear mass [kg/m] and weight [N/m]
    mass_flow_kg_s = (capacity_tph * 1e3) / 3600.0
    material_mass_kg_m = mass_flow_kg_s / speed_m_s
    w_m = material_mass_kg_m * g

    # CEMA reference for 36" (900 mm) belt with C6 (6-inch) carrying idlers
    belt_mass_kg_m = 18.5
    w_b = belt_mass_kg_m * g
    a_i = 1.5

    # 2. CEMA correction factors
    k_t = 1.0 if ambient_temp_c >= 0.0 else 1.0 + 0.01 * abs(ambient_temp_c)
    k_y = 0.022
    k_x = 0.00068 * (w_b + w_m) + a_i

    # 3. Effective tension Te [N]
    empty_belt_term = k_x + k_y * w_b + 0.015 * w_b
    loaded_term = w_m * (length_m * k_y + lift_m)
    t_accessories_n = 2500.0
    t_e_n = (length_m * k_t * empty_belt_term) + loaded_term + t_accessories_n

    # 4. Euler-Eytelwein belt wrap equilibrium
    theta_rad = math.radians(wrap_angle_deg)
    euler_factor = math.exp(mu_pulley * theta_rad)
    t_c_n = belt_mass_kg_m * (speed_m_s**2)
    t_2_n = (t_e_n / (euler_factor - 1.0)) + t_c_n
    t_1_n = t_e_n + t_2_n

    # 5. Required power [kW] and DIN 22101 minimum drum diameter [mm]
    shaft_power_kw = (t_e_n * speed_m_s) * 1e-3
    motor_power_kw = shaft_power_kw / drive_efficiency
    min_pulley_mm = max(400.0, math.sqrt(t_1_n) * 1.8)

    return {
        "capacity_tph": capacity_tph,
        "effective_tension_Te_kN": round(t_e_n * 1e-3, 2),
        "tight_side_T1_kN": round(t_1_n * 1e-3, 2),
        "slack_side_T2_kN": round(t_2_n * 1e-3, 2),
        "shaft_power_kW": round(shaft_power_kw, 2),
        "motor_power_kW": round(motor_power_kw, 1),
        "min_pulley_diameter_mm": round(min_pulley_mm, 0),
    }


def size_drive_pulley_shaft(
    t1_kn: float,
    t2_kn: float,
    bearing_moment_arm_mm: float,
    power_kw: float,
    speed_rpm: float,
    yield_strength_mpa: float = 380.0,
    safety_factor: float = 2.0,
) -> dict[str, float | int | str]:
    """Calculate minimum drive pulley shaft diameter under combined bending and torsion."""
    resultant_n = (t1_kn + t2_kn) * 1e3
    mb_nmm = (resultant_n / 2.0) * bearing_moment_arm_mm

    omega_rad_s = (2.0 * math.pi * speed_rpm) / 60.0
    mt_nmm = ((power_kw * 1e3) / omega_rad_s) * 1e3

    meq_nmm = math.sqrt(mb_nmm**2 + mt_nmm**2)
    allowable_stress_mpa = yield_strength_mpa / safety_factor
    min_diameter_mm = ((32.0 * meq_nmm) / (math.pi * allowable_stress_mpa)) ** (1.0 / 3.0)

    standard_bores = [80, 90, 100, 110, 120, 140, 160, 180, 200]
    commercial_bore = next((d for d in standard_bores if d >= min_diameter_mm), 220)

    return {
        "bending_moment_kNm": round(mb_nmm * 1e-6, 2),
        "torsional_moment_kNm": round(mt_nmm * 1e-6, 2),
        "min_theoretical_diameter_mm": round(min_diameter_mm, 1),
        "commercial_bearing_bore_mm": commercial_bore,
        "recommended_bearing": f"SKF 222{commercial_bore // 5} EK + Adapter Sleeve H",
    }


dimensionar_transportador_cema_completo = size_cema_belt_conveyor
dimensionar_eixo_tambor = size_drive_pulley_shaft


def main() -> None:
    print("=== CEMA 7th Ed. / DIN 22101 Conveyor Sizing Demo (1200 t/h, L=450 m, H=28 m) ===")
    conv = size_cema_belt_conveyor(capacity_tph=1200.0, length_m=450.0, lift_m=28.0)
    shaft = size_drive_pulley_shaft(
        t1_kn=conv["tight_side_T1_kN"],
        t2_kn=conv["slack_side_T2_kN"],
        bearing_moment_arm_mm=320.0,
        power_kw=conv["motor_power_kW"],
        speed_rpm=42.0,
    )
    print("Conveyor:", conv)
    print("Drive Shaft:", shaft)


if __name__ == "__main__":
    main()
