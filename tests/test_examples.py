"""Unit tests for deterministic engineering samples (Zero-Rework verification)."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _load(filename: str):
    path = EXAMPLES_DIR / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = mod
    spec.loader.exec_module(mod)
    return mod


vdi = _load("01_vdi2230_bolted_joint.py")
cema = _load("02_cema_belt_conveyor.py")
modbus = _load("03_modbus_crc16_telemetry.py")
fastmcp_srv = _load("04_fastmcp_engineering_server.py")


class EngineeringSamplesTests(unittest.TestCase):
    def test_vdi2230_von_mises_exceeds_pure_tension_and_catches_torsion_yield(self):
        safe_res = vdi.calculate_vdi2230_joint_torque("M16", "10.9", yield_utilization=0.80)
        self.assertGreater(safe_res["von_mises_stress_MPa"], safe_res["tensile_stress_MPa"])
        self.assertLessEqual(safe_res["von_mises_stress_MPa"], safe_res["yield_limit_MPa"])
        self.assertEqual(safe_res["status"], "SAFE")

        # At 0.90 axial yield with mu=0.12, combined torsion pushes Von Mises past 900 MPa
        over_res = vdi.calculate_vdi2230_joint_torque("M16", "10.9", yield_utilization=0.90)
        self.assertGreater(over_res["von_mises_stress_MPa"], over_res["yield_limit_MPa"])
        self.assertEqual(over_res["status"], "YIELD_RISK_ON_TIGHTENING")
        self.assertLess(over_res["vdi2230_r7_allowable_fm_kN"], over_res["preload_fm_max_kN"])

    def test_cema_tension_balance_and_efficiency(self):
        conv = cema.size_cema_belt_conveyor(capacity_tph=1000.0, length_m=300.0, lift_m=20.0)
        self.assertAlmostEqual(
            conv["tight_side_T1_kN"],
            conv["effective_tension_Te_kN"] + conv["slack_side_T2_kN"],
            delta=0.05,
        )
        self.assertGreater(conv["motor_power_kW"], conv["shaft_power_kW"])
        self.assertGreaterEqual(conv["min_pulley_diameter_mm"], 400.0)
        shaft = cema.size_drive_pulley_shaft(
            conv["tight_side_T1_kN"], conv["slack_side_T2_kN"], 300.0, conv["motor_power_kW"], 45.0
        )
        self.assertGreaterEqual(shaft["commercial_bearing_bore_mm"], shaft["min_theoretical_diameter_mm"])

    def test_modbus_crc16_standard_vector_and_corruption_detection(self):
        self.assertEqual(modbus.compute_crc16_modbus(b"123456789"), 0x4B37)
        pkt = modbus.encode_telemetry_frame(device_id=12, pressure_bar=8.5, temperature_c=62.3)
        ok = modbus.decode_telemetry_frame(pkt, strict_crc=True)
        self.assertTrue(ok["crc_ok"])
        self.assertAlmostEqual(ok["pressure_bar"], 8.5, places=3)
        self.assertAlmostEqual(ok["temperature_C"], 62.3, places=1)

        corrupted = bytearray(pkt)
        corrupted[4] ^= 0x80
        bad = modbus.decode_telemetry_frame(bytes(corrupted), strict_crc=False)
        self.assertFalse(bad["crc_ok"])
        with self.assertRaises(ValueError):
            modbus.decode_telemetry_frame(bytes(corrupted), strict_crc=True)

    def test_fastmcp_w200x46_section_properties(self):
        props = fastmcp_srv.compute_w_section_inertia(d_mm=203.0, bf_mm=203.0, tw_mm=7.2, tf_mm=11.0)
        self.assertAlmostEqual(props["area_cm2"], 57.69, delta=0.5)
        self.assertAlmostEqual(props["ix_cm4"], 4476.16, delta=5.0)
        self.assertGreater(props["ix_cm4"], props["iy_cm4"])
        self.assertGreater(props["rx_cm"], props["ry_cm"])


if __name__ == "__main__":
    unittest.main()
