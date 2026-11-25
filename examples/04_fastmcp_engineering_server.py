"""FastMCP engineering server exposing deterministic ABNT NBR 8800 I/W section properties.

Adapted from Chapter 6 of *Everyday Agentic Engineering with Google Antigravity*.
Runs cleanly in standalone `--demo` / test mode even when `fastmcp` is not installed.
When executed without `--demo` and `fastmcp` is installed, starts the stdio MCP server.
Educational/prototyping reference only; verify independently with a licensed engineer before production use.
"""
from __future__ import annotations

import argparse
import math

try:
    from fastmcp import FastMCP
except ImportError:  # pragma: no cover - optional runtime dependency for live MCP transport
    FastMCP = None


def compute_w_section_inertia(
    d_mm: float,
    bf_mm: float,
    tw_mm: float,
    tf_mm: float,
    steel_density_kg_m3: float = 7850.0,
) -> dict[str, float]:
    """Compute geometric section properties for a symmetric I / W steel profile (NBR 8800).

    Args:
        d_mm: Overall depth [mm].
        bf_mm: Flange width [mm].
        tw_mm: Web thickness [mm].
        tf_mm: Flange thickness [mm].
        steel_density_kg_m3: Steel volumetric density [kg/m^3].
    """
    if min(d_mm, bf_mm, tw_mm, tf_mm) <= 0 or 2 * tf_mm >= d_mm or tw_mm >= bf_mm:
        raise ValueError("Invalid structural I/W profile dimensions.")

    area_flange_mm2 = bf_mm * tf_mm
    web_height_mm = d_mm - 2.0 * tf_mm
    area_web_mm2 = web_height_mm * tw_mm
    total_area_mm2 = 2.0 * area_flange_mm2 + area_web_mm2

    # Strong axis (X-X) second moment of area [cm^4]
    ix_web_mm4 = (tw_mm * (web_height_mm**3)) / 12.0
    flange_centroid_mm = (d_mm - tf_mm) / 2.0
    ix_flanges_mm4 = 2.0 * (
        ((bf_mm * (tf_mm**3)) / 12.0) + area_flange_mm2 * (flange_centroid_mm**2)
    )
    ix_cm4 = (ix_web_mm4 + ix_flanges_mm4) * 1e-4

    # Weak axis (Y-Y) second moment of area [cm^4]
    iy_web_mm4 = (web_height_mm * (tw_mm**3)) / 12.0
    iy_flanges_mm4 = 2.0 * ((tf_mm * (bf_mm**3)) / 12.0)
    iy_cm4 = (iy_web_mm4 + iy_flanges_mm4) * 1e-4

    # Radii of gyration [cm]
    rx_cm = math.sqrt((ix_cm4 * 1e4) / total_area_mm2) * 0.1
    ry_cm = math.sqrt((iy_cm4 * 1e4) / total_area_mm2) * 0.1

    return {
        "area_cm2": round(total_area_mm2 * 0.01, 2),
        "mass_kg_m": round((total_area_mm2 * 1e-6) * steel_density_kg_m3, 2),
        "ix_cm4": round(ix_cm4, 2),
        "iy_cm4": round(iy_cm4, 2),
        "rx_cm": round(rx_cm, 2),
        "ry_cm": round(ry_cm, 2),
    }


calcular_momento_inercia_perfil_w = compute_w_section_inertia

if FastMCP is not None:  # pragma: no branch
    mcp = FastMCP("Industrial-Engineering-Core")
    mcp.tool()(compute_w_section_inertia)


def main() -> None:
    parser = argparse.ArgumentParser(description="FastMCP NBR 8800 W-Profile Engineering Tool")
    parser.add_argument("--demo", action="store_true", help="Run local verification on W 200x46.1")
    args = parser.parse_args()

    if args.demo or FastMCP is None:
        # W 200 x 46.1 nominal dimensions: d=203 mm, bf=203 mm, tw=7.2 mm, tf=11.0 mm
        props = compute_w_section_inertia(d_mm=203.0, bf_mm=203.0, tw_mm=7.2, tf_mm=11.0)
        print("W 200x46.1 (NBR 8800, without root fillets):", props)
        if not args.demo and FastMCP is None:
            print("Note: install `fastmcp` (`pip install fastmcp`) to expose via MCP stdio.")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
