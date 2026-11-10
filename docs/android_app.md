# ClearPath AI Android App

## 開啟專案

Android Studio → **File → Open → 選 `android/` 資料夾**（不是 repo 根目錄，否則無法 Gradle sync）。

## Google Maps 金鑰

導航需要 Google Maps Platform 金鑰，在 Google Cloud Console 啟用 **Places API (New)** 與 **Routes API** 後，
寫進 `android/local.properties`（此檔不會被 commit）：

```
MAPS_API_KEY=AIza...
```

沒有金鑰時避障功能照常運作，只有導航會說「尚未設定 Google Maps 金鑰」。

### 金鑰限制（Android 應用程式）

App 每次呼叫 Google 都會帶上 `X-Android-Package` 與 `X-Android-Cert`（簽章 SHA-1），
所以金鑰可以在 Cloud Console 設成「Android 應用程式」限制，別人拿到金鑰也無法使用。

- 套件名稱：`com.blindassist.app`
- SHA-1：**每台電腦的 debug 簽章都不同**。在誰的電腦編譯 APK，就要把那台電腦的 SHA-1 加到同一把金鑰
  （Android Studio → Gradle → app → Tasks → android → `signingReport`，一把金鑰可加多組）。
- 沒加到 SHA-1 的電腦編出來的 APK，導航會出現「地圖服務錯誤 403」。

## 使用方式

| 操作 | 功能 |
|---|---|
| 按大按鈕說「帶我去全家便利商店」 | 搜尋目的地並開始步行導航 |
| 「去附近的便利商店」 | 找最近的一間 |
| 「前面有什麼」或按「前面有什麼」 | 描述前方物體與距離 |
| 「再說一次」 | 重複目前的導航指示 |
| 「停止導航」 | 結束導航 |
| 「影像來源」按鈕 | 切換手機鏡頭（測試用）/ 眼鏡（Wi-Fi，IP 留空自動尋找） |
| 「問問題」按鈕 | 嗶聲後發問（例如「這是什麼」），說完自動送到 AI 伺服器，播放回答；再按一下可提早結束錄音 |
| 長按「問問題」 | 設定 AI 伺服器位址（筆電 IP，預設連接埠 8765） |

避障警告會自動播報，例如「前方1.2公尺有機車，請稍向右」；1 公尺內會立即插播。

## 架構

```
camera/   影像來源：PhoneCameraSource（手機鏡頭）、Esp32StreamSource + Esp32Discovery（XIAO ESP32S3 Wi-Fi，協定見 esp32_protocol.md）
detect/   YOLOv8n（LiteRT）物件辨識 + 中文類別
guide/    ObstacleFuser 雙模測距融合、ObstacleAnnouncer 語音警告、ObstacleMonitor 管線
nav/      Places API + Routes API 路線規劃、GPS 逐步導引、偏離重算
speech/   TTS、語音指令辨識與解析
```

## AI 伺服器（問問題）

「問問題」使用 [BlindAssistDevice](https://github.com/tzicube/BlindAssistDevice) 的 AI 伺服器（`AiServer/test.py`，port 8765），
API 不需修改：App 先把當下畫面送到 `POST /api/videoframe`（image/jpeg），再把錄音送到 `POST /api/recognize`（audio/wav，16 kHz），
伺服器以 Whisper 轉文字、Gemma 看畫面回答、Piper 轉語音，回傳 audio/wav 由手機播放。

1. 筆電和手機連同一個網路（例如都連手機熱點）。
2. 筆電啟動伺服器：
   - 真的伺服器：照 BlindAssistDevice 的說明啟動（需要 GPU、Ollama）。
   - 沒有 GPU 時測試：`python tools/mock_ai_server.py`。API 相同，回答是一段提示音，收到的錄音和畫面會存在 `mock_ai_output/`，可以聽錄音品質。
3. 終端機會印出筆電 IP。在 App 長按「問問題」輸入這個 IP（或在 `local.properties` 寫 `AI_SERVER_URL=192.168.x.x`）。
4. Windows 第一次會跳出防火牆詢問，**私人和公用網路都要允許**（手機熱點常被當成公用網路）。

伺服器只用 HTTP，所以 App 透過 `res/xml/network_security_config.xml` 允許明文連線；Google Maps 仍走 HTTPS。

## 與提案書的對照

| 提案項目 | 目前狀態 |
|---|---|
| YOLOv8n 物件辨識 | ✅ 手機端 LiteRT 執行（COCO 80 類；施工圍欄需自行訓練） |
| 雙目立體視覺測距 | ⏳ XIAO ESP32S3 Sense 只有一顆鏡頭，需第二片 XIAO；暫以單鏡頭 + 物體高度估距，協定已預留第二鏡頭 |
| 超聲波感測 + 互相校驗 | ✅ App 融合邏輯與 XIAO 韌體都已完成（`esp32/clearpath_glasses/`） |
| 信心不足只說「有障礙物」 | ✅ |
| Google Maps 戶外導引 | ✅ Places API (New) + Routes API（Directions API 的後繼版本） |
| Whisper 語音辨識 | ⏳ 導航指令暫用 Android 內建語音辨識；「問問題」經 AI 伺服器跑 Whisper（App 端完成，待真伺服器實測） |
| 多模態語音助理（Whisper + Gemma） | ⏳ 「問問題」接 BlindAssistDevice AI 伺服器，App 端完成，待真伺服器實測 |
| Gemma 生成語音文字 | ⏳ 暫用規則式短句（≤ 20 字）|
| 家屬監控 / 觸碰微引導 | ⏳ 延伸功能，尚未開始 |

## 測試

```
cd android
./gradlew testDebugUnitTest
```
