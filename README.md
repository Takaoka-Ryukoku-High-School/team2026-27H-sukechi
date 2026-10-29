# 今日の段取り / くますずのプログラム / 超音波距離計

Python と Flet で作った、ブラウザで使えるシンプルなToDoリストと超音波センサーデモです。

## 1. ToDoアプリ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python kumasu_program.py
```

## 2. 超音波距離計

```bash
source .venv/bin/activate
python ultrasonic_sensor.py
```

## 3. 音声で近い・遠いを知らせる版

```bash
source .venv/bin/activate
python ultrasonic_voice_alert.py
```

## 4. 音声で近い・遠いを知らせる v2

```bash
source .venv/bin/activate
python ultrasonic_voice_alert_v2.py
```

## 5. 音声で近い・遠いを知らせる v3

```bash
source .venv/bin/activate
python ultrasonic_voice_alert_v3.py
```

v3 には、超音波の状態通知に加えて、赤い SOS ボタンを押すと「SOS」「助けてください」を読み上げる機能が統合されています。

## 6. スマホ向け版

```bash
source .venv/bin/activate
python ultrasonic_voice_alert_phone.py
```

スマホ向け版は実際の超音波センサーを本体に持たないため、距離をスライダーで入力して判定し、音声で「近いです」「遠いです」を知らせます。実機のセンサーモジュールと組み合わせると、スマホ画面で簡単に確認できます。

## 7. SOSボタン

```bash
source .venv/bin/activate
python sos_button.py
```

SOSボタンは大きな赤いボタンを押すと、音声で「SOS」「助けてください」を読み上げ、緊急用の短い警告音を再生します。

超音波距離計は HC-SR04 を Raspberry Pi に接続している場合に実距離を測定し、実機が無い環境では擬似値で動作します。音声版では「近いです」「遠いです」「ちょうどいいです」を自動で読み上げ、近い/遠い/適度の状態ごとに音のビープも変えます。

起動するとブラウザでアプリが開きます。