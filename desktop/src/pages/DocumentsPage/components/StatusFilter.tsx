import React from 'react';
import { DocumentStatus } from '../types';
import { STATUS_OPTIONS, UI_TEXT } from '../constants';

interface StatusFilterProps {
  selectedStatus: DocumentStatus;
  onStatusChange: (status: DocumentStatus) => void;
}

export const StatusFilter: React.FC<StatusFilterProps> = ({ 
  selectedStatus, 
  onStatusChange 
}) => {
  return (
    <div className="flex items-center space-x-2">
      <label className="text-sm font-medium">{UI_TEXT.FILTER_LABEL}</label>
      <select
        value={selectedStatus}
        onChange={(e) => onStatusChange(e.target.value as DocumentStatus)}
        className="px-3 py-1 border border-input rounded-md bg-background text-foreground"
      >
        {STATUS_OPTIONS.map(option => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
};