export type VoiceControlAction = "back" | "home" | "help" | "repeat" | "stop";

function normalize(command: string): string {
  return command
    .trim()
    .toLocaleLowerCase("en-CA")
    .replace(/[.,!?;:]+$/g, "")
    .replace(/\s+/g, " ");
}

export function resolveVoiceControl(command: string): VoiceControlAction | null {
  const normalized = normalize(command);

  if (/^(?:go\s+)?back$|^(?:open\s+the\s+)?previous\s+page$/.test(normalized)) return "back";
  if (/^(?:go\s+)?home$|^(?:return\s+to|open)\s+(?:the\s+)?dashboard$/.test(normalized)) return "home";
  if (/^help$|^voice\s+commands$|^what\s+can\s+i\s+say$/.test(normalized)) return "help";
  if (/^repeat(?:\s+that|\s+the\s+(?:last\s+)?answer)?$|^say\s+that\s+again$/.test(normalized)) {
    return "repeat";
  }
  if (
    /^stop$|^stop\s+listening$|^(?:turn\s+off|disable|stop)\s+(?:hey\s+)?chat$/.test(normalized)
  ) {
    return "stop";
  }

  return null;
}
