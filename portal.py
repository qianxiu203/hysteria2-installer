"""仅监听回环地址；公网 TLS 由 Hysteria 的 masquerade proxy 提供。
采用现代轻奢 Tab 导航系统，解耦节点连接、多用户管理（支持 IP 限制与实时流量统计）与集群 API 凭据。
"""
import base64
import hashlib
import hmac
import html
import json
import re
import secrets
import subprocess
import sys
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, quote, urlencode


STYLE = """
:root{color-scheme:light;--ink:#122b31;--muted:#667c81;--line:#dce7e6;--accent:#087f74;--accent-hover:#066960;--danger:#cf3c3c;--danger-bg:#fdf2f2;--brand-bg:#eaf5ef;--card-bg:#ffffff}
*{box-sizing:border-box}body{margin:0;background:#f3f7f6;color:var(--ink);font:15px/1.6 system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
main{max-width:1160px;margin:auto;padding:32px 28px 48px}.topbar{display:flex;justify-content:space-between;align-items:center;padding-bottom:24px}
.brand{font-weight:800;letter-spacing:.04em;display:flex;gap:10px;align-items:center}.logo{background:var(--ink);color:white;border-radius:12px;padding:7px 12px;font-size:17px}.private{font-size:12px;color:var(--accent);border:1px solid #c3ddd5;border-radius:30px;padding:5px 12px;background:#eaf5ef}
.eyebrow{font-size:11px;letter-spacing:.16em;font-weight:750;color:var(--accent)}h1{font-size:32px;letter-spacing:-.04em;margin:6px 0}h2{font-size:18px;margin:0 0 4px}p{margin:0;color:var(--muted)}.hero{margin-bottom:24px}.hero p{font-size:14px}

/* Tab 导航容器 */
.tab-bar{display:flex;gap:8px;border-bottom:2px solid var(--line);margin-bottom:26px;overflow-x:auto;padding-bottom:2px}
.tab-btn{display:inline-flex;align-items:center;gap:8px;padding:11px 18px;border:none;background:none;color:var(--muted);font-size:14px;font-weight:700;cursor:pointer;border-radius:10px 10px 0 0;position:relative;transition:all .18s ease;white-space:nowrap}
.tab-btn:hover{color:var(--ink);background:#ebf3f1}
.tab-btn.active{color:var(--accent);background:#fff}
.tab-btn.active:after{content:'';position:absolute;bottom:-2px;left:0;right:0;height:2px;background:var(--accent)}
.tab-pane{display:none}
.tab-pane.active{display:block;animation:fadeIn .2s ease-out}
@keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}

/* 卡片与网格 */
.layout{display:grid;grid-template-columns:320px minmax(0,1fr);gap:22px;align-items:start}
.card{background:#fff;border:1px solid var(--line);border-radius:20px;padding:24px;box-shadow:0 5px 22px #183f3505}
.qr-card{text-align:center}.qr-frame{background:#fff;border:1px solid var(--line);border-radius:16px;padding:14px;margin:20px 0}.qr-frame img{display:block;width:100%;height:auto}
.hint{font-size:12px}.tags{display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin-top:18px}.tag{background:#f0f5f4;color:#526a70;border-radius:6px;padding:3px 8px;font-size:11px}
.stack{display:grid;gap:18px}.card-head{display:flex;gap:14px;align-items:center;margin-bottom:16px}.step{display:grid;place-items:center;flex:0 0 38px;height:38px;border-radius:11px;background:#e8f4f0;color:var(--accent);font-weight:750}.card-head p{font-size:12px}
textarea{display:block;width:100%;min-width:0;border:1px solid var(--line);background:#f7faf9;border-radius:12px;padding:14px;color:#35545c;font:12px/1.7 ui-monospace,SFMono-Regular,Consolas,monospace;resize:vertical;overflow-wrap:anywhere}
textarea.link{height:92px}textarea.config{height:290px;margin-top:18px}textarea:focus{outline:2px solid #65b3a5;outline-offset:2px}
.actions{display:flex;gap:10px;align-items:center;margin-top:14px;flex-wrap:wrap}
.button{display:inline-flex;align-items:center;justify-content:center;gap:6px;border:1px solid var(--line);background:white;border-radius:9px;padding:9px 15px;color:var(--ink);text-decoration:none;font:600 12px/1.5 inherit;cursor:pointer}
.button.primary{background:var(--accent);color:white;border-color:var(--accent)}.button.danger{background:var(--danger);color:white;border-color:var(--danger)}.button:hover{filter:brightness(.94)}
.note{font-size:12px;margin-top:12px}.advanced{margin-top:24px}.advanced-title{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}.advanced-title p{font-size:12px}.config-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}
summary{cursor:pointer;font-weight:650;list-style-position:inside}summary span{font-size:11px;font-weight:400;color:var(--muted);margin-left:10px}
.security{margin-top:24px;padding:15px 18px;border:1px solid #d8e6df;border-radius:12px;background:#eaf2ed;color:#4f6a60;font-size:12px}
footer{display:flex;justify-content:space-between;margin-top:32px;color:#879996;font-size:11px}.status{font-size:12px;color:var(--accent)}

/* 多用户与集群专属卡片样式 */
.user-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;flex-wrap:wrap;gap:12px}
.badge-count{background:var(--brand-bg);color:var(--accent);border:1px solid #c3ddd5;border-radius:20px;padding:4px 12px;font-size:12px;font-weight:700}
.switch-box{display:flex;align-items:center;gap:12px;background:#f8fbfb;border:1px solid var(--line);border-radius:14px;padding:16px 20px;margin-bottom:20px;justify-content:space-between;flex-wrap:wrap}
.switch-info{display:flex;flex-direction:column;gap:4px}
.switch-title{font-size:14px;font-weight:700;color:var(--ink);display:flex;align-items:center;gap:8px}
.switch-desc{font-size:12px;color:var(--muted)}
.toggle-btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:8px 18px;border-radius:10px;font-size:13px;font-weight:700;cursor:pointer;border:1px solid transparent;transition:all .15s ease}
.toggle-btn.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.toggle-btn.off{background:#fff;color:var(--muted);border-color:var(--line)}
.toggle-btn:hover{filter:brightness(.92)}
.user-table-wrap{width:100%;overflow-x:auto;border:1px solid var(--line);border-radius:14px;background:#fff}
.user-table{width:100%;border-collapse:collapse;text-align:left;font-size:13px}
.user-table th{background:#f8fbfb;padding:12px 14px;color:var(--muted);font-weight:700;border-bottom:1px solid var(--line);white-space:nowrap}
.user-table td{padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:middle;white-space:nowrap}
.user-table tr:last-child td{border-bottom:none}
.status-pill{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:700}
.status-pill.active{background:#eafaf3;color:#0b8650}
.status-pill.expired{background:#fff1f0;color:#cf3c3c}
.traffic-bar{height:6px;width:90px;background:#e6edec;border-radius:4px;overflow:hidden;margin-top:5px}
.traffic-fill{height:100%;background:var(--accent);border-radius:4px}
.traffic-fill.danger{background:var(--danger)}
.api-box{background:#f7faf9;border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.api-key-code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:13px;color:#284d56;word-break:break-all;margin-top:4px}
.modal-form{display:grid;grid-template-columns:1fr 1fr;gap:16px 20px;background:#f8fbfb;border:1px solid var(--line);border-radius:14px;padding:22px;margin-bottom:20px}
.form-field{display:flex;flex-direction:column;gap:6px}
.form-field-full{grid-column:1/-1}
.form-field label{font-size:13px;font-weight:700;color:var(--ink);display:flex;justify-content:space-between;align-items:center}
.form-field label span{font-weight:400;color:var(--muted);font-size:12px}
.form-field input{height:42px;padding:0 12px;border:1px solid var(--line);border-radius:9px;font-size:13px;background:#fff;outline:none;transition:border-color .15s}
.form-field input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(8,127,116,0.12)}
.form-field small{font-size:11px;color:var(--muted);line-height:1.4;margin-top:2px}
.input-with-action{display:flex;gap:8px}
.input-with-action input{flex:1;min-width:0}
.btn-mini{padding:0 12px;height:42px;background:#eaf5ef;border:1px solid #c3ddd5;color:var(--accent);border-radius:9px;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap;display:inline-flex;align-items:center;justify-content:center;transition:background .15s}
.btn-mini:hover{background:#dbeef7}

@media(max-width:760px){
  main{padding:20px 16px 32px}.topbar{padding-bottom:20px}.layout,.config-grid{grid-template-columns:1fr}.qr-frame{max-width:248px;margin:18px auto}.card{padding:20px}h1{font-size:26px}.advanced-title{display:block}footer{gap:15px;flex-direction:column}.private{font-size:10px}.brand{font-size:13px}
  .login-card{padding:28px 20px;border-radius:20px}
  .tab-btn{padding:9px 12px;font-size:13px}
  .modal-form{grid-template-columns:1fr;gap:14px;padding:16px}
}

/* 登录样式 */
.login-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px 16px;background:radial-gradient(ellipse at top,#eef5f3 0%,#f3f7f6 100%)}
.login-card{width:100%;max-width:420px;background:#fff;border:1px solid var(--line);border-radius:24px;padding:36px 30px;box-shadow:0 12px 36px rgba(18,43,49,0.06)}
.login-brand{text-align:center;margin-bottom:28px}
.login-logo{display:inline-flex;align-items:center;justify-content:center;width:60px;height:60px;background:var(--accent);color:#fff;border-radius:18px;font-size:26px;font-weight:800;box-shadow:0 6px 16px rgba(8,127,116,0.22);margin-bottom:14px}
.login-badge{display:inline-block;font-size:11px;letter-spacing:.14em;font-weight:750;color:var(--accent);text-transform:uppercase;margin-bottom:6px}
.login-title{font-size:24px;letter-spacing:-.03em;color:var(--ink);margin:0 0 6px;font-weight:700}
.login-sub{font-size:13px;color:var(--muted);margin:0}
.login-form{display:grid;gap:18px}
.field-group{display:grid;gap:7px}
.field-label{font-size:13px;font-weight:650;color:var(--ink);display:flex;justify-content:space-between;align-items:center}
.field-input{width:100%;height:44px;padding:0 14px;border:1px solid var(--line);border-radius:11px;background:#f7faf9;color:var(--ink);font-size:14px;transition:all .15s ease}
.field-input:focus{outline:none;border-color:var(--accent);background:#fff;box-shadow:0 0 0 3px rgba(8,127,116,0.12)}
.field-pwd{position:relative}
.field-pwd input{padding-right:68px}
.toggle-pwd{position:absolute;right:8px;top:50%;transform:translateY(-50%);background:none;border:none;color:var(--muted);font-size:12px;font-weight:600;padding:6px 8px;cursor:pointer;border-radius:6px}
.toggle-pwd:hover{color:var(--accent);background:#eef5f3}
.remember-row{display:flex;align-items:center;gap:8px;margin-top:2px}
.remember-row input{accent-color:var(--accent);cursor:pointer;width:15px;height:15px}
.remember-row label{font-size:13px;color:var(--muted);cursor:pointer;user-select:none}
.btn-submit{width:100%;height:46px;background:var(--accent);color:#fff;border:none;border-radius:12px;font-size:14px;font-weight:700;cursor:pointer;transition:all .15s;margin-top:6px;display:flex;align-items:center;justify-content:center}
.btn-submit:hover{background:var(--accent-hover);box-shadow:0 4px 12px rgba(8,127,116,0.2)}
.btn-submit:active{transform:scale(0.99)}
.error-tip{padding:10px 14px;border-radius:10px;background:var(--danger-bg);color:var(--danger);font-size:13px;font-weight:550;display:flex;align-items:center;gap:8px;border:1px solid #f6cfcf}
.login-footer{margin-top:24px;padding-top:18px;border-top:1px solid #edf2f1;font-size:12px;color:var(--muted);line-height:1.6;text-align:center}
.login-footer code{background:#eef4f2;color:#33565f;padding:2px 6px;border-radius:4px;font-family:ui-monospace,SFMono-Regular,Consolas,monospace}

@media(max-width:760px){
  main{padding:20px 16px 32px}.topbar{padding-bottom:20px}.layout,.config-grid{grid-template-columns:1fr}.qr-frame{max-width:248px;margin:18px auto}.card{padding:20px}h1{font-size:26px}.advanced-title{display:block}footer{gap:15px;flex-direction:column}.private{font-size:10px}.brand{font-size:13px}
  .login-card{padding:28px 20px;border-radius:20px}
  .tab-btn{padding:9px 12px;font-size:13px}
}

/* 专属连接弹窗与独立页面样式 */
.modal-backdrop{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(18,43,49,0.48);backdrop-filter:blur(5px);display:none;align-items:center;justify-content:center;z-index:9999;padding:16px}
.modal-backdrop.show{display:flex;animation:fadeIn .15s ease-out}
.modal-card{width:100%;max-width:700px;background:#fff;border:1px solid var(--line);border-radius:22px;padding:26px;box-shadow:0 20px 48px rgba(18,43,49,0.18);max-height:90vh;overflow-y:auto;display:flex;flex-direction:column;gap:16px}
.modal-head{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding-bottom:14px}
.modal-close{background:none;border:none;font-size:24px;color:var(--muted);cursor:pointer;padding:4px 8px;border-radius:6px;line-height:1}
.modal-close:hover{background:#f0f5f4;color:var(--ink)}
.user-connect-grid{display:grid;grid-template-columns:250px minmax(0,1fr);gap:18px;align-items:start}
@media(max-width:660px){.user-connect-grid{grid-template-columns:1fr}}
.user-meta-bar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;background:#f7faf9;padding:10px 14px;border-radius:10px;border:1px solid var(--line);font-size:12px}
"""

SCRIPT = """
function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  const btn = document.querySelector('[data-tab="' + tabId + '"]');
  const pane = document.getElementById('pane-' + tabId);
  if (btn && pane) {
    btn.classList.add('active');
    pane.classList.add('active');
    history.replaceState(null, null, '#' + tabId);
  }
}

document.querySelectorAll('[data-tab]').forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

if (location.hash) {
  const hash = location.hash.substring(1);
  if (document.getElementById('pane-' + hash)) {
    switchTab(hash);
  }
}

function genRandom(targetId, prefix='') {
  const el = document.getElementById(targetId);
  if (!el) return;
  const rand = Array.from(crypto.getRandomValues(new Uint8Array(8))).map(b => b.toString(16).padStart(2, '0')).join('');
  el.value = prefix ? (prefix + '_' + rand.substring(0, 8)) : rand;
}

document.querySelectorAll('[data-gen]').forEach(btn => {
  btn.addEventListener('click', () => {
    genRandom(btn.dataset.gen, btn.dataset.prefix || '');
  });
});

document.querySelectorAll('[data-copy]').forEach(button => {
  button.addEventListener('click', async () => {
    const field = document.getElementById(button.dataset.copy);
    const status = document.getElementById('copy-status');
    try {
      const val = field.value || field.textContent || '';
      await navigator.clipboard.writeText(val);
      if (status) status.textContent = '已复制到剪贴板 ✓';
      button.textContent = '已复制 ✓';
      setTimeout(() => { button.textContent = button.dataset.orig || '复制'; }, 1800);
    } catch (_) {
      if (field.select) { field.focus(); field.select(); }
      if (status) status.textContent = '已选中，请按 Ctrl+C 复制';
    }
  });
});

// 专属连接弹窗逻辑
const uModal = document.getElementById('user-modal');
const uModalTitle = document.getElementById('um-title');
const uModalSub = document.getElementById('um-sub');
const uModalBody = document.getElementById('um-body');
const uModalClose = document.getElementById('um-close');

// WARP 状态与一键开关逻辑
const warpBadge = document.getElementById('warp-badge');
const btnToggleWarp = document.getElementById('btn-toggle-warp');

async function checkWarpStatus() {
  if (!warpBadge || !btnToggleWarp) return;
  try {
    const res = await fetch(location.pathname + 'warp-status', { credentials: 'same-origin' });
    if (!res.ok) return;
    const json = await res.json();
    if (!json.ok) return;
    if (json.enabled) {
      warpBadge.textContent = json.connected ? ('● 运行中 (' + (json.ip || '已连通') + ')') : '● 正在连接 / 异常';
      warpBadge.style.background = json.connected ? '#eaf3de' : '#fff1f0';
      warpBadge.style.color = json.connected ? '#27500a' : '#cf3c3c';
      btnToggleWarp.textContent = '已开启 (点击关闭)';
      btnToggleWarp.className = 'toggle-btn on';
    } else {
      warpBadge.textContent = '○ 已停用 (直连模式)';
      warpBadge.style.background = '#f1efe8';
      warpBadge.style.color = '#5f5e5a';
      btnToggleWarp.textContent = '已关闭 (点击开启)';
      btnToggleWarp.className = 'toggle-btn off';
    }
  } catch (_) {}
}

if (btnToggleWarp) {
  checkWarpStatus();
  btnToggleWarp.addEventListener('click', async () => {
    btnToggleWarp.disabled = true;
    btnToggleWarp.textContent = '正在切换...';
    try {
      const res = await fetch(location.pathname + 'manage-warp', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'action=toggle'
      });
      const json = await res.json();
      if (!json.ok) alert(json.error || '切换失败');
    } catch (e) {
      alert('操作失败: ' + e.message);
    } finally {
      btnToggleWarp.disabled = false;
      checkWarpStatus();
    }
  });
}

function closeUserModal() {
  if (uModal) uModal.classList.remove('show');
}
if (uModalClose) uModalClose.addEventListener('click', closeUserModal);
if (uModal) {
  uModal.addEventListener('click', (e) => {
    if (e.target === uModal) closeUserModal();
  });
}

document.querySelectorAll('.btn-user-connect').forEach(btn => {
  btn.addEventListener('click', async () => {
    const uid = btn.dataset.uid;
    const token = btn.dataset.token;
    const userKey = btn.dataset.key;
    if (!uModal || !uModalBody) return;
    
    uModalTitle.textContent = '用户专属连接: ' + uid;
    uModalSub.textContent = '正在获取专属配置与独立连接页...';
    uModalBody.innerHTML = '<div style="text-align:center;padding:36px;color:var(--muted)">加载专属数据中...</div>';
    uModal.classList.add('show');
    
    try {
      const res = await fetch('/' + token + '/user-config?user_id=' + encodeURIComponent(uid), { credentials: 'same-origin' });
      if (res.status === 401) {
        throw new Error('登录状态已失效，请刷新页面重新登录');
      }
      if (!res.ok) {
        throw new Error('网络请求异常 (HTTP ' + res.status + ')');
      }
      const json = await res.json();
      if (!json.ok) throw new Error(json.error || '加载失败');
      
      uModalSub.textContent = json.note ? ('备注: ' + json.note) : '专属独立配置与下载链接';
      
      const shareUrl = location.origin + '/' + token + '/u/' + encodeURIComponent(uid) + '?k=' + userKey;
      
      let trafficText = (json.traffic_limit > 0) 
        ? ((json.traffic_used / (1024**2)).toFixed(1) + ' MB / ' + (json.traffic_limit / (1024**3)).toFixed(1) + ' GB')
        : ((json.traffic_used / (1024**2)).toFixed(1) + ' MB (不限)');
      let expireText = (json.expires_at < 2000000000) ? new Date(json.expires_at * 1000).toLocaleString() : '永久有效';
      let ipText = (json.ip_limit > 0) ? (json.ip_limit + ' IP') : '不限';
      
      uModalBody.innerHTML = `
        <div class="user-meta-bar">
          <span>📅 到期: <b>${expireText}</b></span>
          <span>📊 流量: <b>${trafficText}</b></span>
          <span>📱 IP限制: <b>${ipText}</b></span>
        </div>
        
        <div style="background:#eaf5ef;border:1px solid #c3ddd5;border-radius:12px;padding:12px 14px">
          <div style="font-size:12px;font-weight:700;color:var(--accent);margin-bottom:6px">🌐 专属独立连接页面 (可直接发给客户):</div>
          <div class="input-with-action">
            <input type="text" id="um-share-url" value="${shareUrl}" readonly style="font-size:12px;height:38px">
            <button class="button primary" style="padding:0 12px;height:38px;font-size:12px" type="button" data-modal-copy="um-share-url">复制页面链接</button>
            <a class="button" style="padding:0 12px;height:38px;font-size:12px" href="${shareUrl}" target="_blank">打开页面 ↗</a>
          </div>
        </div>

        <div class="user-connect-grid">
          <div style="text-align:center;background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px">
            <div style="font-size:12px;font-weight:700;color:var(--ink);margin-bottom:8px">专属二维码扫码导入</div>
            <div class="qr-frame" style="margin:0 auto;max-width:210px;padding:8px">${json.qr_svg || '<p style="color:var(--muted)">二维码生成中...</p>'}</div>
            <div style="font-size:11px;color:var(--muted);margin-top:8px">Shadowrocket / v2rayNG / Nekobox</div>
          </div>
          <div style="display:flex;flex-direction:column;gap:12px">
            <div>
              <div style="font-size:12px;font-weight:700;color:var(--ink);margin-bottom:4px">专属节点直链 (URI):</div>
              <textarea id="um-uri" class="link" style="height:65px;font-size:11px" readonly>${json.uri}</textarea>
              <div style="margin-top:6px;display:flex;gap:8px">
                <button class="button primary" style="padding:6px 14px;font-size:11px" type="button" data-modal-copy="um-uri">复制直链</button>
              </div>
            </div>
            <div>
              <div style="font-size:12px;font-weight:700;color:var(--ink);margin-bottom:4px">Clash / Mihomo 专属订阅链接:</div>
              <div class="input-with-action">
                <input type="text" id="um-clash-sub" value="${location.origin}/${token}/u/${encodeURIComponent(uid)}/clash.yaml?k=${userKey}" readonly style="font-size:11px;height:36px">
                <button class="button primary" style="padding:0 12px;height:36px;font-size:11px" type="button" data-modal-copy="um-clash-sub">复制订阅</button>
                <a class="button" style="padding:0 10px;height:36px;font-size:11px" href="/${token}/u/${encodeURIComponent(uid)}/clash.yaml?k=${userKey}" download="clash-${uid}.yaml">下载 ↓</a>
              </div>
              <details style="margin-top:6px">
                <summary style="font-size:11px;color:var(--muted)">查看/复制配置文本</summary>
                <textarea id="um-clash" class="link" style="height:65px;font-size:10px;margin-top:4px" readonly>${json.clash}</textarea>
                <div style="margin-top:4px"><button class="button" style="padding:2px 8px;font-size:10px" type="button" data-modal-copy="um-clash">复制文本</button></div>
              </details>
            </div>
          </div>
        </div>
      `;
      
      uModalBody.querySelectorAll('[data-modal-copy]').forEach(b => {
        b.addEventListener('click', async () => {
          const target = document.getElementById(b.dataset.modalCopy);
          if (!target) return;
          const text = target.value || target.textContent || '';
          await navigator.clipboard.writeText(text);
          const orig = b.textContent;
          b.textContent = '已复制 ✓';
          setTimeout(() => { b.textContent = orig; }, 1800);
        });
      });
      
    } catch (err) {
      uModalBody.innerHTML = `<div style="text-align:center;padding:24px;color:var(--danger)">加载失败: ${err.message}</div>`;
    }
  });
});
"""

LOGIN_SCRIPT = """
function toggleSecret(id, btn) {
  const el = document.getElementById(id);
  if (el.type === 'password') {
    el.type = 'text';
    btn.textContent = '隐藏';
  } else {
    el.type = 'password';
    btn.textContent = '显示';
  }
}
"""

USER_SCRIPT = """
document.querySelectorAll('[data-copy]').forEach(button => {
  button.addEventListener('click', async () => {
    const field = document.getElementById(button.dataset.copy);
    try {
      const val = field.value || field.textContent || '';
      await navigator.clipboard.writeText(val);
      const orig = button.textContent;
      button.textContent = '已复制 ✓';
      setTimeout(() => { button.textContent = orig; }, 1800);
    } catch (_) {
      if (field.select) { field.focus(); field.select(); }
    }
  });
});
"""


def user_view_key(secret, user_id):
    return hmac.new(str(secret).encode(), f'uv:{user_id}'.encode(), hashlib.sha256).hexdigest()[:16]


def format_bytes(b):
    if b < 1024:
        return f"{b} B"
    elif b < 1024**2:
        return f"{b/1024:.1f} KB"
    elif b < 1024**3:
        return f"{b/1024**2:.2f} MB"
    else:
        return f"{b/1024**3:.2f} GB"


def page_html(m, uri, subscription, clash, sing, users=None, api_key=None, token="", session_secret=""):
    def field(identifier, value, kind="link"):
        return f'<textarea id="{identifier}" class="{kind}" aria-label="{identifier}" readonly spellcheck="false">{html.escape(value)}</textarea>'
    def copy(identifier):
        return f'<button class="button primary" type="button" data-copy="{identifier}" data-orig="复制">复制</button>'
    
    is_insecure = m.get("is_insecure", False)
    server_name = m.get("server_name") or m.get("public_ip", "localhost")
    public_ip = m.get("public_ip", server_name)
    host = public_ip if is_insecure else server_name
    sub_port = m.get("subscription_port", 8443)
    _raw_pin = (m.get("pin_sha256") or "").strip().lower()
    pin_sha256 = _raw_pin if (is_insecure and len(_raw_pin) == 64
                              and all(c in "0123456789abcdef" for c in _raw_pin)) else ""
    pin_block = (f'<div class="api-box"><div><div style="font-size:11px;color:var(--muted);font-weight:700">'
                 f'自签证书 SHA-256 指纹 (HEX · 已写入直链 pinSHA256 / Xray 的 pinnedPeerCertSha256)</div>'
                 f'<div class="api-key-code" id="api-pin-val">{html.escape(pin_sha256)}</div></div>'
                 f'<button class="button" type="button" data-copy="api-pin-val" data-orig="复制指纹">复制指纹</button></div>') if pin_sha256 else ''
    listen_port = m.get("listen_port", 19984)
    obfs_pw = m.get("obfs_password", "")
    users = users or {}
    now_ts = int(time.time())
    
    user_rows = []
    active_count = 0
    total_used_bytes = 0

    for uid, u in sorted(users.items(), key=lambda x: x[1].get("created_at", 0), reverse=True):
        used_bytes = int(u.get("used_bytes", 0))
        limit_bytes = int(u.get("limit_bytes", 0))
        total_used_bytes += used_bytes

        is_traffic_ok = limit_bytes == 0 or used_bytes < limit_bytes
        is_time_ok = u.get("expires_at", 0) >= now_ts
        is_active = u.get("status") == "active" and is_time_ok and is_traffic_ok

        if is_active:
            active_count += 1

        if not is_traffic_ok:
            status_html = '<span class="status-pill expired">流量超额</span>'
        elif not is_time_ok:
            status_html = '<span class="status-pill expired">已到期</span>'
        elif u.get("status") != "active":
            status_html = '<span class="status-pill expired">已停用</span>'
        else:
            status_html = '<span class="status-pill active">正常</span>'

        expires_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(u.get("expires_at", 0))) if u.get("expires_at", 0) < 2000000000 else "永久有效"
        ip_limit = u.get("ip_limit", 0)
        ip_limit_str = f"{ip_limit} IP" if ip_limit > 0 else "不限"
        online_ips = len(u.get("online_ips", {}))
        online_str = f'<span class="badge-count" style="font-size:11px;">{online_ips} 在线</span>' if online_ips > 0 else '<span style="color:var(--muted)">0</span>'
        
        # 流量展示与进度条
        if limit_bytes > 0:
            percent = min(round((used_bytes / limit_bytes) * 100), 100)
            bar_class = "danger" if percent >= 90 else ""
            traffic_display = f"""<div>{format_bytes(used_bytes)} / {format_bytes(limit_bytes)} <span style="font-size:11px;color:var(--muted)">({percent}%)</span></div>
            <div class="traffic-bar"><div class="traffic-fill {bar_class}" style="width:{percent}%"></div></div>"""
        else:
            traffic_display = f"""<div>{format_bytes(used_bytes)} <span style="font-size:11px;color:var(--muted)">(不限)</span></div>"""

        note = u.get("note") or "-"
        user_key = user_view_key(session_secret, uid) if session_secret else ""
        
        user_rows.append(f"""<tr>
          <td><strong>{html.escape(uid)}</strong><div style="font-size:11px;color:var(--muted)">{html.escape(note)}</div></td>
          <td>{status_html}</td>
          <td>{ip_limit_str} ({online_str})</td>
          <td>{traffic_display}</td>
          <td>{expires_str}</td>
          <td><code style="font-size:11px">{html.escape(u.get("password","")[:4] + "****" + u.get("password","")[-4:])}</code></td>
          <td>
            <button class="button primary btn-user-connect" style="padding:4px 10px;font-size:11px;margin-right:6px" type="button" data-uid="{html.escape(uid)}" data-token="{token}" data-key="{user_key}">专属连接</button>
            <form method="POST" action="/{token}/manage-user" style="display:inline" onsubmit="return confirm('确定注销此用户？')">
              <input type="hidden" name="action" value="delete">
              <input type="hidden" name="user_id" value="{html.escape(uid)}">
              <button class="button danger" style="padding:4px 10px;font-size:11px" type="submit">删除</button>
            </form>
          </td>
        </tr>""")

    users_table_html = "".join(user_rows) or '<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:24px">暂无多用户数据</td></tr>'
    obfs_badge = "Salamander" if obfs_pw else "QUIC"
    field_hy2 = field("hy2-link", uri)
    copy_hy2 = copy("hy2-link")
    field_sub = field("clash-subscription", subscription)
    copy_sub = copy("clash-subscription")
    field_clash_cfg = field("clash-config", clash, "config")
    copy_clash_cfg = copy("clash-config")
    field_sing_cfg = field("sing-config", sing, "config")
    copy_sing_cfg = copy("sing-config")

    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>HY2 · 节点与集群中心</title><style>{STYLE}</style></head><body><main>
<nav class="topbar" aria-label="页面标识"><div class="brand"><span class="logo">H₂</span> HYSTERIA <span> / 控制中心</span></div><span class="private">● 集群运行中</span></nav>
<header class="hero"><div class="eyebrow">HYSTERIA 2 NODE DASHBOARD</div><h1>{html.escape(server_name)}</h1><p>官方核心驱动 · 极速 QUIC 代理 · 多用户开户与流量/IP限制</p></header>

<!-- 顶部 Tab 导航栏 -->
<div class="tab-bar">
  <button class="tab-btn active" data-tab="connect">🚀 节点导入 (Connect)</button>
  <button class="tab-btn" data-tab="users">👥 多用户管理 ({active_count}/{len(users)})</button>
  <button class="tab-btn" data-tab="cluster">🔑 通用 REST API 对接</button>
  <button class="tab-btn" data-tab="configs">⚙️ 高级配置</button>
</div>

<!-- Tab 1: 节点连接视图 -->
<div class="tab-pane active" id="pane-connect">
  <div class="layout">
    <section class="card qr-card">
      <div class="eyebrow">QUICK CONNECT</div>
      <h2>主管理员扫码</h2>
      <p class="hint">适用于支持 Hysteria 2 的客户端</p>
      <div class="qr-frame"><img src="qr.svg" alt="HY2 节点导入二维码" width="260" height="260"></div>
      <p class="hint">打开客户端扫描二维码直接导入</p>
      <div class="tags"><span class="tag">Hysteria 2</span><span class="tag">TLS</span><span class="tag">{obfs_badge}</span></div>
    </section>
    <div class="stack">
      <section class="card">
        <div class="card-head"><span class="step">01</span><div><h2>节点直链 (URI)</h2><p>v2rayN / Nekobox / Shadowrocket</p></div></div>
        {field_hy2}
        <div class="actions">{copy_hy2}</div>
        <p class="note">{html.escape(host)} · UDP {int(listen_port)}</p>
      </section>
      <section class="card">
        <div class="card-head"><span class="step">02</span><div><h2>Clash 订阅</h2><p>适用于 Clash Meta / Mihomo 内核</p></div></div>
        {field_sub}
        <div class="actions">{copy_sub}<a class="button" href="clash.yaml" download="clash.yaml">下载配置 ↓</a></div>
        <p class="note">在客户端添加订阅链接即可自动同步。</p>
      </section>
    </div>
  </div>
</div>

<!-- Tab 2: 多用户与流量/IP 限制视图 -->
<div class="tab-pane" id="pane-users">
  <section class="card">
    <div class="user-header">
      <div><h2>多用户、流量与 IP 限制管理</h2><p style="font-size:13px">实时监控当前节点有效用户、到期时间、实时流量消耗与在线 IP 限制</p></div>
      <div class="user-stats">
        <span class="badge-count">有效用户: {active_count} / {len(users)}</span>
        <span class="badge-count" style="background:#f0f7f6">总已用流量: {format_bytes(total_used_bytes)}</span>
      </div>
    </div>

    <!-- 手动添加用户卡片 (结构化字段 + 随机生成辅助) -->
    <!-- WARP 出口分流全局控制卡片 -->
    <div class="switch-box" id="warp-box">
      <div class="switch-info">
        <div class="switch-title">
          <span>⚡ Cloudflare WARP 智能分流出口 (AI 加速)</span>
          <span class="status-pill" id="warp-badge" style="background:#eaf3de;color:#27500a">检测中...</span>
        </div>
        <div class="switch-desc">
          开启后 OpenAI (ChatGPT), Claude, Google Gemini 流量自动经由 Cloudflare 干净网络出口，有效防止封号与验证码；普通网页与下载仍维持 VPS 原生高速直连。
        </div>
      </div>
      <div style="display:flex;gap:10px;align-items:center">
        <button class="toggle-btn off" id="btn-toggle-warp" type="button">切换中...</button>
      </div>
    </div>

    <details style="margin-bottom:18px">
      <summary class="button" style="margin-bottom:12px;list-style:none">＋ 手动添加/开通新用户</summary>
      <form class="modal-form" method="POST" action="/{token}/manage-user">
        <input type="hidden" name="action" value="create">
        
        <div class="form-field">
          <label for="f_uid">用户标识 (User ID) <span>必填</span></label>
          <div class="input-with-action">
            <input id="f_uid" name="user_id" placeholder="例如: user_01" required>
            <button type="button" class="btn-mini" data-gen="f_uid" data-prefix="user">🎲 随机生成</button>
          </div>
          <small>客户端节点命名或用户唯一标识</small>
        </div>

        <div class="form-field">
          <label for="f_pwd">连接认证密码 <span>留空随机</span></label>
          <div class="input-with-action">
            <input id="f_pwd" name="password" placeholder="留空提交时自动生成">
            <button type="button" class="btn-mini" data-gen="f_pwd">🎲 随机密码</button>
          </div>
          <small>买家或客户端用于握手的秘密连接密钥</small>
        </div>

        <div class="form-field">
          <label for="f_days">服务有效期 (天) <span>默认 30</span></label>
          <input id="f_days" name="duration_days" type="number" min="1" max="3650" value="30" placeholder="默认 30 天">
          <small>从创建时间起算的有效天数</small>
        </div>

        <div class="form-field">
          <label for="f_traffic">流量限额 (GB) <span>0 为不限</span></label>
          <input id="f_traffic" name="traffic_gb" type="number" step="0.5" min="0" value="0" placeholder="输入例如 100">
          <small>达到限额后系统将自动阻断连接</small>
        </div>

        <div class="form-field">
          <label for="f_iplimit">同时在线 IP 限制 <span>0 为不限</span></label>
          <input id="f_iplimit" name="ip_limit" type="number" min="0" max="100" value="0" placeholder="例如填 1 或 2">
          <small>限制单人或单家庭设备同时使用</small>
        </div>

        <div class="form-field">
          <label for="f_note">备注信息 <span>选填</span></label>
          <input id="f_note" name="note" placeholder="例如: 客户小明 / 微信购买">
          <small>便于你在控制台快速区分订单来源</small>
        </div>

        <div class="form-field-full" style="margin-top:6px">
          <button class="button primary" style="width:100%;height:44px;font-size:14px" type="submit">立即创建并开通用户 →</button>
        </div>
      </form>
    </details>

    <div class="user-table-wrap">
      <table class="user-table">
        <thead><tr><th>用户标识</th><th>状态</th><th>IP 限制 (实时)</th><th>已用流量 / 配额</th><th>到期时间</th><th>连接密码</th><th>操作</th></tr></thead>
        <tbody>{users_table_html}</tbody>
      </table>
    </div>
  </section>
</div>

<!-- Tab 3: 集群与通用 REST API 对接视图 -->
<div class="tab-pane" id="pane-cluster">
  <section class="card" style="border-left:4px solid var(--accent)">
    <div class="card-head"><span class="step">API</span><div><h2>通用 REST API 接口与集群对接凭据</h2><p>支持接入任何自动化发卡商城、用户控制中心或第三方管理系统</p></div></div>
    
    <div class="api-box">
      <div>
        <div style="font-size:11px;color:var(--muted);font-weight:700">API 基础地址 (Base URL)</div>
        <div class="api-key-code" id="api-base-val">https://{host}:{sub_port}</div>
      </div>
      <button class="button" type="button" data-copy="api-base-val" data-orig="复制地址">复制地址</button>
    </div>
    
    <div class="api-box">
      <div>
        <div style="font-size:11px;color:var(--muted);font-weight:700">通信鉴权密钥 (Bearer API Key)</div>
        <div class="api-key-code" id="api-key-val">{html.escape(api_key or "")}</div>
      </div>
      <button class="button primary" type="button" data-copy="api-key-val" data-orig="复制 Key">复制 Key</button>
    </div>

    {pin_block}

    <!-- 标准 REST API 接口调用规范与示例 -->
    <div style="margin-top:24px">
      <h3 style="font-size:15px;margin:0 0 12px;color:var(--ink)">📋 标准 REST API 接口规范与代码示例</h3>

      <div style="display:grid;gap:14px">
        <details class="card" style="padding:16px;box-shadow:none;border-color:#d7e5e2">
          <summary style="font-size:13px;color:#1e4c56"><strong>1. 创建/开通用户 (支持流量与IP配额)</strong> <code>POST /api/v1/users/create</code></summary>
          <div style="margin-top:12px;font-size:12px;color:var(--muted)">
            <p style="margin-bottom:6px"><strong>请求 Header：</strong> <code>Authorization: Bearer &lt;API_KEY&gt;</code> &nbsp;|&nbsp; <code>Content-Type: application/json</code></p>
            <p style="margin-bottom:6px"><strong>请求 Body 参数：</strong></p>
            <pre style="background:#f4f8f7;padding:10px;border-radius:8px;overflow-x:auto;color:#284850">{{"user_id": "buyer_01", "password": "custom_password", "duration_days": 30, "traffic_gb": 100, "ip_limit": 1, "note": "客户订单"}}</pre>
            <p style="margin:8px 0 6px"><strong>响应内容：</strong> 包含 <code>ok: true</code>, 专属 <code>uri</code> 节点直链与 <code>clash</code> 配置片段。</p>
          </div>
        </details>

        <details class="card" style="padding:16px;box-shadow:none;border-color:#d7e5e2">
          <summary style="font-size:13px;color:#1e4c56"><strong>2. 延长有效期 (续费)</strong> <code>POST /api/v1/users/renew</code></summary>
          <div style="margin-top:12px;font-size:12px;color:var(--muted)">
            <pre style="background:#f4f8f7;padding:10px;border-radius:8px;overflow-x:auto;color:#284850">{{"user_id": "buyer_01", "extend_days": 30, "add_traffic_gb": 100}}</pre>
          </div>
        </details>

        <details class="card" style="padding:16px;box-shadow:none;border-color:#d7e5e2">
          <summary style="font-size:13px;color:#1e4c56"><strong>3. 注销/删除用户</strong> <code>POST /api/v1/users/delete</code></summary>
          <div style="margin-top:12px;font-size:12px;color:var(--muted)">
            <pre style="background:#f4f8f7;padding:10px;border-radius:8px;overflow-x:auto;color:#284850">{{"user_id": "buyer_01"}}</pre>
          </div>
        </details>

        <details class="card" style="padding:16px;box-shadow:none;border-color:#d7e5e2">
          <summary style="font-size:13px;color:#1e4c56"><strong>4. 节点健康状态与用户数</strong> <code>GET /api/v1/node/meta</code></summary>
          <div style="margin-top:12px;font-size:12px;color:var(--muted)">
            <p>返回当前节点的端口、公网 IP/域名、混淆模式以及当前有效用户数与总流量统计。</p>
          </div>
        </details>
      </div>

      <div style="margin-top:16px;padding:14px;background:#f3f7f6;border-radius:10px;font-size:12px;color:#456972">
        💡 <strong>通用性说明：</strong>任何自动化系统（如发卡商城、WHMCS、Telegram 机器人、自建 Python/Node.js/Go 后端）只需发送标准 HTTP POST 请求携带 Bearer Token，即可实现全自动集群开户、流量限制与到期停用。
      </div>
    </div>
  </section>
</div>

<!-- Tab 4: 高级配置文件视图 -->
<div class="tab-pane" id="pane-configs">
  <section class="advanced" style="margin-top:0">
    <div class="advanced-title"><h2>完整配置文件片段</h2><p>支持手动复制或下载独立配置文件。</p></div>
    <div class="config-grid">
      <div class="card">
        <div class="card-head"><span class="step">C</span><div><h2>Clash / Mihomo</h2><p>完整配置文件</p></div></div>
        {field_clash_cfg}
        <div class="actions">{copy_clash_cfg}<a class="button" href="clash.yaml" download="clash.yaml">下载 ↓</a></div>
      </div>
      <div class="card">
        <div class="card-head"><span class="step">S</span><div><h2>Sing-box</h2><p>出站 Outbounds JSON</p></div></div>
        {field_sing_cfg}
        <div class="actions">{copy_sing_cfg}<a class="button" href="sing-box.json" download="sing-box.json">下载 ↓</a></div>
      </div>
    </div>
  </section>
</div>

<div class="security">私密提示 · 链接和二维码包含连接凭据，请勿公开分享或发送截图给他人。</div>
<p id="copy-status" class="status" role="status" aria-live="polite"></p>

<!-- 专属用户连接模态框 -->
<div class="modal-backdrop" id="user-modal">
  <div class="modal-card">
    <div class="modal-head">
      <div>
        <h2 id="um-title" style="margin:0;font-size:18px">专属用户连接</h2>
        <p id="um-sub" style="font-size:12px;margin-top:2px;color:var(--muted)"></p>
      </div>
      <button class="modal-close" type="button" id="um-close">&times;</button>
    </div>
    <div id="um-body"></div>
  </div>
</div>

<footer><span>HYSTERIA 2 / CLUSTER AGENT PORTAL</span><span>配置由你的服务器动态生成</span></footer>
</main><script>{SCRIPT}</script></body></html>"""


def login_html(token, error_msg=None):
    error_banner = f'<div class="error-tip" role="alert"><span>⚠</span><span>{html.escape(error_msg)}</span></div>' if error_msg else ''
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>验证访问 · Hysteria 2 节点中心</title><style>{STYLE}</style></head><body>
<div class="login-wrap"><div class="login-card">
<div class="login-brand"><div class="login-logo">H₂</div><div class="login-badge">HYSTERIA 2 GATEWAY</div><h1 class="login-title">私密身份认证</h1><p class="login-sub">请输入服务器生成的专属凭据以进入节点中心</p></div>
<form class="login-form" method="POST" action="/{token}/login">
{error_banner}
<div class="field-group"><label class="field-label" for="username">用户名 (Username)</label><input class="field-input" id="username" name="username" type="text" autocomplete="username" required autofocus placeholder="输入随机生成的用户名"></div>
<div class="field-group"><div class="field-label"><label for="password">密码 (Password)</label></div><div class="field-pwd"><input class="field-input" id="password" name="password" type="password" autocomplete="current-password" required placeholder="输入访问密钥"><button type="button" class="toggle-pwd" onclick="toggleSecret('password', this)">显示</button></div></div>
<div class="remember-row"><input type="checkbox" id="remember" name="remember" value="1" checked><label for="remember">在此浏览器保持登录（30天）</label></div>
<button class="btn-submit" type="submit">立即进入私密中心 →</button>
</form>
<div class="login-footer">如果遗忘凭据，随时在服务器终端执行<br><code>bash install.sh info</code> 找回账号密码</div>
</div></div>
<script>{LOGIN_SCRIPT}</script></body></html>'''


def user_page_html(server_name, host, listen_port, obfs_badge, uid, uinfo, uri, clash, sing, qr_svg, token, user_key):
    used_bytes = int(uinfo.get("used_bytes", 0))
    limit_bytes = int(uinfo.get("limit_bytes", 0))
    now_ts = int(time.time())
    is_traffic_ok = limit_bytes == 0 or used_bytes < limit_bytes
    is_time_ok = uinfo.get("expires_at", 0) >= now_ts
    is_active = uinfo.get("status") == "active" and is_time_ok and is_traffic_ok

    if not is_traffic_ok:
        status_html = '<span class="status-pill expired">流量已超额</span>'
    elif not is_time_ok:
        status_html = '<span class="status-pill expired">服务已到期</span>'
    elif uinfo.get("status") != "active":
        status_html = '<span class="status-pill expired">账号已停用</span>'
    else:
        status_html = '<span class="status-pill active">运行正常</span>'

    expires_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(uinfo.get("expires_at", 0))) if uinfo.get("expires_at", 0) < 2000000000 else "永久有效"
    ip_limit = uinfo.get("ip_limit", 0)
    ip_limit_str = f"{ip_limit} 台设备" if ip_limit > 0 else "不限制"

    if limit_bytes > 0:
        percent = min(round((used_bytes / limit_bytes) * 100), 100)
        bar_class = "danger" if percent >= 90 else ""
        traffic_display = f"""<div>{format_bytes(used_bytes)} / {format_bytes(limit_bytes)} <span style="font-size:12px;color:var(--muted)">({percent}%)</span></div>
        <div class="traffic-bar" style="width:100%;height:8px"><div class="traffic-fill {bar_class}" style="width:{percent}%"></div></div>"""
    else:
        traffic_display = f"""<div>{format_bytes(used_bytes)} <span style="font-size:12px;color:var(--muted)">(不限制总流量)</span></div>"""

    note = uinfo.get("note") or "-"
    sub_port = uinfo.get("subscription_port") or 8443
    clash_sub_url = f"https://{host}:{sub_port}/{token}/u/{quote(uid)}/clash.yaml?k={user_key}"

    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>个人专属连接 · {html.escape(uid)}</title><style>{STYLE}</style></head><body><main style="max-width:860px">
<nav class="topbar"><div class="brand"><span class="logo">H₂</span> HYSTERIA <span> / 个人连接中心</span></div><div>{status_html}</div></nav>
<header class="hero"><div class="eyebrow">HYSTERIA 2 CLIENT ACCESS</div><h1>{html.escape(uid)}</h1><p>专属节点连接凭据与客户端配置 · 备注: {html.escape(note)}</p></header>

<!-- 配额用量卡片 -->
<section class="card" style="margin-bottom:22px">
  <div class="user-header" style="margin-bottom:12px">
    <h2>账号服务状态</h2>
    <div>{status_html}</div>
  </div>
  <div class="user-meta-bar" style="font-size:13px;padding:14px;background:#f8fbfb">
    <div style="flex:1;min-width:180px">📅 有效期至: <b>{expires_str}</b></div>
    <div style="flex:1;min-width:180px">📱 同时在线限制: <b>{ip_limit_str}</b></div>
    <div style="flex:2;min-width:220px">📊 流量消耗: {traffic_display}</div>
  </div>
</section>

<div class="layout" style="grid-template-columns:300px minmax(0,1fr)">
  <!-- 扫码卡片 -->
  <section class="card qr-card" style="margin-top:0">
    <div class="eyebrow">QUICK CONNECT</div>
    <h2>扫码快速导入</h2>
    <p class="hint">支持 v2rayNG / Shadowrocket / Nekobox</p>
    <div class="qr-frame" style="margin:16px 0">{qr_svg}</div>
    <p class="hint">在客户端点击右上角扫描即可直接接入</p>
    <div class="tags"><span class="tag">Hysteria 2</span><span class="tag">专属认证</span><span class="tag">{obfs_badge}</span></div>
  </section>

  <!-- 直链与客户端配置 -->
  <div class="stack">
    <section class="card">
      <div class="card-head"><span class="step">01</span><div><h2>节点直链 (URI)</h2><p>全平台通用直链 (点击一键导入/剪贴板导入)</p></div></div>
      <textarea id="u-hy2-uri" class="link" readonly>{html.escape(uri)}</textarea>
      <div class="actions">
        <button class="button primary" type="button" data-copy="u-hy2-uri">复制直链</button>
      </div>
      <p class="note">{html.escape(host)} · UDP {int(listen_port)}</p>
    </section>

    <section class="card">
      <div class="card-head"><span class="step">02</span><div><h2>Clash / Mihomo 专属订阅</h2><p>适用于 Clash Verge / Clash.Meta 核心客户端 (一键订阅同步)</p></div></div>
      <textarea id="u-clash-sub" class="link" style="height:68px" readonly>{html.escape(clash_sub_url)}</textarea>
      <div class="actions">
        <button class="button primary" type="button" data-copy="u-clash-sub">复制订阅链接</button>
        <a class="button" href="/{token}/u/{quote(uid)}/clash.yaml?k={user_key}" download="clash-{uid}.yaml">下载 clash.yaml ↓</a>
      </div>
      <details style="margin-top:10px">
        <summary style="font-size:11px;color:var(--muted)">查看/复制原始配置源码 (备用)</summary>
        <textarea id="u-clash-cfg" class="config" style="height:110px;margin-top:6px" readonly>{html.escape(clash)}</textarea>
        <div style="margin-top:4px"><button class="button" type="button" data-copy="u-clash-cfg" style="padding:4px 10px;font-size:11px">复制配置文本</button></div>
      </details>
    </section>

    <section class="card">
      <div class="card-head"><span class="step">03</span><div><h2>Sing-box 出站配置</h2><p>适用 SFI / SFA / Sing-box 客户端</p></div></div>
      <textarea id="u-sing-cfg" class="config" style="height:140px" readonly>{html.escape(sing)}</textarea>
      <div class="actions">
        <button class="button primary" type="button" data-copy="u-sing-cfg">复制配置</button>
        <a class="button" href="/{token}/u/{quote(uid)}/sing-box.json?k={user_key}" download="sing-box-{uid}.json">下载 sing-box.json ↓</a>
      </div>
    </section>
  </div>
</div>

<div class="security">私密提示 · 该页面为你的个人节点专属连接页面，包含连接密钥，请妥善保管。</div>
<footer><span>HYSTERIA 2 / PERSONAL PORTAL</span><span>由你的专属服务器动态生成</span></footer>
</main><script>{USER_SCRIPT}</script></body></html>"""


def content_policy(extra_script=None):
    def digest(value):
        return base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
    scripts = ["'sha256-" + digest(SCRIPT) + "'", "'sha256-" + digest(LOGIN_SCRIPT) + "'", "'sha256-" + digest(USER_SCRIPT) + "'"]
    if extra_script:
        scripts.append("'sha256-" + digest(extra_script) + "'")
    return ("default-src 'none'; connect-src 'self'; img-src 'self' data:; style-src 'sha256-" + digest(STYLE)
            + "'; script-src " + " ".join(scripts)
            + "; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


def get_cert_pin_sha256(root_path):
    """SHA-256 of the certificate DER, as plain lowercase HEX.

    v2rayNG/v2rayN (Xray core) copy the hysteria2 URI's `pinSHA256` straight into
    Xray's `pinnedPeerCertSha256`, which is a HEX field - a base64 value there makes
    Xray abort with `encoding/hex: invalid byte`.
    """
    cert_file = Path(root_path) / 'cert' / 'server.crt'
    if not cert_file.exists():
        return ''
    try:
        p1 = subprocess.Popen(['openssl', 'x509', '-in', str(cert_file), '-outform', 'DER'],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        p2 = subprocess.Popen(['openssl', 'dgst', '-sha256'], stdin=p1.stdout,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        p1.stdout.close()
        out = p2.communicate()[0].decode().strip()
        hexval = out.rsplit('=', 1)[-1].strip().lower()
        return hexval if len(hexval) == 64 and all(c in '0123456789abcdef' for c in hexval) else ''
    except Exception:
        return ''


def artifacts(m, auth_override=None, name_override=None):
    is_insecure = m.get('is_insecure', False)
    server_name = m.get('server_name') or m.get('public_ip', 'localhost')
    public_ip = m.get('public_ip', server_name)
    host = public_ip if is_insecure else server_name
    name = name_override or ('Hy2-' + host)
    password = auth_override or m.get('auth_password', '')
    listen_port = m.get('listen_port', 19984)
    obfs_password = m.get('obfs_password', '')
    hop_port_range = m.get('hop_port_range', '')
    # 证书信任策略（已逐条对照 v2rayNG 源码 / Xray 内核行为对齐）：
    #   * 公网可信证书：直链不带任何 pin / insecure，全客户端开箱即用；
    #   * 自签证书：同时带 pinSHA256(<HEX64>) 与 insecure=1 ——
    #       v2rayNG/v2rayN 把 pinSHA256 直接塞进 Xray 的 pinnedPeerCertSha256，该字段必须是【纯 HEX】，
    #       写 base64 会触发 `encoding/hex: invalid byte` 导致配置构建失败（这正是上一版扫码连不上的根因）；
    #       v2rayNG 源码仅在 pin 为空时才输出 allowInsecure，故两者并存既不报错，又能让只认 insecure 的
    #       sing-box / NekoBox / Clash / 官方 hysteria 正常跳过校验。
    raw_pin = (m.get('pin_sha256') or '').strip().lower()
    pin_sha256 = raw_pin if len(raw_pin) == 64 and all(c in '0123456789abcdef' for c in raw_pin) else ''
    params = {'sni': server_name}
    if is_insecure:
        params['insecure'] = '1'
        if pin_sha256:
            params['pinSHA256'] = pin_sha256
    if obfs_password:
        params.update({'obfs': 'salamander', 'obfs-password': obfs_password})
    if hop_port_range:
        params['mport'] = hop_port_range
    uri = f"hysteria2://{quote(password, safe='')}@{host}:{listen_port}?{urlencode(params)}#{quote(name)}"
    
    proxy = dict(name=name, type='hysteria2', server=host, port=listen_port,
                 password=password, sni=server_name, **{'skip-cert-verify': is_insecure})
    sing = dict(type='hysteria2', tag=name, server=host, server_port=listen_port,
                password=password, tls=dict(enabled=True, server_name=server_name, insecure=is_insecure))
    if hop_port_range:
        proxy['ports'] = str(listen_port) + ',' + hop_port_range
        sing['server_ports'] = [str(listen_port), hop_port_range.replace('-', ':')]
        del sing['server_port']
    if obfs_password:
        proxy.update({'obfs': 'salamander', 'obfs-password': obfs_password})
        sing['obfs'] = dict(type='salamander', password=obfs_password)
    clash = {'mixed-port': 7890, 'allow-lan': False, 'mode': 'rule', 'proxies': [proxy],
             'proxy-groups': [{'name': 'PROXY', 'type': 'select', 'proxies': [name, 'DIRECT']}],
             'rules': ['MATCH,PROXY']}
    return uri, json.dumps(clash, ensure_ascii=False, indent=2), json.dumps({'outbounds': [sing]}, ensure_ascii=False, indent=2)


def sync_pin(m, root, meta_path):
    """Align client_meta.json's pin_sha256 with the node's trust model.

    Trusted cert  -> pin wiped entirely (a stale/base64 value must never linger:
                     Xray reads pinSHA256 as HEX and a base64 char aborts the build).
    Self-signed   -> a valid lowercase HEX64 pin, recomputed from cert/server.crt
                     whenever it is missing or malformed.
    """
    if m.get('is_insecure'):
        cur = (m.get('pin_sha256') or '').strip().lower()
        if len(cur) != 64 or any(c not in '0123456789abcdef' for c in cur):
            new = get_cert_pin_sha256(root)
            if new != m.get('pin_sha256'):
                m['pin_sha256'] = new
                Path(meta_path).write_text(json.dumps(m, ensure_ascii=False))
    elif m.get('pin_sha256'):
        m['pin_sha256'] = ''
        Path(meta_path).write_text(json.dumps(m, ensure_ascii=False))


def prepare(meta_path, port, node_api_key=None):
    root = Path(meta_path).parent
    m = json.loads(Path(meta_path).read_text())
    sync_pin(m, root, meta_path)

    uri, clash, sing = artifacts(m)
    qr = subprocess.run(['qrencode', '-t', 'SVG', '-o', '-'], input=uri.encode(), capture_output=True, check=True).stdout
    user, password, token = secrets.token_hex(8), secrets.token_urlsafe(32), secrets.token_hex(32)
    host = m['public_ip'] if m['is_insecure'] else m['server_name']
    base = f"https://{host}:{m['subscription_port']}/{token}/"
    subscription = f"https://{user}:{password}@{host}:{m['subscription_port']}/{token}/clash.yaml"
    session_secret = secrets.token_hex(32)
    api_key = node_api_key or secrets.token_hex(24)

    users = {
        'admin_master': {
            'password': m['auth_password'],
            'expires_at': 2085974400,
            'ip_limit': 0,
            'limit_bytes': 0,
            'used_bytes': 0,
            'status': 'active',
            'created_at': int(time.time()),
            'note': 'Master Admin'
        }
    }
    page = page_html(m, uri, subscription, clash, sing, users=users, api_key=api_key, token=token, session_secret=session_secret)
    auth = base64.b64encode(f'{user}:{password}'.encode())

    data = dict(port=int(port), token=token, auth_hash=hashlib.sha256(auth).hexdigest(),
                session_secret=session_secret, api_key=api_key, users=users,
                page=page, qr=qr.decode(), clash=clash, sing=sing)
    for filename, value in [('portal.json', data), ('portal-access.json', dict(url=base, username=user, password=password, api_key=api_key))]:
        path = root / filename
        path.write_text(json.dumps(value, ensure_ascii=False))
        path.chmod(0o600)


def refresh(meta_path):
    root = Path(meta_path).parent
    m = json.loads(Path(meta_path).read_text())
    sync_pin(m, root, meta_path)

    access = json.loads((root / 'portal-access.json').read_text())
    path = root / 'portal.json'
    data = json.loads(path.read_text())
    uri, clash, sing = artifacts(m)
    host = m['public_ip'] if m['is_insecure'] else m['server_name']
    subscription = f"https://{access['username']}:{access['password']}@{host}:{m['subscription_port']}/{data['token']}/clash.yaml"
    
    if 'session_secret' not in data:
        data['session_secret'] = secrets.token_hex(32)
    if 'api_key' not in data:
        data['api_key'] = access.get('api_key') or secrets.token_hex(24)
        access['api_key'] = data['api_key']
        (root / 'portal-access.json').write_text(json.dumps(access, ensure_ascii=False))
    if 'users' not in data:
        data['users'] = {
            'admin_master': {
                'password': m['auth_password'],
                'expires_at': 2085974400,
                'ip_limit': 0,
                'limit_bytes': 0,
                'used_bytes': 0,
                'status': 'active',
                'created_at': int(time.time()),
                'note': 'Master Admin'
            }
        }
    data['page'] = page_html(m, uri, subscription, clash, sing, users=data['users'], api_key=data['api_key'], token=data['token'], session_secret=data.get('session_secret', ''))
    
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False))
    temporary.chmod(0o600)
    temporary.replace(path)


def serve(path):
    portal_path = Path(path)
    data = json.loads(portal_path.read_text())
    session_secret = data.get('session_secret', data['auth_hash'])
    meta_path = portal_path.parent / 'client_meta.json'

    data_lock = threading.Lock()
    ip_tracker = {}
    IP_TIMEOUT_SECONDS = 180
    VALID_USER_ID_RE = re.compile(r'^[a-zA-Z0-9_\-\.]{1,64}$')

    def save_data():
        with data_lock:
            try:
                temp = portal_path.with_suffix('.tmp')
                temp.write_text(json.dumps(data, ensure_ascii=False))
                temp.chmod(0o600)
                temp.replace(portal_path)
            except OSError:
                disk_path = Path('/etc/hysteria/portal.json')
                if disk_path.exists():
                    disk_temp = disk_path.with_suffix('.tmp')
                    disk_temp.write_text(json.dumps(data, ensure_ascii=False))
                    disk_temp.chmod(0o600)
                    disk_temp.replace(disk_path)

    def regenerate_page():
        m = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        uri, clash, sing = artifacts(m)
        root = portal_path.parent
        access_file = root / 'portal-access.json'
        access = json.loads(access_file.read_text()) if access_file.exists() else {}
        host = m.get('public_ip', '127.0.0.1') if m.get('is_insecure') else m.get('server_name', 'localhost')
        subscription = f"https://{access.get('username','')}:{access.get('password','')}@{host}:{m.get('subscription_port',8443)}/{data['token']}/clash.yaml"
        
        now_ts = int(time.time())
        display_users = {}
        with data_lock:
            # 清理离线已久的 ip_tracker 键
            dead_uids = [u for u, tr in ip_tracker.items() if not any(now_ts - t < IP_TIMEOUT_SECONDS for t in tr.values())]
            for du in dead_uids:
                del ip_tracker[du]

            for uid, uinfo in data.get('users', {}).items():
                u_copy = dict(uinfo)
                user_ips = {ip: t for ip, t in ip_tracker.get(uid, {}).items() if now_ts - t < IP_TIMEOUT_SECONDS}
                u_copy['online_ips'] = user_ips
                display_users[uid] = u_copy

            data['page'] = page_html(m, uri, subscription, clash, sing, users=display_users, api_key=data.get('api_key'), token=data['token'], session_secret=session_secret)
        save_data()

    def sign_session(token):
        sig = hmac.new(session_secret.encode(), f'sess:{token}'.encode(), hashlib.sha256).hexdigest()
        return f'{token}.{sig}'

    def verify_session(cookie_header):
        if not cookie_header:
            return False
        cookies = SimpleCookie()
        try:
            cookies.load(cookie_header)
        except Exception:
            return False
        if 'hy2_session' not in cookies:
            return False
        raw = cookies['hy2_session'].value
        if '.' not in raw:
            return False
        t, sig = raw.split('.', 1)
        expected = hmac.new(session_secret.encode(), f'sess:{t}'.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(t, data['token']) and hmac.compare_digest(sig, expected)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'Gateway'
        sys_version = ''
        def setup(self):
            super().setup()
            self.connection.settimeout(5)
        def log_message(self, *args):
            pass

        def verify_api_key(self):
            auth_header = self.headers.get('Authorization', '')
            expected = 'Bearer ' + data.get('api_key', '')
            return hmac.compare_digest(auth_header, expected)

        def is_authenticated(self):
            auth = self.headers.get('Authorization', '')
            if auth.startswith('Basic '):
                digest = hashlib.sha256(auth.removeprefix('Basic ').encode()).hexdigest()
                if hmac.compare_digest(digest, data['auth_hash']):
                    return True
            return verify_session(self.headers.get('Cookie', ''))

        def reply_json(self, code, payload):
            body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def check_rate_limit(self, bucket='web'):
            now = time.monotonic()
            with data_lock:
                if bucket == 'api':
                    self.server.api_requests[:] = [t for t in self.server.api_requests if now - t < 1]
                    if len(self.server.api_requests) >= 50:
                        return False
                    self.server.api_requests.append(now)
                    return True
                else:
                    self.server.requests[:] = [t for t in self.server.requests if now - t < 1]
                    self.server.failures[:] = [t for t in self.server.failures if now - t < 60]
                    if len(self.server.requests) >= 50 or len(self.server.failures) >= 60:
                        return False
                    self.server.requests.append(now)
                    return True

        def record_failure(self):
            now = time.monotonic()
            with data_lock:
                self.server.failures.append(now)

        def do_POST(self):
            # 1. Hysteria 2 本地 HTTP 动态鉴权、实时流量统计与 IP 限额拦截端点 (来自 127.0.0.1 豁免限流)
            if self.path == '/auth':
                try:
                    length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(length).decode('utf-8')
                    req_data = json.loads(body)
                    client_auth = req_data.get('auth', '').strip()
                    client_addr = req_data.get('addr', '')
                    # tx (客户端上行/服务器接收), rx (客户端下行/服务器发送) 流量增量统计
                    tx_bytes = int(req_data.get('tx', 0))
                    rx_bytes = int(req_data.get('rx', 0))
                    delta_traffic = tx_bytes + rx_bytes
                    client_ip = client_addr.rsplit(':', 1)[0].strip('[]') if client_addr else ''
                except Exception:
                    return self.reply_json(200, {'ok': False, 'msg': 'Bad auth request'})

                now_ts = int(time.time())
                with data_lock:
                    users = data.get('users', {})
                    matched_uid, matched_user = None, None
                    for uid, uinfo in users.items():
                        if uinfo.get('password') == client_auth:
                            matched_uid, matched_user = uid, uinfo
                            break

                    if not matched_user:
                        return self.reply_json(200, {'ok': False, 'msg': 'User not found'})

                    if matched_user.get('status') != 'active':
                        return self.reply_json(200, {'ok': False, 'msg': 'User account inactive'})

                    if matched_user.get('expires_at', 0) < now_ts:
                        return self.reply_json(200, {'ok': False, 'msg': 'User account expired'})

                    # -------- 流量限额检查与增量累加 -------- #
                    limit_bytes = int(matched_user.get('limit_bytes', 0))
                    used_bytes = int(matched_user.get('used_bytes', 0)) + delta_traffic
                    matched_user['used_bytes'] = used_bytes

                    if limit_bytes > 0 and used_bytes >= limit_bytes:
                        # 流量超额，阻断拒绝连接
                        return self.reply_json(200, {'ok': False, 'msg': 'Traffic quota exceeded'})

                    # -------- 同时在线 IP 限制检查 -------- #
                    ip_limit = int(matched_user.get('ip_limit', 0))
                    if ip_limit > 0 and client_ip:
                        tracker = ip_tracker.setdefault(matched_uid, {})
                        active_ips = {ip: t for ip, t in tracker.items() if now_ts - t < IP_TIMEOUT_SECONDS}
                        ip_tracker[matched_uid] = active_ips

                        if client_ip not in active_ips and len(active_ips) >= ip_limit:
                            return self.reply_json(200, {'ok': False, 'msg': f'Concurrent IP limit exceeded ({ip_limit} max)'})
                        active_ips[client_ip] = now_ts
                    elif client_ip:
                        tracker = ip_tracker.setdefault(matched_uid, {})
                        tracker[client_ip] = now_ts

                return self.reply_json(200, {'ok': True, 'id': matched_uid})

            # 2. REST API 接口通道 (独立 API 速率桶)
            if self.path.startswith('/api/v1/'):
                if not self.check_rate_limit(bucket='api'):
                    return self.reply(429, b'Too many requests')

                if not self.verify_api_key():
                    return self.reply_json(401, {'ok': False, 'error': 'Unauthorized API key'})

                try:
                    length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(length).decode('utf-8') if length > 0 else '{}'
                    params = json.loads(body)
                except Exception:
                    return self.reply_json(400, {'ok': False, 'error': 'Invalid JSON body'})

                sub = self.path[len('/api/v1/'):]
                now_ts = int(time.time())

                # 动态开户 (支持 duration_days, ip_limit, traffic_gb)
                if sub == 'users/create':
                    user_id = (params.get('user_id') or ('hy2_' + secrets.token_hex(6))).strip()
                    if not VALID_USER_ID_RE.match(user_id):
                        return self.reply_json(400, {'ok': False, 'error': 'Invalid user_id format: only 1-64 alphanumeric, dash, dot and underscore characters allowed'})

                    pwd = params.get('password') or secrets.token_hex(16)
                    days = int(params.get('duration_days', 30))
                    ip_limit = int(params.get('ip_limit', 0))
                    traffic_gb = float(params.get('traffic_gb', 0))
                    limit_bytes = int(traffic_gb * (1024**3)) if traffic_gb > 0 else 0
                    expires = int(params.get('expires_at', now_ts + days * 86400))
                    note = str(params.get('note', '')).strip()[:200]

                    with data_lock:
                        data.setdefault('users', {})[user_id] = {
                            'password': pwd,
                            'expires_at': expires,
                            'ip_limit': ip_limit,
                            'limit_bytes': limit_bytes,
                            'used_bytes': 0,
                            'status': 'active',
                            'created_at': now_ts,
                            'note': note
                        }
                    regenerate_page()

                    m = json.loads(meta_path.read_text()) if meta_path.exists() else {}
                    uri, clash_yaml, sing_json = artifacts(m, auth_override=pwd, name_override=f"Hy2-{user_id}")
                    return self.reply_json(200, {
                        'ok': True,
                        'user_id': user_id,
                        'password': pwd,
                        'ip_limit': ip_limit,
                        'traffic_gb': traffic_gb,
                        'expires_at': expires,
                        'uri': uri,
                        'clash': clash_yaml,
                        'sing_box': sing_json
                    })

                elif sub == 'users/renew':
                    user_id = str(params.get('user_id', '')).strip()
                    if not VALID_USER_ID_RE.match(user_id):
                        return self.reply_json(400, {'ok': False, 'error': 'Invalid user_id format'})
                    days = int(params.get('extend_days', 30))
                    add_traffic_gb = float(params.get('add_traffic_gb', 0))
                    with data_lock:
                        u = data.get('users', {}).get(user_id)
                        if not u:
                            return self.reply_json(404, {'ok': False, 'error': 'User not found'})
                        base_time = max(u.get('expires_at', 0), now_ts)
                        u['expires_at'] = base_time + days * 86400
                        if add_traffic_gb > 0:
                            u['limit_bytes'] = int(u.get('limit_bytes', 0)) + int(add_traffic_gb * (1024**3))
                        u['status'] = 'active'
                        exp_at = u['expires_at']
                        lim_b = u.get('limit_bytes', 0)
                    regenerate_page()
                    return self.reply_json(200, {'ok': True, 'user_id': user_id, 'expires_at': exp_at, 'limit_bytes': lim_b})

                elif sub == 'users/delete':
                    user_id = str(params.get('user_id', '')).strip()
                    if not VALID_USER_ID_RE.match(user_id):
                        return self.reply_json(400, {'ok': False, 'error': 'Invalid user_id format'})
                    with data_lock:
                        if user_id in data.get('users', {}):
                            del data['users'][user_id]
                            if user_id in ip_tracker:
                                del ip_tracker[user_id]
                            deleted = True
                        else:
                            deleted = False
                    if deleted:
                        regenerate_page()
                        return self.reply_json(200, {'ok': True, 'message': 'User deleted'})
                    return self.reply_json(404, {'ok': False, 'error': 'User not found'})

                return self.reply_json(404, {'ok': False, 'error': 'API endpoint not found'})

            # 普通 Web 请求限流
            if not self.check_rate_limit(bucket='web'):
                return self.reply(429, b'Too many requests')

            # 3. Web 网页版管理通道 (用户管理 / WARP 开关)
            prefix = '/' + data['token'] + '/'
            if self.path == prefix + 'manage-warp':
                if not self.is_authenticated():
                    return self.reply_json(401, {'ok': False, 'error': 'Unauthorized'})
                try:
                    with data_lock:
                        curr = data.get('warp_enabled', False)
                        data['warp_enabled'] = not curr
                        new_state = data['warp_enabled']
                    save_data()
                    # 触发后台更新 Hysteria 2 ACL 规则并重载
                    try:
                        subprocess.Popen(['bash', '/etc/hysteria/toggle_warp.sh', '1' if new_state else '0'],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
                    return self.reply_json(200, {'ok': True, 'enabled': new_state})
                except Exception as e:
                    return self.reply_json(500, {'ok': False, 'error': str(e)})

            if self.path == prefix + 'manage-user':
                if not self.is_authenticated():
                    return self.reply(401, b'Unauthorized')
                try:
                    length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(length).decode('utf-8')
                    form = parse_qs(body)
                    action = form.get('action', [''])[0]
                    user_id = form.get('user_id', [''])[0].strip()
                    now_ts = int(time.time())

                    if not VALID_USER_ID_RE.match(user_id):
                        return self.reply(400, b'Invalid user_id format')

                    if action == 'create' and user_id:
                        pwd = form.get('password', [''])[0].strip() or secrets.token_hex(16)
                        days = int(form.get('duration_days', ['30'])[0] or 30)
                        ip_limit = int(form.get('ip_limit', ['0'])[0] or 0)
                        traffic_gb = float(form.get('traffic_gb', ['0'])[0] or 0)
                        limit_bytes = int(traffic_gb * (1024**3)) if traffic_gb > 0 else 0
                        note = form.get('note', [''])[0].strip()[:200]
                        with data_lock:
                            data.setdefault('users', {})[user_id] = {
                                'password': pwd,
                                'expires_at': now_ts + days * 86400,
                                'ip_limit': ip_limit,
                                'limit_bytes': limit_bytes,
                                'used_bytes': 0,
                                'status': 'active',
                                'created_at': now_ts,
                                'note': note
                            }
                    elif action == 'delete' and user_id:
                        with data_lock:
                            if user_id in data.get('users', {}):
                                del data['users'][user_id]
                                if user_id in ip_tracker:
                                    del ip_tracker[user_id]

                    regenerate_page()
                    self.send_response(302)
                    self.send_header('Location', prefix + '#users')
                    self.end_headers()
                    return
                except Exception:
                    return self.reply(400, b'Bad request')

            # 4. Web 表单登录
            if self.path == prefix + 'login':
                try:
                    length = int(self.headers.get('Content-Length', 0))
                    if length > 4096:
                        return self.reply(400, b'Bad request')
                    body = self.rfile.read(length).decode('utf-8', errors='ignore')
                    params = parse_qs(body)
                    user = params.get('username', [''])[0]
                    pwd = params.get('password', [''])[0]
                    remember = params.get('remember', ['0'])[0] == '1'
                except Exception:
                    return self.reply(400, b'Bad request')

                submitted_auth = base64.b64encode(f'{user}:{pwd}'.encode())
                submitted_digest = hashlib.sha256(submitted_auth).hexdigest()

                if not hmac.compare_digest(submitted_digest, data['auth_hash']):
                    self.record_failure()
                    page = login_html(data['token'], error_msg='用户名或密码不正确，请重新输入')
                    return self.reply(200, page.encode('utf-8'), 'text/html; charset=utf-8')

                sess_val = sign_session(data['token'])
                max_age = '; Max-Age=2592000' if remember else ''
                cookie = f'hy2_session={sess_val}; Path=/{data["token"]}/; HttpOnly; SameSite=Strict; Secure{max_age}'
                self.send_response(302)
                self.send_header('Location', prefix)
                self.send_header('Set-Cookie', cookie)
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                return

            return self.reply(404, b'Not found')

        def do_GET(self):
            if self.path.startswith('/api/v1/'):
                if not self.check_rate_limit(bucket='api'):
                    return self.reply(429, b'Too many requests')
                if not self.verify_api_key():
                    return self.reply_json(401, {'ok': False, 'error': 'Unauthorized API key'})
                sub = self.path[len('/api/v1/'):]
                if sub == 'node/meta':
                    m = json.loads(meta_path.read_text()) if meta_path.exists() else {}
                    with data_lock:
                        users_count = len(data.get('users', {}))
                    return self.reply_json(200, {'ok': True, 'meta': m, 'users_count': users_count, 'time': int(time.time())})
                return self.reply_json(404, {'ok': False, 'error': 'API endpoint not found'})

            if not self.check_rate_limit(bucket='web'):
                return self.reply(429, b'Too many requests')

            prefix = '/' + data['token'] + '/'
            if not self.path.startswith(prefix):
                return self.reply(404, b'Not found')

            subpath = self.path[len(prefix):]
            auth_header = self.headers.get('Authorization', '')
            is_client_api = subpath in ('clash.yaml', 'sing-box.json') or auth_header.startswith('Basic ')

            # 1. 专属用户独立页面与客户端直连下载路由 (可免管理员登录凭证，支持 ?k= 访问)
            if subpath.startswith('u/'):
                user_rest = subpath[2:].split('?', 1)[0]
                parts = user_rest.split('/', 1)
                target_uid = parts[0]
                action_file = parts[1] if len(parts) > 1 else ''

                if not VALID_USER_ID_RE.match(target_uid):
                    return self.reply(400, b'Invalid user_id format')

                with data_lock:
                    u = data.get('users', {}).get(target_uid)
                    if not u:
                        return self.reply(404, b'User not found')
                    u_copy = dict(u)

                query = parse_qs(self.path.split('?', 1)[1]) if '?' in self.path else {}
                k_val = query.get('k', [''])[0]
                expected_k = user_view_key(session_secret, target_uid)

                if not self.is_authenticated() and not (k_val and hmac.compare_digest(k_val, expected_k)):
                    return self.reply(403, b'Access denied: invalid key')

                m = json.loads(meta_path.read_text()) if meta_path.exists() else {}
                pwd = u_copy.get('password', '')
                uri, clash_yaml, sing_json = artifacts(m, auth_override=pwd, name_override=f"Hy2-{target_uid}")

                if action_file == 'clash.yaml':
                    return self.reply(200, clash_yaml.encode('utf-8'), 'application/yaml')
                elif action_file == 'sing-box.json':
                    return self.reply(200, sing_json.encode('utf-8'), 'application/json')
                elif action_file == 'qr.svg':
                    try:
                        qr_bytes = subprocess.run(['qrencode', '-t', 'SVG', '-o', '-'], input=uri.encode(), capture_output=True, check=True).stdout
                        return self.reply(200, qr_bytes, 'image/svg+xml')
                    except Exception:
                        return self.reply(500, b'QR generation failed')
                elif action_file == '':
                    try:
                        qr_svg = subprocess.run(['qrencode', '-t', 'SVG', '-o', '-'], input=uri.encode(), capture_output=True, check=True).stdout.decode('utf-8')
                    except Exception:
                        qr_svg = ''
                    server_name = m.get('server_name') or m.get('public_ip', 'localhost')
                    host = m.get('public_ip', server_name) if m.get('is_insecure') else server_name
                    listen_port = m.get('listen_port', 19984)
                    obfs_badge = "Salamander" if m.get('obfs_password') else "QUIC"
                    page = user_page_html(server_name, host, listen_port, obfs_badge, target_uid, u_copy, uri, clash_yaml, sing_json, qr_svg, data['token'], expected_k)
                    return self.reply(200, page.encode('utf-8'), 'text/html; charset=utf-8')
                else:
                    return self.reply(404, b'Not found')

            # 2. 用户专属配置 API (供管理后台弹窗使用，需管理员已登录认证)
            if subpath == 'warp-status':
                if not self.is_authenticated():
                    return self.reply_json(401, {'ok': False, 'error': 'Unauthorized'})
                with data_lock:
                    enabled = data.get('warp_enabled', False)
                # 简单本地探测 40000 端口连通性
                connected = False
                outbound_ip = ''
                if enabled:
                    try:
                        import urllib.request
                        proxy_handler = urllib.request.ProxyHandler({'http': 'socks5h://127.0.0.1:40000',
                                                                     'https': 'socks5h://127.0.0.1:40000'})
                        opener = urllib.request.build_opener(proxy_handler)
                        req = urllib.request.Request('https://api4.ipify.org', headers={'User-Agent': 'curl/7.88.1'})
                        with opener.open(req, timeout=3) as resp:
                            if resp.status == 200:
                                outbound_ip = resp.read().decode('utf-8').strip()
                                connected = True
                    except Exception:
                        connected = False
                return self.reply_json(200, {'ok': True, 'enabled': enabled, 'connected': connected, 'ip': outbound_ip})

            if subpath == 'user-config' or subpath.startswith('user-config?'):
                if not self.is_authenticated():
                    return self.reply_json(401, {'ok': False, 'error': 'Unauthorized'})
                query = parse_qs(self.path.split('?', 1)[1]) if '?' in self.path else {}
                target_uid = query.get('user_id', [''])[0].strip()
                if not VALID_USER_ID_RE.match(target_uid):
                    return self.reply_json(400, {'ok': False, 'error': 'Invalid user_id format'})
                with data_lock:
                    u = data.get('users', {}).get(target_uid)
                    if not u:
                        return self.reply_json(404, {'ok': False, 'error': 'User not found'})
                    u_copy = dict(u)

                m = json.loads(meta_path.read_text()) if meta_path.exists() else {}
                pwd = u_copy.get('password', '')
                uri, clash_yaml, sing_json = artifacts(m, auth_override=pwd, name_override=f"Hy2-{target_uid}")
                qr_svg = ""
                try:
                    qr_svg = subprocess.run(['qrencode', '-t', 'SVG', '-o', '-'], input=uri.encode(), capture_output=True, check=True).stdout.decode('utf-8')
                except Exception:
                    pass

                return self.reply_json(200, {
                    'ok': True,
                    'user_id': target_uid,
                    'note': u_copy.get('note', ''),
                    'uri': uri,
                    'clash': clash_yaml,
                    'sing_box': sing_json,
                    'qr_svg': qr_svg,
                    'expires_at': u_copy.get('expires_at', 0),
                    'traffic_used': u_copy.get('used_bytes', 0),
                    'traffic_limit': u_copy.get('limit_bytes', 0),
                    'ip_limit': u_copy.get('ip_limit', 0),
                })

            if not self.is_authenticated():
                if is_client_api:
                    self.record_failure()
                    return self.reply(401, b'Authentication required', www_auth=True)
                page = login_html(data['token'])
                return self.reply(200, page.encode('utf-8'), 'text/html; charset=utf-8')

            if subpath == '':
                regenerate_page()

            routes = {'': ('page', 'text/html; charset=utf-8'), 'qr.svg': ('qr', 'image/svg+xml'),
                      'clash.yaml': ('clash', 'application/yaml'), 'sing-box.json': ('sing', 'application/json')}
            route = routes.get(subpath)
            if route is None:
                return self.reply(404, b'Not found')
            key, mime = route
            with data_lock:
                content = data[key].encode()
            self.reply(200, content, mime)

        def reply(self, code, body, mime='text/plain', www_auth=False):
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Robots-Tag', 'noindex, nofollow, noarchive')
            self.send_header('Content-Security-Policy', content_policy())
            if www_auth:
                self.send_header('WWW-Authenticate', 'Basic realm="Private", charset="UTF-8"')
            if code == 429:
                self.send_header('Retry-After', '60')
            self.end_headers()
            self.wfile.write(body)

    class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True

    server = ThreadingHTTPServer(('127.0.0.1', data['port']), Handler)
    server.requests, server.failures, server.api_requests = [], [], []
    server.serve_forever()


if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        api_key = sys.argv[4] if len(sys.argv) > 4 else None
        prepare(sys.argv[2], sys.argv[3], api_key)
    elif sys.argv[1] == 'refresh':
        refresh(sys.argv[2])
    else:
        serve(sys.argv[2])
