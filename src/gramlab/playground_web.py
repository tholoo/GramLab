# ruff: noqa: E501
"""Loopback browser client for one authenticated persistent playground."""

from __future__ import annotations

import html
import json
import secrets
import threading
import webbrowser
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Self
from urllib.parse import urlsplit

from gramlab.playground import request

_BODY_LIMIT = 64 * 1024
_OPERATIONS = {"send": "send", "tap": "tap", "add-bot": "add_bot", "reset": "reset", "stop": "stop"}


def _page(title: str, preferred_actors: dict[int, int]) -> bytes:
    configuration = json.dumps(
        {"preferredActors": {str(chat): actor for chat, actor in preferred_actors.items()}},
        ensure_ascii=True,
        separators=(",", ":"),
    ).replace("<", "\\u003c")
    rendered_title = html.escape(title, quote=True)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{rendered_title}</title>
<style>
:root{{color-scheme:light;--ink:#17212b;--muted:#70808f;--line:#dce5eb;--panel:#fff;
--canvas:#eaf2f6;--accent:#2878b5;--accent-dark:#1f6599;--own:#d9fdd3;--bot:#fff;
--danger:#b33b45;--shadow:0 18px 60px rgba(34,58,74,.18)}}
*{{box-sizing:border-box}}
html,body{{height:100%;margin:0}}
body{{font:15px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
background:linear-gradient(145deg,#dcecf3,#f3f7f9);color:var(--ink);padding:clamp(0px,2vw,24px)}}
button,select,textarea{{font:inherit}}
button{{cursor:pointer}}
button:disabled{{cursor:not-allowed;opacity:.55}}
.app{{height:100%;max-width:1280px;margin:auto;display:grid;grid-template-columns:320px 1fr;
background:var(--panel);border:1px solid rgba(95,124,142,.22);border-radius:20px;overflow:hidden;
box-shadow:var(--shadow)}}
.sidebar{{display:flex;min-width:0;flex-direction:column;border-right:1px solid var(--line);background:#f8fbfc}}
.brand{{padding:21px 22px 18px;border-bottom:1px solid var(--line)}}
.brand h1{{font-size:18px;margin:0 0 3px;letter-spacing:-.01em}}
.connection{{display:flex;align-items:center;gap:7px;color:var(--muted);font-size:13px}}
.dot{{width:8px;height:8px;border-radius:50%;background:#d49239;box-shadow:0 0 0 3px #f8e9d4}}
.dot.online{{background:#42a568;box-shadow:0 0 0 3px #dff2e5}}
.chats{{overflow:auto;padding:9px;flex:1}}
.chat-button{{width:100%;border:0;background:transparent;border-radius:12px;padding:12px;text-align:left;
display:grid;grid-template-columns:42px 1fr;gap:11px;color:inherit}}
.chat-button:hover{{background:#edf4f7}}
.chat-button.active{{background:#dfeff7}}
.avatar{{width:42px;height:42px;border-radius:50%;display:grid;place-items:center;color:white;
font-weight:700;background:linear-gradient(145deg,#3188c3,#62b0be)}}
.chat-name{{font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px}}
.chat-meta{{color:var(--muted);font-size:12px;margin-top:3px}}
.sidebar-actions{{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:12px;border-top:1px solid var(--line)}}
.secondary{{border:1px solid var(--line);background:white;border-radius:10px;padding:9px 10px;color:var(--ink)}}
.secondary:hover{{background:#f1f6f8}}
.secondary.danger{{color:var(--danger)}}
.conversation{{min-width:0;display:grid;grid-template-rows:auto 1fr auto;background:var(--canvas);
background-image:radial-gradient(rgba(74,116,139,.08) 1px,transparent 1px);background-size:18px 18px}}
.topbar{{min-height:74px;padding:13px 20px;display:flex;align-items:center;justify-content:space-between;
gap:16px;background:rgba(255,255,255,.94);border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}}
.title h2{{font-size:16px;margin:0 0 3px}}
.title p{{font-size:12px;color:var(--muted);margin:0}}
.actor{{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:12px}}
.actor select{{max-width:170px;border:1px solid var(--line);border-radius:9px;background:white;padding:7px 28px 7px 9px;color:var(--ink)}}
.messages{{overflow:auto;padding:24px clamp(14px,3vw,42px);display:flex;flex-direction:column;gap:9px}}
.empty{{margin:auto;color:var(--muted);background:rgba(255,255,255,.75);padding:10px 14px;border-radius:12px}}
.message{{max-width:min(680px,82%);align-self:flex-start;background:var(--bot);border-radius:14px 14px 14px 4px;
padding:9px 12px 7px;box-shadow:0 1px 2px rgba(27,52,67,.16)}}
.message.own{{align-self:flex-end;background:var(--own);border-radius:14px 14px 4px 14px}}
.sender{{color:var(--accent-dark);font-size:12px;font-weight:700;margin-bottom:3px}}
.body{{white-space:pre-wrap;overflow-wrap:anywhere}}
.message-actions{{display:grid;gap:5px;margin-top:9px}}
.message-actions button{{border:1px solid #bbd8ea;background:#f6fbfe;color:var(--accent-dark);border-radius:9px;
padding:7px 10px;font-weight:650}}
.message-actions button:hover{{background:#e7f4fb}}
.time{{text-align:right;color:var(--muted);font-size:10px;margin-top:3px}}
.compose-area{{background:rgba(255,255,255,.94);border-top:1px solid var(--line);padding:10px 14px 14px}}
.add-bot{{display:none;align-items:center;justify-content:space-between;gap:12px;margin-bottom:9px;
background:#fff6d9;border:1px solid #ead99e;border-radius:11px;padding:9px 11px;font-size:13px}}
.add-bot.visible{{display:flex}}
.add-bot button{{border:0;border-radius:8px;background:#8d6c17;color:white;padding:7px 10px;font-weight:650}}
.composer{{display:grid;grid-template-columns:1fr auto;gap:9px;align-items:end}}
textarea{{width:100%;resize:none;max-height:140px;min-height:44px;border:1px solid var(--line);border-radius:14px;
background:white;padding:11px 13px;outline:none;color:var(--ink)}}
textarea:focus{{border-color:#7db5d8;box-shadow:0 0 0 3px rgba(73,151,200,.13)}}
#send{{height:44px;border:0;border-radius:12px;background:var(--accent);color:white;padding:0 19px;font-weight:700}}
#send:hover{{background:var(--accent-dark)}}
.notice{{min-height:18px;color:var(--danger);font-size:12px;padding:4px 3px 0}}
@media(max-width:720px){{body{{padding:0}}.app{{border:0;border-radius:0;grid-template-columns:96px 1fr}}
.brand{{padding:16px 9px}}.brand h1{{font-size:13px}}.connection span:last-child{{display:none}}
.chats{{padding:6px}}.chat-button{{display:block;padding:8px 3px;text-align:center}}.avatar{{margin:auto}}
.chat-name{{font-size:10px;margin-top:4px}}.chat-meta,.sidebar-actions{{display:none}}
.topbar{{padding:10px 12px}}.actor span{{display:none}}.message{{max-width:92%}}}}
</style>
</head>
<body>
<main class="app">
  <aside class="sidebar">
    <div class="brand"><h1>{rendered_title}</h1><div class="connection"><span id="dot" class="dot"></span><span id="connection">Starting playground…</span></div></div>
    <nav id="chats" class="chats" aria-label="Conversations"></nav>
    <div class="sidebar-actions"><button id="reset" class="secondary">Reset state</button><button id="stop" class="secondary danger">Stop</button></div>
  </aside>
  <section class="conversation">
    <header class="topbar"><div class="title"><h2 id="chat-title">Loading…</h2><p id="chat-detail"></p></div>
      <label class="actor"><span>Send as</span><select id="actor" aria-label="Send as"></select></label></header>
    <div id="messages" class="messages" aria-live="polite"><div class="empty">Preparing your seeded chats…</div></div>
    <div class="compose-area">
      <div id="add-bot" class="add-bot"><span id="add-bot-copy"></span><button id="add-bot-button" type="button">Add bot</button></div>
      <form id="composer-form" class="composer"><textarea id="composer" rows="1" maxlength="4096" placeholder="Write a message" aria-label="Message"></textarea><button id="send" type="submit">Send</button></form>
      <div id="notice" class="notice" role="status"></div>
    </div>
  </section>
</main>
<script>
"use strict";
const config={configuration};
const root=new URL(".",window.location.href).pathname;
const chatsNode=document.getElementById("chats");
const messagesNode=document.getElementById("messages");
const actorNode=document.getElementById("actor");
const composer=document.getElementById("composer");
const composerForm=document.getElementById("composer-form");
const notice=document.getElementById("notice");
let snapshot=null;
let selectedChat=null;
let sending=false;
const actorChoices={{...config.preferredActors}};

async function api(path,payload){{
  const options=payload===undefined?{{cache:"no-store"}}:{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify(payload)}};
  const response=await fetch(root+"api/"+path,options);
  const body=await response.json();
  if(!response.ok)throw new Error(body.error||"The playground request failed");
  return body;
}}
function user(id){{return snapshot.world.users.find(item=>item.id===id)}}
function name(person){{return person?(person.first_name+(person.last_name?" "+person.last_name:"")):"Unknown"}}
function chatName(chat){{
  if(chat.type==="supergroup")return chat.title;
  return name(user(chat.bot_id));
}}
function members(chat){{
  if(chat.type==="private")return [user(chat.user_id)].filter(Boolean);
  const active=new Set(chat.members.filter(item=>item.status!=="left"&&item.status!=="kicked").map(item=>item.user_id));
  return snapshot.world.users.filter(item=>active.has(item.id)&&!item.is_bot);
}}
function selectedActor(chat){{
  const people=members(chat);
  const preferred=Number(actorChoices[String(chat.id)]);
  return people.some(item=>item.id===preferred)?preferred:(people[0]?.id??null);
}}
function textValue(value){{
  if(typeof value==="string")return value;
  if(Array.isArray(value))return value.map(textValue).join("");
  if(!value||typeof value!=="object")return "";
  if(value.type==="custom_emoji")return value.alternative_text||"";
  if(value.type==="button")return "";
  if("text" in value)return textValue(value.text);
  return "";
}}
function richLines(value,lines=[]){{
  if(!value||typeof value!=="object")return lines;
  if(Array.isArray(value)){{value.forEach(item=>richLines(item,lines));return lines}}
  if(value.type==="button"||("callback_data" in value&&"text" in value))return lines;
  for(const field of ["text","summary","credit"]){{if(field in value){{const text=textValue(value[field]);if(text)lines.push(text)}}}}
  if(value.caption)richLines(value.caption,lines);
  for(const field of ["blocks","items","cells"]){{if(field in value)richLines(value[field],lines)}}
  return lines;
}}
function buttonLabels(value,result=[]){{
  if(!value||typeof value!=="object")return result;
  if(Array.isArray(value)){{value.forEach(item=>buttonLabels(item,result));return result}}
  const button=value.type==="button"&&value.button?value.button:value;
  if("text" in button&&(Object.hasOwn(button,"callback_data")||Object.hasOwn(button,"disabled"))){{
    result.push({{label:textValue(button.text),disabled:Object.hasOwn(button,"disabled")}});
    if(button!==value)return result;
  }}
  Object.values(value).forEach(item=>buttonLabels(item,result));
  return result;
}}
function messageText(message){{
  const parts=[];
  if(message.text)parts.push(message.text);
  if(message.caption)parts.push(message.caption);
  if(message.rich_message)parts.push(...richLines(message.rich_message));
  return [...new Set(parts)].join("\\n");
}}
function renderChats(){{
  chatsNode.replaceChildren();
  for(const chat of snapshot.world.chats){{
    const button=document.createElement("button");button.type="button";button.className="chat-button"+(chat.id===selectedChat?" active":"");
    const avatar=document.createElement("span");avatar.className="avatar";avatar.textContent=chatName(chat).slice(0,1).toUpperCase();
    const copy=document.createElement("span");const title=document.createElement("div");title.className="chat-name";title.textContent=chatName(chat);
    const meta=document.createElement("div");meta.className="chat-meta";meta.textContent=(snapshot.histories[String(chat.id)]||[]).length+" messages";
    copy.append(title,meta);button.append(avatar,copy);button.addEventListener("click",()=>{{selectedChat=chat.id;render()}});chatsNode.append(button);
  }}
}}
function renderActors(chat){{
  const people=members(chat);actorNode.replaceChildren();
  for(const person of people){{const option=document.createElement("option");option.value=String(person.id);option.textContent=name(person);actorNode.append(option)}}
  const selected=selectedActor(chat);if(selected!==null)actorNode.value=String(selected);
  actorNode.disabled=people.length===0;
}}
function renderMessages(chat){{
  const wasNearBottom=messagesNode.scrollHeight-messagesNode.scrollTop-messagesNode.clientHeight<80;
  messagesNode.replaceChildren();const history=snapshot.histories[String(chat.id)]||[];const actor=selectedActor(chat);
  if(!history.length){{const empty=document.createElement("div");empty.className="empty";empty.textContent="No messages yet";messagesNode.append(empty);return}}
  for(const message of history){{
    const bubble=document.createElement("article");bubble.className="message"+(message.sender_id===actor?" own":"");bubble.dir="auto";
    const sender=document.createElement("div");sender.className="sender";sender.textContent=name(user(message.sender_id));bubble.append(sender);
    const body=document.createElement("div");body.className="body";body.textContent=messageText(message);bubble.append(body);
    const labels=message.rich_message?buttonLabels(message.rich_message):[];
    if(labels.length){{const actions=document.createElement("div");actions.className="message-actions";
      for(const item of labels){{const control=document.createElement("button");control.type="button";control.textContent=item.label;control.disabled=item.disabled;
        control.addEventListener("click",()=>perform("tap",{{chat_id:chat.id,actor_id:Number(actorNode.value),label:item.label}}));actions.append(control)}}bubble.append(actions)}}
    const date=document.createElement("div");date.className="time";date.textContent=new Date(message.date*1000).toLocaleTimeString([],{{hour:"2-digit",minute:"2-digit"}});bubble.append(date);
    messagesNode.append(bubble);
  }}
  if(wasNearBottom)requestAnimationFrame(()=>messagesNode.scrollTop=messagesNode.scrollHeight);
}}
function renderAddBot(chat){{
  const panel=document.getElementById("add-bot");panel.classList.remove("visible");panel.dataset.bot="";panel.dataset.actor="";
  if(chat.type!=="supergroup")return;
  const present=new Set(chat.members.filter(item=>item.status!=="left"&&item.status!=="kicked").map(item=>item.user_id));
  const missing=Object.entries(snapshot.bots).find(([,id])=>!present.has(id));
  const privileged=chat.members.find(item=>["creator","administrator"].includes(item.status)&&!user(item.user_id)?.is_bot);
  if(!missing||!privileged)return;
  panel.dataset.bot=missing[0];panel.dataset.actor=user(privileged.user_id)?.username||"";
  document.getElementById("add-bot-copy").textContent=missing[0]+" is not in this group.";
  document.getElementById("add-bot-button").textContent="Add "+missing[0];panel.classList.add("visible");
}}
function render(){{
  if(!snapshot)return;
  if(selectedChat===null||!snapshot.world.chats.some(chat=>chat.id===selectedChat))selectedChat=snapshot.world.chats[0]?.id??null;
  renderChats();const chat=snapshot.world.chats.find(item=>item.id===selectedChat);if(!chat)return;
  document.getElementById("chat-title").textContent=chatName(chat);
  document.getElementById("chat-detail").textContent=chat.type==="supergroup"?members(chat).length+" people":"Private chat";
  renderActors(chat);renderMessages(chat);renderAddBot(chat);composer.disabled=actorNode.disabled;document.getElementById("send").disabled=actorNode.disabled;
}}
async function refresh(){{
  if(sending)return;
  try{{snapshot=await api("status");document.getElementById("dot").classList.add("online");document.getElementById("connection").textContent=snapshot.at_baseline?"Ready · seed unchanged":"Ready · seed changed";notice.textContent="";render()}}
  catch(error){{document.getElementById("dot").classList.remove("online");document.getElementById("connection").textContent="Waiting for playground…";notice.textContent=error.message}}
}}
async function perform(operation,payload){{
  if(sending)return;sending=true;notice.textContent="";
  try{{const result=await api(operation,payload);if(operation==="reset")snapshot=result;if(operation==="stop"){{document.getElementById("connection").textContent="Stopped";notice.textContent="You can close this tab."}}else await refresh();render()}}
  catch(error){{notice.textContent=error.message}}finally{{sending=false}}
}}
actorNode.addEventListener("change",()=>{{actorChoices[String(selectedChat)]=Number(actorNode.value);renderMessages(snapshot.world.chats.find(chat=>chat.id===selectedChat))}});
composer.addEventListener("keydown",event=>{{if(event.key==="Enter"&&!event.shiftKey){{event.preventDefault();composerForm.requestSubmit()}}}});
composerForm.addEventListener("submit",event=>{{event.preventDefault();const text=composer.value;if(!text)return;const payload={{chat_id:selectedChat,actor_id:Number(actorNode.value),text}};composer.value="";perform("send",payload)}});
document.getElementById("reset").addEventListener("click",()=>perform("reset",{{}}));
document.getElementById("stop").addEventListener("click",()=>perform("stop",{{}}));
document.getElementById("add-bot-button").addEventListener("click",()=>{{const panel=document.getElementById("add-bot");perform("add-bot",{{group:snapshot.world.chats.find(chat=>chat.id===selectedChat).title,bot:panel.dataset.bot,actor:panel.dataset.actor}})}});
refresh();window.setInterval(refresh,750);
</script>
</body>
</html>""".encode()


class BrowserPlayground:
    """Serve and optionally open one capability-scoped loopback playground page."""

    def __init__(
        self,
        output: Path,
        *,
        title: str = "GramLab playground",
        preferred_actors: dict[int, int] | None = None,
        opener: Callable[[str], bool] = webbrowser.open,
    ) -> None:
        if (
            not isinstance(title, str)
            or not 1 <= len(title) <= 120
            or any(ord(c) < 32 for c in title)
        ):
            raise ValueError("Playground title must contain 1 to 120 visible characters")
        actors = preferred_actors or {}
        if any(type(chat) is not int or type(actor) is not int for chat, actor in actors.items()):
            raise ValueError("Preferred playground actors must map integer chats to integer users")
        self.output = output.absolute()
        self.title = title
        self.preferred_actors = dict(actors)
        self.opener = opener
        self._token = secrets.token_urlsafe(24)
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._url: str | None = None

    @property
    def url(self) -> str:
        if self._url is None:
            raise RuntimeError("Browser playground has not started")
        return self._url

    def start(self) -> str:
        if self._server is not None:
            raise RuntimeError("Browser playground is already started")
        owner = self
        page = _page(self.title, self.preferred_actors)

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _send(self, status: int, body: bytes, content_type: str) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src data:; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
                )
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Referrer-Policy", "no-referrer")
                self.end_headers()
                self.wfile.write(body)

            def _json(self, status: int, value: dict[str, Any]) -> None:
                self._send(
                    status, json.dumps(value, ensure_ascii=True).encode(), "application/json"
                )

            def _valid_host(self) -> bool:
                expected = f"127.0.0.1:{self.server.server_port}"  # type: ignore[attr-defined]
                return self.headers.get("Host") == expected

            def do_GET(self) -> None:
                path = urlsplit(self.path).path
                if not self._valid_host():
                    self._json(421, {"error": "The playground host did not match"})
                elif path == f"/{owner._token}/":
                    self._send(200, page, "text/html; charset=utf-8")
                elif path == f"/{owner._token}/api/status":
                    try:
                        self._json(200, request(owner.output, "status"))
                    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
                        self._json(503, {"error": str(error)})
                else:
                    self._json(404, {"error": "Not found"})

            def do_POST(self) -> None:
                path = urlsplit(self.path).path
                prefix = f"/{owner._token}/api/"
                parsed = urlsplit(owner.url)
                expected_origin = f"{parsed.scheme}://{parsed.netloc}"
                if not self._valid_host() or self.headers.get("Origin") != expected_origin:
                    self._json(403, {"error": "The playground request origin did not match"})
                    return
                operation_name = path.removeprefix(prefix) if path.startswith(prefix) else ""
                operation = _OPERATIONS.get(operation_name)
                if operation is None or self.headers.get_content_type() != "application/json":
                    self._json(404, {"error": "Not found"})
                    return
                try:
                    size = int(self.headers.get("Content-Length", ""))
                except ValueError:
                    size = -1
                if not 0 <= size <= _BODY_LIMIT:
                    self._json(413, {"error": "The playground request is too large"})
                    return
                try:
                    parameters = json.loads(self.rfile.read(size))
                    if not isinstance(parameters, dict):
                        raise ValueError("Playground parameters must be an object")
                    result = request(owner.output, operation, parameters)
                except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
                    self._json(400, {"error": str(error)})
                    return
                self._json(200, result)

            def log_message(self, *_: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        self._server = server
        self._url = f"http://127.0.0.1:{server.server_port}/{self._token}/"
        self._thread = threading.Thread(target=server.serve_forever, daemon=True)
        self._thread.start()
        self.opener(self.url)
        return self.url

    def close(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                raise RuntimeError("Browser playground server did not stop")
        self._server = None
        self._thread = None
        self._url = None

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
