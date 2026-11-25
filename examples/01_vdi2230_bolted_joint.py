"""Deterministic VDI 2230 Blatt 1 / ABNT NBR 8800 bolted joint calculator.

Adapted from Chapter 10 of *Everyday Agentic Engineering with Google Antigravity*.
Computes maximum permissible assembly preload (FM_max), nominal tightening torque (MA),
and combined tensile + torsional Von Mises equivalent stress during tightening.
Educational/prototyping reference only; verify independently with a licensed engineer before production use.
"""
from __future__ import annotations

import math

ISO_METRIC_BOLTS: dict[str, dict[str, float]] = {
    "M16": {"d": 16.0, "p": 2.00, "d2": 14.701, "as_mm2": 157.0, "dw": 22.5, "dh": 17.5},
    "M20": {"d": 20.0, "p": 2.50, "d2": 18.376, "as_mm2": 245.0, "dw": 28.2, "dh": 22.0},
    "M24": {"d": 24.0, "p": 3.00, "d2": 22.051, "as_mm2": 353.0, "dw": 33.6, "dh": 26.0},
    "M30": {"d": 30.0, "p": 3.50, "d2": 27.727, "as_mm2": 561.0, "dw": 42.8, "dh": 33.0},
}

STRENGTH_CLASSES: dict[str, dict[str, float]] = {
    "8.8": {"f_yb_MPa": 640.0, "f_ub_MPa": 800.0},
    "10.9": {"f_yb_MPa": 900.0, "f_ub_MPa": 1000.0},
    "12.9": {"f_yb_MPa": 1080.0, "f_ub_MPa": 1200.0},
}


def calculate_vdi2230_joint_torque(
    size: str,
    strength_class: str = "10.9",
    yield_utilization: float = 0.80,
    mu_thread: float = 0.12,
    mu_bearing: float = 0.12,
    tightening_factor_alpha_a: float = 1.4,
) -> dict[str, float | str]:
    """Calculate nominal assembly preload, torque, and Von Mises tightening stress."""
    if size not in ISO_METRIC_BOLTS or strength_class not in STRENGTH_CLASSES:
        raise ValueError(f"Unsupported bolt size '{size}' or class '{strength_class}'.")
    if not (0.1 <= yield_utilization <= 0.95):
        raise ValueError("yield_utilization must stay within [0.10, 0.95] per VDI 2230.")

    geo = ISO_METRIC_BOLTS[size]
    prop = STRENGTH_CLASSES[strength_class]
    a_s = geo["as_mm2"]
    f_yb = prop["f_yb_MPa"]

    # 1. Axial assembly preload [N] for the requested axial yield ratio
    fm_max_n = yield_utilization * f_yb * a_s

    # 2. Thread and under-head friction lever arms [mm -> m]
    d_km = (geo["dw"] + geo["dh"]) / 2.0
    thread_arm_mm = 0.16 * geo["p"] + 0.58 * geo["d2"] * mu_thread
    head_arm_mm = (d_km / 2.0) * mu_bearing
    torque_nm = fm_max_n * (thread_arm_mm + head_arm_mm) * 1e-3

    # 3. Combined tensile + torsional Von Mises stress (VDI 2230 Step R7)
    w_p = (math.pi / 16.0) * (geo["d2"] ** 3)
    thread_torque_nmm = fm_max_n * thread_arm_mm
    tau_mpa = thread_torque_nmm / w_p
    sigma_t_mpa = fm_max_n / a_s
    sigma_vm_mpa = math.sqrt(sigma_t_mpa**2 + 3.0 * (tau_mpa**2))

    # VDI 2230 R7 permissible preload keeping combined Von Mises <= 0.90 * f_yb
    torsion_derate = sigma_t_mpa / sigma_vm_mpa
    fm_vdi_r7_kn = (0.90 * f_yb * a_s * torsion_derate) * 1e-3
    fm_min_required_kn = (fm_max_n / tightening_factor_alpha_a) * 1e-3

    return {
        "size": size,
        "class": strength_class,
        "preload_fm_max_kN": round(fm_max_n * 1e-3, 2),
        "preload_fm_min_kN": round(fm_min_required_kn, 2),
        "vdi2230_r7_allowable_fm_kN": round(fm_vdi_r7_kn, 2),
        "torque_ma_Nm": round(torque_nm, 1),
        "tensile_stress_MPa": round(sigma_t_mpa, 1),
        "von_mises_stress_MPa": round(sigma_vm_mpa, 1),
        "yield_limit_MPa": f_yb,
        "tightening_factor_alpha_a": tightening_factor_alpha_a,
        "status": "SAFE" if sigma_vm_mpa <= f_yb else "YIELD_RISK_ON_TIGHTENING",
    }


# Portuguese alias matching book listing signature
calcular_torque_junta_vdi2230 = calculate_vdi2230_joint_torque


def main() -> None:
    print("=== VDI 2230 Blatt 1 / NBR 8800 Bolted Joint Audit (mu_G = mu_K = 0.12) ===")
    for bolt in ("M16", "M20", "M24", "M30"):
        res = calculate_vdi2230_joint_torque(bolt, strength_class="10.9")
        print(
            f"{res['size']} cl.{res['class']} | FM_max={res['preload_fm_max_kN']:6.2f} kN | "
            f"MA={res['torque_ma_Nm']:6.1f} N.m | sigma_vM={res['von_mises_stress_MPa']:5.1f} MPa "
            f"(<= {res['yield_limit_MPa']:.0f} MPa) -> {res['status']}"
        )


if __name__ == "__main__":
    main()
