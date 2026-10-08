#!/usr/bin/env bash
# 从零安装后，用真实客户端连一次，证明"装完真的能用"。
set -u
CF=/etc/hysteria/config.yaml
HY="$(command -v hysteria || echo /usr/local/bin/hysteria)"

#🔴 端口解析不要用 `tr -d ' :'` —— 它会连"listen" 里的字母一起删掉，
#    粘成 "listen15067" 这种垃圾。用 sed 只取冒号后的数字。
PORT=$(sed -n 's/^listen:[[:space:]]*[:0-9]*//p' "$CF" | head -1)
[[ "$PORT" =~ ^[0-9]+$ ]] || PORT=$(grep -E '^listen:' "$CF" | head -1 | sed 's/.*://')
echo "端口=$PORT"
PW=$(awk '/^auth:/{f=1;next} f&&/password:/{gsub(/[" ]/,"",$2);print $2;exit}' "$CF")
OP=$(awk '/^obfs:/{f=1;next} f&&/password:/{gsub(/[" ]/,"",$2);print $2;exit}' "$CF")
echo "密码长度=${#PW}  obfs长度=${#OP}"
if [ -z "$PORT" ] || [ -z "$PW" ] || [ -z "$OP" ]; then
    echo "解析配置失败（port=[$PORT]）"
    exit 1
fi

cat > /tmp/c.yaml <<YEOF
server: 127.0.0.1:$PORT
auth: "$PW"
tls:
  sni: www.bing.com
  insecure: true
obfs:
  type: salamander
  salamander:
    password: "$OP"
socks5:
  listen: 127.0.0.1:18080
YEOF

"$HY" client -c /tmp/c.yaml > /tmp/cl.log 2>&1 &
CPID=$!
sleep 8
echo "--- 客户端日志 ---"
head -5 /tmp/cl.log
echo "--- 经代理访问外网 ---"
CODE=$(curl -s -x socks5h://127.0.0.1:18080 -o /dev/null -w '%{http_code}' -m 25 https://www.bing.com 2>/dev/null)
echo "  HTTP $CODE"
# 🔴 不能只认200：bing/部分站点会返回 3xx 重定向，那是**连通**的证据。
# 真正要判断的是「代理是否真的把请求送出去了」——
# 所以以2xx/3xx 都算通，000 才是真的不通。
case "$CODE" in
    000|"") echo "  ❌ 新装节点不通（代理无响应）" ;;
    2*|3*)  echo "  ✅ 新装节点可用（代理转发成功，HTTP $CODE）" ;;
    *)     echo "  ⚠️  连通但状态异常 HTTP $CODE（可能被目标站拒绝）" ;;
esac
kill $CPID 2>/dev/null
exit 0