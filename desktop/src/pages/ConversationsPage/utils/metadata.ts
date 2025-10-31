import type { MessageMetadata, ErrorMessageMetadata } from '../types';

export function parseMessageMetadata(metadata: string | MessageMetadata): MessageMetadata {
  if (typeof metadata === 'string') {
    return JSON.parse(metadata) as MessageMetadata;
  }
  return metadata;
}

export function isErrorMetadata(metadata: MessageMetadata): metadata is ErrorMessageMetadata {
  return metadata.is_error === true;
}

export function getMessageMetadata(metadata: string | MessageMetadata): MessageMetadata {
  return parseMessageMetadata(metadata);
}

export function getErrorMetadata(metadata: string | MessageMetadata): ErrorMessageMetadata | null {
  const parsed = parseMessageMetadata(metadata);
  return isErrorMetadata(parsed) ? parsed : null;
}
