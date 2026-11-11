#!/usr/bin/env python3
"""Battery life model of the ESP32-H2 Matter-over-Thread button (README, "Bảng tính thời lượng pin"), for the cell of
each board in hardware/: CR2450 (module-cr2450) and CR123A (module-cr123a). Same electronics and firmware on both.

Every parameter carries its source:
  [DS] datasheet value              (ESP32-H2 datasheet v1.3, TPS63900 SLVSET3D, Energizer/Panasonic cells)
  [ME] Espressif measurement        (esp-matter examples/icd_app/README.md current waveforms, ESP32-H2 DevKitC,
                                     20 dBm TX: LIT 20 s poll -> 46.6 uA avg, 26.7 uA floor over 160.3 s;
                                     SIT 5 s poll -> 88.5 uA avg, 27.0 uA floor over 20.0 s)
  [AS] assumption / estimate        -> replace with the values measured on the real board (README test plan)

Charges are at the 3.3 V rail (load side); the TPS63900 turns them into battery charge with
  Q_bat = Q_load * V_DD / (eta * V_BAT).

Usage:  python3 tools/battery_model.py                (README tables, every cell)
        python3 tools/battery_model.py --cell CR123A  (one cell)
        python3 tools/battery_model.py --breakdown     (where the average current goes, reference cases)
Edit the PARAMETERS block with your measurements and run again.
"""

import argparse

# ---------------------------------------------------------------------------------------------------- PARAMETERS
V_DD = 3.3            # [design] TPS63900 output, VO(2) = 3.3 V
ETA = 0.89            # [DS] TPS63900 efficiency, VO 3.3 V, VI 2.5..3.0 V, 10 uA..10 mA (Figure 8-7)
I_Q_CONV = 75e-9      # [DS] TPS63900 quiescent current into VIN (typ)
I_LEAK = 0.15e-6      # [AS] ADC pin (<= 50 nA [DS max]) + MLCC bulk capacitors + MOSFET, at 25 degC

# Cells of the boards: name -> (capacity mAh, usable fraction, mean voltage under load V, self-discharge per year,
# board, source tags). Usable fraction [AS]: the cell is "empty" for this design when it can no longer feed a 2 s
# re-attach RX (25 mA at 3.3 V = ~95 mW at the converter input, constant power) above the TPS63900 UVLO; short TX/RX
# bursts are bridged by the bulk capacitors much longer. TI SWRA349: 50-100 % of rated depending on the vendor.
CELLS = {
    # coin cell: R_int climbs to ~20 ohm well before the end (as the CR2032 of the former board: ~80 % usable)
    "CR2450": (620.0, 0.80, 2.85, 0.01, "module-cr2450", "[DS] Energizer CR2450 620 mAh, plateau ~2.9 V; [AS] usable"),
    # bobbin cell, pulse capable (R_int well under 1 ohm for most of its life): ~90 % usable
    "CR123A": (1500.0, 0.90, 2.90, 0.01, "module-cr123a", "[DS] Li-MnO2 1500 mAh class (Panasonic, Energizer); "
               "[AS] usable"),
}
CELL = "CR2450"       # the cell of the tables; --cell picks another one
CAP_MAH, USABLE, V_BAT, SELF_DISCHARGE = CELLS[CELL][:4]

I_SLEEP = 27e-6       # [ME] Light-sleep floor, peripherals + flash powered down (datasheet 25 uA typ [DS])

Q_POLL_20DBM = 0.35e-3  # [ME] one data poll incl. wake-up, 20 dBm (0.31..0.40 mC from the two waveforms)
TX_DELTA = 0.10e-3      # [AS] (140 - 36) mA [DS] x ~1 ms of TX per poll (34-byte secured Data Request at
                        #      250 kbit/s = 1.1 ms): 20 dBm -> 0 dBm
Q_POLL_0DBM = Q_POLL_20DBM - TX_DELTA

Q_REPORT = 0.6e-3     # [AS] one report exchange with one controller: encode + AES-CCM + 2 frames TX + ACKs + the
                      #      StatusResponse picked up at the next fast poll + standalone MRP ack
Q_BUTTON = 0.1e-3     # [AS] GPIO / debounce / window wake-ups of one gesture (Light-sleep in between)
T_GESTURE = 0.5       # [AS] s from the press to the last event of a single press (press + 350 ms window)
Q_MAINT_PER_H = 2.5e-3  # [AS] SRP lease renewal, MLE child updates, battery measurement, daily OTA query, per hour

Q_COMMISSION = 1.5    # [AS] C, one BLE commissioning + attach + CASE + subscriptions (once)
Q_REATTACH = 0.06     # [AS] C, one Thread re-attach (~2 s RX at 25 mA + CPU)

FAST_POLL = 0.2       # [cfg] CONFIG_ICD_FAST_POLL_INTERVAL_MS
IDLE_MODE = 3600.0    # [cfg] CONFIG_ICD_IDLE_MODE_INTERVAL_SEC = subscription max interval (keep-alive report)
ACTIVE_MODE = 1.0     # [cfg] CONFIG_ICD_ACTIVE_MODE_INTERVAL_MS

# ICD operating points: (name, slow poll s, ActiveModeThreshold s)
ICD_MODES = {
    "SIT 15 s": (15.0, 1.0),    # default build: every controller, Apple Home included
    "LIT 120 s": (120.0, 5.0),  # sdkconfig.defaults.lit, controllers that register a Check-In client
}
# Reports per gesture and per controller (Switch feature map): single press, MS|MSR|MSL|MSM:
# InitialPress, ShortRelease, MultiPressComplete -> up to 3 reports (events closer than one exchange share one)
REPORTS_PER_PRESS = 3   # [AS]

# Power sources compared, same firmware and electronics (README "Phương án"):
#   (name, capacity mAh, usable fraction, mean voltage under load V, self-discharge per year, source tags)
ALTERNATIVES = [
    ("CR2450 (bo module-cr2450)", *CELLS["CR2450"][:4], CELLS["CR2450"][5]),
    ("CR123A (bo module-cr123a)", *CELLS["CR123A"][:4], CELLS["CR123A"][5]),
    ("CR2032 (bo cũ, đã bỏ)", 220.0, 0.80, 2.85, 0.01, "[DS] Energizer/Panasonic, [AS] usable"),
    ("2 x AAA alkaline (không có bo)", 1150.0, 0.90, 2.50, 0.03,
     "[DS] ~1150 mAh/cell at low drain, [AS] usable to 0.85 V/cell"),
]
# ------------------------------------------------------------------------------------------------- END PARAMETERS


def use_cell(name):
    """Select the cell of the tables (module globals, as the PARAMETERS block)."""
    global CELL, CAP_MAH, USABLE, V_BAT, SELF_DISCHARGE
    CELL = name
    CAP_MAH, USABLE, V_BAT, SELF_DISCHARGE = CELLS[name][:4]


def bat_from_load(i_load, v_bat=None):
    """Battery current for a load current on the 3.3 V rail."""
    return i_load * V_DD / (ETA * (v_bat or V_BAT))


def average_load_current(mode, presses_per_day, controllers, q_poll=Q_POLL_0DBM):
    """Average current at the 3.3 V rail, split by cause (A)."""
    slow_poll, threshold = ICD_MODES[mode]
    tail_polls = lambda seconds: seconds / FAST_POLL
    parts = {}
    parts["light-sleep floor"] = I_SLEEP
    parts["slow polling"] = q_poll / slow_poll
    q_keepalive = controllers * Q_REPORT + tail_polls(ACTIVE_MODE + threshold) * q_poll
    parts["keep-alive reports"] = q_keepalive / IDLE_MODE
    parts["Thread/Matter maintenance"] = Q_MAINT_PER_H / 3600
    q_press = Q_BUTTON + controllers * REPORTS_PER_PRESS * Q_REPORT + tail_polls(T_GESTURE + threshold) * q_poll
    parts["button presses"] = presses_per_day * q_press / 86400
    return parts, q_press


def battery_current(parts, v_bat=None):
    return bat_from_load(sum(parts.values()), v_bat) + I_Q_CONV + I_LEAK


def life_months(i_bat, cap_mah=None, usable=None, self_discharge=None):
    cap_mah = cap_mah or CAP_MAH
    usable = usable or USABLE
    self_discharge = SELF_DISCHARGE if self_discharge is None else self_discharge
    usable_ah = cap_mah / 1000 * usable
    # Self-discharge as an extra constant drain
    hours = usable_ah / (i_bat + cap_mah / 1000 * self_discharge / 8760)
    return hours / 730.0


def table(controllers, q_poll=Q_POLL_0DBM, label="0 dBm"):
    rows = []
    header = "| Chế độ ICD | Bộ điều khiển | " + " | ".join(f"{n} lần/ngày" for n in (5, 20, 50, 100)) + " |"
    rows.append(header)
    rows.append("|---|---|" + "---|" * 4)
    for mode in ICD_MODES:
        cells = []
        for presses in (5, 20, 50, 100):
            parts, _ = average_load_current(mode, presses, controllers, q_poll)
            i_bat = battery_current(parts)
            cells.append(f"{i_bat * 1e6:.0f} µA → **{life_months(i_bat):.1f} tháng**")
        rows.append(f"| {mode} ({label}) | {controllers} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def states_table():
    """Charge and energy of each operating state (load side), and its cost in battery charge."""
    k = V_DD / (ETA * V_BAT)
    q_sit_press = average_load_current("SIT 15 s", 0, 1)[1]
    q_lit_press = average_load_current("LIT 120 s", 0, 1)[1]
    rows = [
        ("Light-sleep (sàn)", f"{I_SLEEP * 1e6:.0f} µA liên tục", I_SLEEP * 3600, "[ME] (datasheet 25 µA [DS])", "/giờ"),
        ("Data poll 0 dBm (1 lần)", "~5 ms thức + RX/TX", Q_POLL_0DBM, "[ME] 20 dBm − [AS] ΔTX", ""),
        ("Data poll 20 dBm (1 lần, để so sánh)", "", Q_POLL_20DBM, "[ME] esp-matter icd_app", ""),
        ("Đánh thức GPIO + debounce (1 cử chỉ)", "", Q_BUTTON, "[AS]", ""),
        ("Gửi 1 report sự kiện tới 1 controller", "", Q_REPORT, "[AS]", ""),
        ("1 lần nhấn đơn, SIT, 1 controller", "3 report + fast poll", q_sit_press, "tính từ các dòng trên", ""),
        ("1 lần nhấn đơn, LIT, 1 controller", "3 report + 5,5 s fast poll", q_lit_press, "tính từ các dòng trên", ""),
        ("Thread re-attach (1 lần)", "~2 s RX 25 mA + CPU", Q_REATTACH, "[AS]", ""),
        ("Commissioning BLE + Thread + CASE", "một lần", Q_COMMISSION, "[AS]", ""),
    ]
    out = ["| Trạng thái / sự kiện | Ghi chú | Điện tích tại 3,3 V | Năng lượng | Từ pin (µAh) | Nguồn số liệu |",
           "|---|---|---|---|---|---|"]
    for name, note, q, src, per in rows:
        q_txt = f"{q * 1e3:.2f} mC{per}" if q < 1 else f"{q:.2f} C{per}"
        e_mj = q * V_DD * 1e3
        e_txt = f"{e_mj:.2f} mJ{per}" if e_mj < 1000 else f"{e_mj / 1000:.1f} J{per}"
        uah = q * k / 3.6 * 1000
        out.append(f"| {name} | {note} | {q_txt} | {e_txt} | {uah:.2f}{per} | {src} |")
    return "\n".join(out)


def alternatives_table(presses=20, controllers=1):
    out = ["| Nguồn | Dung lượng | SIT 15 s | LIT 120 s | Nguồn số liệu |", "|---|---|---|---|---|"]
    for name, cap, usable, v_bat, sd, src in ALTERNATIVES:
        cells = []
        for mode in ICD_MODES:
            parts, _ = average_load_current(mode, presses, controllers)
            i_bat = battery_current(parts, v_bat)
            cells.append(f"{i_bat * 1e6:.0f} µA → **{life_months(i_bat, cap, usable, sd):.1f} tháng**")
        out.append(f"| {name} | {cap:.0f} mAh × {usable:.2f} | " + " | ".join(cells) + f" | {src} |")
    return "\n".join(out)


def floor_sensitivity(presses=20, controllers=1):
    """Life if only the Light-sleep floor changed (e.g. another SoC with the same radio costs)."""
    global I_SLEEP
    saved = I_SLEEP
    out = ["| Dòng sàn khi ngủ (tải) | SIT 15 s | LIT 120 s |", "|---|---|---|"]
    for floor in (27e-6, 15e-6, 5e-6, 2e-6):
        I_SLEEP = floor
        cells = []
        for mode in ICD_MODES:
            i_bat = battery_current(average_load_current(mode, presses, controllers)[0])
            cells.append(f"{i_bat * 1e6:.0f} µA → **{life_months(i_bat):.1f} tháng**")
        out.append(f"| {floor * 1e6:.0f} µA | " + " | ".join(cells) + " |")
    I_SLEEP = saved
    return "\n".join(out)


def breakdown(mode, presses, controllers, q_poll=Q_POLL_0DBM):
    parts, q_press = average_load_current(mode, presses, controllers, q_poll)
    total_load = sum(parts.values())
    print(f"\n{mode}, {presses} presses/day, {controllers} controller(s), poll {q_poll * 1e3:.2f} mC")
    for name, i in parts.items():
        print(f"  {name:28s} {i * 1e6:7.2f} uA  ({100 * i / total_load:4.1f} %)")
    i_bat = battery_current(parts)
    print(f"  {'load total (3.3 V rail)':28s} {total_load * 1e6:7.2f} uA")
    print(f"  {'battery (TPS63900 + leaks)':28s} {i_bat * 1e6:7.2f} uA  -> {life_months(i_bat):.1f} months")
    print(f"  charge per press {q_press * 1e3:.1f} mC at 3.3 V ({bat_from_load(q_press) * 1e3:.1f} mC from the cell)")


def report(breakdowns):
    usable = CAP_MAH * USABLE
    print(f"=== {CELL} (board {CELLS[CELL][4]}) ===\n")
    print(f"Usable capacity {usable:.0f} mAh ({CAP_MAH:.0f} mAh x {USABLE:.2f}), converter factor "
          f"{V_DD / (ETA * V_BAT):.2f} (3.3 V / ({ETA} x {V_BAT} V)), poll {Q_POLL_0DBM * 1e3:.2f} mC at 0 dBm")
    floor = bat_from_load(I_SLEEP) + I_Q_CONV + I_LEAK
    print(f"Sleep floor at the battery {floor * 1e6:.1f} uA -> upper bound with no activity at all: "
          f"{life_months(floor):.1f} months\n")
    print("1 controller (Apple Home or Home Assistant), TX 0 dBm:\n")
    print(table(1))
    print("\n2 controllers (Apple Home + Home Assistant, Multi-Admin), TX 0 dBm:\n")
    print(table(2))
    print("\nFor comparison, ESP-IDF default TX power (+20 dBm, not used by this firmware), 1 controller:\n")
    print(table(1, Q_POLL_20DBM, "20 dBm"))
    print(f"\n{CELL} if only the sleep floor changed (20 presses/day, 1 controller):\n")
    print(floor_sensitivity())
    if breakdowns:
        breakdown("SIT 15 s", 20, 1)
        breakdown("SIT 15 s", 100, 2)
        breakdown("LIT 120 s", 20, 1)
        breakdown("LIT 120 s", 100, 1)
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--breakdown", action="store_true")
    ap.add_argument("--cell", choices=sorted(CELLS), help="one cell only (default: every cell)")
    args = ap.parse_args()

    for name in [args.cell] if args.cell else CELLS:
        use_cell(name)
        report(args.breakdown)
    print(f"One-off: commissioning ~{Q_COMMISSION / 3.6:.2f} mAh, "
          f"one Thread re-attach ~{Q_REATTACH / 3.6 * 1000:.0f} uAh (load side, assumptions)")
    print("\nPer state (load side; battery column includes the converter factor of the CR2450):\n")
    use_cell("CR2450")
    print(states_table())
    print("\nPower sources, 20 presses/day, 1 controller, same electronics:\n")
    print(alternatives_table())


if __name__ == "__main__":
    main()
