<?php
$wifi_list = [];

// 扫描附近的 Wi-Fi 热点
exec("sudo iwlist wlan0 scan | grep 'ESSID'", $scan_output);

foreach ($scan_output as $line) {
    if (preg_match('/ESSID:"(.+)"/', $line, $matches)) {
        $ssid = trim($matches[1]);

        // 将类似 \xE6\xB5\x8B\xE8\xAF\x95 转为真实字符
        $ssid = preg_replace_callback('/\\\\x([0-9A-Fa-f]{2})/', function($m) {
            return chr(hexdec($m[1]));
        }, $ssid);

        if ($ssid !== "") {
            $wifi_list[] = $ssid;
        }
    }
}

// 如果用户提交表单
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $ssid = trim($_POST["ssid"]);
    $psk  = trim($_POST["password"]);

    $log_file = "/home/pi/Desktop/log.txt";
    file_put_contents($log_file, "[" . date('Y-m-d H:i:s') . "] 收到配置信息: SSID=$ssid\n", FILE_APPEND);

    $wpa_conf = <<<EOL
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=CN

network={
    ssid="$ssid"
    psk="$psk"
}
EOL;

    if (file_put_contents("/tmp/wifi.conf", $wpa_conf) === false) {
        file_put_contents($log_file, "[" . date('Y-m-d H:i:s') . "] 写入临时 Wi-Fi 配置失败\n", FILE_APPEND);
        echo "<h2>写入配置失败，请检查文件权限</h2>";
        exit;
    }

    // 替换系统 Wi-Fi 配置
    file_put_contents($log_file, "[" . date('Y-m-d H:i:s') . "] 替换系统配置...\n", FILE_APPEND);
    exec("sudo mv /tmp/wifi.conf /etc/wpa_supplicant/wpa_supplicant.conf");

    // 切换为 STA 模式（从热点转为连接 Wi-Fi）
    file_put_contents($log_file, "[" . date('Y-m-d H:i:s') . "] 正在切换至 STA 模式...\n", FILE_APPEND);
    $output_sh = shell_exec("sudo /home/pi/Desktop/net_mode_manager/to_STA_mode.sh 2>&1");
    file_put_contents($log_file, $output_sh, FILE_APPEND);

    // 等待切换完成
    sleep(15);

    exec("sudo /home/pi/Desktop/net_mode_manager/to_STA_mode.sh 2>&1");

    // 打印 shell 脚本输出
    echo "<h3>to_STA_mode.sh 执行输出：</h3><pre>" . htmlspecialchars($output_sh) . "</pre>";

    exec("ping -c 3 www.baidu.com", $output, $code);
    file_put_contents($log_file, "[" . date('Y-m-d H:i:s') . "] ping 结果：" . implode("\n", $output) . "\n", FILE_APPEND);

    echo "<h2>Wi-Fi 配置完成，正在尝试连接网络...</h2>";
    echo "<pre>配置内容:\n\n" . htmlspecialchars($wpa_conf) . "\n\n连接测试：\n" . implode("\n", $output) . "</pre>";

    echo $code === 0 ? "<p>已成功连接到互联网。</p>" : "<p>无法连接，请检查 SSID 和密码。</p>";
    echo '<meta http-equiv="refresh" content="10;url=http://baidu.com">';

    //exec("sudo reboot")
    exit;
}
?>

<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>Wi-Fi 配置</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary-color: #319EEB;
            --background-color: #f4f7f9;
            --text-color: #333;
        }

        body {
            margin: 0;
            padding: 40px 0 20px;
            font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            background-color: var(--background-color);
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .page-title {
            font-size: 30px;
            font-weight: bold;
            color: #000;
            text-align: center;
            margin-bottom: 30px;
        }

        .container {
            background-color: #FFFFFF;
            padding: 30px 40px;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
            width: 100%;
            max-width: 420px;
            box-sizing: border-box;
        }

        label {
            display: block;
            margin: 16px 0 8px;
            color: var(--text-color);
            font-weight: 600;
        }

        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 12px;
            border: 1px solid #ccc;
            border-radius: 6px;
            font-size: 16px;
            box-sizing: border-box;
            transition: border-color 0.3s;
        }

        input[type="submit"] {
            margin-top: 24px;
            width: 100%;
            padding: 14px;
            background-color: var(--primary-color);
            color: white;
            font-size: 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
        }

        .divider {
            margin-top: 30px;
            border-top: 1px solid #ddd;
            padding-top: 16px;
            text-align: center;
            color: #555;
            font-size: 15px;
        }

        .wifi-list {
            margin-top: 10px;
            list-style: none;
            padding: 0;
            color: #444;
        }

        .wifi-list li {
            padding: 8px 0;
            border-bottom: 1px dashed #ccc;
            cursor: pointer;
            transition: background 0.2s;
        }

        .wifi-list li:hover {
            background-color: #f0f0f0;
        }

        @media (max-width: 480px) {
            .container {
                margin: 0 16px;
                padding: 24px;
            }

            .page-title {
                font-size: 24px;
                margin-bottom: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="page-title">配置 Wi-Fi 网络</div>
    <div class="container">
        <form method="post">
            <label for="ssid">SSID：</label>
            <input type="text" id="ssid" name="ssid" required>

            <label for="password">密码：</label>
            <input type="password" id="password" name="password" required>

            <input type="submit" value="保存并连接">
        </form>

        <div class="divider">选择附近的 2.4G Wi-Fi 网络</div>
        <ul class="wifi-list">
            <?php foreach ($wifi_list as $wifi): ?>
                <li onclick="document.getElementById('ssid').value='<?php echo htmlspecialchars($wifi); ?>'">
                    <?php echo htmlspecialchars($wifi); ?>
                </li>
            <?php endforeach; ?>
        </ul>
    </div>
</body>
</html>
