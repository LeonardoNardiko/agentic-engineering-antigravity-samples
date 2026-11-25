"""Industrial serial binary frame encoder/decoder with CRC-16 Modbus validation.

Adapted from Chapter 7 of *Everyday Agentic Engineering with Google Antigravity*.
Demonstrates deterministic binary protocol reverse engineering and CRC-16 (0xA001) integrity checks.
Educational/prototyping reference only; verify independently with a licensed engineer before production use.
"""
from __future__ import annotations

import struct


def compute_crc16_modbus(payload: bytes) -> int:
    """Compute standard Modbus RTU CRC-16 (poly 0xA001, init 0xFFFF)."""
    crc = 0xFFFF
    for byte in payload:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def encode_telemetry_frame(device_id: int, pressure_bar: float, temperature_c: float) -> bytes:
    """Pack [0xAA55 header 2B][device_id 1B][pressure float 4B][temp*10 int16 2B][CRC-16 BE 2B]."""
    if not (0 <= device_id <= 255):
        raise ValueError("device_id must fit in 1 unsigned byte (0..255).")
    temp_tenths = int(round(temperature_c * 10.0))
    body = struct.pack(">HBfh", 0xAA55, device_id, pressure_bar, temp_tenths)
    crc = compute_crc16_modbus(body)
    return body + struct.pack(">H", crc)


def decode_telemetry_frame(frame: bytes, strict_crc: bool = False) -> dict[str, int | float | bool]:
    """Unpack and verify an 11-byte industrial binary telemetry frame."""
    if len(frame) < 11:
        raise ValueError(f"[PROTOCOL ERROR] Incomplete frame ({len(frame)} bytes, expected >= 11).")

    header, device_id = struct.unpack(">HB", frame[:3])
    if header != 0xAA55:
        raise ValueError(f"[SYNC ERROR] Invalid header: 0x{header:04X}")

    pressure_bar, temp_raw = struct.unpack(">fh", frame[3:9])
    (received_crc,) = struct.unpack(">H", frame[9:11])
    computed_crc = compute_crc16_modbus(frame[:9])
    crc_ok = received_crc == computed_crc

    if strict_crc and not crc_ok:
        raise ValueError(
            f"[CRC MISMATCH] received=0x{received_crc:04X}, expected=0x{computed_crc:04X}"
        )

    return {
        "device_id": device_id,
        "pressure_bar": round(pressure_bar, 3),
        "temperature_C": round(temp_raw * 0.1, 1),
        "received_crc": received_crc,
        "computed_crc": computed_crc,
        "crc_ok": crc_ok,
    }


calcular_crc16_modbus = compute_crc16_modbus
decodificar_quadro_telemetria = decode_telemetry_frame


def main() -> None:
    pkt = encode_telemetry_frame(device_id=7, pressure_bar=6.425, temperature_c=74.8)
    print(f"Encoded 11-byte frame (hex): {pkt.hex(' ').upper()}")
    decoded = decode_telemetry_frame(pkt)
    print("Valid decode:", decoded)

    corrupted = bytearray(pkt)
    corrupted[5] ^= 0x01  # flip 1 bit in payload
    bad = decode_telemetry_frame(bytes(corrupted), strict_crc=False)
    print("Single-bit corruption check:", bad)


if __name__ == "__main__":
    main()
