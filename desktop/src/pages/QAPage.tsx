import React from 'react';
import {
  useQAState,
  useQAConversation,
  useQuestionSubmit,
  useClearConfirmation,
  QAHeader,
  MessageArea,
  InputArea,
} from './QAPage/index';

const QAPage: React.FC = () => {
  // Use custom hooks for state management
  const {
    currentQuestion,
    setCurrentQuestion,
    isLoading,
    setIsLoading,
    contextLimit,
    setContextLimit,
    showClearConfirm,
    setShowClearConfirm,
  } = useQAState();

  const {
    messages,
    addMessage,
    clearConversation,
    conversationStats,
  } = useQAConversation();

  const { handleSubmit } = useQuestionSubmit(
    currentQuestion,
    contextLimit,
    setCurrentQuestion,
    setIsLoading,
    addMessage
  );

  const { handleClearConversation } = useClearConfirmation(
    showClearConfirm,
    setShowClearConfirm,
    clearConversation
  );

  return (
    <div className="flex flex-col h-full bg-background">
      <QAHeader
        conversationStats={conversationStats}
        contextLimit={contextLimit}
        showClearConfirm={showClearConfirm}
        onContextLimitChange={setContextLimit}
        onShowClearConfirm={setShowClearConfirm}
        onClearConversation={handleClearConversation}
      />

      <MessageArea
        messages={messages}
        isLoading={isLoading}
      />

      <InputArea
        currentQuestion={currentQuestion}
        isLoading={isLoading}
        onQuestionChange={setCurrentQuestion}
        onSubmit={handleSubmit}
      />
    </div>
  );
};

export default QAPage;