export interface LLMModel {
  id: string;
  name: string;
  performance: string;
}

export interface AvailableModels {
  llm_models: LLMModel[];
}

export interface SettingsResponse {
  llm_model: string;
  embedding_model?: string;
  whisper_model?: string;
  ocr_lang?: string;
  [key: string]: unknown;
}

export interface ConversationSettingsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleteAllConversations: () => void;
}
