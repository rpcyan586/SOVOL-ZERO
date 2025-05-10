from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.route('/scan_wifi', methods=['GET'])
def scan_wifi():
    # 获取 SSID、信号强度、加密方式
    result = subprocess.getoutput("nmcli -t -f SSID,SIGNAL,SECURITY device wifi list")
    wifi_list = []
    for line in result.strip().split('\n'):
        if line:
            parts = line.split(':')
            if len(parts) >= 3:
                ssid = parts[0] or "<隐藏网络>"
                signal = parts[1]
                security = parts[2]
                wifi_list.append({
                    "ssid": ssid,
                    "signal": int(signal),
                    "security": security
                })

    # 按信号强度从高到底排序
    wifi_list.sort(key=lambda x: x['signal'], reverse=True)
    return jsonify(wifi_list)

@app.route('/connect_wifi', methods=['POST'])
def connect_wifi():
    data = request.json
    ssid = data.get('ssid')
    password = data.get('password')
    cmd = f"nmcli device wifi connect '{ssid}' password '{password}'"
    result = subprocess.getoutput(cmd)
    return jsonify({'result': result})

@app.route('/get_ip', methods=['GET'])
def get_ip():
    try:
        result = subprocess.getoutput("ip -4 addr show wlan0 | grep -oP '(?<=inet\\s)\\d+(\\.\\d+){3}'")
        ip_address = result.strip()
        if ip_address:
            return jsonify({'ip': ip_address})
        else:
            return jsonify({'error': 'No IP found on wlan0'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        

@app.route('/disconnect_wifi', methods=['POST'])
def disconnect_wifi():
    try:
        # 获取当前连接的 WiFi 名称
        result = subprocess.run(['nmcli', '-t', '-f', 'active,ssid', 'dev', 'wifi'], 
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        current_ssid = None
        for line in result.stdout.strip().split('\n'):
            if line.startswith('yes:'):
                current_ssid = line.split(':')[1]
                break

        if not current_ssid:
            return jsonify({"status": "error", "message": "No active WiFi connection found."}), 404

        # 断开连接
        disconnect_result = subprocess.run(['nmcli', 'con', 'down', current_ssid],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if disconnect_result.returncode != 0:
            return jsonify({"status": "error", "message": disconnect_result.stderr.strip()}), 500

        return jsonify({"status": "success", "message": f"Disconnected from {current_ssid}."})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
        

@app.route('/networkInterface', methods=['GET'])
def network_interface():
    try:
        result = subprocess.run(['ip', 'link', 'show', 'wlan0'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            return jsonify({
                "status": "error",
                "message": result.stderr.strip()
            }), 500

        return jsonify({
            "status": "success",
            "message": result.stdout.strip()
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/interfaceStatus', methods=['GET'])
def interface_status():
    try:
        result = subprocess.run(['iw', 'dev', 'wlan0', 'info'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            return jsonify({
                "status": "error",
                "message": result.stderr.strip()
            }), 500

        return jsonify({
            "status": "success",
            "message": result.stdout.strip()
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/activeConnections', methods=['GET'])
def active_connections():
    try:
        result = subprocess.run(['nmcli', 'device', 'status'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            return jsonify({
                "status": "error",
                "message": result.stderr.strip()
            }), 500

        return jsonify({
            "status": "success",
            "message": result.stdout.strip()
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/linkStatus', methods=['GET'])
def link_status():
    try:
        result = subprocess.run(['iw', 'wlan0', 'link'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            return jsonify({
                "status": "error",
                "message": result.stderr.strip()
            }), 500

        return jsonify({
            "status": "success",
            "message": result.stdout.strip()
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

ALLOWED_COMMANDS = ('nmcli', 'ip', 'iw', 'ifconfig', 'ping', 'iwconfig')

@app.route('/command', methods=['POST'])
def exec_command():
    data = request.get_json()
    cmd = data.get("command")

    if not cmd:
        return jsonify({
            "status": "error",
            "message": "No command provided."
        }), 400

    # 检查命令是否以允许的前缀开头
    if not any(cmd.strip().startswith(prefix) for prefix in ALLOWED_COMMANDS):
        return jsonify({
            "status": "error",
            "message": "Command not supported."
        }), 403

    try:
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return jsonify({
            "status": "success" if result.returncode == 0 else "error",
            "message": result.stdout.strip()
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({
        "status": "success",
        "message": "OK"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

