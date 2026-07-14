import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");
const readSource = (path: string) => readFileSync(resolve(root, path), "utf8");

const settings = readSource("src/components/embed/ChatSettings.vue");
const embedChat = readSource("src/views/EmbedChat.vue");
const debugPanel = readSource("src/components/DebugConfigPanel.vue");
const agentDebug = readSource("src/views/AgentDebug.vue");

assert.doesNotMatch(settings, />模型选择</, "settings should remove the duplicate model selector");
assert.match(settings, />反幻觉校验</, "settings should expose the grounding toggle");
assert.match(settings, /handleSetGrounding\(true\)/, "settings should allow enabling grounding");
assert.match(settings, /handleSetGrounding\(false\)/, "settings should allow disabling grounding");
assert.match(embedChat, /enableGrounding:\s*false/, "grounding should default to disabled");
assert.match(
  embedChat,
  /grounding_enabled:\s*config\.enableGrounding/,
  "every chat request should send an explicit grounding boolean",
);
assert.match(
  embedChat,
  /const resetSession[\s\S]*?config\.enableGrounding\s*=\s*false/,
  "starting a new conversation should reset grounding to disabled",
);

assert.doesNotMatch(
  debugPanel,
  /模型覆盖 \(Model Override\)/,
  "AgentDebug panel should remove the duplicate model override",
);
assert.match(debugPanel, />反幻觉校验</, "AgentDebug panel should expose the grounding toggle");
assert.match(
  debugPanel,
  /v-model="config\.enableGrounding"/,
  "AgentDebug panel should bind the shared grounding setting",
);
assert.match(agentDebug, /enableGrounding:\s*false/, "AgentDebug should default grounding to disabled");
assert.match(
  agentDebug,
  /grounding_enabled:\s*debugConfig\.enableGrounding/,
  "AgentDebug should send an explicit grounding boolean",
);
assert.match(
  agentDebug,
  /const generateNewConversation[\s\S]*?debugConfig\.enableGrounding\s*=\s*false/,
  "a new AgentDebug conversation should reset grounding to disabled",
);
assert.match(
  agentDebug,
  /:selected-model="debugConfig\.model"[\s\S]*?@update:selected-model="debugConfig\.model = \$event"/,
  "the AgentDebug input model selector should remain available",
);

console.log("groundingToggle.test.ts passed");
