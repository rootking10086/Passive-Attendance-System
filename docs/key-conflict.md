# SSH 密钥冲突解决

当 SSH 连接出现 `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED` 时，清除旧的密钥缓存:

```bash
ssh-keygen -R 192.168.12.1
```
