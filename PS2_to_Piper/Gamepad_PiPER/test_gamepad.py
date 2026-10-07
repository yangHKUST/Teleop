#!/usr/bin/env python3
"""Live gamepad tester: press buttons / move sticks and see their index.

Run:
    ~/miniconda3/envs/piper/bin/python test_gamepad.py
"""
import time
import pygame

# Xbox 360 (xpad) button names, index -> name
BUTTON_NAMES = {
    0: "A", 1: "B", 2: "X", 3: "Y",
    4: "LB", 5: "RB", 6: "Back", 7: "Start",
    8: "Guide(中间大圆键/Home)", 9: "L3(左摇杆按下)", 10: "R3(右摇杆按下)",
}
AXIS_NAMES = {
    0: "左摇杆X", 1: "左摇杆Y", 2: "LT(左扳机)",
    3: "右摇杆X", 4: "右摇杆Y", 5: "RT(右扳机)",
}

pygame.init()
pygame.joystick.init()

count = pygame.joystick.get_count()
print(f"检测到 {count} 个手柄")
if count == 0:
    print("没有手柄！请检查接收器/手柄电源。")
    raise SystemExit(1)

j = pygame.joystick.Joystick(0)
j.init()
print(f"已绑定: {j.get_name()}  buttons={j.get_numbuttons()} axes={j.get_numaxes()}")
print("逐个按按键 / 推摇杆，会实时打印编号；Ctrl+C 退出。\n")

while True:
    pygame.event.pump()
    pressed = [i for i in range(j.get_numbuttons()) if j.get_button(i)]
    if pressed:
        names = [f"{i}={BUTTON_NAMES.get(i, '?')}" for i in pressed]
        print("按键按下:", ", ".join(names))

    axes = [(i, round(j.get_axis(i), 2)) for i in range(j.get_numaxes()) if abs(j.get_axis(i)) > 0.1]
    if axes:
        desc = ", ".join(f"{i}={AXIS_NAMES.get(i, '?')}:{v}" for i, v in axes)
        print("摇杆/扳机:", desc)

    hats = j.get_numhats()
    for h in range(hats):
        hv = j.get_hat(h)
        if hv != (0, 0):
            print(f"方向键(D-pad): {hv}")

    time.sleep(0.08)
