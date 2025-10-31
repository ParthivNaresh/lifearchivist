import { Trash2 } from 'lucide-react';
import * as Tabs from '@radix-ui/react-tabs';

interface DangerZoneTabProps {
  onDeleteAll: () => void;
}

export const DangerZoneTab: React.FC<DangerZoneTabProps> = ({ onDeleteAll }) => {
  return (
    <Tabs.Content value="danger" className="space-y-4 overflow-y-auto h-full">
      <div className="bg-destructive/5 backdrop-blur-sm rounded-lg border border-destructive/20 p-6">
        <h3 className="text-base font-medium mb-2 text-destructive flex items-center space-x-2">
          <Trash2 className="h-5 w-5" />
          <span>Danger Zone</span>
        </h3>
        <p className="text-sm text-muted-foreground mb-4">
          Permanently delete all conversations. This action cannot be undone.
        </p>
        <button
          onClick={onDeleteAll}
          className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90 transition-colors font-medium"
        >
          <Trash2 className="h-4 w-4" />
          <span>Delete All Conversations</span>
        </button>
      </div>
    </Tabs.Content>
  );
};
