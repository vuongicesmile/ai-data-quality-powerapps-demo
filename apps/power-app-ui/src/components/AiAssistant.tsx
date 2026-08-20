import { Button, Input } from "@fluentui/react-components";
import { BotSparkleRegular, DismissRegular, SendRegular } from "@fluentui/react-icons";
import { useState } from "react";
import { useDemoWorkspace } from "../state/DemoWorkspaceProvider";
import type { ChatMessage, ViewName } from "../ui/types";

const welcome: ChatMessage[] = [
  { id: 1, sender: "bot", text: "Xin chào! Tôi là Trợ lý AI. Tôi có thể giúp bạn điều hướng hoặc giải đáp về luồng dữ liệu." },
  { id: 2, sender: "bot", text: "Hiện tại bạn đang ở bước Review Rules. Bạn muốn mở tác vụ nào?", suggestions: [
    { label: "Xem 3 Rules đang chờ duyệt", view: "rules" }, { label: "Đi đến Phê duyệt Bronze", view: "bronze_approval" }, { label: "Xem kết quả Silver", view: "silver" },
  ] },
];

const intents: Array<[string[], ViewName, string]> = [
  [["workspace", "home", "trang chủ"], "workspace", "Đang chuyển bạn đến Workspace..."],
  [["ingestion", "runs"], "ingestion", "Đang mở danh sách Ingestion Runs..."],
  [["bronze approval", "duyệt bronze", "phê duyệt bronze"], "bronze_approval", "Đang mở Phê duyệt Bronze..."],
  [["silver"], "silver", "Đang mở dữ liệu Silver..."], [["gold"], "gold", "Đang mở công thức Gold..."],
  [["mapping"], "mapping", "Đang mở Schema Mapping..."], [["activity", "history"], "activity", "Đang mở Activity..."],
  [["profiles"], "profiles", "Đang mở Profiles..."], [["rules"], "rules", "Đang mở Rules & Evidence..."], [["bronze"], "bronze", "Đang mở Bronze..."],
];

export function AiAssistant() {
  const { navigate } = useDemoWorkspace();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(welcome);
  const [input, setInput] = useState("");
  function add(text: string) {
    const value = text.trim(); if (!value) return;
    const normalized = value.toLowerCase();
    const match = intents.find(([keys]) => keys.some((key) => normalized.includes(key)));
    let response = "Tôi có thể giúp bạn điều hướng giữa Workspace, Bronze, Profiles, Rules, Mapping, Silver và Gold.";
    if (normalized.includes("bronze là gì")) response = "Bronze là lớp snapshot dữ liệu thô, bất biến, được chụp từ SharePoint và lưu trong Dataverse.";
    else if (normalized.includes("quality") || normalized.includes("chất lượng")) response = "Điểm chất lượng hiện tại là 91%. Email thấp nhất ở mức 82%.";
    else if (match) response = match[2];
    setMessages((current) => [...current, { id: Date.now(), sender: "user", text: value }, { id: Date.now() + 1, sender: "bot", text: response }]);
    setInput("");
    if (match) window.setTimeout(() => navigate(match[1]), 500);
  }
  return <>
    {open && <section className="chat-window" aria-label="AI Assistant"><header><span><BotSparkleRegular /> AI Assistant</span><Button appearance="transparent" aria-label="Close chat" icon={<DismissRegular />} onClick={() => setOpen(false)} /></header><div className="chat-messages">{messages.map((message) => <div className={`chat-message ${message.sender}`} key={message.id}><p>{message.text}</p>{message.suggestions && <div className="chat-suggestions">{message.suggestions.map((suggestion) => <Button key={suggestion.view} size="small" onClick={() => { setMessages((current) => [...current, { id: Date.now(), sender: "user", text: suggestion.label }]); navigate(suggestion.view); }}>{suggestion.label}</Button>)}</div>}</div>)}</div><form className="chat-composer" onSubmit={(event) => { event.preventDefault(); add(input); }}><Input value={input} onChange={(_, data) => setInput(data.value)} placeholder="Gõ yêu cầu hoặc câu hỏi..." /><Button type="submit" appearance="primary" aria-label="Send" icon={<SendRegular />} /></form></section>}
    <Button className="chat-launcher" shape="circular" appearance="primary" size="large" aria-label="Open AI Assistant" icon={<BotSparkleRegular />} onClick={() => setOpen((value) => !value)} />
  </>;
}
