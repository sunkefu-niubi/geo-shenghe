#!/bin/bash
# 门店GEO官网一键部署：重建站点 → 上传 COS → 服务器拉取上线 → GitHub 备份 → 在线校验
# 用法：bash tools/deploy.sh
# 备案通过换绑正式域名后：把 SITE 改成 https://域名，重跑一次即可（sitemap/canonical 会跟着变）
set -e

SITE="http://82.156.182.65:8088"
BUCKET="shengyatai-web-1428215718"
COS_BASE="https://$BUCKET.cos.ap-beijing.myqcloud.com"
INSTANCE="lhins-5ta2e7fo"
DIR="$(cd "$(dirname "$0")/.." && pwd)"
COSCLI="$DIR/tools/coscli"
TCCLI="/Users/sunkefu/Library/Application Support/kimi-desktop/daimon-share/daimon/runtime/python/.venv/bin/tccli"
STAGE=/tmp/geo_deploy
GIT_REMOTE="git@github.com:sunkefu-niubi/geo-shenghe.git"

echo "== 1/5 重建站点 =="
cd "$DIR"
SITE_URL="$SITE" python3 tools/build_content.py
if grep -rq "__SITE_URL__" index.html xiaoqu/ baogao/ 2>/dev/null; then
  sed -i '' "s|__SITE_URL__|$SITE|g" index.html xiaoqu/*.html baogao/*.html
fi
if grep -rq "__SITE_URL__" index.html xiaoqu/ baogao/ 2>/dev/null; then
  echo "!! 占位符未替换干净，中止"; exit 1
fi

echo "== 2/5 收集部署文件 + 生成清单 =="
rm -rf "$STAGE" && mkdir -p "$STAGE/.deploy"
cp index.html 404.html robots.txt sitemap.xml llms.txt "$STAGE"/
cp -R assets xiaoqu baogao "$STAGE"/
( cd "$STAGE" && find . -type f ! -path "./.deploy/*" | sed 's|^\./||' | sort > .deploy/manifest.txt )

echo "== 3/5 上传 COS =="
"$COSCLI" cp -r "$STAGE"/ "cos://$BUCKET/" 2>&1 | tail -1

echo "== 4/5 服务器拉取上线 =="
# 服务器上的 /root/geo_pull.sh 按清单从 COS 拉文件到 /var/www/geo 并重载 nginx
# 注意：tccli tat RunCommand 的 --Content 必须是命令整体的 base64
CMD_B64=$(printf 'bash /root/geo_pull.sh' | base64)
INV=$("$TCCLI" tat RunCommand --InstanceIds "[\"$INSTANCE\"]" \
  --CommandType SHELL --Username root --Timeout 300 \
  --Content "$CMD_B64" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['InvocationId'])")
echo "  TAT 任务: $INV"
sleep 8
OUT=$("$TCCLI" tat DescribeInvocationTasks \
  --Filters "[{\"Name\":\"invocation-id\",\"Values\":[\"$INV\"]}]" --HideOutput false \
  | python3 -c "import json,sys,base64; t=json.load(sys.stdin)['InvocationTaskSet'][0]; print(t['TaskStatus']); print(base64.b64decode(t['TaskResult']['Output']).decode('utf-8','replace'))")
echo "$OUT" | tail -3
echo "$OUT" | grep -q "DEPLOY_OK" || { echo "!! 服务器拉取失败，中止"; exit 1; }

echo "== 5/5 GitHub 备份 + 在线校验 =="
cd "$DIR"
git add -A
git commit -m "月度更新 $(date +%Y-%m-%d)" 2>/dev/null || echo "  (无本地变更)"
git push origin HEAD:main 2>&1 | tail -1 || echo "!! GitHub 推送失败（不阻断上线）"

FAIL=0
for p in "/" "/xiaoqu/" "/baogao/" "/robots.txt" "/sitemap.xml" "/llms.txt"; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$SITE$p")
  echo "  $CODE $p"
  [ "$CODE" = "200" ] || FAIL=1
done
[ "$FAIL" = "0" ] && echo "部署完成 ✓ $SITE" || { echo "有页面异常，请检查"; exit 1; }
