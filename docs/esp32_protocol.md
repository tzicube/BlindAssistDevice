# ESP32 → Android 傳輸協定

硬體：**Seeed Studio XIAO ESP32S3 Sense**（內建 OV2640/OV3660 鏡頭、8 MB PSRAM、2.4 GHz Wi-Fi、BLE 5）。
眼鏡端韌體：`esp32/clearpath_glasses/`　Android 端實作：`android/app/src/main/java/com/blindassist/app/camera/`

## 為什麼用 Wi-Fi，不用藍牙

- ESP32-S3 **沒有藍牙 Classic（SPP）**，只有 BLE。
- 320×240 JPEG 每張約 8–15 KB，10 FPS 需要約 100–150 KB/s；BLE 實際只有幾十 KB/s，跑不到 10 FPS。
- 所以影像與超聲波都走 Wi-Fi。

## 連線方式

```
手機開「個人熱點」(2.4 GHz)
        ▲  Wi-Fi
        │
XIAO ESP32S3 連上熱點 ──每秒廣播 UDP "CLEARPATH 8888" 到 port 8889──▶ 手機 App 收到後得知眼鏡 IP
        │
        └──── TCP port 8888（眼鏡當 server，手機連過去）──── 影像 + 超聲波封包
```

- 眼鏡的熱點名稱 / 密碼寫在 `esp32/clearpath_glasses/config.h`。
- App 選「影像來源 → 眼鏡（Wi-Fi）」，IP **留空**就會自動尋找；也可以手動輸入 IP。
- 熱點要設成 **2.4 GHz**（iPhone 打開「最大化相容性」；Android 在熱點設定選 2.4 GHz），ESP32-S3 不支援 5 GHz。
- 手機開熱點時仍可用行動網路查 Google Maps，不影響導航。

## 封包格式

```
+------+------+------+----------------------+-----------------+
| 0xBA | 0xC1 | type | length (uint32, LE)  | payload (length)|
+------+------+------+----------------------+-----------------+
```

| type | 內容 | payload |
|---|---|---|
| `0x01` | 鏡頭 JPEG | 一張完整 JPEG（320×240，品質 12） |
| `0x02` | 第二顆鏡頭 JPEG | 保留給雙目測距（需要第二片 XIAO），App 目前尚未使用 |
| `0x10` | 超聲波距離 | N 個 uint16 LE，單位公分，順序 **左 → 中 → 右**；沒有回波填 `0xFFFF` |

- payload 上限 512 KB，超過會被視為壞封包並重新同步。
- 超聲波每 120 ms 送一次；App 只採用 1.5 秒內的讀數。
- 影像要正向（不需旋轉）。若鏡頭裝反，在韌體用 `s->set_vflip()` / `set_hmirror()` 修正。

## 規劃中：眼鏡麥克風（App 尚未實作，格式待組內確認）

XIAO ESP32S3 Sense 內建 PDM 麥克風，不用另外接線。聲音沿用同一條 TCP 連線傳給手機，再由手機送 AI 伺服器；
回答從手機（藍牙耳機）播放，眼鏡不需要喇叭。

| type | 內容 | payload |
|---|---|---|
| `0x20` | 聲音 | PCM 16-bit LE、單聲道、16 kHz，每包約 100 ms（1600 個樣本 = 3200 bytes） |
| `0x21` | 按鈕 | 1 byte：`1` = 按下（開始說話）、`0` = 放開（說完） |

- **有按鈕**（建議，按住說話）：只在按住時送 `0x20`，按下、放開各送一次 `0x21`。按鈕可接 D6 或 D7。
- **沒有按鈕**：持續送 `0x20`（約 32 KB/s），由 App 的「問問題」按鈕決定何時開始，並自動判斷說完。
- 導航語音指令仍用手機麥克風（Android 內建辨識只能聽手機麥克風）。

## 超聲波接線（XIAO ESP32S3 Sense）

Sense 擴充板的鏡頭、麥克風、SD 卡已佔用其他腳位，D0–D5 可自由使用：

| 感測器 | TRIG | ECHO |
|---|---|---|
| 左 | D0 | D1 |
| 中 | D2 | D3 |
| 右 | D4 | D5 |

- 請用 **3.3 V 相容**的模組（HC-SR04P、RCWL-1601）。傳統 HC-SR04 的 ECHO 是 5 V，要加分壓電阻（例如 1 kΩ + 2 kΩ）才能接 XIAO，否則可能燒腳位。
- 三顆感測器輪流量測，避免互相干擾。

## 燒錄

1. Arduino IDE → 開發板管理員安裝 **esp32 by Espressif**（3.x）。
2. 開發板選 **XIAO_ESP32S3**，**Tools → PSRAM → OPI PSRAM**（沒開鏡頭會初始化失敗）。
3. 修改 `config.h` 的熱點名稱與密碼，上傳。
4. 序列埠監看視窗（115200）會顯示取得的 IP 與「Phone connected」。

## 沒有硬體時測試

`esp32/tools/fake_glasses.py` 會假裝成眼鏡（含 UDP 廣播）：

```
python esp32/tools/fake_glasses.py 某張照片.jpg --sonar=-1,80,-1
```

手機與電腦在同一個 Wi-Fi 下，App 選「眼鏡（Wi-Fi）」留空即可。
