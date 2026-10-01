"""门户前端资源（CSS / 内嵌 JS）。

🔴 这个文件里的 JS 常量必须是**原始字符串**（三引号前加 r）。
写成普通三引号字符串的话，源码里为 JS 字符串准备的 `\n` 会被 Python
在解析阶段转成真实换行、塞进 JS 单引号字符串里 —— JS 语法错误会让整段脚本
失效：页面能打开，但标签页切不动、所有按钮失灵。真实事故过一次。

由 portal.py 引入使用；部署时必须与 portal.py 成对存在（见 install.sh 的
portal_ensure_py —— 两个文件一起拉，要么都成功要么都不落地）。
"""


# ============================================================================
# STYLE
# ============================================================================
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
.speed-badge{display:inline-flex;align-items:center;gap:4px;background:#eef6f5;color:var(--accent);border-radius:6px;padding:2px 6px;font-size:11px;font-weight:700;font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
.speed-badge.active{background:#e1f5ee;color:#085041}
.speed-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:18px}
.speed-card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px;display:flex;align-items:center;justify-content:space-between}
.speed-card .val{font-size:20px;font-weight:800;letter-spacing:-.02em;color:var(--ink);font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
.speed-card .lbl{font-size:11px;color:var(--muted);font-weight:700;text-transform:uppercase}
.proxy-card{border-left:4px solid #534AB7}
.proxy-table{width:100%;border-collapse:collapse;text-align:left;font-size:13px}
.proxy-table th{background:#f8fbfb;padding:10px 12px;color:var(--muted);font-weight:700;border-bottom:1px solid var(--line);white-space:nowrap}
.proxy-table td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:middle}
.proxy-table tr:last-child td{border-bottom:none}
.proxy-type{display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
.proxy-type.socks5{background:#EEEDFE;color:#3C3489}
.proxy-type.http{background:#E6F1FB;color:#0C447C}
.proxy-type.https{background:#E1F5EE;color:#085041}
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

/* 代理成功专属弹窗高颜值设计 */
.pm-card{width:100%;max-width:650px;background:#fff;border:1px solid var(--line);border-radius:24px;padding:26px;box-shadow:0 24px 60px rgba(18,43,49,0.2);max-height:92vh;overflow-y:auto;display:flex;flex-direction:column;gap:16px}
.pm-banner{background:linear-gradient(135deg,#f0f8f6 0%,#f6faf9 100%);border:1.5px solid #cce8e1;border-radius:16px;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
.pm-host-box{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.pm-host-val{font-size:17px;font-weight:800;color:var(--ink);font-family:ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:-.02em}
.pm-port-val{color:var(--accent);font-weight:850}
.pm-status-tag{display:inline-flex;align-items:center;gap:4px;background:#e1f5ee;color:#085041;font-size:11px;font-weight:700;border-radius:20px;padding:3px 10px;border:1px solid #b7ebd8}
.pm-cred-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.pm-cred-card{background:#f8fbfb;border:1px solid var(--line);border-radius:12px;padding:12px 14px;display:flex;justify-content:space-between;align-items:center}
.pm-cred-lbl{font-size:11px;color:var(--muted);font-weight:700;margin-bottom:3px}
.pm-cred-val{font-size:13px;font-weight:750;color:var(--ink);font-family:ui-monospace,SFMono-Regular,Consolas,monospace;word-break:break-all}
.pm-main-grid{display:grid;grid-template-columns:140px minmax(0,1fr);gap:16px;align-items:center;background:#fafcfb;border:1px solid var(--line);border-radius:14px;padding:14px}
@media(max-width:560px){.pm-main-grid{grid-template-columns:1fr;justify-items:center}.pm-cred-grid{grid-template-columns:1fr}}
.pm-qr-frame{background:#fff;border:1px solid var(--line);border-radius:10px;padding:6px;display:flex;justify-content:center;align-items:center;width:130px;height:130px;box-shadow:0 3px 10px rgba(0,0,0,0.03)}
.pm-qr-frame svg{display:block;width:100%;height:100%}
.pm-links-stack{display:flex;flex-direction:column;gap:10px;min-width:0;width:100%}
.pm-code-box{display:flex;gap:6px;align-items:center;background:#fff;border:1px solid var(--line);border-radius:8px;padding:4px 6px 4px 10px;transition:border-color .15s}
.pm-code-box:focus-within{border-color:var(--accent);box-shadow:0 0 0 2px rgba(8,127,116,0.1)}
.pm-code-input{flex:1;min-width:0;border:none;background:transparent;font:11px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;color:#284d56;outline:none}

/* WARP 与自定义分流模块高阶专业排版 */
.warp-section { margin-top: 10px; }
.warp-switch-card { background: #f6faf9; border: 1px solid #d3e7e2; border-radius: 14px; padding: 16px 20px; margin-bottom: 20px; }
.warp-desc-title { font-size: 13.5px; font-weight: 750; color: #11342d; display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.warp-desc-text { font-size: 12.5px; color: #496861; line-height: 1.6; margin: 0; }

.warp-rules-card { background: #ffffff; border: 1px solid var(--line); border-radius: 16px; padding: 22px; box-shadow: 0 4px 16px rgba(18, 43, 49, 0.03); }
.warp-rules-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 10px; }
.warp-rules-title-box { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.warp-rules-title { font-size: 14px; font-weight: 800; color: var(--ink); margin: 0; }
.warp-count-badge { background: #eaf5ef; color: var(--accent); border: 1px solid #c0ded4; border-radius: 20px; padding: 3px 10px; font-size: 11.5px; font-weight: 700; }
.warp-reset-btn { background: #fff; border: 1px solid var(--line); color: var(--muted); border-radius: 8px; padding: 5px 12px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all .15s ease; }
.warp-reset-btn:hover { background: #f0f5f4; color: var(--ink); border-color: #b0d0c8; }

.warp-add-form { display: flex; gap: 10px; margin-bottom: 14px; }
@media(max-width: 600px) { .warp-add-form { flex-direction: column; } }
.warp-domain-input { flex: 1; height: 42px; padding: 0 14px; border: 1.5px solid var(--line); border-radius: 10px; font-size: 13px; color: var(--ink); background: #fdfefe; outline: none; transition: all .15s ease; }
.warp-domain-input:focus { border-color: var(--accent); background: #fff; box-shadow: 0 0 0 3px rgba(8, 127, 116, 0.12); }
.warp-add-btn { height: 42px; padding: 0 20px; font-size: 13px; font-weight: 700; border-radius: 10px; background: var(--accent); color: #fff; border: none; cursor: pointer; white-space: nowrap; transition: all .15s ease; }
.warp-add-btn:hover { filter: brightness(0.92); }

.warp-presets-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 18px; flex-wrap: wrap; font-size: 12px; color: var(--muted); }
.warp-preset-chip { display: inline-flex; align-items: center; gap: 4px; background: #f3f7f6; color: #2e554d; border: 1px solid #d4e5e1; border-radius: 14px; padding: 3px 10px; text-decoration: none; font-size: 11.5px; font-weight: 600; transition: all .15s ease; }
.warp-preset-chip:hover { background: #e6f3ef; border-color: var(--accent); color: var(--accent); transform: translateY(-1px); }

.warp-tags-wrap { display: flex; flex-wrap: wrap; gap: 8px; padding: 14px; background: #fafcfb; border: 1px solid var(--line); border-radius: 12px; min-height: 48px; align-items: center; }
.warp-tag-item { display: inline-flex; align-items: center; gap: 6px; background: #ffffff; border: 1.5px solid #cfe0dc; color: #184239; border-radius: 20px; padding: 5px 12px; font-size: 12.5px; font-weight: 650; box-shadow: 0 2px 6px rgba(18, 43, 49, 0.03); transition: all .15s ease; }
.warp-tag-item:hover { border-color: #a8cfc6; box-shadow: 0 3px 8px rgba(18, 43, 49, 0.06); }
.warp-tag-text { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; letter-spacing: -0.01em; }
.warp-tag-del { color: #d64545; text-decoration: none; font-size: 15px; line-height: 1; padding: 0 2px; font-weight: 800; cursor: pointer; border-radius: 50%; }
.warp-tag-del:hover { color: #a82020; transform: scale(1.2); }

/* BBR 拥塞控制模块全局专属高质感样式 */
.bbr-section { margin-top: 24px; border-left: 4px solid var(--accent); }
.bbr-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 14px; }
@media(max-width: 860px) { .bbr-grid { grid-template-columns: 1fr; } }
.bbr-card { background: #ffffff; border: 1.5px solid var(--line); border-radius: 16px; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; gap: 14px; box-shadow: 0 4px 14px rgba(18, 43, 49, 0.03); transition: all .18s ease; }
.bbr-card:hover { border-color: #a8cfc6; transform: translateY(-2px); box-shadow: 0 6px 20px rgba(18, 43, 49, 0.06); }
.bbr-card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.bbr-card-title { font-size: 14.5px; font-weight: 800; color: var(--ink); }
.bbr-card-desc { font-size: 12px; color: var(--muted); margin: 0; line-height: 1.6; }
.bbr-btn { width: 100%; height: 42px; font-size: 13px; font-weight: 750; border-radius: 10px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; transition: all .15s ease; border: 1px solid transparent; }
.bbr-btn.v1 { background: var(--accent); color: #fff; }
.bbr-btn.v1:hover { filter: brightness(0.92); }
.bbr-btn.v2 { background: #f6ffed; border-color: #b7eb8f; color: #237804; }
.bbr-btn.v2:hover { background: #d9f7be; }
.bbr-btn.v3 { background: #fff0f6; border-color: #ffd6e7; color: #c41d7f; }
.bbr-btn.v3:hover { background: #ffadd2; }

.bbr-info-bar { background: #f8fbfb; border: 1px solid var(--line); border-radius: 14px; padding: 16px 20px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
.bbr-stat-val { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; color: var(--accent); font-weight: 800; font-size: 14px; }
.bbr-sub-text { font-size: 12px; color: var(--muted); margin-top: 3px; }

/* 全局自定义高颜值确认弹窗与 Toast 样式 */
.confirm-card { width: 100%; max-width: 440px; background: #ffffff; border: 1.5px solid var(--line); border-radius: 20px; padding: 24px; box-shadow: 0 20px 50px rgba(18, 43, 49, 0.22); animation: scaleUp .18s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes scaleUp { from { opacity: 0; transform: scale(0.94); } to { opacity: 1; transform: scale(1); } }
.confirm-icon-box { width: 48px; height: 48px; border-radius: 14px; background: #eaf5ef; color: var(--accent); display: flex; align-items: center; justify-content: center; font-size: 24px; margin-bottom: 14px; }
.confirm-icon-box.danger { background: #fdf2f2; color: var(--danger); }
.confirm-icon-box.warn { background: #fff8e6; color: #d46b08; }
.confirm-title { font-size: 17px; font-weight: 800; color: var(--ink); margin-bottom: 8px; }
.confirm-text { font-size: 13px; color: var(--muted); line-height: 1.6; margin-bottom: 22px; }
.confirm-actions { display: flex; gap: 10px; justify-content: flex-end; }
.confirm-btn { height: 40px; padding: 0 18px; border-radius: 10px; font-size: 13px; font-weight: 700; cursor: pointer; transition: all .15s ease; border: 1px solid transparent; }
.confirm-btn.cancel { background: #f3f7f6; color: var(--ink); border-color: #d8e5e2; }
.confirm-btn.cancel:hover { background: #e5eeec; }
.confirm-btn.primary { background: var(--accent); color: #fff; }
.confirm-btn.primary:hover { filter: brightness(0.92); }
.confirm-btn.danger { background: var(--danger); color: #fff; }
.confirm-btn.danger:hover { filter: brightness(0.92); }

/* 全局 Toast 通知栏 */
.toast-container { position: fixed; top: 24px; right: 24px; z-index: 99999; display: flex; flex-direction: column; gap: 10px; pointer-events: none; }
.toast-item { background: #122b31; color: #ffffff; border-radius: 12px; padding: 12px 20px; font-size: 13px; font-weight: 650; box-shadow: 0 10px 30px rgba(0,0,0,0.18); display: flex; align-items: center; gap: 10px; pointer-events: auto; animation: toastIn .2s cubic-bezier(0.16, 1, 0.3, 1); }
.toast-item.success { background: #087f74; }
.toast-item.error { background: #cf3c3c; }
@keyframes toastIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }

/* ===== AmneziaWG 抗 DPI 协议卡片 ===== */
.awg-card { background: #ffffff; border: 1px solid var(--line); border-radius: 16px; padding: 22px; box-shadow: 0 4px 16px rgba(18, 43, 49, 0.03); }
.awg-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 10px; }
.awg-title-box { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.awg-title { font-size: 15px; font-weight: 800; color: var(--ink); margin: 0; }
.awg-desc { font-size: 12.5px; color: var(--muted); line-height: 1.7; margin: 0 0 14px; }
.awg-meta { display: flex; gap: 10px; flex-wrap: wrap; font-size: 12px; color: var(--muted); margin-bottom: 16px; }
.awg-meta span { background: #f3f7f6; border: 1px solid #d4e5e1; border-radius: 12px; padding: 4px 11px; font-weight: 650; }
.awg-install-box { background: #f8fbfa; border: 1px solid #d9ebe6; border-radius: 14px; padding: 16px 18px; margin-bottom: 18px; }
.awg-label { display: block; font-size: 12px; font-weight: 700; color: var(--muted); margin: 12px 0 5px; }
.awg-label:first-child { margin-top: 0; }
.awg-input, .awg-select { width: 100%; height: 40px; padding: 0 12px; border: 1.5px solid var(--line); border-radius: 10px; font-size: 13px; color: var(--ink); background: #fdfefe; outline: none; box-sizing: border-box; }
.awg-input:focus, .awg-select:focus { border-color: var(--accent); background: #fff; box-shadow: 0 0 0 3px rgba(8, 127, 116, 0.12); }
.awg-warn { font-size: 11.5px; color: #993c1d; background: #faece7; border: 1px solid #f5c4b3; border-radius: 10px; padding: 9px 12px; line-height: 1.6; margin: 12px 0 0; }
.awg-add-form { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.awg-add-form .awg-input { flex: 1; min-width: 150px; width: auto; }
.awg-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.awg-table th { text-align: left; font-size: 11.5px; color: var(--muted); font-weight: 700; padding: 8px 10px; border-bottom: 1px solid var(--line); white-space: nowrap; }
.awg-table td { padding: 10px; border-bottom: 1px solid #f0f4f3; color: var(--ink); vertical-align: middle; }
.awg-foot { display: flex; gap: 10px; margin-top: 16px; flex-wrap: wrap; }
.awg-hint { font-size: 11.5px; color: var(--muted); margin: 10px 0 0; line-height: 1.6; }
@media(max-width: 600px) { .awg-add-form { flex-direction: column; } .awg-add-form .awg-input { width: 100%; } }



"""

# ============================================================================
# SCRIPT
# ============================================================================
SCRIPT = r"""

// 全局高颜值 Promise 确认框与 Toast 机制
function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) { alert(msg); return; }
  const toast = document.createElement('div');
  toast.className = 'toast-item ' + type;
  const icon = type === 'success' ? '✓ ' : (type === 'error' ? '✕ ' : 'ℹ ');
  toast.textContent = icon + msg;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.transition = 'all .25s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-8px)';
    setTimeout(() => toast.remove(), 250);
  }, 2800);
}

function showConfirm(options = {}) {
  return new Promise((resolve) => {
    const modal = document.getElementById('custom-confirm-modal');
    const titleEl = document.getElementById('confirm-title');
    const textEl = document.getElementById('confirm-text');
    const iconEl = document.getElementById('confirm-icon');
    const okBtn = document.getElementById('confirm-btn-ok');
    const cancelBtn = document.getElementById('confirm-btn-cancel');

    if (!modal || !titleEl || !textEl || !okBtn || !cancelBtn) {
      resolve(confirm(options.text || '确定执行吗？'));
      return;
    }

    titleEl.textContent = options.title || '操作确认';
    textEl.textContent = options.text || '确定要继续执行吗？';
    if (iconEl) {
      iconEl.textContent = options.icon || '💡';
      iconEl.className = 'confirm-icon-box ' + (options.isDanger ? 'danger' : (options.isWarn ? 'warn' : ''));
    }

    okBtn.textContent = options.confirmText || '确定执行';
    okBtn.className = 'confirm-btn ' + (options.isDanger ? 'danger' : 'primary');

    modal.classList.add('show');

    function cleanup(result) {
      modal.classList.remove('show');
      okBtn.removeEventListener('click', onOk);
      cancelBtn.removeEventListener('click', onCancel);
      resolve(result);
    }

    function onOk() { cleanup(true); }
    function onCancel() { cleanup(false); }

    okBtn.addEventListener('click', onOk);
    cancelBtn.addEventListener('click', onCancel);
  });
}

// 🔴 删除用户的二次确认不能写成内联的 onsubmit="return confirm(...)"：
// CSP 的 script-src 只允许带哈希的脚本、没有 'unsafe-inline'，内联事件处理器
// 会被浏览器直接拒绝 —— 表现为点了「删除」毫无提示、用户被静默删掉。
// 必须在这里用 addEventListener 绑定。
document.querySelectorAll('form.js-confirm-delete').forEach(form => {
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    showConfirm({
      title: '注销用户',
      text: form.dataset.confirm || '确定注销此用户？此操作不可撤销。',
      icon: '⚠️',
      isDanger: true,
      confirmText: '确定注销'
    }).then(ok => { if (ok) form.submit(); });
  });
});

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

// WARP 状态与一键安装与自定义分流交互
const warpBadge = document.getElementById('warp-badge');
const btnToggleWarp = document.getElementById('btn-toggle-warp');
const btnInstallWarp = document.getElementById('btn-install-warp');
const warpTagsCloud = document.getElementById('warp-tags-cloud');
const warpRulesCount = document.getElementById('warp-rules-count');
const formAddWarpRule = document.getElementById('form-add-warp-rule');
const inputWarpDomain = document.getElementById('input-warp-domain');
const btnResetWarpRules = document.getElementById('btn-reset-warp-rules');

function renderWarpRules(rules) {
  if (!warpTagsCloud) return;
  if (warpRulesCount) warpRulesCount.textContent = rules.length + ' 个生效中';
  if (rules.length === 0) {
    warpTagsCloud.innerHTML = '<span style="font-size:12px;color:var(--muted)">暂无分流域名，上方输入即可快速添加</span>';
    return;
  }
  warpTagsCloud.innerHTML = rules.map(d => {
    // 🔴 不能写成 onclick="delWarpRule('...')"：CSP 的 script-src 只有哈希白名单、
    // 没有 'unsafe-inline'，内联事件会被浏览器直接丢弃，表现为"× 点了没反应"。
    // 改为 data-domain + 下方容器上的事件委托（对动态重渲染的标签同样生效）。
    return `<span class="warp-tag-item">
      <span class="warp-tag-text">${d}</span>
      <a href="javascript:void(0)" class="warp-tag-del" data-domain="${d}" title="移除此域名">×</a>
    </span>`;
  }).join('');
}

// WARP 分流标签的删除按钮：容器级事件委托（标签是动态重渲染的，不能逐个绑定）
if (warpTagsCloud) {
  warpTagsCloud.addEventListener('click', (e) => {
    const del = e.target.closest('.warp-tag-del');
    if (!del) return;
    e.preventDefault();
    const dom = del.getAttribute('data-domain');
    if (dom) delWarpRule(dom);
  });
}

async function addWarpRule(domain) {
  if (!domain) return;
  try {
    const res = await fetch(location.pathname + 'manage-warp', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'action=add_rule&domain=' + encodeURIComponent(domain)
    });
    const json = await res.json();
    if (json.ok) {
      if (inputWarpDomain) inputWarpDomain.value = '';
      if (Array.isArray(json.rules)) renderWarpRules(json.rules);
    } else {
      alert(json.error || '添加失败');
    }
  } catch (e) {
    alert('请求异常: ' + e.message);
  }
}

async function delWarpRule(domain) {
  if (!confirm('确定将 ' + domain + ' 从 WARP 分流列表中移除吗？')) return;
  try {
    const res = await fetch(location.pathname + 'manage-warp', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'action=del_rule&domain=' + encodeURIComponent(domain)
    });
    const json = await res.json();
    if (json.ok && Array.isArray(json.rules)) {
      renderWarpRules(json.rules);
    }
  } catch (e) {
    alert('请求异常: ' + e.message);
  }
}
window.delWarpRule = delWarpRule;

async function checkWarpStatus() {
  if (!warpBadge) return;
  try {
    const res = await fetch(location.pathname + 'warp-status', { credentials: 'same-origin' });
    if (!res.ok) return;
    const json = await res.json();
    if (!json.ok) return;

    if (btnInstallWarp) {
      if (!json.installed) {
        btnInstallWarp.style.display = 'inline-flex';
      } else {
        btnInstallWarp.style.display = 'none';
      }
    }

    if (!json.installed) {
      warpBadge.textContent = '● 未安装 WARP 客户端';
      warpBadge.style.background = '#fff1f0';
      warpBadge.style.color = '#cf3c3c';
      if (btnToggleWarp) btnToggleWarp.style.display = 'none';
      return;
    } else {
      if (btnToggleWarp) btnToggleWarp.style.display = 'inline-flex';
    }

    if (json.enabled) {
      warpBadge.textContent = json.connected ? ('● 运行中 (' + (json.ip || '已连通') + ')') : '● 正在连接 / 异常';
      warpBadge.style.background = json.connected ? '#eaf3de' : '#fff1f0';
      warpBadge.style.color = json.connected ? '#27500a' : '#cf3c3c';
      if (btnToggleWarp) {
        btnToggleWarp.textContent = '已开启 (点击关闭)';
        btnToggleWarp.className = 'toggle-btn on';
      }
    } else {
      warpBadge.textContent = '○ 已停用 (直连模式)';
      warpBadge.style.background = '#f1efe8';
      warpBadge.style.color = '#5f5e5a';
      if (btnToggleWarp) {
        btnToggleWarp.textContent = '已关闭 (点击开启)';
        btnToggleWarp.className = 'toggle-btn off';
      }
    }

    if (Array.isArray(json.rules)) {
      renderWarpRules(json.rules);
    }
  } catch (_) {}
}

if (btnToggleWarp) {
  btnToggleWarp.addEventListener('click', async () => {
    btnToggleWarp.disabled = true;
    btnToggleWarp.textContent = '切换中...';
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
      await checkWarpStatus();
    }
  });
}

if (btnInstallWarp) {
  btnInstallWarp.addEventListener('click', async () => {
    if (!confirm("确定要在服务器上一键部署 Cloudflare WARP 本地出口吗？将自动安装 wgcf + wireproxy，并启用 127.0.0.1:19898 的 socks5 出口。")) return;
    btnInstallWarp.disabled = true;
    const origText = btnInstallWarp.textContent;
    btnInstallWarp.textContent = '⏳ 正在安装 WARP (耗时约 30 秒)...';
    try {
      const res = await fetch(location.pathname + 'install-warp', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      if (!res.ok) {
        const errText = await res.text();
        showToast('安装失败 (HTTP ' + res.status + '): ' + errText, 'error');
        return;
      }
      const json = await res.json();
      if (json.ok) {
        showToast(json.message || 'Cloudflare WARP 安装成功！服务已自动就绪。', 'success');
        await checkWarpStatus();
      } else {
        showToast(json.error || '安装失败，请检查网络', 'error');
      }
    } catch (e) {
      showToast('安装请求异常: ' + e.message, 'error');
    } finally {
      btnInstallWarp.disabled = false;
      btnInstallWarp.textContent = origText;
    }
  });
}

if (formAddWarpRule) {
  formAddWarpRule.addEventListener('submit', (e) => {
    e.preventDefault();
    if (inputWarpDomain) addWarpRule(inputWarpDomain.value.trim());
  });
}

document.querySelectorAll('.preset-rule').forEach(el => {
  el.addEventListener('click', () => {
    const dom = el.getAttribute('data-domain');
    if (dom) addWarpRule(dom);
  });
});

if (btnResetWarpRules) {
  btnResetWarpRules.addEventListener('click', async () => {
    if (!confirm('确定重置为系统默认推荐的 AI 域名规则列表吗？')) return;
    try {
      const res = await fetch(location.pathname + 'manage-warp', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'action=reset_rules'
      });
      const json = await res.json();
      if (json.ok && Array.isArray(json.rules)) {
        renderWarpRules(json.rules);
      }
    } catch (e) {
      alert('请求异常: ' + e.message);
    }
  });
}

checkWarpStatus();

// VLESS-Reality 客户端与状态交互
const realityBadge = document.getElementById('reality-badge');
const btnInstallXray = document.getElementById('btn-install-xray');
const btnToggleReality = document.getElementById('btn-toggle-reality');
const realityContentBox = document.getElementById('reality-content-box');
const realityUriVal = document.getElementById('reality-uri-val');
const realityQrBox = document.getElementById('reality-qr-box');
const realitySniVal = document.getElementById('reality-sni-val');
const realityUuidVal = document.getElementById('reality-uuid-val');
const realityPubkeyVal = document.getElementById('reality-pubkey-val');
const realityFlowVal = document.getElementById('reality-flow-val');
const btnCopyRealityUri = document.getElementById('btn-copy-reality-uri');
const btnResetRealityKeys = document.getElementById('btn-reset-reality-keys');

async function checkRealityStatus() {
  if (!realityBadge) return;
  try {
    const res = await fetch(location.pathname + 'reality-status', { credentials: 'same-origin' });
    if (!res.ok) return;
    const json = await res.json();
    if (!json.ok) return;

    if (!json.installed) {
      realityBadge.textContent = '● 未安装 Xray 核心';
      realityBadge.style.background = '#fff1f0';
      realityBadge.style.color = '#cf3c3c';
      if (btnInstallXray) btnInstallXray.style.display = 'inline-flex';
      if (btnToggleReality) btnToggleReality.style.display = 'none';
      if (realityContentBox) realityContentBox.style.display = 'none';
      return;
    }

    if (btnInstallXray) btnInstallXray.style.display = 'none';
    if (btnToggleReality) btnToggleReality.style.display = 'inline-flex';

    if (json.active) {
      realityBadge.textContent = '● 运行中 (TCP 443 端口)';
      realityBadge.style.background = '#eaf3de';
      realityBadge.style.color = '#27500a';
      btnToggleReality.textContent = '已开启 (点击关闭)';
      btnToggleReality.className = 'toggle-btn on';
      if (realityContentBox) realityContentBox.style.display = 'block';
    } else {
      realityBadge.textContent = '○ 已停止';
      realityBadge.style.background = '#f1efe8';
      realityBadge.style.color = '#5f5e5a';
      btnToggleReality.textContent = '已关闭 (点击开启)';
      btnToggleReality.className = 'toggle-btn off';
      if (realityContentBox) realityContentBox.style.display = 'none';
    }

    if (json.config) {
      const cfg = json.config;
      if (realityUriVal) realityUriVal.value = cfg.uri || '';
      if (realityQrBox && cfg.qr_svg) realityQrBox.innerHTML = cfg.qr_svg;
      if (realitySniVal) realitySniVal.textContent = (cfg.sni || 'www.apple.com') + ':' + (cfg.port || 443);
      if (realityUuidVal) realityUuidVal.textContent = cfg.uuid || '-';
      if (realityPubkeyVal) realityPubkeyVal.textContent = cfg.pub_key || '-';
      if (realityFlowVal) realityFlowVal.textContent = (cfg.short_id || '') + ' · ' + (cfg.flow || 'xtls-rprx-vision');
    }
  } catch (_) {}
}

if (btnInstallXray) {
  btnInstallXray.addEventListener('click', async () => {
    if (!confirm("确定要一键安装 Xray 官方核心并部署 VLESS-Reality 节点吗？")) return;
    btnInstallXray.disabled = true;
    const orig = btnInstallXray.textContent;
    btnInstallXray.textContent = '⏳ 正在下载并配置 Xray (约 20-30 秒)...';
    try {
      const res = await fetch(location.pathname + 'install-xray', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      const json = await res.json();
      if (json.ok) {
        alert(json.message || 'Xray-core 安装并启动成功！');
        await checkRealityStatus();
      } else {
        alert(json.error || '安装失败');
      }
    } catch (e) {
      alert('请求异常: ' + e.message);
    } finally {
      btnInstallXray.disabled = false;
      btnInstallXray.textContent = orig;
    }
  });
}

if (btnToggleReality) {
  btnToggleReality.addEventListener('click', async () => {
    btnToggleReality.disabled = true;
    btnToggleReality.textContent = '切换中...';
    try {
      const res = await fetch(location.pathname + 'manage-reality', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'action=toggle'
      });
      const json = await res.json();
      if (!json.ok) alert(json.error || '切换失败');
      await checkRealityStatus();
    } catch (e) {
      alert('请求异常: ' + e.message);
    } finally {
      btnToggleReality.disabled = false;
    }
  });
}

if (btnResetRealityKeys) {
  btnResetRealityKeys.addEventListener('click', async () => {
    if (!confirm("确定要重新生成 UUID 与 Reality 密钥对吗？旧客户端连接凭据将失效。")) return;
    try {
      const res = await fetch(location.pathname + 'manage-reality', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'action=reset'
      });
      const json = await res.json();
      if (json.ok) {
        alert('密钥与 UUID 已重新生成并生效！');
        await checkRealityStatus();
      } else {
        alert(json.error || '重置失败');
      }
    } catch (e) {
      alert('请求异常: ' + e.message);
    }
  });
}

if (btnCopyRealityUri) {
  btnCopyRealityUri.addEventListener('click', () => {
    if (realityUriVal && realityUriVal.value) {
      navigator.clipboard.writeText(realityUriVal.value).then(() => {
        const orig = btnCopyRealityUri.textContent;
        btnCopyRealityUri.textContent = '✓ 已复制直链';
        setTimeout(() => btnCopyRealityUri.textContent = orig, 1500);
      });
    }
  });
}

checkRealityStatus();

// BBR 状态获取与一键切换交互
const bbrBadge = document.getElementById('bbr-badge');
const bbrCurrentText = document.getElementById('bbr-current-text');
const bbrQdiscText = document.getElementById('bbr-qdisc-text');
const bbrKernelText = document.getElementById('bbr-kernel-text');
const bbrRebootTip = document.getElementById('bbr-reboot-tip');
const btnRebootServer = document.getElementById('btn-reboot-server');

async function checkBbrStatus() {
  if (!bbrBadge) return;
  try {
    const res = await fetch(location.pathname + 'bbr-status', { credentials: 'same-origin' });
    if (!res.ok) return;
    const json = await res.json();
    if (!json.ok) return;

    if (bbrCurrentText) bbrCurrentText.textContent = json.current || 'cubic';
    if (bbrQdiscText) bbrQdiscText.textContent = json.qdisc || 'fq_codel';
    if (bbrKernelText) bbrKernelText.textContent = json.kernel || '--';

    const isBbrActive = (json.current && json.current.includes('bbr'));
    if (bbrBadge) {
      if (isBbrActive) {
        bbrBadge.textContent = '● 已开启 ' + json.current.toUpperCase();
        bbrBadge.style.background = '#eaf3de';
        bbrBadge.style.color = '#27500a';
      } else {
        bbrBadge.textContent = '○ 未开启 BBR (' + json.current + ')';
        bbrBadge.style.background = '#f1efe8';
        bbrBadge.style.color = '#5f5e5a';
      }
    }

    if (bbrRebootTip && btnRebootServer) {
      if (json.need_reboot) {
        bbrRebootTip.style.display = 'block';
        bbrRebootTip.textContent = '⚠️ 已成功配置 ' + json.configured.toUpperCase() + '，需要重启服务器后生效！';
        btnRebootServer.style.display = 'inline-flex';
      } else {
        bbrRebootTip.style.display = 'none';
        btnRebootServer.style.display = 'none';
      }
    }
  } catch (_) {}
}

document.querySelectorAll('.btn-apply-bbr').forEach(btn => {
  btn.addEventListener('click', async () => {
    const ver = btn.getAttribute('data-version') || 'v1';
    const label = { v1: 'BBR V1 (经典官方)', v2: 'BBR V2 (低丢包)', v3: 'BBR V3 (极限吞吐)' }[ver];
    const confirmed = await showConfirm({
      title: '开启 ' + label + ' 加速引擎',
      text: '系统将自动将拥塞控制与排队规则写入 Linux 内核持久化配置（/etc/sysctl.d/99-bbr.conf）。配置后可能需要安全重启服务器以完成生效。',
      icon: '🚀',
      confirmText: '立即开启 ' + ver.toUpperCase()
    });
    if (!confirmed) return;

    btn.disabled = true;
    const orig = btn.textContent;
    btn.textContent = '正在配置...';
    try {
      const res = await fetch(location.pathname + 'set-bbr', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'version=' + encodeURIComponent(ver)
      });
      const json = await res.json();
      if (json.ok) {
        showToast(json.message || '配置成功！', 'success');
        await checkBbrStatus();
      } else {
        showToast(json.error || '配置失败', 'error');
      }
    } catch (e) {
      alert('请求异常: ' + e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = orig;
    }
  });
});

if (btnRebootServer) {
  btnRebootServer.addEventListener('click', async () => {
    const confirmed = await showConfirm({
      title: '安全重启服务器',
      text: '确定要立即重启服务器以完成新 BBR 内核网络参数生效吗？服务器将在 10 秒内安全完成重启，页面将自动发起 25 秒倒计时并在就绪后重连。',
      icon: '🔄',
      confirmText: '确定立即重启',
      isWarn: true
    });
    if (!confirmed) return;
    btnRebootServer.disabled = true;
    btnRebootServer.textContent = '⏳ 重启指令已发送...';
    try {
      const res = await fetch(location.pathname + 'reboot-server', {
        method: 'POST',
        credentials: 'same-origin'
      });
      alert("服务器正在重启中，系统将在 25 秒后自动刷新页面！");
      let countdown = 25;
      const timer = setInterval(() => {
        countdown--;
        btnRebootServer.textContent = '正在重启中 (' + countdown + 's)...';
        if (countdown <= 0) {
          clearInterval(timer);
          location.reload();
        }
      }, 1000);
    } catch (e) {
      alert("重启请求已发出: " + e.message);
    }
  });
}

checkBbrStatus();

// 版本检测与一键更新交互
const coreVerDisplay = document.getElementById('core-ver-display');
const portalVerDisplay = document.getElementById('portal-ver-display');
const awgVerDisplay = document.getElementById('awg-ver-display');
const btnUpdateCore = document.getElementById('btn-update-core');
const btnUpdatePortal = document.getElementById('btn-update-portal');
const btnUpdateAwgEngine = document.getElementById('btn-update-awg-engine');
const updateStatusMsg = document.getElementById('update-status-msg');
const btnRecheckUpdate = document.getElementById('btn-recheck-update');

// 版本展示：区分「未安装 / 拿不到远端 / 有新版本 / 最新」四种情况，
// 避免拿不到远端时误报「最新」。
function fmtVer(current, latest, hasUpdate, installed) {
  if (installed === false) return '未安装';
  if (!current || current === '未安装') return '未安装';
  if (!latest) return current + '（远端未取到，无法比对）';
  return hasUpdate ? (current + ' → ' + latest + ' 有新版本') : (current + '（最新）');
}

async function checkVersions() {
  if (!coreVerDisplay || !portalVerDisplay) return;
  try {
    const res = await fetch(location.pathname + 'check-version', { credentials: 'same-origin' });
    if (!res.ok) return;
    const json = await res.json();
    if (!json.ok) return;

    // 核心展示
    coreVerDisplay.textContent = json.core_current + (json.core_has_update ? (' → 可升级至 ' + json.core_latest) : ' (最新)');
    if (btnUpdateCore) {
      btnUpdateCore.style.display = json.core_has_update ? 'inline-flex' : 'none';
      btnUpdateCore.onclick = () => doUpgrade('core');
    }

    // 面板展示
    portalVerDisplay.textContent = fmtVer(json.portal_current, json.portal_latest, json.portal_has_update, true);
    if (btnUpdatePortal) {
      btnUpdatePortal.style.display = json.portal_has_update ? 'inline-flex' : 'none';
      btnUpdatePortal.onclick = () => doUpgrade('portal');
    }

    // AmneziaWG 引擎展示
    if (awgVerDisplay) {
      awgVerDisplay.textContent = fmtVer(json.awg_current, json.awg_latest, json.awg_has_update, json.awg_installed);
      if (btnUpdateAwgEngine) {
        btnUpdateAwgEngine.style.display = json.awg_has_update ? 'inline-flex' : 'none';
        btnUpdateAwgEngine.onclick = () => doUpgrade('awg');
      }
    }
  } catch (_) {}
}

async function doUpgrade(target) {
  const names = { core: 'Hysteria 2 官方核心', portal: '控制面板自身', awg: 'AmneziaWG 引擎' };
  const btns = { core: btnUpdateCore, portal: btnUpdatePortal, awg: btnUpdateAwgEngine };
  const btn = btns[target];
  if (!confirm('确定要升级 ' + (names[target] || target) + ' 吗？')) return;
  if (btn) { btn.disabled = true; btn.textContent = '升级中...'; }
  if (updateStatusMsg) updateStatusMsg.textContent = '正在下载并应用更新，请稍候...';
  try {
    const res = await fetch(location.pathname + 'do-upgrade', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'target=' + encodeURIComponent(target)
    });
    const json = await res.json();
    if (json.ok) {
      const msg = json.message || '升级已触发';
      if (updateStatusMsg) updateStatusMsg.textContent = msg + '，5 秒后自动刷新页面...';
      setTimeout(() => location.reload(), 5000);
    } else {
      alert(json.error || '升级失败');
      if (updateStatusMsg) updateStatusMsg.textContent = json.error || '升级失败';
      if (btn) { btn.disabled = false; btn.textContent = '重试升级'; }
    }
  } catch (e) {
    alert('升级请求异常: ' + e.message);
    if (btn) { btn.disabled = false; btn.textContent = '重试升级'; }
  }
}

if (btnRecheckUpdate) {
  btnRecheckUpdate.addEventListener('click', async () => {
    if (updateStatusMsg) updateStatusMsg.textContent = '正在检测...';
    await checkVersions();
    if (updateStatusMsg) updateStatusMsg.textContent = '检测完成（远端结果在服务端缓存 5 分钟）';
  });
}

checkVersions();

// 实时吞吐量与网速轮询 (每 2 秒更新一次)
const speedRxEl = document.getElementById('node-speed-rx');
const speedTxEl = document.getElementById('node-speed-tx');
const rxTagEl = document.getElementById('rx-active-tag');
const txTagEl = document.getElementById('tx-active-tag');

function fmtSpeed(bytesPerSec) {
  if (bytesPerSec < 1024) return bytesPerSec.toFixed(0) + ' B/s';
  if (bytesPerSec < 1024 * 1024) return (bytesPerSec / 1024).toFixed(1) + ' KB/s';
  return (bytesPerSec / (1024 * 1024)).toFixed(2) + ' MB/s';
}

async function pollTrafficSpeed() {
  try {
    const res = await fetch(location.pathname + 'traffic-speed', { credentials: 'same-origin' });
    if (!res.ok) return;
    const json = await res.json();
    if (!json.ok) return;

    if (speedRxEl) speedRxEl.textContent = fmtSpeed(json.node_rx || 0);
    if (speedTxEl) speedTxEl.textContent = fmtSpeed(json.node_tx || 0);

    if (rxTagEl) rxTagEl.className = (json.node_rx > 1024) ? 'speed-badge active' : 'speed-badge';
    if (txTagEl) txTagEl.className = (json.node_tx > 1024) ? 'speed-badge active' : 'speed-badge';

    // 更新各个用户的实时速率标签
    if (json.users) {
      document.querySelectorAll('[data-user-speed]').forEach(badge => {
        const uid = badge.dataset.userSpeed;
        const u = json.users[uid];
        if (u && (u.rx > 0 || u.tx > 0)) {
          badge.textContent = '↓ ' + fmtSpeed(u.rx) + ' · ↑ ' + fmtSpeed(u.tx);
          badge.className = 'speed-badge active';
        } else {
          badge.textContent = '↓ 0 B/s · ↑ 0 B/s';
          badge.className = 'speed-badge';
        }
      });
    }
  } catch (_) {}
}

setInterval(pollTrafficSpeed, 2000);
pollTrafficSpeed();

// 入站代理服务管理 (gost 驱动)
const gostBadge = document.getElementById('gost-badge');
const proxyTbody = document.getElementById('proxy-tbody');
const btnInstallGost = document.getElementById('btn-install-gost');
const proxyModal = document.getElementById('proxy-modal');
const pmClose = document.getElementById('pm-close');
const resPType = document.getElementById('res-ptype');
const resPHost = document.getElementById('res-phost');
const resPPort = document.getElementById('res-pport');
const resPUser = document.getElementById('res-puser');
const resPPass = document.getElementById('res-ppass');
const resPUrl = document.getElementById('res-purl');
const resPFmt = document.getElementById('res-pfmt');
const btnCopyPUrl = document.getElementById('btn-copy-purl');
const btnCopyPFmt = document.getElementById('btn-copy-pfmt');

let curProxyServerHost = location.hostname;

function closeProxyModal() {
  if (proxyModal) proxyModal.classList.remove('show');
}
if (pmClose) pmClose.addEventListener('click', closeProxyModal);
if (proxyModal) {
  proxyModal.addEventListener('click', (e) => {
    if (e.target === proxyModal) closeProxyModal();
  });
}

const resPTypeBadge = document.getElementById('res-ptype-badge');
const resPQr = document.getElementById('res-pqr');

function showProxyResult(data) {
  if (!proxyModal) return;
  const host = data.host || curProxyServerHost;
  const ptype = data.type || 'socks5';
  const url = data.url || (ptype + '://' + data.username + ':' + data.password + '@' + host + ':' + data.port);
  const fmt = data.format || (host + ':' + data.port + ':' + data.username + ':' + data.password);

  if (resPTypeBadge) {
    resPTypeBadge.textContent = ptype.toUpperCase();
    resPTypeBadge.className = 'proxy-type ' + ptype;
  }
  if (resPHost) resPHost.textContent = host;
  if (resPPort) resPPort.textContent = data.port;
  if (resPUser) resPUser.textContent = data.username;
  if (resPPass) resPPass.textContent = data.password;
  if (resPUrl) resPUrl.value = url;
  if (resPFmt) resPFmt.value = fmt;

  if (resPQr && data.qr) {
    resPQr.innerHTML = data.qr;
  }

  if (btnCopyPUrl) {
    btnCopyPUrl.onclick = async () => {
      try {
        await navigator.clipboard.writeText(url);
        btnCopyPUrl.textContent = '已复制 ✓';
        setTimeout(() => { btnCopyPUrl.textContent = '复制 URL'; }, 1800);
      } catch (_) { alert('复制失败，请手动选择复制'); }
    };
  }

  if (btnCopyPFmt) {
    btnCopyPFmt.onclick = async () => {
      try {
        await navigator.clipboard.writeText(fmt);
        btnCopyPFmt.textContent = '已复制 ✓';
        setTimeout(() => { btnCopyPFmt.textContent = '复制格式'; }, 1800);
      } catch (_) { alert('复制失败，请手动选择复制'); }
    };
  }

  document.querySelectorAll('[data-copy-field]').forEach(b => {
    b.onclick = async () => {
      const el = document.getElementById(b.dataset.copyField);
      if (el) {
        try {
          await navigator.clipboard.writeText(el.textContent);
          const orig = b.textContent;
          b.textContent = '✓';
          setTimeout(() => { b.textContent = orig; }, 1500);
        } catch (_) {}
      }
    };
  });

  proxyModal.classList.add('show');
}

// 绑定秒级一键生成按钮
document.querySelectorAll('.btn-quick-proxy').forEach(btn => {
  btn.addEventListener('click', async () => {
    const ptype = btn.dataset.ptype;
    const cPortEl = document.getElementById('custom-proxy-port');
    const customPort = cPortEl ? cPortEl.value.trim() : '';
    btn.disabled = true;
    const origText = btn.textContent;
    btn.textContent = '⚡ 正在生成...';
    try {
      let body = 'action=create&type=' + encodeURIComponent(ptype);
      if (customPort) body += '&port=' + encodeURIComponent(customPort);

      const res = await fetch(location.pathname + 'manage-proxy', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body
      });
      const json = await res.json();
      if (json.ok) {
        if (cPortEl) cPortEl.value = '';
        showProxyResult(json);
        loadProxyServices();
      } else {
        alert(json.error || '生成失败');
      }
    } catch (e) {
      alert('生成异常: ' + e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = origText;
    }
  });
});

if (btnInstallGost) {
  btnInstallGost.addEventListener('click', async () => {
    if (!confirm("确定要一键安装或更新 GOST 代理服务吗？系统将自动匹配架构并配置自启。")) return;
    btnInstallGost.disabled = true;
    const origText = btnInstallGost.textContent;
    btnInstallGost.textContent = '⏳ 正在安装 GOST...';
    try {
      const res = await fetch(location.pathname + 'install-gost', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      const json = await res.json();
      if (json.ok) {
        alert(json.message || 'GOST 安装成功！服务已就绪。');
        loadProxyServices();
      } else {
        alert(json.error || '安装失败，请检查服务器网络或日志');
      }
    } catch (e) {
      alert('安装请求异常: ' + e.message);
    } finally {
      btnInstallGost.disabled = false;
      btnInstallGost.textContent = origText;
    }
  });
}

async function loadProxyServices() {
  if (!proxyTbody) return;
  try {
    const res = await fetch(location.pathname + 'proxy-services', { credentials: 'same-origin' });
    if (!res.ok) return;
    const json = await res.json();
    if (!json.ok) return;

    if (gostBadge) {
      if (!json.gost_installed) {
        gostBadge.textContent = '● 未安装 gost';
        gostBadge.style.background = '#fff1f0';
        gostBadge.style.color = '#cf3c3c';
        if (btnInstallGost) {
          btnInstallGost.style.display = 'inline-flex';
          btnInstallGost.textContent = '⚡ 一键安装 GOST';
        }
      } else if (json.gost_active) {
        gostBadge.textContent = '● gost 运行中';
        gostBadge.style.background = '#eaf3de';
        gostBadge.style.color = '#27500a';
        if (btnInstallGost) {
          btnInstallGost.style.display = 'none';
        }
      } else {
        gostBadge.textContent = '● gost 未启动';
        gostBadge.style.background = '#f1efe8';
        gostBadge.style.color = '#5f5e5a';
        if (btnInstallGost) {
          btnInstallGost.style.display = 'inline-flex';
          btnInstallGost.textContent = '🔄 重启/修复 GOST';
        }
      }
    }

    const services = json.services || [];
    if (services.length === 0) {
      proxyTbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:24px">暂无代理服务，点击上方「添加代理服务」创建</td></tr>';
      return;
    }
    if (json.host) curProxyServerHost = json.host;
    const typeLabel = { socks5: 'SOCKS5', http: 'HTTP', https: 'HTTPS' };
    proxyTbody.innerHTML = services.map(s => {
      const fullUrl = `${s.type}://${s.username}:${s.password}@${curProxyServerHost}:${s.port}`;
      return `
      <tr>
        <td><span class="proxy-type ${s.type}">${typeLabel[s.type] || s.type}</span></td>
        <td><code style="font-size:12px;font-weight:700;color:var(--accent)">:${s.port}</code></td>
        <td><code style="font-size:12px">${s.username}</code></td>
        <td><code style="font-size:12px">${s.password}</code></td>
        <td>
          <div style="display:flex;align-items:center;gap:6px">
            <code style="font-size:11px;background:#f5f8f7;padding:2px 6px;border-radius:4px;word-break:break-all">${s.type}://${s.username}:****@${curProxyServerHost}:${s.port}</code>
            <button class="button" style="padding:2px 8px;font-size:11px;white-space:nowrap" type="button" data-copy-link="${fullUrl}">复制链接</button>
          </div>
        </td>
        <td><button class="button danger" style="padding:4px 10px;font-size:11px" type="button" data-proxy-del="${s.id}">删除</button></td>
      </tr>`;
    }).join('');

    proxyTbody.querySelectorAll('[data-copy-link]').forEach(btn => {
      btn.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(btn.dataset.copyLink);
          const orig = btn.textContent;
          btn.textContent = '已复制 ✓';
          setTimeout(() => { btn.textContent = orig; }, 1800);
        } catch (_) { alert('复制失败'); }
      });
    });
    proxyTbody.querySelectorAll('[data-proxy-del]').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('确定删除该代理服务？')) return;
        const res = await fetch(location.pathname + 'manage-proxy', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: 'action=delete&id=' + encodeURIComponent(btn.dataset.proxyDel)
        });
        const json = await res.json();
        if (json.ok) loadProxyServices();
        else alert(json.error || '删除失败');
      });
    });
  } catch (_) {}
}

// proxyForm replaced with instant buttons

loadProxyServices();

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

/* ==================== AmneziaWG 抗 DPI 协议管理 ==================== */
const awgBadge = document.getElementById('awg-badge');
const awgInstallBox = document.getElementById('awg-install-box');
const btnInstallAwg = document.getElementById('btn-install-awg');
const btnDoInstallAwg = document.getElementById('btn-do-install-awg');
const awgLineSelect = document.getElementById('awg-line-select');
const awgEndpointInput = document.getElementById('awg-endpoint-input');
const awgMetaBox = document.getElementById('awg-meta');
const awgMetaLine = document.getElementById('awg-meta-line');
const awgMetaPort = document.getElementById('awg-meta-port');
const awgMetaPeers = document.getElementById('awg-meta-peers');
const awgMetaChip = document.getElementById('awg-meta-chip');
const awgPanel = document.getElementById('awg-panel');
const awgPeerTbody = document.getElementById('awg-peer-tbody');
const awgPeerName = document.getElementById('awg-peer-name');
const awgPeerEndpoint = document.getElementById('awg-peer-endpoint');
const btnAddAwgPeer = document.getElementById('btn-add-awg-peer');
const btnSwitchAwgLine = document.getElementById('btn-switch-awg-line');
const btnUpdateAwg = document.getElementById('btn-update-awg');
let awgCurrentEndpoint = '';
let awgCurrentLine = '3';

function awgPost(endpoint, params) {
  return fetch(location.pathname + endpoint, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(params).toString()
  }).then(r => r.json()).catch(e => ({ ok: false, error: '请求异常: ' + e.message }));
}

function setAwgBadge(text, bg, color) {
  if (!awgBadge) return;
  awgBadge.textContent = text;
  awgBadge.style.background = bg;
  awgBadge.style.color = color;
}

async function loadAwgState() {
  if (!awgBadge) return;
  try {
    const res = await fetch(location.pathname + 'awg-state', { credentials: 'same-origin' });
    if (!res.ok) return;
    const json = await res.json();
    if (!json.ok) return;

    awgCurrentEndpoint = json.endpoint || '';
    awgCurrentLine = json.line || '3';
    if (awgEndpointInput && !awgEndpointInput.value) awgEndpointInput.value = awgCurrentEndpoint;
    if (awgPeerEndpoint && !awgPeerEndpoint.value) awgPeerEndpoint.value = awgCurrentEndpoint;
    if (awgMetaChip) awgMetaChip.textContent = json.installed ? ('AWG ' + awgCurrentLine + '.x') : '未安装';

    if (!json.installed) {
      setAwgBadge('● 未安装 AmneziaWG', '#fff1f0', '#cf3c3c');
      if (awgMetaBox) awgMetaBox.style.display = 'none';
      if (awgPanel) awgPanel.style.display = 'none';
      if (awgInstallBox) awgInstallBox.style.display = 'none';
      if (btnInstallAwg) { btnInstallAwg.style.display = 'inline-flex'; btnInstallAwg.textContent = '⚡ 一键安装 AmneziaWG'; }
      return;
    }

    if (awgLineSelect && awgCurrentLine) awgLineSelect.value = awgCurrentLine;

    if (json.active) {
      setAwgBadge('● AmneziaWG 运行中', '#eaf3de', '#27500a');
    } else {
      setAwgBadge('● AmneziaWG 已安装未运行', '#f1efe8', '#5f5e5a');
    }
    if (btnInstallAwg) btnInstallAwg.style.display = 'none';
    if (awgInstallBox) awgInstallBox.style.display = 'none';
    if (awgMetaBox) awgMetaBox.style.display = 'flex';
    if (awgMetaLine) awgMetaLine.textContent = '协议线 AWG ' + awgCurrentLine + '.x';
    if (awgMetaPort) awgMetaPort.textContent = 'UDP ' + (json.port || '未知');
    if (awgMetaPeers) awgMetaPeers.textContent = '客户端 ' + (json.peer_count || 0) + ' 个';
    if (awgPanel) awgPanel.style.display = 'block';

    renderAwgPeers(json.peers || []);
  } catch (e) { /* 静默失败，不打扰主界面 */ }
}

function renderAwgPeers(peers) {
  if (!awgPeerTbody) return;
  if (!peers.length) {
    awgPeerTbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--muted);padding:20px">暂无客户端，用上方表单新增</td></tr>';
    return;
  }
  awgPeerTbody.innerHTML = peers.map(p => {
    const enc = encodeURIComponent(p.name);
    const bs = 'padding:3px 10px;font-size:11px';
    return '<tr>'
      + '<td><strong>' + p.name + '</strong></td>'
      + '<td>' + p.address + '</td>'
      + '<td style="color:var(--muted);font-size:11.5px">' + (p.created_at || '-') + '</td>'
      + '<td style="white-space:nowrap">'
      + '<button class="button" type="button" data-awg-conf="' + enc + '" style="' + bs + '">下载配置</button> '
      + '<button class="button" type="button" data-awg-qr="' + enc + '" style="' + bs + '">二维码</button> '
      + '<button class="button" type="button" data-awg-del="' + enc + '" style="' + bs + ';color:#cf3c3c">删除</button>'
      + '</td></tr>';
  }).join('');

  awgPeerTbody.querySelectorAll('[data-awg-conf]').forEach(b => {
    b.addEventListener('click', () => {
      window.open(location.pathname + 'awg-conf?name=' + b.getAttribute('data-awg-conf'), '_blank');
    });
  });
  awgPeerTbody.querySelectorAll('[data-awg-qr]').forEach(b => {
    b.addEventListener('click', () => {
      window.open(location.pathname + 'awg-qr.svg?name=' + b.getAttribute('data-awg-qr'), '_blank');
    });
  });
  awgPeerTbody.querySelectorAll('[data-awg-del]').forEach(b => {
    b.addEventListener('click', async () => {
      const n = decodeURIComponent(b.getAttribute('data-awg-del'));
      if (!confirm('确认删除客户端「' + n + '」？该客户端会立即断开连接。')) return;
      const json = await awgPost('manage-amneziawg', { action: 'peer_del', name: n });
      if (json.ok) { showToast('已删除客户端 ' + n, 'success'); loadAwgState(); }
      else { alert(json.error || '删除失败'); }
    });
  });
}

if (btnInstallAwg) {
  btnInstallAwg.addEventListener('click', () => {
    if (!awgInstallBox) return;
    awgInstallBox.style.display = (awgInstallBox.style.display === 'none') ? 'block' : 'none';
  });
}

if (btnDoInstallAwg) {
  btnDoInstallAwg.addEventListener('click', async () => {
    const line = awgLineSelect ? awgLineSelect.value : '3';
    const endpoint = awgEndpointInput ? awgEndpointInput.value.trim() : '';
    if (!endpoint) { alert('请填写客户端连接地址（域名或公网 IP）'); return; }
    if (!confirm('确认安装 AmneziaWG（协议线 AWG ' + line + '.x）？\n\n会下载自建静态二进制并启动独立服务，不影响现有的 Hysteria 2。')) return;
    btnDoInstallAwg.disabled = true;
    const orig = btnDoInstallAwg.textContent;
    btnDoInstallAwg.textContent = '⏳ 安装中，请稍候...';
    try {
      const json = await awgPost('install-amneziawg', { line: line, endpoint: endpoint });
      if (json.ok) { showToast(json.message || '安装完成', 'success'); loadAwgState(); }
      else { alert(json.error || '安装失败'); }
    } finally {
      btnDoInstallAwg.disabled = false;
      btnDoInstallAwg.textContent = orig;
    }
  });
}

if (btnAddAwgPeer) {
  btnAddAwgPeer.addEventListener('click', async () => {
    const name = awgPeerName ? awgPeerName.value.trim() : '';
    const endpoint = (awgPeerEndpoint && awgPeerEndpoint.value.trim()) || awgCurrentEndpoint;
    if (!name) { alert('请填写客户端名称'); return; }
    if (!/^[A-Za-z0-9_.-]{1,32}$/.test(name)) { alert('名称只允许字母、数字、点、下划线、连字符，且不超过 32 字符'); return; }
    if (!endpoint) { alert('请填写连接地址'); return; }
    btnAddAwgPeer.disabled = true;
    try {
      const json = await awgPost('manage-amneziawg', { action: 'peer_add', name: name, endpoint: endpoint });
      if (json.ok) {
        if (awgPeerName) awgPeerName.value = '';
        showToast('已新增客户端 ' + name + '，正在打开配置', 'success');
        window.open(location.pathname + 'awg-conf?name=' + encodeURIComponent(name), '_blank');
        loadAwgState();
      } else { alert(json.error || '新增失败'); }
    } finally {
      btnAddAwgPeer.disabled = false;
    }
  });
}

if (btnSwitchAwgLine) {
  btnSwitchAwgLine.addEventListener('click', async () => {
    const target = prompt('切换 AmneziaWG 协议线\n\n2 = AWG 2.x（参数体系稳定）\n3 = AWG 3.x（含头部保护与抗行为分析）\n\n⚠️ 切换会重新生成全部混淆参数，已发放的客户端配置会立即失效，必须重新导出。\n\n请输入目标协议线：', awgCurrentLine === '3' ? '2' : '3');
    if (target !== '2' && target !== '3') return;
    if (target === awgCurrentLine) { alert('已经是 AWG ' + awgCurrentLine + '.x，无需切换。'); return; }
    if (!confirm('确认切换到 AWG ' + target + '.x？所有已发放的客户端配置都会失效。')) return;
    const json = await awgPost('manage-amneziawg', { action: 'set_line', line: target });
    if (json.ok) { showToast(json.message || '已切换协议线', 'success'); loadAwgState(); }
    else { alert(json.error || '切换失败'); }
  });
}

if (btnUpdateAwg) {
  btnUpdateAwg.addEventListener('click', async () => {
    if (!confirm('确认更新 AmneziaWG 二进制？协议线与混淆参数保持不变，客户端无需重新导入。')) return;
    const json = await awgPost('manage-amneziawg', { action: 'update' });
    if (json.ok) { showToast(json.message || '更新完成', 'success'); loadAwgState(); }
    else { alert(json.error || '更新失败'); }
  });
}

loadAwgState();
"""

# ============================================================================
# LOGIN_SCRIPT
# ============================================================================
LOGIN_SCRIPT = r"""
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

// 🔴 不能写成 <button onclick="toggleSecret(...)"> —— CSP 的 script-src 只有
// 哈希白名单、没有 'unsafe-inline'，内联事件处理器会被浏览器直接拒绝执行，
// 按钮点了毫无反应。必须在这里用 addEventListener 绑定（整段脚本有 CSP 哈希，
// 因此被允许）。
document.querySelectorAll('.toggle-pwd').forEach(btn => {
  btn.addEventListener('click', () => {
    const input = btn.parentElement.querySelector('input');
    if (input) toggleSecret(input.id, btn);
  });
});
"""

# ============================================================================
# USER_SCRIPT
# ============================================================================
USER_SCRIPT = r"""
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
