# くますずのプログラム

ToDo、超音波距離計、距離に応じた音声通知、手動での距離判定、SOS通知をひとつのFletアプリにまとめています。

## 起動方法

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python kumasu_program.py
```

`launcher.py` からも同じアプリを起動できます。ブラウザで画面を切り替えて各機能を使えます。

スマホのブラウザでは画面幅に合わせて表示され、画面下のナビゲーションから「段取り・距離・音声・SOS」を切り替えられます。

ToDoのデータは `~/.kumasu_program_tasks.json` に保存されます。HC-SR04をRaspberry Piに接続していない場合は、距離計が擬似計測モードで動作します。
