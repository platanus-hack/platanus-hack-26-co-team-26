"""Verifica que cada vector dorado sobreviva un round-trip de parseo+reserializado
byte a byte en Python. No prueba el lado Kotlin (eso corre en Gradle, ver
core/src/androidUnitTest/kotlin/co/helius/core/protocol/BundleGoldenVectorTest.kt)
pero sí confirma que el fixture es válido y estable antes de comparar contra él.

Uso: python3 protocol/test-vectors/verify_python_roundtrip.py
"""
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "shared", "src", "api", "protocol"))

from helius.v1 import bundle_pb2  # noqa: E402


def main() -> int:
    bundles_dir = os.path.join(os.path.dirname(__file__), "bundles")
    bin_files = sorted(glob.glob(os.path.join(bundles_dir, "*.bin")))
    if not bin_files:
        print("ERROR: no se encontraron vectores dorados en", bundles_dir)
        return 1

    failures = []
    for path in bin_files:
        name = os.path.basename(path)
        with open(path, "rb") as f:
            original = f.read()

        bundle = bundle_pb2.Bundle()
        bundle.ParseFromString(original)
        roundtripped = bundle.SerializeToString()

        if roundtripped == original:
            print(f"OK   {name} ({len(original)} bytes)")
        else:
            print(f"FAIL {name}: round-trip no coincide byte a byte "
                  f"({len(original)} -> {len(roundtripped)} bytes)")
            failures.append(name)

    if failures:
        print(f"\n{len(failures)}/{len(bin_files)} vectores fallaron el round-trip")
        return 1

    print(f"\n{len(bin_files)}/{len(bin_files)} vectores OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
