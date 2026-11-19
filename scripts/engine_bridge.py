"""JSON over standard input/output for the .NET host. No HTTP or persistence."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    payload = json.load(sys.stdin)
    if payload.get('operation') == 'verify_legacy_password':
        from werkzeug.security import check_password_hash
        print(json.dumps({'valid': check_password_hash(payload['hash'], payload['password'])}))
        return
    from flood.simulator import Scenario, simulate
    from flood.territory import load_territory
    _, arrays, _ = load_territory(Path(__file__).resolve().parents[1] / 'data/pilot-v1')
    result = simulate(arrays['elevation_m'], arrays['infiltration_mmh'], Scenario.from_dict(payload['scenario']))
    for key in ('maximum_mm', 'final_mm', 'index'):
        result[key] = result[key].tolist()
    print(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main()
