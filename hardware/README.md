# Phần cứng: các bo của nút nhấn Matter

Mỗi bo một thư mục, đặt tên `<mạch MCU>-<loại pin>[-<biến thể>]`. Mạch điện giống nhau ở mọi bo (module ESP32-H2-WROOM-02C, buck-boost TPS63900 3,3 V, nút, LED, đo pin, pad nạp; [README chính](../README.md) mục 2–4). Giữa các bo khác nhau ở đế pin, tụ bulk và bố trí; bo `-mini` khác thêm vài chân GPIO. Firmware là một, mỗi bo chọn bằng một file `sdkconfig.defaults.<…>` trong [`../firmware`](../firmware).

| Bo | Pin | Kích thước bo (cả anten) | Tụ bulk | Tuổi pin dự tính (SIT / LIT, 20 lần nhấn/ngày) | Firmware | Trạng thái |
|---|---|---|---|---|---|---|
| [`module-cr2450/`](module-cr2450/README.md) | CR2450 (620 mAh), đế Keystone 3008 dán ở mặt dưới | 37,4 × 30,5 mm (37,4 × 36,5 mm) | 2 × 220 µF gốm | ~11 / ~15 tháng | mặc định (`sdkconfig.defaults`) | ERC/DRC sạch, chưa đặt mạch |
| [`module-cr123a/`](module-cr123a/README.md) | CR123A (1500 mAh), đế Bulgin BX0123 xuyên lỗ ở mặt dưới | 42,4 × 27,5 mm (42,4 × 33,5 mm) | 1 × 100 µF gốm | ~30 / ~41 tháng | `sdkconfig.defaults.cr123a` | ERC/DRC sạch, chưa đặt mạch |
| [`module-cr123a-mini/`](module-cr123a-mini/README.md) | CR123A (1500 mAh) **trong vỏ, dọc cạnh dưới bo**; tiếp điểm của vỏ nối dây vào pad BAT+ / BAT− ở mép dưới; nút và LED ở mép trên (phía anten) | **34,5 × 14,8 mm** (34,5 × 20,8 mm): dài đúng một viên CR123A | 1 × 22 µF gốm | ~30 / ~41 tháng | `sdkconfig.defaults.cr123a_mini` (LED GPIO11, đo pin GPIO4) | ERC/DRC sạch, chưa đặt mạch; mọi đường vẽ tay, lắp ráp một mặt |

Bo CR2032 (29,8 × 23,9 mm, Keystone 3034) và bo chip ESP32-H2 không dùng module (`hardware-chip/`) đã bỏ: xem lịch sử git, commit `dad9ded` là bản cuối có cả hai.

## Cấu trúc thư mục

```
hardware/
├── README.md                 (file này)
├── scripts/                  bộ sinh KiCad dùng chung cho mọi bo
│   ├── circuit.py            mạch chung: linh kiện, giá trị, mã MPN/LCSC, chân → net, vị trí trên schematic
│   ├── kicad_sexp.py         tiện ích ghi S-expression; tìm bo theo thư mục hiện tại (hoặc BOARD_DIR)
│   ├── gen_project.py        .kicad_pro (luật, net class), lib/ (module, VBAT, bản sửa footprint đế pin)
│   ├── gen_sch.py            .kicad_sch
│   ├── gen_pcb.py            .kicad_pcb: đặt linh kiện, đi dây tay, FreeRouting, phủ đồng GND, via khâu
│   └── gen_fab.py            ERC + DRC, Gerber, BOM, CPL, PDF, ảnh
├── module-cr2450/
│   ├── design.py             nguồn duy nhất của bo: pin, tụ bulk, viền bo, vị trí, đường mạch, vùng cấm
│   ├── README.md             thông số, bố trí, lắp ráp của bo
│   ├── matter-button-module-cr2450.kicad_{pro,sch,pcb}, lib/, fp-lib-table, sym-lib-table   (sinh ra)
│   ├── fab/                  Gerber, BOM, CPL (sinh ra), bom-vi.csv (viết tay)
│   └── docs/                 schematic.pdf, bản vẽ lắp ráp, ảnh (sinh ra)
├── module-cr123a/            cùng cấu trúc
└── module-cr123a-mini/       cùng cấu trúc; design.py sửa thêm mạch chung (bỏ JP1/JP2, đổi chân LED và đo pin)
```

Mọi file KiCad trong thư mục bo đều được sinh từ `design.py` của bo đó. Muốn sửa thì sửa `design.py` (hoặc `scripts/circuit.py` nếu thay đổi áp dụng cho mọi bo) rồi sinh lại, không sửa tay file `.kicad_*`.

## Sinh lại một bo

Cần KiCad 9 (`kicad-cli` và module Python `pcbnew`, Python ≥ 3.11). Java 21 và [FreeRouting 2.1.0](https://github.com/freerouting/freerouting/releases) chỉ cần khi bo còn kết nối chưa vẽ tay (bo `module-cr123a`; `module-cr2450` và `module-cr123a-mini` vẽ tay toàn bộ). Trên Windows chạy trong "KiCad 9.0 Command Prompt" và gõ `python` thay cho `python3`. Trên Linux không cài KiCad thì dùng Docker image `kicad/kicad:9.0`, sau khi chép `/usr/share/kicad/template/{sym,fp}-lib-table` vào `~/.config/kicad/9.0/`.

```bash
cd hardware/module-cr2450              # hoặc module-cr123a, module-cr123a-mini
python3 ../scripts/gen_project.py      # .kicad_pro, lib/, bảng thư viện
python3 ../scripts/gen_sch.py          # .kicad_sch
python3 ../scripts/gen_pcb.py place    # .kicad_pcb: viền bo, vị trí, đường vẽ tay, vùng cấm
FREEROUTING_JAR=/đường/dẫn/freerouting-2.1.0.jar python3 ../scripts/gen_pcb.py route
python3 ../scripts/gen_fab.py          # ERC + DRC (dừng nếu có lỗi hay cảnh báo), fab/, docs/
```

- Chỉ đổi giá trị hoặc mã linh kiện (cùng footprint, cùng net): `gen_sch.py`, rồi `python3 ../scripts/gen_pcb.py sync`, rồi `gen_fab.py`.
- FreeRouting không cho cùng một kết quả mỗi lần chạy. `gen_fab.py` chỉ xuất file khi DRC sạch.
- Ảnh layout 2D (`docs/pcb-layout.png`) cần thêm `pip install cairosvg pillow`; thiếu thì bước này được bỏ qua.
- CI (`.github/workflows/build.yml`, job `hardware-check`) chạy ERC + DRC cho mọi bo trên file đã commit.

## Thêm một bo mới (pin khác, bố trí khác)

1. Chép thư mục bo gần giống nhất, ví dụ `cp -r module-cr123a module-2xaaa`, xoá các file sinh ra (`*.kicad_*`, `lib/`, `fp-lib-table`, `sym-lib-table`, `fab/*` trừ `bom-vi.csv`, `docs/`).
2. Sửa `design.py`: `PROJECT`, `BATTERY`, `TITLE`; đế pin (`holder`: footprint chuẩn của KiCad, một bản sửa qua `CUSTOM_FOOTPRINTS`, hoặc chỉ các pad nối dây như `CR123A_WirePads` của bo mini: `CUSTOM_FOOTPRINTS` với `pads=[...]`) và tụ bulk (`bulk`) trong `circuit.battery_parts()`; `OUTLINE`, `PLACE`, `ROUTES`, `VIAS`, các vùng cấm và chữ in. Bo cần bỏ hay đổi chân của vài linh kiện chung thì sửa danh sách trong `design.py` của nó (xem `_adapt()` trong `module-cr123a-mini/design.py`), không sửa `circuit.py`.
3. Sinh lại như trên cho tới khi ERC/DRC sạch; viết `README.md` và `fab/bom-vi.csv` của bo.
4. Firmware: thêm loại pin vào `choice BATTERY_TYPE` trong [`../firmware/main/Kconfig.projbuild`](../firmware/main/Kconfig.projbuild) (tên IEC, mô tả thay pin, dung lượng, chuỗi phiên bản phần cứng) nếu là pin mới, thêm `firmware/sdkconfig.defaults.<bo>` chọn nó (và đặt `BATTERY_SENSE_GPIO`, `STATUS_LED_GPIO`, `DEVICE_HARDWARE_VERSION_STRING` nếu bo khác chân, như `sdkconfig.defaults.cr123a_mini`); thêm bo vào ma trận `hardware-check` và biến thể vào ma trận `build` của CI; thêm pin vào `CELLS` của [`../tools/battery_model.py`](../tools/battery_model.py).
5. Mạch khác hẳn (MCU khác, thêm linh kiện) thì đưa phần mạch riêng vào `design.py` thay vì `circuit.CORE_PARTS`.
