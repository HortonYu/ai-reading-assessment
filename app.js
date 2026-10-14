// 全局通用辅助逻辑
function checkKeyStatus() {
  const key = localStorage.getItem("deepseek_api_key");
  const indicator = document.getElementById("key-indicator");
  if (indicator) {
    if (key && key.startsWith("sk-")) {
      indicator.className = "w-2 h-2 rounded-full bg-emerald-500 inline-block ml-1";
      indicator.title = "DeepSeek Key 已设置";
    } else {
      indicator.className = "w-2 h-2 rounded-full bg-amber-500 inline-block ml-1";
      indicator.title = "未设置 Key，将优先从后端读取";
    }
  }
}

function promptApiKey() {
  const currentKey = localStorage.getItem("deepseek_api_key") || "";
  const input = prompt("请输入你的 DeepSeek API Key (以 sk- 开头)：", currentKey);
  if (input !== null) {
    localStorage.setItem("deepseek_api_key", input.trim());
    checkKeyStatus();
    alert("DeepSeek API Key 设置已更新！");
  }
}
