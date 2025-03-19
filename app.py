from flask import Flask, request, jsonify
import requests
import json
import sys
import tkinter as tk
from tkinter import ttk
import threading
import queue
import time

app = Flask(__name__)
command_queue = queue.Queue()
last_command = None

# Ollama API endpoint
OLLAMA_API_URL = "http://localhost:11434/api/generate"

def clean_response(response):
    # 先去除思考過程
    response = extract_final_response(response)
    
    # 定義動作及其相關詞彙的映射
    command_mappings = {
        "向左移動": ["向左移動", "往左移動", "左移", "向左走", "往左走"],
        "向右移動": ["向右移動", "往右移動", "右移", "向右走", "往右走"],
        "向左旋轉": ["向左旋轉", "往左轉", "左轉", "逆時針轉"],
        "向右旋轉": ["向右旋轉", "往右轉", "右轉", "順時針轉"],
        "放大": ["放大", "變大", "身體變大"],
        "縮小": ["縮小", "變小", "身體變小"],
        "跳躍": ["跳躍", "跳起來", "跳上去", "往上跳", "跳", "跳高"],
        "蹲下": ["蹲下", "下蹲", "蹲低", "趴下"],
        "伸展": ["伸展", "伸直", "站起來", "回復原狀"]
    }
    
    found_commands = []
    response = response.lower()  # 轉換為小寫以進行比對
    
    # 檢查每個標準命令及其變體
    for standard_command, variants in command_mappings.items():
        for variant in variants:
            if variant in response:
                if standard_command not in found_commands:
                    found_commands.append(standard_command)
                break
    
    return found_commands

def extract_final_response(text):
    """去除AI的思考過程，只保留最後的實際回應"""
    # 如果包含<think>標記，取最後一個非思考的部分
    if "<think>" in text:
        parts = text.split("</think>")
        return parts[-1].strip()
    return text.strip()

class AICommandWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI 控制面板")
        self.root.geometry("400x300")
        
        # 設置樣式
        style = ttk.Style()
        style.configure('TButton', padding=5)
        style.configure('TEntry', padding=5)
        
        # 創建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 輸入框
        ttk.Label(main_frame, text="請輸入指令:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.input_field = ttk.Entry(main_frame, width=40)
        self.input_field.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 發送按鈕
        self.send_button = ttk.Button(main_frame, text="發送", command=self.send_command)
        self.send_button.grid(row=2, column=0, columnspan=2, pady=10)
        
        # 回應顯示區域
        ttk.Label(main_frame, text="AI回應:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.response_text = tk.Text(main_frame, height=8, width=40)
        self.response_text.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 狀態標籤
        self.status_label = ttk.Label(main_frame, text="就緒")
        self.status_label.grid(row=5, column=0, columnspan=2, pady=5)
        
        # 綁定Enter鍵
        self.input_field.bind('<Return>', lambda e: self.send_command())
        
    def send_command(self):
        command = self.input_field.get().strip()
        if command:
            self.status_label.config(text="處理中...")
            self.send_button.config(state='disabled')
            self.input_field.config(state='disabled')
            
            # 直接處理命令
            self.process_command(command)
            
            # 清空輸入框
            self.input_field.delete(0, tk.END)
    
    def process_command(self, command):
        try:
            system_prompt = """你是一個AI助手，同時也是一隻貓咪。請使用以下標準動作命令來描述你的行為，必須完全按照下列命令格式：

標準命令列表：
- "向左移動"
- "向右移動"
- "向左旋轉"
- "向右旋轉"
- "放大"
- "縮小"
- "跳躍"
- "蹲下"
- "伸展"

重要規則：
1. 請只使用上述標準命令，不要使用其他相似表達
2. 每個動作都必須使用完整的標準命令格式
3. 可以組合多個標準命令，但每個命令都要完整表達

正確示例：
"我向左移動，然後跳躍，最後伸展。"

錯誤示例：
"我往左跑，跳起來，伸直身體。" (使用了非標準表達)

請嚴格遵守這些規則來描述你的行為。"""
            
            full_prompt = f"{system_prompt}\n\n用戶請求：{command}"
            
            ollama_request = {
                "model": "deepseek-r1:latest",
                "prompt": full_prompt,
                "stream": False
            }
            
            response = requests.post(OLLAMA_API_URL, json=ollama_request)
            
            if response.status_code == 200:
                response_data = response.json()
                generated_text = response_data.get('response', '')
                commands = clean_response(generated_text)
                
                # 更新Tkinter窗口，顯示完整的AI回應
                self.update_response(f"AI回應：{generated_text}\n\n識別到的命令：{', '.join(commands)}")
                
                # 將所有命令依序放入隊列
                for cmd in commands:
                    command_queue.put(cmd)
            else:
                self.update_response(f"錯誤: Ollama返回狀態碼 {response.status_code}")
                
        except Exception as e:
            self.update_response(f"錯誤: {str(e)}")
    
    def update_response(self, response):
        self.response_text.delete(1.0, tk.END)
        self.response_text.insert(tk.END, response)
        self.status_label.config(text="就緒")
        self.send_button.config(state='normal')
        self.input_field.config(state='normal')
        self.input_field.focus()
    
    def run(self):
        self.root.mainloop()

# 創建Tkinter窗口
command_window = AICommandWindow()

@app.route('/generate', methods=['POST'])
def generate_response():
    global last_command
    try:
        data = request.json
        prompt = data.get('prompt', '')
        print(f"Received prompt: {prompt}")
        
        # 如果是Unity的定期檢查請求
        if prompt == "check":
            # 檢查是否有新命令
            try:
                command = command_queue.get_nowait()
                last_command = command
                return jsonify({
                    'success': True,
                    'response': command
                })
            except queue.Empty:
                # 沒有新命令，返回最後一個命令或空字符串
                return jsonify({
                    'success': True,
                    'response': last_command if last_command else ""
                })
        
        return jsonify({
            'success': True,
            'response': ""
        })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def run_flask():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    print("Starting Flask server...")
    print("Make sure Ollama is running on http://localhost:11434")
    
    # 在新線程中運行Flask服務器
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # 在主線程中運行Tkinter窗口
    command_window.run()
