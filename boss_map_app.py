import tkinter as tk
from PIL import Image, ImageTk
from collections import Counter
from tkinter import messagebox
import os
import json

# ボス位置（白丸の座標）
boss_positions = [
    (268, 195), (331, 246), (642, 215), (314, 383),
    (464, 358), (545, 384), (731, 503), (448, 504),
    (449, 571), (302, 816), (440, 710), (665, 766)
]

# ボス一覧
normal_bosses = [
    "亜人の女王", "黄金カバ", "王配の赤狼", "黒き刃の刺客", "ザミェルの古英雄",
    "獅子の混種", "接ぎ木の貴公子", "ミランダフラワー", "夜の騎兵", "王族の幽鬼","老獅子"
]
strong_bosses = [
    "黄金樹の化身", "カーリアの親衛騎士", "丘陵の飛竜", "黒き剣の眷属", "死儀礼の鳥",
    "鈴玉狩り", "祖霊", "爛れた樹霊", "ツリーガード", "溶岩土竜", "竜のツリーガード"
]

normal_boss_number_map = {name: i + 1 for i, name in enumerate(normal_bosses)}
strong_boss_number_map = {name: i + 1 for i, name in enumerate(strong_bosses)}
boss_number_map = {**normal_boss_number_map, **strong_boss_number_map}

quest_names = [
    "三つ首の獣", "喰らいつく顎", "知性の蟲", "兆し",
    "調律の魔物", "闇駆ける狩人", "霧の裂け目", "夜を象る者"
]

# ===== 位置定義を一元化 =====
# スタート位置（表示名, (x, y)）
START_POSITIONS = [
    ("南西", (180, 677)),
    ("西",   (194, 528)),
    ("北西1",(219, 384)),
    ("北西2",(357, 402)),
    ("北",   (520, 213)),
    ("北東a", (682, 371)),
    ("北東b", (665, 366)),
    ("東",   (787, 539)),
    ("南1",  (584, 788)),
    ("南2",  (546, 666)),
    ("南3a",  (542, 598)),
    ("南3b",  (542, 598)),
]
START_ORDER  = [name for name, _ in START_POSITIONS]
START_COORDS = {name: xy for name, xy in START_POSITIONS}

# DAY安置（表示名, マーカー座標(x, y), 円中心(Noneなら未定義=マーカー座標を使用)）
DAY_POSITIONS = [
    ("中央", (425, 616), None),
    ("南",   (471, 764), (542, 614)),
    ("南西", (267, 748), (358, 647)),
    ("西",   (202, 412), (389, 356)),
    ("北西", (216, 214), (350, 352)),
    ("北",   (565, 280), (555, 370)),
    ("北東", (790, 240), (647, 367)),
    ("東",   (706, 573), None),
    ("南東", (702, 684), None),
]
DAY_ORDER            = [name for name, _, _ in DAY_POSITIONS]
DAY_MARKER_COORDS    = {name: xy for name, xy, _ in DAY_POSITIONS}
DAY_CIRCLE_CENTERS   = {name: cc for name, _, cc in DAY_POSITIONS if cc is not None}
DAY_CIRCLE_RADIUS = 236

SAVE_FILE = "boss_location.json"

# 追加キー定義（ここを増減するだけでUI/キー/保存順に反映されます）
OPTIONAL_KEYS = [
    {
        "label": "地変",
        "var_name": "chihen",
        "choices": ["", "火口", "山嶺", "腐れ森", "ノクラテオ"],
        "default": ""
    }
]
NON_NUMERIC_ORDER = ["DAY1安地", "DAY2安地"]

class BossMapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("NIGHTREIGN マップパターン集計ツール ver.1.0.0")
        self.root.geometry("1280x680")  # 起動時のウィンドウサイズ

        self.state = self.load_state()
        self.undo_state = {}  # 元に戻す用の状態保持
        self.readonly = tk.BooleanVar(value=True)  # 読み取り専用トグル
        self.compact = tk.BooleanVar(value=False)  # コンパクト表示トグル
        self.compact_boundary = 160                # マップ右に確保する固定幅(px)
        self._left_col_width = None  # コンパクト解除時に使う左列の幅（px)
        self.font = ("Helvetica", 12)  # 共通フォント設定（12pt）
        self.styles = {
            "button": {  # 標準ボタン
                "relief": "ridge",
                "bd": 2,
                "padx": 10,
                "pady": 4,
                "font": self.font,
                "activebackground": "#808080",
            },
            "small_button": {  # 保存・解除・元に戻す用（初期状態に近い）
            "relief": "raised",
            "bd": 2,
            "padx": 6,
            "pady": 3,
            "font": self.font,
        },
            "toggle": {  # チェック/ラジオ共通
                "indicatoron": 0,
                "relief": "ridge",
                "bd": 2,
                "overrelief": "sunken",
                "padx": 8,
                "pady": 4,
                "font": self.font,
                "selectcolor": "#c0c0c0",
                "activebackground": "#808080",
            },
            "boss_toggle": {  # ★ボスリスト専用
                "indicatoron": 0,
                "relief": "ridge",
                "bd": 2,
                "overrelief": "sunken",
                "padx": 4,   # ← 横の余白
                "pady": 2,    # ← 高さ余白
                "font": ("Helvetica", 14),  # ← フォントサイズ
                "selectcolor": "#c0c0c0",
                "activebackground": "#808080",
                "anchor": "w",   # 左寄せ
                "justify": "left"
            },
        }

        self.mode = tk.StringVar(value="通常")
        self.players = tk.IntVar(value=1)  # デフォルトは1人
        self.quest_name = tk.StringVar(value=quest_names[0])
        self.start_pos = tk.StringVar(value="南西")

        # ▼ DAY1安置（新規）
        self.day1_pos = tk.StringVar(value="")  # 未選択開始
        self.day1_position_coords = DAY_MARKER_COORDS
        self.day1_circle_center   = DAY_CIRCLE_CENTERS

        self.day2_pos = tk.StringVar(value="")

        script_dir = os.path.dirname(os.path.abspath(__file__))
        map_path = os.path.join(script_dir, "map.jpg")
        self.map_img = Image.open(map_path)
        self.tk_img = ImageTk.PhotoImage(self.map_img)

        # ルート直下は pack に統一するためのコンテナ
        container = tk.Frame(root)
        container.pack(fill=tk.BOTH, expand=True)

        # 右パネル（先に右側へ固定）
        self.right = tk.Frame(container)
        self.right.pack(side=tk.RIGHT, fill=tk.Y, padx=10)

        # キャンバス作成（親：container）
        self.canvas = tk.Canvas(container, width=self.tk_img.width(), height=self.tk_img.height())
        self.canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        self._resize_job = None

        # 背景画像アイテム ID を保持（以後、画像差し替え）
        self.bg_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img, tags=("bg",))

        # 元画像サイズと現在スケール
        self.base_w, self.base_h = self.tk_img.width(), self.tk_img.height()
        self.scale = 1.0

        # Canvas サイズ変化でリサイズ
        self.canvas.bind("<Configure>", self._schedule_resize)

        # 丸と番号の初期描画（スケール対応）
        self.redraw_static_items()

        # 左カラム：ボスリスト表示用
        self.right_left = tk.Frame(self.right)
        self.right_left.pack(side=tk.LEFT, anchor="n", padx=(0, 10))  # 左にボスリスト

        # 右カラム：ボタン・ドロップダウン類
        self.right_right = tk.Frame(self.right)
        self.right_right.pack(side=tk.LEFT, anchor="n", fill=tk.Y)

        # 上部UIコンテナ
        self.controls = tk.Frame(self.right_right)
        self.controls.pack(fill=tk.X)

        self.root.bind("<Configure>", self._schedule_resize)

        # --- 固定幅フレームを作る関数 ---
        def fixed_frame(parent, width_px, height_px):
            f = tk.Frame(parent, width=width_px, height=height_px)
            f.pack_propagate(False)  # 中身のサイズで縮ませない
            return f

        # --- 読み取り専用トグル（固定幅化 & ONで「編集中」表示）---
        ro_frame = fixed_frame(self.controls, width_px=140, height_px=35)  # 幅140px・高さ40px固定
        ro_frame.pack(pady=(10, 0))

        self.ro_button = tk.Checkbutton(
            ro_frame,
            text="読み取り専用",  # 初期表示
            variable=self.readonly,
            onvalue=False,  # チェックON → 編集モード
            offvalue=True,  # チェックOFF → 読み取り専用
            command=self.on_readonly_toggle,
            **self.styles["toggle"]
        )
        self.ro_button.config(relief='sunken', offrelief='sunken',bg="#c0c0c0",activebackground="#c0c0c0")
        self.ro_button.pack(fill=tk.BOTH, expand=True)
        # ここで一度、表示と状態を同期
        self.on_readonly_toggle()

        self._last_readonly = self.readonly.get()  # 直前状態の記録（初期は True）
        self._ro_guard = False                     # 再入防止ガード

        self.boss_vars = {}
        self.boss_checks = {}

        # モード選択
        # --- モード選択 ---
        tk.Label(self.controls, text="モード", font=self.font).pack(pady=(5, 0))
        mode_frame = tk.Frame(self.controls)
        mode_frame.pack()
        self.make_radio(mode_frame, self.mode, "通常", text="通常",
                        command=self.update_display, width=len("通常")).pack(side=tk.LEFT, padx=4)
        self.make_radio(mode_frame, self.mode, "常夜", text="常夜",
                        command=self.update_display, width=len("常夜")).pack(side=tk.LEFT, padx=4)

        # --- プレイ人数選択 ---
        tk.Label(self.controls, text="プレイ人数", font=self.font).pack(pady=(5, 0))
        players_frame = tk.Frame(self.controls)
        players_frame.pack()
        for num in [1, 2, 3]:
            self.make_radio(players_frame, self.players, num, text=str(num),
                            command=self.update_display, width=len(str(num))).pack(side=tk.LEFT, padx=5)

        # クエスト選択
        tk.Label(self.controls, text="クエスト", font=self.font).pack(pady=(5, 0))
        self.quest_menu = self._make_optionmenu(self.controls, self.quest_name, quest_names, lambda *_: self.update_display())
        self.quest_menu.pack()

        # ▼ 追加キー（OPTIONAL_KEYS）をまとめて生成：クエストの直下に挿入
        self.extra_vars = {}
        for opt in OPTIONAL_KEYS:
            var = tk.StringVar(value=opt.get("default", ""))
            self.extra_vars[opt["var_name"]] = var
            tk.Label(self.controls, text=opt["label"], font=self.font).pack(pady=(5, 0))
            self._make_optionmenu(self.controls, var, opt["choices"], lambda *_: self.update_display()).pack()

        # スタート位置（ラベルと★）
        start_label_frame = tk.Frame(self.controls)
        start_label_frame.pack(pady=(5, 0))  # クエスト選択との間隔を確保
        tk.Label(start_label_frame, text="スタート位置", font=self.font).pack(side=tk.LEFT)
        self.start_marker_label = tk.Label(start_label_frame, text="★", font=("Helvetica", 12), fg="lime")
        self.start_marker_label.pack(side=tk.LEFT)

        # スタート位置ドロップダウン
        self.start_menu = self._make_optionmenu(self.controls, self.start_pos, START_ORDER, lambda *_: self.update_display())
        self.start_menu.pack()

        # DAY1安置 ラベル＋▼マーク
        day1_label_frame = tk.Frame(self.controls)
        day1_label_frame.pack(pady=(5, 0))
        tk.Label(day1_label_frame, text="DAY1安地", font=self.font).pack(side=tk.LEFT)
        tk.Label(day1_label_frame, text="▼", font=("Helvetica", 12), fg="deepskyblue").pack(side=tk.LEFT)
        # DAY1安置 ドロップダウン
        self.day1_menu = self._make_optionmenu(self.controls, self.day1_pos, [""] + DAY_ORDER, self.on_day1_change)
        self.day1_menu.pack()

        # DAY2安置 ラベル＋▼マーク
        day2_label_frame = tk.Frame(self.controls)
        day2_label_frame.pack(pady=(5, 0))
        tk.Label(day2_label_frame, text="DAY2安地", font=self.font).pack(side=tk.LEFT)
        tk.Label(day2_label_frame, text="▼", font=("Helvetica", 12), fg="red").pack(side=tk.LEFT)

        # DAY2安置 ドロップダウン（座標はDAY1と共通を再利用）
        self.day2_menu = self._make_optionmenu(self.controls, self.day2_pos, [""] + DAY_ORDER, self.on_day2_change)
        self.day2_menu.pack()

        # --- コンパクト表示（ONで左列を隠し＋リサイズ、OFFで左列を戻す）---
        self.compact_btn = tk.Checkbutton(
            self.controls,
            text="コンパクト表示",
            variable=self.compact,
            command=self.on_compact_toggle,
            **self.styles["toggle"]
        )
        self.compact_btn.pack(pady=(6, 0), fill=tk.X)

        # --- 残りスペースを埋めてボタンを最下段へ押し下げる ---
        spacer = tk.Frame(self.right_right)
        spacer.pack(expand=True, fill=tk.BOTH)

        # --- 最下段：ボタンを縦に並べる ---
        buttons_col = tk.Frame(self.right_right)
        buttons_col.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 6))

        self.btn_save  = self.make_button(buttons_col, variant="small_button", text="💾 保存", command=self.save_state)
        self.btn_clear = self.make_button(buttons_col, variant="small_button", text="🗑 すべて解除", command=self.clear_all)
        self.btn_undo  = self.make_button(buttons_col, variant="small_button", text="↩ 元に戻す", command=self.undo_clear)

        self.btn_save.pack(fill=tk.X, pady=3)
        self.btn_clear.pack(fill=tk.X, pady=3)
        self.btn_undo.pack(fill=tk.X, pady=3)

        self.boss_list_frame = tk.Frame(self.right_left)
        self.boss_list_frame.pack(pady=10)

        # ▼ 集計グラフ（ボスリストの下）
        self.stats_frame = tk.Frame(self.right_left)
        self.stats_frame.pack(fill=tk.X, pady=(8, 0))
        self.stats_title = tk.Label(self.stats_frame, text="出現数（同一モード/人数/クエスト）", font=self.font)
        self.stats_title.pack(anchor="w")
        self.stats_canvas = tk.Canvas(self.stats_frame, height=40, highlightthickness=0)
        self.stats_canvas.pack(fill=tk.X)

        self._prev_start = None
        self._prev_day1 = None
        self._prev_day2 = None

        # ボスリストUIを一度だけ構築する
        self._boss_list_built = False
        def build_boss_list_ui():
            if self._boss_list_built:
                return
            # 2列の土台
            self.left_col  = tk.Frame(self.boss_list_frame)
            self.right_col = tk.Frame(self.boss_list_frame)
            self.left_col.pack(side=tk.LEFT, anchor="n", padx=(0, 10))
            self.right_col.pack(side=tk.LEFT, anchor="n")

            tk.Label(self.left_col,  text="通常ボス", font=self.font).pack(anchor="w")
            tk.Label(self.right_col, text="恐るべき強敵", fg="red", font=self.font).pack(anchor="w")

            # 変数とウィジェットを保持
            self.boss_vars = getattr(self, "boss_vars", {})

            def add_item(parent, name, is_strong=False):
                if name not in self.boss_vars:
                    self.boss_vars[name] = tk.IntVar(value=0)
                var = self.boss_vars[name]
                fg = "red" if is_strong else "black"
                label_text = f"{boss_number_map.get(name, '')}. {name}"
                cb = tk.Checkbutton(
                    parent,
                    text=label_text,
                    variable=var,
                    fg=fg,
                    command=lambda n=name, v=var: v.set(1 if n in self._current_values else 0),
                    **self.styles["boss_toggle"]  # ←ここをボス専用に
                )
                cb.pack(fill=tk.X, pady=0)
                self.boss_checks[name] = cb

            for name in normal_bosses:
                add_item(self.left_col, name, is_strong=False)

            for name in strong_bosses:
                add_item(self.right_col, name, is_strong=True)

            self._boss_list_built = True

        build_boss_list_ui()

        self.update_display()
        self.update_readonly_ui()  # ← 初期状態を反映
        self.root.update_idletasks()
        self.on_canvas_resize()

    # --- ファクトリメソッド ---
    def make_button(self, parent, variant="button", **kwargs):
        style = {**self.styles.get(variant, self.styles["button"]), **kwargs}
        return tk.Button(parent, **style)
    def make_radio(self, parent, variable, value, **kwargs):
        return tk.Radiobutton(
            parent, variable=variable, value=value, **{**self.styles["toggle"], **kwargs}
        )
    def _make_optionmenu(self, parent, var, choices, cmd=None):
        om = tk.OptionMenu(parent, var, *choices, command=cmd)
        om.config(font=self.font)
        om["menu"].config(font=self.font)
        return om
    def on_readonly_toggle(self):
        # 再入防止（変数をプログラム側でセットし直す時に command が再発火するのを抑止）
        if getattr(self, "_ro_guard", False):
            return
        new_ro = self.readonly.get()  # True: 読み取り専用 / False: 編集中
        # 「読み取り専用 → 編集中」に切り替えようとしたときだけ確認ダイアログ
        if getattr(self, "_last_readonly", True) is True and new_ro is False:
            ok = messagebox.askyesno("編集モードにしますか？",
                                    "編集モードに切り替えます。よろしいですか？")
            if not ok:
                # ユーザーがキャンセル → 変数を元に戻す（command が再発火しないようにガード）
                self._ro_guard = True
                try:
                    self.readonly.set(True)  # 読み取り専用に戻す
                finally:
                    self._ro_guard = False
                # テキストとUIを現在状態（読み取り専用）に合わせて更新
                self.ro_button.config(text="読み取り専用")
                self.update_readonly_ui()
                # 直前状態を維持して終了
                self._last_readonly = True
                return
        # ここに来たら変更を反映
        self.ro_button.config(text=("読み取り専用" if new_ro else "編集中"))
        self.update_readonly_ui()
        # 直前状態を更新
        self._last_readonly = new_ro

    def get_key(self):
        extras = [self.extra_vars[opt["var_name"]].get() for opt in OPTIONAL_KEYS]
        return "|".join([
            self.mode.get(),
            str(self.players.get()),
            self.quest_name.get(),
            *extras,
            self.start_pos.get()
        ])

    def _schedule_resize(self, _event):
        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)
        # ルートのサイズ変化をデバウンスして処理
        self._resize_job = self.root.after(60, self.on_canvas_resize)
    def on_canvas_resize(self):
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        new_scale = min(cw / self.base_w, ch / self.base_h)
        if abs(new_scale - getattr(self, "scale", 1.0)) < 0.01:
            return
        self.scale = new_scale
        resized = self.map_img.resize(
            (max(1, int(self.base_w * self.scale)), max(1, int(self.base_h * self.scale))),
            Image.LANCZOS
        )
        self.tk_img = ImageTk.PhotoImage(resized)
        self.canvas.itemconfig(self.bg_id, image=self.tk_img)
        self.redraw_static_items()
        self._prev_start = None
        self._prev_day1 = None
        self._prev_day2 = None
        self.update_display()

    def redraw_static_items(self):
        """ボス丸と番号（テキスト）を現在スケールで再配置"""
        self.canvas.delete("boss_items")
        r = max(6, int(20 * self.scale))  # 最小6px
        font_sz = max(10, int(20 * self.scale))
        for i, (x, y) in enumerate(boss_positions):
            sx, sy = int(x * self.scale), int(y * self.scale)
            tag = f"boss{i}"
            self.canvas.create_oval(
                sx - r, sy - r, sx + r, sy + r,
                fill="white", outline="black",
                tags=(tag, "boss_items")
            )
            self.canvas.create_text(
                sx, sy, text="", font=("Helvetica", font_sz, "bold"),
                tags=(f"label{i}", tag, "boss_items")
            )
            self.canvas.tag_bind(tag, "<Button-1>", lambda e, idx=i: self.assign_boss(idx))

    def assign_boss(self, index):
        # 読み取り専用中はポップアップを開かない
        if self.readonly.get():
            return
        key = self.get_key()
        current_boss = self.state.get(key, {}).get(str(index), "")

        popup = tk.Toplevel(self.root)
        popup.title("ボス選択")
        popup.geometry("+%d+%d" % (self.root.winfo_pointerx(), self.root.winfo_pointery()))
        popup.grab_set()

        normal_var = tk.StringVar(value="")
        strong_var = tk.StringVar(value="")

        if current_boss in normal_bosses:
            normal_var.set(current_boss)
        elif current_boss in strong_bosses:
            strong_var.set(current_boss)

        def on_normal_select(*_):
            if normal_var.get():
                strong_var.set("")

        def on_strong_select(*_):
            if strong_var.get():
                normal_var.set("")

        boss_frame = tk.Frame(popup)
        boss_frame.pack(padx=10, pady=(10, 0))

        # 左側（通常ボス）
        normal_col = tk.Frame(boss_frame)
        normal_col.pack(side=tk.LEFT, padx=5)
        tk.Label(normal_col, text="▶ 通常ボス", font=self.font).pack()
        normal_menu = tk.OptionMenu(normal_col, normal_var, *normal_bosses, command=on_normal_select)
        normal_menu.config(font=self.font)
        normal_menu["menu"].config(font=self.font)
        normal_menu.pack()

        # 右側（恐るべき強敵）
        strong_col = tk.Frame(boss_frame)
        strong_col.pack(side=tk.LEFT, padx=5)
        tk.Label(strong_col, text="▶ 恐るべき強敵", font=self.font).pack()
        strong_menu = tk.OptionMenu(strong_col, strong_var, *strong_bosses, command=on_strong_select)
        strong_menu.config(font=self.font)
        strong_menu["menu"].config(font=self.font)
        strong_menu.pack()

        def confirm():
            selected = normal_var.get() or strong_var.get()
            if not selected:
                popup.destroy()
                return
            if key not in self.state:
                self.state[key] = {}
            self.state[key][str(index)] = selected
            popup.destroy()
            self.update_display()

        def clear():
            if key in self.state:
                self.state[key].pop(str(index), None)
            popup.destroy()
            self.update_display()

        btn_frame = tk.Frame(popup)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="OK", command=confirm, font=self.font).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="選択解除", command=clear, font=self.font).pack(side=tk.LEFT, padx=5)

    def update_display(self):
        key = self.get_key()
        current = self.state.get(key, {})
        if key not in self.state:
            self.state[key] = current = {}

        # --- マップ上のボス番号ラベルを更新 ---
        for i in range(12):
            boss = current.get(str(i), "")
            color = "red" if boss in strong_bosses else "black"
            label = str(boss_number_map.get(boss, ""))
            self.canvas.itemconfig(f"label{i}", text=label, fill=color)

        # --- ボスリスト（再packせず、IntVarだけ更新）---
        if not hasattr(self, "boss_vars"):
            self.boss_vars = {}
        self._current_values = set(current.values())
        for name in normal_bosses + strong_bosses:
            if name in self.boss_vars:
                self.boss_vars[name].set(1 if name in self._current_values else 0)

        # --- ★スタート位置（変更時のみ再描画）---
        if getattr(self, "_prev_start", None) != self.start_pos.get():
            self._prev_start = self.start_pos.get()
            self.canvas.delete("start_marker")
            pos = START_COORDS.get(self._prev_start)
            if pos:
                x, y = pos
                sx, sy = int(x * self.scale), int(y * self.scale)
                f1 = max(16, int(34 * self.scale))
                f2 = max(14, int(30 * self.scale))
                self.canvas.create_text(sx, sy, text="★", font=("Helvetica", f1),
                                        fill="black", tags="start_marker")
                self.canvas.create_text(sx, sy, text="★", font=("Helvetica", f2),
                                        fill="lime", tags="start_marker")
                self.canvas.tag_raise("start_marker")

        # --- DAY1安置（UI同期→変更時のみ再描画）---
        day1_selected = current.get("DAY1安地", "")
        if self.day1_pos.get() != day1_selected:
            self.day1_pos.set(day1_selected)

        if getattr(self, "_prev_day1", None) != day1_selected:
            self._prev_day1 = day1_selected
            self.canvas.delete("day1_zone")
            self.canvas.delete("day1_marker")
            if day1_selected:
                pos2 = self.day1_position_coords.get(day1_selected)
                if pos2:
                    x2, y2 = pos2
                    cx, cy = self.day1_circle_center.get(day1_selected, (x2, y2))
                    r = DAY_CIRCLE_RADIUS
                    scx, scy = int(cx * self.scale), int(cy * self.scale)
                    sx2, sy2 = int(x2 * self.scale), int(y2 * self.scale)
                    rr = max(8, int(r * self.scale))
                    self.canvas.create_oval(scx - rr, scy - rr, scx + rr, scy + rr,
                                            outline="deepskyblue", width=2, tags="day1_zone")
                    self.canvas.tag_lower("day1_zone", "boss_items")
                    f1 = max(14, int(32 * self.scale))
                    f2 = max(12, int(28 * self.scale))
                    self.canvas.create_text(sx2, sy2, text="▼", font=("Helvetica", f1),
                                            fill="black", tags="day1_marker")
                    self.canvas.create_text(sx2, sy2, text="▼", font=("Helvetica", f2),
                                            fill="deepskyblue", tags="day1_marker")

        # --- DAY2安置（UI同期→変更時のみ再描画）---
        day2_selected = current.get("DAY2安地", "")
        if self.day2_pos.get() != day2_selected:
            self.day2_pos.set(day2_selected)

        if getattr(self, "_prev_day2", None) != day2_selected:
            self._prev_day2 = day2_selected
            self.canvas.delete("day2_zone")
            self.canvas.delete("day2_marker")
            if day2_selected:
                pos = self.day1_position_coords.get(day2_selected)
                if pos:
                    x, y = pos
                    cx, cy = self.day1_circle_center.get(day2_selected, (x, y))
                    r = DAY_CIRCLE_RADIUS
                    scx, scy = int(cx * self.scale), int(cy * self.scale)
                    sx, sy = int(x * self.scale), int(y * self.scale)
                    rr = max(8, int(r * self.scale))
                    self.canvas.create_oval(scx - rr, scy - rr, scx + rr, scy + rr,
                                            outline="red", width=2, tags="day2_zone")
                    self.canvas.tag_lower("day2_zone", "boss_items")
                    f1 = max(14, int(32 * self.scale))
                    f2 = max(12, int(28 * self.scale))
                    self.canvas.create_text(sx, sy, text="▼", font=("Helvetica", f1),
                                            fill="black", tags="day2_marker")
                    self.canvas.create_text(sx, sy, text="▼", font=("Helvetica", f2),
                                            fill="red", tags="day2_marker")

        self.update_stats_chart()

    def aggregate_boss_counts_and_patterns(self):
        """
        モード/人数/クエスト一致の全レコードから集計。
        ・counts: ボス名 -> 出現数
        ・pattern_count: 数値キーに1つ以上ボスが入っているレコード数
        （地変・スタート位置は無視）
        """
        target = (self.mode.get(), str(self.players.get()), self.quest_name.get())
        counts = Counter()
        pattern_count = 0

        for key, positions in self.state.items():
            parts = key.split("|")
            if len(parts) < 3:
                continue
            if (parts[0], parts[1], parts[2]) != target:
                continue

            # 数値キーで非空のみ
            numeric_names = [v for k, v in positions.items() if str(k).isdigit() and v]
            if not numeric_names:
                continue

            pattern_count += 1
            counts.update(numeric_names)

        return dict(counts), pattern_count

    def update_stats_chart(self):
        """stats_canvas に横棒グラフを描画（出現数の多い順）＋ パターン数表示"""
        self.stats_canvas.delete("all")
        counts, pattern_count = self.aggregate_boss_counts_and_patterns()

        # タイトルに「出現頻度：モード / 人数 /クエスト | パターン数：n」を表示
        if hasattr(self, "stats_title"):
            mode_label = self.mode.get()
            players_label = f"{self.players.get()}人"
            quest_label = self.quest_name.get()
            self.stats_title.config(
                text=f"出現頻度：{mode_label} / {players_label} / {quest_label}  |  パターン数：{pattern_count}"
            )

        # データなし
        if not counts:
            self.stats_canvas.config(height=30)
            self.stats_canvas.create_text(10, 15, anchor="w", text="データなし", font=self.font, fill="gray")
            return

        # 出現数降順→名前昇順
        items = sorted(counts.items(), key=lambda x: (-x[1], x[0]))

        # レイアウト
        self.stats_canvas.update_idletasks()
        width = max(self.stats_canvas.winfo_width(), 300)
        left_label_w = 180
        right_pad = 10
        bar_area_w = max(width - left_label_w - right_pad - 10, 80)
        bar_h = 18
        gap = 4
        top_pad = 6
        height = top_pad + len(items) * (bar_h + gap) + 6
        self.stats_canvas.config(height=height)

        max_count = max(c for _, c in items)

        y = top_pad
        for name, c in items:
            label = f"{boss_number_map.get(name, '')}. {name}"
            self.stats_canvas.create_text(8, y + bar_h/2, anchor="w", text=label, font=self.font)

            w = int(bar_area_w * (c / max_count)) if max_count else 0
            x0 = left_label_w
            x1 = left_label_w + w
            fill = "red" if name in strong_bosses else "black"
            self.stats_canvas.create_rectangle(x0, y, x1, y + bar_h, fill=fill, outline="")
            self.stats_canvas.create_text(x1 + 6, y + bar_h/2, anchor="w", text=str(c), font=self.font)
            y += bar_h + gap

    def clear_all(self):
        key = self.get_key()
        # 現在の状態を undo 用に保存（深いコピー）
        self.undo_state[key] = self.state.get(key, {}).copy()
        # 実際にクリア
        self.state[key] = {}
        self.update_display()

    def undo_clear(self):
        key = self.get_key()
        if key in self.undo_state:
            self.state[key] = self.undo_state[key].copy()
            self.update_display()
            print("元に戻しました。")
        else:
            print("元に戻すデータがありません。")

    def save_state(self):
        try:
            # 並び順（定義順で揃える）
            mode_order    = ["通常", "常夜"]
            players_order = [1, 2, 3]
            quest_order   = quest_names
            # 追加キーは定義の choices をそのまま並び順として使う
            extras_orders = [opt["choices"] for opt in OPTIONAL_KEYS]
            start_order = START_ORDER

            def _idx(val, order_list):
                try:
                    return order_list.index(val)
                except ValueError:
                    return 999

            # --- 旧キーを新キーへ正規化（可変長の追加キーに対応）---
            normalized = {}
            expected_extras = len(OPTIONAL_KEYS)
            for key, positions in self.state.items():
                parts = key.split("|")
                if len(parts) < 4:
                    continue  # 想定外はスキップ
                mode    = parts[0]
                players = parts[1]
                quest   = parts[2]
                start   = parts[-1]
                extras  = parts[3:-1]  # 中間はすべて「追加キー」

                # 欠けていれば空文字で埋め、余っていれば切り落とす
                if len(extras) < expected_extras:
                    extras = extras + [""] * (expected_extras - len(extras))
                elif len(extras) > expected_extras:
                    extras = extras[:expected_extras]

                new_key = "|".join([mode, players, quest, *extras, start])
                normalized[new_key] = positions

            # --- 並べ替え用キー関数（定義順で並べる）---
            def parse_key(k: str):
                parts = k.split("|")
                # 先頭3 + 可変extras + 最後が start
                mode    = parts[0] if len(parts) > 0 else ""
                players = parts[1] if len(parts) > 1 else "0"
                quest   = parts[2] if len(parts) > 2 else ""
                extras  = parts[3:-1] if len(parts) > 4 else []
                start   = parts[-1] if len(parts) >= 4 else ""

                try:
                    players_num = int(players)
                except ValueError:
                    players_num = None

                keys = [
                    _idx(mode, mode_order),
                    _idx(players_num, players_order),
                    _idx(quest, quest_order),
                ]
                # 追加キーを順に比較
                for i, ex_val in enumerate(extras):
                    order_list = extras_orders[i] if i < len(extras_orders) else []
                    keys.append(_idx(ex_val, order_list))
                # スタート位置
                keys.append(_idx(start, start_order))
                # 最後に元文字列でタイブレーク（安定）
                keys.extend([mode, players, quest, *extras, start])
                return tuple(keys)

            # --- トップレベルを希望順に並び替え ---
            ordered_keys = sorted(normalized.keys(), key=parse_key)

            # --- 各キー配下は既存の規則でソート（数値昇順→非数値）---
            sorted_state = {}
            for k in ordered_keys:
                positions = normalized.get(k, {}) or {}
                sorted_state[k] = self._sort_positions(positions) if isinstance(positions, dict) else {}

            save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), SAVE_FILE)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(sorted_state, f, ensure_ascii=False, indent=2)

            print(f"保存成功: {save_path}")
        except Exception as e:
            print(f"保存失敗: {e}")

    def load_state(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), SAVE_FILE)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 新形式 {"version": x, "state": {...}} を優先
            if isinstance(data, dict) and "state" in data and isinstance(data["state"], dict):
                return data["state"]

            # 旧形式：そのまま（key -> positions の辞書）
            if isinstance(data, dict):
                return data

            # 想定外形式
            return {}
        except Exception as e:
            # 破損時は .bak を試す
            bak_path = path + ".bak"
            if os.path.exists(bak_path):
                try:
                    with open(bak_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict) and "state" in data and isinstance(data["state"], dict):
                        print("バックアップから復旧しました。")
                        return data["state"]
                    if isinstance(data, dict):
                        print("バックアップ（旧形式）から復旧しました。")
                        return data
                except Exception:
                    pass
            print(f"読み込み失敗: {e}")
            return {}

    def on_day1_change(self, value):
        key = self.get_key()
        if key not in self.state:
            self.state[key] = {}
        if value:
            self.state[key]["DAY1安地"] = value
        else:
            self.state[key].pop("DAY1安地", None)
        self.update_display()

    def on_day2_change(self, value):
        key = self.get_key()
        if key not in self.state:
            self.state[key] = {}
        if value:
            self.state[key]["DAY2安地"] = value
        else:
            self.state[key].pop("DAY2安地", None)
        self.update_display()

    def update_readonly_ui(self):
        ro = self.readonly.get()
        # キー変更は許可（mode / players / quest / start_pos）は触らない
        # それ以外（DAY1/2安置、保存/解除/元に戻す）は無効化
        state = "disabled" if ro else "normal"

        # DAY1 / DAY2 ドロップダウン
        if hasattr(self, "day1_menu"):
            self.day1_menu.config(state=state)
        if hasattr(self, "day2_menu"):
            self.day2_menu.config(state=state)

        # 操作ボタン
        if hasattr(self, "btn_save"):
            self.btn_save.config(state=state)
        if hasattr(self, "btn_clear"):
            self.btn_clear.config(state=state)
        if hasattr(self, "btn_undo"):
            self.btn_undo.config(state=state)

        # --- ヘルパー：位置ディクショナリを安定ソート ---
    def _sort_positions(self, positions: dict) -> dict:
        # 数値キー/非数値キーに分離
        numeric = {k: v for k, v in positions.items() if str(k).isdigit()}
        others  = {k: v for k, v in positions.items() if not str(k).isdigit()}

        # 数値キーは昇順
        sorted_numeric = dict(sorted(numeric.items(), key=lambda kv: int(kv[0])))

        # 非数値は指定順（NON_NUMERIC_ORDER）→残りは名前順
        ordered_others = {k: others[k] for k in NON_NUMERIC_ORDER if k in others}
        for k in sorted(k for k in others if k not in ordered_others):
            ordered_others[k] = others[k]

        return {**sorted_numeric, **ordered_others}

    def on_compact_toggle(self):
        """コンパクト表示トグル:
        ON  -> 左列(ボスリスト)を隠して、キャンバス画像幅 + 境界幅 でウィンドウをリサイズ
        OFF -> 左列を戻す前に、キャンバス画像幅 + 境界幅 + 左列幅 でウィンドウをリサイズ
        """
        # 現在のキャンバス画像サイズ
        self.root.update_idletasks()
        img_w = self.tk_img.width()
        img_h = self.tk_img.height()

        if self.compact.get():
            # --- ON: 左列を隠す前に幅を保存 ---
            self.root.update_idletasks()
            w = self.right_left.winfo_width()
            if not w:
                w = self.right_left.winfo_reqwidth()
            self._left_col_width = w

            # 隠す
            if self.right_left.winfo_ismapped():
                self.right_left.pack_forget()

            # リサイズ
            new_w = img_w + self.compact_boundary
            self.root.geometry(f"{new_w}x{img_h}")
            self.root.update_idletasks()

        else:
            # --- OFF: まずリサイズ ---
            left_w = self._left_col_width or self.right_left.winfo_reqwidth()
            new_w = img_w + self.compact_boundary + left_w + 10
            self.root.geometry(f"{new_w}x{img_h}")
            self.root.update_idletasks()

            # その後、左列を元の位置に復帰（ボタン列の左に確実に戻す）
            if not self.right_left.winfo_ismapped():
                self.right_left.pack(
                    side=tk.LEFT, anchor="n", padx=(0, 10),
                    before=self.right_right
                )

if __name__ == "__main__":
    root = tk.Tk()
    app = BossMapApp(root)
    root.mainloop()
