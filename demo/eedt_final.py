import tkinter as tk
import numpy as np
import time

class EEDTUltraSilky:
    def __init__(self, dt=0.015):
        """
        EEDT Ultra Silky: ラグゼロかつ「極上の滑らかさ」重視のチューニング
        """
        self.dt = dt
        self.x = np.zeros(4)
        self.P = np.eye(4) * 100.0
        
        # 物理モデル: 等速
        self.F = np.array([
            [1, dt, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, dt],
            [0, 0, 0, 1]
        ])
        self.H = np.array([
            [1, 0, 0, 0],
            [0, 0, 1, 0]
        ])
        
        # ★ここが変更点: "Silky Smooth" チューニング★
        # R (観測ノイズ) を大きくして、手ブレを強力に無視する
        self.R = np.eye(2) * 100.0  
        
        # Q (プロセスノイズ) のベースを極小にして、基本は物理法則に従う
        self.Q = np.eye(4) * 0.001   
        
        self.first_run = True

    def reset(self, mx, my):
        self.x = np.array([mx, 0, my, 0])
        self.P = np.eye(4) * 100.0
        self.first_run = False

    def update(self, mx, my):
        if self.first_run:
            self.reset(mx, my)
            return mx, my, "INIT", 0.0

        # 1. Prediction
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q

        # 2. Adaptive Tuning
        z = np.array([mx, my])
        y_residual = z - (self.H @ self.x)
        err = np.linalg.norm(y_residual)
        
        # ★変更点: 感度の上がり方をマイルドにする★
        # 誤差が小さい時は反応せず、大きく動いた時だけグッと加速する曲線
        adaptive_scale = 0.001 + min((err ** 2) * 0.2, 80.0)
        self.Q = np.eye(4) * adaptive_scale

        # 3. Measurement Update
        S = self.H @ self.P @ self.H.T + self.R
        try:
            K = self.P @ self.H.T @ np.linalg.inv(S)
        except np.linalg.LinAlgError:
            return self.x[0], self.x[2], "⚠️ SAFETY", 0.0

        self.x = self.x + K @ y_residual
        self.P = (np.eye(4) - K @ self.H) @ self.P
        
        # 4. Future Prediction Boost
        # 滑らかにした分、ラグが出やすいので先読み時間を少し増やす
        lookahead_time = 0.08 # 60ms -> 80ms
        
        future_x = self.x[0] + self.x[1] * lookahead_time
        future_y = self.x[2] + self.x[3] * lookahead_time
        
        mode = "🚀 FAST" if adaptive_scale > 10 else "✨ SILKY"
        
        return future_x, future_y, mode, lookahead_time

class MouseAppSilky:
    def __init__(self, root):
        self.root = root
        self.root.title("EEDT Ultra: Silky Smooth Edition")
        self.root.geometry("900x700")
        self.root.configure(bg="#111")
        
        self.canvas = tk.Canvas(root, bg="black", width=900, height=700, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.stabilizer = EEDTUltraSilky()
        self.is_drawing = False
        self.prev_raw = None
        self.prev_stab = None
        
        self.info_text = self.canvas.create_text(20, 30, text="Status: Ready", fill="white", font=("Consolas", 14), anchor="w")
        self.sub_text = self.canvas.create_text(20, 55, text="", fill="gray", font=("Consolas", 10), anchor="w")
        self.canvas.create_text(880, 30, text="L-Click: Draw | R-Click: Reset", fill="gray", font=("Consolas", 10), anchor="e")

        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.drawing)
        self.canvas.bind("<ButtonRelease-1>", self.stop_draw)
        self.canvas.bind("<Button-3>", self.reset_canvas)

    def start_draw(self, event):
        self.is_drawing = True
        self.prev_raw = (event.x, event.y)
        self.prev_stab = (event.x, event.y)
        self.stabilizer.reset(event.x, event.y)

    def stop_draw(self, event):
        self.is_drawing = False
        self.prev_raw = None
        self.prev_stab = None

    def reset_canvas(self, event):
        self.canvas.delete("lines")
        self.stabilizer = EEDTUltraSilky()
        self.canvas.itemconfig(self.info_text, text="Status: Reset", fill="white")

    def drawing(self, event):
        if not self.is_drawing: return
        x, y = event.x, event.y
        
        sx, sy, mode, lat = self.stabilizer.update(x, y)
        
        color = "#00ffff" if "FAST" in mode else "#00ff00"
        self.canvas.itemconfig(self.info_text, text=f"MODE: {mode}", fill=color)
        self.canvas.itemconfig(self.sub_text, text=f"Lookahead: {lat*1000:.0f}ms | Smoothness: {self.stabilizer.R[0,0]:.0f}")
        
        if self.prev_raw:
            self.canvas.create_line(self.prev_raw[0], self.prev_raw[1], x, y, 
                                  fill="#ff3333", width=1, dash=(2, 4), tag="lines")
            self.canvas.create_line(self.prev_stab[0], self.prev_stab[1], sx, sy, 
                                  fill=color, width=3, capstyle=tk.ROUND, tag="lines")
            
        self.prev_raw = (x, y)
        self.prev_stab = (sx, sy)

if __name__ == "__main__":
    root = tk.Tk()
    app = MouseAppSilky(root)
    root.mainloop()