"""Reproducible legacy/improved comparison; only kinematics, no hardware.
The fixture is a pre-change snapshot and must not be used for control.
"""
import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path
import time
import numpy as np
HERE = Path(__file__).resolve().parent
CORE = HERE.parent
sys.path.insert(0, str(CORE))
from openarm_urdf_ik import OpenArmDecoupledIk, _exp_so3, _so3_log
from openarm_umi_core import default_home_q
spec = importlib.util.spec_from_file_location('legacy_ik', HERE/'fixtures/legacy_openarm_ik.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)

def run(side, mode, output):
    home = default_home_q(side)
    k = (legacy.OpenArmDecoupledIk(urdf_path=str(CORE/'urdf/openarm_bimanual.urdf'), side=side)
         if mode == 'legacy' else OpenArmDecoupledIk(side=side))
    if mode != 'legacy':
        k.reset(home)
        k.set_posture(home, [1,1,1,0.5,0.3,0.3,0.3], speed=0.15 if mode=='posture' else 0)
    initial = k.fk(home)
    q = home.copy()
    rows = []
    durations = []
    # stationary startup, two smooth outbound/return cycles, stationary end
    phases = np.r_[np.zeros(20), np.linspace(0,4*np.pi,301), np.zeros(20)]
    for tick, phase in enumerate(phases):
        target = initial.copy()
        target.translation += [0.04*np.sin(phase),0.01*(1-np.cos(phase)),0.02*np.sin(phase)]
        target.rotation = target.rotation @ _exp_so3(np.array([0.08,0.12,0.04])*np.sin(phase))
        start = time.perf_counter()
        if mode == 'legacy':
            # Reproduce production probe call followed by command solve.
            k.ik6d(target)
            result, ok, _ = k.ik6d(target)
        else:
            k.ik6d(target, q_seed=q, commit=False)
            result, ok, _ = k.track_step(target, q_seed=q, max_delta=np.radians(30)*0.02)
        durations.append((time.perf_counter()-start)*1000)
        if mode != 'legacy' and not ok:
            result = q.copy()
        elif mode != 'legacy':
            k.reset(result)
        actual = k.fk(result)
        rows.append([tick, bool(ok), np.linalg.norm(actual.translation-target.translation),
                     np.linalg.norm(_so3_log(actual.rotation.T@target.rotation)),
                     np.max(np.abs(result-q)), np.linalg.norm(result-home),
                     *result.tolist()])
        q = result
    with (output/f'{side}_{mode}.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['tick','solver_ok','position_error_m','orientation_error_rad',
                                  'max_joint_delta_rad','distance_home_rad']+[f'q{i}_rad' for i in range(1,8)]);w.writerows(rows)
    arr=np.array(rows,dtype=float)
    joints=arr[:,6:]
    velocity = np.diff(np.vstack([home, joints]), axis=0) / 0.02
    acceleration = np.diff(velocity, axis=0) / 0.02
    return dict(max_command_acceleration_rad_s2=float(np.max(np.abs(acceleration))), accepted_fraction=float(np.mean(arr[:,1])), max_position_error_mm=float(np.max(arr[:,2])*1000),
                max_orientation_error_deg=float(np.degrees(np.max(arr[:,3]))),
                max_joint_step_deg=float(np.degrees(np.max(arr[:,4]))),
                total_joint_travel_deg=float(np.degrees(np.sum(np.abs(np.diff(np.vstack([home,joints]),axis=0))))),
                return_max_joint_error_deg=float(np.degrees(np.max(np.abs(q-home)))),
                solve_pair_p95_ms=float(np.percentile(durations,95)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('/tmp/openarm_ik_comparison'))
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    summary={f'{side}_{mode}':run(side,mode,args.output) for side in ['left','right'] for mode in ['legacy','off','posture']}
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
